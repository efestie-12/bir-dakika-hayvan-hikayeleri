"""3D sahne katmanı (isteğe bağlı) — Three.js + başsız Chromium ile kare dizisi.

story.json'da bir sahnede "scene3d": {...} varsa build.py seslendirmeden ve ensure_images'tan sonra ensure_3d()
çağırır. Her 3D sahne work/<slug>/3d/<hash>/%04d.jpg (kalite 92) olarak bir kez çizilir; hash = çözülmüş sahne +
süre + kare sayısı + çizici sürümü + engine/web3d dosyaları (önbellek). Başarılı sahnede spec['_3d_dir'] dolar ve
engine/scene.py katmanı bu karelerden alır (zoom/punch/shake/fx/overlay/altyazı aynen çalışır). Herhangi bir hata,
eksik Chrome/playwright ya da süre bütçesi aşımında uyarı yazılır ve sahne kendi "backdrop"/"actors" alanlarıyla
çizilir: bu modül build'i hiçbir durumda durdurmaz. "scene3d" alanı olmayan hikâyelerde hiçbir şey yapmaz/yazmaz.

Şema (sahne içinde; zamanlar "line:1", "end:-1" ya da saniye — Python'da sayıya çevrilir, JS'ye yalnız sayı gider):
  "scene3d": {
    "stage":   {"preset": "workshop" | "dungeon", "light": "#ffb36b", "fog": "#2a211b", "exposure": 1.1},
    "camera":  {"pos": [x,y,z], "look": [x,y,z], "fov": 50, "drift": 0.015,
                "to": {"pos": [..], "look": [..], "fov": 47, "at": <zaman>, "dur": 3.0}},       # dolly
    "figures": [{"id": "usta", "x": -2.3, "z": 0.1, "yaw": 90, "outfit": "worker|prisoner|guard|none",
                 "do": [{"at": 0, "anim": "walk", "to": [x, z], "dur": 1.5},
                        {"at": "line:0:0.5", "anim": "turn", "to": 15},          # derece
                        {"at": 1.6, "anim": "wave", "dur": 1.6},
                        {"at": 3.4, "anim": "grab", "to": "<prop id>", "dur": 0.8},
                        {"at": 4.4, "anim": "lift", "dur": 0.8}]}],
    "props":   [{"id": "cekic", "kind": "hammer", "attach": "bench", "pos": [x, 0, z], "rot": [90, 0, -75]},
                {"id": "kutu", "shape": "box", "size": [0.3, 0.2, 0.3], "color": "#8a6a44", "pos": [x, y, z],
                 "track": [{"at": "line:1", "pos": [x, y, z], "rot": [0, 45, 0], "dur": 0.8}]}]
  }
  Koordinatlar metre; y yukarı, +z kameraya doğru, yaw 0 = kameraya bakar. Tezgâh (bench) iki presette de
  x 0.0-1.9, z -0.85..-0.05 civarındadır; "attach": "bench" prop'un y'sini tezgâh üstüne oturtur.
  Prop türleri/animasyonlar/kıyafetler: engine/web3d/props.json.

Ortam: BD_3D=0 kapatır · BD_CHROME=<yol> tarayıcı · BD_3D_BUDGET_S (varsayılan 1500) toplam süre bütçesi ·
BD_3D_SCALE (varsayılan 1.0) çözünürlük çarpanı (kareler katman boyutuna ölçeklenir).
"""
import base64, hashlib, json, os, shutil, time

RENDERER_VERSION = 1
FPS = 30
QUALITY = 92
ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, 'web3d')
HOST = 'http://bd3d.local/'
_CT = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json'}


def load_catalog():
    with open(os.path.join(WEB, 'props.json'), encoding='utf-8') as f:
        return json.load(f)


def has_3d(story):
    return any(isinstance(sc.get('scene3d'), dict) for sc in story.get('scenes', []))


def layer_size():
    from .scene import WW, WH          # katman boyutu (1188x2112); 3D kare bu boyuta oturur
    return WW, WH


