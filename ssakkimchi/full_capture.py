from typing import Optional

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication, QImage, QScreen

from .capture_core import grab_qimage, grab_rect
from .coords import screen_physical_geometry


def capture_screen_image(screen: QScreen) -> Optional[QImage]:
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    if screen is None:
        return None
    phys = screen_physical_geometry(screen)
    return grab_qimage(
        {
            "left": phys.x(),
            "top": phys.y(),
            "width": phys.width(),
            "height": phys.height(),
        }
    )


def capture_rect_image(rect: QRect, dpr: float = 1.0) -> Optional[QImage]:
    return grab_rect(rect, dpr)
