"""Figure & prop library. All coordinates are frame coords (1080x1920); Canvas adds the margin."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from .base import (Canvas, gradient, add_glow, glow_layer, to_img, grain_tex, ridge, bear, soldier,
                   truck, tent, FW, FH, LW, LH, OX, OY, hexc, font_path)
import os

# ------------------------------------------------------------------ figures
def husky(c, x, y, h, col, d=1, phase=None, tail=True):
    """Side-view sled dog. phase=None -> standing; 0..1 -> gallop cycle."""
    u = h / 100.0
    X = lambda a: x + a * u * d
    Y = lambda b: y - b * u
    E = lambda ax, by, w, hh: c.ellipse(X(ax), Y(by), w * u, hh * u, col)
    L = lambda pts, w: c.line([(X(a), Y(b)) for a, b in pts], w * u, col)
    bob = 0 if phase is None else 3 * math.sin(phase * 4 * math.pi)
    by = 52 + bob
    E(0, by, 72, 30)
    E(24, by + 1, 30, 32)
    E(-24, by - 1, 30, 28)
    c.poly([(X(16), Y(by + 10)), (X(30), Y(by + 26)), (X(44), Y(by + 22)), (X(36), Y(by + 2))], col)
    hx, hy = 42, by + 22
    E(hx, hy, 24, 20)
    c.poly([(X(hx + 4), Y(hy + 6)), (X(hx + 21), Y(hy - 1)), (X(hx + 21), Y(hy - 6)), (X(hx + 4), Y(hy - 9))], col)
    E(hx + 21, hy - 3, 5, 5)
    c.poly([(X(hx - 9), Y(hy + 6)), (X(hx - 5), Y(hy + 22)), (X(hx - 1), Y(hy + 7))], col)
    c.poly([(X(hx - 2), Y(hy + 7)), (X(hx + 3), Y(hy + 21)), (X(hx + 6), Y(hy + 6))], col)
    if tail:
        L([(-34, by + 6), (-44, by + 18), (-38, by + 28), (-28, by + 24)], 8)
    legs = [(22, 1, 0.0), (16, 1, 0.5), (-22, -1, 0.15), (-16, -1, 0.65)]
    for hx0, side, off in legs:
        hip = (hx0, by - 10)
        if phase is None:
            L([hip, (hx0 + 1, 20), (hx0 + 2, 2)], 7)
            E(hx0 + 4, 1.5, 9, 4)
        else:
            a = 2 * math.pi * (phase + off)
            dx = 16 * math.sin(a)
            lift = max(0.0, 10 * math.cos(a))
            knee = (hx0 + dx * 0.5 + (4 if side > 0 else -4), 20 + lift * 0.6)
            paw = (hx0 + dx, 2 + lift)
            L([hip, knee, paw], 7)


def musher(c, x, y, h, col, d=1, lean=0.0):
    u = h / 100.0
    X = lambda a: x + a * u * d
    Y = lambda b: y - b * u
    E = lambda ax, by, w, hh: c.ellipse(X(ax), Y(by), w * u, hh * u, col)
    L = lambda pts, w: c.line([(X(a), Y(b)) for a, b in pts], w * u, col)
    L([(-4, 46), (-6, 3)], 10)
    L([(5, 46), (7, 3)], 10)
    E(-2, 2, 15, 6)
    E(9, 2, 15, 6)
    c.poly([(X(-15 + lean), Y(84)), (X(13 + lean), Y(84)), (X(18), Y(40)), (X(-17), Y(40))], col)
    E(lean, 88, 30, 30)       # fur hood
    L([(9 + lean, 78), (22, 62), (27, 58)], 9)
    L([(-8 + lean, 78), (14, 60), (24, 56)], 9)


def sled(c, x, y, w, col, d=1):
    u = w / 100.0
    X = lambda a: x + a * u * d
    Y = lambda b: y - b * u
    c.line([(X(0), Y(2)), (X(88), Y(2)), (X(100), Y(10))], 3.2 * u, col)
    c.poly([(X(14), Y(10)), (X(84), Y(10)), (X(80), Y(26)), (X(16), Y(26))], col)
    c.line([(X(6), Y(2)), (X(6), Y(44))], 2.6 * u, col)
    c.line([(X(6), Y(44)), (X(14), Y(46))], 2.6 * u, col)
    for px in (24, 46, 68):
        c.line([(X(px), Y(2)), (X(px), Y(10))], 2 * u, col, caps=False)


def team(c, x, y, h, col, n=5, phase=0.0, d=1, gap=96, sled_w=170, musher_h=None):
    """Sled at x (rear), dogs extend in direction d."""
    u = h / 100.0
    sled(c, x, y, sled_w, col, d)
    musher(c, x + 2 * d, y - 4, musher_h or h * 1.55, col, d=d, lean=4)
    x0 = x + (sled_w + 30 * u) * d
    c.line([(x + sled_w * 0.95 * d, y - 20 * u), (x0 + (n - 1) * gap * u * d + 30 * u * d, y - 54 * u)],
           2.2 * u, col, caps=False)
    for i in range(n):
        husky(c, x0 + i * gap * u * d, y, h, col, d=d, phase=(phase + i * 0.17) % 1.0)


def spruce(c, x, y, h, col):
    w = h * 0.42
    for k in range(5):
        top = y - h + k * h * 0.17
        ww = w * (0.35 + k * 0.17)
        c.poly([(x, top), (x + ww / 2, top + h * 0.3), (x - ww / 2, top + h * 0.3)], col)
    c.rect(x - h * 0.03, y - h * 0.08, x + h * 0.03, y, col)


def bare_tree(c, x, y, h, col, seed=0):
    rnd = random.Random(seed)

    def br(x0, y0, ang, ln, w, depth):
        x1 = x0 + ln * math.cos(ang)
        y1 = y0 - ln * math.sin(ang)
        c.line([(x0, y0), (x1, y1)], w, col)
        if depth > 0:
            for s in (-1, 1):
                br(x1, y1, ang + s * rnd.uniform(0.3, 0.7), ln * rnd.uniform(0.6, 0.78), w * 0.68, depth - 1)
    br(x, y, math.pi / 2 + rnd.uniform(-0.08, 0.08), h * 0.38, h * 0.05, 5)


def house(c, x, y, w, h, col, win='#ffc766', snow='#cfdcec', steeple=False):
    c.rect(x, y - h, x + w, y, col)
    c.poly([(x - w * 0.08, y - h), (x + w / 2, y - h - w * 0.42), (x + w * 1.08, y - h)], col)
    c.poly([(x - w * 0.1, y - h + 2), (x + w / 2, y - h - w * 0.44), (x + w * 1.1, y - h + 2),
            (x + w * 1.0, y - h + 10), (x + w / 2, y - h - w * 0.34), (x, y - h + 10)], snow)
    c.rect(x + w * 0.68, y - h - w * 0.36, x + w * 0.8, y - h - w * 0.12, col)
    if steeple:
        c.rect(x + w * 0.38, y - h - w * 0.9, x + w * 0.62, y - h - w * 0.2, col)
        c.poly([(x + w * 0.34, y - h - w * 0.9), (x + w / 2, y - h - w * 1.35), (x + w * 0.66, y - h - w * 0.9)], col)
    for wx in (0.18, 0.6):
        c.rect(x + w * wx, y - h * 0.62, x + w * (wx + 0.2), y - h * 0.32, win)



# ------------------------------------------------------------------ dynamic helpers
def aurora(t, w=270, h=480, strength=1.0, y0=0.12, y1=0.5):
    """Low-res animated aurora as RGBA image at frame size."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn = xx / w
    yn = yy / h
    a = np.zeros((h, w), np.float32)
    col = np.zeros((h, w, 3), np.float32)
    for k, (amp, fr, sp, ph, base) in enumerate(((0.06, 2.2, 0.25, 0.0, 0.26), (0.05, 3.1, -0.18, 1.7, 0.33),
                                                  (0.04, 1.6, 0.12, 3.1, 0.2))):
        cy = y0 + (y1 - y0) * base / 0.4 + amp * np.sin(2 * np.pi * (fr * xn + sp * t) + ph) \
            + 0.02 * np.sin(2 * np.pi * (6 * xn - 0.4 * t) + k)
        dy = yn - cy
        band = np.where(dy < 0, np.exp(-(dy / 0.11) ** 2), np.exp(-(dy / 0.018) ** 2))
        flick = 0.75 + 0.25 * np.sin(2 * np.pi * (9 * xn + 0.5 * t + k))
        a += band * flick * (0.55 - 0.1 * k)
    a = np.clip(a * strength, 0, 1)
    g = np.clip((yn - y0) / (y1 - y0), 0, 1)
    col[..., 0] = 60 + 120 * (1 - g) ** 3
    col[..., 1] = 255 - 40 * (1 - g)
    col[..., 2] = 160 + 60 * (1 - g)
    out = np.dstack([col, a[..., None] * 200]).astype(np.uint8)
    return Image.fromarray(out, 'RGBA').resize((FW, FH), Image.BILINEAR)


