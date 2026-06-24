from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    Qt,
)
from PySide6.QtGui import QFont, QFontMetrics, QGuiApplication
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)


GAP_PX = 10
OUTER_MARGIN = 0
INNER_PAD_H = 13
INNER_PAD_V_TOP = 9
INNER_PAD_V_BOTTOM = 10
LINE_GAP = 2
WIDTH_BUFFER = 4


class DockHoverLabel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._name_font = self._make_font(12, QFont.DemiBold)
        self._desc_font = self._make_font(11, QFont.Normal)

        self._current_color = ""

        self._build_ui()

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(140)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)

    @staticmethod
    def _make_font(pixel_size: int, weight) -> QFont:
        f = QFont()
        f.setFamily("Segoe UI Variable")
        f.setStyleHint(QFont.SansSerif)
        f.setPixelSize(pixel_size)
        f.setWeight(weight)
        return f

    def _build_ui(self) -> None:
        self._card = QWidget(self)
        self._card.setObjectName("hoverCard")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN
        )
        outer.addWidget(self._card)

        inner = QVBoxLayout(self._card)
        inner.setContentsMargins(
            INNER_PAD_H, INNER_PAD_V_TOP, INNER_PAD_H, INNER_PAD_V_BOTTOM
        )
        inner.setSpacing(LINE_GAP)

        self._name = QLabel()
        self._name.setObjectName("hoverName")
        self._name.setFont(self._name_font)
        self._name.setTextInteractionFlags(Qt.NoTextInteraction)
        inner.addWidget(self._name)

        self._desc = QLabel()
        self._desc.setObjectName("hoverDesc")
        self._desc.setFont(self._desc_font)
        self._desc.setTextInteractionFlags(Qt.NoTextInteraction)
        inner.addWidget(self._desc)

        self._apply_color("#6366F1")

    def _apply_color(self, color_hex: str) -> None:
        if color_hex == self._current_color:
            return
        self._current_color = color_hex
        self._card.setStyleSheet(self._stylesheet_for(color_hex))

    def _stylesheet_for(self, color_hex: str) -> str:
        return f"""
        QWidget#hoverCard {{
            background: {color_hex};
            border: none;
            border-radius: 12px;
        }}
        QLabel#hoverName {{
            color: #FFFFFF;
            background: transparent;
            letter-spacing: 0.1px;
        }}
        QLabel#hoverDesc {{
            color: rgba(255, 255, 255, 0.82);
            background: transparent;
        }}
        """

    def _compute_width(self, name: str, description: str) -> int:
        name_w = QFontMetrics(self._name_font).horizontalAdvance(name)
        desc_w = (
            QFontMetrics(self._desc_font).horizontalAdvance(description)
            if description
            else 0
        )
        content = max(name_w, desc_w)
        return content + INNER_PAD_H * 2 + OUTER_MARGIN * 2 + WIDTH_BUFFER

    def show_for(
        self,
        name: str,
        description: str,
        anchor_global: QPoint,
        side: str = "left",
        color: str = "#6366F1",
    ) -> None:
        if not name:
            self.hide_immediate()
            return

        self._apply_color(color)

        self._name.setText(name)
        if description:
            self._desc.setText(description)
            self._desc.show()
        else:
            self._desc.setText("")
            self._desc.hide()

        self.setFixedWidth(self._compute_width(name, description))
        self.adjustSize()

        if side == "right":
            x = anchor_global.x() + GAP_PX
            y = anchor_global.y() - self.height() // 2
        elif side == "left":
            x = anchor_global.x() - self.width() - GAP_PX
            y = anchor_global.y() - self.height() // 2
        elif side == "below":
            x = anchor_global.x() - self.width() // 2
            y = anchor_global.y() + GAP_PX
        elif side == "above":
            x = anchor_global.x() - self.width() // 2
            y = anchor_global.y() - self.height() - GAP_PX
        else:
            x = anchor_global.x() - self.width() - GAP_PX
            y = anchor_global.y() - self.height() // 2

        screen = QGuiApplication.screenAt(anchor_global) or QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            x = max(avail.x() + 4, min(x, avail.x() + avail.width() - self.width() - 4))
            y = max(
                avail.y() + 4,
                min(y, avail.y() + avail.height() - self.height() - 4),
            )

        self.move(x, y)

        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self.raise_()
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(1.0)
        self._fade.start()

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