# ------------------------------------------------------------------ zaman çözümü + hash
def resolve(spec, info, catalog=None, size=None):
    """Sahne spec'i + zaman bilgisi -> JS'ye gidecek, yalnız sayılardan oluşan yapılandırma."""
    from .overlays import Ctx
    s3 = spec['scene3d']
    dur = float(info['dur'])
    ctx = Ctx(dur, [l['start'] for l in info['lines']], [l['dur'] for l in info['lines']])

    def at(v, d=0.0):
        return round(float(ctx.at(v, d)), 4)

    def dur_of(a, d):
        if a.get('until') is not None:
            return round(max(0.05, at(a['until']) - at(a.get('at'))), 4)
        return round(float(a['dur']), 4) if a.get('dur') is not None else d

    cam = dict(s3.get('camera') or {})
    if isinstance(cam.get('to'), dict):
        to = dict(cam['to'])
        to['at'] = at(to.get('at'), 0.0)
        to['dur'] = dur_of(to, max(0.5, dur - to['at']))
        to.pop('until', None)
        cam['to'] = to
    figures = []
    for f in s3.get('figures') or []:
        f = dict(f)
        acts = []
        for a in f.get('do') or []:
            a = dict(a)
            a['at'] = at(a.get('at'), 0.0)
            d = dur_of(a, None)
            a.pop('until', None)
            if d is not None:
                a['dur'] = d
            else:
                a.pop('dur', None)
            acts.append(a)
        f['do'] = acts
        figures.append(f)
    props = []
    for p in s3.get('props') or []:
        p = dict(p)
        if p.get('track'):
            tr = []
            for k in p['track']:
                k = dict(k)
                k['at'] = at(k.get('at'), 0.0)
                k['dur'] = dur_of(k, 0.8)
                k.pop('until', None)
                tr.append(k)
            p['track'] = tr
        props.append(p)
    catalog = catalog or load_catalog()
    w, h = size or layer_size()
    return {'w': int(w), 'h': int(h), 'dur': round(dur, 4), 'stage': dict(s3.get('stage') or {}), 'camera': cam,
            'figures': figures, 'props': props, 'kinds': catalog.get('kinds', {})}


def _web_digest():
    h = hashlib.sha256()
    for name in ('index.html', 'stage.js', 'lib.js', 'props.json'):
        with open(os.path.join(WEB, name), 'rb') as f:
            h.update(name.encode() + b'\0' + f.read())
    return h.hexdigest()


def scene_hash(cfg, n):
    blob = json.dumps({'cfg': cfg, 'n': n, 'fps': FPS, 'q': QUALITY, 'v': RENDERER_VERSION, 'web': _web_digest()},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]


# ------------------------------------------------------------------ tarayıcı
def _chrome_path():
    p = os.environ.get('BD_CHROME', '').strip()
    if p:
        return p if os.path.isfile(p) else None
    for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'):
        q = shutil.which(name)
        if q:
            return q
    return ''          # '' = playwright'ın kendi Chromium'unu dene


class _Browser:
    """Tek Chromium; sahne başına yeni sayfa. Dosyalar yerel diskten route ile sunulur (port açılmaz)."""

    def __init__(self):
        from playwright.sync_api import sync_playwright      # tembel import: yalnız 3D sahne varsa
        exe = _chrome_path()
        if exe is None:
            raise RuntimeError('BD_CHROME bulunamadı')
        self._pw = sync_playwright().start()
        args = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--mute-audio',
                '--disable-background-networking', '--disable-component-update', '--disable-sync',
                '--disable-default-apps', '--no-first-run']   # ağ yok: sayfa yerelden route ile sunulur
        try:
            kw = {'args': args}
            if exe:
                kw['executable_path'] = exe
            self.b = self._pw.chromium.launch(**kw)
        except Exception:
            self._pw.stop()
            raise
        self.exe = exe or 'playwright-chromium'

    def page(self, cfg):
        pg = self.b.new_page(viewport={'width': 400, 'height': 400})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)[:300]))

        def serve(route):
            rel = route.request.url[len(HOST):].split('?', 1)[0] or 'index.html'
            path = os.path.normpath(os.path.join(WEB, rel))
            if not path.startswith(WEB + os.sep) or not os.path.isfile(path):
                return route.fulfill(status=404, body='')
            with open(path, 'rb') as f:
                route.fulfill(status=200, body=f.read(), headers={'Content-Type': _CT.get(os.path.splitext(path)[1], 'application/octet-stream')})

        pg.route(HOST + '**', serve)
        pg.goto(HOST + 'index.html')
        pg.wait_for_function('window.ready0 === true', timeout=120000)
        pg.evaluate('cfg => window.setup(cfg)', cfg)
        if errs:
            raise RuntimeError('sayfa hatası: ' + errs[0])
        pg.evaluate('window.renderAt(0)')         # ısınma: shader derleme
        return pg, errs

    def close(self):
        try:
            self.b.close()
        finally:
            self._pw.stop()


class _NoBrowser(Exception):
    """Tarayıcı açılamadı: kalan 3D sahneler de denenmez."""


def _msg(ex):
    return f'{type(ex).__name__}: ' + (str(ex).strip().splitlines() or [''])[0][:200]


def _grab(pg, t):
    u = pg.evaluate("t => (window.renderAt(t), document.getElementById('c').toDataURL('image/jpeg', %.2f))" % (QUALITY / 100), t)
    return base64.b64decode(u.split(',', 1)[1])


# ------------------------------------------------------------------ ana giriş
def _clear(story):
    for sc in story.get('scenes', []):
        sc.pop('_3d_dir', None)
        sc.pop('_3d_n', None)


