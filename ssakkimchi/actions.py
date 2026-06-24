from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ActionSpec:
    key: str
    label: str
    default_hotkey: str


ACTIONS: List[ActionSpec] = [
    ActionSpec("region", "부분 캡처", "<alt>+1"),
    ActionSpec("full", "전체 캡처", "<alt>+2"),
    ActionSpec("window", "창 캡처", "<alt>+3"),
    ActionSpec("scroll", "스크롤 캡처", "<alt>+4"),
    ActionSpec("color", "색 추출", "<alt>+5"),
    ActionSpec("distance", "거리 측정", "<alt>+6"),
    ActionSpec("ocr", "OCR", "<alt>+7"),
    ActionSpec("record", "화면 녹화", "<alt>+8"),
    ActionSpec("gif", "GIF 녹화", "<alt>+9"),
]


def default_hotkeys() -> dict:
    return {a.key: a.default_hotkey for a in ACTIONS}


def action_labels() -> list:
    return [(a.key, a.label) for a in ACTIONS]
