from typing import Callable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .icons import app_icon


class TrayController:
    def __init__(
        self,
        on_toggle_dock: Callable[[], None],
        on_region: Callable[[], None],
        on_color: Callable[[], None],
        on_quit: Callable[[], None],
        on_record: Callable[[], None] | None = None,
        on_gif: Callable[[], None] | None = None,
    ) -> None:
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(app_icon(64))
        self._tray.setToolTip("싹싹김치 캡처")

        menu = QMenu()

        toggle = QAction("도크 보이기 / 숨기기", menu)
        toggle.triggered.connect(on_toggle_dock)
        menu.addAction(toggle)

        menu.addSeparator()

        region = QAction("부분 캡처\tAlt+1", menu)
        region.triggered.connect(on_region)
        menu.addAction(region)

        color = QAction("색 추출\tAlt+5", menu)
        color.triggered.connect(on_color)
        menu.addAction(color)

        if on_record is not None:
            record = QAction("화면 녹화 (시작/정지)\tAlt+8", menu)
            record.triggered.connect(on_record)
            menu.addAction(record)

        if on_gif is not None:
            gif = QAction("GIF 녹화 (시작/정지)\tAlt+9", menu)
            gif.triggered.connect(on_gif)
            menu.addAction(gif)

        menu.addSeparator()

        quit_action = QAction("싹싹김치 캡처 종료", menu)
        quit_action.triggered.connect(on_quit)
        menu.addAction(quit_action)

        self._menu = menu
        self._tray.setContextMenu(menu)
        self._on_toggle = on_toggle_dock
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            self._on_toggle()

    def hide(self) -> None:
        self._tray.hide()
