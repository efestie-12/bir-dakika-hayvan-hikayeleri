"""Story storyboard -> voice-over audio + timeline.json (scene/line start times)."""
import json, os
import numpy as np
import soundfile as sf
from .tts import TrVoice

GAP, SCENE_GAP, LEAD_IN, TAIL = 0.18, 0.45, 0.35, 2.6


def build_timeline(story, workdir, voice=None, length_scale=0.95):
    os.makedirs(os.path.join(workdir, 'vo'), exist_ok=True)
    tv = TrVoice(voice or story.get('voice', 'fahrettin'), length_scale, story.get('pron'))
    sr = tv.sr
    t = LEAD_IN
    scenes = []
    for si, sc in enumerate(story['scenes']):
        start = 0.0 if si == 0 else t - 0.25
        entry = {'id': sc['id'], 'start': start, 'lines': []}
        for li, ln in enumerate(sc['lines']):
            a = tv.synth(ln['tts'])
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
    tl = {'total': total, 'sr': sr, 'scenes': scenes}
    json.dump(tl, open(os.path.join(workdir, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    return tl
