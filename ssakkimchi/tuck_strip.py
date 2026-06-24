from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget

from .tokens import COLORS


STRIP_THICKNESS = 12
STRIP_RADIUS = 6
FADE_MS = 160


class TuckStripWindow(QWidget):
    hover_enter = Signal()
    context_menu_requested = Signal(QPoint)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        self._edge = "right"

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(FADE_MS)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)

    def show_at(
        self,
        x: int,
        y: int,
        cross_length: int,
        edge: str = "right",
    ) -> None:
        self._edge = edge
        if edge in ("left", "right"):
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.setFixedWidth(STRIP_THICKNESS)
            self.setFixedHeight(cross_length)
        else:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.setFixedHeight(STRIP_THICKNESS)
            self.setFixedWidth(cross_length)
        self.move(x, y)
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self.raise_()
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(1.0)
        self._fade.start()
        self.update()

    def hide_animated(self) -> None:
        if not self.isVisible():
            return
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._after_fade, Qt.SingleShotConnection)
        self._fade.start()

    def hide_immediate(self) -> None:
        self._fade.stop()
        self.hide()

    def _after_fade(self) -> None:
        self.hide()

    def enterEvent(self, event) -> None:
        self.hover_enter.emit()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.RightButton:
            self.context_menu_requested.emit(event.globalPosition().toPoint())
        elif event.button() == Qt.LeftButton:
            self.hover_enter.emit()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect())
        rad = STRIP_RADIUS

        path = self._build_shape_path(rect, rad)

        p.setBrush(QColor(COLORS["bg_primary"]))
        p.setPen(QPen(QColor(COLORS["border_solid"]), 1))
        p.drawPath(path)

        self._draw_chevron(p, rect)

    def _build_shape_path(self, rect: QRectF, rad: float) -> QPainterPath:
        path = QPainterPath()
        if self._edge == "right":
            path.moveTo(rect.right() + 0.5, rect.top())
            path.lineTo(rect.left() + rad, rect.top())
            path.quadTo(rect.left(), rect.top(), rect.left(), rect.top() + rad)
            path.lineTo(rect.left(), rect.bottom() - rad)
            path.quadTo(rect.left(), rect.bottom(), rect.left() + rad, rect.bottom())
            path.lineTo(rect.right() + 0.5, rect.bottom())
        elif self._edge == "left":
            path.moveTo(rect.left() - 0.5, rect.top())
            path.lineTo(rect.right() - rad, rect.top())
            path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + rad)
            path.lineTo(rect.right(), rect.bottom() - rad)
            path.quadTo(rect.right(), rect.bottom(), rect.right() - rad, rect.bottom())
            path.lineTo(rect.left() - 0.5, rect.bottom())
        elif self._edge == "top":
            path.moveTo(rect.left(), rect.top() - 0.5)
            path.lineTo(rect.left(), rect.bottom() - rad)
            path.quadTo(rect.left(), rect.bottom(), rect.left() + rad, rect.bottom())
            path.lineTo(rect.right() - rad, rect.bottom())
            path.quadTo(rect.right(), rect.bottom(), rect.right(), rect.bottom() - rad)
            path.lineTo(rect.right(), rect.top() - 0.5)
        else:
            path.moveTo(rect.left(), rect.bottom() + 0.5)
            path.lineTo(rect.left(), rect.top() + rad)
            path.quadTo(rect.left(), rect.top(), rect.left() + rad, rect.top())
            path.lineTo(rect.right() - rad, rect.top())
            path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + rad)
            path.lineTo(rect.right(), rect.bottom() + 0.5)
        return path

    def _draw_chevron(self, p: QPainter, rect: QRectF) -> None:
        pen = QPen(QColor(COLORS["text_tertiary"]), 1.4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        cx = rect.width() / 2.0
        cy = rect.height() / 2.0
        a = 1.8
        if self._edge == "right":
            chevron = [QPointF(cx + 1.4, cy - 4), QPointF(cx - a, cy), QPointF(cx + 1.4, cy + 4)]
        elif self._edge == "left":
            chevron = [QPointF(cx - 1.4, cy - 4), QPointF(cx + a, cy), QPointF(cx - 1.4, cy + 4)]
        elif self._edge == "top":
            chevron = [QPointF(cx - 4, cy - 1.4), QPointF(cx, cy + a), QPointF(cx + 4, cy - 1.4)]
        else:
            chevron = [QPointF(cx - 4, cy + 1.4), QPointF(cx, cy - a), QPointF(cx + 4, cy + 1.4)]
        p.drawPolyline(chevron)