def crack_paths(seed, x, y, n=5, length=420, spread=1.0):
    rnd = random.Random(seed)
    paths = []

    def grow(px, py, ang, ln, depth):
        pts = [(px, py)]
        steps = int(ln / 18)
        for _ in range(steps):
            ang += rnd.uniform(-0.45, 0.45)
            px += 18 * math.cos(ang)
            py += 18 * math.sin(ang) * 0.35
            pts.append((px, py))
            if depth > 0 and rnd.random() < 0.12:
                grow(px, py, ang + rnd.choice((-1, 1)) * rnd.uniform(0.6, 1.2), ln * 0.45, depth - 1)
        paths.append(pts)
    for k in range(n):
        grow(x, y, k / n * 2 * math.pi * spread + rnd.uniform(-0.3, 0.3), length * rnd.uniform(0.6, 1.2), 2)
    return paths


def newspaper(headline, sub, seed=0, w=520, h=680, masthead='THE NORTHERN DISPATCH', date='FEBRUARY 1925'):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (w, h), (232, 222, 196, 255))
    d = ImageDraw.Draw(im)
    serif_b = font_path('DejaVuSerif-Bold.ttf')
    serif = font_path('DejaVuSerifCondensed.ttf')
    f1 = ImageFont.truetype(serif_b, 34)
    f2 = ImageFont.truetype(serif_b, 66)
    f3 = ImageFont.truetype(serif, 22)
    d.text((w / 2, 40), masthead, font=f1, fill=(30, 26, 20), anchor='mm')
    d.line([(24, 66), (w - 24, 66)], fill=(30, 26, 20), width=3)
    d.text((w / 2, 82), date, font=f3, fill=(60, 50, 40), anchor='mm')
    d.line([(24, 98), (w - 24, 98)], fill=(30, 26, 20), width=1)
    y = 108
    for line in headline.split('\n'):
        d.text((w / 2, y + 36), line, font=f2, fill=(20, 16, 12), anchor='mm')
        y += 74
    d.text((w / 2, y + 22), sub, font=f3, fill=(50, 40, 30), anchor='mm')
    y += 50
    # photo block
    d.rectangle([30, y, w - 30, y + 210], fill=(70, 62, 52))
    ph = Canvas()
    img_dog = Image.new('RGBA', (w - 60, 210), (70, 62, 52, 255))
    dd = ImageDraw.Draw(img_dog)
    # tiny dog silhouette (simple shapes)
    cx, cy = (w - 60) / 2, 160
    dd.ellipse([cx - 80, cy - 60, cx + 60, cy - 10], fill=(28, 24, 20))
    dd.ellipse([cx + 30, cy - 95, cx + 95, cy - 45], fill=(28, 24, 20))
    dd.polygon([(cx + 40, cy - 85), (cx + 48, cy - 120), (cx + 60, cy - 88)], fill=(28, 24, 20))
    dd.polygon([(cx + 62, cy - 88), (cx + 74, cy - 118), (cx + 80, cy - 85)], fill=(28, 24, 20))
    for lx in (-60, -40, 20, 40):
        dd.rectangle([cx + lx, cy - 20, cx + lx + 12, cy + 30], fill=(28, 24, 20))
    im.paste(img_dog, (30, y))
    y += 228
    colw = (w - 60) / 3
    for col in range(3):
        yy = y
        while yy < h - 24:
            ln = rnd.uniform(0.6, 1.0) * (colw - 14)
            d.line([(30 + col * colw, yy), (30 + col * colw + ln, yy)], fill=(120, 110, 95), width=5)
            yy += 14
    return im


