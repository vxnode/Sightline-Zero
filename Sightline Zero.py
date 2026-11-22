import sys
import os
import re
import json
import html
import math
import shutil
import ctypes

from PySide6.QtCore import (
    Qt, QPointF, QRectF, QTimer, Signal, QVariantAnimation,
    QPropertyAnimation, QEasingCurve, QUrl,
)
from PySide6.QtGui import (
    QColor, QPainter, QPen, QPixmap, QImage, QIcon, QFont, QFontDatabase,
    QLinearGradient, QRadialGradient, QConicalGradient, QPainterPath,
    QFontMetrics, QShortcut, QKeySequence, QPolygonF, QPalette,
    QDesktopServices,
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QLabel, QPushButton, QAbstractButton,
    QSlider, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QFileDialog, QLineEdit, QMenu, QMessageBox, QColorDialog,
    QGraphicsOpacityEffect, QSizeGrip,
)
from PIL import Image as PILImage, ImageFilter, ImageChops


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CROSSHAIR_DIR = os.path.join(BASE_DIR, "crosshairs")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

DEFAULT_CONFIG = {
    "last_crosshair": "",
    "scale": 1.0,
    "opacity": 1.0,
    "fade": 0.0,
    "offset_x": 0,
    "offset_y": 0,
    "tint": "",
    "auto_apply": True,
    "show_guides": True,
    "bg_mode": 0,
}


class C:
    SHELL_TOP = "#10121A"
    SHELL_BOT = "#0A0B0F"
    CARD = "#12141A"
    INSET = "#0D0F14"
    BORDER = "#1F232D"
    BORDER_HI = "#2E3444"
    TEXT = "#ECEEF4"
    TEXT_SOFT = "#C9CDD8"
    MUTED = "#8D93A3"
    FAINT = "#596072"
    AMBER = "#FFB020"
    AMBER_DEEP = "#FF7A29"
    GREEN = "#35D68A"
    RED = "#FF5C6C"


def qc(hex_color, alpha=255):
    c = QColor(hex_color)
    c.setAlpha(alpha)
    return c


def mix(c1, c2, t):
    a, b = QColor(c1), QColor(c2)
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
    )


def ui_font(px, weight=QFont.Weight.Medium):
    f = QFont()
    f.setPixelSize(px)
    f.setWeight(weight)
    return f


def screen_dpr():
    s = QApplication.primaryScreen()
    return float(s.devicePixelRatio()) if s else 1.0


STYLESHEET = """
* { outline: none; }
QToolTip {
    background: #1A1D26; color: #ECEEF4; border: 1px solid #2E3444;
    padding: 6px 9px; border-radius: 6px; font-size: 11px;
}
QLabel { color: #ECEEF4; background: transparent; }
QFrame#Card { background: #12141A; border: 1px solid #1F232D; border-radius: 14px; }
QFrame#Divider { background: #1C1F27; border: none; max-height: 1px; min-height: 1px; }
QLabel#Brand { font-size: 15px; font-weight: 700; color: #F6F7FA; }
QLabel#ProBadge {
    color: #FFB020; border: 1px solid rgba(255,176,32,0.45); border-radius: 4px;
    padding: 0px 7px; font-size: 10px; font-weight: 700;
}
QLabel#CardTitle { font-size: 14px; font-weight: 600; color: #F6F7FA; }
QLabel#Hint { color: #8D93A3; font-size: 11px; }
QLabel#SectionLabel { color: #8D93A3; font-size: 11px; font-weight: 600; }
QLabel#RowTitle { color: #C9CDD8; font-size: 12px; font-weight: 500; }
QLabel#RowSub { color: #6F7586; font-size: 11px; }
QLabel#SelName { font-size: 13px; font-weight: 600; color: #F6F7FA; }
QLabel#ValuePill {
    background: #0D0F14; border: 1px solid #1F232D; border-radius: 6px;
    padding: 2px 8px; color: #ECEEF4; font-size: 11px; font-weight: 600;
}
QLabel#Toast {
    background: #1A1D26; border: 1px solid #2E3444; border-radius: 10px;
    padding: 10px 16px; color: #ECEEF4; font-size: 12px; font-weight: 600;
}
QLineEdit#Search {
    background: #0D0F14; border: 1px solid #1F232D; border-radius: 9px;
    padding: 0 12px; color: #ECEEF4; min-height: 32px; font-size: 12px;
    selection-background-color: #FFB020; selection-color: #1A1204;
}
QLineEdit#Search:focus { border-color: rgba(255,176,32,0.6); }
QPushButton#Primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FFC24A, stop:1 #FF8A2B);
    color: #1A1204; border: none; border-radius: 11px;
    font-size: 13px; font-weight: 700;
}
QPushButton#Primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FFD070, stop:1 #FF9A45);
}
QPushButton#Primary:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E8A83F, stop:1 #E87A22);
}
QPushButton#Primary[live="true"] {
    background: #0F2219; color: #35D68A; border: 1px solid rgba(53,214,138,0.5);
}
QPushButton#Primary[live="true"]:hover { background: #143023; }
QPushButton#Accent {
    background: rgba(255,176,32,0.12); border: 1px solid rgba(255,176,32,0.4);
    color: #FFB020; border-radius: 9px; padding: 0 14px; min-height: 32px;
    font-weight: 600; font-size: 12px;
}
QPushButton#Accent:hover { background: rgba(255,176,32,0.22); }
QPushButton#Ghost {
    background: transparent; color: #8D93A3; border: none;
    font-size: 11px; font-weight: 600; padding: 4px 6px;
}
QPushButton#Ghost:hover { color: #FFB020; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #2A2F3C; border-radius: 3px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3A4152; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QSizeGrip { background: transparent; width: 14px; height: 14px; }
QMenu {
    background: #161922; border: 1px solid #2E3444; border-radius: 10px;
    padding: 6px; color: #ECEEF4; font-size: 12px;
}
QMenu::item { padding: 7px 22px 7px 14px; border-radius: 6px; }
QMenu::item:selected { background: rgba(255,176,32,0.16); color: #FFB020; }
QMenu::separator { height: 1px; background: #232733; margin: 5px 8px; }
QMessageBox, QColorDialog { background: #12141A; }
QMessageBox QPushButton, QColorDialog QPushButton {
    background: #1A1D26; border: 1px solid #262B38; border-radius: 8px;
    padding: 6px 16px; color: #ECEEF4; min-width: 70px; font-weight: 600;
}
QMessageBox QPushButton:hover, QColorDialog QPushButton:hover { border-color: #FFB020; }
"""


