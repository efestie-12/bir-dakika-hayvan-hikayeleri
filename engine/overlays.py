"""On-screen graphics. Each overlay spec is compiled into a draw(img, t) callable.

Times ("at") are seconds from the scene start, or a string:
  "line:N"       start of voice line N            "line:N:0.7"  70% into line N
  "end:-1.5"     1.5 s before the scene ends
Types: chip, counter, big, bars, tag, route, newspapers, title, outro
"""
import math, os
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .base import FW, FH, font_path
from . import lib as A

COL = {'gold': (255, 205, 70), 'ice': (150, 225, 255), 'white': (255, 255, 255), 'red': (226, 70, 50),
       'grey': (138, 160, 184), 'mint': (160, 255, 215), 'cream': (240, 230, 210)}


def color(c):
    if isinstance(c, str):
        if c in COL:
            return COL[c]
        c = c.lstrip('#')
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(c)


@lru_cache(maxsize=64)
def F(name, size):
    return ImageFont.truetype(font_path(name), size)


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def eo(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def back(x):
    x = min(1.0, max(0.0, x))
    return 1 + 2.9 * (x - 1) ** 3 + 1.9 * (x - 1) ** 2


def spaced(text, font, fill, spacing=0, stroke=0, sfill=(0, 0, 0)):
    w = sum(font.getlength(ch) for ch in text) + spacing * max(0, len(text) - 1) + stroke * 2 + 10
    asc, desc = font.getmetrics()
    im = Image.new('RGBA', (int(w) + 4, asc + desc + stroke * 2 + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = stroke + 5
    for ch in text:
        d.text((x, stroke + 5), ch, font=font, fill=fill, stroke_width=stroke, stroke_fill=sfill)
        x += font.getlength(ch) + spacing
    return im


def alpha(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel('A').point(lambda v: int(v * max(0, a))))
    return im


def paste_c(img, im, cx, cy, a=1.0, scale=1.0):
    if a <= 0.01:
        return
    if abs(scale - 1) > 0.01:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    im = alpha(im, a)
    img.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)


def fmt_num(v):
    return f'{int(v):,}'.replace(',', '.')


class Ctx:
    """Timing context for one scene."""
    def __init__(self, dur, line_starts, line_durs):
        self.dur, self.ls, self.ld = dur, line_starts, line_durs
        self.scene = None

    def at(self, spec, default=0.0):
        if spec is None:
            return default
        if isinstance(spec, (int, float)):
            return float(spec)
        p = str(spec).split(':')
        if p[0] == 'line':
            i = min(int(p[1]), len(self.ls) - 1)
            fr = float(p[2]) if len(p) > 2 else 0.0
            return self.ls[i] + self.ld[i] * fr
        if p[0] == 'end':
            return self.dur + float(p[1])
        return float(spec)


# ------------------------------------------------------------------ overlay builders
def b_chip(o, ctx):
    t0 = ctx.at(o.get('at'), 0.15)
    y = o.get('y', 250)
    tx = spaced(o['text'], F('Inter-Bold.otf', 34), (240, 245, 250), 4)
    im = Image.new('RGBA', (tx.width + 66, 74), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, 73], radius=37, fill=(6, 10, 18, 165))
    d.rounded_rectangle([20, 26, 30, 47], radius=5, fill=color(o.get('dot', 'ice')))
    im.alpha_composite(tx, (42, 10))

    def draw(img, t):
        p = eo((t - t0) / 0.35)
        if p <= 0:
            return
        a = alpha(im, p)
        img.paste(a, (int(64 - 40 * (1 - p)), y), a)
    return draw


def b_counter(o, ctx):
    t0, dur = ctx.at(o.get('at'), 0.0), o.get('dur', 1.4)
    y, to = o.get('y', 560), o['to']
    col = color(o.get('color', 'gold'))
    unit = o.get('unit', '')
    label = spaced(o['label'], F('Inter-Bold.otf', 34), (230, 236, 246), 6, 4) if o.get('label') else None
    size = o.get('size', 150)

    def draw(img, t):
        if t < t0:
            return
        p = eo((t - t0) / dur)
        txt = fmt_num(to * p) + (' ' + unit if unit else '')
        im = spaced(txt, F('InterDisplay-Black.otf', size), col, 2, 8)
        a = eo((t - t0) / 0.3)
        paste_c(img, im, FW / 2, y, a, 0.9 + 0.1 * back((t - t0) / 0.4))
        if label:
            paste_c(img, label, FW / 2, y + size * 0.8, a)
    return draw


def b_big(o, ctx):
    t0 = ctx.at(o.get('at'), 0.0)
    y = o.get('y', 560)
    col = color(o.get('color', 'gold'))
    im = spaced(o['text'], F('InterDisplay-Black.otf', o.get('size', 120)), col, o.get('spacing', 4), o.get('stroke', 8))
    sub = spaced(o['sub'], F('Inter-Bold.otf', 34), (240, 236, 226), 5, 4) if o.get('sub') else None
    until = ctx.at(o.get('until'), 1e9)

    def draw(img, t):
        if t < t0 or t > until:
            return
        p = back((t - t0) / 0.45)
        fade = min(1.0, (until - t) / 0.3) if until < 1e8 else 1.0
        paste_c(img, im, o.get('x', FW / 2), y, min(1, p) * fade, 0.55 + 0.45 * p)
        if sub:
            paste_c(img, sub, o.get('x', FW / 2), y + im.height * 0.62, min(1, p) * fade)
    return draw


def b_tag(o, ctx):
    t0 = ctx.at(o.get('at'), 0.0)
    x, y = o.get('x', 0), o.get('y', 0)
    col = color(o.get('color', 'gold'))
    im = spaced(o['text'], F('InterDisplay-Black.otf', o.get('size', 64)), col, 6, 6)
    sub = spaced(o['sub'], F('Inter-Bold.otf', 28), (240, 246, 250), 3, 5, (2, 8, 14)) if o.get('sub') else None
    ring = o.get('ring')
    follow = o.get('follow')

    def draw(img, t):
        nonlocal x, y, ring
        p = back((t - t0) / 0.45)
        if p <= 0:
            return
        if follow:
            sc = ctx.scene
            act = sc.spec['actors'][follow.get('actor', 0)]
            at = ctx.at(act.get('at'), 0.0) if not isinstance(act.get('at'), (int, float)) else act.get('at', 0.0)
            dx = act.get('speed', 0.0) * (t - at)
            fx, fy = sc.to_frame(follow['x'], follow['y'], act.get('factor', 0.6), t, dx)
            r0 = follow.get('r', 95)
            ring = (fx, fy, r0)
            x, y = fx, fy - r0 - follow.get('label_gap', 50)
        if ring:
            ov = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
            r = ring[2] + 6 * math.sin(t * 6)
            ImageDraw.Draw(ov).ellipse([ring[0] - r, ring[1] - r, ring[0] + r, ring[1] + r], outline=col + (230,), width=6)
            ov = alpha(ov, min(1, p))
            img.paste(ov, (0, 0), ov)
        paste_c(img, im, x, y, min(1, p), 0.6 + 0.4 * p)
        if sub:
            paste_c(img, sub, x, y + im.height * 0.75, min(1, p))
    return draw


def b_bars(o, ctx):
    items = o['items']
    mx = o.get('max') or max(i['value'] for i in items)
    y0, gap = o.get('y0', 640), o.get('gap', 320)
    title = spaced(o['title'], F('Inter-ExtraBold.otf', 46), (230, 236, 246), 4) if o.get('title') else None
    t_title = ctx.at(o.get('at'), 0.0)
    unit = o.get('unit', 'km')
    dogs = {}
    for it in items:
        c = Canvas_icon(o.get('icon', 'husky'), color(it.get('color', 'gold')))
        dogs[it['name']] = c

    def draw(img, t):
        if title:
            paste_c(img, title, FW / 2, y0 - 280, eo((t - t_title) / 0.4))
        d = ImageDraw.Draw(img)
        for k, it in enumerate(items):
            ta = ctx.at(it.get('at'), t_title + 0.25 + k)
            if t < ta:
                continue
            y = y0 + k * gap
            p = eo((t - ta) / 1.3)
            x0, maxw = 100, 860
            frac = max(0.02, it['value'] / mx)
            w = maxw * frac * p
            col = color(it.get('color', 'gold'))
            d.rounded_rectangle([x0, y, x0 + maxw, y + 70], radius=35, fill=(28, 34, 46))
            if w > 70:
                d.rounded_rectangle([x0, y, x0 + w, y + 70], radius=35, fill=col)
            nm = spaced(it['name'], F('InterDisplay-Black.otf', 64), col, 6)
            img.paste(nm, (x0, y + 88), nm)
            vt = spaced(f'≈ {fmt_num(it["value"] * p)} {unit}', F('Inter-ExtraBold.otf', 52), (255, 255, 255), 2)
            img.paste(vt, (int(x0 + maxw - vt.width), y + 96), vt)
            dg = dogs[it['name']]
            img.paste(dg, (int(x0 + max(w, 90) - 120), y - 128), dg)
    return draw


def Canvas_icon(kind, col):
    from .base import Canvas, OX, OY
    c = Canvas()
    hexcol = '#%02x%02x%02x' % col
    if kind == 'cat':
        A.cat(c, 0, 0, 120, hexcol)
    elif kind == 'horse':
        A.horse(c, 0, 0, 120, hexcol)
    elif kind == 'elephant':
        A.elephant(c, 0, 0, 100, hexcol)
    elif kind == 'bird':
        A.bird(c, 0, 0, 100, hexcol)
    else:
        A.husky(c, 0, 0, 120, hexcol)
    return c.done().crop((OX - 70, OY - 130, OX + 90, OY + 10))


def b_route(o, ctx):
    pts = [(p[0], p[1]) for p in o['points']]
    names = {i: p[2] for i, p in enumerate(o['points']) if len(p) > 2 and p[2]}
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    t0 = ctx.at(o.get('at'), 0.3)
    dur = (ctx.at(o['dur_to']) - t0) if o.get('dur_to') else o.get('dur', 5.0)
    km_total = o.get('total', 0)
    labels = {i: spaced(n, F('Inter-ExtraBold.otf', 40), (240, 246, 255), 5, 5, (4, 10, 20)) for i, n in names.items()}
    extra = [(spaced(e['text'], F('Inter-Bold.otf', e.get('size', 26)), (110, 170, 215), 6), e['x'], e['y'])
             for e in o.get('labels', [])]

    def pos(k):
        dist = k * total
        for i, s in enumerate(seg):
            if dist <= s:
                a = dist / s
                p0, p1 = pts[i], pts[i + 1]
                return (p0[0] + (p1[0] - p0[0]) * a, p0[1] + (p1[1] - p0[1]) * a), i
            dist -= s
        return pts[-1], len(seg) - 1

    def draw(img, t):
        if t < t0 - 0.1:
            return
        k = ease((t - t0) / dur)
        ov = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            n = max(1, int(seg[i] / 16))
            for j in range(n):
                q = j / n
                x, y = p0[0] + (p1[0] - p0[0]) * q, p0[1] + (p1[1] - p0[1]) * q
                d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(120, 160, 200, 140))
        (hx, hy), idx = pos(k)
        trail = pts[:idx + 1] + [(hx, hy)]
        glow = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
        ImageDraw.Draw(glow).line(trail, fill=(255, 190, 60, 255), width=22, joint='curve')
        glow = glow.filter(ImageFilter.GaussianBlur(10))
        ov.alpha_composite(glow)
        d.line(trail, fill=(255, 214, 110, 255), width=8, joint='curve')
        for i, (x, y) in enumerate(pts):
            on = i <= idx
            r = 13 if on else 9
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 205, 70, 255) if on else (60, 90, 120, 255),
                      outline=(10, 16, 26, 255), width=3)
        pr = 26 + 8 * math.sin(t * 8)
        d.ellipse([hx - pr, hy - pr, hx + pr, hy + pr], outline=(255, 230, 160, 200), width=4)
        d.ellipse([hx - 12, hy - 12, hx + 12, hy + 12], fill=(255, 255, 255, 255))
        img.paste(ov, (0, 0), ov)
        for i, im in labels.items():
            x, y = pts[i]
            a = 1.0 if i == 0 else 0.5 + 0.5 * ease((k - 0.9) / 0.1) if i == len(pts) - 1 else 1.0
            paste_c(img, im, x - 10, y - 58, a)
        for im, x, y in extra:
            paste_c(img, im, x, y, 0.9)
        if km_total:
            paste_c(img, spaced(f'{fmt_num(km_total * k)} / {fmt_num(km_total)} KM', F('Inter-ExtraBold.otf', 40),
                                (255, 214, 110), 3, 5, (4, 10, 20)), FW / 2, 300)
    return draw


