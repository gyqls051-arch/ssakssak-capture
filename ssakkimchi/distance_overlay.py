import math
from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .capture_core import virtual_desktop_geometry
from .tokens import FONT_FAMILY


class DistanceOverlay(QWidget):
    measured = Signal(int, int, float)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self._virtual_geom = virtual_desktop_geometry()
        self.setGeometry(self._virtual_geom)
        self._start: Optional[QPoint] = None
        self._cursor = QPoint(0, 0)

    def begin(self) -> None:
        self._start = None
        self._virtual_geom = virtual_desktop_geometry()
        self.setGeometry(self._virtual_geom)
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

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self._start is None:
                self._start = event.position().toPoint()
                self._cursor = self._start
                self.update()
            else:
                end = event.position().toPoint()
                dx = end.x() - self._start.x()
                dy = end.y() - self._start.y()
                dist = math.sqrt(dx * dx + dy * dy)
                self.hide()
                self.measured.emit(int(dx), int(dy), dist)
        elif event.button() == Qt.RightButton:
            self.hide()
            self.cancelled.emit()

    def mouseMoveEvent(self, event) -> None:
        self._cursor = event.position().toPoint()
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(0, 0, 0, 70))

        if self._start is None:
            self._draw_hint(p, "두 점을 클릭해서 거리 측정  ·  ESC 취소")
            return

        start = self._start
        end = self._cursor
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        dist = math.sqrt(dx * dx + dy * dy)

        pen = QPen(QColor("#10B981"), 1.5)
        p.setPen(pen)
        p.drawLine(start, end)

        self._draw_marker(p, start)
        self._draw_marker(p, end)

        self._draw_distance_label(p, end, abs(dx), abs(dy), dist)

    def _draw_marker(self, p: QPainter, pt: QPoint) -> None:
        p.setBrush(QColor("#10B981"))
        p.setPen(QPen(QColor(255, 255, 255), 1.5))
        p.drawEllipse(pt, 5, 5)

    def _draw_distance_label(self, p: QPainter, near: QPoint, dx: int, dy: int, dist: float) -> None:
        text = f"{int(round(dist))} px   ·   {dx} × {dy}"
        font = QFont()
        font.setFamily(FONT_FAMILY.split(",")[0].strip().strip('"'))
        font.setPixelSize(12)
        font.setBold(True)
        p.setFont(font)
        metrics = p.fontMetrics()
        pad_x, pad_y = 10, 6
        w = metrics.horizontalAdvance(text) + pad_x * 2
        h = metrics.height() + pad_y * 2

        bx = near.x() + 14
        by = near.y() + 14
        if bx + w + 4 > self.width():
            bx = near.x() - w - 14
        if by + h + 4 > self.height():
            by = near.y() - h - 14

        bg = QRect(bx, by, w, h)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#10B981"))
        p.drawRoundedRect(bg, 8, 8)
        p.setPen(QColor(255, 255, 255))
        p.drawText(bg, Qt.AlignCenter, text)

    def _draw_hint(self, p: QPainter, text: str) -> None:
        font = QFont()
        font.setFamily(FONT_FAMILY.split(",")[0].strip().strip('"'))
        font.setPixelSize(13)
        p.setFont(font)
        metrics = p.fontMetrics()
        w = metrics.horizontalAdvance(text) + 32
        h = 36
        x = (self.width() - w) // 2
        y = self.height() - h - 80
        bg = QRect(x, y, w, h)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(bg, 10, 10)
        p.setPen(QColor(26, 26, 26))
        p.drawText(bg, Qt.AlignCenter, text)
