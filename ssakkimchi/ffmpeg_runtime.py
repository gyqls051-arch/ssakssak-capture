"""ffmpeg.exe 위치 탐색 + 사용 가능한 HW 인코더 자동 선택.

탐색 순서:
1. PyInstaller 번들 (sys._MEIPASS/ffmpeg/ffmpeg.exe)
2. 프로젝트 로컬 bin (ssakkimchi/bin/ffmpeg.exe)
3. ~/.ssakkimchi/bin/ffmpeg.exe (사용자가 직접 두는 곳)
4. PATH (shutil.which)

인코더 선호 순위: nvenc > qsv > amf > mpeg4 (SW 폴백)
- 본 앱은 LGPL ffmpeg 빌드를 번들하므로 GPL인 libx264/libx265는 사용하지 않는다.
- mpeg4는 FFmpeg 내장 인코더라 LGPL 빌드에도 포함되며,
  HW 인코더 미지원 환경에서 호환성을 우선해 fallback으로 선택.
한 번만 감지하고 캐시.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .paths import user_root
from .win_job import assign_pid as _job_assign_pid


_CACHED_FFMPEG: Optional[str] = None
_CACHED_ENCODER: Optional[str] = None

_ENCODER_PREFERENCE = ("h264_nvenc", "h264_qsv", "h264_amf", "mpeg4")


def find_ffmpeg() -> Optional[str]:
    """ffmpeg.exe 절대 경로를 돌려준다. 못 찾으면 None.

    캐시된 경로가 실제로 존재하지 않으면 (사용자가 ffmpeg 삭제/이동) 재탐색.
    """
    global _CACHED_FFMPEG, _CACHED_ENCODER
    if _CACHED_FFMPEG:
        if Path(_CACHED_FFMPEG).is_file():
            return _CACHED_FFMPEG
        _CACHED_FFMPEG = None
        _CACHED_ENCODER = None
    elif _CACHED_FFMPEG == "":
        return None

    candidates: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "ffmpeg" / "ffmpeg.exe")
        candidates.append(Path(meipass) / "ffmpeg.exe")

    module_dir = Path(__file__).resolve().parent
    candidates.append(module_dir / "bin" / "ffmpeg.exe")
    candidates.append(module_dir.parent / "bin" / "ffmpeg.exe")

    candidates.append(user_root() / "bin" / "ffmpeg.exe")

    for c in candidates:
        if c.is_file():
            _CACHED_FFMPEG = str(c)
            return _CACHED_FFMPEG

    on_path = shutil.which("ffmpeg")
    if on_path:
        _CACHED_FFMPEG = on_path
        return _CACHED_FFMPEG

    _CACHED_FFMPEG = ""
    return None


def _list_encoders(ffmpeg_path: str) -> str:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        p = subprocess.Popen(
            [ffmpeg_path, "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )
        _job_assign_pid(p.pid)
        try:
            out, err = p.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()
            return ""
        return (out or "") + (err or "")
    except OSError:
        return ""


def detect_best_encoder() -> Optional[str]:
    """mpeg4 폴백 포함해서 가장 좋은 인코더 이름을 반환. 없으면 None."""
    global _CACHED_ENCODER
    if _CACHED_ENCODER is not None:
        return _CACHED_ENCODER or None

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        _CACHED_ENCODER = ""
        return None

    listing = _list_encoders(ffmpeg)
    if not listing:
        _CACHED_ENCODER = ""
        return None

    for enc in _ENCODER_PREFERENCE:
        if enc in listing:
            _CACHED_ENCODER = enc
            return enc

    _CACHED_ENCODER = ""
    return None


def encoder_args(encoder: str) -> list[str]:
    """선택된 인코더에 맞는 ffmpeg 인자 묶음."""
    if encoder == "h264_nvenc":
        return [
            "-c:v", "h264_nvenc",
            "-preset", "p5",
            "-tune", "hq",
            "-rc", "vbr",
            "-cq", "23",
            "-b:v", "0",
            "-pix_fmt", "yuv420p",
        ]
    if encoder == "h264_qsv":
        return [
            "-c:v", "h264_qsv",
            "-preset", "medium",
            "-global_quality", "23",
        ]
    if encoder == "h264_amf":
        return [
            "-c:v", "h264_amf",
            "-quality", "balanced",
            "-rc", "cqp",
            "-qp_i", "23", "-qp_p", "23",
            "-pix_fmt", "yuv420p",
        ]
    # SW fallback: mpeg4 (FFmpeg 내장, LGPL 빌드 포함)
    # libx264 대비 화질·압축률은 약하지만 HW 인코더 미지원 환경의 호환성 확보가 우선.
    # qscale 1(최고)~31(최저) 중 4 = 일반적 고화질.
    return [
        "-c:v", "mpeg4",
        "-vtag", "xvid",      # MP4 컨테이너 호환성
        "-qscale:v", "4",
        "-pix_fmt", "yuv420p",
    ]


def reset_cache() -> None:
    """테스트나 ffmpeg을 새로 떨군 직후 재탐색하고 싶을 때."""
    global _CACHED_FFMPEG, _CACHED_ENCODER
    _CACHED_FFMPEG = None
    _CACHED_ENCODER = None
