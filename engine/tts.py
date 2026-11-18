"""Turkish TTS: Piper (offline) and Edge neural voices (online), with pronunciation fixes.

Piper (TrVoice): ü/ö/ı vowel fixes, foreign names, real pauses.
Edge (EdgeVoice): Microsoft Edge neural voices via the unofficial `edge-tts` package (network). Same text
pipeline (normalize + respelling); "..." becomes a real BD_TTS_PAUSE silence like Piper. Every request is
cached as mp3 under <work>/vo_cache/edge/ keyed by (voice, rate, final text), so re-renders stay offline.
Network errors raise EdgeTTSError after retries; engine/voice.py then falls back to Piper for the whole video.

Voices live in $TR_VOICE_DIR (default ~/tts) as vits-piper-tr_TR-<voice>-medium/. Use scripts/fetch_voice.sh.
Extra respellings come from pronunciations.json (word -> how to spell it so Turkish reads it right)
and from a story's own "pron" dict (story wins). Keys match whole words only, so a Turkish suffix after an
apostrophe is kept ("Shackleton'ın" -> "Şekılton'ın") and a key never fires inside another word.

Optional tuning via env vars (unset = current behaviour, nothing changes):
  BD_TTS_LENGTH   length_scale (speed; default 0.95 from voice.py, >1 = slower)
  BD_TTS_NOISE    noise_scale  (default: model's 0.667; higher = more pitch/energy variation)
  BD_TTS_NOISEW   noise_w_scale (default: model's 0.8; higher = more varied phoneme durations/rhythm)
  BD_TTS_SENT_GAP silence between sentences in seconds (default 0.22)
  BD_TTS_PAUSE    silence for "..." in seconds (default 0.5; Piper and Edge)
  BD_EDGE_RATE    Edge speaking rate (default "+0%")
  BD_EDGE_TIMEOUT Edge per-request timeout in seconds (default 30)
"""
import asyncio, hashlib, json, os, re, subprocess, time
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOWEL_PH = set('aɑeɛæɯiɪoɔœøuʊyʏ')
VOWEL_L = set('aeıioöuü')


def load_pron(extra=None):
    p = {}
    f = os.path.join(ROOT, 'pronunciations.json')
    if os.path.exists(f):
        p.update(json.load(open(f, encoding='utf-8')))
    p.update(extra or {})
    return p


def _env_float(name, default):
    v = os.environ.get(name, '').strip()
    if not v:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def pron_regex(pron):
    """One-pass, whole-word matcher; longest key first so "Oskar Pfungst" wins over "Pfungst".
    A key matches only when not glued to other letters/digits; an apostrophe suffix may follow."""
    keys = sorted((k for k in pron if k), key=len, reverse=True)
    if not keys:
        return None
    return re.compile(r'(?<![\w])(' + '|'.join(re.escape(k) for k in keys) + r')(?![\w])')


def apply_pron(text, pron, rx=None):
    rx = rx if rx is not None else pron_regex(pron)
    if rx is None:
        return text
    return rx.sub(lambda m: pron[m.group(1)], text)


def normalize_text(text):
    """Small, safe cleanups before synthesis (no wording changes)."""
    text = text.replace('\u2026', '...')               # unicode ellipsis -> real pause
    text = text.replace('\u2019', "'").replace('\u2018', "'")
    text = re.sub(r'\.{4,}', '...', text)
    return re.sub(r'\s+', ' ', text).strip()


# circumflex letters are plain vowels for alignment (hâlâ, rüzgâr, resmî)
_PLAIN = str.maketrans({'â': 'a', 'î': 'i', 'û': 'u', 'Â': 'a', 'Î': 'i', 'Û': 'u'})


def tr_lower(s):
    return s.replace('I', 'ı').replace('İ', 'i').lower()


def _align(word, ph):
    """Pair each vowel phoneme index in ph with the Turkish vowel letter it stands for, or None.
    espeak merges vowel+ğ+vowel into one long vowel (düşündüğü -> ...døː...), so when plain counting
    fails, a long vowel ("Vː") may stand for two letters."""
    letters = [c for c in tr_lower(word).translate(_PLAIN) if c in VOWEL_L]
    idx = [i for i, c in enumerate(ph) if c in VOWEL_PH]
    if len(letters) == len(idx):
        return list(zip(letters, idx))
    long_ = [i for i in idx if i + 1 < len(ph) and ph[i + 1] == 'ː']
    if long_ and 'ğ' in tr_lower(word) and len(idx) + len(long_) == len(letters):
        out, li = [], 0
        for i in idx:
            out.append((letters[li], i))
            li += 2 if i in long_ else 1
        return out
    return None


