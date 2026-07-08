"""OCR 결과 확인/수정 다이얼로그.

modeless(show)로 띄워 화면 원본과 대조하며 오인식을 고칠 수 있게 한다.
클립보드 자동 복사는 app.py에서 이미 끝난 상태 — 여기의 [전체 복사]는
수정본을 다시 복사하는 용도.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from .toast import Toast
from .tokens import COLORS, FONT_FAMILY


class OcrResultDialog(QDialog):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("OCR 결과")
        # 앱에 메인 창이 없어 뒤로 깔리기 쉬움 + 화면과 대조하는 용도라 항상 위
        self.setWindowFlags(
            (self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.resize(520, 380)
        self.setStyleSheet(
            f"""
            QDialog {{
                background: {COLORS['bg_primary']};
                font-family: {FONT_FAMILY};
            }}
            QLabel#ocrMeta {{
                color: {COLORS['text_secondary']};
                font-size: 12px;
            }}
            QPlainTextEdit {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border_solid']};
                border-radius: 8px;
                padding: 8px;
                font-family: {FONT_FAMILY};
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}
            QPushButton {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border_solid']};
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
                color: {COLORS['text_primary']};
                min-width: 64px;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_secondary']};
            }}
            QPushButton#ocrCopy {{
                background: #06B6D4;
                color: white;
                border: 1px solid #06B6D4;
            }}
            QPushButton#ocrCopy:hover {{
                background: #0891B2;
            }}
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(10)

        self._meta = QLabel(f"{len(text)}자 인식됨 · 수정 후 다시 복사할 수 있어요")
        self._meta.setObjectName("ocrMeta")
        outer.addWidget(self._meta)

        self._edit = QPlainTextEdit()
        self._edit.setPlainText(text)
        outer.addWidget(self._edit, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        copy_btn = QPushButton("전체 복사")
        copy_btn.setObjectName("ocrCopy")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_all)
        btn_row.addWidget(copy_btn)

        close_btn = QPushButton("닫기")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)

        outer.addLayout(btn_row)

    def _copy_all(self) -> None:
        QApplication.clipboard().setText(self._edit.toPlainText())
        Toast.show_text("복사됨", duration_ms=1200)
