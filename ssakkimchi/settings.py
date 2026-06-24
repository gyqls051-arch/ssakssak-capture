import json
from pathlib import Path
from typing import Optional

from .paths import default_captures_dir, is_safe_user_path, settings_path


def _load() -> dict:
    path = settings_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _save(data: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_captures_dir() -> Path:
    data = _load()
    raw = data.get("captures_dir")
    if raw:
        try:
            p = Path(raw).expanduser()
            if is_safe_user_path(p):
                p.mkdir(parents=True, exist_ok=True)
                return p
        except Exception:
            pass
    p = default_captures_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def set_captures_dir(path: Optional[Path]) -> bool:
    data = _load()
    if path is None:
        data.pop("captures_dir", None)
        _save(data)
        return True
    p = Path(path).expanduser()
    if not is_safe_user_path(p):
        return False
    data["captures_dir"] = str(p)
    _save(data)
    return True
