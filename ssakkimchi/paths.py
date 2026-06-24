import os
from pathlib import Path


def user_root() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".ssakkimchi"


def default_captures_dir() -> Path:
    return user_root() / "captures"


def palette_path() -> Path:
    return user_root() / "palette.json"


def settings_path() -> Path:
    return user_root() / "settings.json"


_FORBIDDEN_PREFIXES = (
    "\\\\.\\",
    "\\\\?\\",
    "//./",
    "//?/",
)


def is_safe_user_path(candidate: Path) -> bool:
    raw = str(candidate)
    if any(raw.startswith(prefix) for prefix in _FORBIDDEN_PREFIXES):
        return False
    try:
        resolved = candidate.expanduser().resolve(strict=False)
    except (OSError, RuntimeError):
        return False
    s = str(resolved)
    if any(s.startswith(prefix) for prefix in _FORBIDDEN_PREFIXES):
        return False
    forbidden_roots = []
    win_root = os.environ.get("SystemRoot")
    if win_root:
        forbidden_roots.append(Path(win_root).resolve())
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        forbidden_roots.append(Path(program_files).resolve())
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    if program_files_x86:
        forbidden_roots.append(Path(program_files_x86).resolve())
    for forbidden in forbidden_roots:
        try:
            resolved.relative_to(forbidden)
            return False
        except ValueError:
            continue
    return True
