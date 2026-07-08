from typing import Optional, Tuple

from PySide6.QtCore import QRect
from PySide6.QtGui import QCursor, QGuiApplication, QImage, QScreen

import mss


def active_screen_info() -> Tuple[Optional[QScreen], QRect, float]:
    """마우스 커서가 있는 모니터의 (screen, 논리 geometry, dpr).

    오버레이는 이 화면 1개만 덮는다 — 가상 데스크톱 전체를 덮으면
    Qt6가 mouse event를 못 받는 이슈가 있음 (듀얼모니터 실측, CLAUDE.md)."""
    cursor = QCursor.pos()
    screen = QGuiApplication.screenAt(cursor) or QGuiApplication.primaryScreen()
    if screen is None:
        return None, virtual_desktop_geometry(), 1.0
    return screen, QRect(screen.geometry()), float(screen.devicePixelRatio() or 1.0)


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
