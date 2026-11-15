"""Particle effects drawn on top of the composed frame: snow, blizzard, embers, motes, rain, dust."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .base import FW, FH


KINDS = ('snow', 'blizzard', 'embers', 'motes', 'rain', 'dust')


class Particles:
    def __init__(self, kind, seed=1):
        r = np.random.default_rng(seed)
        self.kind = kind
        if kind == 'snow':
            self.n, self.wind, self.speed, self.size, self.alpha, self.blur = 170, 40, (40, 110), (1.5, 4.5), (120, 230), 0.8
        elif kind == 'blizzard':
            self.n, self.wind, self.speed, self.size, self.alpha, self.blur = 300, 400, (200, 400), (1.2, 3.4), (110, 220), 0.5
        elif kind == 'embers':
            self.n, self.wind, self.speed, self.size, self.alpha, self.blur = 46, 0, (40, 120), (1.5, 4.0), (150, 250), 1.2
        elif kind == 'motes':
            self.n, self.wind, self.speed, self.size, self.alpha, self.blur = 34, 0, (6, 18), (1.5, 3.2), (90, 150), 1.2
        elif kind == 'rain':
            self.n, self.wind, self.speed, self.size, self.alpha, self.blur = 260, 120, (900, 1400), (1.0, 2.0), (80, 160), 0.4
        elif kind == 'dust':
            self.n, self.wind, self.speed, self.size, self.alpha, self.blur = 90, 240, (20, 60), (1.5, 4), (60, 130), 1.6
        else:
            raise ValueError(f'unknown fx: {kind}')
        self.p = [(r.uniform(-200, FW + 200), r.uniform(0, FH), r.uniform(*self.speed), r.uniform(*self.size),
                   r.uniform(0, 6.28), r.uniform(*self.alpha)) for _ in range(self.n)]

    def draw(self, img, t):
        ov = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        k = self.kind
        for x0, y0, sp, r, ph, a in self.p:
            if k in ('snow', 'blizzard', 'rain'):
                y = (y0 + sp * t) % (FH + 40) - 20
                x = (x0 + self.wind * t * (0.9 if k != 'snow' else 0.3) + 20 * math.sin(t * 0.8 + ph)) % (FW + 400) - 200
                if k == 'snow':
                    d.ellipse([x - r, y - r, x + r, y + r], fill=(240, 246, 255, int(a)))
                elif k == 'blizzard':
                    d.line([(x, y), (x - self.wind * 0.06 * r, y - sp * 0.02 * r)], fill=(235, 242, 255, int(a)),
                           width=max(1, int(r * 0.8)))
                else:
                    d.line([(x, y), (x - 8, y - 38 * r)], fill=(190, 210, 235, int(a)), width=max(1, int(r)))
            elif k == 'embers':
                y = (y0 - sp * t) % 1400
                x = x0 + 18 * math.sin(t * 1.3 + ph)
                al = int(max(0, a * (0.6 + 0.4 * math.sin(t * 7 + ph * 3))))
                d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 160, 70, al))
            elif k == 'motes':
                y = y0 - sp * t
                y = 300 + (y - 300) % 1000
                x = x0 + 22 * math.sin(t * 0.6 + ph)
                al = int(max(0, a * (0.7 + 0.3 * math.sin(t * 2 + ph))))
                d.ellipse([x - r * 3, y - r * 3, x + r * 3, y + r * 3], fill=(255, 230, 170, al))
            elif k == 'dust':
                y = (y0 + 10 * math.sin(t + ph)) % FH
                x = (x0 + self.wind * t) % (FW + 400) - 200
                d.ellipse([x - r * 2, y - r, x + r * 2, y + r], fill=(235, 200, 150, int(a)))
        if self.blur:
            ov = ov.filter(ImageFilter.GaussianBlur(self.blur))
        img.paste(ov, (0, 0), ov)


def make_fx(names, seed=1):
    return [Particles(n, seed + i * 7) for i, n in enumerate(names or [])]
