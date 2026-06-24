import atexit
import os
import subprocess
import sys
import warnings
from pathlib import Path
from typing import List

from PySide6.QtCore import QRect, QTimer, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from .capture_preview import CapturePreview
from .capture_storage import save_image
from .color_picker import ColorPickerOverlay
from .distance_overlay import DistanceOverlay
from .dock import Dock
from .full_capture import capture_screen_image
from .actions import default_hotkeys
from .hotkeys import HotkeyManager
from .hotkey_dialog import HotkeyDialog
from .palette_panel import PalettePanel
from .recording import RecordRegion, RecordingController, cleanup_stale_temp_files
from .recording_pill import RecordingPill
from .logging_setup import collect_diagnostics, get_logger, logs_dir
from .system_integration import (
    disable_snipping_route,
    enable_snipping_route,
    get_prtsc_routes_to_snipping,
    read_snipping_route_raw,
    restore_snipping_route,
)
from .version import version_string


log = get_logger("app")
from .region_capture import RegionCaptureOverlay
from .scroll_capture import ScrollCaptureController
from .storage import load_data, save_data
from .toast import Toast
from .tokens import PALETTE_MAX_HISTORY, PANEL_GAP
from .tray import TrayController
from .window_capture import WindowCaptureSession

try:
    from .ocr_engine import OcrWorker, is_available as ocr_available
except Exception:
    OcrWorker = None

    def ocr_available() -> bool:
        return False