# ------------------------------------------------------------------ more animals
def _helpers(c, x, y, h, d):
    u = h / 100.0
    X = lambda a: x + a * u * d
    Y = lambda b: y - b * u
    E = lambda ax, by, w, hh, col: c.ellipse(X(ax), Y(by), w * u, hh * u, col)
    L = lambda pts, w, col: c.line([(X(a), Y(b)) for a, b in pts], w * u, col)
    P = lambda pts, col: c.poly([(X(a), Y(b)) for a, b in pts], col)
    return u, X, Y, E, L, P


def cat(c, x, y, h, col, d=1, pose='sit', phase=None):
    u, X, Y, E, L, P = _helpers(c, x, y, h, d)
    if pose == 'sit':
        E(-4, 22, 52, 40, col)
        E(2, 38, 36, 50, col)
        E(8, 66, 30, 26, col)
        P([(-3, 72), (-1, 92), (7, 78)], col)
        P([(10, 78), (17, 92), (20, 72)], col)
        L([(12, 44), (14, 3)], 7, col)
        L([(4, 44), (5, 3)], 7, col)
        L([(-24, 8), (-38, 4), (-46, 14), (-42, 26)], 6, col)
    else:
        bob = 0 if phase is None else 2 * math.sin(phase * 4 * math.pi)
        by = 40 + bob
        E(0, by, 64, 24, col)
        E(34, by + 12, 26, 22, col)
        P([(25, by + 18), (27, by + 34), (33, by + 22)], col)
        P([(36, by + 22), (41, by + 34), (44, by + 18)], col)
        L([(-30, by + 2), (-42, by + 22), (-38, by + 38)], 6, col)
        for hx0, off in ((22, 0.0), (16, 0.5), (-22, 0.15), (-16, 0.65)):
            if phase is None:
                L([(hx0, by - 6), (hx0 + 1, 2)], 6, col)
            else:
                a = 2 * math.pi * (phase + off)
                L([(hx0, by - 6), (hx0 + 10 * math.sin(a), 2 + max(0, 6 * math.cos(a)))], 6, col)


