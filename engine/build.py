"""Build a video from a storyboard.

  python -m engine.build stories/<slug>/story.json --out out/<slug>.mp4 [--workers 2] [--stills 3.0,8.5] [--no-images]

"visual": "image" olan hikâyelerde sahne görselleri seslendirmeden sonra engine/images.py ile hazırlanır
(work/<slug>/images/ önbelleği; --stills ve tam render aynı dosyaları kullanır).
"""
import argparse, json, os, shutil, subprocess, sys, time
from multiprocessing import Pool

FPS = 30


def _render_scene(args):
    spec, info, seed, path = args
    from .scene import Scene, finish
    sc = Scene(spec, info, seed)
    n = int(round(info['dur'] * FPS))
    tmp = path + '.tmp.mp4'
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1080x1920',
                           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '22',
                           '-pix_fmt', 'yuv420p', '-r', str(FPS), tmp], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(finish(sc.frame(i / FPS), i).tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError(f'ffmpeg failed for {spec["id"]}')
    os.replace(tmp, path)
    return spec['id']


def scene_infos(story, tl):
    out = []
    for sc, ts in zip(story['scenes'], tl['scenes']):
        out.append({'dur': ts['end'] - ts['start'],
                    'lines': [{'start': l['start'] - ts['start'], 'dur': l['dur'], 'cap': l['cap'], 'style': l['style']}
                              for l in ts['lines']]})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('story')
    ap.add_argument('--out', default='out/video.mp4')
    ap.add_argument('--work', default=None)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--stills', default=None, help='comma-separated times; renders PNGs of every scene and exits')
    ap.add_argument('--voice', default=None)
    ap.add_argument('--no-compress', action='store_true')
    ap.add_argument('--no-images', action='store_true', help='yapay zekâ görsellerini kapat, yedek çizimi kullan')
    a = ap.parse_args(argv)
    if a.no_images:
        os.environ['BD_IMAGES'] = '0'

    story = json.load(open(a.story, encoding='utf-8'))
    slug = os.path.splitext(os.path.basename(os.path.dirname(os.path.abspath(a.story))))[0]
    work = a.work or os.path.join('work', slug)
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    t0 = time.time()

    from .voice import build_timeline
    print('voice...', flush=True)
    tl = build_timeline(story, work, a.voice)
    infos = scene_infos(story, tl)
    print(f'  total {tl["total"]:.1f}s', flush=True)

    from .images import ensure_images
    ensure_images(story, work)   # "visual": "image" değilse hiçbir şey yapmaz; hata vermez

    if a.stills:
        from .scene import Scene, finish
        os.makedirs(os.path.join(work, 'stills'), exist_ok=True)
        times = [float(x) for x in a.stills.split(',')]
        for i, (sp, inf) in enumerate(zip(story['scenes'], infos)):
            sc = Scene(sp, inf, i + 1)
            for t in times:
                if t < inf['dur']:
                    sc.frame(t).save(os.path.join(work, 'stills', f'{i:02d}_{sp["id"]}_{t}.png'))
        print('stills in', os.path.join(work, 'stills'))
        return

    sdir = os.path.join(work, 'scenes')
    shutil.rmtree(sdir, ignore_errors=True)
    os.makedirs(sdir)
    jobs = [(sp, inf, i + 1, os.path.join(sdir, f'{i:02d}.mp4')) for i, (sp, inf) in enumerate(zip(story['scenes'], infos))]
    print(f'rendering {len(jobs)} scenes...', flush=True)
    with Pool(a.workers) as pool:
        for sid in pool.imap_unordered(_render_scene, jobs):
            print('  done', sid, flush=True)

    from .music import compose
    print('music...', flush=True)
    mix = compose(story, tl, os.path.join(work, 'mix.wav'), os.path.join(work, 'vo_track.wav'))

    lst = os.path.join(work, 'list.txt')
    with open(lst, 'w') as f:
        for j in jobs:
            f.write(f"file '{os.path.abspath(j[3])}'\n")
    vid = os.path.join(work, 'video_only.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', vid], check=True)
    crf = '22' if a.no_compress else '26'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-i', mix, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                    '-b:a', '192k', '-shortest', '-movflags', '+faststart', a.out], check=True)
    print(f'done -> {a.out}  ({time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
