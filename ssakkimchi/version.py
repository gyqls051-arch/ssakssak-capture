"""앱 버전 정보. 새 릴리스마다 VERSION 수정."""
from __future__ import annotations

VERSION = "1.0.2"
BUILD_DATE = "2026-05-25"


def version_string() -> str:
    return f"싹싹김치 캡처 v{VERSION} ({BUILD_DATE})"