def horse(c, x, y, h, col, d=1, phase=None, head_down=False):
    u, X, Y, E, L, P = _helpers(c, x, y, h, d)
    bob = 0 if phase is None else 2.5 * math.sin(phase * 4 * math.pi)
    by = 62 + bob
    E(0, by, 84, 36, col)
    E(30, by + 2, 34, 38, col)
    E(-30, by, 34, 34, col)
    hy = by + (10 if head_down else 40)
    P([(22, by + 12), (40, hy - 2), (52, hy + 2), (44, by + 4)], col)
    E(52, hy, 18, 16, col)
    c.poly([(X(48), Y(hy + 6)), (X(70), Y(hy - 8)), (X(72), Y(hy - 16)), (X(56), Y(hy - 8))], col)
    E(66, hy - 12, 14, 11, col)
    P([(46, hy + 6), (48, hy + 16), (52, hy + 7)], col)
    L([(-42, by + 8), (-52, by - 14), (-50, by - 30)], 7, col)
    for hx0, off in ((30, 0.0), (22, 0.5), (-30, 0.2), (-22, 0.7)):
        if phase is None:
            L([(hx0, by - 12), (hx0 + 1, 22), (hx0, 3)], 6, col)
        else:
            a = 2 * math.pi * (phase + off)
            dx = 14 * math.sin(a)
            lift = max(0.0, 9 * math.cos(a))
            L([(hx0, by - 12), (hx0 + dx * 0.5, 24 + lift), (hx0 + dx, 3 + lift)], 6, col)
        E(hx0 + (0 if phase is None else 14 * math.sin(2 * math.pi * (phase + off))), 2 + (0 if phase is None else max(0, 9 * math.cos(2 * math.pi * (phase + off)))), 8, 5, col)


