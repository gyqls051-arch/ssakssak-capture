from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from .tokens import COLORS


_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
    "{body}</svg>"
)


_ICONS = {
    "full": (
        '<path d="M5 9V6a1 1 0 0 1 1-1h3"/>'
        '<path d="M19 9V6a1 1 0 0 0-1-1h-3"/>'
        '<path d="M5 15v3a1 1 0 0 0 1 1h3"/>'
        '<path d="M19 15v3a1 1 0 0 1-1 1h-3"/>'
    ),
    "region": (
        '<rect x="4.5" y="4.5" width="15" height="15" rx="1.5" stroke-dasharray="3 2.5"/>'
    ),
    "window": (
        '<rect x="3.5" y="5" width="17" height="14" rx="2"/>'
        '<line x1="3.5" y1="9" x2="20.5" y2="9"/>'
        '<circle cx="6.5" cy="7" r="0.4" fill="{color}" stroke="none"/>'
        '<circle cx="8.5" cy="7" r="0.4" fill="{color}" stroke="none"/>'
    ),
    "scroll": (
        '<rect x="6" y="3.5" width="12" height="17" rx="2"/>'
        '<path d="M9.5 8.5L12 6l2.5 2.5"/>'
        '<path d="M9.5 15.5L12 18l2.5-2.5"/>'
    ),
    "color": (
        '<path d="M13.5 4.5l6 6"/>'
        '<path d="M16 7l-9 9-2.5.5L5 14l9-9z"/>'
        '<path d="M14.5 5.5a2 2 0 1 1 4 4"/>'
    ),
    "distance": (
        '<rect x="2" y="9" width="20" height="6" rx="1" transform="rotate(-30 12 12)"/>'
        '<path d="M8.6 10.7l0.8 1.4"/>'
        '<path d="M11.2 9.2l0.8 1.4"/>'
        '<path d="M13.8 7.7l0.8 1.4"/>'
        '<path d="M16.4 6.2l0.8 1.4"/>'
    ),
    "ocr": (
        '<path d="M6 8V6.5h12V8"/>'
        '<path d="M12 6.5v13"/>'
        '<path d="M9 19.5h6"/>'
    ),
    "record": (
        '<circle cx="12" cy="12" r="8"/>'
        '<circle cx="12" cy="12" r="3.5" fill="{color}" stroke="none"/>'
    ),
    "gif": (
        '<rect x="3.5" y="6" width="17" height="12" rx="2"/>'
        '<path d="M9 11h-1.5a1.5 1.5 0 1 0 0 3H9v-1.5"/>'
        '<path d="M12 10.5v3"/>'
        '<path d="M15 13.5V11h2.2"/>'
        '<path d="M15 12.5h1.6"/>'
    ),
    "stop": (
        '<rect x="6" y="6" width="12" height="12" rx="1.5" fill="{color}" stroke="none"/>'
    ),
    "chevron_left": (
        '<path d="M14 6l-6 6 6 6"/>'
    ),
    "chevron_right": (
        '<path d="M10 6l6 6-6 6"/>'
    ),
    "chevron_up": (
        '<path d="M6 14l6-6 6 6"/>'
    ),
    "chevron_down": (
        '<path d="M6 10l6 6 6-6"/>'
    ),
    "layout": (
        '<path d="M20 12a8 8 0 1 1-2.6-5.9"/>'
        '<path d="M20 4v4h-4"/>'
    ),
    "close": (
        '<path d="M6 6l12 12"/>'
        '<path d="M18 6l-12 12"/>'
    ),
    "download": (
        '<path d="M12 4v12"/>'
        '<path d="M7 11l5 5 5-5"/>'
        '<path d="M5 20h14"/>'
    ),
    "app": (
        '<rect x="3" y="3" width="18" height="18" rx="4" fill="{color}" stroke="none"/>'
        '<path d="M8 8h8v8H8z" stroke="#FFFFFF" stroke-width="1.8" fill="none"/>'
    ),
}


def _svg(name: str, color: str) -> bytes:
    body = _ICONS[name].format(color=color)
    return _SVG_TEMPLATE.format(color=color, body=body).encode("utf-8")


def render_pixmap(name: str, size: int = 24, color: str = None) -> QPixmap:
    if color is None:
        color = COLORS["text_primary"]
    svg = _svg(name, color)
    renderer = QSvgRenderer(QByteArray(svg))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    return pixmap


def make_icon(name: str, size: int = 24, color: str = None) -> QIcon:
    return QIcon(render_pixmap(name, size=size, color=color))


def app_icon(size: int = 64) -> QIcon:
    return make_icon("app", size=size, color="#1A1A1A")
