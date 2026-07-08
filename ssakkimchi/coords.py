"""물리(px) ↔ 논리(Qt) 좌표 변환 헬퍼.

전제: Qt6 앱은 Windows에서 Per-Monitor DPI Aware v2로 실행된다. 따라서
- Win32 API(GetWindowRect, DWM EXTENDED_FRAME_BOUNDS, GetCursorPos,
  EnumDisplayMonitors)는 **물리 픽셀**을 반환하고,
- Qt(QScreen.geometry(), event.globalPosition())는 **논리 픽셀**이며,
- mss는 **물리 픽셀**을 받는다.

"논리 × dpr = 물리" 근사는 해당 모니터의 물리 원점이 논리 원점 × dpr일 때만
성립한다(단일 모니터/주 모니터는 참, 배율이 다른 보조 모니터에선 거짓).

QScreen ↔ Win32 모니터 매칭:
Qt6의 QScreen.name()은 GDI 장치명(\\\\.\\DISPLAY1)이 아니라 모델명
("BenQ GW2480 (1)")을 돌려주므로 이름 매칭은 불가(2026-07 실측).
대신 **원점 정렬 순서 + 크기 검증**으로 짝을 맞춘다: Windows 배치는
물리/논리 양쪽에서 상대 순서가 보존되므로 (x, y) 정렬 순으로 zip하고,
각 쌍이 "논리 크기 × dpr == 물리 크기"를 만족하는지 확인한다.
검증 실패/개수 불일치/비-Windows에서는 논리 × dpr 폴백 — 기존 동작과 동일.
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from typing import List, Optional, Tuple

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QCursor, QGuiApplication, QScreen


# 모니터 열거는 캡처 시점마다 최신이면 충분 — 짧은 TTL 캐시로
# 디스플레이 구성 변경(WM_DISPLAYCHANGE)을 따로 구독하지 않아도 된다.
_CACHE_TTL_S = 1.0
_pairs_cache: Optional[Tuple[float, List[Tuple[QScreen, QRect]]]] = None


class _MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", ctypes.c_wchar * 32),
    ]


def _enum_monitors() -> List[QRect]:
    """Win32 모니터들의 물리 QRect 목록. 실패/비-Windows면 빈 리스트."""
    if sys.platform != "win32":
        return []
    out: List[QRect] = []
    try:
        user32 = ctypes.windll.user32
        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HANDLE,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM,
        )

        def _cb(hmon, _hdc, _lprect, _lparam):
            info = _MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(info)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
                r = info.rcMonitor
                out.append(QRect(r.left, r.top, r.right - r.left, r.bottom - r.top))
            return True

        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_cb), 0)
    except Exception:
        return []
    return out


def _build_pairs() -> List[Tuple[QScreen, QRect]]:
    """QScreen ↔ 물리 rect 짝 맞추기. 신뢰할 수 없으면 빈 리스트(→폴백)."""
    monitors = _enum_monitors()
    screens = list(QGuiApplication.screens())
    if not monitors or len(monitors) != len(screens):
        return []
    monitors_sorted = sorted(monitors, key=lambda r: (r.x(), r.y()))
    screens_sorted = sorted(
        screens, key=lambda s: (s.geometry().x(), s.geometry().y())
    )
    pairs: List[Tuple[QScreen, QRect]] = []
    for screen, phys in zip(screens_sorted, monitors_sorted):
        dpr = float(screen.devicePixelRatio() or 1.0)
        g = screen.geometry()
        # 크기 검증 — 어긋나면 짝 맞춤 전체를 불신하고 폴백
        if (
            abs(g.width() * dpr - phys.width()) > 2
            or abs(g.height() * dpr - phys.height()) > 2
        ):
            return []
        pairs.append((screen, QRect(phys)))
    return pairs


def _screen_pairs() -> List[Tuple[QScreen, QRect]]:
    global _pairs_cache
    now = time.monotonic()
    if _pairs_cache is not None and now - _pairs_cache[0] < _CACHE_TTL_S:
        return _pairs_cache[1]
    pairs = _build_pairs()
    _pairs_cache = (now, pairs)
    return pairs


def _physical_rect_for(screen: QScreen) -> Optional[QRect]:
    for s, phys in _screen_pairs():
        if s is screen:
            return QRect(phys)
    return None


def screen_physical_geometry(screen: QScreen) -> QRect:
    """해당 스크린의 물리 픽셀 rect (mss/gdigrab에 그대로 사용 가능)."""
    phys = _physical_rect_for(screen)
    if phys is not None:
        return phys
    geom = screen.geometry()
    dpr = float(screen.devicePixelRatio() or 1.0)
    return QRect(
        int(round(geom.x() * dpr)),
        int(round(geom.y() * dpr)),
        int(round(geom.width() * dpr)),
        int(round(geom.height() * dpr)),
    )


def logical_to_physical_point(point: QPoint, screen: Optional[QScreen] = None) -> QPoint:
    if screen is None:
        screen = QGuiApplication.screenAt(point) or QGuiApplication.primaryScreen()
    if screen is None:
        return QPoint(point)
    dpr = float(screen.devicePixelRatio() or 1.0)
    origin_l = screen.geometry().topLeft()
    phys = _physical_rect_for(screen)
    if phys is not None:
        origin_p = phys.topLeft()
    else:
        origin_p = QPoint(int(round(origin_l.x() * dpr)), int(round(origin_l.y() * dpr)))
    return QPoint(
        origin_p.x() + int(round((point.x() - origin_l.x()) * dpr)),
        origin_p.y() + int(round((point.y() - origin_l.y()) * dpr)),
    )


def logical_to_physical_rect(rect: QRect, screen: Optional[QScreen] = None) -> QRect:
    if screen is None:
        screen = QGuiApplication.screenAt(rect.center()) or QGuiApplication.primaryScreen()
    top_left = logical_to_physical_point(rect.topLeft(), screen)
    dpr = float(screen.devicePixelRatio() or 1.0) if screen is not None else 1.0
    return QRect(
        top_left.x(),
        top_left.y(),
        max(1, int(round(rect.width() * dpr))),
        max(1, int(round(rect.height() * dpr))),
    )


def physical_to_logical_point(point: QPoint) -> QPoint:
    """물리 → 논리. 포함하는 모니터를 찾아 변환, 못 찾으면 주 모니터 dpr 근사."""
    for screen, phys in _screen_pairs():
        if phys.contains(point):
            dpr = float(screen.devicePixelRatio() or 1.0)
            origin_l = screen.geometry().topLeft()
            return QPoint(
                origin_l.x() + int(round((point.x() - phys.x()) / dpr)),
                origin_l.y() + int(round((point.y() - phys.y()) / dpr)),
            )
    screen = QGuiApplication.primaryScreen()
    dpr = float(screen.devicePixelRatio() or 1.0) if screen is not None else 1.0
    return QPoint(int(round(point.x() / dpr)), int(round(point.y() / dpr)))


def physical_to_logical_rect(rect: QRect) -> QRect:
    """물리 rect → 논리 rect. 중심점이 속한 모니터의 dpr 기준."""
    center = rect.center()
    for screen, phys in _screen_pairs():
        if phys.contains(center):
            dpr = float(screen.devicePixelRatio() or 1.0)
            origin_l = screen.geometry().topLeft()
            return QRect(
                origin_l.x() + int(round((rect.x() - phys.x()) / dpr)),
                origin_l.y() + int(round((rect.y() - phys.y()) / dpr)),
                max(1, int(round(rect.width() / dpr))),
                max(1, int(round(rect.height() / dpr))),
            )
    screen = QGuiApplication.primaryScreen()
    dpr = float(screen.devicePixelRatio() or 1.0) if screen is not None else 1.0
    return QRect(
        int(round(rect.x() / dpr)),
        int(round(rect.y() / dpr)),
        max(1, int(round(rect.width() / dpr))),
        max(1, int(round(rect.height() / dpr))),
    )


def cursor_physical_pos() -> QPoint:
    """커서의 물리 픽셀 좌표. Win32 GetCursorPos(PMv2에서 물리) 우선."""
    if sys.platform == "win32":
        try:
            pt = wintypes.POINT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                return QPoint(pt.x, pt.y)
        except Exception:
            pass
    return logical_to_physical_point(QCursor.pos())
