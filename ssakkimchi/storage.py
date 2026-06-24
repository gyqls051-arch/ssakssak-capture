import json
from pathlib import Path
from typing import Any, Dict

from .actions import default_hotkeys
from .paths import palette_path, user_root


def _storage_path() -> Path:
    user_root().mkdir(parents=True, exist_ok=True)
    return palette_path()


def default_data() -> Dict[str, Any]:
    return {
        "palette": [],
        "settings": {
            "hotkeys": default_hotkeys(),
        },
    }


def load_data() -> Dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return default_data()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return default_data()
    merged = default_data()
    if isinstance(data.get("palette"), list):
        merged["palette"] = [str(c) for c in data["palette"] if isinstance(c, str)]
    if isinstance(data.get("settings"), dict):
        settings_in = data["settings"]
        if isinstance(settings_in.get("hotkeys"), dict):
            merged["settings"]["hotkeys"].update(
                {k: str(v) for k, v in settings_in["hotkeys"].items() if isinstance(v, str)}
            )
    return merged


def save_data(data: Dict[str, Any]) -> None:
    path = _storage_path()
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)
