from typing import List

from PySide6.QtCore import (
    QEasingCurve,
    QMimeData,
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
    QDrag,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .icons import make_icon, render_pixmap
from .tokens import (
    ANIM_PANEL_MS,
    COLORS,
    FEEDBACK_DURATION_MS,
    FONT_FAMILY,
    PALETTE_GRID_COLS,
    PALETTE_GRID_ROWS,
    PALETTE_MAX_VISIBLE,
    PANEL_GAP,
    PANEL_WIDTH,
    RADIUS,
    SWATCH_SIZE,
)


class Swatch(QWidget):
    clicked = Signal(str)
    drag_outside = Signal(str)

    def __init__(self, hex_value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hex = hex_value
        self._hovered = False
        self._press_pos: QPoint | None = None
        self._drag_started = False
        self.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)

    def set_hex(self, hex_value: str) -> None:
        self._hex = hex_value
        self.setVisible(bool(hex_value))
        self.update()

    def hex_value(self) -> str:
        return self._hex

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._hex:
            self._press_pos = event.position().toPoint()
            self._drag_started = False

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._press_pos is None
            or self._drag_started
            or not (event.buttons() & Qt.LeftButton)
        ):
            return
        if (event.position().toPoint() - self._press_pos).manhattanLength() < 10:
            return
        self._drag_started = True
        self._run_drag()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        if not self._drag_started and self._press_pos is not None:
            if (event.position().toPoint() - self._press_pos).manhattanLength() < 6:
                self.clicked.emit(self._hex)
        self._press_pos = None
        self._drag_started = False

    def _run_drag(self) -> None:
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self._hex)
        drag.setMimeData(mime)

        pix = QPixmap(self.size())
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing, True)
        self._paint_swatch(p, opacity=0.85)
        p.end()
        drag.setPixmap(pix)
        drag.setHotSpot(QPoint(self.width() // 2, self.height() // 2))

        drag.exec(Qt.MoveAction | Qt.CopyAction)

        end_pos = QCursor.pos()
        top = self.window()
        if top is not None and not top.geometry().contains(end_pos):
            self.drag_outside.emit(self._hex)

    def paintEvent(self, event) -> None:
        if not self._hex:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        self._paint_swatch(p)

    def _paint_swatch(self, p: QPainter, opacity: float = 1.0) -> None:
        rect = self.rect().adjusted(2, 2, -2, -2)
        if self._hovered:
            rect = rect.adjusted(-1, -1, 1, 1)

        p.setOpacity(opacity)
        color = QColor(self._hex) if self._hex else QColor("#FFFFFF")
        p.setBrush(color)
        if self._hovered:
            p.setPen(QPen(QColor(0, 0, 0, 60), 1))
        else:
            p.setPen(QPen(QColor(0, 0, 0, 25), 1))
        p.drawRoundedRect(rect, RADIUS["swatch"], RADIUS["swatch"])
        p.setOpacity(1.0)


class PalettePanel(QWidget):
    swatch_clicked = Signal(str)
    swatch_removed = Signal(str)
    export_requested = Signal()
    collapse_requested = Signal()

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
        self.setFixedWidth(PANEL_WIDTH)

        self._build_ui()

        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(ANIM_PANEL_MS)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(ANIM_PANEL_MS)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)

        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(self._reset_footer)

        self._target_geom: QRect | None = None

    def _build_ui(self) -> None:
        self._root = QWidget(self)
        self._root.setObjectName("panelRoot")
        self._root.setStyleSheet(self._stylesheet())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._root)

        layout = QVBoxLayout(self._root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 0)
        header.setSpacing(4)

        title = QLabel("Palette")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch(1)

        self._collapse_btn = QPushButton()
        self._collapse_btn.setObjectName("iconButton")
        self._collapse_btn.setFixedSize(20, 20)
        self._collapse_btn.setIcon(make_icon("close", size=18, color=COLORS["text_secondary"]))
        self._collapse_btn.setIconSize(QSize(12, 12))
        self._collapse_btn.setCursor(Qt.PointingHandCursor)
        self._collapse_btn.setToolTip("팔레트 닫기")
        self._collapse_btn.clicked.connect(self.collapse_requested.emit)
        header.addWidget(self._collapse_btn)

        layout.addLayout(header)

        grid_wrap = QWidget()
        grid = QGridLayout(grid_wrap)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self._swatches: List[Swatch] = []
        for i in range(PALETTE_MAX_VISIBLE):
            sw = Swatch()
            sw.clicked.connect(self._on_swatch_clicked)
            sw.drag_outside.connect(self._on_swatch_drag_outside)
            r = i // PALETTE_GRID_COLS
            c = i % PALETTE_GRID_COLS
            grid.addWidget(sw, r, c, alignment=Qt.AlignCenter)
            self._swatches.append(sw)

        for r in range(PALETTE_GRID_ROWS):
            grid.setRowMinimumHeight(r, SWATCH_SIZE + 2)
        for c in range(PALETTE_GRID_COLS):
            grid.setColumnMinimumWidth(c, SWATCH_SIZE + 2)

        layout.addWidget(grid_wrap, 1)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {COLORS['border_solid']};")
        layout.addWidget(sep)

        self._footer = QWidget()
        footer_layout = QHBoxLayout(self._footer)
        footer_layout.setContentsMargins(0, 2, 0, 0)
        footer_layout.setSpacing(0)

        self._export_btn = QPushButton(" Export")
        self._export_btn.setObjectName("exportButton")
        self._export_btn.setIcon(make_icon("download", size=18, color=COLORS["text_secondary"]))
        self._export_btn.setIconSize(QSize(14, 14))
        self._export_btn.setCursor(Qt.PointingHandCursor)
        self._export_btn.clicked.connect(self.export_requested.emit)
        footer_layout.addWidget(self._export_btn)

        self._feedback_label = QLabel("")
        self._feedback_label.setObjectName("feedbackLabel")
        self._feedback_label.setAlignment(Qt.AlignCenter)
        self._feedback_label.hide()
        footer_layout.addWidget(self._feedback_label)

        layout.addWidget(self._footer)

    def _stylesheet(self) -> str:
        return f"""
        QWidget#panelRoot {{
            background: {COLORS['bg_primary']};
            border-radius: {RADIUS['panel']}px;
            border: 1px solid {COLORS['border_solid']};
        }}
        QLabel#panelTitle {{
            color: {COLORS['text_secondary']};
            font-family: {FONT_FAMILY};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.3px;
            padding: 2px;
        }}
        QPushButton#iconButton {{
            background: transparent;
            border: none;
            border-radius: 4px;
        }}
        QPushButton#iconButton:hover {{
            background: {COLORS['bg_secondary']};
        }}
        QPushButton#exportButton {{
            background: transparent;
            color: {COLORS['text_secondary']};
            border: none;
            border-radius: 6px;
            padding: 6px 10px;
            text-align: center;
            font-family: {FONT_FAMILY};
            font-size: 11px;
        }}
        QPushButton#exportButton:hover {{
            background: {COLORS['bg_secondary']};
            color: {COLORS['text_primary']};
        }}
        QLabel#feedbackLabel {{
            color: {COLORS['text_primary']};
            font-family: {FONT_FAMILY};
            font-size: 11px;
            font-weight: 600;
            padding: 6px 0;
        }}
        """

    def height_for(self, dock_height: int) -> int:
        return dock_height

    def set_palette(self, colors: List[str]) -> None:
        visible = colors[:PALETTE_MAX_VISIBLE]
        for i, sw in enumerate(self._swatches):
            sw.set_hex(visible[i] if i < len(visible) else "")

    def show_at(
        self,
        target_geom: QRect,
        animated: bool = True,
        from_side: str = "right",
    ) -> None:
        self._target_geom = target_geom
        self._from_side = from_side
        if not animated:
            self.setGeometry(target_geom)
            self.setWindowOpacity(1.0)
            self.show()
            return

        start_geom = QRect(target_geom)
        if from_side == "right":
            start_geom.moveLeft(target_geom.x() + 24)
        elif from_side == "left":
            start_geom.moveLeft(target_geom.x() - 24)
        elif from_side == "top":
            start_geom.moveTop(target_geom.y() - 24)
        elif from_side == "bottom":
            start_geom.moveTop(target_geom.y() + 24)

        self.setGeometry(start_geom)
        self.setWindowOpacity(0.0)
        self.show()

        self._anim.stop()
        self._anim.setStartValue(start_geom)
        self._anim.setEndValue(target_geom)
        self._anim.start()

        self._fade.stop()
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def hide_animated(self) -> None:
        if not self.isVisible():
            return
        current = self.geometry()
        target = QRect(current)
        from_side = getattr(self, "_from_side", "right")
        if from_side == "right":
            target.moveLeft(current.x() + 24)
        elif from_side == "left":
            target.moveLeft(current.x() - 24)
        elif from_side == "top":
            target.moveTop(current.y() - 24)
        elif from_side == "bottom":
            target.moveTop(current.y() + 24)

        self._anim.stop()
        self._anim.setStartValue(current)
        self._anim.setEndValue(target)
        self._anim.start()

        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._after_hide, Qt.SingleShotConnection)
        self._fade.start()

    def _after_hide(self) -> None:
        self.hide()

    def _on_swatch_clicked(self, hex_value: str) -> None:
        if not hex_value:
            return
        self.swatch_clicked.emit(hex_value)
        self._show_feedback(f"{hex_value} · copied")

    def _on_swatch_drag_outside(self, hex_value: str) -> None:
        if not hex_value:
            return
        self.swatch_removed.emit(hex_value)

    def _show_feedback(self, text: str) -> None:
        self._feedback_label.setText(text)
        self._export_btn.hide()
        self._feedback_label.show()
        self._feedback_timer.start(FEEDBACK_DURATION_MS)

    def _reset_footer(self) -> None:
        self._feedback_label.hide()
        self._export_btn.show()
