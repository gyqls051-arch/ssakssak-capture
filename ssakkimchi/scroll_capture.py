from typing import List, Optional

from PySide6.QtCore import QObject, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtWidgets import QWidget

from PIL import Image, ImageChops
import numpy as np

import mss

from .toast import Toast

try:
    from pynput import keyboard as _pkb
except Exception:
    _pkb = None


CAPTURE_INTERVAL_MS = 180
MAX_FRAMES = 120
IDLE_FRAMES_TO_STOP = 12
MIN_DIFF_TO_KEEP = 1.2
MIN_OVERLAP_PX = 20
STITCH_STEP_COARSE = 2
STITCH_STEP_REFINE = 1
REFINE_WINDOW = 3
PIXEL_MATCH_TOLERANCE = 12
MIN_MATCH_RATIO = 0.92
EDGE_MARGIN_PX = 40


class ScrollCaptureController(QObject):
    finished = Signal(QImage)
    cancelled = Signal()
    progress = Signal(int)

    def __init__(self, region_rect: QRect, dpr: float, parent=None) -> None:
        super().__init__(parent)
        self._rect = region_rect
        self._dpr = dpr
        self._mss_region = {
            "left": int(round(region_rect.x() * dpr)),
            "top": int(round(region_rect.y() * dpr)),
            "width": int(round(region_rect.width() * dpr)),
            "height": int(round(region_rect.height() * dpr)),
        }
        self._frames: List[Image.Image] = []
        self._idle_count = 0
        self._timer = QTimer(self)
        self._timer.setInterval(CAPTURE_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._sct = None
        self._key_listener = None
        self._finalized = False

    def start(self) -> None:
        self._sct = mss.mss()
        new_frame = self._grab_frame()
        if new_frame is not None:
            self._frames.append(new_frame)
            self.progress.emit(len(self._frames))
        self._timer.start()
        self._start_key_listener()
        Toast.show_text("페이지를 스크롤하세요 · ESC 취소 · 멈추면 자동 종료", duration_ms=2400)

    def _start_key_listener(self) -> None:
        if _pkb is None:
            return
        try:
            self._key_listener = _pkb.Listener(on_press=self._on_key_press)
            self._key_listener.start()
        except Exception:
            self._key_listener = None

    def _stop_key_listener(self) -> None:
        if self._key_listener is not None:
            try:
                self._key_listener.stop()
            except Exception:
                pass
            self._key_listener = None

    def _on_key_press(self, key) -> None:
        try:
            if key == _pkb.Key.esc:
                QTimer.singleShot(0, self.cancel)
        except Exception:
            pass

    def _teardown(self) -> None:
        self._timer.stop()
        self._stop_key_listener()
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None

    def stop(self) -> None:
        if self._finalized:
            return
        self._finalized = True
        self._teardown()
        if len(self._frames) < 2:
            self.cancelled.emit()
            return
        stitched = self._stitch_frames(self._frames)
        if stitched is None:
            self.cancelled.emit()
            return
        qimg = self._pil_to_qimage(stitched)
        self.finished.emit(qimg)

    def cancel(self) -> None:
        if self._finalized:
            return
        self._finalized = True
        self._teardown()
        self.cancelled.emit()

    def _tick(self) -> None:
        if self._finalized:
            return
        if len(self._frames) >= MAX_FRAMES:
            self.stop()
            return
        new_frame = self._grab_frame()
        if new_frame is None:
            return
        if self._frames:
            last = self._frames[-1]
            diff_score = self._diff_score(last, new_frame)
            if diff_score < MIN_DIFF_TO_KEEP:
                self._idle_count += 1
                if self._idle_count >= IDLE_FRAMES_TO_STOP:
                    self.stop()
                return
            self._idle_count = 0
        self._frames.append(new_frame)
        self.progress.emit(len(self._frames))

    def _grab_frame(self) -> Optional[Image.Image]:
        if self._sct is None:
            return None
        try:
            shot = self._sct.grab(self._mss_region)
        except Exception:
            return None
        return Image.frombytes("RGB", (shot.width, shot.height), shot.rgb)

    @staticmethod
    def _diff_score(a: Image.Image, b: Image.Image) -> float:
        if a.size != b.size:
            return 999.0
        diff = ImageChops.difference(a, b)
        gray = diff.convert("L")
        hist = gray.getdata()
        total = sum(hist)
        return total / max(1, len(hist))

    @classmethod
    def _stitch_frames(cls, frames: List[Image.Image]) -> Optional[Image.Image]:
        if not frames:
            return None
        result = frames[0]
        for nxt in frames[1:]:
            overlap = cls._find_vertical_overlap(result, nxt)
            new_w = max(result.width, nxt.width)
            new_h = result.height + nxt.height - overlap
            canvas = Image.new("RGB", (new_w, new_h), (255, 255, 255))
            canvas.paste(result, (0, 0))
            canvas.paste(nxt, (0, result.height - overlap))
            result = canvas
        return result

    @staticmethod
    def _find_vertical_overlap(top: Image.Image, bottom: Image.Image) -> int:
        top_gray = np.asarray(top.convert("L"), dtype=np.int16)
        bot_gray = np.asarray(bottom.convert("L"), dtype=np.int16)
        width = min(top_gray.shape[1], bot_gray.shape[1])
        if width <= 0:
            return 0
        top_gray = top_gray[:, :width]
        bot_gray = bot_gray[:, :width]

        max_overlap = min(top_gray.shape[0], bot_gray.shape[0]) - EDGE_MARGIN_PX
        if max_overlap <= MIN_OVERLAP_PX:
            return 0

        def ratio_at(overlap: int) -> float:
            a = top_gray[-overlap:, :]
            b = bot_gray[:overlap, :]
            diff = np.abs(a - b)
            return float((diff <= PIXEL_MATCH_TOLERANCE).mean())

        candidate = 0
        for overlap in range(max_overlap, MIN_OVERLAP_PX - 1, -STITCH_STEP_COARSE):
            if ratio_at(overlap) >= MIN_MATCH_RATIO:
                candidate = overlap
                break
        if candidate == 0:
            return 0

        best_o = candidate
        best_r = ratio_at(candidate)
        lo = max(MIN_OVERLAP_PX, candidate - REFINE_WINDOW)
        hi = min(max_overlap, candidate + REFINE_WINDOW)
        for overlap in range(lo, hi + 1, STITCH_STEP_REFINE):
            r = ratio_at(overlap)
            if r > best_r:
                best_r = r
                best_o = overlap
        return best_o

    @staticmethod
    def _pil_to_qimage(img: Image.Image) -> QImage:
        rgba = img.convert("RGBA")
        data = rgba.tobytes("raw", "BGRA")
        qimg = QImage(data, rgba.width, rgba.height, rgba.width * 4, QImage.Format_ARGB32)
        return qimg.copy()
