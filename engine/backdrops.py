"""Declarative backdrops: a preset name or spec dict -> list of (RGBA layer, parallax factor).

Spec keys (all optional when a preset is used):
  sky     : [[y, '#hex'], ...] vertical gradient stops (y in frame coords)
  glow    : [x, y, r, '#hex', strength, squash]
  stars   : int  (number of stars)
  moon    : [x, y, r]            crescent moon
  sun     : [x, y, r, '#hex']
  far     : {type: city|ridge|spruce|none, color, y, ...}
  mid     : {type: bare_trees|spruce|houses|acacia|rocks|none, color, y, ...}
  ground  : {type: ridge|flat|water|ice, color, y, amp, color2}
  fg      : {color, y}           dark foreground strip
  aurora  : bool (consumed by the scene runner, not drawn here)
"""
import copy, math, random
import numpy as np
from .base import (Canvas, gradient, add_glow, to_img, grain_tex, ridge,
                   FW, FH, LW, LH, OX, OY)
from . import lib as A

PRESETS = {
    'night_city': dict(
        sky=[(-200, '#04060e'), (700, '#0b1430'), (1150, '#1c2547')],
        glow=(540, 1060, 520, '#3a4a78', 0.55, 0.5), stars=160,
        far=dict(type='city', color='#0d1328', win='#e9c77a', y=1120),
        mid=dict(type='bare_trees', color='#05070f', y=1230),
        ground=dict(type='ridge', color='#2a3656', y=1215, amp=12),
        fg=dict(color='#0c111f', y=1260)),
    'snow_village': dict(
        sky=[(-200, '#0a0e18'), (800, '#1b2436'), (1150, '#39445c')],
        glow=(540, 1050, 600, '#56627e', 0.5, 0.4),
        far=dict(type='spruce', color='#1e2638', y=1110),
        mid=dict(type='houses', color='#121826', y=1210),
        ground=dict(type='ridge', color='#8492ad', y=1215, amp=10),
        fg=dict(color='#c3cee0', y=1290)),
    'ice_night': dict(
        sky=[(-200, '#020611'), (600, '#06142a'), (1100, '#0f2a3e'), (1200, '#1e3c4c')], stars=300,
        far=dict(type='ridge', color='#0a1a28', y=1080, amp=90, f1=0.006),
        mid=dict(type='spruce', color='#06111a', y=1190, h0=160, h1=260, step=120),
        ground=dict(type='ice', color='#5c7a8c', color2='#2b4157', y=1185),
        aurora=True),
    'desert_sunset': dict(
        sky=[(-200, '#1e1633'), (380, '#45213f'), (760, '#b0463a'), (1060, '#f0a050'), (1140, '#ffd27a')],
        glow=(560, 1020, 430, '#ffcf80', 0.65, 1.0), sun=(560, 1020, 150, '#ffe6ad'),
        far=dict(type='ridge', color='#a9573a', y=1135, amp=22, f1=0.003),
        mid=dict(type='ridge', color='#5e2822', y=1185, amp=34),
        ground=dict(type='ridge', color='#2a1210', y=1245, amp=20),
        fg=dict(color='#140807', y=1310)),
    'savanna_sunset': dict(
        sky=[(-200, '#2a1b3a'), (400, '#6a2f3c'), (800, '#d0603a'), (1060, '#f8b05a'), (1140, '#ffdc8a')],
        glow=(540, 1040, 480, '#ffd08a', 0.7, 0.9), sun=(540, 1040, 130, '#fff0c0'),
        far=dict(type='ridge', color='#7a3a2a', y=1130, amp=30, f1=0.004),
        mid=dict(type='acacia', color='#2a1410', y=1190),
        ground=dict(type='ridge', color='#3a1c12', y=1215, amp=14),
        fg=dict(color='#160a06', y=1290)),
    'ocean_dusk': dict(
        sky=[(-200, '#111a27'), (450, '#2a3b4f'), (850, '#7c888c'), (1080, '#d8b888'), (1130, '#ecd0a0')],
        glow=(760, 1090, 420, '#ffd9a0', 0.5, 0.6),
        far=dict(type='none'),
        mid=dict(type='none'),
        ground=dict(type='water', color='#1c2731', color2='#8a8c82', y=1120),
        fg=dict(color='#0a0e13', y=1290)),
    'forest_dawn': dict(
        sky=[(-200, '#2a3a52'), (500, '#6a7a8a'), (900, '#e0a870'), (1100, '#fbd9a0')],
        glow=(540, 1060, 520, '#ffe0b0', 0.6, 0.8),
        far=dict(type='spruce', color='#2a3a34', y=1120, h0=160, h1=280, step=40),
        mid=dict(type='spruce', color='#14201c', y=1200, h0=240, h1=420, step=90),
        ground=dict(type='ridge', color='#0c1410', y=1230, amp=10),
        fg=dict(color='#070c09', y=1300)),
    'mountain_dawn': dict(
        sky=[(-200, '#2a3556'), (450, '#6a6f94'), (850, '#e29a7a'), (1100, '#fbd4a0')],
        glow=(620, 1050, 480, '#ffd0a0', 0.6, 0.7),
        far=dict(type='ridge', color='#5a5a7a', y=1040, amp=150, f1=0.0075),
        mid=dict(type='ridge', color='#2e2e48', y=1140, amp=90, f1=0.0095),
        ground=dict(type='ridge', color='#141420', y=1220, amp=18),
        fg=dict(color='#0a0a12', y=1300)),
    'station_dusk': dict(
        sky=[(-200, '#1c1a36'), (500, '#4a2f55'), (900, '#c75d4a'), (1100, '#f0a060')],
        glow=(540, 1040, 520, '#ffb070', 0.6, 0.7),
        far=dict(type='city', color='#2a1a36', win=None, y=1130, hmin=100, hmax=300),
        mid=dict(type='none'),
        ground=dict(type='flat', color='#1a1224', y=1200),
        fg=dict(color='#0c0812', y=1300)),
    'map_dark': dict(
        map=dict(land=[(-120, 250), (1200, 250), (1200, 1250), (640, 1250), (560, 1150), (470, 1120), (430, 1000),
                       (360, 960), (300, 990), (220, 950), (170, 860), (210, 760), (120, 720), (-120, 760)],
                 river=[(980, 560), (880, 600), (760, 620), (650, 700), (560, 780), (520, 880), (560, 1000), (640, 1120)],
                 coast_from=3)),
    'plain_dark': dict(
        sky=[(-200, '#07080c'), (1920, '#0d1018')], glow=(540, 820, 600, '#1d2a3a', 0.7, 1.0),
        far=dict(type='none'), mid=dict(type='none'), ground=dict(type='none')),
    'plain_warm': dict(
        sky=[(-200, '#0b0906'), (1920, '#171109')], glow=(540, 820, 620, '#3b2a14', 0.65, 1.0),
        far=dict(type='none'), mid=dict(type='none'), ground=dict(type='none')),
}


