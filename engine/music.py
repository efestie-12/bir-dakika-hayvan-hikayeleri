"""Mood-driven score + SFX + VO mix.

Story keys: key ("Dm", "Am", "Em", "Gm", "Cm"), per scene: mood, wind (0-1), sfx [{type, at}].
Moods: calm | wonder | build | tension | drive | warm | resolve | data
SFX types: impact | riser | crack | whoosh | swish | tom
"""
import numpy as np
import soundfile as sf
from math import gcd
from scipy.signal import butter, lfilter, fftconvolve, resample_poly
from .overlays import Ctx

SR = 44100
MOODS = ('calm', 'wonder', 'build', 'tension', 'drive', 'warm', 'resolve', 'data')
SFX_TYPES = ('impact', 'riser', 'crack', 'whoosh', 'swish', 'tom')
ROOTS = {'Am': 45, 'Bm': 47, 'Cm': 48, 'Dm': 50, 'Em': 52, 'Fm': 53, 'Gm': 43}


def mf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


class Mix:
    def __init__(self, dur, seed=3):
        self.N = int(SR * dur) + SR
        self.L, self.R = np.zeros(self.N), np.zeros(self.N)
        self.SL, self.SR_ = np.zeros(self.N), np.zeros(self.N)
        self.rng = np.random.default_rng(seed)

    def add(self, sig, t0, gain=1.0, pan=0.0, sfx=False):
        i = int(t0 * SR)
        if i >= self.N or i < 0:
            return
        sig = sig[:self.N - i]
        gl, gr = gain * np.sqrt((1 - pan) / 2), gain * np.sqrt((1 + pan) / 2)
        if sfx:
            self.SL[i:i + len(sig)] += sig * gl
            self.SR_[i:i + len(sig)] += sig * gr
        else:
            self.L[i:i + len(sig)] += sig * gl
            self.R[i:i + len(sig)] += sig * gr

    # ---- instruments
    def pad(self, t0, dur, notes, gain=0.045, bright=6, att=0.8, rel=1.2):
        n = int((dur + rel) * SR)
        t = np.arange(n) / SR
        e = np.ones(n)
        na = max(1, int(att * SR))
        e[:na] = np.linspace(0, 1, na) ** 1.5
        sus = int(dur * SR)
        if sus < n:
            e[sus:] = np.linspace(1, 0, n - sus) ** 2
        for m in notes:
            for side, det in ((-0.6, -5), (0.6, 5)):
                s = np.zeros(n)
                for k in range(1, bright + 1):
                    s += np.sin(2 * np.pi * mf(m) * k * 2 ** (det / 1200) * t + self.rng.uniform(0, 6.28)) / k ** 1.4
                self.add(s * e, t0, gain, side)
        root = min(notes)
        b = np.sin(2 * np.pi * mf(root - 12) * t) + 0.25 * np.sin(2 * np.pi * mf(root) * t)
        self.add(b * e, t0, gain * 1.5)

    def pluck(self, m, t0, gain, pan=0.0):
        n = int(0.3 * SR)
        t = np.arange(n) / SR
        s = sum(np.sin(2 * np.pi * mf(m) * k * t) / k for k in range(1, 8))
        self.add(s * np.exp(-t / 0.08) * np.minimum(1, t / 0.003), t0, gain, pan)

    def piano(self, t0, m, gain=0.12, pan=0.0):
        n = int(3.0 * SR)
        t = np.arange(n) / SR
        s = sum((0.55 ** (k - 1)) * np.sin(2 * np.pi * mf(m) * k * 1.0008 ** k * t) * np.exp(-t / (1.5 / k ** 0.6))
                for k in range(1, 7))
        self.add(s * np.minimum(1, t / 0.004), t0, gain, pan)

    def lp(self, n, cut):
        b, a = butter(2, cut / (SR / 2), 'low')
        return lfilter(b, a, self.rng.normal(0, 1, n))

    def tom(self, t0, gain=0.2):
        n = int(0.7 * SR)
        t = np.arange(n) / SR
        f = 65 + 55 * np.exp(-t / 0.05)
        self.add(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22), t0, gain)

    def kick(self, t0, gain=0.2):
        n = int(0.5 * SR)
        t = np.arange(n) / SR
        f = 45 + 90 * np.exp(-t / 0.03)
        self.add(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18), t0, gain)

    def impact(self, t0, gain=1.0):
        n = int(2.4 * SR)
        t = np.arange(n) / SR
        f = 38 + 70 * np.exp(-t / 0.07)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.8)
        self.add(body + 1.6 * self.lp(n, 1800) * np.exp(-t / 0.15), t0, 0.5 * gain, sfx=True)

    def riser(self, t_end, length=1.4, gain=0.1):
        n = int(length * SR)
        x = np.linspace(0, 1, n)
        out = np.zeros(n)
        noise = self.rng.normal(0, 1, n)
        zi, blk = None, 2048
        for i in range(0, n, blk):
            b, a = butter(2, (300 + 7000 * x[i] ** 2) / (SR / 2), 'low')
            if zi is None:
                zi = np.zeros(max(len(a), len(b)) - 1)
            y, zi = lfilter(b, a, noise[i:i + blk], zi=zi)
            out[i:i + blk] = y
        out *= x ** 2.2
        self.add(out, t_end - length, gain, -0.2, sfx=True)
        self.add(out, t_end - length + 0.01, gain, 0.2, sfx=True)

    def whoosh(self, tc, gain=0.09, length=0.7):
        n = int(length * SR)
        x = np.linspace(0, 1, n)
        out = np.zeros(n)
        noise = self.rng.normal(0, 1, n)
        zi, blk = np.zeros(2), 1024
        for i in range(0, n, blk):
            b, a = butter(2, (400 + 4000 * np.sin(np.pi * x[i])) / (SR / 2), 'low')
            y, zi = lfilter(b, a, noise[i:i + blk], zi=zi)
            out[i:i + blk] = y
        out *= np.sin(np.pi * x) ** 2
        self.add(out, tc - length * 0.6, gain, -0.4, sfx=True)
        self.add(out[::-1], tc - length * 0.6, gain * 0.7, 0.4, sfx=True)

    def wind(self, t0, t1, gain=0.12, bright=1100):
        n = int((t1 - t0) * SR)
        if n <= 0:
            return
        noise = self.rng.normal(0, 1, n)
        out = np.zeros(n)
        tt = np.arange(n) / SR
        mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * tt) * np.sin(2 * np.pi * 0.07 * tt + 1)
        zi, blk = np.zeros(4), 2048
        for i in range(0, n, blk):
            c = 250 + bright * mod[i]
            b, a = butter(2, [c * 0.6 / (SR / 2), c * 1.6 / (SR / 2)], 'band')
            y, zi = lfilter(b, a, noise[i:i + blk], zi=zi)
            out[i:i + blk] = y
        e = np.minimum(1, np.minimum(tt / 0.6, (tt[-1] - tt) / 0.6))
        out *= (0.6 + 0.6 * mod) * e
        self.add(out, t0, gain, -0.3, sfx=True)
        self.add(np.roll(out, 9000), t0, gain * 0.8, 0.3, sfx=True)

    def crack(self, t0, gain=0.5):
        n = int(2.0 * SR)
        out = np.zeros(n)
        t = np.arange(n) / SR
        tc = 0.0
        for k in range(26):
            tc += self.rng.exponential(0.035) if k else 0
            i, m = int(tc * SR), int(0.15 * SR)
            tt = np.arange(m) / SR
            click = np.sin(2 * np.pi * self.rng.uniform(900, 3500) * tt) * np.exp(-tt / self.rng.uniform(0.004, 0.02))
            click *= self.rng.uniform(0.3, 1)
            out[i:i + m] += click[:max(0, min(m, n - i))]
        out += 1.2 * np.sin(2 * np.pi * np.cumsum(55 + 40 * np.exp(-t / 0.1)) / SR) * np.exp(-t / 0.5)
        out += 0.8 * self.lp(n, 600) * np.exp(-t / 0.4)
        self.add(out, t0, gain, sfx=True)

    def swish(self, t0, gain=0.14):
        n = int(0.45 * SR)
        x = np.linspace(0, 1, n)
        b, a = butter(2, [1500 / (SR / 2), 7000 / (SR / 2)], 'band')
        s = lfilter(b, a, self.rng.normal(0, 1, n)) * np.sin(np.pi * x) ** 1.5
        self.add(s, t0, gain, self.rng.uniform(-0.5, 0.5), sfx=True)


