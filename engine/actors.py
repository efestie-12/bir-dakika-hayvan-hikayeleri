"""Actors: animated silhouettes with optional rim light, rendered as pre-drawn phase frames.

Actor spec (dict):
  type   : husky | cat | horse | bird | elephant | bear | person | soldier | team | musher | rock | lamp
           | ship | train | truck | tent  (bu dördünde x = orta nokta, y = taban/su çizgisi; d etkisiz)
  x, y   : foot position in frame coords
  h      : height in px
  d      : 1 faces right, -1 faces left
  color  : body hex      rim : rim-light hex (optional)
  motion : idle | gallop | walk | fly     speed : px/s the actor travels (+ = right)
  at     : seconds from scene start when it appears
  plus type-specific keys: pose, hat, arm, coat, n (team), gap, sled_w, cap, lift, head_down, rifle,
                           w (rock/ship/train/truck/tent), lights (ship/train), cars (train), lit (tent)
"""
from .base import Canvas, bear, soldier, truck, tent
from . import lib as A

N_FRAMES = 6
ANIM_FPS = {'gallop': 14, 'walk': 8, 'fly': 10}
TYPES = ('husky', 'cat', 'horse', 'bird', 'elephant', 'bear', 'person', 'soldier', 'team', 'musher', 'rock', 'lamp',
         'ship', 'train', 'truck', 'tent')


def _draw(c, a, x, y, col, ph):
    t, h, d = a['type'], a.get('h', 300), a.get('d', 1)
    if t == 'husky':
        A.husky(c, x, y, h, col, d=d, phase=ph)
    elif t == 'cat':
        A.cat(c, x, y, h, col, d=d, pose='walk' if ph is not None else a.get('pose', 'sit'), phase=ph)
    elif t == 'horse':
        A.horse(c, x, y, h, col, d=d, phase=ph, head_down=a.get('head_down', False))
    elif t == 'bird':
        A.bird(c, x, y, h, col, d=d, wing=ph)
    elif t == 'elephant':
        A.elephant(c, x, y, h, col, d=d, phase=ph)
    elif t == 'bear':
        bear(c, x, y, h, col, pose=a.get('pose', 'stand'), d=d, cap=a.get('cap', False), lift=a.get('lift', 0.0))
    elif t == 'person':
        A.person(c, x, y, h, col, d=d, hat=a.get('hat', 'none'), arm=a.get('arm', 'down'),
                 coat=a.get('coat', True))
    elif t == 'soldier':
        soldier(c, x, y, h, col, d=d, pose=a.get('pose', 'down'), hat=a.get('hat', 'helmet'),
                rifle=a.get('rifle', False))
    elif t == 'team':
        A.team(c, x, y, h, col, n=a.get('n', 5), phase=ph or 0.0, d=d, gap=a.get('gap', 96),
               sled_w=a.get('sled_w', 170))
    elif t == 'musher':
        A.musher(c, x, y, h, col, d=d, lean=a.get('lean', 0.0))
    elif t == 'rock':
        A.rock(c, x, y, a.get('w', h * 1.5), h, col)
    elif t == 'lamp':
        A.lamp_post(c, x, y, h, col)
    elif t == 'ship':
        w = a.get('w', h * 1.8)
        A.ship(c, x - w / 2, y, w, col, lights=a.get('lights', '#e8c890'))
    elif t == 'train':
        cars = a.get('cars', 2)
        w = a.get('w', h * 2.27)
        A.train(c, x - w * (0.44 + 0.46 * cars) / 2, y, w, col, cars=cars, lights=a.get('lights', '#ffd27a'))
    elif t == 'truck':
        w = a.get('w', h * 1.9)
        truck(c, x - w / 2, y, w, col)
    elif t == 'tent':
        w = a.get('w', h * 1.6)
        tent(c, x - w / 2, x + w / 2, y, y - h, col, lit=a.get('lit'))
    else:
        raise ValueError(f'unknown actor type: {t}')


def make_actor(a):
    """Return (fn(t) -> (RGBA layer, dx) | None, parallax factor)."""
    col = a.get('color', '#05070c')
    rim = a.get('rim')
    motion = a.get('motion', 'idle')
    n = N_FRAMES if motion in ANIM_FPS else 1
    frames = []
    for k in range(n):
        ph = None if n == 1 else k / n
        c = Canvas()
        if rim:
            r = Canvas()
            _draw(r, a, a['x'] + 2, a['y'] - 3, rim, ph)
            img = r.done(0.8)
            _draw(c, a, a['x'], a['y'], col, ph)
            img.alpha_composite(c.done())
        else:
            _draw(c, a, a['x'], a['y'], col, ph)
            img = c.done()
        frames.append(img)
    speed, fps, at = a.get('speed', 0.0), ANIM_FPS.get(motion, 0), a.get('at', 0.0)

    def fn(t):
        if t < at:
            return None
        im = frames[int(t * fps) % n] if n > 1 else frames[0]
        return im, speed * (t - at)
    return fn, a.get('factor', 0.6)
