from typing import Optional

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication, QImage

import mss


def virtual_desktop_geometry() -> QRect:
    screens = QGuiApplication.screens()
    if not screens:
        return QRect(0, 0, 800, 600)
    rect = QRect(screens[0].geometry())
    for s in screens[1:]:
        rect = rect.united(s.geometry())
    return rect


def region_dict(rect: QRect, dpr: float = 1.0) -> dict:
    return {
        "left": int(round(rect.x() * dpr)),
        "top": int(round(rect.y() * dpr)),
        "width": int(round(rect.width() * dpr)),
        "height": int(round(rect.height() * dpr)),
    }


def grab_qimage(region: dict, sct: Optional[object] = None) -> Optional[QImage]:
    own = sct is None
    if own:
        sct = mss.mss()
    try:
        try:
            shot = sct.grab(region)
        except Exception:
            return None
        return QImage(
            bytes(shot.bgra),
            shot.width,
            shot.height,
            shot.width * 4,
            QImage.Format_ARGB32,
        ).copy()
    finally:
        if own:
            try:
                sct.close()
            except Exception:
                pass


def grab_rect(rect: QRect, dpr: float = 1.0) -> Optional[QImage]:
    return grab_qimage(region_dict(rect, dpr))
