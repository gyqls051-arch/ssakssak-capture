from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QImage,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QWidget

from .capture_core import grab_qimage, virtual_desktop_geometry
from .tokens import FONT_FAMILY


def _active_screen_geometry() -> tuple[QRect, float]:
    """마우스 커서가 있는 모니터 1개의 geometry + DPR. 듀얼모니터 호환."""
    cursor = QCursor.pos()
    screen = QGuiApplication.screenAt(cursor)
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    if screen is None:
        return virtual_desktop_geometry(), 1.0
    return QRect(screen.geometry()), float(screen.devicePixelRatio() or 1.0)


class RegionCaptureOverlay(QWidget):
    captured = Signal(QImage)
    region_selected = Signal(QRect, float)
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
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self._virtual_geom, self._dpr = _active_screen_geometry()
        self.setGeometry(self._virtual_geom)
        self._start: QPoint | None = None
        self._end: QPoint | None = None
        self._cursor_pos = QPoint(0, 0)

    def begin(self) -> None:
        self._start = None
        self._end = None
        self._virtual_geom, self._dpr = _active_screen_geometry()
        self.setGeometry(self._virtual_geom)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.OtherFocusReason)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.grabKeyboard()
        self.grabMouse()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.releaseKeyboard()
        self.releaseMouse()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self.update()

    def mouseMoveEvent(self, event) -> None:
        self._cursor_pos = event.position().toPoint()
        if self._start is not None:
            self._end = self._cursor_pos
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or self._start is None:
            return
        self._end = event.position().toPoint()
        rect = self._selection_rect()
        self.hide()
        if rect.width() >= 2 and rect.height() >= 2:
            global_rect = QRect(
                self._virtual_geom.x() + rect.x(),
                self._virtual_geom.y() + rect.y(),
                rect.width(),
                rect.height(),
            )
            self.region_selected.emit(global_rect, self._dpr)
            image = self._grab(rect)
            self.captured.emit(image)
        else:
            self.cancelled.emit()

    def _selection_rect(self) -> QRect:
        if self._start is None or self._end is None:
            return QRect()
        return QRect(self._start, self._end).normalized()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))

        if self._start is not None and self._end is not None:
            rect = self._selection_rect()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            pen = QPen(QColor(255, 255, 255, 235), 1)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

            self._draw_size_badge(painter, rect)
        else:
            self._draw_hint(painter)

    def _draw_hint(self, painter: QPainter) -> None:
        text = "Drag to capture · Esc to cancel"
        font = QFont()
        font.setFamily(FONT_FAMILY.split(",")[0].strip().strip('"'))
        font.setPixelSize(13)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        w = metrics.horizontalAdvance(text) + 24
        h = 28
        x = (self.width() - w) // 2
        y = self.height() - h - 64
        bg = QRect(x, y, w, h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawRoundedRect(bg, 8, 8)
        painter.setPen(QColor(26, 26, 26))
        painter.drawText(bg, Qt.AlignCenter, text)

    def _draw_size_badge(self, painter: QPainter, rect: QRect) -> None:
        text = f"{rect.width()} × {rect.height()}"
        font = QFont()
        font.setFamily(FONT_FAMILY.split(",")[0].strip().strip('"'))
        font.setPixelSize(11)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        pad_x, pad_y = 6, 3
        w = metrics.horizontalAdvance(text) + pad_x * 2
        h = metrics.height() + pad_y * 2

        bx = rect.x()
        by = rect.y() - h - 4
        if by < self.rect().y() + 2:
            by = rect.y() + 4
            bx = rect.x() + 4
        badge = QRect(bx, by, w, h)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawRoundedRect(badge, 4, 4)
        painter.setPen(QColor(26, 26, 26))
        painter.drawText(badge, Qt.AlignCenter, text)

    def _grab(self, qrect: QRect) -> QImage:
        dpr = self._dpr
        gx = self._virtual_geom.x() + qrect.x()
        gy = self._virtual_geom.y() + qrect.y()
        region = {
            "left": int(round(gx * dpr)),
            "top": int(round(gy * dpr)),
            "width": max(1, int(round(qrect.width() * dpr))),
            "height": max(1, int(round(qrect.height() * dpr))),
        }
        return grab_qimage(region) or QImage()