def _merge(a, b):
    out = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def resolve(spec):
    if isinstance(spec, str):
        return copy.deepcopy(PRESETS[spec])
    if 'preset' in spec:
        return _merge(PRESETS[spec['preset']], {k: v for k, v in spec.items() if k != 'preset'})
    return copy.deepcopy(spec)


def _acacia(c, x, y, h, col):
    c.line([(x, y), (x + h * 0.04, y - h * 0.55), (x - h * 0.02, y - h * 0.8)], h * 0.035, col)
    c.ellipse(x, y - h * 0.86, h * 0.9, h * 0.2, col)
    c.ellipse(x + h * 0.25, y - h * 0.78, h * 0.5, h * 0.14, col)


def _far(c, f, gy, seed):
    t = f.get('type', 'none')
    col = f.get('color', '#101018')
    y = f.get('y', gy - 100)
    rnd = random.Random(seed)
    if t == 'city':
        A.city(c, y, col, f.get('win'), seed, f.get('hmin', 160), f.get('hmax', 520))
    elif t == 'ridge':
        ridge(c, y, f.get('amp', 70), col, seed=seed, f1=f.get('f1', 0.005))
    elif t == 'spruce':
        ridge(c, y + 6, 8, col, seed=seed)
        for x in range(-100, 1220, f.get('step', 46)):
            A.spruce(c, x + rnd.uniform(-14, 14), y + 4, rnd.uniform(f.get('h0', 130), f.get('h1', 220)), col)


def _mid(c, m, gy, seed):
    t = m.get('type', 'none')
    col = m.get('color', '#080810')
    y = m.get('y', gy)
    rnd = random.Random(seed)
    if t == 'bare_trees':
        for i, x in enumerate(m.get('xs', (60, 220, 900, 1040))):
            A.bare_tree(c, x, y, m.get('h', 460) * rnd.uniform(0.8, 1.2), col, seed=i + 1)
    elif t == 'spruce':
        for x in range(-60, 1200, m.get('step', 70)):
            A.spruce(c, x + rnd.uniform(-12, 12), y, rnd.uniform(m.get('h0', 140), m.get('h1', 230)), col)
    elif t == 'houses':
        xs = m.get('xs', (-40, 200, 420, 700, 900))
        ws = (190, 150, 210, 160, 200)
        hs = (150, 120, 170, 125, 160)
        for i, x in enumerate(xs):
            A.house(c, x, y - rnd.randint(0, 6), ws[i % 5], hs[i % 5], col, snow=m.get('snow', '#9eacc6'),
                    steeple=(i == 2))
    elif t == 'acacia':
        for x in m.get('xs', (120, 760, 980)):
            _acacia(c, x, y, rnd.uniform(220, 340), col)
    elif t == 'rocks':
        for x in m.get('xs', (100, 400, 800)):
            A.rock(c, x, y, rnd.uniform(160, 280), rnd.uniform(80, 160), col)


