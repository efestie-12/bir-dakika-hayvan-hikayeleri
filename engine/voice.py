"""Story storyboard -> voice-over audio + timeline.json (scene/line start times).

Voice choice (first that is set): env BD_VOICE_OVERRIDE > --voice > story "voice" > "karma".
  ahmet / emel -> Edge neural voice (tr-TR-AhmetNeural / tr-TR-EmelNeural), network
  karma        -> one Edge voice per VIDEO, alternating by creation order (see pick_karma)
  fahrettin / dfki / fettah -> Piper (offline), unchanged
BD_TTS_ENGINE=piper forces Piper (Edge names map to fahrettin). If any Edge line fails after retries, the WHOLE
video is re-voiced with Piper fahrettin; one video never mixes voices and TTS network errors never crash the build.
"""
import json, os, zlib
import numpy as np
import soundfile as sf
from .tts import TrVoice, EdgeVoice, EDGE_VOICES

GAP, SCENE_GAP, LEAD_IN, TAIL = 0.18, 0.45, 0.35, 2.6
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPER_VOICES = ('fahrettin', 'dfki', 'fettah')
FALLBACK_PIPER = 'fahrettin'
KARMA_ORDER = ('ahmet', 'emel')


def pick_karma(slug, history_path=None):
    """even index -> ahmet, odd -> emel. Index = position of slug in history.json entries; a story not yet
    recorded gets the index it will take when appended (len(entries)), so --stills (before history add) and the
    final render (after) choose the same voice. No/unreadable history.json -> zlib.crc32(slug) % 2."""
    path = history_path or os.path.join(ROOT, 'history.json')
    try:
        entries = json.load(open(path, encoding='utf-8')).get('entries', [])
        slugs = [e.get('slug') for e in entries]
        idx = slugs.index(slug) if slug in slugs else len(slugs)
    except (OSError, ValueError, AttributeError):
        idx = zlib.crc32((slug or '').encode('utf-8'))
    return KARMA_ORDER[idx % 2]


def resolve_voice(story, voice=None, slug=None, history_path=None):
    """-> (requested, concrete): concrete is an Edge key (ahmet/emel) or a Piper voice name."""
    req = (os.environ.get('BD_VOICE_OVERRIDE', '').strip() or voice or story.get('voice') or 'karma').lower()
    if req == 'karma':
        return req, pick_karma(slug or story.get('slug', ''), history_path)
    return req, req


def _synth_all(tv, story):
    return [[tv.synth(ln['tts']) for ln in sc['lines']] for sc in story['scenes']]


def synth_story(story, workdir, voice=None, length_scale=0.95):
    """-> (audio[scene][line], sr, info). Never raises for Edge/network problems."""
    slug = story.get('slug') or os.path.basename(os.path.abspath(workdir))
    req, conc = resolve_voice(story, voice, slug)
    force_piper = os.environ.get('BD_TTS_ENGINE', '').strip().lower() == 'piper'
    reason = None
    if conc in EDGE_VOICES and not force_piper:
        try:
            tv = EdgeVoice(conc, story.get('pron'), cache_dir=os.path.join(workdir, 'vo_cache', 'edge'))
            audio = _synth_all(tv, story)
            print(f'ses: edge-tts {tv.voice} (istenen {req} -> {conc}, hiz {tv.rate}; '
                  f'{tv.requests} istek, {tv.cache_hits} onbellek)', flush=True)
            return audio, tv.sr, {'engine': 'edge', 'requested': req, 'voice': conc, 'edge_voice': tv.voice,
                                  'rate': tv.rate}
        except Exception as ex:   # ImportError, EdgeTTSError, anything network-related
            reason = f'{type(ex).__name__}: {str(ex)[:200]}'
            print(f"ses: edge-tts basarisiz -> Piper {FALLBACK_PIPER}'e dusuldu (neden: {reason})", flush=True)
    elif conc in EDGE_VOICES:
        reason = 'BD_TTS_ENGINE=piper'
    if conc not in PIPER_VOICES:
        conc = FALLBACK_PIPER
    tv = TrVoice(conc, length_scale, story.get('pron'))
    audio = _synth_all(tv, story)
    print(f'ses: piper {conc} (istenen {req}' + (f'; {reason}' if reason else '') + ')', flush=True)
    info = {'engine': 'piper', 'requested': req, 'voice': conc}
    if reason:
        info['fallback_reason'] = reason
    return audio, tv.sr, info


def build_timeline(story, workdir, voice=None, length_scale=0.95):
    os.makedirs(os.path.join(workdir, 'vo'), exist_ok=True)
    audio, sr, vinfo = synth_story(story, workdir, voice, length_scale)
    t = LEAD_IN
    scenes = []
    for si, sc in enumerate(story['scenes']):
        start = 0.0 if si == 0 else t - 0.25
        entry = {'id': sc['id'], 'start': start, 'lines': []}
        for li, ln in enumerate(sc['lines']):
            a = audio[si][li]
            thr = 0.02 * np.abs(a).max()
            idx = np.where(np.abs(a) > thr)[0]
            a = a[max(0, idx[0] - int(0.03 * sr)): idx[-1] + int(0.08 * sr)]
            fn = os.path.join(workdir, 'vo', f'{si:02d}_{li}.wav')
            sf.write(fn, a, sr)
            dur = len(a) / sr
            entry['lines'].append({'file': fn, 'start': round(t, 3), 'dur': round(dur, 3), 'cap': ln.get('cap', ln['tts']),
                                   'style': ln.get('style', 'cap')})
            t += dur + GAP
        t += SCENE_GAP
        scenes.append(entry)
    for i, s in enumerate(scenes):
        s['end'] = scenes[i + 1]['start'] if i + 1 < len(scenes) else round(t + TAIL, 3)
        s['start'], s['end'] = round(s['start'], 3), round(s['end'], 3)
    total = scenes[-1]['end']
    vo = np.zeros(int(total * sr) + sr)
    for s in scenes:
        for ln in s['lines']:
            a, _ = sf.read(ln['file'])
            i = int(ln['start'] * sr)
            vo[i:i + len(a)] += a
    vo = vo / (np.abs(vo).max() + 1e-9) * 0.95
    sf.write(os.path.join(workdir, 'vo_track.wav'), vo, sr)
    tl = {'total': total, 'sr': sr, 'voice': vinfo, 'scenes': scenes}
    json.dump(tl, open(os.path.join(workdir, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    return tl