class SsakKimchiApp:
    def __init__(self) -> None:
        self._data = load_data()

        # PrtSc 레지스트리 안전망: 앱 시작 시점의 '원래 값'을 보존해 두고,
        # 종료 시(정상 quit + 비정상 종료 모두) 이 값으로 복원한다.
        # disable_snipping_route()로 0을 써둔 채 크래시/강제종료되면
        # PrintScreenKeyForSnippingEnabled=0 이 영구히 남아 OS의 PrtSc가
        # 먹통이 되는데, 이를 막기 위한 장치.
        self._prtsc_original = read_snipping_route_raw()
        self._prtsc_taken_over = False
        self._prtsc_restored = False
        # 인터프리터 강제 종료/예외 경로에서도 한 번은 복원이 돌도록 atexit 등록.
        atexit.register(self._restore_prtsc_on_exit)

        self._dock = Dock()
        self._panel = PalettePanel()
        self._shared_region_overlay = RegionCaptureOverlay()
        self._color_overlay = ColorPickerOverlay()
        self._window_session = WindowCaptureSession()
        self._distance_overlay = DistanceOverlay()
        self._scroll_controller = None
        self._ocr_worker = None
        self._recorder = RecordingController()
        self._record_pill = RecordingPill()
        self._record_mode: str | None = None
        self._overlay_signals_bound = False
        self._preview = CapturePreview()
        self._hotkeys = HotkeyManager()

        self._tray = TrayController(
            on_toggle_dock=self.toggle_dock,
            on_region=self.start_region_capture,
            on_color=self.start_color_pick,
            on_quit=self.quit,
            on_record=self._toggle_record_video,
            on_gif=self._toggle_record_gif,
        )

        self._panel.set_palette(self._data.get("palette", []))
        self._color_active = False
        self._panel_visible = False

        self._dock.item_clicked.connect(self._on_dock_clicked)
        self._dock.tucked.connect(self._on_dock_tucked)
        self._dock.quit_requested.connect(self.quit)
        self._dock.hide_requested.connect(self._hide_dock)
        self._dock.hotkey_settings_requested.connect(self.open_hotkey_dialog)
        self._dock.prtsc_takeover_requested.connect(self.take_over_prtsc_key)
        self._dock.prtsc_release_requested.connect(self.release_prtsc_key)
        self._dock.about_requested.connect(self.show_about_dialog)

        self._panel.swatch_clicked.connect(self._on_palette_swatch_clicked)
        self._panel.swatch_removed.connect(self._on_palette_swatch_removed)
        self._panel.export_requested.connect(self._on_export)
        self._panel.collapse_requested.connect(self._collapse_panel)

        self._color_overlay.picked.connect(self._on_color_picked)
        self._color_overlay.cancelled.connect(self._on_color_cancelled)

        self._window_session.captured.connect(self._on_window_captured)
        self._window_session.cancelled.connect(self._on_capture_overlay_cancelled)

        self._distance_overlay.measured.connect(self._on_distance_measured)
        self._distance_overlay.cancelled.connect(self._on_capture_overlay_cancelled)

        self._record_region_rect: QRect | None = None
        self._recorder.started.connect(self._on_recording_started)
        self._recorder.progress.connect(self._record_pill.update_elapsed)
        self._recorder.finished.connect(self._on_recording_finished)
        self._recorder.failed.connect(self._on_recording_failed)
        self._record_pill.stop_clicked.connect(self._stop_recording)

        self._hotkeys.triggered.connect(self._on_hotkey, type=Qt.QueuedConnection)

    def start(self) -> None:
        cleanup_stale_temp_files()
        self._dock.show_anchored()
        self._hotkeys.start(self._current_hotkey_bindings())

    def take_over_prtsc_key(self) -> None:
        """도크 우클릭 메뉴에서 호출. PrtSc를 부분캡처로 바인딩하고 OS 라우팅 끔."""
        already = get_prtsc_routes_to_snipping() is False
        ok = disable_snipping_route()
        if not ok:
            Toast.show_text("Windows 설정 변경 실패", duration_ms=2400)
            return
        settings = self._data.setdefault("settings", {})
        hotkeys = settings.setdefault("hotkeys", dict(default_hotkeys()))
        hotkeys["region"] = "<print_screen>"
        save_data(self._data)
        self._hotkeys.restart(hotkeys)
        # 우리가 라우팅을 껐음을 표시 → 종료 시 안전망 복원 대상.
        self._prtsc_taken_over = True
        self._prtsc_restored = False
        suffix = "" if already else "\n(즉시 안 되면 Windows 한 번 재로그인)"
        Toast.show_text(f"PrtSc → 부분캡처{suffix}", duration_ms=3000)

    def show_about_dialog(self) -> None:
        """버전 + 진단 정보 + 로그 폴더 바로가기."""
        diag = collect_diagnostics()
        msg = QMessageBox()
        msg.setWindowTitle("정보 / 진단")
        msg.setIcon(QMessageBox.Information)
        msg.setText(version_string())
        msg.setInformativeText(diag)
        copy_btn = msg.addButton("진단 정보 복사", QMessageBox.ActionRole)
        open_logs_btn = msg.addButton("로그 폴더 열기", QMessageBox.ActionRole)
        msg.addButton("닫기", QMessageBox.AcceptRole)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked is copy_btn:
            QApplication.clipboard().setText(f"{version_string()}\n\n{diag}")
            Toast.show_text("진단 정보 복사됨", duration_ms=1600)
        elif clicked is open_logs_btn:
            try:
                os.startfile(str(logs_dir()))
            except Exception:
                log.exception("logs folder open failed")
                Toast.show_text("로그 폴더 열기 실패")

    def release_prtsc_key(self) -> None:
        """PrtSc를 Windows 기본(Snipping Tool)으로 되돌리고 region 핫키를 기본값으로 복원."""
        ok = enable_snipping_route()
        if not ok:
            Toast.show_text("Windows 설정 복원 실패", duration_ms=2400)
            return
        settings = self._data.setdefault("settings", {})
        hotkeys = settings.setdefault("hotkeys", dict(default_hotkeys()))
        defaults = default_hotkeys()
        if hotkeys.get("region") == "<print_screen>":
            hotkeys["region"] = defaults["region"]
        save_data(self._data)
        self._hotkeys.restart(hotkeys)
        # 사용자가 명시적으로 되돌렸으므로 안전망 복원은 더 할 필요 없음.
        self._prtsc_taken_over = False
        self._prtsc_restored = True
        Toast.show_text("PrtSc → Windows 기본으로 복원됨", duration_ms=2400)

    def _restore_prtsc_on_exit(self) -> None:
        """종료 안전망: 우리가 PrtSc 라우팅을 껐다면 시작 시점의 원래 값으로 복원.

        atexit과 quit() 양쪽에서 호출될 수 있으므로 중복 실행을 막는다.
        Qt가 이미 내려간 atexit 단계에서도 동작하도록 Toast 등 UI는 쓰지 않는다."""
        if self._prtsc_restored or not self._prtsc_taken_over:
            return
        self._prtsc_restored = True
        try:
            restore_snipping_route(self._prtsc_original)
        except Exception:
            # 종료 경로 — 실패해도 예외를 더 위로 던지지 않는다.
            pass

    def _current_hotkey_bindings(self) -> dict:
        settings = self._data.setdefault("settings", {})
        bindings = settings.get("hotkeys")
        defaults = default_hotkeys()
        if not isinstance(bindings, dict):
            bindings = dict(defaults)
            settings["hotkeys"] = bindings
        else:
            for k, v in defaults.items():
                bindings.setdefault(k, v)
            settings["hotkeys"] = bindings
        return bindings

    def _on_hotkey(self, action: str) -> None:
        if action in ("record", "gif") and self._recorder.is_active():
            self._stop_recording()
            return
        handler = {
            "region": self.start_region_capture,
            "full": self.start_full_capture,
            "window": self.start_window_capture,
            "scroll": self.start_scroll_capture,
            "record": self.start_record_video,
            "gif": self.start_record_gif,
            "color": self.start_color_pick,
            "distance": self.start_distance_measure,
            "ocr": self.start_ocr_capture,
        }.get(action)
        if handler:
            handler()

    def open_hotkey_dialog(self) -> None:
        current = dict(self._current_hotkey_bindings())
        dlg = HotkeyDialog(current)
        if dlg.exec() != HotkeyDialog.Accepted:
            return
        new_bindings = dlg.result_bindings()
        settings = self._data.setdefault("settings", {})
        settings["hotkeys"] = new_bindings
        save_data(self._data)
        self._hotkeys.restart(new_bindings)
        Toast.show_text("단축키 저장됨", duration_ms=1500)

    def _hide_dock(self) -> None:
        self._dock.hide()
        if self._panel.isVisible():
            self._panel.hide()
            self._panel_visible = False

    def bring_to_front(self) -> None:
        if self._dock.is_tucked():
            self._dock.peek()
        elif not self._dock.isVisible():
            self._dock.show_anchored()
        else:
            self._dock.raise_()

    def toggle_dock(self) -> None:
        if self._dock.isVisible():
            self._dock.hide()
            if self._panel.isVisible():
                self._panel.hide()
                self._panel_visible = False
        else:
            self._dock.show_anchored()

    def _on_dock_tucked(self) -> None:
        if self._panel.isVisible():
            self._panel.hide_animated()
            self._panel_visible = False
        if self._color_active:
            self._color_overlay.hide()

    def _on_dock_clicked(self, key: str) -> None:
        if key in ("record", "gif") and self._recorder.is_active():
            self._stop_recording()
            return
        if key == "region":
            self.start_region_capture()
        elif key == "full":
            self.start_full_capture()
        elif key == "window":
            self.start_window_capture()
        elif key == "scroll":
            self.start_scroll_capture()
        elif key == "record":
            self.start_record_video()
        elif key == "gif":
            self.start_record_gif()
        elif key == "distance":
            self.start_distance_measure()
        elif key == "ocr":
            self.start_ocr_capture()
        elif key == "color":
            if self._color_active:
                self._stop_color_pick()
            else:
                self.start_color_pick()
        elif key == "layout":
            self._toggle_dock_layout()
        else:
            Toast.show_text("준비 중인 기능")

    def _stop_color_pick(self) -> None:
        if self._color_overlay.isVisible():
            self._color_overlay.hide()
        self._color_active = False
        self._dock.set_active("color", False)
        self._dock.set_auto_tuck_paused(False)

    def _toggle_dock_layout(self) -> None:
        if self._panel.isVisible():
            self._panel.hide()
            self._panel_visible = False
        if self._color_active:
            self._stop_color_pick()
        self._dock.toggle_orientation()

    def _begin_shared_overlay(self, mode: str) -> None:
        """공유 RegionCaptureOverlay 시그널을 모드별 핸들러로 재연결 후 begin."""
        ov = self._shared_region_overlay
        if self._overlay_signals_bound:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                for sig in (ov.captured, ov.region_selected, ov.cancelled):
                    try:
                        sig.disconnect()
                    except (TypeError, RuntimeError):
                        pass
        self._overlay_signals_bound = True
        if mode == "region":
            ov.captured.connect(self._on_region_captured)
            ov.cancelled.connect(self._on_region_cancelled)
        elif mode == "scroll":
            ov.region_selected.connect(self._on_scroll_region_picked)
            ov.cancelled.connect(self._on_capture_overlay_cancelled)
        elif mode == "ocr":
            ov.captured.connect(self._on_ocr_region_picked)
            ov.cancelled.connect(self._on_capture_overlay_cancelled)
        elif mode == "record":
            ov.region_selected.connect(self._on_record_region_picked)
            ov.cancelled.connect(self._on_record_overlay_cancelled)
        elif mode == "gif":
            ov.region_selected.connect(self._on_gif_region_picked)
            ov.cancelled.connect(self._on_record_overlay_cancelled)
        ov.begin()

    def start_region_capture(self) -> None:
        if self._color_active:
            self._color_overlay.hide()
        self._hide_dock_for_capture()
        QTimer.singleShot(80, lambda: self._begin_shared_overlay("region"))

    def _on_region_captured(self, image: QImage) -> None:
        self._restore_after_capture()
        self._deliver_capture(image, kind="region", label="부분 캡처됨")

    def _on_region_cancelled(self) -> None:
        self._restore_after_capture()

    def _restore_after_capture(self) -> None:
        if self._recorder.is_active():
            return
        self._dock.show_anchored()
        if self._dock.is_pinned() and getattr(
            self, "_panel_was_visible_before_capture", False
        ):
            self._open_panel(animated=False)

    def _hide_dock_for_capture(self) -> None:
        self._panel_was_visible_before_capture = self._panel.isVisible()
        self._dock.hide()
        if self._panel.isVisible():
            self._panel.hide()

    def _on_capture_overlay_cancelled(self) -> None:
        self._restore_after_capture()

    def _deliver_capture(self, image: QImage, kind: str, label: str) -> None:
        QApplication.clipboard().setImage(image)
        path = save_image(image, kind=kind)
        self._preview.show_capture(image, path, label=label)

    def start_full_capture(self) -> None:
        if self._color_active:
            self._stop_color_pick()
        self._hide_dock_for_capture()
        screen = self._dock.screen()
        QTimer.singleShot(140, lambda s=screen: self._do_full_capture(s))

    def _do_full_capture(self, screen) -> None:
        try:
            img = capture_screen_image(screen)
        except Exception:
            self._restore_after_capture()
            Toast.show_text("전체 캡처 실패")
            return
        self._restore_after_capture()
        self._deliver_capture(img, kind="full", label="전체 화면 캡처됨")

    def start_window_capture(self) -> None:
        if self._color_active:
            self._stop_color_pick()
        self._hide_dock_for_capture()
        QTimer.singleShot(80, self._window_session.begin)

    def _on_window_captured(self, image: QImage) -> None:
        self._restore_after_capture()
        self._deliver_capture(image, kind="window", label="창 캡처됨")

    def start_distance_measure(self) -> None:
        if self._color_active:
            self._stop_color_pick()
        self._hide_dock_for_capture()
        QTimer.singleShot(80, self._distance_overlay.begin)

    def _on_distance_measured(self, dx: int, dy: int, dist: float) -> None:
        text = f"{int(round(dist))} px ({abs(dx)} × {abs(dy)})"
        QApplication.clipboard().setText(text)
        self._restore_after_capture()
        Toast.show_text(f"{text}  ·  클립보드 복사됨")

    def start_scroll_capture(self) -> None:
        if self._color_active:
            self._stop_color_pick()
        self._hide_dock_for_capture()
        Toast.show_text("스크롤 캡처 영역을 드래그로 선택하세요", duration_ms=2200)
        QTimer.singleShot(180, lambda: self._begin_shared_overlay("scroll"))

    def _on_scroll_region_picked(self, rect: QRect, dpr: float) -> None:
        if self._scroll_controller is not None:
            try:
                self._scroll_controller.cancel()
            except Exception:
                pass
        self._scroll_controller = ScrollCaptureController(rect, dpr)
        self._scroll_controller.finished.connect(self._on_scroll_finished)
        self._scroll_controller.cancelled.connect(self._on_scroll_cancelled)
        self._scroll_controller.progress.connect(self._on_scroll_progress)
        self._scroll_controller.start()

    def _on_scroll_progress(self, count: int) -> None:
        if count > 1 and count % 4 == 0:
            Toast.show_text(f"📸 스크롤 캡처 · {count}장", duration_ms=900)

    def _on_scroll_finished(self, image: QImage) -> None:
        self._scroll_controller = None
        self._restore_after_capture()
        self._deliver_capture(image, kind="scroll", label="스크롤 캡처됨")

    def _on_scroll_cancelled(self) -> None:
        self._scroll_controller = None
        self._restore_after_capture()
        Toast.show_text("스크롤 캡처 취소됨")

    def start_ocr_capture(self) -> None:
        if not ocr_available():
            Toast.show_text("이 시스템에서 Windows OCR을 사용할 수 없습니다")
            return
        if self._color_active:
            self._stop_color_pick()
        self._hide_dock_for_capture()
        Toast.show_text("OCR 할 영역을 드래그로 선택", duration_ms=2000)
        QTimer.singleShot(180, lambda: self._begin_shared_overlay("ocr"))

    def _on_ocr_region_picked(self, image: QImage) -> None:
        if OcrWorker is None:
            self._restore_after_capture()
            Toast.show_text("OCR 모듈 없음")
            return
        # 이전 OCR 워커가 아직 돌고 있으면 안전하게 떼어낸다.
        # 단순 참조 덮어쓰기는 QThread가 GC되며 "Destroyed while thread is
        # still running" 크래시를 유발하므로, 시그널을 끊고 deleteLater로
        # 수명 관리를 Qt에 넘긴 뒤 새 워커로 교체한다.
        self._detach_ocr_worker()
        worker = OcrWorker(image)
        self._ocr_worker = worker
        worker.finished_ok.connect(self._on_ocr_done)
        worker.failed.connect(self._on_ocr_failed)
        # 스레드가 끝나면 Qt가 객체를 정리하도록 한다(참조가 None이 돼도 안전).
        worker.finished.connect(worker.deleteLater)
        Toast.show_text("OCR 분석 중...", duration_ms=1200)
        worker.start()
        self._restore_after_capture()

    def _detach_ocr_worker(self) -> None:
        """진행 중인 OCR 워커를 안전하게 분리한다.

        시그널을 끊어 콜백이 더는 안 오게 하고, 인터럽션을 요청한 뒤
        잠깐 wait 한다. 끝나지 않아도 deleteLater로 수명을 Qt에 위임해
        QThread 파괴 크래시를 막는다."""
        worker = self._ocr_worker
        self._ocr_worker = None
        if worker is None:
            return
        try:
            worker.finished_ok.disconnect()
        except (RuntimeError, TypeError):
            pass
        try:
            worker.failed.disconnect()
        except (RuntimeError, TypeError):
            pass
        try:
            if worker.isRunning():
                worker.requestInterruption()
                worker.quit()
                worker.wait(2000)
        except RuntimeError:
            # 이미 파괴된 경우 등 — 무시
            return
        try:
            worker.finished.connect(worker.deleteLater)
            worker.deleteLater()
        except RuntimeError:
            pass

    def _on_ocr_done(self, text: str) -> None:
        self._ocr_worker = None
        if not text:
            Toast.show_text("OCR 결과 없음")
            return
        QApplication.clipboard().setText(text)
        Toast.show_text(f"OCR 완료 · {len(text)}자 복사됨")

    def _on_ocr_failed(self, message: str) -> None:
        self._ocr_worker = None
        Toast.show_text(message or "OCR 실패")

    def start_record_video(self) -> None:
        self._begin_record_flow(mode="mp4", overlay_mode="record",
                                hint="녹화할 영역을 드래그로 선택")

    def start_record_gif(self) -> None:
        self._begin_record_flow(mode="gif", overlay_mode="gif",
                                hint="GIF로 녹화할 영역을 드래그로 선택")

    def _toggle_record_video(self) -> None:
        if self._recorder.is_active():
            self._stop_recording()
        else:
            self.start_record_video()

    def _toggle_record_gif(self) -> None:
        if self._recorder.is_active():
            self._stop_recording()
        else:
            self.start_record_gif()

    def _begin_record_flow(self, mode: str, overlay_mode: str, hint: str) -> None:
        if self._recorder.is_active():
            Toast.show_text("이미 녹화 중입니다 · 정지 후 다시 시도")
            return
        if self._color_active:
            self._stop_color_pick()
        self._record_mode = mode
        self._hide_dock_for_capture()
        Toast.show_text(hint, duration_ms=1800)
        QTimer.singleShot(160, lambda om=overlay_mode: self._begin_shared_overlay(om))

    def _on_record_region_picked(self, rect: QRect, dpr: float) -> None:
        self._start_recording_with_rect(rect, dpr, mode="mp4")

    def _on_gif_region_picked(self, rect: QRect, dpr: float) -> None:
        self._start_recording_with_rect(rect, dpr, mode="gif")

    def _start_recording_with_rect(self, rect: QRect, dpr: float, mode: str) -> None:
        self._record_region_rect = QRect(rect)
        region = RecordRegion.from_qrect(rect, dpr)
        err = self._recorder.start(region, mode=mode)
        if err is not None:
            self._record_mode = None
            self._record_region_rect = None
            self._dock.reset_active()
            self._restore_after_capture()
            Toast.show_text(err, duration_ms=3200)

    def _on_record_overlay_cancelled(self) -> None:
        self._record_mode = None
        self._dock.reset_active()
        self._restore_after_capture()

    def _on_recording_started(self) -> None:
        if self._record_mode:
            self._dock.set_active("record", self._record_mode == "mp4")
            self._dock.set_active("gif", self._record_mode == "gif")
            self._record_pill.show_for(self._record_mode, self._record_region_rect)

    def _stop_recording(self) -> None:
        if self._recorder.is_active():
            Toast.show_text("녹화 정지 · 인코딩 중…", duration_ms=1400)
        self._recorder.stop()

    def _on_recording_finished(self, path, kind: str) -> None:
        self._record_mode = None
        self._record_region_rect = None
        self._dock.reset_active()
        self._record_pill.hide_pill()
        self._restore_after_capture()
        label = "GIF 저장됨" if kind == "gif" else "녹화 저장됨"
        Toast.show_text(f"{label}\n{Path(path).name}", duration_ms=2600)
        self._reveal_in_explorer(Path(path))

    def _reveal_in_explorer(self, file_path: Path) -> None:
        if sys.platform != "win32" or not file_path.exists():
            return
        try:
            subprocess.Popen(
                ["explorer", f"/select,{file_path}"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            try:
                os.startfile(str(file_path.parent))
            except Exception:
                pass

    def _on_recording_failed(self, message: str) -> None:
        self._record_mode = None
        self._record_region_rect = None
        self._dock.reset_active()
        self._record_pill.hide_pill()
        self._restore_after_capture()
        Toast.show_text(message or "녹화 실패", duration_ms=3200)

    def start_color_pick(self) -> None:
        if self._dock.is_tucked():
            self._dock.peek()
        self._dock.set_auto_tuck_paused(True)
        if not self._panel.isVisible():
            self._open_panel(animated=True)
        self._color_active = True
        self._dock.set_active("color", True)
        QTimer.singleShot(50, self._color_overlay.begin)

    def _on_color_picked(self, hex_value: str) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(hex_value)
        self._record_color(hex_value)
        Toast.show_text(f"{hex_value} · copied")

    def _on_color_cancelled(self) -> None:
        self._color_active = False
        self._dock.set_active("color", False)
        self._dock.set_auto_tuck_paused(False)

    def _record_color(self, hex_value: str) -> None:
        hex_value = hex_value.upper()
        palette: List[str] = list(self._data.get("palette", []))
        palette = [c for c in palette if c.upper() != hex_value]
        palette.insert(0, hex_value)
        palette = palette[:PALETTE_MAX_HISTORY]
        self._data["palette"] = palette
        save_data(self._data)
        self._panel.set_palette(palette)

    def _on_palette_swatch_clicked(self, hex_value: str) -> None:
        QApplication.clipboard().setText(hex_value)

    def _on_palette_swatch_removed(self, hex_value: str) -> None:
        hex_upper = hex_value.upper()
        palette = [c for c in self._data.get("palette", []) if c.upper() != hex_upper]
        self._data["palette"] = palette
        save_data(self._data)
        self._panel.set_palette(palette)
        Toast.show_text("삭제됨")

    def _open_panel(self, animated: bool) -> None:
        dock_geom = self._dock.geometry()
        edge = self._dock.edge()
        panel_w = self._panel.width()

        if edge in ("left", "right"):
            panel_h = dock_geom.height()
            panel_y = dock_geom.y()
            if edge == "right":
                panel_x = dock_geom.x() - panel_w - PANEL_GAP
            else:
                panel_x = dock_geom.x() + dock_geom.width() + PANEL_GAP
        else:
            panel_h = 280
            panel_x = dock_geom.x() + (dock_geom.width() - panel_w) // 2
            if edge == "top":
                panel_y = dock_geom.y() + dock_geom.height() + PANEL_GAP
            else:
                panel_y = dock_geom.y() - panel_h - PANEL_GAP

        target = QRect(panel_x, panel_y, panel_w, panel_h)
        self._panel.setFixedHeight(panel_h)
        self._panel.show_at(target, animated=animated, from_side=edge)
        self._panel_visible = True

    def _collapse_panel(self) -> None:
        self._panel.hide_animated()
        self._panel_visible = False
        if self._color_active:
            self._stop_color_pick()

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            None,
            "Export Palette",
            "ssakkimchi-palette.txt",
            "Text (*.txt)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for hex_value in self._data.get("palette", []):
                    f.write(f"{hex_value}\n")
            Toast.show_text("팔레트 내보냄")
        except OSError:
            Toast.show_text("내보내기 실패")

    def quit(self) -> None:
        try:
            self._restore_prtsc_on_exit()
        except Exception:
            pass
        try:
            self._detach_ocr_worker()
        except Exception:
            pass
        try:
            self._recorder.cancel()
        except Exception:
            pass
        try:
            self._record_pill.hide_pill()
        except Exception:
            pass
        try:
            self._dock.hide()
        except Exception:
            pass
        try:
            self._show_exit_ad()
        except Exception:
            log.exception("exit ad failed")
        self._hotkeys.stop()
        self._tray.hide()
        QApplication.quit()

    def _show_exit_ad(self) -> None:
        from .exit_ad import ExitAdDialog, BANNER_ENABLED
        if not BANNER_ENABLED:
            return
        dlg = ExitAdDialog()
        dlg.exec()