def b_newspapers(o, ctx):
    t0 = ctx.at(o.get('at'), 0.1)
    step = o.get('step', 0.75)
    fade_at = ctx.at(o.get('fade_at'), 1e9)
    dim_on = o.get('dim', True)
    papers = [A.newspaper(it['headline'], it.get('sub', ''), i + 1, masthead=o.get('masthead', 'THE DAILY NEWS'),
                          date=o.get('date', '')) for i, it in enumerate(o['items'])]
    n = len(papers)

    def draw(img, t):
        dark = ease((t - fade_at) / 0.5) if t > fade_at else 0.0
        for i, pim in enumerate(papers):
            ti = t0 + i * step
            if t < ti:
                continue
            p = eo((t - ti) / 0.55)
            ang = (1 - p) * (40 - 30 * i) + (-6 + 6 * i)
            sc = 1.8 - 0.8 * p + 0.03 * (t - ti)
            cx = FW / 2 + (1 - p) * (-600 + 600 * i) + (i - (n - 1) / 2) * 40
            cy = 760 + (1 - p) * (-300) + (i - (n - 1) / 2) * 30
            im = pim.rotate(ang, resample=Image.BICUBIC, expand=True)
            paste_c(img, im, cx, cy, (1 - 0.75 * dark) * min(1, p * 2), sc * 0.95)
        if dark > 0 and dim_on:
            ov = Image.new('RGBA', (FW, FH), (8, 6, 4, int(180 * dark)))
            img.paste(ov, (0, 0), ov)
    return draw