def _ground(c, g, seed):
    t = g.get('type', 'none')
    col = g.get('color', '#101018')
    y = g.get('y', 1230)
    if t == 'ridge':
        ridge(c, y, g.get('amp', 12), col, seed=seed, f1=0.003, f2=0.009)
    elif t in ('flat', 'water', 'ice'):
        c.rect(-120, y, 1200, 2200, col)
        if t == 'water':
            rnd = random.Random(seed)
            for _ in range(60):
                yy = rnd.uniform(y + 4, y + 90)
                xx = rnd.uniform(-100, 1180)
                c.rect(xx, yy, xx + rnd.uniform(20, 120), yy + 2, g.get('color2', '#8a8c82'))
        if t == 'ice':
            A.floes(c, y, 1600, g.get('color2', '#2b4157'), '#11202f', seed)


def _map(spec):
    m = spec['map']
    arr = gradient([(-200, '#06101c'), (1920, '#0a1626')])
    yy, xx = np.mgrid[0:LH, 0:LW]
    grid = ((xx % 60) < 2) | ((yy % 60) < 2)
    arr[grid, 0] += 10
    arr[grid, 1] += 18
    arr[grid, 2] += 26
    layers = [(to_img(arr), 0.0)]
    c = Canvas()
    land = [tuple(p) for p in m['land']]
    c.poly(land, m.get('land_color', '#163049'))
    k = m.get('coast_from', 0)
    c.line(land[k:] + [land[-1]], 3, '#2f5a80', caps=False)
    if m.get('river'):
        c.line([tuple(p) for p in m['river']], 4, '#25496b')
    layers.append((c.done(), 0.0))
    return layers


def build(spec, seed=1):
    spec = resolve(spec)
    if spec.get('map'):
        return _map(spec), spec
    layers = []
    sky = gradient([tuple(s) for s in spec['sky']])
    if spec.get('stars'):
        rng = np.random.default_rng(seed)
        for _ in range(spec['stars']):
            sx = int(rng.integers(0, LW))
            sy = int(rng.integers(0, OY + 850))
            sz = 2 if rng.random() < 0.85 else 3
            sky[sy:sy + sz, sx:sx + sz, :3] = rng.uniform(110, 230)
    if spec.get('glow'):
        g = list(spec['glow']) + [1.0] * (6 - len(spec['glow']))
        sky = add_glow(sky, g[0], g[1], g[2], g[3], g[4], g[5])
    if spec.get('moon'):
        mx, my, mr = spec['moon']
        yy, xx = np.mgrid[0:LH, 0:LW].astype(np.float32)
        d1 = np.sqrt((xx - mx - OX) ** 2 + (yy - my - OY) ** 2)
        d2 = np.sqrt((xx - mx - OX - mr * 0.45) ** 2 + (yy - my - OY + mr * 0.28) ** 2)
        a = np.clip(mr - d1, 0, 1) * np.clip(d2 - (mr - 4), 0, 1)
        for i, v in enumerate((243, 236, 210)):
            sky[..., i] = sky[..., i] * (1 - a) + v * a
    layers.append((to_img(grain_tex(sky, 4, seed)), 0.0))
    if spec.get('sun'):
        sx, sy, sr, sc = spec['sun']
        c = Canvas()
        c.circle(sx, sy, sr, sc)
        layers.append((c.done(), 0.08))
    gy = spec.get('ground', {}).get('y', 1230)
    if spec.get('far', {}).get('type', 'none') != 'none':
        c = Canvas()
        _far(c, spec['far'], gy, seed + 3)
        layers.append((c.done(1.2), 0.15))
    if spec.get('mid', {}).get('type', 'none') != 'none':
        c = Canvas()
        _mid(c, spec['mid'], gy, seed + 5)
        layers.append((c.done(0.8), 0.38))
    if spec.get('ground', {}).get('type', 'none') != 'none':
        c = Canvas()
        _ground(c, spec['ground'], seed + 7)
        layers.append((c.done(), 0.55))
    return layers, spec


def foreground(spec, seed=1):
    """Dark strip drawn above actors (factor 0.85); returns layer or None."""
    f = spec.get('fg')
    if not f:
        return None
    c = Canvas()
    ridge(c, f.get('y', 1290), f.get('amp', 8), f['color'], seed=seed + 11)
    return (c.done(), 0.85)
