"""로깅 시스템 — 친구 PC 진단의 기반.

- 파일: ~/.ssakkimchi/logs/ssakkimchi.log (5MB × 3 rotate)
- 콘솔: SSAKKIMCHI_DEBUG=1 환경변수 또는 --debug 인자 있을 때만
- uncaught exception은 자동으로 로그에 traceback과 함께 기록
- Qt 메시지(qWarning, qCritical)도 같은 파일로
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import traceback
from pathlib import Path
from typing import Optional

from .paths import user_root


_LOG_FILE_BYTES = 5 * 1024 * 1024
_LOG_BACKUP_COUNT = 3
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def logs_dir() -> Path:
    p = user_root() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def log_file_path() -> Path:
    return logs_dir() / "ssakkimchi.log"


def _debug_enabled() -> bool:
    if os.environ.get("SSAKKIMCHI_DEBUG"):
        return True
    return "--debug" in sys.argv


def setup_logging(force: bool = False) -> logging.Logger:
    """프로세스 1회 호출. 이미 셋업됐으면 그대로 반환."""
    global _configured
    root = logging.getLogger("ssakkimchi")
    if _configured and not force:
        return root

    root.setLevel(logging.DEBUG if _debug_enabled() else logging.INFO)
    root.propagate = False
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT)

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path(),
            maxBytes=_LOG_FILE_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root.addHandler(file_handler)
    except OSError:
        pass

    if _debug_enabled():
        try:
            console = logging.StreamHandler(sys.stderr)
            console.setFormatter(formatter)
            console.setLevel(logging.DEBUG)
            root.addHandler(console)
        except Exception:
            pass

    _install_excepthook(root)
    _install_qt_handler(root)

    _configured = True
    root.info("logging initialized (debug=%s) → %s", _debug_enabled(), log_file_path())
    return root


def get_logger(name: str) -> logging.Logger:
    """모듈별 로거. 'ssakkimchi.recording', 'ssakkimchi.app' 같은 식."""
    if not _configured:
        setup_logging()
    return logging.getLogger(f"ssakkimchi.{name}")


def _install_excepthook(root: logging.Logger) -> None:
    prev_hook = sys.excepthook

    def _hook(exc_type, exc_value, tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            prev_hook(exc_type, exc_value, tb)
            return
        try:
            tb_str = "".join(traceback.format_exception(exc_type, exc_value, tb))
            root.critical("UNCAUGHT EXCEPTION:\n%s", tb_str)
        except Exception:
            pass
        prev_hook(exc_type, exc_value, tb)

    sys.excepthook = _hook

    try:
        import threading
        prev_thread_hook = getattr(threading, "excepthook", None)

        def _thread_hook(args) -> None:
            try:
                tb_str = "".join(
                    traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
                )
                root.critical("UNCAUGHT EXCEPTION in thread %s:\n%s",
                              getattr(args.thread, "name", "?"), tb_str)
            except Exception:
                pass
            if prev_thread_hook is not None:
                prev_thread_hook(args)

        if prev_thread_hook is not None:
            threading.excepthook = _thread_hook
    except Exception:
        pass


def _install_qt_handler(root: logging.Logger) -> None:
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except Exception:
        return

    qt_logger = logging.getLogger("ssakkimchi.qt")
    level_map = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }

    def _qt_handler(msg_type, context, msg) -> None:
        try:
            qt_logger.log(level_map.get(msg_type, logging.INFO), "%s", msg)
        except Exception:
            pass

    try:
        qInstallMessageHandler(_qt_handler)
    except Exception:
        pass


def collect_diagnostics() -> str:
    """진단 텍스트: 클립보드로 복사하거나 친구 디버깅 시 사용."""
    import platform
    lines = [
        f"OS: {platform.platform()}",
        f"Python: {platform.python_version()} ({sys.executable})",
        f"Frozen: {getattr(sys, 'frozen', False)}",
        f"Log: {log_file_path()}",
        f"Captures: {user_root() / 'captures'}",
    ]
    try:
        from .ffmpeg_runtime import find_ffmpeg, detect_best_encoder
        lines.append(f"ffmpeg: {find_ffmpeg()}")
        lines.append(f"encoder: {detect_best_encoder()}")
    except Exception as exc:
        lines.append(f"ffmpeg probe failed: {exc}")
    try:
        from PySide6 import __version__ as pyside_ver
        lines.append(f"PySide6: {pyside_ver}")
    except Exception:
        pass
    return "\n".join(lines)
