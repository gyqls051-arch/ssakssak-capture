"""앱 버전 정보. 새 릴리스마다 VERSION 수정."""
from __future__ import annotations

VERSION = "1.0.4"
BUILD_DATE = "2026-07-08"


def version_string() -> str:
    return f"싹싹김치 캡처 v{VERSION} ({BUILD_DATE})"
