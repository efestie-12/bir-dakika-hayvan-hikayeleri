"""Layered silhouette artwork for the Wojtek short.
Frame is 1080x1920. Layers are 1296x2304 so the camera can pan/zoom.
All drawing coordinates are in FRAME space (0..1080, 0..1920); the layer
margin (OX, OY) is added automatically. Drawn at 2x and downsampled.
"""
import math, random, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FW, FH = 1080, 1920
LW, LH = 1296, 2304
OX, OY = (LW - FW) // 2, (LH - FH) // 2
SS = 2

# ---------------------------------------------------------------- fonts
# Önce repo içindeki assets/fonts aranır; yoksa (eski düzen) fonts/, en son sistem font klasörleri.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIRS = [os.path.join(ROOT, 'assets', 'fonts'), os.path.join(ROOT, 'fonts'),
             '/usr/share/fonts/opentype/inter', '/usr/share/fonts/truetype/dejavu',
             '/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.fonts')]
_FALLBACK = {'.otf': 'DejaVuSans-Bold.ttf', '.ttf': 'DejaVuSans.ttf'}


def font_path(name):
    """Font dosyasının tam yolunu döndürür (assets/fonts -> fonts -> sistem)."""
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    for d in FONT_DIRS[2:]:
        if os.path.isdir(d):
            for r, _, fs in os.walk(d):
                if name in fs:
                    return os.path.join(r, name)
    fb = _FALLBACK.get(os.path.splitext(name)[1], 'DejaVuSans.ttf')
    for d in FONT_DIRS:
        for r, _, fs in (os.walk(d) if os.path.isdir(d) else []):
            if fb in fs:
                return os.path.join(r, fb)
    raise FileNotFoundError(f'Font bulunamadı: {name} (assets/fonts klasörünü kontrol edin)')


