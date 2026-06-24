from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication, QImage, QScreen

from .capture_core import grab_rect


def capture_screen_image(screen: QScreen) -> QImage:
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    geom = screen.geometry()
    dpr = float(screen.devicePixelRatio() or 1.0)
    return grab_rect(geom, dpr)


def capture_rect_image(rect: QRect, dpr: float = 1.0) -> QImage:
    return grab_rect(rect, dpr)