def b_title(o, ctx):
    t0 = ctx.at(o.get('at'), 0.4)
    y = o.get('y', 560)
    im = spaced(o['text'], F('InterDisplay-Black.otf', o.get('size', 170)), color(o.get('color', 'gold')), o.get('spacing', 22), 0)
    sub = spaced(o['sub'], F('Inter-Medium.otf', 54), (230, 240, 236), 4) if o.get('sub') else None

    def draw(img, t):
        p = eo((t - t0) / 0.8)
        paste_c(img, im, FW / 2, y, p)
        if sub:
            paste_c(img, sub, FW / 2, y + 130, p)
    return draw


CHANNEL = 'Bir Dakika!'
OUTRO_CTA = 'Her gün gerçek bir hayvan hikâyesi için TAKİP ET'
OUTRO_FOOTER = f'{CHANNEL} · Gerçek hikâye · Görseller temsilidir'


def fit_w(im, maxw=1000):
    """Metin görselini ekran genişliğine sığacak şekilde küçültür."""
    if im is None or im.width <= maxw:
        return im
    k = maxw / im.width
    return im.resize((maxw, max(1, int(im.height * k))), Image.LANCZOS)


def b_outro(o, ctx):
    t0 = ctx.at(o.get('at'), 0.0)
    cta_t = o.get('cta', OUTRO_CTA)
    foot_t = o.get('footer', OUTRO_FOOTER)
    cta = fit_w(spaced(cta_t, F('Inter-ExtraBold.otf', 38), (255, 255, 255), 1, 5, (0, 0, 0))) if cta_t else None
    foot = fit_w(spaced(foot_t, F('Inter-Regular.otf', 30), (170, 190, 190), 1)) if foot_t else None

    def draw(img, t):
        q = eo((t - t0) / 0.5)
        if q <= 0:
            return
        if foot:
            paste_c(img, foot, FW / 2, 1790, q)
        if cta:
            paste_c(img, cta, FW / 2, 1680, q, 0.9 + 0.1 * back((t - t0) / 0.5))
        if t > ctx.dur - 0.6:
            k = (t - (ctx.dur - 0.6)) / 0.6
            img.paste(Image.blend(img, Image.new('RGB', (FW, FH), (0, 0, 0)), min(1, k)))
    return draw