def ensure_3d(story, workdir, infos, times=None):
    """3D sahnelerin karelerini üretir/önbellekten bulur; başarılı sahnede spec['_3d_dir'] doldurur.
    times verilirse (--stills) yalnız o anların kareleri çizilir. Hiçbir durumda istisna fırlatmaz."""
    _clear(story)
    if not has_3d(story):
        return None
    if os.environ.get('BD_3D', '1').strip() == '0':
        print('3d: kapalı (BD_3D=0) -> yedek backdrop/actors', flush=True)
        return None
    br = None
    t0 = time.time()
    budget = float(os.environ.get('BD_3D_BUDGET_S', '1500') or 1500)
    scale = float(os.environ.get('BD_3D_SCALE', '1.0') or 1.0)
    report = []
    try:
        catalog = load_catalog()
        lw, lh = layer_size()
        size = (int(round(lw * scale / 2)) * 2, int(round(lh * scale / 2)) * 2)
        for i, (sc, inf) in enumerate(zip(story['scenes'], infos)):
            if not isinstance(sc.get('scene3d'), dict):
                continue
            ts = time.time()
            try:
                cfg = resolve(sc, inf, catalog, size)
                n = max(1, int(round(inf['dur'] * FPS)))
                d = os.path.join(workdir, '3d', scene_hash(cfg, n))
                os.makedirs(d, exist_ok=True)
                want = sorted({min(n - 1, int(round(t * FPS))) for t in times if t < inf['dur']}) if times else list(range(n))
                todo = [k for k in want if not os.path.isfile(os.path.join(d, f'{k:04d}.jpg'))]
                if todo:
                    if br is None:
                        try:
                            br = _Browser()
                        except Exception as ex:
                            raise _NoBrowser(_msg(ex)) from ex
                        print(f'3d: tarayıcı {br.exe} ({time.time() - t0:.1f} sn)', flush=True)
                    pg, errs = br.page(cfg)
                    try:
                        tr = time.time()
                        for j, k in enumerate(todo):
                            if time.time() - t0 > budget:
                                raise TimeoutError(f'süre bütçesi ({budget:.0f} sn) doldu')
                            data = _grab(pg, k / FPS)
                            tmp = os.path.join(d, f'{k:04d}.jpg.tmp')
                            with open(tmp, 'wb') as f:
                                f.write(data)
                            os.replace(tmp, os.path.join(d, f'{k:04d}.jpg'))
                            if j % 30 == 0 or j == len(todo) - 1:
                                el = time.time() - tr
                                print(f'  3d: sahne[{i}] kare {j + 1}/{len(todo)} ({el / (j + 1):.2f} sn/kare)', flush=True)
                        if errs:
                            raise RuntimeError('sayfa hatası: ' + errs[0])
                    finally:
                        pg.close()
                missing = [k for k in want if not os.path.isfile(os.path.join(d, f'{k:04d}.jpg'))]
                if missing:
                    raise RuntimeError(f'{len(missing)} kare eksik')
                sc['_3d_dir'] = os.path.abspath(d)
                sc['_3d_n'] = n
                dt = time.time() - ts
                print(f'3d: sahne[{i}] {sc.get("id")}: {len(want)} kare ({len(todo)} yeni, {len(want) - len(todo)} önbellek) '
                      f'{dt:.1f} sn' + (f' = {dt / len(todo):.2f} sn/kare' if todo else ''), flush=True)
                report.append({'scene': i, 'id': sc.get('id'), 'frames': len(want), 'new': len(todo), 'sec': round(dt, 1)})
            except _NoBrowser:
                raise
            except Exception as ex:
                sc.pop('_3d_dir', None)
                print(f'3d: UYARI sahne[{i}] {sc.get("id")} çizilemedi ({_msg(ex)}) '
                      f'-> yedek backdrop/actors', flush=True)
                report.append({'scene': i, 'id': sc.get('id'), 'error': type(ex).__name__})
                if isinstance(ex, TimeoutError):
                    break
    except Exception as ex:      # playwright/Chrome yok, tarayıcı açılamadı vb.
        print(f'3d: UYARI 3D kullanılamıyor ({_msg(ex) if not isinstance(ex, _NoBrowser) else "tarayıcı açılamadı: " + str(ex)}) '
              f'-> yedek backdrop/actors', flush=True)
        for sc in story.get('scenes', []):
            sc.pop('_3d_dir', None)
    finally:
        if br is not None:
            try:
                br.close()
            except Exception:
                pass
    print(f'3d: toplam {time.time() - t0:.1f} sn', flush=True)
    return report


# ------------------------------------------------------------------ scene.py katmanı
def frame_layer(d, n, size):
    """t -> WWxWH RGB kare (scene.py dinamik katmanı). Eksik kare olursa en yakın mevcut kare kullanılır."""
    from PIL import Image
    cache = {}

    def get(t):
        k = min(max(0, (n or 1) - 1), max(0, int(round(t * FPS))))
        if k in cache:
            return cache[k]
        p = os.path.join(d, f'{k:04d}.jpg')
        if not os.path.isfile(p):
            have = sorted(int(f[:4]) for f in os.listdir(d) if f.endswith('.jpg') and f[:4].isdigit())
            k2 = min(have, key=lambda x: abs(x - k))
            p = os.path.join(d, f'{k2:04d}.jpg')
        im = Image.open(p).convert('RGB')
        if im.size != tuple(size):
            im = im.resize(tuple(size), Image.LANCZOS)
        cache.clear()
        cache[k] = im
        return im
    return get
