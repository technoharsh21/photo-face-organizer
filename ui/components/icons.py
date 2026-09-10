"""
Vector SVG Icon Library & Helper for Photo Face AI.

Provides crisp, high-DPI vector icons rendered on-demand with custom colors and sizes.
Eliminates missing font glyphs / emoji discrepancies across Linux and Windows desktop platforms.
"""

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

SVG_TEMPLATES: dict[str, str] = {
    # Zoom controls
    "zoom_in": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="11" cy="11" r="7.5"/>'
        '<line x1="21" y1="21" x2="16.5" y2="16.5"/>'
        '<line x1="11" y1="8" x2="11" y2="14"/>'
        '<line x1="8" y1="11" x2="14" y2="11"/>'
        '</svg>'
    ),
    "zoom_out": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="11" cy="11" r="7.5"/>'
        '<line x1="21" y1="21" x2="16.5" y2="16.5"/>'
        '<line x1="8" y1="11" x2="14" y2="11"/>'
        '</svg>'
    ),
    "zoom_fit": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>'
        '</svg>'
    ),
    "zoom_actual": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="18" height="18" rx="3" ry="3"/>'
        '<path d="M8 9.5l1.5-1.5v8"/>'
        '<circle cx="12" cy="11" r="0.75" fill="{color}"/>'
        '<circle cx="12" cy="14" r="0.75" fill="{color}"/>'
        '<path d="M14.5 9.5l1.5-1.5v8"/>'
        '</svg>'
    ),
    # Rotation controls
    "rotate_cw": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>'
        '<polyline points="21 3 21 8 16 8"/>'
        '</svg>'
    ),
    "rotate_ccw": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>'
        '<polyline points="3 3 3 8 8 8"/>'
        '</svg>'
    ),
    # Navigation and actions
    "close": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="18" y1="6" x2="6" y2="18"/>'
        '<line x1="6" y1="6" x2="18" y2="18"/>'
        '</svg>'
    ),
    "chevron_left": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="15 18 9 12 15 6"/>'
        '</svg>'
    ),
    "chevron_right": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="9 18 15 12 9 6"/>'
        '</svg>'
    ),
    "folder_open": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
        '</svg>'
    ),
    "download": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="7 10 12 15 17 10"/>'
        '<line x1="12" y1="15" x2="12" y2="3"/>'
        '</svg>'
    ),
    "save": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
        '<polyline points="17 21 17 13 7 13 7 21"/>'
        '<polyline points="7 3 7 8 15 8"/>'
        '</svg>'
    ),
    "search": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="11" cy="11" r="7.5"/>'
        '<line x1="21" y1="21" x2="16.5" y2="16.5"/>'
        '</svg>'
    ),
    "check_square": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="9 11 12 14 22 4"/>'
        '<path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'
        '</svg>'
    ),
    "square": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>'
        '</svg>'
    ),
    "pause": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="6" y="4" width="4" height="16" fill="{color}"/>'
        '<rect x="14" y="4" width="4" height="16" fill="{color}"/>'
        '</svg>'
    ),
    "play": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polygon points="5 3 19 12 5 21 5 3" fill="{color}"/>'
        '</svg>'
    ),
    "stop_circle": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="9"/>'
        '<rect x="9" y="9" width="6" height="6" fill="{color}"/>'
        '</svg>'
    ),
    "refresh": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="23 4 23 10 17 10"/>'
        '<polyline points="1 20 1 14 7 14"/>'
        '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>'
        '</svg>'
    ),
    "trash": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="3 6 5 6 21 6"/>'
        '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '</svg>'
    ),
    "plus": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="12" y1="5" x2="12" y2="19"/>'
        '<line x1="5" y1="12" x2="19" y2="12"/>'
        '</svg>'
    ),
    "camera": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>'
        '<circle cx="12" cy="13" r="4"/>'
        '</svg>'
    ),
    "target": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<circle cx="12" cy="12" r="6"/>'
        '<circle cx="12" cy="12" r="2"/>'
        '</svg>'
    ),
}

_ICON_CACHE: dict[tuple[str, str, str, int], QIcon] = {}
_PIXMAP_CACHE: dict[tuple[str, str, int], QPixmap] = {}


def get_pixmap(name: str, color: str = "#ffffff", size: int = 24) -> QPixmap:
    """Render a crisp vector SVG pixmap with anti-aliasing."""
    cache_key = (name, color, size)
    if cache_key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[cache_key]

    template = SVG_TEMPLATES.get(name)
    if not template:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        return pix

    svg_str = template.format(color=color)
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    if renderer.isValid():
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        renderer.render(painter)
        painter.end()

    _PIXMAP_CACHE[cache_key] = pix
    return pix


def get_icon(
    name: str,
    color: str = "#ffffff",
    disabled_color: str = "#64748b",
    size: int = 24,
) -> QIcon:
    """
    Return a multi-state QIcon for standard and disabled button states.
    """
    cache_key = (name, color, disabled_color, size)
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    template = SVG_TEMPLATES.get(name)
    if not template:
        return QIcon()

    pix_normal = get_pixmap(name, color=color, size=size)
    pix_disabled = get_pixmap(name, color=disabled_color, size=size)

    icon = QIcon()
    icon.addPixmap(pix_normal, QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(pix_disabled, QIcon.Mode.Disabled, QIcon.State.Off)

    _ICON_CACHE[cache_key] = icon
    return icon


def save_svg_assets():
    """Export all SVG templates to ui/assets/icons/ directory."""
    assets_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for name, template in SVG_TEMPLATES.items():
        svg_content = template.format(color="#ffffff")
        out_file = assets_dir / f"{name}.svg"
        out_file.write_text(svg_content, encoding="utf-8")
