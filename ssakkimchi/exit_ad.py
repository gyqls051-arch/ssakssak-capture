"""앱 종료 시 뜨는 팝업 배너 다이얼로그.

기본값은 자매 제품 OFFCUT STUDIO 홍보 배너입니다.
배너를 바꾸려면 아래 ★배너 설정★ 블록만 고치면 됩니다 (코드 수정 불필요).

- assets/<BANNER_IMAGE> 이미지가 있으면 그 이미지를 배너로 표시 (클릭 시 BANNER_URL 열림).
- 이미지가 없으면 BANNER_TITLE/SUBTITLE/DESC 로 텍스트 그라데이션 카드 표시(fallback).
- BANNER_ENABLED = False 로 두면 종료 시 팝업이 아예 안 뜸.
- BANNER_URL = "" 로 두면 클릭/[방문] 버튼 없이 단순 안내 배너로 동작.
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


# ════════════════════════ ★배너 설정★ (여기만 고치면 됨) ════════════════════════
# 종료 시 팝업 배너를 띄울지. False면 조용히 종료.
BANNER_ENABLED = True

# 배너 이미지 파일명 (assets/ 폴더에 둠). 이 파일이 있으면 텍스트 카드 대신 이미지를 표시.
# 권장: 가로 1040px(레티나 ×2), 다이얼로그 가로 520px에 맞춰 자동 축소.
# 이 이름이 없으면 exit_ad.png / .jpg / .webp 도 자동으로 찾음.
BANNER_IMAGE = "exit_ad.png"

# 배너 또는 [방문] 버튼 클릭 시 열 주소. 빈 문자열("")이면 클릭/버튼 비활성.
BANNER_URL = "https://offcut.app"

# ── 텍스트 카드(이미지 없을 때 fallback)용 문구 ──
BANNER_WINDOW_TITLE = "OFFCUT STUDIO"            # 창 제목
BANNER_TITLE = "OFFCUT STUDIO"                   # 큰 제목
BANNER_SUBTITLE = "Premiere Pro 컷편집 가속기"    # 부제
BANNER_DESC = (                                  # 설명 (\n 으로 줄바꿈)
    "자동 컷 · 자막 · AI 캡션 · 클립 라이브러리\n"
    "싹싹김치 캡처 사용자에게 추천드려요"
)
BANNER_BUTTON = "OFFCUT STUDIO 보러가기 →"        # 방문 버튼 문구
BANNER_ACCENT = "#4f46e5"                         # 버튼/포인트 색 (hex)
# ══════════════════════════════════════════════════════════════════════════════

# 하위호환 별칭 (옛 코드/문서가 STUDIO_URL 을 참조)
STUDIO_URL = BANNER_URL

AD_WIDTH = 520


def _shade(hex_color: str, factor: float) -> str:
    """hex 색을 factor(<1 어둡게)만큼 조정. 버튼 hover/pressed 색 자동 생성용."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r, g, b = (max(0, min(255, int(c * factor))) for c in (r, g, b))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


def _asset_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


def _find_ad_image() -> Optional[Path]:
    base = _asset_dir()
    seen: set[str] = set()
    for name in (BANNER_IMAGE, "exit_ad.png", "exit_ad.jpg", "exit_ad.webp"):
        if not name or name in seen:
            continue
        seen.add(name)
        p = base / name
        if p.is_file():
            return p
    return None


class ExitAdDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(BANNER_WINDOW_TITLE)
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
        if BANNER_URL:
            label.setCursor(Qt.PointingHandCursor)
            label.mousePressEvent = lambda _e: self._open_link()
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
        if BANNER_URL:
            card.setCursor(Qt.PointingHandCursor)
            card.mousePressEvent = lambda _e: self._open_link()

        cl = QVBoxLayout(card)
        cl.setAlignment(Qt.AlignCenter)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(0)

        brand = QLabel(BANNER_TITLE)
        bf = QFont()
        bf.setPointSize(30)
        bf.setBold(True)
        bf.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        brand.setFont(bf)
        brand.setAlignment(Qt.AlignCenter)
        brand.setStyleSheet("color: #ffffff;")

        tagline = QLabel(BANNER_SUBTITLE)
        tf = QFont()
        tf.setPointSize(13)
        tagline.setFont(tf)
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet("color: #a5b4fc; margin-top: 6px;")

        desc = QLabel(BANNER_DESC)
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

        rl.addStretch()
        rl.addWidget(close_btn)

        if BANNER_URL:
            visit_btn = QPushButton(BANNER_BUTTON)
            visit_btn.setCursor(Qt.PointingHandCursor)
            visit_btn.setDefault(True)
            visit_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {BANNER_ACCENT}; color: white;
                    border: none; padding: 10px 20px;
                    border-radius: 6px; font-size: 13px; font-weight: bold;
                }}
                QPushButton:hover {{ background: {_shade(BANNER_ACCENT, 0.85)}; }}
                QPushButton:pressed {{ background: {_shade(BANNER_ACCENT, 0.7)}; }}
                """
            )
            visit_btn.clicked.connect(self._open_link)
            rl.addWidget(visit_btn)

        root.addWidget(row)

    def _open_link(self) -> None:
        if BANNER_URL:
            QDesktopServices.openUrl(QUrl(BANNER_URL))
        self.accept()
