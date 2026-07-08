from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

from .capture_core import active_screen_info, grab_qimage
from .coords import screen_physical_geometry
from .tokens import FONT_FAMILY


DIM_COLOR = QColor(0, 0, 0, 90)


class RegionCaptureOverlay(QWidget):
    """드래그 영역 선택 오버레이 (커서가 있는 모니터 1개만 덮음).

    freeze 모드(부분 캡처/OCR): begin() 시점에 화면을 얼려 배경으로 깔고,
    확정 시 얼린 이미지에서 크롭한다 → hide/컴포지터 타이밍 레이스 없음,
    드래그 중 화면이 변해도 '열었을 때 본 그대로' 캡처됨.
    live 모드(녹화/GIF/스크롤 영역 선택): rect만 emit하므로 얼리지 않고
    반투명 딤 + 구멍 방식으로 라이브 화면을 보여준다.
    """

    captured = Signal(QImage)
    region_selected = Signal(QRect, float)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self._screen = None
        self._virtual_geom, self._dpr = QRect(), 1.0
        self._screen, self._virtual_geom, self._dpr = active_screen_info()
        self.setGeometry(self._virtual_geom)
        self._start: QPoint | None = None
        self._end: QPoint | None = None
        self._cursor_pos = QPoint(0, 0)
        self._frozen: QImage | None = None
        self._frozen_pm = QPixmap()

    def begin(self, freeze: bool = True) -> None:
        self._start = None
        self._end = None
        self._screen, self._virtual_geom, self._dpr = active_screen_info()
        self.setGeometry(self._virtual_geom)
        self._frozen = None
        self._frozen_pm = QPixmap()
        if freeze and self._screen is not None:
            phys = screen_physical_geometry(self._screen)
            img = grab_qimage(
                {
                    "left": phys.x(),
                    "top": phys.y(),
                    "width": phys.width(),
                    "height": phys.height(),
                }
            )
            # grab 실패 시 라이브 모드로 자연 폴백 (기존 동작)
            if img is not None and not img.isNull():
                self._frozen = img
                pm = QPixmap.fromImage(img)
                pm.setDevicePixelRatio(self._dpr)
                self._frozen_pm = pm
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.OtherFocusReason)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.grabKeyboard()
        self.grabMouse()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.releaseKeyboard()
        self.releaseMouse()
        # 얼린 프레임(1080p 기준 ~8MB)은 표시 중에만 유지
        self._frozen = None
        self._frozen_pm = QPixmap()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self.update()

    def mouseMoveEvent(self, event) -> None:
        self._cursor_pos = event.position().toPoint()
        if self._start is not None:
            self._end = self._cursor_pos
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or self._start is None:
            return
        self._end = event.position().toPoint()
        rect = self._selection_rect()
        frozen = self._frozen  # hide()가 프레임을 비우기 전에 잡아둔다
        self.hide()
        if rect.width() >= 2 and rect.height() >= 2:
            global_rect = QRect(
                self._virtual_geom.x() + rect.x(),
                self._virtual_geom.y() + rect.y(),
                rect.width(),
                rect.height(),
            )
            self.region_selected.emit(global_rect, self._dpr)
            if frozen is not None:
                image = self._crop_frozen(frozen, rect)
            else:
                image = self._grab(rect)
            self.captured.emit(image)
        else:
            self.cancelled.emit()

    def _selection_rect(self) -> QRect:
        if self._start is None or self._end is None:
            return QRect()
        return QRect(self._start, self._end).normalized()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        if not self._frozen_pm.isNull():
            painter.drawPixmap(0, 0, self._frozen_pm)

        if self._start is not None and self._end is not None:
            rect = self._selection_rect()
            if self._frozen_pm.isNull():
                # 라이브 모드: 전체 딤 후 선택 영역을 투명 구멍으로
                painter.fillRect(self.rect(), DIM_COLOR)
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.fillRect(rect, Qt.transparent)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            else:
                # frozen 모드: 선택 영역 바깥 4개 조각만 딤
                # (얼린 픽스맵 부분 재드로우보다 좌표 모호성이 없음)
                self._dim_outside(painter, rect)

            pen = QPen(QColor(255, 255, 255, 235), 1)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

            self._draw_size_badge(painter, rect)
        else:
            painter.fillRect(self.rect(), DIM_COLOR)
            self._draw_hint(painter)

    def _dim_outside(self, painter: QPainter, sel: QRect) -> None:
        full = self.rect()
        painter.setPen(Qt.NoPen)
        painter.setBrush(DIM_COLOR)
        top = QRect(full.x(), full.y(), full.width(), sel.y() - full.y())
        bottom = QRect(
            full.x(), sel.y() + sel.height(),
            full.width(), full.y() + full.height() - (sel.y() + sel.height()),
        )
        left = QRect(full.x(), sel.y(), sel.x() - full.x(), sel.height())
        right = QRect(
            sel.x() + sel.width(), sel.y(),
            full.x() + full.width() - (sel.x() + sel.width()), sel.height(),
        )
        for r in (top, bottom, left, right):
            if r.width() > 0 and r.height() > 0:
                painter.fillRect(r, DIM_COLOR)

    def _draw_hint(self, painter: QPainter) -> None:
        text = "Drag to capture · Esc to cancel"
        font = QFont()
        font.setFamily(FONT_FAMILY.split(",")[0].strip().strip('"'))
        font.setPixelSize(13)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        w = metrics.horizontalAdvance(text) + 24
        h = 28
        x = (self.width() - w) // 2
        y = self.height() - h - 64
        bg = QRect(x, y, w, h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawRoundedRect(bg, 8, 8)
        painter.setPen(QColor(26, 26, 26))
        painter.drawText(bg, Qt.AlignCenter, text)

    def _draw_size_badge(self, painter: QPainter, rect: QRect) -> None:
        text = f"{rect.width()} × {rect.height()}"
        font = QFont()
        font.setFamily(FONT_FAMILY.split(",")[0].strip().strip('"'))
        font.setPixelSize(11)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        pad_x, pad_y = 6, 3
        w = metrics.horizontalAdvance(text) + pad_x * 2
        h = metrics.height() + pad_y * 2

        bx = rect.x()
        by = rect.y() - h - 4
        if by < self.rect().y() + 2:
            by = rect.y() + 4
            bx = rect.x() + 4
        badge = QRect(bx, by, w, h)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawRoundedRect(badge, 4, 4)
        painter.setPen(QColor(26, 26, 26))
        painter.drawText(badge, Qt.AlignCenter, text)

    def _crop_frozen(self, frozen: QImage, local_rect: QRect) -> QImage:
        """얼린 프레임(활성 화면의 물리 픽셀)에서 논리 선택 영역을 크롭.

        오버레이와 얼린 프레임이 같은 화면을 덮으므로
        로컬 논리 좌표 × dpr = 프레임 내 물리 좌표 (한 화면 안에선 정확)."""
        dpr = self._dpr
        phys = QRect(
            int(round(local_rect.x() * dpr)),
            int(round(local_rect.y() * dpr)),
            max(1, int(round(local_rect.width() * dpr))),
            max(1, int(round(local_rect.height() * dpr))),
        ).intersected(frozen.rect())
        if phys.isEmpty():
            return QImage()
        return frozen.copy(phys)

    def _grab(self, qrect: QRect) -> QImage:
        """라이브 폴백: 화면에서 직접 grab (frozen 실패 시에만)."""
        if self._screen is not None:
            origin = screen_physical_geometry(self._screen).topLeft()
        else:
            origin = QPoint(
                int(round(self._virtual_geom.x() * self._dpr)),
                int(round(self._virtual_geom.y() * self._dpr)),
            )
        dpr = self._dpr
        region = {
            "left": origin.x() + int(round(qrect.x() * dpr)),
            "top": origin.y() + int(round(qrect.y() * dpr)),
            "width": max(1, int(round(qrect.width() * dpr))),
            "height": max(1, int(round(qrect.height() * dpr))),
        }
        return grab_qimage(region) or QImage()