PRESETS = {
    "classic-cross": [
        ("line", 64, 32, 64, 56, 3), ("line", 64, 72, 64, 96, 3),
        ("line", 32, 64, 56, 64, 3), ("line", 72, 64, 96, 64, 3),
    ],
    "open-cross": [
        ("line", 64, 26, 64, 50, 3.5), ("line", 64, 78, 64, 102, 3.5),
        ("line", 26, 64, 50, 64, 3.5), ("line", 78, 64, 102, 64, 3.5),
        ("dot", 64, 64, 3),
    ],
    "hairline": [
        ("line", 64, 18, 64, 58, 1.6), ("line", 64, 70, 64, 110, 1.6),
        ("line", 18, 64, 58, 64, 1.6), ("line", 70, 64, 110, 64, 1.6),
    ],
    "precision-dot": [("dot", 64, 64, 4.5)],
    "ring": [("ring", 64, 64, 22, 3)],
    "ring-dot": [("ring", 64, 64, 20, 2.5), ("dot", 64, 64, 3)],
    "crossed-ring": [
        ("ring", 64, 64, 26, 2),
        ("line", 64, 30, 64, 50, 2.5), ("line", 64, 78, 64, 98, 2.5),
        ("line", 30, 64, 50, 64, 2.5), ("line", 78, 64, 98, 64, 2.5),
        ("dot", 64, 64, 2),
    ],
    "arcs": [
        ("arc", 64, 64, 24, 20, 50, 3), ("arc", 64, 64, 24, 110, 50, 3),
        ("arc", 64, 64, 24, 200, 50, 3), ("arc", 64, 64, 24, 290, 50, 3),
    ],
    "tee": [
        ("line", 36, 64, 58, 64, 3), ("line", 70, 64, 92, 64, 3),
        ("line", 64, 70, 64, 92, 3),
    ],
    "chevron": [("poly", [(42, 82), (64, 58), (86, 82)], 4)],
    "diamond": [("poly", [(64, 38), (90, 64), (64, 90), (38, 64), (64, 38)], 2.5)],
    "delta": [
        ("poly", [(64, 42), (88, 86), (40, 86), (64, 42)], 2.5), ("dot", 64, 72, 2.5),
    ],
    "brackets": [
        ("poly", [(38, 52), (38, 38), (52, 38)], 3),
        ("poly", [(76, 38), (90, 38), (90, 52)], 3),
        ("poly", [(90, 76), (90, 90), (76, 90)], 3),
        ("poly", [(52, 90), (38, 90), (38, 76)], 3),
    ],
}


def _paint_op(p, op, col, ow):
    kind = op[0]
    p.setBrush(Qt.BrushStyle.NoBrush)
    if kind == "line":
        _, x1, y1, x2, y2, w = op
        if ow:
            dx, dy = x2 - x1, y2 - y1
            ln = math.hypot(dx, dy) or 1.0
            ux, uy = dx / ln * ow / 2, dy / ln * ow / 2
            x1, y1, x2, y2 = x1 - ux, y1 - uy, x2 + ux, y2 + uy
        p.setPen(QPen(col, w + ow, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    elif kind == "dot":
        _, cx, cy, r = op
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx, cy), r + ow / 2, r + ow / 2)
    elif kind == "ring":
        _, cx, cy, r, w = op
        p.setPen(QPen(col, w + ow))
        p.drawEllipse(QPointF(cx, cy), r, r)
    elif kind == "poly":
        _, pts, w = op
        pen = QPen(col, w + ow, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap,
                   Qt.PenJoinStyle.MiterJoin)
        p.setPen(pen)
        p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in pts]))
    elif kind == "arc":
        _, cx, cy, r, start, span, w = op
        p.setPen(QPen(col, w + ow, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), int(start * 16), int(span * 16))


def write_preset(name, ops):
    size = 128
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    for outline in (True, False):
        col = QColor(0, 0, 0, 225) if outline else QColor(255, 255, 255, 255)
        ow = 2.6 if outline else 0.0
        for op in ops:
            _paint_op(p, op, col, ow)
    p.end()
    img.save(os.path.join(CROSSHAIR_DIR, f"preset-{name}.png"), "PNG")


def ensure_presets(force=False):
    os.makedirs(CROSSHAIR_DIR, exist_ok=True)
    existing = [f for f in os.listdir(CROSSHAIR_DIR) if f.lower().endswith(IMAGE_EXTS)]
    if not force and existing:
        return
    for name, ops in PRESETS.items():
        if force and os.path.exists(os.path.join(CROSSHAIR_DIR, f"preset-{name}.png")):
            continue
        write_preset(name, ops)


def pretty_name(filename):
    base = os.path.splitext(filename)[0]
    base = re.sub(r"^preset[-_]", "", base, flags=re.I)
    return re.sub(r"[-_]+", " ", base).strip().title()


_BASE_CACHE = {}


def load_base(path):
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    hit = _BASE_CACHE.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        img = PILImage.open(path).convert("RGBA")
    except Exception as e:
        print("Could not open image:", path, e)
        return None
    longest = max(img.size)
    if longest > 1024:
        r = 1024 / longest
        img = img.resize((max(1, int(img.width * r)), max(1, int(img.height * r))),
                         PILImage.Resampling.LANCZOS)
    _BASE_CACHE[path] = (mtime, img)
    return img


def pil_to_pixmap(img, dpr=1.0):
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, img.width * 4,
                  QImage.Format.Format_RGBA8888).copy()
    pm = QPixmap.fromImage(qimg)
    pm.setDevicePixelRatio(dpr)
    return pm


def _tint(img, hex_color):
    c = QColor(hex_color)
    lum = img.convert("RGB").convert("L")
    top = lum.getextrema()[1] or 1
    if top < 255:
        lum = lum.point([min(255, int(i * 255 / top)) for i in range(256)])
    flat = PILImage.merge("RGB", (lum, lum, lum))
    color = PILImage.new("RGB", img.size, (c.red(), c.green(), c.blue()))
    out = ImageChops.multiply(flat, color).convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


def render_crosshair(path, scale, opacity, fade, tint):
    try:
        img = load_base(path)
        if img is None:
            return QPixmap()
        if abs(scale - 1.0) > 1e-3:
            nw = max(1, int(round(img.width * scale)))
            nh = max(1, int(round(img.height * scale)))
            img = img.resize((nw, nh), PILImage.Resampling.LANCZOS)
        if tint:
            img = _tint(img, tint)
        if fade > 0:
            pad = int(math.ceil(fade * 3))
            canvas = PILImage.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
            canvas.paste(img, (pad, pad))
            img = canvas.filter(ImageFilter.GaussianBlur(radius=fade))
        if opacity < 1.0:
            alpha = img.getchannel("A").point(lambda v: int(v * opacity))
            img = img.copy()
            img.putalpha(alpha)
        return pil_to_pixmap(img, screen_dpr())
    except Exception as e:
        print("Error rendering crosshair:", e)
        return QPixmap()


def make_thumb(path, box=54):
    base = load_base(path)
    if base is None:
        return QPixmap()
    dpr = screen_dpr()
    f = min(box / max(base.size), 3.0)
    img = base.resize((max(1, int(base.width * f * dpr)), max(1, int(base.height * f * dpr))),
                      PILImage.Resampling.LANCZOS)
    return pil_to_pixmap(img, dpr)


def make_window_clickthrough(hwnd):
    try:
        GWL_EXSTYLE = -20
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= 0x20 | 0x80000 | 0x80 | 0x08000000
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    except Exception as e:
        print("Click-through not supported:", e)


class CrosshairOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._pm = QPixmap()
        self._dx = 0
        self._dy = 0

    def set_state(self, pm, dx, dy):
        self._pm = pm if pm is not None else QPixmap()
        self._dx, self._dy = dx, dy
        self.update()

    def paintEvent(self, event):
        if self._pm.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        sz = self._pm.deviceIndependentSize()
        x = round((self.width() - sz.width()) / 2 + self._dx)
        y = round((self.height() - sz.height()) / 2 + self._dy)
        p.drawPixmap(QPointF(x, y), self._pm)
        p.end()

    def showEvent(self, event):
        super().showEvent(event)
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        if sys.platform == "win32":
            make_window_clickthrough(int(self.winId()))


def paint_logo(p, rect):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    g.setColorAt(0, qc("#FFC24A"))
    g.setColorAt(1, qc(C.AMBER_DEEP))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(g)
    rad = rect.width() * 0.3
    p.drawRoundedRect(rect, rad, rad)
    c = rect.center()
    u = rect.width() / 30.0
    ink = qc("#1A1204")
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(ink, 1.9 * u))
    p.drawEllipse(c, 6.6 * u, 6.6 * u)
    p.setPen(QPen(ink, 1.9 * u, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        p.drawLine(QPointF(c.x() + dx * 9.2 * u, c.y() + dy * 9.2 * u),
                   QPointF(c.x() + dx * 5.2 * u, c.y() + dy * 5.2 * u))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ink)
    p.drawEllipse(c, 1.5 * u, 1.5 * u)


def app_icon():
    pm = QPixmap(128, 128)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    paint_logo(p, QRectF(8, 8, 112, 112))
    p.end()
    return QIcon(pm)


class LogoMark(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(30, 30)

    def paintEvent(self, e):
        p = QPainter(self)
        paint_logo(p, QRectF(0, 0, 30, 30))


class WinButton(QAbstractButton):
    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.setFixedSize(38, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        close = self.kind == "close"
        if self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qc(C.RED, 210) if close else qc("#FFFFFF", 20))
            p.drawRoundedRect(r, 8, 8)
        p.setPen(QPen(qc("#FFFFFF" if (close and self._hover) else C.MUTED), 1.4,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        c = r.center()
        if close:
            p.drawLine(QPointF(c.x() - 4.5, c.y() - 4.5), QPointF(c.x() + 4.5, c.y() + 4.5))
            p.drawLine(QPointF(c.x() + 4.5, c.y() - 4.5), QPointF(c.x() - 4.5, c.y() + 4.5))
        else:
            p.drawLine(QPointF(c.x() - 5, c.y()), QPointF(c.x() + 5, c.y()))


class StatusPill(QWidget):
    def __init__(self):
        super().__init__()
        self.live = False
        self.phase = 0.0
        self.setFixedHeight(28)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self.set_live(False)

    def set_live(self, live):
        self.live = live
        self.text = "Overlay live" if live else "Overlay off"
        w = QFontMetrics(ui_font(12, QFont.Weight.DemiBold)).horizontalAdvance(self.text)
        self.setFixedWidth(w + 44)
        if live:
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _tick(self):
        self.phase = (self.phase + 0.03) % 1.0
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        accent = C.GREEN if self.live else C.FAINT
        p.setBrush(qc(C.GREEN, 22) if self.live else qc("#14161C"))
        p.setPen(QPen(qc(C.GREEN, 80) if self.live else qc("#232733"), 1))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        dot = QPointF(15, r.center().y())
        if self.live:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(qc(C.GREEN, int(110 * (1 - self.phase))), 1.2))
            rr = 3.5 + 6 * self.phase
            p.drawEllipse(dot, rr, rr)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qc(accent))
        p.drawEllipse(dot, 3.5, 3.5)
        p.setFont(ui_font(12, QFont.Weight.DemiBold))
        p.setPen(qc(C.GREEN if self.live else C.MUTED))
        p.drawText(QRectF(28, 0, self.width() - 30, self.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text)


class TitleBar(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self._drag = None
        self.setFixedHeight(58)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 14, 0)
        lay.setSpacing(10)
        brand = QLabel("Sightline Zero")
        brand.setObjectName("Brand")
        badge = QLabel("PRO")
        badge.setObjectName("ProBadge")
        self.status = StatusPill()
        self.btn_min = WinButton("min")
        self.btn_close = WinButton("close")
        badge.setFixedHeight(18)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(LogoMark(), 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(brand, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addStretch()
        lay.addWidget(self.status)
        lay.addSpacing(8)
        lay.addWidget(self.btn_min)
        lay.addWidget(self.btn_close)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setPen(qc("#FFFFFF", 14))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            handle = self.win.windowHandle()
            if handle is not None and handle.startSystemMove():
                return
            self._drag = e.globalPosition().toPoint() - self.win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.win.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None


class Shell(QFrame):
    RADIUS = 18

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        g = QLinearGradient(0, 0, 0, r.height())
        g.setColorAt(0, qc(C.SHELL_TOP))
        g.setColorAt(1, qc(C.SHELL_BOT))
        p.setPen(QPen(qc("#2A2F3C"), 1))
        p.setBrush(g)
        p.drawRoundedRect(r, self.RADIUS, self.RADIUS)

        clip = QPainterPath()
        clip.addRoundedRect(r, self.RADIUS, self.RADIUS)
        p.setClipPath(clip)
        glow = QRadialGradient(QPointF(r.left() + 120, r.top() - 10), 420)
        glow.setColorAt(0, qc(C.AMBER, 20))
        glow.setColorAt(1, qc(C.AMBER, 0))
        p.fillRect(r, glow)


class Segmented(QWidget):
    changed = Signal(int)

    def __init__(self, options, index=0):
        super().__init__()
        self.options = options
        self.index = index
        self._hover = -1
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        fm = QFontMetrics(ui_font(12, QFont.Weight.DemiBold))
        self._widths = [fm.horizontalAdvance(o) + 26 for o in options]
        self.setFixedSize(sum(self._widths) + 8, 32)

    def _rects(self):
        x, out = 4.0, []
        for w in self._widths:
            out.append(QRectF(x, 4, w, self.height() - 8))
            x += w
        return out

    def set_index(self, i):
        self.index = i
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(qc(C.BORDER), 1))
        p.setBrush(qc(C.INSET))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)
        p.setFont(ui_font(12, QFont.Weight.DemiBold))
        for i, r in enumerate(self._rects()):
            if i == self.index:
                p.setPen(QPen(qc("#343A4C"), 1))
                p.setBrush(qc("#1E222D"))
                p.drawRoundedRect(r, 7, 7)
                p.setPen(qc(C.TEXT))
            else:
                p.setPen(qc(C.TEXT_SOFT if i == self._hover else C.MUTED))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.options[i])

    def _at(self, pos):
        for i, r in enumerate(self._rects()):
            if r.contains(pos):
                return i
        return -1

    def mouseMoveEvent(self, e):
        h = self._at(e.position())
        if h != self._hover:
            self._hover = h
            self.update()

    def leaveEvent(self, e):
        self._hover = -1
        self.update()

    def mousePressEvent(self, e):
        i = self._at(e.position())
        if i >= 0 and i != self.index:
            self.index = i
            self.update()
            self.changed.emit(i)


class GlowSlider(QSlider):
    PAD = 9

    def __init__(self, lo, hi, value, default, centered=False):
        super().__init__(Qt.Orientation.Horizontal)
        self.setRange(lo, hi)
        self.setValue(value)
        self._default = default
        self._centered = centered
        self._hover = False
        self._down = False
        self.setFixedHeight(22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Double-click to reset")

    def _ratio(self, v=None):
        v = self.value() if v is None else v
        span = self.maximum() - self.minimum()
        return (v - self.minimum()) / span if span else 0.0

    def _value_at(self, x):
        t = min(1.0, max(0.0, (x - self.PAD) / max(1, self.width() - 2 * self.PAD)))
        return self.minimum() + round(t * (self.maximum() - self.minimum()))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._down = True
            self.setValue(self._value_at(e.position().x()))
            self.update()

    def mouseMoveEvent(self, e):
        if self._down:
            self.setValue(self._value_at(e.position().x()))

    def mouseReleaseEvent(self, e):
        self._down = False
        self.update()

    def mouseDoubleClickEvent(self, e):
        self.setValue(self._default)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        x0, x1 = self.PAD, self.width() - self.PAD
        cy = self.height() / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qc("#252A36"))
        p.drawRoundedRect(QRectF(x0, cy - 2, x1 - x0, 4), 2, 2)

        hx = x0 + self._ratio() * (x1 - x0)
        if self._centered:
            zx = x0 + self._ratio(0) * (x1 - x0)
            a, b = min(zx, hx), max(zx, hx)
            p.setBrush(qc("#3A4152"))
            p.drawRoundedRect(QRectF(zx - 0.75, cy - 5, 1.5, 10), 0.75, 0.75)
        else:
            a, b = x0, hx
        if b - a > 0.5:
            g = QLinearGradient(a, 0, b, 0)
            g.setColorAt(0, qc(C.AMBER_DEEP))
            g.setColorAt(1, qc(C.AMBER))
            p.setBrush(g)
            p.drawRoundedRect(QRectF(a, cy - 2, b - a, 4), 2, 2)

        if self._hover or self._down:
            p.setBrush(qc(C.AMBER, 38 if self._down else 26))
            p.drawEllipse(QPointF(hx, cy), 12, 12)
        p.setBrush(qc("#000000", 90))
        p.drawEllipse(QPointF(hx, cy + 1), 8.5, 8.5)
        p.setBrush(qc("#FFFFFF"))
        p.drawEllipse(QPointF(hx, cy), 7, 7)
        p.setBrush(qc(C.AMBER))
        p.drawEllipse(QPointF(hx, cy), 2.4, 2.4)


class SliderRow(QWidget):
    changed = Signal()

    def __init__(self, title, lo, hi, value, default, fmt, centered=False):
        super().__init__()
        self.fmt = fmt
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        top = QHBoxLayout()
        t = QLabel(title)
        t.setObjectName("RowTitle")
        self.pill = QLabel(fmt(value))
        self.pill.setObjectName("ValuePill")
        top.addWidget(t)
        top.addStretch()
        top.addWidget(self.pill)
        self.slider = GlowSlider(lo, hi, value, default, centered)
        self.slider.valueChanged.connect(self._on)
        lay.addLayout(top)
        lay.addWidget(self.slider)

    def _on(self, v):
        self.pill.setText(self.fmt(v))
        self.changed.emit()

    def value(self):
        return self.slider.value()

    def set_value(self, v):
        self.slider.setValue(v)

    def reset(self):
        self.slider.setValue(self.slider._default)


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked=False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._t = 1.0 if checked else 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set)
        self.toggled.connect(self._animate)

    def _animate(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def _set(self, v):
        self._t = float(v)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(mix("#2A2F3C", C.AMBER, self._t))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = r.left() + 3 + self._t * (r.width() - d - 6)
        p.setBrush(qc("#000000", 70))
        p.drawEllipse(QRectF(x, r.top() + 3.8, d, d))
        p.setBrush(mix("#C9CDD8", "#FFFFFF", self._t))
        p.drawEllipse(QRectF(x, r.top() + 3, d, d))


class ToggleRow(QWidget):
    def __init__(self, title, sub, checked):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel(title)
        t.setObjectName("RowTitle")
        s = QLabel(sub)
        s.setObjectName("RowSub")
        col.addWidget(t)
        col.addWidget(s)
        self.switch = ToggleSwitch(checked)
        lay.addLayout(col)
        lay.addStretch()
        lay.addWidget(self.switch)

    def mousePressEvent(self, e):
        self.switch.toggle()


class ColorSwatch(QAbstractButton):
    def __init__(self, color, label, custom=False):
        super().__init__()
        self.color = color
        self.custom = custom
        self.setCheckable(True)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label)
        self.shown_color = color

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        if self.isChecked():
            p.setPen(QPen(qc(C.AMBER), 1.8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, 13.2, 13.2)
        r = 9.5
        if self.custom and not self.shown_color:
            g = QConicalGradient(c, 0)
            for i, col in enumerate(("#FF4757", "#FFE23B", "#35F28B", "#22E0FF", "#7C6CFF", "#FF4FD8", "#FF4757")):
                g.setColorAt(i / 6, qc(col))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawEllipse(c, r, r)
            p.setBrush(qc("#12141A"))
            p.drawEllipse(c, 4.2, 4.2)
        elif not self.shown_color:
            p.setPen(QPen(qc("#3A4152"), 1.2))
            p.setBrush(qc("#1A1D26"))
            p.drawEllipse(c, r, r)
            p.setPen(QPen(qc(C.MUTED), 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(c.x() - 4.5, c.y() + 4.5), QPointF(c.x() + 4.5, c.y() - 4.5))
        else:
            p.setPen(QPen(qc("#FFFFFF", 40), 1))
            p.setBrush(qc(self.shown_color))
            p.drawEllipse(c, r, r)


class ThumbCard(QAbstractButton):
    W, H = 104, 118

    def __init__(self, path, name, is_preset):
        super().__init__()
        self.path, self.name, self.is_preset = path, name, is_preset
        self.thumb = make_thumb(path)
        self.setCheckable(True)
        self.setFixedSize(self.W, self.H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(name)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._hover = False

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        on = self.isChecked()
        if on:
            p.setBrush(Qt.BrushStyle.NoBrush)
            for i, a in enumerate((34, 18, 8)):
                p.setPen(QPen(qc(C.AMBER, a), 1))
                p.drawRoundedRect(r.adjusted(-1 - i, -1 - i, 1 + i, 1 + i), 13 + i, 13 + i)
        p.setBrush(qc("#171A22") if self._hover else qc("#10131A"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 12, 12)
        if on:
            g = QLinearGradient(r.topLeft(), r.bottomLeft())
            g.setColorAt(0, qc(C.AMBER, 30))
            g.setColorAt(1, qc(C.AMBER, 4))
            p.setBrush(g)
            p.drawRoundedRect(r, 12, 12)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qc(C.AMBER) if on else qc(C.BORDER_HI if self._hover else C.BORDER),
                      1.5 if on else 1))
        p.drawRoundedRect(r, 12, 12)

        area = QRectF(r.left() + 8, r.top() + 8, r.width() - 16, 68)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qc("#0A0C10"))
        p.drawRoundedRect(area, 8, 8)
        if not self.thumb.isNull():
            sz = self.thumb.deviceIndependentSize()
            p.drawPixmap(QPointF(area.center().x() - sz.width() / 2,
                                 area.center().y() - sz.height() / 2), self.thumb)

        p.setFont(ui_font(11, QFont.Weight.Medium))
        p.setPen(qc(C.TEXT if (on or self._hover) else C.MUTED))
        cap = QRectF(r.left() + 8, area.bottom() + 4, r.width() - 16, 20)
        txt = QFontMetrics(p.font()).elidedText(self.name, Qt.TextElideMode.ElideRight, int(cap.width()))
        p.drawText(cap, Qt.AlignmentFlag.AlignCenter, txt)

        if on:
            b = QPointF(r.right() - 11, r.top() + 11)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qc(C.AMBER))
            p.drawEllipse(b, 7.5, 7.5)
            p.setPen(QPen(qc("#1A1204"), 1.7, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPolyline(QPolygonF([QPointF(b.x() - 3, b.y() + 0.2),
                                      QPointF(b.x() - 0.8, b.y() + 2.4),
                                      QPointF(b.x() + 3.2, b.y() - 2.4)]))


class AddTile(QAbstractButton):
    def __init__(self):
        super().__init__()
        self.setFixedSize(ThumbCard.W, ThumbCard.H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Import a PNG / JPG / WebP crosshair")
        self._hover = False

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        col = qc(C.AMBER) if self._hover else qc("#343A4C")
        pen = QPen(col, 1.2)
        pen.setDashPattern([4, 4])
        p.setPen(pen)
        p.setBrush(qc(C.AMBER, 10) if self._hover else Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, 12, 12)
        c = QPointF(r.center().x(), r.center().y() - 8)
        p.setPen(QPen(col, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c.x() - 8, c.y()), QPointF(c.x() + 8, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - 8), QPointF(c.x(), c.y() + 8))
        p.setFont(ui_font(11, QFont.Weight.Medium))
        p.setPen(qc(C.AMBER if self._hover else C.MUTED))
        p.drawText(QRectF(r.left(), c.y() + 14, r.width(), 20), Qt.AlignmentFlag.AlignCenter, "Import")


class Gallery(QScrollArea):
    GAP = 10

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)
        self.host = QWidget()
        self.host.setAutoFillBackground(False)
        self.grid = QGridLayout(self.host)
        self.grid.setContentsMargins(0, 2, 6, 2)
        self.grid.setSpacing(self.GAP)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setWidget(self.host)
        self._widgets = []
        self._cols_now = 0

    def _cols(self):
        avail = self.viewport().width() - 8
        return max(1, (avail + self.GAP) // (ThumbCard.W + self.GAP))

    def layout_widgets(self, widgets):
        self._widgets = widgets
        while self.grid.count():
            self.grid.takeAt(0)
        cols = self._cols()
        for i, w in enumerate(widgets):
            self.grid.addWidget(w, i // cols, i % cols)
        self._cols_now = cols

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._widgets and self._cols() != self._cols_now:
            self.layout_widgets(self._widgets)


class Toast(QLabel):
    COLORS = {"info": C.AMBER, "ok": C.GREEN, "warn": C.RED}

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.fx = QGraphicsOpacityEffect(self)
        self.fx.setOpacity(0.0)
        self.setGraphicsEffect(self.fx)
        self.anim = QPropertyAnimation(self.fx, b"opacity", self)
        self.anim.setDuration(180)
        self.anim.finished.connect(self._done)
        self.hold = QTimer(self)
        self.hold.setSingleShot(True)
        self.hold.timeout.connect(self._out)
        self._out_phase = False
        self.hide()

    def popup(self, text, kind="info"):
        col = self.COLORS.get(kind, C.AMBER)
        self.setText(f'<span style="color:{col}">&#9679;</span>&nbsp;&nbsp;{html.escape(text)}')
        self.adjustSize()
        par = self.parentWidget()
        self.move((par.width() - self.width()) // 2, par.height() - self.height() - 28)
        self.show()
        self.raise_()
        self._out_phase = False
        self.anim.stop()
        self.anim.setStartValue(self.fx.opacity())
        self.anim.setEndValue(1.0)
        self.anim.start()
        self.hold.start(2400)

    def _out(self):
        self._out_phase = True
        self.anim.stop()
        self.anim.setStartValue(self.fx.opacity())
        self.anim.setEndValue(0.0)
        self.anim.start()

    def _done(self):
        if self._out_phase:
            self.hide()


class PreviewCanvas(QWidget):
    BG_NAMES = ["Range", "Void", "Dusk", "Daylight"]

    def __init__(self):
        super().__init__()
        self.setMinimumSize(380, 220)
        self.pm = None
        self.dx = self.dy = 0
        self.bg_mode = 0
        self.show_guides = True

    def set_state(self, pm, dx, dy):
        self.pm, self.dx, self.dy = pm, dx, dy
        self.update()

    def _bg(self, p, r):
        w, h = r.width(), r.height()
        if self.bg_mode == 0:
            hy = h * 0.5
            g = QLinearGradient(0, 0, 0, h)
            g.setColorAt(0.0, qc("#0B0D13"))
            g.setColorAt(0.49, qc("#171B26"))
            g.setColorAt(0.5, qc("#0F1218"))
            g.setColorAt(1.0, qc("#090A0E"))
            p.fillRect(r, g)
            glow = QRadialGradient(QPointF(w / 2, hy), w * 0.6)
            glow.setColorAt(0, qc(C.AMBER, 36))
            glow.setColorAt(1, qc(C.AMBER, 0))
            p.fillRect(r, glow)
            for i in range(-16, 17):
                a = int(34 * (1 - abs(i) / 18))
                p.setPen(QPen(qc("#FFFFFF", a), 1))
                p.drawLine(QPointF(w / 2, hy), QPointF(w / 2 + i * w / 8, h))
            for k in range(1, 15):
                t = (k / 14) ** 2.2
                p.setPen(QPen(qc("#FFFFFF", int(8 + 44 * t)), 1))
                y = hy + (h - hy) * t
                p.drawLine(QPointF(0, y), QPointF(w, y))
        elif self.bg_mode == 1:
            g = QRadialGradient(r.center(), max(w, h) * 0.7)
            g.setColorAt(0, qc("#181B24"))
            g.setColorAt(1, qc("#0A0B0F"))
            p.fillRect(r, g)
        elif self.bg_mode == 2:
            g = QLinearGradient(0, 0, w, h)
            g.setColorAt(0.0, qc("#2B1336"))
            g.setColorAt(0.55, qc("#121A30"))
            g.setColorAt(1.0, qc("#0B2B3A"))
            p.fillRect(r, g)
        else:
            g = QLinearGradient(0, 0, 0, h)
            g.setColorAt(0.0, qc("#86B4E6"))
            g.setColorAt(0.5, qc("#E3EEF8"))
            g.setColorAt(0.5001, qc("#D2C7A6"))
            g.setColorAt(1.0, qc("#A69A78"))
            p.fillRect(r, g)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(r, 12, 12)
        p.setClipPath(clip)
        self._bg(p, r)

        light = self.bg_mode == 3
        ink = "#000000" if light else "#FFFFFF"
        cx, cy = r.width() / 2, r.height() / 2


        p.setPen(QPen(qc(ink, 80 if light else 60), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        m, L = 16, 18
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x = m if sx > 0 else r.width() - m
            y = m if sy > 0 else r.height() - m
            p.drawLine(QPointF(x, y), QPointF(x + sx * L, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + sy * L))

        if self.show_guides:
            pen = QPen(qc(ink, 34))
            pen.setDashPattern([3, 5])
            p.setPen(pen)
            p.drawLine(QPointF(cx, 0), QPointF(cx, r.height()))
            p.drawLine(QPointF(0, cy), QPointF(r.width(), cy))
            p.setPen(QPen(qc(C.AMBER, 90), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), 20, 20)

        if self.pm is not None and not self.pm.isNull():
            sz = self.pm.deviceIndependentSize()
            p.drawPixmap(QPointF(round(cx - sz.width() / 2 + self.dx),
                                 round(cy - sz.height() / 2 + self.dy)), self.pm)
            info = f"{self.pm.width()} \u00d7 {self.pm.height()} px   offset {self.dx}, {self.dy}"
        else:
            info = "No crosshair selected"
            p.setFont(ui_font(13, QFont.Weight.Medium))
            p.setPen(qc(ink, 120))
            p.drawText(QRectF(0, cy + 34, r.width(), 24), Qt.AlignmentFlag.AlignCenter,
                       "Pick one from the library below")


        p.setFont(ui_font(11, QFont.Weight.DemiBold))
        tw = QFontMetrics(p.font()).horizontalAdvance(info)
        chip = QRectF(16, r.height() - 16 - 26, tw + 22, 26)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qc("#FFFFFF", 150) if light else qc("#000000", 120))
        p.drawRoundedRect(chip, 8, 8)
        p.setPen(qc("#1A1D26") if light else qc("#FFFFFF", 200))
        p.drawText(chip, Qt.AlignmentFlag.AlignCenter, info)

        p.setClipping(False)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qc("#FFFFFF", 22), 1))
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)


TINTS = [
    ("", "Original colors"), ("#FFFFFF", "White"), ("#35F28B", "Green"),
    ("#22E0FF", "Cyan"), ("#FFE23B", "Yellow"), ("#FF4FD8", "Pink"), ("#FF4757", "Red"),
]


def make_card():
    f = QFrame()
    f.setObjectName("Card")
    return f


def divider():
    f = QFrame()
    f.setObjectName("Divider")
    return f


def section_label(text):
    l = QLabel(text)
    l.setObjectName("SectionLabel")
    return l


class CrosshairManager(QWidget):
    MARGIN = 16

    def __init__(self):
        super().__init__()
        os.makedirs(CROSSHAIR_DIR, exist_ok=True)
        ensure_presets()

        self.setWindowTitle("Sightline Zero")
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.setMinimumSize(1060 + 2 * self.MARGIN, 700 + 2 * self.MARGIN)
        self.resize(1200, 820)

        self.cfg = self.load_config()
        self.selected = ""
        self.overlay = None
        self.overlay_on = False
        self.cards = []
        self._pm = None

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(20)
        self._refresh_timer.timeout.connect(self._do_refresh)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self.save_config)

        self.build_ui()
        self.reload_library()
        self.apply_saved_config()

        sc = QShortcut(QKeySequence("Ctrl+E"), self)
        sc.activated.connect(self.toggle_overlay)


    def load_config(self):
        cfg = dict(DEFAULT_CONFIG)
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    cfg.update(json.load(f))
            except Exception as e:
                print("Error loading config:", e)
        return cfg

    def save_config(self):
        try:
            self.cfg.update({
                "scale": self.row_scale.value() / 10.0,
                "opacity": self.row_opacity.value() / 100.0,
                "fade": self.row_fade.value() / 10.0,
                "offset_x": self.row_x.value(),
                "offset_y": self.row_y.value(),
                "auto_apply": self.tg_auto.switch.isChecked(),
                "show_guides": self.tg_guides.switch.isChecked(),
                "bg_mode": self.preview.bg_mode,
                "last_crosshair": self.selected or self.cfg.get("last_crosshair", ""),
            })
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.cfg, f, indent=4)
        except Exception as e:
            print("Error saving config:", e)

    def schedule_save(self):
        self._save_timer.start()


    def build_ui(self):
        M = self.MARGIN
        outer = QVBoxLayout(self)
        outer.setContentsMargins(M, M, M, M)
        self.shell = Shell()
        outer.addWidget(self.shell)
        shell_l = QVBoxLayout(self.shell)
        shell_l.setContentsMargins(0, 0, 0, 0)
        shell_l.setSpacing(0)

        self.titlebar = TitleBar(self)
        self.titlebar.btn_min.clicked.connect(self.showMinimized)
        self.titlebar.btn_close.clicked.connect(self.close)
        shell_l.addWidget(self.titlebar)

        body = QHBoxLayout()
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(14)
        shell_l.addLayout(body, 1)

        left = QVBoxLayout()
        left.setSpacing(14)
        left.addWidget(self.build_preview_card(), 5)
        left.addWidget(self.build_library_card(), 4)
        body.addLayout(left, 1)
        body.addWidget(self.build_settings_card())

        self.toast = Toast(self.shell)
        self.grip = QSizeGrip(self.shell)

    def build_preview_card(self):
        card = make_card()
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(12)

        head = QHBoxLayout()
        t = QLabel("Live preview")
        t.setObjectName("CardTitle")
        self.bg_seg = Segmented(PreviewCanvas.BG_NAMES, int(self.cfg["bg_mode"]) % 4)
        self.bg_seg.changed.connect(self.on_bg_changed)
        head.addWidget(t)
        head.addStretch()
        head.addWidget(self.bg_seg)
        v.addLayout(head)

        self.preview = PreviewCanvas()
        self.preview.bg_mode = self.bg_seg.index
        self.preview.show_guides = bool(self.cfg["show_guides"])
        v.addWidget(self.preview, 1)

        foot = QHBoxLayout()
        self.sel_name = QLabel("No selection")
        self.sel_name.setObjectName("SelName")
        self.sel_meta = QLabel("")
        self.sel_meta.setObjectName("Hint")
        foot.addWidget(self.sel_name)
        foot.addStretch()
        foot.addWidget(self.sel_meta)
        v.addLayout(foot)
        return card

    def build_library_card(self):
        card = make_card()
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 12)
        v.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel("Library")
        t.setObjectName("CardTitle")
        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("Hint")
        titles.addWidget(t)
        titles.addWidget(self.count_lbl)
        self.filter_seg = Segmented(["All", "Presets", "Mine"], 0)
        self.filter_seg.changed.connect(lambda _: self.apply_filter())
        imp = QPushButton("Import image")
        imp.setObjectName("Accent")
        imp.setCursor(Qt.CursorShape.PointingHandCursor)
        imp.clicked.connect(self.import_dialog)
        head.addLayout(titles)
        head.addStretch()
        head.addWidget(self.filter_seg)
        head.addWidget(imp)
        v.addLayout(head)

        self.search = QLineEdit()
        self.search.setObjectName("Search")
        self.search.setPlaceholderText("Search crosshairs")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _: self.apply_filter())
        v.addWidget(self.search)

        self.gallery = Gallery()
        self.gallery.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.gallery.customContextMenuRequested.connect(self.gallery_menu)
        v.addWidget(self.gallery, 1)
        return card

    def build_settings_card(self):
        card = make_card()
        card.setFixedWidth(340)
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 14, 18, 18)
        v.setSpacing(0)

        head = QHBoxLayout()
        t = QLabel("Tune")
        t.setObjectName("CardTitle")
        reset = QPushButton("Reset all")
        reset.setObjectName("Ghost")
        reset.setCursor(Qt.CursorShape.PointingHandCursor)
        reset.clicked.connect(self.reset_all)
        head.addWidget(t)
        head.addStretch()
        head.addWidget(reset)
        v.addLayout(head)
        v.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        inner = QWidget()
        inner.setAutoFillBackground(False)
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 8, 0)
        iv.setSpacing(14)

        cfg = self.cfg
        self.row_scale = SliderRow("Size", 1, 50, int(round(cfg["scale"] * 10)), 10,
                                   lambda v: f"{v / 10:.1f}\u00d7")
        self.row_opacity = SliderRow("Opacity", 10, 100, int(round(cfg["opacity"] * 100)), 100,
                                     lambda v: f"{v}%")
        self.row_fade = SliderRow("Softness", 0, 100, int(round(cfg["fade"] * 10)), 0,
                                  lambda v: f"{v / 10:.1f}")
        self.row_x = SliderRow("Offset X", -300, 300, int(cfg["offset_x"]), 0, lambda v: f"{v:+d} px", True)
        self.row_y = SliderRow("Offset Y", -300, 300, int(cfg["offset_y"]), 0, lambda v: f"{v:+d} px", True)
        for r in (self.row_scale, self.row_opacity, self.row_fade, self.row_x, self.row_y):
            r.changed.connect(self.refresh)

        iv.addWidget(section_label("Appearance"))
        iv.addWidget(self.row_scale)
        iv.addWidget(self.row_opacity)
        iv.addWidget(self.row_fade)
        iv.addWidget(divider())

        pos_head = QHBoxLayout()
        pos_head.addWidget(section_label("Position"))
        pos_head.addStretch()
        center = QPushButton("Center")
        center.setObjectName("Ghost")
        center.setCursor(Qt.CursorShape.PointingHandCursor)
        center.clicked.connect(lambda: (self.row_x.reset(), self.row_y.reset()))
        pos_head.addWidget(center)
        iv.addLayout(pos_head)
        iv.addWidget(self.row_x)
        iv.addWidget(self.row_y)
        iv.addWidget(divider())

        iv.addWidget(section_label("Color"))
        sw_row = QHBoxLayout()
        sw_row.setSpacing(6)
        self.swatches = []
        for hex_, label in TINTS:
            s = ColorSwatch(hex_, label)
            s.clicked.connect(lambda _=False, h=hex_: self.set_tint(h))
            self.swatches.append(s)
            sw_row.addWidget(s)
        self.custom_swatch = ColorSwatch("", "Custom color", custom=True)
        self.custom_swatch.clicked.connect(self.pick_custom_tint)
        sw_row.addWidget(self.custom_swatch)
        sw_row.addStretch()
        iv.addLayout(sw_row)
        iv.addWidget(divider())

        iv.addWidget(section_label("Behavior"))
        self.tg_auto = ToggleRow("Launch on start", "Re-enable the last overlay automatically",
                                 bool(cfg["auto_apply"]))
        self.tg_guides = ToggleRow("Preview guides", "Center lines and aim ring in the preview",
                                   bool(cfg["show_guides"]))
        self.tg_auto.switch.toggled.connect(lambda _: self.schedule_save())
        self.tg_guides.switch.toggled.connect(self.on_guides_toggled)
        iv.addWidget(self.tg_auto)
        iv.addWidget(self.tg_guides)
        iv.addStretch()
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)

        v.addSpacing(12)
        self.primary = QPushButton("Enable overlay")
        self.primary.setObjectName("Primary")
        self.primary.setFixedHeight(46)
        self.primary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.primary.clicked.connect(self.toggle_overlay)
        v.addWidget(self.primary)
        hint = QLabel("Ctrl+E toggles the overlay  \u00b7  drop images here to import")
        hint.setObjectName("Hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addSpacing(8)
        v.addWidget(hint)

        self.sync_swatches()
        return card


    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(Qt.BrushStyle.NoBrush)
        g = self.shell.geometry()
        for i in range(1, self.MARGIN):
            a = int(46 * (1 - i / self.MARGIN) ** 2.4)
            p.setPen(QPen(QColor(0, 0, 0, a), 1))
            p.drawRoundedRect(QRectF(g).adjusted(-i, -i + 4, i, i + 4),
                              Shell.RADIUS + i, Shell.RADIUS + i)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.grip.move(self.shell.width() - self.grip.width() - 5,
                       self.shell.height() - self.grip.height() - 5)


    def reload_library(self):
        for c in self.cards:
            c.setParent(None)
            c.deleteLater()
        self.cards = []
        if not hasattr(self, "add_tile"):
            self.add_tile = AddTile()
            self.add_tile.clicked.connect(self.import_dialog)

        files = [f for f in os.listdir(CROSSHAIR_DIR) if f.lower().endswith(IMAGE_EXTS)]
        files.sort(key=lambda f: (f.lower().startswith("preset-"), f.lower()))
        for f in files:
            path = os.path.join(CROSSHAIR_DIR, f)
            card = ThumbCard(path, pretty_name(f), f.lower().startswith("preset-"))
            card.clicked.connect(lambda _=False, p=path: self.select_crosshair(p))
            card.customContextMenuRequested.connect(lambda pos, c=card: self.card_menu(c, pos))
            self.cards.append(card)
        self.apply_filter()
        self.sync_checked()

    def apply_filter(self):
        q = self.search.text().strip().lower()
        mode = self.filter_seg.index
        vis = []
        for c in self.cards:
            ok = (mode == 0 or (mode == 1 and c.is_preset) or (mode == 2 and not c.is_preset))
            ok = ok and (not q or q in c.name.lower())
            c.setVisible(ok)
            if ok:
                vis.append(c)
        total = len(self.cards)
        self.count_lbl.setText(f"{total} crosshairs" if len(vis) == total
                               else f"{len(vis)} of {total} shown")
        show_add = not q
        self.add_tile.setVisible(show_add)
        if show_add:
            vis.append(self.add_tile)
        self.gallery.layout_widgets(vis)

    def sync_checked(self):
        for c in self.cards:
            c.setChecked(c.path == self.selected)

    def select_crosshair(self, path, save=True):
        self.selected = path
        self.sync_checked()
        name = pretty_name(os.path.basename(path))
        self.sel_name.setText(name)
        is_preset = os.path.basename(path).lower().startswith("preset-")
        self.sel_meta.setText("Built-in preset" if is_preset else "Imported image")
        self.refresh()
        for c in self.cards:
            if c.path == path and c.isVisible():
                self.gallery.ensureWidgetVisible(c)
        if save:
            self.schedule_save()


    def import_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import crosshair images", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if paths:
            self.import_files(paths)

    def import_files(self, paths):
        last, count = None, 0
        for src in paths:
            base, ext = os.path.splitext(os.path.basename(src))
            if base.lower().startswith("preset"):
                base = "import-" + base
            dest = os.path.join(CROSSHAIR_DIR, base + ext)
            i = 1
            while os.path.exists(dest):
                dest = os.path.join(CROSSHAIR_DIR, f"{base}_{i}{ext}")
                i += 1
            try:
                shutil.copy(src, dest)
                last = dest
                count += 1
            except OSError as ex:
                print("Import failed:", ex)
        if last:
            self.filter_seg.set_index(0)
            self.search.clear()
            self.reload_library()
            self.select_crosshair(last)
            self.toast.popup(f"Imported {count} crosshair" + ("s" if count != 1 else ""), "ok")
        else:
            self.toast.popup("Could not import that file", "warn")

    def delete_crosshair(self, path):
        name = pretty_name(os.path.basename(path))
        ans = QMessageBox.question(
            self, "Delete crosshair",
            f"Remove \u201c{name}\u201d from your library?\nThe file is deleted from disk.")
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            os.remove(path)
        except OSError as ex:
            self.toast.popup(f"Could not delete: {ex.strerror}", "warn")
            return
        _BASE_CACHE.pop(path, None)
        if self.selected == path:
            self.selected = ""
            if self.overlay_on:
                self.stop_overlay()
        self.reload_library()
        if not self.selected and self.cards:
            self.select_crosshair(self.cards[0].path)
        elif not self.selected:
            self.refresh()
        self.toast.popup(f"Deleted {name}", "info")

    def card_menu(self, card, pos):
        m = QMenu(self)
        a_sel = m.addAction("Use this crosshair")
        a_dir = m.addAction("Show in folder")
        m.addSeparator()
        a_del = m.addAction("Delete\u2026")
        act = m.exec(card.mapToGlobal(pos))
        if act == a_sel:
            self.select_crosshair(card.path)
        elif act == a_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(CROSSHAIR_DIR))
        elif act == a_del:
            self.delete_crosshair(card.path)

    def gallery_menu(self, pos):
        m = QMenu(self)
        a_imp = m.addAction("Import image\u2026")
        a_res = m.addAction("Restore built-in presets")
        a_dir = m.addAction("Open crosshairs folder")
        act = m.exec(self.gallery.mapToGlobal(pos))
        if act == a_imp:
            self.import_dialog()
        elif act == a_res:
            ensure_presets(force=True)
            self.reload_library()
            self.toast.popup("Presets restored", "ok")
        elif act == a_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(CROSSHAIR_DIR))


    def on_bg_changed(self, i):
        self.preview.bg_mode = i
        self.preview.update()
        self.schedule_save()

    def on_guides_toggled(self, on):
        self.preview.show_guides = on
        self.preview.update()
        self.schedule_save()

    def set_tint(self, hex_color):
        self.cfg["tint"] = hex_color
        self.sync_swatches()
        self.refresh()

    def pick_custom_tint(self):
        start = QColor(self.cfg["tint"] or "#FFFFFF")
        col = QColorDialog.getColor(start, self, "Pick a crosshair color")
        if col.isValid():
            self.set_tint(col.name())
        else:
            self.sync_swatches()

    def sync_swatches(self):
        tint = (self.cfg.get("tint") or "").lower()
        preset_hexes = [h.lower() for h, _ in TINTS]
        for s in self.swatches:
            s.setChecked(s.color.lower() == tint)
        is_custom = bool(tint) and tint not in preset_hexes
        self.custom_swatch.shown_color = tint if is_custom else ""
        self.custom_swatch.setChecked(is_custom)
        for s in self.swatches + [self.custom_swatch]:
            s.update()

    def reset_all(self):
        for r in (self.row_scale, self.row_opacity, self.row_fade, self.row_x, self.row_y):
            r.reset()
        self.set_tint("")
        self.toast.popup("Settings reset", "info")


    def refresh(self):
        self._refresh_timer.start()

    def _do_refresh(self):
        pm = None
        if self.selected and os.path.exists(self.selected):
            pm = render_crosshair(
                self.selected,
                self.row_scale.value() / 10.0,
                self.row_opacity.value() / 100.0,
                self.row_fade.value() / 10.0,
                self.cfg.get("tint", ""),
            )
        self._pm = pm
        dx, dy = self.row_x.value(), self.row_y.value()
        self.preview.set_state(pm, dx, dy)
        if self.overlay_on and self.overlay:
            self.overlay.set_state(pm, dx, dy)
        self.schedule_save()


    def toggle_overlay(self):
        if self.overlay_on:
            self.stop_overlay()
        else:
            self.start_overlay()

    def start_overlay(self):
        if not self.selected or not os.path.exists(self.selected):
            self.toast.popup("Pick a crosshair from the library first", "warn")
            return
        self._refresh_timer.stop()
        self._do_refresh()
        if self.overlay is None:
            self.overlay = CrosshairOverlay()
        self.overlay.set_state(self._pm, self.row_x.value(), self.row_y.value())
        self.overlay.show()
        self.overlay_on = True
        self.sync_live_ui()
        self.toast.popup("Overlay is live", "ok")

    def stop_overlay(self):
        if self.overlay:
            self.overlay.hide()
        self.overlay_on = False
        self.sync_live_ui()

    def sync_live_ui(self):
        live = self.overlay_on
        self.primary.setText("Disable overlay" if live else "Enable overlay")
        self.primary.setProperty("live", live)
        self.primary.style().unpolish(self.primary)
        self.primary.style().polish(self.primary)
        self.titlebar.status.set_live(live)

    def apply_saved_config(self):
        last = self.cfg.get("last_crosshair", "")
        if last and not os.path.isabs(last):
            last = os.path.join(BASE_DIR, last)
        if last and os.path.exists(last):
            self.select_crosshair(last, save=False)
            if self.cfg.get("auto_apply", True):
                self.start_overlay()
        elif self.cards:
            self.select_crosshair(self.cards[0].path, save=False)


    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(
                u.toLocalFile().lower().endswith(IMAGE_EXTS) for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls()
                 if u.toLocalFile().lower().endswith(IMAGE_EXTS)]
        if paths:
            self.import_files(paths)

    def closeEvent(self, e):
        self.save_config()
        if self.overlay:
            self.overlay.close()
        e.accept()


def apply_dark_palette(app):
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#12141A"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(C.TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor("#0D0F14"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#12141A"))
    pal.setColor(QPalette.ColorRole.Text, QColor(C.TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor("#1A1D26"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(C.TEXT))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1A1D26"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(C.TEXT))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(C.AMBER))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#1A1204"))
    app.setPalette(pal)


def main():
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("sightlinezero.app")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_dark_palette(app)
    families = set(QFontDatabase.families())
    for fam in ("Inter", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text",
                "Helvetica Neue", "Ubuntu", "Noto Sans"):
        if fam in families:
            app.setFont(QFont(fam, 10))
            break
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(app_icon())

    win = CrosshairManager()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()