from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QGuiApplication,
    QMouseEvent,
    QPainter,
)
from PySide6.QtWidgets import (
    QBoxLayout,
    QFileDialog,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import os
import subprocess

from .settings import get_captures_dir, set_captures_dir
from .toast import Toast

from .hover_label import DockHoverLabel
from .icons import make_icon
from .tuck_strip import TuckStripWindow, STRIP_THICKNESS
from .tokens import (
    COLORS,
    DOCK_EDGE_MARGIN,
    DOCK_PADDING,
    DOCK_WIDTH,
    FONT_FAMILY,
    ICON_BTN_SIZE,
    ICON_GAP,
    ICON_SVG_SIZE,
    RADIUS,
    SEPARATOR_HEIGHT,
)


HOVER_ICON_SIZE = 26
HOVER_ANIM_MS = 140

HANDLE_HEIGHT = 18
HANDLE_DOT_DIAM = 2
HANDLE_DOT_GAP = 4
HANDLE_DOT_ROWS = 2
HANDLE_DOT_COLS = 3


class DockHandle(QWidget):
    context_menu_requested = Signal(QPoint)
    drag_ended = Signal()

    def __init__(self, orientation: str = "vertical", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._orientation = orientation
        self.set_orientation(orientation)
        self.setCursor(Qt.SizeAllCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self._drag_window_origin: Optional[QPoint] = None
        self._drag_mouse_origin: Optional[QPoint] = None
        self._hovered = False

    def set_orientation(self, orientation: str) -> None:
        self._orientation = orientation
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        if orientation == "vertical":
            self.setFixedHeight(HANDLE_HEIGHT)
        else:
            self.setFixedWidth(HANDLE_HEIGHT)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        color = QColor(
            COLORS["text_secondary"] if self._hovered else COLORS["text_tertiary"]
        )
        p.setPen(Qt.NoPen)
        p.setBrush(color)

        total_w = HANDLE_DOT_COLS * HANDLE_DOT_DIAM + (HANDLE_DOT_COLS - 1) * HANDLE_DOT_GAP
        total_h = HANDLE_DOT_ROWS * HANDLE_DOT_DIAM + (HANDLE_DOT_ROWS - 1) * HANDLE_DOT_GAP
        start_x = (self.width() - total_w) / 2
        start_y = (self.height() - total_h) / 2
        for r in range(HANDLE_DOT_ROWS):
            for c in range(HANDLE_DOT_COLS):
                x = start_x + c * (HANDLE_DOT_DIAM + HANDLE_DOT_GAP)
                y = start_y + r * (HANDLE_DOT_DIAM + HANDLE_DOT_GAP)
                p.drawEllipse(int(x), int(y), HANDLE_DOT_DIAM, HANDLE_DOT_DIAM)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            top = self.window()
            self._drag_window_origin = top.pos()
            self._drag_mouse_origin = event.globalPosition().toPoint()
        elif event.button() == Qt.RightButton:
            self.context_menu_requested.emit(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._drag_window_origin is None
            or self._drag_mouse_origin is None
            or not (event.buttons() & Qt.LeftButton)
        ):
            return
        delta = event.globalPosition().toPoint() - self._drag_mouse_origin
        self.window().move(self._drag_window_origin + delta)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            had_drag = self._drag_window_origin is not None
            self._drag_window_origin = None
            self._drag_mouse_origin = None
            if had_drag:
                self.drag_ended.emit()


@dataclass
class DockItem:
    key: str
    icon: str
    name: str = ""
    description: str = ""
    color: str = "#6366F1"
    checkable: bool = False


class IconButton(QPushButton):
    hovered_in = Signal(object)
    hovered_out = Signal(object)

    def __init__(self, item: DockItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._item = item
        self._is_hover = False
        self.setObjectName("dockIconButton")
        self.setFixedSize(ICON_BTN_SIZE, ICON_BTN_SIZE)
        self.setIconSize(QSize(ICON_SVG_SIZE, ICON_SVG_SIZE))
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("")
        self.setCheckable(item.checkable)
        self._refresh_icon()

        self._icon_anim = QPropertyAnimation(self, b"iconSize", self)
        self._icon_anim.setDuration(HOVER_ANIM_MS)
        self._icon_anim.setEasingCurve(QEasingCurve.OutCubic)

    @property
    def item(self) -> DockItem:
        return self._item

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        if self.isChecked():
            color = self._item.color or COLORS["text_active"]
        elif self._is_hover and self._item.color:
            color = self._item.color
        else:
            color = COLORS["text_primary"]
        self.setIcon(make_icon(self._item.icon, size=HOVER_ICON_SIZE, color=color))

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._is_hover = True
        self._refresh_icon()
        self._animate_icon(QSize(HOVER_ICON_SIZE, HOVER_ICON_SIZE))
        self.hovered_in.emit(self)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._is_hover = False
        self._refresh_icon()
        self._animate_icon(QSize(ICON_SVG_SIZE, ICON_SVG_SIZE))
        self.hovered_out.emit(self)

    def _animate_icon(self, target: QSize) -> None:
        self._icon_anim.stop()
        self._icon_anim.setStartValue(self.iconSize())
        self._icon_anim.setEndValue(target)
        self._icon_anim.start()


class Dock(QWidget):
    item_clicked = Signal(str)
    tucked = Signal()
    quit_requested = Signal()
    hide_requested = Signal()
    hotkey_settings_requested = Signal()
    prtsc_takeover_requested = Signal()
    prtsc_release_requested = Signal()
    about_requested = Signal()

    ITEMS: List[DockItem] = [
        DockItem("full", "full", "전체 캡처", "화면 전체를 한 번에 클립보드로", color="#6366F1"),
        DockItem("region", "region", "부분 캡처", "드래그한 영역만 캡처", color="#8B5CF6"),
        DockItem("window", "window", "창 캡처", "선택한 창만 깔끔하게", color="#06B6D4"),
        DockItem("scroll", "scroll", "스크롤 캡처", "긴 페이지를 이어붙여서", color="#F97316"),
        DockItem("__sep__", "", "", "", color=""),
        DockItem("record", "record", "화면 녹화", "드래그한 영역을 MP4로 녹화", color="#EF4444", checkable=True),
        DockItem("gif", "gif", "GIF 녹화", "짧은 동작을 부드러운 GIF로", color="#F43F5E", checkable=True),
        DockItem("__sep__", "", "", "", color=""),
        DockItem("color", "color", "색 추출", "화면 어디서든 픽셀 컬러", color="#EC4899", checkable=True),
        DockItem("distance", "distance", "거리 측정", "두 지점 사이 픽셀 거리", color="#10B981"),
        DockItem("ocr", "ocr", "OCR", "이미지 속 글자를 텍스트로", color="#F59E0B"),
        DockItem("__sep__", "", "", "", color=""),
        DockItem("layout", "layout", "레이아웃 전환", "한 번 클릭으로 가로 ↔ 세로", color="#64748B"),
    ]

    MODE_PINNED = "pinned"
    MODE_TUCKED = "tucked"
    MODE_PEEKED = "peeked"
    TUCK_VISIBLE = STRIP_THICKNESS
    PEEK_LEAVE_DELAY_MS = 800
    PEEK_BUFFER_PX = 18
    DOCK_FADE_MS = 160

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._buttons: dict[str, IconButton] = {}
        self._mode = self.MODE_PINNED
        self._edge = "right"
        self._auto_tuck_paused = False

        self._snap_anim = QPropertyAnimation(self, b"pos", self)
        self._snap_anim.setDuration(180)
        self._snap_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(self.DOCK_FADE_MS)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._strip = TuckStripWindow()
        self._strip.hover_enter.connect(self._on_strip_hover)
        self._strip.context_menu_requested.connect(self._show_handle_menu)

        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(80)
        self._cursor_timer.timeout.connect(self._poll_cursor)

        self._leave_timer = QTimer(self)
        self._leave_timer.setSingleShot(True)
        self._leave_timer.setInterval(self.PEEK_LEAVE_DELAY_MS)
        self._leave_timer.timeout.connect(self._on_peek_leave)

        self._hover_label = DockHoverLabel()
        self._hovered_button: Optional[IconButton] = None
        self._label_hide_timer = QTimer(self)
        self._label_hide_timer.setSingleShot(True)
        self._label_hide_timer.setInterval(600)
        self._label_hide_timer.timeout.connect(self._maybe_hide_label)

        self._build_ui()

    def orientation(self) -> str:
        return "horizontal" if self._edge in ("top", "bottom") else "vertical"

    def _build_ui(self) -> None:
        if self.layout() is not None:
            old_layout = self.layout()
            while old_layout.count() > 0:
                item = old_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()

        self._root = QWidget(self)
        self._root.setObjectName("dockRoot")
        self._root.setStyleSheet(self._stylesheet())

        if self.layout() is None:
            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
        else:
            outer = self.layout()
        outer.addWidget(self._root)

        is_vertical = self.orientation() == "vertical"
        direction = QBoxLayout.TopToBottom if is_vertical else QBoxLayout.LeftToRight
        column = QBoxLayout(direction, self._root)
        column.setContentsMargins(
            DOCK_PADDING, DOCK_PADDING, DOCK_PADDING, DOCK_PADDING
        )
        column.setSpacing(ICON_GAP)
        column.setAlignment(
            (Qt.AlignTop | Qt.AlignHCenter) if is_vertical else (Qt.AlignLeft | Qt.AlignVCenter)
        )

        self._handle = DockHandle(orientation=self.orientation())
        self._handle.context_menu_requested.connect(self._show_handle_menu)
        self._handle.drag_ended.connect(self._snap_to_nearest_edge)
        column.addWidget(self._handle)

        self._buttons = {}
        for item in self.ITEMS:
            if item.key == "__sep__":
                column.addWidget(self._make_separator(is_vertical))
                continue
            btn = IconButton(item)
            btn.clicked.connect(lambda _=False, k=item.key: self.item_clicked.emit(k))
            btn.hovered_in.connect(self._on_button_hover_in)
            btn.hovered_out.connect(self._on_button_hover_out)
            cross_align = Qt.AlignHCenter if is_vertical else Qt.AlignVCenter
            column.addWidget(btn, alignment=cross_align)
            self._buttons[item.key] = btn

        self._tuck_btn = QPushButton()
        self._tuck_btn.setObjectName("dockTuckButton")
        if is_vertical:
            self._tuck_btn.setFixedSize(24, 20)
        else:
            self._tuck_btn.setFixedSize(20, 24)
        self._tuck_btn.setIconSize(QSize(14, 14))
        self._tuck_btn.setCursor(Qt.PointingHandCursor)
        self._tuck_btn.clicked.connect(self.toggle_tuck)
        column.addWidget(
            self._tuck_btn,
            alignment=Qt.AlignHCenter if is_vertical else Qt.AlignVCenter,
        )
        self._update_tuck_button()

        column.addStretch(1)
        self._apply_orientation_constraints()
        self.adjustSize()

    def _apply_orientation_constraints(self) -> None:
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        if self.orientation() == "vertical":
            self.setFixedWidth(DOCK_WIDTH)
        else:
            self.setFixedHeight(DOCK_WIDTH)

    def _make_separator(self, vertical: bool) -> QWidget:
        sep = QWidget()
        if vertical:
            sep.setFixedHeight(SEPARATOR_HEIGHT)
            sep_layout = QHBoxLayout(sep)
            sep_layout.setContentsMargins(6, 4, 6, 4)
            line = QWidget()
            line.setFixedHeight(1)
        else:
            sep.setFixedWidth(SEPARATOR_HEIGHT)
            sep_layout = QVBoxLayout(sep)
            sep_layout.setContentsMargins(4, 6, 4, 6)
            line = QWidget()
            line.setFixedWidth(1)
        line.setStyleSheet(f"background: {COLORS['border_solid']};")
        sep_layout.addWidget(line)
        return sep

    def _stylesheet(self) -> str:
        return f"""
        QWidget#dockRoot {{
            background: {COLORS['bg_primary']};
            border-radius: {RADIUS['dock']}px;
            border: 1px solid {COLORS['border_solid']};
            font-family: {FONT_FAMILY};
        }}
        QPushButton#dockIconButton {{
            background: transparent;
            border: none;
            border-radius: {RADIUS['icon_hover']}px;
        }}
        QPushButton#dockIconButton:hover {{
            background: {COLORS['bg_secondary']};
        }}
        QPushButton#dockIconButton:pressed {{
            background: {COLORS['bg_active']};
        }}
        QPushButton#dockIconButton:checked {{
            background: {COLORS['bg_active']};
        }}
        QPushButton#dockTuckButton {{
            background: transparent;
            border: none;
            border-radius: 4px;
        }}
        QPushButton#dockTuckButton:hover {{
            background: {COLORS['bg_secondary']};
        }}
        QToolTip {{
            background: {COLORS['bg_primary']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border_solid']};
            padding: 4px 6px;
            font-family: {FONT_FAMILY};
            font-size: 11px;
        }}
        """

    def set_active(self, key: str, active: bool) -> None:
        btn = self._buttons.get(key)
        if btn is not None and btn.isCheckable():
            btn.setChecked(active)

    def reset_active(self) -> None:
        for btn in self._buttons.values():
            if btn.isCheckable():
                btn.setChecked(False)

    def is_pinned(self) -> bool:
        return self._mode == self.MODE_PINNED

    def is_tucked(self) -> bool:
        return self._mode == self.MODE_TUCKED

    def set_auto_tuck_paused(self, paused: bool) -> None:
        self._auto_tuck_paused = paused
        if paused:
            self._leave_timer.stop()

    def show_anchored(self) -> None:
        if self._mode == self.MODE_TUCKED:
            self._show_strip_at_current_screen()
            return
        target = self._pinned_pos()
        self.move(target)
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()

    def anchor_to_screen_edge(self) -> None:
        self.move(self._pinned_pos())

    def toggle_tuck(self) -> None:
        if self._mode == self.MODE_PINNED:
            self._enter_tucked(animated=True)
        else:
            self._enter_pinned(animated=True)

    def peek(self) -> None:
        if self._mode == self.MODE_TUCKED:
            self._enter_peeked()

    def _show_strip_at_current_screen(self) -> None:
        pos = self._tucked_pos()
        self._strip.show_at(pos.x(), pos.y(), self._strip_cross_length(), edge=self._edge)

    def _current_screen(self):
        geom = self.geometry()
        if not geom.isEmpty():
            probe = QPoint(geom.x(), geom.y() + geom.height() // 2)
            s = QGuiApplication.screenAt(probe)
            if s is not None:
                return s
        if self.isVisible():
            s = self.screen()
            if s is not None:
                return s
        return QGuiApplication.primaryScreen()

    def _pinned_pos(self, center: bool = False) -> QPoint:
        screen = self._current_screen()
        if screen is None:
            return QPoint(0, 0)
        avail = screen.availableGeometry()

        if self._edge == "left":
            x = avail.x() + DOCK_EDGE_MARGIN
            y = self._clamp_y(avail, center)
        elif self._edge == "right":
            x = avail.x() + avail.width() - self.width() - DOCK_EDGE_MARGIN
            y = self._clamp_y(avail, center)
        elif self._edge == "top":
            x = self._clamp_x(avail, center)
            y = avail.y() + DOCK_EDGE_MARGIN
        else:
            x = self._clamp_x(avail, center)
            y = avail.y() + avail.height() - self.height() - DOCK_EDGE_MARGIN
        return QPoint(x, y)

    def _clamp_y(self, avail, center: bool) -> int:
        if center or self.y() == 0:
            return avail.y() + (avail.height() - self.height()) // 2
        return max(avail.y() + 8, min(self.y(), avail.y() + avail.height() - self.height() - 8))

    def _clamp_x(self, avail, center: bool) -> int:
        if center or self.x() == 0:
            return avail.x() + (avail.width() - self.width()) // 2
        return max(avail.x() + 8, min(self.x(), avail.x() + avail.width() - self.width() - 8))

    def _tucked_pos(self) -> QPoint:
        screen = self._current_screen()
        if screen is None:
            return QPoint(0, 0)
        avail = screen.availableGeometry()
        pinned = self._pinned_pos()

        if self._edge == "left":
            return QPoint(avail.x(), pinned.y())
        if self._edge == "right":
            return QPoint(avail.x() + avail.width() - self.TUCK_VISIBLE, pinned.y())
        if self._edge == "top":
            return QPoint(pinned.x(), avail.y())
        return QPoint(pinned.x(), avail.y() + avail.height() - self.TUCK_VISIBLE)

    def _strip_origin(self) -> QPoint:
        return self._tucked_pos()

    def _strip_cross_length(self) -> int:
        return self.height() if self.orientation() == "vertical" else self.width()

    def _detect_edge_from_position(self) -> str:
        screen = self._current_screen()
        if screen is None:
            return self._edge
        avail = screen.availableGeometry()
        cx = self.x() + self.width() // 2
        cy = self.y() + self.height() // 2
        distances = {
            "left": cx - avail.x(),
            "right": (avail.x() + avail.width()) - cx,
            "top": cy - avail.y(),
            "bottom": (avail.y() + avail.height()) - cy,
        }
        return min(distances, key=distances.get)

    def _snap_to_nearest_edge(self) -> None:
        if self._mode != self.MODE_PINNED:
            return
        new_edge = self._detect_edge_from_position()
        old_orientation = self.orientation()
        self._edge = new_edge
        new_orientation = self.orientation()

        if new_orientation != old_orientation:
            self._build_ui()
            self.move(self._pinned_pos(center=True))
        else:
            target = self._pinned_pos()
            self._snap_anim.stop()
            self._snap_anim.setStartValue(self.pos())
            self._snap_anim.setEndValue(target)
            self._snap_anim.start()

    def edge(self) -> str:
        return self._edge

    def toggle_orientation(self) -> None:
        if self._mode == self.MODE_TUCKED:
            return
        if self._mode == self.MODE_PEEKED:
            self._enter_pinned(animated=False)
        new_edge = "top" if self.orientation() == "vertical" else "right"
        old_orientation = self.orientation()
        self._edge = new_edge
        if self.orientation() != old_orientation:
            self._build_ui()
            self.adjustSize()
            self.move(self._pinned_pos(center=True))
        else:
            self.move(self._pinned_pos())
        self.show()
        self.raise_()
        self._update_tuck_button()

    def _enter_pinned(self, animated: bool) -> None:
        previous = self._mode
        self._mode = self.MODE_PINNED
        self._cursor_timer.stop()
        self._leave_timer.stop()
        self._strip.hide_animated()
        self.move(self._pinned_pos())
        if animated and previous == self.MODE_TUCKED:
            self._fade_in_dock()
        else:
            self.setWindowOpacity(1.0)
            if not self.isVisible():
                self.show()
            self.raise_()
        self._update_tuck_button()

    def _enter_tucked(self, animated: bool) -> None:
        if self._mode == self.MODE_TUCKED:
            return
        previous = self._mode
        self._mode = self.MODE_TUCKED
        self._leave_timer.stop()
        self._hover_label.hide_immediate()
        self._hovered_button = None
        strip_pos = self._strip_origin()
        self._strip.show_at(
            strip_pos.x(), strip_pos.y(), self._strip_cross_length(), edge=self._edge
        )
        if animated:
            self._fade_out_dock_then_hide()
        else:
            self.hide()
        self._update_tuck_button()
        if previous == self.MODE_PINNED:
            self.tucked.emit()

    def _enter_peeked(self) -> None:
        if self._mode != self.MODE_TUCKED:
            return
        self._mode = self.MODE_PEEKED
        self._strip.hide_animated()
        self.move(self._pinned_pos())
        self._fade_in_dock()
        self._update_tuck_button()
        self._cursor_timer.start()

    def _fade_in_dock(self) -> None:
        self._fade_anim.stop()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self.raise_()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def _fade_out_dock_then_hide(self) -> None:
        if not self.isVisible():
            return
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._after_fade_out, Qt.SingleShotConnection)
        self._fade_anim.start()

    def _after_fade_out(self) -> None:
        if self._mode == self.MODE_TUCKED:
            self.hide()

    def _on_strip_hover(self) -> None:
        if self._mode == self.MODE_TUCKED:
            self._enter_peeked()

    def _poll_cursor(self) -> None:
        if self._mode != self.MODE_PEEKED:
            return
        if self._auto_tuck_paused:
            self._leave_timer.stop()
            return
        if not self.isVisible():
            return
        cur = QCursor.pos()
        buf = self.geometry().adjusted(
            -self.PEEK_BUFFER_PX,
            -self.PEEK_BUFFER_PX,
            self.PEEK_BUFFER_PX,
            self.PEEK_BUFFER_PX,
        )
        if buf.contains(cur):
            self._leave_timer.stop()
        elif not self._leave_timer.isActive():
            self._leave_timer.start()

    def _on_peek_leave(self) -> None:
        if self._mode == self.MODE_PEEKED:
            self._cursor_timer.stop()
            self._enter_tucked(animated=True)

    def _update_tuck_button(self) -> None:
        if self._mode == self.MODE_PINNED:
            icon_map = {
                "left": "chevron_left",
                "right": "chevron_right",
                "top": "chevron_up",
                "bottom": "chevron_down",
            }
            tip = "가장자리에 숨기기"
        else:
            icon_map = {
                "left": "chevron_right",
                "right": "chevron_left",
                "top": "chevron_down",
                "bottom": "chevron_up",
            }
            tip = "도크 고정하기"
        icon_name = icon_map.get(self._edge, "chevron_right")
        self._tuck_btn.setIcon(make_icon(icon_name, size=14, color=COLORS["text_tertiary"]))
        self._tuck_btn.setToolTip(tip)

    def hideEvent(self, event) -> None:
        self._cursor_timer.stop()
        self._leave_timer.stop()
        self._label_hide_timer.stop()
        self._hover_label.hide_immediate()
        self._hovered_button = None
        super().hideEvent(event)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if self._hovered_button is not None:
            btn = self._hovered_button
            anchor, side = self._hover_anchor_for(btn)
            self._hover_label.show_for(
                btn.item.name,
                btn.item.description,
                anchor,
                side=side,
                color=btn.item.color or "#6366F1",
            )

    def _on_button_hover_in(self, btn: IconButton) -> None:
        if self._mode == self.MODE_TUCKED:
            return
        self._label_hide_timer.stop()
        self._hovered_button = btn
        anchor, side = self._hover_anchor_for(btn)
        self._hover_label.show_for(
            btn.item.name,
            btn.item.description,
            anchor,
            side=side,
            color=btn.item.color or "#6366F1",
        )

    def _hover_anchor_for(self, btn: IconButton):
        if self._edge == "left":
            return btn.mapToGlobal(QPoint(btn.width(), btn.height() // 2)), "right"
        if self._edge == "right":
            return btn.mapToGlobal(QPoint(0, btn.height() // 2)), "left"
        if self._edge == "top":
            return btn.mapToGlobal(QPoint(btn.width() // 2, btn.height())), "below"
        return btn.mapToGlobal(QPoint(btn.width() // 2, 0)), "above"

    def _on_button_hover_out(self, btn: IconButton) -> None:
        if self._hovered_button is btn:
            self._hovered_button = None
        self._label_hide_timer.start()

    def _maybe_hide_label(self) -> None:
        if self._hovered_button is None:
            self._hover_label.hide_animated()

    def _show_handle_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_stylesheet())

        if self._mode == self.MODE_PINNED:
            act_tuck = menu.addAction("가장자리에 숨기기")
            act_tuck.triggered.connect(self.toggle_tuck)
        else:
            act_pin = menu.addAction("도크 고정하기")
            act_pin.triggered.connect(self.toggle_tuck)

        act_hide = menu.addAction("도크 닫기  (트레이에서 다시 열기)")
        act_hide.triggered.connect(self.hide_requested.emit)

        menu.addSeparator()

        act_open_dir = menu.addAction("캡처 저장 폴더 열기")
        act_open_dir.triggered.connect(self._open_captures_dir)

        act_change_dir = menu.addAction("캡처 저장 경로 변경…")
        act_change_dir.triggered.connect(self._change_captures_dir)

        act_hotkeys = menu.addAction("단축키 설정…")
        act_hotkeys.triggered.connect(self.hotkey_settings_requested.emit)

        try:
            from .system_integration import get_prtsc_routes_to_snipping
            routes = get_prtsc_routes_to_snipping()
        except Exception:
            routes = None
        if routes is True:
            act_prtsc = menu.addAction("PrtSc 키로 부분캡처 (Windows 설정 변경)")
            act_prtsc.triggered.connect(self.prtsc_takeover_requested.emit)
        elif routes is False:
            act_prtsc = menu.addAction("PrtSc 키 → Windows 기본으로 되돌리기")
            act_prtsc.triggered.connect(self.prtsc_release_requested.emit)

        menu.addSeparator()

        act_about = menu.addAction("정보 / 진단…")
        act_about.triggered.connect(self.about_requested.emit)

        act_quit = menu.addAction("싹싹김치 캡처 종료")
        act_quit.triggered.connect(self.quit_requested.emit)

        menu.exec(global_pos)

    def _open_captures_dir(self) -> None:
        path = get_captures_dir()
        try:
            os.startfile(str(path))
        except Exception:
            try:
                subprocess.Popen(["explorer", str(path)])
            except Exception:
                Toast.show_text("폴더를 열 수 없어", duration_ms=1500)

    def _change_captures_dir(self) -> None:
        current = str(get_captures_dir())
        chosen = QFileDialog.getExistingDirectory(
            self,
            "캡처 저장 폴더 선택",
            current,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if not chosen:
            return
        ok = set_captures_dir(chosen)
        if ok:
            Toast.show_text(f"저장 경로 변경됨\n{chosen}", duration_ms=2000)
        else:
            Toast.show_text("허용되지 않는 경로", duration_ms=1500)

    def _menu_stylesheet(self) -> str:
        return f"""
        QMenu {{
            background: {COLORS['bg_primary']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border_solid']};
            border-radius: 8px;
            padding: 4px;
            font-family: {FONT_FAMILY};
            font-size: 12px;
        }}
        QMenu::item {{
            padding: 6px 18px 6px 12px;
            border-radius: 4px;
            margin: 1px 2px;
        }}
        QMenu::item:selected {{
            background: {COLORS['bg_secondary']};
            color: {COLORS['text_primary']};
        }}
        QMenu::separator {{
            height: 1px;
            background: {COLORS['border_solid']};
            margin: 4px 6px;
        }}
        """
