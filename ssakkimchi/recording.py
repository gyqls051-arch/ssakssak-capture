"""ffmpeg subprocess 기반 화면 녹화 (MP4 / GIF).

설계 원칙
- ffmpeg에 'q' 를 stdin으로 보내서 graceful stop (윈도우는 SIGINT 안 통함)
- stop()의 wait()는 별도 데몬 스레드에서 실행 → UI 블록 0
- stderr는 DEVNULL (장시간 녹화 시 64KB 파이프 풀 방지)
  실패 진단용 마지막 stderr는 ffmpeg가 -report 안 쓰는 한 못 잡지만, return code로 분기
- MP4: gdigrab → 자동 감지된 인코더 (nvenc/qsv/amf → SW 폴백 h264_mf/libopenh264/mpeg4).
  시작 직후(2초 내) ffmpeg가 죽으면 인코더 초기화 실패로 보고
  다음 우선순위 인코더로 자동 재시도 (HW 오탐지·MF 불안정 환경 커버).
- GIF: 일단 MP4로 녹화 → stop 시 별도 QThread에서 2-pass palettegen으로 변환
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from .capture_storage import captures_dir
from .ffmpeg_runtime import available_encoders, encoder_args, find_ffmpeg
from .logging_setup import get_logger
from .win_job import assign_pid as _job_assign_pid


log = get_logger("recording")


GIF_FPS = 12
GIF_SCALE_WIDTH = 720
RECORDING_FPS = 30
TEMP_PREFIX = "rec_tmp_"


def _ascii_workspace_if_needed(target_dir: Path) -> Optional[Path]:
    """target_dir이 비-ASCII 경로면 ffmpeg가 못 다룸 → 영문 임시 작업 폴더 반환.
    ASCII 경로면 None (그대로 사용)."""
    if str(target_dir).isascii():
        return None
    ws = Path(tempfile.gettempdir()) / "ssakkimchi_recording"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@dataclass(frozen=True)
class RecordRegion:
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_qrect(cls, rect, dpr: float) -> "RecordRegion":
        w = max(2, int(round(rect.width() * dpr)))
        h = max(2, int(round(rect.height() * dpr)))
        w -= w % 2
        h -= h % 2
        return cls(
            x=int(round(rect.x() * dpr)),
            y=int(round(rect.y() * dpr)),
            width=max(2, w),
            height=max(2, h),
        )


def _creation_flags() -> int:
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _timestamped(kind: str, ext: str, base: Optional[Path] = None) -> Path:
    if base is None:
        base = captures_dir()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = base / f"{stamp}_{kind}.{ext}"
    counter = 1
    while path.exists():
        path = base / f"{stamp}_{kind}_{counter}.{ext}"
        counter += 1
    return path


def cleanup_stale_temp_files() -> int:
    """앱 시작 시 호출. 비정상 종료로 남은 rec_tmp_*.mp4 청소.
    captures_dir + 임시 workspace(%TEMP%/ssakkimchi_recording) 둘 다 본다."""
    removed = 0
    workspace = Path(tempfile.gettempdir()) / "ssakkimchi_recording"
    for base in (captures_dir(), workspace):
        if not base.exists():
            continue
        try:
            for path in base.glob(f"*{TEMP_PREFIX}*.mp4"):
                try:
                    path.unlink(missing_ok=True)
                    removed += 1
                except OSError:
                    pass
            for path in base.glob("*.palette.png"):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
        except OSError:
            pass
    return removed


class _GifConvertWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, ffmpeg: str, src_mp4: Path, dst_gif: Path) -> None:
        super().__init__()
        self._ffmpeg = ffmpeg
        self._src = src_mp4
        self._dst = dst_gif
        self._current_proc: Optional[subprocess.Popen] = None
        self._cancelled = False

    def _run_ffmpeg(self, args: list[str]) -> int:
        """Popen으로 띄워서 Job에 붙이고 wait. cancel 시 외부에서 kill 가능."""
        p = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_creation_flags(),
        )
        _job_assign_pid(p.pid)
        self._current_proc = p
        try:
            return p.wait()
        finally:
            self._current_proc = None

    def cancel(self) -> None:
        """외부에서 호출. 현재 실행 중인 ffmpeg subprocess 즉시 kill."""
        self._cancelled = True
        proc = self._current_proc
        if proc is not None:
            try:
                proc.kill()
            except OSError:
                pass

    def run(self) -> None:
        try:
            vf_palette = (
                f"fps={GIF_FPS},scale={GIF_SCALE_WIDTH}:-1:flags=lanczos,"
                "palettegen=stats_mode=full"
            )
            lavfi = (
                f"fps={GIF_FPS},scale={GIF_SCALE_WIDTH}:-1:flags=lanczos[x];"
                "[x][1:v]paletteuse=dither=floyd_steinberg"
            )
            palette_png = self._src.with_suffix(".palette.png")
            rc1 = self._run_ffmpeg(
                [self._ffmpeg, "-y", "-i", str(self._src), "-vf", vf_palette, str(palette_png)]
            )
            if self._cancelled:
                return
            if rc1 != 0 or not palette_png.exists():
                self.failed.emit("팔레트 생성 실패")
                return
            rc2 = self._run_ffmpeg(
                [
                    self._ffmpeg,
                    "-y",
                    "-i", str(self._src),
                    "-i", str(palette_png),
                    "-lavfi", lavfi,
                    str(self._dst),
                ]
            )
            try:
                palette_png.unlink(missing_ok=True)
            except OSError:
                pass
            try:
                self._src.unlink(missing_ok=True)
            except OSError:
                pass
            if self._cancelled:
                try:
                    self._dst.unlink(missing_ok=True)
                except OSError:
                    pass
                return
            if rc2 != 0 or not self._dst.exists():
                self.failed.emit("GIF 인코딩 실패")
                return
            self.done.emit(self._dst)
        except Exception as exc:
            if not self._cancelled:
                self.failed.emit(f"GIF 변환 예외: {exc}")


class RecordingController(QObject):
    """단일 녹화 세션 관리. 동시 녹화 금지.

    - started: ffmpeg가 떴을 때
    - progress(int): 1초마다 elapsed 초
    - finished(path, kind): 최종 파일 저장 완료. kind는 'mp4' 또는 'gif'
    - failed(message): 어느 단계에서든 실패
    """

    started = Signal()
    progress = Signal(int)
    finished = Signal(object, str)
    failed = Signal(str)
    _async_done = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._proc: Optional[subprocess.Popen] = None
        self._stopping = False
        self._mode = "mp4"
        self._region: Optional[RecordRegion] = None
        self._encoder = ""
        self._encoders: list[str] = []
        self._mp4_path: Optional[Path] = None
        self._gif_path: Optional[Path] = None
        self._final_dir: Optional[Path] = None
        self._gif_worker: Optional[_GifConvertWorker] = None
        self._elapsed = 0
        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)
        self._async_done.connect(self._on_async_stop_complete)

    def is_active(self) -> bool:
        return self._proc is not None or self._gif_worker is not None or self._stopping

    def start(self, region: RecordRegion, mode: str = "mp4") -> Optional[str]:
        if self.is_active():
            return "이미 녹화 중"
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            return "ffmpeg.exe를 찾지 못함\n(~/.ssakkimchi/bin/ffmpeg.exe 에 두거나 PATH 등록)"
        # 사용 가능한 인코더 전부를 후보 큐로 — 첫 후보가 시작 직후 죽으면
        # _on_tick이 다음 후보로 자동 재시도한다.
        self._encoders = list(available_encoders()) or ["mpeg4"]
        self._mode = mode
        self._region = region

        target_dir = captures_dir()
        workspace = _ascii_workspace_if_needed(target_dir)
        work_base = workspace if workspace is not None else target_dir
        self._final_dir = target_dir if workspace is not None else None
        if mode == "gif":
            self._mp4_path = _timestamped(f"{TEMP_PREFIX}gif", "mp4", base=work_base)
            self._gif_path = _timestamped("record", "gif", base=work_base)
        else:
            self._mp4_path = _timestamped("record", "mp4", base=work_base)
            self._gif_path = None

        err = self._launch(ffmpeg, self._encoders.pop(0))
        if err is not None:
            return err

        self._elapsed = 0
        self._tick.start()
        self.started.emit()
        return None

    def _launch(self, ffmpeg: str, encoder: str) -> Optional[str]:
        """지정 인코더로 ffmpeg 기동. 실패 메시지 또는 None."""
        region = self._region
        self._encoder = encoder
        cmd: list[str] = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-f", "gdigrab",
            "-framerate", str(RECORDING_FPS),
            "-offset_x", str(region.x),
            "-offset_y", str(region.y),
            "-video_size", f"{region.width}x{region.height}",
            "-draw_mouse", "1",
            "-i", "desktop",
            *encoder_args(encoder),
            "-r", str(RECORDING_FPS),
            "-g", str(RECORDING_FPS * 2),
            "-movflags", "+faststart",
            "-y",
            str(self._mp4_path),
        ]

        log.info("starting recording: mode=%s, region=%dx%d at (%d,%d), encoder=%s, output=%s",
                 self._mode, region.width, region.height, region.x, region.y,
                 encoder, self._mp4_path)
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=_creation_flags(),
            )
        except OSError as exc:
            self._proc = None
            log.exception("ffmpeg Popen failed")
            return f"ffmpeg 실행 실패: {exc}"

        _job_assign_pid(self._proc.pid)
        return None

    def _on_tick(self) -> None:
        if self._proc is None or self._stopping:
            return
        if self._proc.poll() is not None:
            rc = self._proc.returncode
            self._proc = None
            log.error("ffmpeg died unexpectedly (rc=%s, encoder=%s)", rc, self._encoder)
            # 시작 직후 사망 = 인코더 초기화 실패 가능성 → 남은 후보로 자동 재시도.
            # 중반 사망은 재시도해도 기존 내용이 사라지므로 그냥 실패 처리.
            if self._elapsed < 2 and self._encoders:
                ffmpeg = find_ffmpeg()
                if ffmpeg and self._mp4_path is not None:
                    try:
                        self._mp4_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    nxt = self._encoders.pop(0)
                    log.info("retrying with fallback encoder: %s", nxt)
                    if self._launch(ffmpeg, nxt) is None:
                        return
            self._tick.stop()
            self.failed.emit(f"녹화가 비정상 종료됨 (rc={rc}, 인코더={self._encoder})")
            return
        self._elapsed += 1
        self.progress.emit(self._elapsed)

    def stop(self) -> None:
        """비차단 graceful stop. wait()는 데몬 스레드로.

        UI 스레드는 즉시 반환. 완료되면 _async_done 시그널이
        UI 스레드로 큐잉돼 _on_async_stop_complete가 후처리.
        """
        if self._proc is None or self._stopping:
            return
        proc = self._proc
        self._stopping = True
        self._tick.stop()

        def _wait_then_signal() -> None:
            try:
                if proc.stdin is not None:
                    try:
                        proc.stdin.write(b"q")
                        proc.stdin.flush()
                    except (OSError, ValueError):
                        pass
                    try:
                        proc.stdin.close()
                    except OSError:
                        pass
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                ok = (proc.returncode == 0)
            except Exception:
                ok = False
            self._async_done.emit(ok)

        threading.Thread(target=_wait_then_signal, daemon=True).start()

    def _on_async_stop_complete(self, ok: bool) -> None:
        self._proc = None
        self._stopping = False
        self._after_ffmpeg_stop()

    def cancel(self) -> None:
        """동기 강제 종료. quit() 경로 전용."""
        if self._proc is not None:
            proc = self._proc
            self._proc = None
            self._stopping = False
            self._tick.stop()
            try:
                proc.kill()
            except OSError:
                pass
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            if self._mp4_path is not None:
                try:
                    self._mp4_path.unlink(missing_ok=True)
                except OSError:
                    pass
            self._mp4_path = None
            self._gif_path = None
        if self._gif_worker is not None:
            worker = self._gif_worker
            self._gif_worker = None
            try:
                worker.cancel()
                worker.wait(2000)
            except Exception:
                pass

    def _move_to_final(self, src: Path, ext: str) -> Path:
        """workspace에서 작업한 결과를 captures_dir(한글 경로)로 이동.
        ASCII 경로 사용 케이스면 그대로 반환."""
        if self._final_dir is None:
            return src
        dst = _timestamped("record", ext, base=self._final_dir)
        try:
            shutil.move(str(src), str(dst))
            return dst
        except OSError:
            return src

    def _after_ffmpeg_stop(self) -> None:
        if self._mp4_path is None or not self._mp4_path.exists():
            self.failed.emit("녹화 파일이 생성되지 않음")
            return

        if self._mode == "gif":
            ffmpeg = find_ffmpeg()
            if not ffmpeg or self._gif_path is None:
                self.failed.emit("GIF 변환 ffmpeg 없음")
                return
            worker = _GifConvertWorker(ffmpeg, self._mp4_path, self._gif_path)
            worker.done.connect(self._on_gif_done)
            worker.failed.connect(self._on_gif_failed)
            worker.finished.connect(worker.deleteLater)
            self._gif_worker = worker
            worker.start()
        else:
            path = self._move_to_final(self._mp4_path, "mp4")
            self._mp4_path = None
            self._final_dir = None
            self.finished.emit(path, "mp4")

    def _on_gif_done(self, path) -> None:
        self._gif_worker = None
        self._mp4_path = None
        self._gif_path = None
        final = self._move_to_final(Path(path), "gif")
        self._final_dir = None
        self.finished.emit(final, "gif")

    def _on_gif_failed(self, message: str) -> None:
        self._gif_worker = None
        if self._mp4_path is not None:
            try:
                self._mp4_path.unlink(missing_ok=True)
            except OSError:
                pass
        self._mp4_path = None
        self._gif_path = None
        self.failed.emit(message)
