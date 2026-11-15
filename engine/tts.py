"""Turkish Piper TTS with pronunciation fixes (ü/ö/ı vowels, foreign names, real pauses).

Voices live in $TR_VOICE_DIR (default ~/tts) as vits-piper-tr_TR-<voice>-medium/. Use scripts/fetch_voice.sh.
Extra respellings come from pronunciations.json (word -> how to spell it so Turkish reads it right)
and from a story's own "pron" dict.
"""
import json, os, re
import numpy as np
from piper import PiperVoice, SynthesisConfig

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


def tr_lower(s):
    return s.replace('I', 'ı').replace('İ', 'i').lower()


def fix_word(word, ph):
    letters = [c for c in tr_lower(word) if c in VOWEL_L]
    idx = [i for i, c in enumerate(ph) if c in VOWEL_PH]
    if len(letters) != len(idx):
        return ph, False
    ph = list(ph)
    changed = False
    for l, i in zip(letters, idx):
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
        self.v = PiperVoice.load(os.path.join(d, f'tr_TR-{voice}-medium.onnx'))
        self.sr = self.v.config.sample_rate
        self.cfg = SynthesisConfig(length_scale=length_scale)
        self.pron = load_pron(pron)

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

    def synth(self, text, pause=0.5, sent_gap=0.22):
        for a, b in self.pron.items():
            text = text.replace(a, b)
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