def bird(c, x, y, h, col, d=1, wing=None):
    """Pigeon/dove. wing=None perched, 0..1 flap phase."""
    u, X, Y, E, L, P = _helpers(c, x, y, h, d)
    E(0, 40, 58, 30, col)
    E(24, 56, 22, 20, col)
    P([(33, 58), (42, 55), (33, 52)], col)
    P([(-24, 44), (-50, 52), (-52, 38), (-24, 34)], col)
    if wing is None:
        P([(-14, 50), (18, 52), (8, 34), (-26, 38)], col)
        L([(2, 26), (2, 6)], 3, col)
        L([(8, 26), (10, 6)], 3, col)
    else:
        k = math.sin(wing * 2 * math.pi)
        tip = 40 + 50 * k
        P([(-10, 46), (16, 48), (4, tip + 10), (-30, tip)], col)


def elephant(c, x, y, h, col, d=1, phase=None):
    u, X, Y, E, L, P = _helpers(c, x, y, h, d)
    E(0, 60, 104, 62, col)
    E(46, 70, 40, 44, col)
    E(36, 70, 30, 44, col)
    L([(60, 64), (70, 40), (68, 18), (74, 10)], 12, col)
    P([(58, 56), (74, 50), (72, 46), (58, 52)], col)
    L([(-50, 70), (-56, 50)], 3, col)
    for hx0, off in ((30, 0.0), (18, 0.5), (-34, 0.2), (-22, 0.7)):
        dx = 0 if phase is None else 8 * math.sin(2 * math.pi * (phase + off))
        c.rect(X(hx0 - 7 + dx), Y(40), X(hx0 + 7 + dx), Y(0), col)


def person(c, x, y, h, col, d=1, hat='none', arm='down', coat=True, var=0):
    """Generic civilian. hat: none|hat|cap|hood|scarf. arm: down|wave|point|hold|pocket."""
    u, X, Y, E, L, P = _helpers(c, x, y, h, d)
    L([(-4, 48), (-6, 3)], 9, col)
    L([(4, 48), (7, 3)], 9, col)
    E(-3, 2, 13, 5, col)
    E(10, 2, 13, 5, col)
    bot = 34 if coat else 46
    P([(-11, 82), (11, 82), (15 if coat else 12, bot), (-15 if coat else -12, bot)], col)
    E(1, 85, 9, 9, col)
    E(2, 91, 14, 15, col)
    if hat == 'hat':
        E(2, 97, 26, 4, col)
        c.rect(X(-5), Y(98), X(9), Y(106), col)
    elif hat == 'cap':
        E(1, 97, 17, 7, col)
        E(9, 95, 10, 3, col)
    elif hat == 'hood':
        E(1, 92, 22, 22, col)
    L([(-9, 80), (-12, 52)], 7, col)
    if arm == 'down':
        L([(9, 80), (12, 52)], 7, col)
    elif arm == 'wave':
        tip = (21, 110) if var == 0 else (27, 106)
        L([(9, 80), (20, 92), tip], 7, col)
    elif arm == 'point':
        L([(9, 80), (30, 82)], 7, col)
    elif arm == 'hold':
        L([(9, 80), (17, 66), (11, 60)], 7, col)
    elif arm == 'pocket':
        L([(9, 80), (13, 62), (8, 56)], 7, col)


# ------------------------------------------------------------------ more props
def fence(c, x0, x1, y, h, col, step=34):
    c.rect(x0, y - h + 10, x1, y - h + 22, col)
    c.rect(x0, y - 20, x1, y - 8, col)
    fx = x0 + 10
    while fx < x1:
        c.rect(fx, y - h, fx + 7, y, col)
        c.poly([(fx - 3, y - h + 2), (fx + 3.5, y - h - 14), (fx + 10, y - h + 2)], col)
        fx += step


def lamp_post(c, x, y, h, col):
    c.line([(x, y), (x, y - h)], max(4, h * 0.03), col)
    c.circle(x, y - h - h * 0.025, h * 0.05, col)


def rock(c, x, y, w, h, col):
    c.poly([(x - w / 2, y), (x - w * 0.42, y - h * 0.8), (x - w * 0.2, y - h), (x + w * 0.3, y - h * 0.98),
            (x + w * 0.45, y - h * 0.7), (x + w / 2, y)], col)


