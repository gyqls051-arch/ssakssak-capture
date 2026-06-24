from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from .tokens import (
    ANIM_TOAST_MS,
    COLORS,
    FONT_FAMILY,
    RADIUS,
    TOAST_DURATION_MS,
)


class Toast(QWidget):
    _instance: "Toast | None" = None

    @classmethod
    def show_text(cls, text: str, duration_ms: int = TOAST_DURATION_MS) -> None:
        if cls._instance is None:
            cls._instance = Toast()
        cls._instance.display(text, duration_ms)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._label = QLabel(self)
        self._label.setStyleSheet(
            f"""
            QLabel {{
                background: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_solid']};
                border-radius: {RADIUS['toast']}px;
                padding: 8px 14px;
                font-family: {FONT_FAMILY};
                font-size: 12px;
            }}
            """
        )
        self._label.setAlignment(Qt.AlignCenter)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        self._label.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._label)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(ANIM_TOAST_MS)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)

    def display(self, text: str, duration_ms: int) -> None:
        self._label.setText(text)
        self._label.adjustSize()
        self.adjustSize()
        self._place()
        self.setWindowOpacity(0.0)
        self.show()
        self._fade.stop()
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()
        self._hide_timer.start(duration_ms)

    def _fade_out(self) -> None:
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._on_hidden, Qt.SingleShotConnection)
        self._fade.start()

    def _on_hidden(self) -> None:
        self.hide()

    def _place(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        x = avail.x() + (avail.width() - self.width()) // 2
        y = avail.y() + avail.height() - self.height() - 64
        self.move(x, y)
