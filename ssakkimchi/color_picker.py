from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QImage,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

import mss

from .capture_core import virtual_desktop_geometry
from .icons import render_pixmap
from .tokens import FONT_FAMILY


def _build_eyedropper_cursor() -> QCursor:
    body = render_pixmap("color", size=28, color="#1F2937")
    outline = render_pixmap("color", size=28, color="#FFFFFF")
    composite = QPixmap(28, 28)
    composite.fill(Qt.transparent)
    p = QPainter(composite)
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        p.drawPixmap(dx, dy, outline)
    p.drawPixmap(0, 0, body)
    p.end()
    return QCursor(composite, 5, 22)


class ColorPickerOverlay(QWidget):
    picked = Signal(str)
    cancelled = Signal()

    SAMPLE_SIZE = 11
    SAMPLE_SCALE = 11
    MAGNIFIER_PAD = 8
    LABEL_HEIGHT = 22
    CURSOR_OFFSET = 22

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
        self.setCursor(_build_eyedropper_cursor())
        self._virtual_geom = virtual_desktop_geometry()
        self.setGeometry(self._virtual_geom)

        self._cursor_pos = QPoint(0, 0)
        self._current_hex = "#000000"
        self._magnifier_pixmap = QPixmap()
        self._sct = None

        self._refresh = QTimer(self)
        self._refresh.setInterval(33)
        self._refresh.timeout.connect(self._sample_and_update)

    def begin(self) -> None:
        self._virtual_geom = virtual_desktop_geometry()
        self.setGeometry(self._virtual_geom)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.OtherFocusReason)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.grabKeyboard()
        if self._sct is None:
            self._sct = mss.mss()
        self._refresh.start()
        self._sample_and_update()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._refresh.stop()
        self.releaseKeyboard()
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self._cursor_pos = event.position().toPoint()
        self._sample_and_update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.picked.emit(self._current_hex)
        elif event.button() == Qt.RightButton:
            self.hide()
            self.cancelled.emit()

    def _sample_and_update(self) -> None:
        self._sample()
        self.update()

    def _sample(self) -> None:
        if self._sct is None:
            return
        screen = self.screen() or QGuiApplication.primaryScreen()
        dpr = float(screen.devicePixelRatio() if screen else 1.0)

        global_pt = self.mapToGlobal(self._cursor_pos)
        cx = int(round(global_pt.x() * dpr))
        cy = int(round(global_pt.y() * dpr))
        n = self.SAMPLE_SIZE
        region = {
            "left": cx - n // 2,
            "top": cy - n // 2,
            "width": n,
            "height": n,
        }
        try:
            shot = self._sct.grab(region)
        except Exception:
            return

        img = QImage(
            bytes(shot.bgra),
            shot.width,
            shot.height,
            shot.width * 4,
            QImage.Format_ARGB32,
        ).copy()

        center = img.pixelColor(n // 2, n // 2)
        self._current_hex = "#{:02X}{:02X}{:02X}".format(
            center.red(), center.green(), center.blue()
        )

        scaled = img.scaled(
            n * self.SAMPLE_SCALE,
            n * self.SAMPLE_SCALE,
            Qt.IgnoreAspectRatio,
            Qt.FastTransformation,
        )
        self._magnifier_pixmap = QPixmap.fromImage(scaled)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
        painter.setRenderHint(QPainter.Antialiasing, True)

        size = self.SAMPLE_SIZE * self.SAMPLE_SCALE
        ox, oy = self.CURSOR_OFFSET, self.CURSOR_OFFSET
        mx = self._cursor_pos.x() + ox
        my = self._cursor_pos.y() + oy

        if mx + size + 8 > self.width():
            mx = self._cursor_pos.x() - size - ox
        if my + size + self.LABEL_HEIGHT + 8 > self.height():
            my = self._cursor_pos.y() - size - self.LABEL_HEIGHT - oy

        mag_rect = QRect(mx, my, size, size)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(mag_rect.adjusted(-1, -1, 1, 1), 8, 8)

        if not self._magnifier_pixmap.isNull():
            painter.drawPixmap(mag_rect, self._magnifier_pixmap)

        scale = self.SAMPLE_SCALE
        cx = mx + (self.SAMPLE_SIZE // 2) * scale
        cy = my + (self.SAMPLE_SIZE // 2) * scale
        center_rect = QRect(cx, cy, scale, scale)
        pen_outer = QPen(QColor(0, 0, 0, 180), 1)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(center_rect)
        pen_inner = QPen(QColor(255, 255, 255, 220), 1)
        painter.setPen(pen_inner)
        painter.drawRect(center_rect.adjusted(1, 1, -1, -1))

        border_pen = QPen(QColor(0, 0, 0, 30), 1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(mag_rect, 8, 8)

        label_rect = QRect(mx, my + size + 4, size, self.LABEL_HEIGHT)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(label_rect, 4, 4)
        painter.setPen(QPen(QColor(0, 0, 0, 30), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(label_rect, 4, 4)

        font = QFont()
        font.setFamily(FONT_FAMILY.split(",")[0].strip().strip('"'))
        font.setPixelSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(26, 26, 26))
        painter.drawText(label_rect, Qt.AlignCenter, self._current_hex)
