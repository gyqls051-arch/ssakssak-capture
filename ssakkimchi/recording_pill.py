"""녹화 중에 화면 상단에 떠 있는 작은 컨트롤 위젯.

● REC 00:12  ⏹
모달이 아니고, 도크와 별개의 항상-위 표시. 클릭으로 정지 가능.
입력은 받지만 자체적으론 글로벌 정지 핫키 케어 안 함 (app.py에서 핫키 트리거 시 stop 호출).
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from .icons import make_icon
from .tokens import COLORS, FONT_FAMILY, RADIUS


class RecordingPill(QWidget):
    stop_clicked = Signal()

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

        root = QWidget(self)
        root.setObjectName("recPillRoot")
        root.setStyleSheet(self._stylesheet())

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)

        shadow = QGraphicsDropShadowEffect(root)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 70))
        shadow.setOffset(0, 4)
        root.setGraphicsEffect(shadow)

        row = QHBoxLayout(root)
        row.setContentsMargins(12, 6, 8, 6)
        row.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setObjectName("recPillDot")
        self._dot.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        row.addWidget(self._dot)

        self._label = QLabel("REC 00:00")
        self._label.setObjectName("recPillLabel")
        self._label.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        row.addWidget(self._label)

        self._stop_btn = QPushButton()
        self._stop_btn.setObjectName("recPillStop")
        self._stop_btn.setFixedSize(26, 26)
        self._stop_btn.setIconSize(QSize(12, 12))
        self._stop_btn.setIcon(make_icon("stop", size=12, color="#FFFFFF"))
        self._stop_btn.setCursor(Qt.PointingHandCursor)
        self._stop_btn.setToolTip("녹화 정지")
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        row.addWidget(self._stop_btn)

        self._blink = QTimer(self)
        self._blink.setInterval(550)
        self._blink.timeout.connect(self._toggle_dot)
        self._dot_on = True

        self.adjustSize()

    def _stylesheet(self) -> str:
        return f"""
        QWidget#recPillRoot {{
            background: rgba(20, 20, 22, 235);
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 30);
        }}
        QLabel#recPillDot {{
            color: #EF4444;
            font-family: {FONT_FAMILY};
            font-size: 15px;
            min-width: 14px;
        }}
        QLabel#recPillLabel {{
            color: #F5F5F7;
            font-family: {FONT_FAMILY};
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        QPushButton#recPillStop {{
            background: #EF4444;
            border: none;
            border-radius: 13px;
        }}
        QPushButton#recPillStop:hover {{
            background: #DC2626;
        }}
        QPushButton#recPillStop:pressed {{
            background: #B91C1C;
        }}
        """

    def show_for(self, mode: str, region: QRect | None = None) -> None:
        prefix = "GIF" if mode == "gif" else "REC"
        self._label.setText(f"{prefix} 00:00")
        self._dot_on = True
        self._dot.setStyleSheet("color: #EF4444;")
        self.adjustSize()
        self._place_smart(region)
        self.show()
        self.raise_()
        self._blink.start()

    def update_elapsed(self, seconds: int) -> None:
        mm = seconds // 60
        ss = seconds % 60
        text = self._label.text().split()[0]
        self._label.setText(f"{text} {mm:02d}:{ss:02d}")

    def hide_pill(self) -> None:
        self._blink.stop()
        self.hide()

    def _toggle_dot(self) -> None:
        self._dot_on = not self._dot_on
        self._dot.setStyleSheet(
            f"color: {'#EF4444' if self._dot_on else 'rgba(239, 68, 68, 60)'};"
        )

    def _place_smart(self, region: QRect | None) -> None:
        """녹화 영역과 안 겹치게, 영역이 있는 화면 위에 배치.

        - 영역이 있는 화면을 우선 (멀티모니터)
        - 영역 위쪽 24px 자리가 있으면 거기, 아니면 아래쪽
        - 그것도 안 되면 화면 상단 24px (영역 폭만큼 가로 중앙 회피)
        """
        target_screen = QGuiApplication.primaryScreen()
        if region is not None and not region.isEmpty():
            probe = QPoint(region.center())
            screen_at = QGuiApplication.screenAt(probe)
            if screen_at is not None:
                target_screen = screen_at
        if target_screen is None:
            return
        avail = target_screen.availableGeometry()

        w = self.width()
        h = self.height()

        if region is not None and not region.isEmpty():
            cx = region.center().x() - w // 2
            cx = max(avail.x() + 8, min(cx, avail.x() + avail.width() - w - 8))
            above_y = region.y() - h - 12
            below_y = region.y() + region.height() + 12
            if above_y >= avail.y() + 8:
                self.move(cx, above_y)
                return
            if below_y + h <= avail.y() + avail.height() - 8:
                self.move(cx, below_y)
                return
            x = avail.x() + (avail.width() - w) // 2
            if region.contains(QPoint(x + w // 2, avail.y() + 24 + h // 2)):
                x = avail.x() + avail.width() - w - 16
            self.move(x, avail.y() + 24)
            return

        x = avail.x() + (avail.width() - w) // 2
        self.move(x, avail.y() + 24)
