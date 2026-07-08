from typing import Dict, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from .logging_setup import get_logger

try:
    from pynput import keyboard as _pkb
except Exception:
    _pkb = None


log = get_logger("hotkeys")


_KEY_ALIASES = {
    "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "shift_l": "shift", "shift_r": "shift",
    "cmd_l": "cmd", "cmd_r": "cmd",
}


def _pynput_key_to_name(key) -> Optional[str]:
    if key is None:
        return None
    try:
        if hasattr(key, "name") and key.name:
            return _KEY_ALIASES.get(key.name.lower(), key.name.lower())
        if hasattr(key, "char") and key.char:
            return key.char.lower()
    except Exception:
        pass
    return None


def _parse_combo_to_keyset(combo: str) -> frozenset:
    """'<ctrl>+<shift>+1' or 'Alt+1' → frozenset({'ctrl','shift','1'})."""
    parts = [p.strip() for p in combo.split("+") if p.strip()]
    keys = set()
    for p in parts:
        if p.startswith("<") and p.endswith(">"):
            p = p[1:-1]
        keys.add(p.lower())
    return frozenset(keys)


class HotkeyTester(QObject):
    """단일 단축키 동작 검증. 5초 동안 raw key listener로 매칭.

    메인 HotkeyManager와 무관하게 작동. 부수 효과: 사용자가 누른 키가
    시스템의 다른 hotkey도 fire시킬 수 있음 (우리 메인 등 포함).
    """

    result = Signal(bool)

    def __init__(self, target_combo: str, timeout_ms: int = 5000) -> None:
        super().__init__()
        self._target = _parse_combo_to_keyset(target_combo)
        self._pressed: set = set()
        self._matched = False
        self._listener = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(timeout_ms)
        self._timer.timeout.connect(self._on_timeout)

    def start(self) -> bool:
        if _pkb is None or not self._target:
            self.result.emit(False)
            return False
        try:
            self._listener = _pkb.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()
        except Exception:
            self.result.emit(False)
            return False
        self._timer.start()
        return True

    def cancel(self) -> None:
        self._stop_quietly()

    def _on_press(self, key) -> None:
        name = _pynput_key_to_name(key)
        if not name:
            return
        self._pressed.add(name)
        if not self._matched and self._target.issubset(self._pressed):
            self._matched = True
            self._stop_quietly()
            self.result.emit(True)

    def _on_release(self, key) -> None:
        name = _pynput_key_to_name(key)
        if name and name in self._pressed:
            self._pressed.discard(name)

    def _on_timeout(self) -> None:
        if not self._matched:
            self._stop_quietly()
            self.result.emit(False)

    def _stop_quietly(self) -> None:
        self._timer.stop()
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


_MODIFIERS = {"ctrl", "shift", "alt", "meta", "cmd"}
_NAMED_KEYS = {
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8",
    "f9", "f10", "f11", "f12",
    "esc", "tab", "space", "enter", "return", "backspace",
    "delete", "up", "down", "left", "right",
    "home", "end", "pageup", "pagedown", "insert",
    "print_screen", "scroll_lock", "pause",
}

_QT_TO_PYNPUT_ALIAS = {
    "print": "print_screen",
    "sysreq": "print_screen",
    "scrolllock": "scroll_lock",
    "pgup": "pageup",
    "pgdown": "pagedown",
    "return": "enter",
}

_PYNPUT_TO_QT_ALIAS = {
    "print_screen": "Print",
    "scroll_lock": "ScrollLock",
    "pageup": "PgUp",
    "pagedown": "PgDown",
}


def qt_to_pynput(seq_str: str) -> str:
    if not seq_str:
        return ""
    parts = [p.strip() for p in seq_str.split("+") if p.strip()]
    out = []
    for p in parts:
        low = p.lower()
        low = _QT_TO_PYNPUT_ALIAS.get(low, low)
        if low in _MODIFIERS or low in _NAMED_KEYS:
            out.append(f"<{low}>")
        else:
            out.append(low)
    return "+".join(out)


def pynput_to_qt(combo: str) -> str:
    if not combo:
        return ""
    parts = [p.strip() for p in combo.split("+") if p.strip()]
    out = []
    for p in parts:
        clean = p
        if clean.startswith("<") and clean.endswith(">"):
            clean = clean[1:-1]
        if clean in _MODIFIERS:
            out.append(clean.capitalize())
        elif clean in _PYNPUT_TO_QT_ALIAS:
            out.append(_PYNPUT_TO_QT_ALIAS[clean])
        elif clean in _NAMED_KEYS:
            out.append(clean.upper() if clean.startswith("f") and clean[1:].isdigit() else clean.capitalize())
        elif len(clean) == 1 and clean.isalpha():
            out.append(clean.upper())
        else:
            out.append(clean)
    return "+".join(out)


class HotkeyManager(QObject):
    triggered = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._listener: Optional[object] = None

    def start(self, bindings: Dict[str, str]) -> bool:
        """전역 핫키 등록. 하나라도 등록되면 True.

        잘못된 조합 문자열 1개 때문에 전체가 죽지 않도록, 조합별로
        parse 검증해서 나쁜 것만 건너뛴다. 실패는 로그에 남긴다."""
        if _pkb is None:
            log.error("pynput unavailable — global hotkeys disabled")
            return False
        mapping = {}
        for action, combo in bindings.items():
            combo = (combo or "").strip()
            if not combo:
                continue
            try:
                _pkb.HotKey.parse(combo)
            except Exception as exc:
                log.warning("invalid hotkey %r for %s: %s — skipped", combo, action, exc)
                continue
            mapping[combo] = self._make_emitter(action)
        if not mapping:
            log.warning("no valid hotkey bindings to register")
            return False
        try:
            self._listener = _pkb.GlobalHotKeys(mapping)
            self._listener.start()
        except Exception:
            log.exception("GlobalHotKeys start failed")
            self._listener = None
            return False
        return True

    def restart(self, bindings: Dict[str, str]) -> bool:
        self.stop()
        return self.start(bindings)

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _make_emitter(self, action: str):
        def _emit():
            self.triggered.emit(action)
        return _emit