def b_cracks(o, ctx):
    t0, dur = ctx.at(o.get('at'), 0.0), o.get('dur', 1.0)
    paths = A.crack_paths(o.get('seed', 7), o['x'], o['y'], n=o.get('n', 6), length=o.get('length', 520))
    water = o.get('water')

    def draw(img, t):
        if t < t0:
            return
        p = eo((t - t0) / dur)
        ov = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        if water:
            w = water.get('width', 360) * p
            d.polygon([(-50, 1330 - 30 * p), (w * 0.6, 1300 - 20 * p), (w, 1420), (w * 0.7, 1700), (-50, 1700)],
                      fill=(3, 8, 16, 255))
        g = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        for path in paths:
            n = max(2, int(len(path) * p))
            gd.line(path[:n], fill=(120, 220, 255, 255), width=14)
            d.line(path[:n], fill=(230, 250, 255, 255), width=4)
        g = g.filter(ImageFilter.GaussianBlur(8))
        img.paste(g, (0, 0), g)
        img.paste(ov, (0, 0), ov)
    return draw


BUILDERS = {'cracks': b_cracks, 'chip': b_chip, 'counter': b_counter, 'big': b_big, 'bars': b_bars, 'tag': b_tag, 'route': b_route,
            'newspapers': b_newspapers, 'title': b_title, 'outro': b_outro}


def compile_overlays(specs, ctx):
    out = []
    for o in specs or []:
        if o['type'] not in BUILDERS:
            raise ValueError(f"unknown overlay type: {o['type']}")
        out.append(BUILDERS[o['type']](o, ctx))
    return out
