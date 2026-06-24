"""앱 종료 시 뜨는 OFFCUT STUDIO 광고 다이얼로그.

assets/exit_ad.png 이 있으면 그 이미지를 우선 표시.
없으면 텍스트 기반 카드로 fallback.

광고 클릭 또는 [방문하기] → 브라우저로 STUDIO_URL 열고 닫힘.
[닫기] → 그냥 닫힘.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


STUDIO_URL = "https://offcut.app"
AD_WIDTH = 520


def _asset_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


def _find_ad_image() -> Optional[Path]:
    base = _asset_dir()
    for name in ("exit_ad.png", "exit_ad.jpg", "exit_ad.webp"):
        p = base / name
        if p.is_file():
            return p
    return None


class ExitAdDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("OFFCUT STUDIO")
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint
        )
        self.setModal(True)
        self.setFixedWidth(AD_WIDTH)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        ad_image = _find_ad_image()
        if ad_image is not None:
            self._build_image_section(root, ad_image)
        else:
            self._build_text_section(root)

        self._build_button_row(root)

    def _build_image_section(self, root: QVBoxLayout, ad_image: Path) -> None:
        pix = QPixmap(str(ad_image))
        if pix.isNull():
            self._build_text_section(root)
            return
        scaled = pix.scaledToWidth(AD_WIDTH, Qt.SmoothTransformation)
        label = QLabel()
        label.setPixmap(scaled)
        label.setAlignment(Qt.AlignCenter)
        label.setCursor(Qt.PointingHandCursor)
        label.mousePressEvent = lambda _e: self._open_studio()
        root.addWidget(label)

    def _build_text_section(self, root: QVBoxLayout) -> None:
        card = QFrame()
        card.setObjectName("AdCard")
        card.setStyleSheet(
            """
            QFrame#AdCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460);
            }
            """
        )
        card.setFixedHeight(280)
        card.setCursor(Qt.PointingHandCursor)
        card.mousePressEvent = lambda _e: self._open_studio()

        cl = QVBoxLayout(card)
        cl.setAlignment(Qt.AlignCenter)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(0)

        brand = QLabel("OFFCUT STUDIO")
        bf = QFont()
        bf.setPointSize(30)
        bf.setBold(True)
        bf.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        brand.setFont(bf)
        brand.setAlignment(Qt.AlignCenter)
        brand.setStyleSheet("color: #ffffff;")

        tagline = QLabel("Premiere Pro 컷편집 가속기")
        tf = QFont()
        tf.setPointSize(13)
        tagline.setFont(tf)
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet("color: #a5b4fc; margin-top: 6px;")

        desc = QLabel(
            "자동 컷 · 자막 · AI 캡션 · 클립 라이브러리\n"
            "싹싹김치 캡처 사용자에게 추천드려요"
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #cbd5e0; margin-top: 18px; line-height: 1.6;")

        cl.addWidget(brand)
        cl.addSpacing(6)
        cl.addWidget(tagline)
        cl.addSpacing(16)
        cl.addWidget(desc)

        root.addWidget(card)

    def _build_button_row(self, root: QVBoxLayout) -> None:
        row = QFrame()
        row.setStyleSheet("background: #ffffff;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(16, 14, 16, 14)
        rl.setSpacing(8)

        close_btn = QPushButton("닫기")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background: #e2e8f0; color: #2d3748;
                border: none; padding: 10px 20px;
                border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background: #cbd5e0; }
            """
        )
        close_btn.clicked.connect(self.accept)

        visit_btn = QPushButton("OFFCUT STUDIO 보러가기 →")
        visit_btn.setCursor(Qt.PointingHandCursor)
        visit_btn.setDefault(True)
        visit_btn.setStyleSheet(
            """
            QPushButton {
                background: #4f46e5; color: white;
                border: none; padding: 10px 20px;
                border-radius: 6px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #4338ca; }
            QPushButton:pressed { background: #3730a3; }
            """
        )
        visit_btn.clicked.connect(self._open_studio)

        rl.addStretch()
        rl.addWidget(close_btn)
        rl.addWidget(visit_btn)

        root.addWidget(row)

    def _open_studio(self) -> None:
        QDesktopServices.openUrl(QUrl(STUDIO_URL))
        self.accept()
