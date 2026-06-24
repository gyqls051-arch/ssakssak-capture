from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtGui import QImage

from .settings import get_captures_dir


def captures_dir() -> Path:
    return get_captures_dir()


def save_image(image: QImage, kind: str = "capture") -> Optional[Path]:
    if image is None or image.isNull():
        return None
    base = captures_dir()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_kind = "".join(c for c in kind if c.isalnum() or c in "-_")
    path = base / f"{stamp}_{safe_kind}.png"
    counter = 1
    while path.exists():
        path = base / f"{stamp}_{safe_kind}_{counter}.png"
        counter += 1
    if image.save(str(path), "PNG"):
        return path
    return None
