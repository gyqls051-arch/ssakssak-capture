from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QImage,
    QMouseEvent,
    QPixmap,
)
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .icons import make_icon
from .shell_utils import reveal_in_explorer
from .tokens import COLORS, FONT_FAMILY


PREVIEW_MAX_W = 280
PREVIEW_MAX_H = 200
EDGE_MARGIN = 16
AUTO_DISMISS_MS = 5000


class CapturePreview(QWidget):
    folder_requested = Signal(Path)

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

        self._file_path: Optional[Path] = None

        self._build_ui()

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(180)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._fade_out)

    def _build_ui(self) -> None:
        self._card = QWidget(self)
        self._card.setObjectName("previewCard")
        self._card.setStyleSheet(
            f"""
            QWidget#previewCard {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border_solid']};
                border-radius: 12px;
            }}
            QLabel#previewMeta {{
                color: {COLORS['text_secondary']};
                font-family: {FONT_FAMILY};
                font-size: 11px;
            }}
            QLabel#previewTitle {{
                color: {COLORS['text_primary']};
                font-family: {FONT_FAMILY};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#previewIconBtn {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px;
            }}
            QPushButton#previewIconBtn:hover {{
                background: {COLORS['bg_secondary']};
            }}
            """
        )

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 6)
        self._card.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.addWidget(self._card)

        inner = QVBoxLayout(self._card)
        inner.setContentsMargins(12, 10, 10, 10)
        inner.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self._title = QLabel("캡처됨")
        self._title.setObjectName("previewTitle")
        top_row.addWidget(self._title, 1)

        self._open_btn = QPushButton()
        self._open_btn.setObjectName("previewIconBtn")
        self._open_btn.setIcon(make_icon("download", size=18, color=COLORS["text_secondary"]))
        self._open_btn.setIconSize(QSize(14, 14))
        self._open_btn.setCursor(Qt.PointingHandCursor)
        self._open_btn.setFixedSize(22, 22)
        self._open_btn.setToolTip("저장 폴더 열기")
        self._open_btn.clicked.connect(self._open_folder)
        top_row.addWidget(self._open_btn)

        self._close_btn = QPushButton()
        self._close_btn.setObjectName("previewIconBtn")
        self._close_btn.setIcon(make_icon("close", size=18, color=COLORS["text_secondary"]))
        self._close_btn.setIconSize(QSize(12, 12))
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.clicked.connect(self._fade_out)
        top_row.addWidget(self._close_btn)

        inner.addLayout(top_row)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setMinimumSize(120, 60)
        self._image_label.setCursor(Qt.PointingHandCursor)
        inner.addWidget(self._image_label)

        self._meta = QLabel("")
        self._meta.setObjectName("previewMeta")
        self._meta.setWordWrap(False)
        inner.addWidget(self._meta)

    def show_capture(self, image: QImage, file_path: Optional[Path], label: str = "캡처됨") -> None:
        self._file_path = file_path
        self._title.setText(label)

        pix = QPixmap.fromImage(image).scaled(
            PREVIEW_MAX_W,
            PREVIEW_MAX_H,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._image_label.setPixmap(pix)
        self._image_label.setFixedSize(pix.size())

        if file_path is not None:
            self._meta.setText(f"📁 {file_path.name}")
            self._open_btn.setEnabled(True)
            self._open_btn.show()
        else:
            self._meta.setText("📋 클립보드에 복사됨")
            self._open_btn.hide()

        self.adjustSize()
        self._place_bottom_right()

        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self.raise_()
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(1.0)
        self._fade.start()

        self._dismiss_timer.start(AUTO_DISMISS_MS)

    def _place_bottom_right(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        x = avail.x() + avail.width() - self.width() - EDGE_MARGIN
        y = avail.y() + avail.height() - self.height() - EDGE_MARGIN
        self.move(x, y)

    def _open_folder(self) -> None:
        if self._file_path is None:
            return
        reveal_in_explorer(self._file_path)

    def _fade_out(self) -> None:
        self._dismiss_timer.stop()
        if not self.isVisible():
            return
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._after_fade, Qt.SingleShotConnection)
        self._fade.start()

    def _after_fade(self) -> None:
        self.hide()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._fade_out()
