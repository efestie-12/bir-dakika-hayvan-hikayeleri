"""Scene runner: storyboard scene spec + timeline info -> frames.

Scene spec keys:
  id, backdrop (preset name | dict), actors [..], fx ['snow', ...], aurora (strength 0-1),
  camera {zoom:[a,b], pan:[a,b], pany:[a,b]}, punch [{at, amount}], shake [{at, dur, amp}], flash [{at, dur}],
  overlays [..], lines [{tts, cap, style}]
  image {prompt, seed, focus, actors} + _image_path (engine/images.py) -> backdrop yerine yapay zekâ görseli
  scene3d {...} + _3d_dir (engine/scene3d.py) -> backdrop/actors yerine 3D kare dizisi
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from .base import FW, FH
from . import backdrops as B, actors as AC, fx as FX, overlays as OV, lib as A

WW, WH = FW + 108, FH + 192
CAP_Y = 1470
GOLD = (255, 205, 70)
F_CAP = OV.F('Inter-ExtraBold.otf', 64)
F_BIG = OV.F('InterDisplay-Black.otf', 92)
ease, eo = OV.ease, OV.eo


def layout(text, font, maxw=940, lh=78):
    words = text.split(' ')
    sp = font.getlength(' ')
    lines, cur, w = [], [], 0
    for wd in words:
        ww = font.getlength(wd.replace('*', ''))
        if cur and w + sp + ww > maxw:
            lines.append(cur)
            cur, w = [], 0
        cur.append((wd, ww))
        w += (sp if len(cur) > 1 else 0) + ww
    lines.append(cur)
    out = []
    y = CAP_Y - lh * len(lines) / 2
    for ln in lines:
        tw = sum(ww for _, ww in ln) + sp * (len(ln) - 1)
        x = FW / 2 - tw / 2
        for wd, ww in ln:
            out.append([wd.replace('*', ''), wd.startswith('*'), x, y, ww])
            x += ww + sp
        y += lh
    return out


class Scene:
    def __init__(self, spec, info, seed=1):
        """info: {'dur': float, 'lines': [{'start','dur','cap','style'} relative to scene start]}"""
        self.spec, self.info = spec, info
        self.dur = info['dur']
        ls = [l['start'] for l in info['lines']]
        ld = [l['dur'] for l in info['lines']]
        self.ctx = OV.Ctx(self.dur, ls, ld)
        img_path = spec.get('_image_path')   # engine/images.py doldurur (yalnız "visual": "image")
        d3 = spec.get('_3d_dir')              # engine/scene3d.py doldurur (yalnız "scene3d" sahneleri)
        if d3:
            from . import scene3d as S3
            self.layers = [('d', S3.frame_layer(d3, spec.get('_3d_n'), (WW, WH)), 0.0)]
            bspec = None                          # backdrop/actors yalnız yedek; 3D kare tüm katmanı kaplar
            actor_specs = []
        elif img_path:
            from . import images as IM
            im_spec = spec.get('image') or {}
            self.layers = [('s', IM.layer(img_path, im_spec), 0.9)]
            bspec = None                          # ön plan şeridi (fg) ve aurora yok
            actor_specs = spec.get('actors', []) if im_spec.get('actors') else []
        else:
            layers, bspec = B.build(spec.get('backdrop', 'plain_dark'), seed)
            self.layers = [('s', im, f) for im, f in layers]
            if spec.get('aurora'):
                st = float(spec['aurora'])
                y0, y1 = (0.12, 0.5) if st >= 0.8 else (0.08, 0.4)
                self.layers.insert(1, ('d', lambda t, st=st, y0=y0, y1=y1: A.aurora(t, strength=st, y0=y0, y1=y1).resize((WW, WH)), 0.0))
            actor_specs = spec.get('actors', [])
        self.ctx.scene = self
        for a in actor_specs:
            a = dict(a)
            a['at'] = self.ctx.at(a.get('at'), 0.0)
            fn, f = AC.make_actor(a)
            self.layers.append(('d', fn, f))
        fg = B.foreground(bspec, seed) if bspec is not None else None
        if fg:
            self.layers.append(('s', fg[0], fg[1]))
        self.fx = FX.make_fx(spec.get('fx', []), seed)
        self.over = OV.compile_overlays(spec.get('overlays', []), self.ctx)
        cam = spec.get('camera', {})
        self.zoom = cam.get('zoom', [1.0, 1.06])
        self.pan = cam.get('pan', [0, 0])
        self.pany = cam.get('pany', [0, 0])
        self.punch = [(self.ctx.at(p['at']), p.get('amount', 0.08)) for p in spec.get('punch', [])]
        self.shake = [(self.ctx.at(s['at']), s.get('dur', 0.6), s.get('amp', 16)) for s in spec.get('shake', [])]
        self.flash = [(self.ctx.at(s['at']), s.get('dur', 0.12)) for s in spec.get('flash', [])]

    # -------------------------------------------------------------- camera
    def cam_at(self, t):
        k = ease(t / self.dur)
        z = self.zoom[0] + (self.zoom[1] - self.zoom[0]) * k
        for at, amt in self.punch:
            if t > at:
                z += amt * eo((t - at) / 0.25)
        return z, self.pan[0] + (self.pan[1] - self.pan[0]) * k, self.pany[0] + (self.pany[1] - self.pany[0]) * k

    def shake_at(self, t):
        sx = sy = 0.0
        for t0, du, amp in self.shake:
            if t0 <= t < t0 + du:
                e = (1 - (t - t0) / du) ** 1.5
                sx += amp * e * math.sin(t * 91)
                sy += amp * e * math.cos(t * 77)
        return sx, sy

    def to_frame(self, x, y, f, t, dx=0.0):
        """Map layer-space point (frame coords at factor f, with actor dx) to the final frame."""
        from .base import OX, OY
        z, px, py = self.cam_at(t)
        x0, y0 = 54 + px * f - dx, 96 + py * f
        cw, ch = FW / z, FH / z
        cx0, cy0 = (WW - cw) / 2, (WH - ch) / 2
        return (x + OX - x0 - cx0) * z, (y + OY - y0 - cy0) * z

    def compose(self, t):
        z, px, py = self.cam_at(t)
        sx, sy = self.shake_at(t)
        base = None
        for kind, obj, f in self.layers:
            if kind == 's':
                im, dx = obj, 0
            else:
                r = obj(t)
                if r is None:
                    continue
                im, dx = r if isinstance(r, tuple) else (r, 0)
            if im.size == (WW, WH):
                crop = im
            else:
                x0 = int(round(54 + px * f + sx * f - dx))
                y0 = max(0, min(192, int(round(96 + py * f + sy * f))))
                if dx == 0:
                    x0 = max(0, min(108, x0))
                crop = im.crop((x0, y0, x0 + WW, y0 + WH))
            if base is None:
                base = crop.convert('RGB')
            else:
                base.paste(crop, (0, 0), crop)
        cw, ch = FW / z, FH / z
        cx0, cy0 = (WW - cw) / 2 + sx * 0.3, (WH - ch) / 2 + sy * 0.3
        return base.resize((FW, FH), Image.BILINEAR, box=(cx0, cy0, cx0 + cw, cy0 + ch))

    # -------------------------------------------------------------- captions
    def captions(self, img, t):
        lines = self.info['lines']
        ov = Image.new('RGBA', (FW, 640), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        oy = CAP_Y - 320
        drew = False
        for i, ln in enumerate(lines):
            t0 = ln['start']
            t1 = lines[i + 1]['start'] if i + 1 < len(lines) else self.dur
            if not (t0 - 0.05 <= t < t1):
                continue
            fade = min(1.0, (t1 - t) / 0.15)
            big = ln.get('style') == 'big'
            font = F_BIG if big else F_CAP
            words = layout(ln['cap'], font, lh=104 if big else 78)
            chars = [len(w[0]) + 1 for w in words]
            tot, acc = sum(chars), 0
            for wi, (wd, star, x, y, ww) in enumerate(words):
                ta = t0 + ln['dur'] * 0.92 * acc / tot
                acc += chars[wi]
                if t < ta:
                    break
                p = eo((t - ta) / 0.14)
                a = int(255 * p * fade)
                tb = t0 + ln['dur'] * 0.92 * acc / tot
                active = ta <= t < tb + 0.08
                col = GOLD if (star or big) else ((255, 244, 214) if active else (255, 255, 255))
                d.text((x + ww / 2, y - oy + (1 - p) * 18 + 40), wd, font=font, fill=col + (a,), anchor='mm',
                       stroke_width=8, stroke_fill=(0, 0, 0, a))
                drew = True
        if drew:
            img.paste(ov, (0, oy), ov)

    def frame(self, t):
        img = self.compose(t)
        for p in self.fx:
            p.draw(img, t)
        for o in self.over:
            o(img, t)
        self.captions(img, t)
        for at, du in self.flash:
            if at <= t < at + du:
                img.paste(Image.blend(img, Image.new('RGB', (FW, FH), (255, 255, 255)), 0.4 * (1 - (t - at) / du)))
        return img


# ------------------------------------------------------------------ finishing
_yy, _xx = np.mgrid[0:FH, 0:FW].astype(np.float32)
_r = np.sqrt(((_xx - FW / 2) / (FW * 0.62)) ** 2 + ((_yy - FH * 0.45) / (FH * 0.62)) ** 2)
VIG = (np.clip(1.0 - 0.5 * np.clip(_r - 0.55, 0, 1) ** 1.6, 0, 1) * 256).astype(np.uint16)[..., None]
GRAIN = [np.random.default_rng(i).normal(0, 5, (FH, FW, 1)).astype(np.int16) for i in range(4)]


def finish(img, i):
    a = (np.asarray(img, dtype=np.uint16) * VIG) >> 8
    a = a.astype(np.int16) + GRAIN[i % 4]
    return np.clip(a, 0, 255).astype(np.uint8)