def hexc(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


class Canvas:
    def __init__(self):
        self.img = Image.new('RGBA', (LW * SS, LH * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def P(self, x, y):
        return ((x + OX) * SS, (y + OY) * SS)

    def ellipse(self, cx, cy, w, h, fill):
        x0, y0 = self.P(cx - abs(w) / 2, cy - abs(h) / 2)
        x1, y1 = self.P(cx + abs(w) / 2, cy + abs(h) / 2)
        self.d.ellipse([x0, y0, x1, y1], fill=fill)

    def circle(self, cx, cy, r, fill):
        self.ellipse(cx, cy, 2 * r, 2 * r, fill)

    def poly(self, pts, fill):
        self.d.polygon([self.P(x, y) for x, y in pts], fill=fill)

    def line(self, pts, w, fill, caps=True):
        P = [self.P(x, y) for x, y in pts]
        self.d.line(P, fill=fill, width=max(1, int(w * SS)), joint='curve')
        if caps:
            for x, y in pts:
                self.circle(x, y, w / 2, fill)

    def rect(self, x0, y0, x1, y1, fill, r=0):
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        a, b = self.P(x0, y0), self.P(x1, y1)
        if r:
            self.d.rounded_rectangle([a, b], radius=r * SS, fill=fill)
        else:
            self.d.rectangle([a, b], fill=fill)

    def done(self, blur=0):
        im = self.img.resize((LW, LH), Image.LANCZOS)
        if blur:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        return im


# ---------------------------------------------------------------- backgrounds
def gradient(stops):
    ys = np.arange(LH) - OY
    pos = [s[0] for s in stops]
    cols = np.array([hexc(s[1])[:3] for s in stops], float)
    ch = [np.interp(ys, pos, cols[:, i]) for i in range(3)]
    arr = np.zeros((LH, LW, 4), np.float32)
    for i in range(3):
        arr[..., i] = ch[i][:, None]
    arr[..., 3] = 255
    return arr


def add_glow(arr, cx, cy, r, color, strength, squash=1.0):
    yy, xx = np.mgrid[0:LH, 0:LW].astype(np.float32)
    dx = (xx - (cx + OX)) / r
    dy = (yy - (cy + OY)) / (r * squash)
    a = strength * np.exp(-(dx * dx + dy * dy))
    col = np.array(hexc(color)[:3], np.float32)
    for i in range(3):
        arr[..., i] = arr[..., i] * (1 - a) + col[i] * a
    return arr


def glow_layer(cx, cy, r, color, strength, squash=1.0):
    yy, xx = np.mgrid[0:LH, 0:LW].astype(np.float32)
    dx = (xx - (cx + OX)) / r
    dy = (yy - (cy + OY)) / (r * squash)
    a = strength * np.exp(-(dx * dx + dy * dy))
    out = np.zeros((LH, LW, 4), np.uint8)
    col = hexc(color)
    out[..., 0], out[..., 1], out[..., 2] = col[0], col[1], col[2]
    out[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')


def grain_tex(arr, amt=6, seed=0):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, amt, (LH // 4, LW // 4)).astype(np.float32)
    n = np.array(Image.fromarray(n).resize((LW, LH), Image.BICUBIC))
    for i in range(3):
        arr[..., i] += n
    return arr


def ridge(c, base, amp, col, seed=0, f1=0.004, f2=0.011, bottom=2150, step=6):
    rnd = random.Random(seed)
    p1, p2 = rnd.random() * 6.28, rnd.random() * 6.28
    pts = []
    for x in range(-OX - 10, FW + OX + 10, step):
        y = base - amp * (0.65 * math.sin(x * f1 + p1) + 0.35 * math.sin(x * f2 + p2))
        pts.append((x, y))
    pts += [(FW + OX + 10, bottom), (-OX - 10, bottom)]
    c.poly(pts, col)


# ---------------------------------------------------------------- figures
def bear(c, x, y, h, col, pose='stand', d=1, cap=False, lift=0.0):
    u = h / 100.0
    X = lambda a: x + a * u * d
    Y = lambda b: y - b * u
    E = lambda ax, by, w, hh: c.ellipse(X(ax), Y(by), w * u, hh * u, col)
    L = lambda pts, w: c.line([(X(a), Y(b)) for a, b in pts], w * u, col)

    if pose in ('stand', 'carry', 'attention', 'grapple', 'shell'):
        L([(-9, 30), (-10, 5)], 15)
        L([(8, 30), (10, 5)], 15)
        E(-6, 3, 22, 8)
        E(15, 3, 22, 8)
        E(0, 40, 46, 58)
        E(4, 34, 42, 44)
        E(2, 60, 38, 32)
        E(6, 80, 26, 25)            # head
        E(19, 78, 17, 12)           # snout
        E(27, 79.5, 6, 5)           # nose
        if not cap:
            E(-3, 92, 10, 10)
        E(10, 93, 10, 10)
        if cap:
            c.poly([(X(-7), Y(89)), (X(16), Y(93)), (X(13), Y(101)), (X(-4), Y(98))], col)
        if pose == 'stand':
            L([(12, 64), (18, 44), (20, 38)], 11)
            L([(-12, 62), (-15, 42)], 11)
        elif pose == 'attention':
            L([(13, 64), (15, 40)], 11)
            L([(-12, 62), (-12, 40)], 11)
        elif pose == 'grapple':
            L([(12, 64), (24, 74), (30, 76)], 11)
            L([(-4, 66), (20, 80), (28, 84)], 10)
        elif pose == 'carry':
            L([(10, 62), (22, 56), (30, 57)], 11)
            L([(-6, 62), (16, 53)], 11)
            c.rect(X(19), Y(45), X(48), Y(69), col)
        elif pose == 'shell':
            L([(10, 62), (20, 54), (26, 56)], 11)
            L([(-4, 62), (14, 52)], 10)
            # artillery shell held upright against chest
            c.rect(X(22), Y(36), X(33), Y(70), col)
            c.poly([(X(22), Y(70)), (X(33), Y(70)), (X(27.5), Y(84))], col)
            c.rect(X(21), Y(34), X(34), Y(38), col)
    elif pose == 'sit':
        E(0, 28, 60, 56)
        E(-8, 12, 52, 26)
        E(24, 5, 22, 9)
        E(-20, 4, 26, 10)
        L([(14, 44), (21, 8)], 13)
        hx, hy = 22 + (16 - 22) * lift, 52 + (66 - 52) * lift
        sx, sy = 34 + (27 - 34) * lift, 46 + (73 - 46) * lift
        E((hx + 2) / 2 + 4, (hy + 40) / 2, 28, 34)   # neck
        E(hx, hy, 26, 25)
        E(sx, sy, 17, 12)
        E(sx + 7.5, sy + 1 + lift * 2, 6, 5)
        E(hx - 9, hy + 11, 10, 10)
        E(hx + 3, hy + 13, 10, 10)
    elif pose == 'walk':
        E(0, 32, 72, 36)
        E(18, 44, 30, 22)
        E(38, 32, 22, 20)
        E(49, 27, 15, 11)
        E(54, 27.5, 5, 4)
        E(34, 42, 8, 8)
        for a0, a1 in ((24, 28), (12, 8), (-18, -14), (-28, -32)):
            L([(a0, 24), (a1, 3)], 11)


def soldier(c, x, y, h, col, d=1, pose='down', hat='helmet', rifle=False, hunch=0.0, var=0):
    u = h / 100.0
    X = lambda a: x + a * u * d
    Y = lambda b: y - b * u
    E = lambda ax, by, w, hh: c.ellipse(X(ax), Y(by), w * u, hh * u, col)
    L = lambda pts, w: c.line([(X(a), Y(b)) for a, b in pts], w * u, col)

    L([(-4, 50), (-6, 3)], 9)
    L([(4, 50), (7, 3)], 9)
    E(-3, 2, 13, 5)
    E(10, 2, 13, 5)
    c.poly([(X(-11 + hunch), Y(82)), (X(11 + hunch), Y(82)), (X(13), Y(42)), (X(-13), Y(42))], col)
    E(1 + hunch, 85, 9, 9)
    hx, hy = 2 + hunch * 1.4, 91 - hunch * 0.6
    E(hx, hy, 14, 15)
    if hat == 'helmet':
        E(hx, hy + 4, 29, 5)
        E(hx, hy + 6, 18, 11)
    elif hat == 'cap':
        E(hx - 1, hy + 6, 17, 7)
        E(hx + 7, hy + 4, 10, 3)
    if rifle:
        c.line([(X(-10), Y(62)), (X(-19), Y(120))], 2.6 * u, col)
    sx = 9 + hunch
    if pose == 'down':
        L([(sx, 80), (12, 52)], 7)
        L([(-9 + hunch, 80), (-12, 52)], 7)
    elif pose == 'salute':
        L([(-9 + hunch, 80), (-12, 52)], 7)
        L([(sx, 80), (19, 84), (9, 94)], 7)
        E(8, 94, 7, 4)
    elif pose == 'hold':
        L([(sx, 80), (17, 66), (11, 60)], 7)
        L([(-6 + hunch, 80), (14, 63)], 7)
    elif pose == 'reach':
        L([(sx, 80), (27, 74)], 7)
        L([(-4 + hunch, 80), (25, 69)], 7)
    elif pose == 'shoulder':
        L([(sx, 80), (14, 96), (8, 104)], 7)
        L([(-9 + hunch, 80), (-12, 52)], 7)
        c.rect(X(-10), Y(100), X(16), Y(116), col)
    elif pose == 'wave':
        L([(-9 + hunch, 80), (-11, 52)], 7)
        tip = (21, 110) if var == 0 else (27, 106)
        mid = (20, 92) if var == 0 else (23, 90)
        L([(sx, 80), mid, tip], 7)
        E(tip[0], tip[1] + 3, 7, 9)


def rim(fn, c, x, y, *a, col, rimcol, off=(0, -3), **kw):
    fn(c, x + off[0], y + off[1], *a, col=rimcol, **kw)
    fn(c, x, y, *a, col=col, **kw)


def truck(c, x, y, w, col):
    u = w / 100.0
    c.rect(x, y - 34 * u, x + 64 * u, y - 8 * u, col)
    c.poly([(x + 64 * u, y - 8 * u), (x + 64 * u, y - 30 * u), (x + 80 * u, y - 30 * u),
            (x + 96 * u, y - 18 * u), (x + 98 * u, y - 8 * u)], col)
    c.poly([(x - 2 * u, y - 34 * u), (x + 32 * u, y - 52 * u), (x + 64 * u, y - 34 * u)], col)
    for wx in (14, 44, 82):
        c.circle(x + wx * u, y - 6 * u, 8 * u, col)


def tent(c, x0, x1, base, apex, col, lit=None, lit_side=1):
    mx = (x0 + x1) / 2
    c.poly([(x0, base), (mx, apex), (x1, base)], col)
    if lit:
        if lit_side > 0:
            c.poly([(mx, apex + 30), (mx + 8, base), (x1 - 40, base)], lit)
        else:
            c.poly([(mx, apex + 30), (mx - 8, base), (x0 + 40, base)], lit)
    c.poly([(mx - 30, base), (mx, base - 110), (mx + 30, base)], col)