def ship(c, x, y, w, col, lights='#e8c890'):
    u = w / 100.0
    c.poly([(x, y - 10 * u), (x + 100 * u, y - 10 * u), (x + 92 * u, y + 6 * u), (x + 6 * u, y + 6 * u)], col)
    c.rect(x + 14 * u, y - 24 * u, x + 70 * u, y - 10 * u, col)
    c.rect(x + 24 * u, y - 34 * u, x + 54 * u, y - 24 * u, col)
    c.rect(x + 36 * u, y - 50 * u, x + 44 * u, y - 34 * u, col)
    c.line([(x + 80 * u, y - 10 * u), (x + 80 * u, y - 56 * u)], 1.2 * u, col)
    c.line([(x + 80 * u, y - 56 * u), (x + 96 * u, y - 10 * u)], 0.5 * u, col, caps=False)
    for px in range(int(x + 18 * u), int(x + 68 * u), max(4, int(6 * u))):
        c.circle(px, y - 17 * u, 0.9 * u, lights)


def train(c, x, y, w, col, cars=2, lights='#ffd27a'):
    u = w / 100.0
    c.rect(x, y - 30 * u, x + 40 * u, y - 6 * u, col, r=3 * u)
    c.rect(x + 28 * u, y - 44 * u, x + 40 * u, y - 30 * u, col)
    c.rect(x + 6 * u, y - 40 * u, x + 12 * u, y - 30 * u, col)
    c.poly([(x, y - 10 * u), (x - 8 * u, y - 4 * u), (x, y - 4 * u)], col)
    for k in range(cars):
        cx = x + 44 * u + k * 46 * u
        c.rect(cx, y - 32 * u, cx + 42 * u, y - 6 * u, col, r=2 * u)
        for wx in range(3):
            c.rect(cx + 5 * u + wx * 12 * u, y - 26 * u, cx + 12 * u + wx * 12 * u, y - 18 * u, lights)
    for k in range(2 + cars * 2):
        c.circle(x + 8 * u + k * 21 * u, y - 4 * u, 4 * u, col)
    c.rect(x - 60 * u, y, x + (50 + 46 * cars) * u, y + 2 * u, col)


def station(c, x, y, w, h, col, win='#ffd27a', clock=True):
    c.rect(x, y - h, x + w, y, col)
    c.poly([(x - w * 0.06, y - h), (x + w / 2, y - h - w * 0.22), (x + w * 1.06, y - h)], col)
    c.rect(x - w * 0.15, y - h * 0.45, x + w * 1.15, y - h * 0.4, col)
    for k in range(4):
        c.rect(x + w * (0.1 + k * 0.22), y - h * 0.8, x + w * (0.22 + k * 0.22), y - h * 0.55, win)
    if clock:
        c.circle(x + w / 2, y - h - w * 0.08, w * 0.06, '#f4ead0')


def city(c, y, col, win='#e9c77a', seed=4, hmin=160, hmax=520):
    rnd = random.Random(seed)
    x = -110
    while x < 1200:
        w = rnd.randint(50, 120)
        hh = rnd.randint(hmin, hmax)
        c.rect(x, y - hh, x + w, y + 200, col)
        if win:
            for wy in range(int(y - hh + 16), int(y - 10), 26):
                for wx in range(int(x + 8), int(x + w - 10), 18):
                    if rnd.random() < 0.28:
                        c.rect(wx, wy, wx + 7, wy + 10, win)
        x += w + rnd.randint(4, 30)


def floes(c, y0, y1, col1, col2, seed=9, n=70):
    rnd = random.Random(seed)
    for _ in range(n):
        yy = rnd.uniform(y0 + 8, y1)
        xx = rnd.uniform(-100, 1180)
        ww = rnd.uniform(40, 220) * (yy - y0 + 100) / 300
        c.poly([(xx, yy), (xx + ww, yy - 3), (xx + ww * 1.1, yy + 5), (xx + ww * 0.1, yy + 8)],
               col1 if rnd.random() < 0.6 else col2)