def fix_word(word, ph):
    pairs = _align(word, ph)
    if pairs is None:
        return ph, False
    ph = list(ph)
    changed = False
    for l, i in pairs:
        p = ph[i]
        new = p
        if l == 'ü' and p in 'øœuʊ':
            new = 'y'
        elif l == 'ö' and p in 'yʏ':
            new = 'œ'
        elif l == 'ı' and p in 'iɪ':
            new = 'ɯ'
        elif l == 'u' and p in 'yø':
            new = 'ʊ'
        elif l == 'o' and p in 'øœ':
            new = 'o'
        if new != p:
            ph[i] = new
            changed = True
    return ''.join(ph), changed


class TrVoice:
    def __init__(self, voice='fahrettin', length_scale=0.95, pron=None):
        base = os.environ.get('TR_VOICE_DIR', os.path.expanduser('~/tts'))
        d = os.path.join(base, f'vits-piper-tr_TR-{voice}-medium')
        from piper import PiperVoice, SynthesisConfig   # lazy: Edge-only paths/tools need no Piper import
        self.v = PiperVoice.load(os.path.join(d, f'tr_TR-{voice}-medium.onnx'))
        self.sr = self.v.config.sample_rate
        self.cfg = SynthesisConfig(length_scale=_env_float('BD_TTS_LENGTH', length_scale),
                                   noise_scale=_env_float('BD_TTS_NOISE', None),
                                   noise_w_scale=_env_float('BD_TTS_NOISEW', None))
        self.pause = _env_float('BD_TTS_PAUSE', 0.5)
        self.sent_gap = _env_float('BD_TTS_SENT_GAP', 0.22)
        self.pron = load_pron(pron)
        self.pron_rx = pron_regex(self.pron)

    def sentence_phonemes(self, sent):
        ph_sents = self.v.phonemize(sent)
        ph = ' '.join(''.join(s) for s in ph_sents)
        words = re.findall(r"[\wçğıöşüÇĞİÖŞÜâî'’]+", sent)
        toks = ph.split(' ')
        if len([t for t in toks if any(c in VOWEL_PH for c in t)]) != len(words):
            return ph
        out, wi = [], 0
        for t in toks:
            if any(c in VOWEL_PH for c in t):
                m = re.match(r'^([^\wɐ-ʯ]*)(.*?)([,.;:!?]*)$', t)
                pre, body, post = m.groups()
                fixed, _ = fix_word(words[wi].replace("'", ''), body)
                out.append(pre + fixed + post)
                wi += 1
            else:
                out.append(t)
        return ' '.join(out)

    def prepare(self, text):
        return apply_pron(normalize_text(text), self.pron, self.pron_rx)

    def synth(self, text, pause=None, sent_gap=None):
        pause = self.pause if pause is None else pause
        sent_gap = self.sent_gap if sent_gap is None else sent_gap
        text = self.prepare(text)
        parts = [p.strip() for p in text.split('...') if p.strip()]
        audio = []
        for pi, part in enumerate(parts):
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', part) if s.strip()]
            for si, s in enumerate(sents):
                ids = self.v.phonemes_to_ids(list(self.sentence_phonemes(s)))
                a = np.asarray(self.v.phoneme_ids_to_audio(ids, self.cfg), dtype=np.float32).flatten()
                audio.append(a)
                if si < len(sents) - 1:
                    audio.append(np.zeros(int(sent_gap * self.sr), np.float32))
            if pi < len(parts) - 1:
                audio.append(np.zeros(int(pause * self.sr), np.float32))
        return np.concatenate(audio)


# ------------------------------------------------------------------ Edge neural voices (network)
EDGE_VOICES = {'ahmet': 'tr-TR-AhmetNeural', 'emel': 'tr-TR-EmelNeural'}
EDGE_SR = 24000


class EdgeTTSError(RuntimeError):
    pass


