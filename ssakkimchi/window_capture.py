import ctypes
from ctypes import wintypes
from typing import List, Optional, Set, Tuple

from PySide6.QtCore import QObject, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QWidget

from .capture_core import grab_qimage, region_dict, virtual_desktop_geometry
from .tokens import FONT_FAMILY


_user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
_dwmapi = ctypes.windll.dwmapi if hasattr(ctypes, "windll") else None
_GA_ROOT = 2
_DWMWA_EXTENDED_FRAME_BOUNDS = 9
_DWMWA_CLOAKED = 14
_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _visible_rect(hwnd) -> Optional[wintypes.RECT]:
    if _dwmapi is not None:
        rect = wintypes.RECT()
        try:
            hr = _dwmapi.DwmGetWindowAttribute(
                wintypes.HWND(hwnd),
                ctypes.c_uint(_DWMWA_EXTENDED_FRAME_BOUNDS),
                ctypes.byref(rect),
                ctypes.sizeof(rect),
            )
            if hr == 0 and rect.right > rect.left and rect.bottom > rect.top:
                return rect
        except Exception:
            pass
    if _user32 is None:
        return None
    rect = wintypes.RECT()
    if _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return rect
    return None


def _is_cloaked(hwnd) -> bool:
    if _dwmapi is None:
        return False
    val = ctypes.c_int(0)
    try:
        hr = _dwmapi.DwmGetWindowAttribute(
            wintypes.HWND(hwnd),
            ctypes.c_uint(_DWMWA_CLOAKED),
            ctypes.byref(val),
            ctypes.sizeof(val),
        )
        return hr == 0 and val.value != 0
    except Exception:
        return False


def _window_at_excluding(
    x: int, y: int, exclude: Set[int]
) -> Optional[Tuple[int, int, int, int]]:
    if _user32 is None:
        return None
    found: List[Optional[Tuple[int, int, int, int]]] = [None]

    def callback(hwnd, _lparam):
        try:
            if int(hwnd) in exclude:
                return True
            if not _user32.IsWindowVisible(hwnd):
                return True
            if _is_cloaked(hwnd):
                return True
            rect = _visible_rect(hwnd)
            if rect is None:
                return True
            if rect.right - rect.left <= 0 or rect.bottom - rect.top <= 0:
                return True
            if not (rect.left <= x < rect.right and rect.top <= y < rect.bottom):
                return True
            found[0] = (rect.left, rect.top, rect.right, rect.bottom)
            return False
        except Exception:
            return True

    try:
        _user32.EnumWindows(_WNDENUMPROC(callback), 0)
    except Exception:
        return None
    return found[0]


class _HighlightOverlay(QWidget):
    def __init__(self, session: "WindowCaptureSession") -> None:
        super().__init__()
        self._session = session
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self._target_rect = QRect()
        self._virtual_geom = virtual_desktop_geometry()
        self.setGeometry(self._virtual_geom)

    def begin(self) -> None:
        self._virtual_geom = virtual_desktop_geometry()
        self.setGeometry(self._virtual_geom)
        self._target_rect = QRect()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.OtherFocusReason)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.grabKeyboard()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.releaseKeyboard()

    def set_target(self, global_rect: Optional[Tuple[int, int, int, int]]) -> None:
        if global_rect is None:
            new_rect = QRect()
        else:
            l, t, r, b = global_rect
            new_rect = QRect(
                l - self._virtual_geom.x(),
                t - self._virtual_geom.y(),
                r - l,
                b - t,
            )
        if new_rect != self._target_rect:
            self._target_rect = new_rect
            self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self._session._cancel()
        else:
            super().keyPressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        p = event.globalPosition().toPoint()
        self._session._update_target_under(p.x(), p.y())

    def mousePressEvent(self, event) -> None:
        p = event.globalPosition().toPoint()
        if event.button() == Qt.LeftButton:
            self._session._handle_click(p.x(), p.y())
        elif event.button() == Qt.RightButton:
            self._session._cancel()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))
        if self._target_rect.width() > 0:
            inner = self._target_rect
            pen = QPen(QColor("#06B6D4"), 3)
            p.setPen(pen)
            p.setBrush(QColor(6, 182, 212, 36))
            p.drawRect(inner)


class _HintBanner(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.NoDropShadowWindowHint
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(380, 44)

    def begin(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        x = avail.x() + (avail.width() - self.width()) // 2
        y = avail.y() + 28
        self.move(x, y)
        self.show()
        self.raise_()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(self.rect(), 12, 12)
        font = QFont()
        font.setFamily(FONT_FAMILY.split(",")[0].strip().strip('"'))
        font.setPixelSize(13)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(26, 26, 26))
        p.drawText(self.rect(), Qt.AlignCenter, "캡처할 창에 마우스를 올리고 클릭  ·  ESC 취소")


class WindowCaptureSession(QObject):
    captured = Signal(QImage)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._highlight = _HighlightOverlay(self)
        self._banner = _HintBanner()
        self._active = False
        self._exclude_hwnds: Set[int] = set()

    def begin(self) -> None:
        if self._active:
            return
        self._active = True
        self._highlight.begin()
        self._banner.begin()
        self._exclude_hwnds = {
            int(self._highlight.winId()),
            int(self._banner.winId()),
        }

    def _update_target_under(self, x: int, y: int) -> None:
        if not self._active:
            return
        rect = _window_at_excluding(x, y, self._exclude_hwnds)
        self._highlight.set_target(rect)

    def _teardown(self) -> None:
        self._active = False
        self._highlight.hide()
        self._banner.hide()

    def _handle_click(self, x: int, y: int) -> None:
        if not self._active:
            return
        rect = _window_at_excluding(x, y, self._exclude_hwnds)
        self._teardown()
        if not rect:
            self.cancelled.emit()
            return
        left, top, right, bottom = rect
        w = right - left
        h = bottom - top
        if w < 5 or h < 5:
            self.cancelled.emit()
            return
        screen = QGuiApplication.screenAt(QPoint(x, y)) or QGuiApplication.primaryScreen()
        dpr = float(screen.devicePixelRatio() or 1.0) if screen else 1.0
        img = grab_qimage(region_dict(QRect(left, top, w, h), dpr))
        if img is None:
            self.cancelled.emit()
            return
        self.captured.emit(img)

    def _cancel(self) -> None:
        if not self._active:
            return
        self._teardown()
        self.cancelled.emit()