def chords(key):
    r = ROOTS.get(key, 50)
    return [[r, r + 3, r + 7, r + 12], [r - 4, r, r + 3, r + 8], [r + 3, r + 7, r + 10, r + 15],
            [r - 2, r + 2, r + 5, r + 10]]


def compose(story, tl, out_path, vo_path):
    key = story.get('key', 'Dm')
    root = ROOTS.get(key, 50)
    prog = chords(key)
    m = Mix(tl['total'])
    for si, (sc, tsc) in enumerate(zip(story['scenes'], tl['scenes'])):
        s0, s1 = tsc['start'], tsc['end']
        dur = s1 - s0
        mood = sc.get('mood', 'calm')
        ch = prog[si % 4]
        ch2 = prog[(si + 1) % 4]
        half = max(1.0, dur / 2)
        ctx = Ctx(dur, [l['start'] - s0 for l in tsc['lines']], [l['dur'] for l in tsc['lines']])
        bright = {'tension': 4, 'calm': 5, 'data': 3, 'warm': 7, 'resolve': 7, 'wonder': 7}.get(mood, 6)
        gain = {'calm': 0.04, 'data': 0.035, 'tension': 0.045, 'resolve': 0.05, 'warm': 0.05}.get(mood, 0.05)
        m.pad(s0, half, ch, gain, bright, att=0.6)
        m.pad(s0 + half, dur - half, ch2, gain, bright, att=0.4)
        if mood in ('wonder', 'warm', 'calm', 'resolve'):
            seq = [ch[2] + 12, ch[1] + 12, ch[2] + 7, ch[0] + 12] if mood != 'resolve' else [ch[3] + 12, ch[2] + 12, ch[1] + 12, ch[0] + 12]
            step = 0.8 if mood != 'calm' else 1.1
            for k, n in enumerate(seq * 4):
                tt = s0 + 0.3 + k * step
                if tt < s1 - 0.5:
                    m.piano(tt, n, 0.1 if mood != 'calm' else 0.07, 0.2 if k % 2 else -0.2)
        if mood in ('build', 'drive', 'tension', 'data'):
            t, k = s0, 0
            beat = 0.75 if mood == 'tension' else 1.0 if mood == 'data' else 0.25
            while t < s1 - 0.05:
                ramp = min(1.0, 0.4 + (t - s0) / 5)
                r = (ch if t < s0 + half else ch2)[0]
                if mood == 'tension':
                    m.tom(t, 0.15)
                    m.pluck(r + 12, t, 0.03, -0.2)
                    t += beat
                elif mood == 'data':
                    m.kick(t, 0.12)
                    t += beat
                else:
                    m.pluck(r + 12, t, 0.05 * ramp, -0.2)
                    m.pluck(r + (19 if k % 2 else 24), t + 0.125, 0.03 * ramp, 0.25)
                    if k % 4 == 0 or mood == 'drive' and k % 2 == 0:
                        m.kick(t, 0.18)
                    if mood == 'drive':
                        m.tom(t, 0.2 if k % 2 == 0 else 0.1)
                    t += 0.25
                k += 1
            if mood == 'build':
                m.riser(s1, 1.2, 0.08)
        if sc.get('wind'):
            m.wind(s0 - 0.2, s1 + 0.2, 0.18 * float(sc['wind']), 1000 + 600 * float(sc['wind']))
        if si > 0:
            m.whoosh(s0, 0.09)
        for e in sc.get('sfx', []):
            at = s0 + ctx.at(e.get('at'), 0.0)
            ty = e['type']
            if ty == 'impact':
                m.impact(at, e.get('gain', 1.0))
            elif ty == 'riser':
                m.riser(at, e.get('length', 1.4), 0.1)
            elif ty == 'crack':
                m.crack(at, 0.55)
            elif ty == 'whoosh':
                m.whoosh(at, 0.1)
            elif ty == 'swish':
                m.swish(at)
            elif ty == 'tom':
                m.tom(at, 0.25)
    # outro notes on the last scene are covered by 'resolve' mood
    # ---- reverb on music
    ir_n = int(2.2 * SR)
    ti = np.arange(ir_n) / SR
    irs = []
    for _ in range(2):
        ir = m.rng.normal(0, 1, ir_n) * np.exp(-ti / 0.5)
        irs.append(ir / np.sqrt((ir ** 2).sum()))
    N = m.N
    ML = m.L * 0.8 + fftconvolve(m.L, irs[0])[:N] * 0.45
    MR = m.R * 0.8 + fftconvolve(m.R, irs[1])[:N] * 0.45
    # ---- VO + ducking
    vo, vsr = sf.read(vo_path)
    if vo.ndim > 1:
        vo = vo.mean(1)
    if vsr != SR:
        g = gcd(SR, vsr)
        vo = resample_poly(vo, SR // g, vsr // g)
    v = np.zeros(N)
    v[:min(N, len(vo))] = vo[:N]
    b, a = butter(2, 90 / (SR / 2), 'high')
    v = lfilter(b, a, v)
    envv = np.sqrt(lfilter([1 - 0.999], [1, -0.999], v ** 2))
    envv /= envv.max() + 1e-9
    duck = lfilter([1 - 0.9995], [1, -0.9995], 1 - 0.55 * np.clip(envv * 4, 0, 1))
    mus = np.stack([ML, MR], 1)
    mus = mus / (np.abs(mus).max() + 1e-9) * 0.5
    sfx = np.stack([m.SL, m.SR_], 1)
    sfx = sfx / (np.abs(sfx).max() + 1e-9) * 0.55
    vv = v / (np.abs(v).max() + 1e-9) * 0.9
    mix = mus * duck[:, None] + sfx * (0.55 + 0.45 * duck[:, None]) + np.stack([vv, vv], 1)
    end_i = int(tl['total'] * SR)
    fade = np.ones(N)
    fo = int(1.2 * SR)
    fade[end_i - fo:end_i] = np.linspace(1, 0, fo)
    fade[end_i:] = 0
    mix = (mix * fade[:, None])[:end_i]
    mix = np.tanh(mix / np.abs(mix).max() * 1.15) / np.tanh(1.15) * 0.9
    sf.write(out_path, mix.astype(np.float32), SR)
    return out_path