def _decode_mp3(data, sr=EDGE_SR):
    """mp3 bytes -> mono float32 at sr (ffmpeg)."""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-f', 'f32le', '-ac', '1', '-ar', str(sr), 'pipe:1'],
                       input=data, capture_output=True)
    if r.returncode != 0:
        raise EdgeTTSError('mp3 cozulemedi: ' + r.stderr.decode(errors='replace').strip()[-200:])
    a = np.frombuffer(r.stdout, dtype=np.float32).copy()
    if a.size < sr // 20 or not np.isfinite(a).all() or np.abs(a).max() < 1e-4:
        raise EdgeTTSError('bos/sessiz ses geldi')
    return a


def _trim(a, sr, pre=0.03, post=0.08):
    thr = 0.02 * np.abs(a).max()
    idx = np.where(np.abs(a) > thr)[0]
    if idx.size == 0:
        return a
    return a[max(0, idx[0] - int(pre * sr)): idx[-1] + int(post * sr)]


class EdgeVoice:
    """Edge neural voice with the same interface as TrVoice (sr, prepare, synth)."""
    attempts, backoff = 3, (1.0, 3.0)

    def __init__(self, voice='emel', pron=None, cache_dir=None, rate=None):
        import edge_tts   # raises ImportError if the package is missing -> caller falls back to Piper
        self._edge = edge_tts
        self.name = voice
        self.voice = EDGE_VOICES[voice]
        self.rate = rate or os.environ.get('BD_EDGE_RATE', '').strip() or '+0%'
        self.timeout = _env_float('BD_EDGE_TIMEOUT', 30.0)
        self.sr = EDGE_SR
        self.pause = _env_float('BD_TTS_PAUSE', 0.5)
        self.pron = load_pron(pron)
        self.pron_rx = pron_regex(self.pron)
        self.cache_dir = cache_dir
        self.requests = self.cache_hits = 0
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

    def prepare(self, text):
        return apply_pron(normalize_text(text), self.pron, self.pron_rx)

    async def _fetch_async(self, text):
        com = self._edge.Communicate(text, self.voice, rate=self.rate)
        buf = bytearray()
        async for ch in com.stream():
            if ch.get('type') == 'audio' and ch.get('data'):
                buf += ch['data']
        return bytes(buf)

    def _fetch(self, text):
        last = None
        for i in range(self.attempts):
            try:
                self.requests += 1
                data = asyncio.run(asyncio.wait_for(self._fetch_async(text), self.timeout))
                if not data:
                    raise EdgeTTSError('ses verisi gelmedi')
                _decode_mp3(data, self.sr)          # validate before caching
                return data
            except Exception as ex:                 # network, 403, timeout, NoAudioReceived, bad mp3 ...
                last = ex
                if i < self.attempts - 1:
                    time.sleep(self.backoff[min(i, len(self.backoff) - 1)])
        raise EdgeTTSError(f'{type(last).__name__}: {str(last)[:200]}')

    def _clip(self, text):
        key = hashlib.sha1(f'{self.voice}|{self.rate}|{text}'.encode('utf-8')).hexdigest()[:20]
        path = os.path.join(self.cache_dir, key + '.mp3') if self.cache_dir else None
        if path and os.path.exists(path) and os.path.getsize(path) > 0:
            try:
                a = _decode_mp3(open(path, 'rb').read(), self.sr)
                self.cache_hits += 1
                return a
            except EdgeTTSError:
                pass
        data = self._fetch(text)
        if path:
            tmp = path + '.tmp'
            open(tmp, 'wb').write(data)
            os.replace(tmp, path)
        return _decode_mp3(data, self.sr)

    def synth(self, text, pause=None, sent_gap=None):
        """One line -> float32 audio. "..." splits the request; each part is trimmed and joined with a
        fixed pause (Piper semantics). Non-final parts keep "..." so Edge keeps the suspended intonation."""
        pause = self.pause if pause is None else pause
        text = self.prepare(text)
        parts = [p.strip() for p in text.split('...') if p.strip(' ,;')]
        if not parts:
            raise EdgeTTSError('bos metin')
        audio = []
        for pi, part in enumerate(parts):
            last = pi == len(parts) - 1
            a = _trim(self._clip(part if last else part + '...'), self.sr)
            audio.append(a)
            if not last:
                audio.append(np.zeros(int(pause * self.sr), np.float32))
        return np.concatenate(audio).astype(np.float32)
