"""Yapay zekâ sahne görselleri (FLUX) — isteğe bağlı katman.

story.json'da "visual": "image" ve sahnelerde "image": {"prompt": ...} varsa, build.py seslendirmeden sonra
ensure_images() çağırır. Sıra: Cloudflare Workers AI (flux-1-schnell) -> [Pollinations, yalnız BD_POLLINATIONS=1]
-> çizim.
Görsel üretilemeyen sahne kendi "backdrop"/"actors" alanlarıyla çizilir; görselli sahnelerin %75'inden azı
başarılıysa video tümüyle çizime döner. Bu modül hiçbir durumda build'i durdurmaz.

Ortam değişkenleri:
  CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN   Workers AI kimliği (yoksa Cloudflare atlanır)
  BD_IMAGES=0            görselleri kapatır (build.py --no-images)
  BD_POLLINATIONS=1      Pollinations yedeğini açar (varsayılan kapalı; anonim kullanım HTTP 402 veriyor)
  BD_IMAGE_PROVIDER=mock ağsız sahte görsel (yalnız test); BD_MOCK_FAIL=N ilk N isteği başarısız yapar
  BD_IMAGE_BUDGET_S      toplam süre bütçesi (varsayılan 420 sn)
  BD_IMAGE_MAX           video başına üretilen görsel tavanı (varsayılan 30)
  BD_IMAGE_STEPS         Cloudflare adım sayısı (varsayılan 4, en fazla 8)

Güvenlik: token ve tam URL hiçbir zaman yazdırılmaz; hatalarda yalnız sağlayıcı adı ve HTTP kodu basılır.
"""
import base64, hashlib, io, json, os, re, time, urllib.error, urllib.parse, urllib.request
import numpy as np
from PIL import Image, ImageFilter
from .base import LW, LH, OY

STYLE_VERSION = 1
SIZE = 1024
STYLE_PREFIX = ('Cinematic documentary photograph, natural light, 35mm lens, shallow depth of field, subtle film grain, '
                'muted realistic colors, single clear subject centered, simple uncluttered background. ')
STYLE_SUFFIX = ' Color photograph. No text, no letters, no captions, no watermark, no logo, no border.'
PROMPT_MAX = 2048
CF_MODEL = '@cf/black-forest-labs/flux-1-schnell'
CF_BASE = 'https://api.cloudflare.com/client/v4'
POLL_BASE = 'https://image.pollinations.ai'
POLL_GAP = 16.0          # anonim kullanımda istekler arası en az bekleme (sn)
MIN_OK_RATIO = 0.75
UA = 'bir-dakika-video-engine/1.0'

_state = {'cf_off': False, 'poll_last': 0.0, 'mock_calls': 0}


class _Stop(Exception):
    """Sağlayıcıyı bu çalıştırmada bir daha deneme (401/403 kimlik, 429 kota)."""


def _env(k, d=None):
    v = os.environ.get(k)
    return v if v not in (None, '') else d


# ------------------------------------------------------------------ prompt / tohum / önbellek
def full_prompt(story, scene):
    st = story.get('image_style') or {}
    p = str((scene.get('image') or {}).get('prompt', ''))
    p = re.sub(r'\{(subject|setting)\}', lambda m: str(st.get(m.group(1), '')), p)
    p = re.sub(r'\s+', ' ', p).strip()
    room = PROMPT_MAX - len(STYLE_PREFIX) - len(STYLE_SUFFIX)
    return STYLE_PREFIX + p[:room] + STYLE_SUFFIX


def seed_of(story, i, scene):
    im = scene.get('image') or {}
    if isinstance(im.get('seed'), int):
        return im['seed']
    base = (story.get('image_style') or {}).get('seed', 1000)
    return int(base if isinstance(base, int) else 1000) + i


def cache_path(workdir, prompt, seed):
    h = hashlib.sha1(f'{prompt}|{seed}|{SIZE}|{STYLE_VERSION}'.encode('utf-8')).hexdigest()[:16]
    return os.path.join(workdir, 'images', f'{h}.jpg')


# ------------------------------------------------------------------ sağlayıcılar
def _http(req, timeout):
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _cloudflare(prompt, seed, steps=4):
    acct, tok = _env('CLOUDFLARE_ACCOUNT_ID'), _env('CLOUDFLARE_API_TOKEN')
    if not acct or not tok or _state['cf_off']:
        return None
    url = f"{_env('BD_CLOUDFLARE_BASE', CF_BASE)}/accounts/{urllib.parse.quote(acct)}/ai/run/{CF_MODEL}"
    # 'seed' gönderilmez: flux-1-schnell şeması onu kabul etmiyor (HTTP 400 "Additional or unevaluated
    # properties '/seed' not allowed"). seed parametresi yalnız önbellek yolu/mock için imzada kalır.
    body = json.dumps({'prompt': prompt, 'steps': max(1, min(8, int(steps)))}).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST', headers={
        'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json', 'User-Agent': UA})
    try:
        raw = _http(req, 60)
    except urllib.error.HTTPError as ex:
        try:
            detail = ex.read(2000).decode('utf-8', 'replace').lower()
        except Exception:
            detail = ''
        if ex.code in (401, 403) or '"code":10000' in detail.replace(' ', ''):
            _state['cf_off'] = True
            raise _Stop(f'cloudflare HTTP {ex.code} (anahtar/izin)')
        if ex.code == 429 or '4006' in detail or 'neurons' in detail:
            _state['cf_off'] = True
            raise _Stop(f'cloudflare HTTP {ex.code} (günlük kota/sınır)')
        raise RuntimeError(f'cloudflare HTTP {ex.code}')
    except urllib.error.URLError as ex:
        raise RuntimeError(f'cloudflare bağlantı hatası ({type(ex.reason).__name__})')
    ct = raw[:1]
    if ct != b'{':  # bazı sürümler doğrudan görsel baytı döndürebilir
        return raw
    js = json.loads(raw.decode('utf-8'))
    res = js.get('result') if isinstance(js.get('result'), dict) else js
    img = (res or {}).get('image')
    if not js.get('success', True) or not img:
        codes = [e.get('code') for e in js.get('errors', []) if isinstance(e, dict)]
        raise RuntimeError(f'cloudflare yanıtında görsel yok (hata kodları: {codes})')
    return base64.b64decode(img)


def _pollinations(prompt, seed):
    if _env('BD_POLLINATIONS', '0') != '1':
        return None
    wait = POLL_GAP - (time.time() - _state['poll_last'])
    if _state['poll_last'] and wait > 0:
        time.sleep(wait)
    q = urllib.parse.urlencode({'width': SIZE, 'height': SIZE, 'seed': int(seed), 'model': 'flux', 'nologo': 'true'})
    url = f"{_env('BD_POLLINATIONS_BASE', POLL_BASE)}/prompt/{urllib.parse.quote(prompt, safe='')}?{q}"
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        raw = _http(req, 90)
    except urllib.error.HTTPError as ex:
        raise RuntimeError(f'pollinations HTTP {ex.code}')
    except urllib.error.URLError as ex:
        raise RuntimeError(f'pollinations bağlantı hatası ({type(ex.reason).__name__})')
    finally:
        _state['poll_last'] = time.time()
    try:  # olası filigran şeridi: alt %6 kırpılır
        im = Image.open(io.BytesIO(raw)).convert('RGB')
        im = im.crop((0, 0, im.width, int(im.height * 0.94)))
        b = io.BytesIO()
        im.save(b, 'JPEG', quality=93)
        return b.getvalue()
    except Exception:
        return raw


def _mock(prompt, seed):
    """Ağsız, tohumdan türetilmiş sahte 'fotoğraf' (yalnız test)."""
    _state['mock_calls'] += 1
    if _state['mock_calls'] <= int(_env('BD_MOCK_FAIL', '0')):
        raise RuntimeError('mock: yapay hata')
    rng = np.random.default_rng(int(seed) + int(hashlib.sha1(prompt.encode()).hexdigest()[:6], 16))
    c0, c1 = rng.integers(20, 235, 3), rng.integers(20, 235, 3)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32) / SIZE
    a = np.clip(yy[..., None] * 0.8 + xx[..., None] * 0.2, 0, 1)
    img = c0 * (1 - a) + c1 * a
    cx, cy, r = rng.uniform(0.3, 0.7) * SIZE, rng.uniform(0.3, 0.55) * SIZE, rng.uniform(0.12, 0.22) * SIZE
    d = np.sqrt((xx * SIZE - cx) ** 2 + (yy * SIZE - cy) ** 2)
    img[d < r] = img[d < r] * 0.35 + np.array([250, 235, 200]) * 0.65
    img += rng.normal(0, 6, img.shape)
    b = io.BytesIO()
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(b, 'JPEG', quality=92)
    return b.getvalue()


def _valid(data):
    """Pillow açabiliyor, kısa kenar ≥ 512, tek renk/siyah değil -> RGB görsel; aksi hâlde None."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        im = im.convert('RGB')
    except Exception:
        return None
    if min(im.size) < 512:
        return None
    if float(np.asarray(im, dtype=np.float32)[::8, ::8].std()) <= 8:   # tek renk / siyah 'engellendi' görseli
        return None
    return im


def fetch(prompt, seed, deadline=None):
    """(PIL görsel, sağlayıcı) ya da (None, None)."""
    if _env('BD_IMAGE_PROVIDER') == 'mock':
        plan = [('mock', _mock, (1,))]
    else:
        steps = int(_env('BD_IMAGE_STEPS', '4'))
        plan = [('cloudflare', lambda p, s: _cloudflare(p, s, steps), (0, 3))]
        # Pollinations anonim kullanımda HTTP 402 veriyor (deneme başına ~16 sn kayıp): yalnız BD_POLLINATIONS=1 ile
        if _env('BD_POLLINATIONS', '0') == '1':
            plan.append(('pollinations', _pollinations, (0, 8)))
    for name, fn, waits in plan:
        for k, w in enumerate(waits if name != 'mock' else (0,)):
            if deadline and time.time() + w > deadline:
                return None, None
            if w:
                time.sleep(w)
            try:
                data = fn(prompt, seed)
            except _Stop as ex:
                print(f'  images: {ex}; bu çalıştırmada bir daha denenmeyecek', flush=True)
                break
            except Exception as ex:  # zaman aşımı, ağ, bozuk yanıt
                msg = str(ex) if isinstance(ex, RuntimeError) else type(ex).__name__
                print(f'  images: {name} deneme {k + 1} başarısız: {msg}', flush=True)
                continue
            if data is None:
                break  # sağlayıcı kapalı/yapılandırılmamış
            im = _valid(data)
            if im is not None:
                return im, name
            print(f'  images: {name} deneme {k + 1}: geçersiz görsel (boş/küçük/tek renk)', flush=True)
    return None, None


# ------------------------------------------------------------------ ana giriş
def _clear(story):
    for sc in story.get('scenes', []):
        sc.pop('_image_path', None)


def ensure_images(story, workdir):
    """Görselli sahnelerin spec['_image_path'] alanını doldurur. Rapor sözlüğü ya da None döndürür."""
    try:
        return _ensure(story, workdir)
    except Exception as ex:  # görsel hattı hiçbir durumda videoyu durdurmaz
        _clear(story)
        print(f'  images: beklenmeyen hata ({type(ex).__name__}); tümü çizime düştü', flush=True)
        return None


def _ensure(story, workdir):
    _clear(story)
    scenes = story.get('scenes', [])
    stale = os.path.join(workdir, 'images', 'report.json')
    if story.get('visual') != 'image' or _env('BD_IMAGES', '1') == '0':
        if os.path.exists(stale):        # eski rapor yanlış "yapay zekâ görseli var" notu üretmesin
            os.remove(stale)
        if story.get('visual') == 'image':
            print('images: kapalı (--no-images / BD_IMAGES=0) -> çizim', flush=True)
        return None
    idx = [i for i, sc in enumerate(scenes) if isinstance(sc.get('image'), dict) and sc['image'].get('prompt')]
    if not idx:
        return None
    idir = os.path.join(workdir, 'images')
    os.makedirs(idir, exist_ok=True)
    ipath = os.path.join(idir, 'index.json')
    try:
        index = json.load(open(ipath, encoding='utf-8'))
    except (OSError, ValueError):
        index = {}
    budget = float(_env('BD_IMAGE_BUDGET_S', '420'))
    maxn = int(_env('BD_IMAGE_MAX', '30'))
    t0 = time.time()
    deadline = t0 + budget
    got, details = {}, []
    for i in idx:
        sc = scenes[i]
        prompt, seed = full_prompt(story, sc), seed_of(story, i, sc)
        path = cache_path(workdir, prompt, seed)
        prov, cached = None, False
        if os.path.exists(path):
            prov, cached = index.get(os.path.basename(path), 'önbellek'), True
        elif time.time() >= deadline:
            print(f'  images: süre bütçesi ({budget:.0f} sn) doldu; sahne[{i}] çizilecek', flush=True)
        elif len([f for f in os.listdir(idir) if f.endswith('.jpg')]) >= maxn:
            print(f'  images: video başına {maxn} görsel tavanı doldu; sahne[{i}] çizilecek', flush=True)
        else:
            im, prov = fetch(prompt, seed, deadline)
            if im is not None:
                im.save(path, 'JPEG', quality=92)
                index[os.path.basename(path)] = prov
        if prov:
            got[i] = (os.path.abspath(path), prov)
        details.append({'scene': i, 'id': sc.get('id'), 'seed': seed, 'provider': prov or 'drawn',
                        'cached': cached, 'file': os.path.basename(path) if prov else None})
    with open(ipath, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    fallback_all = len(got) < MIN_OK_RATIO * len(idx)
    if fallback_all:
        got = {}
        for d in details:
            d['provider'] = 'drawn'
    for i, (p, _) in got.items():
        scenes[i]['_image_path'] = p
    counts = {}
    for d in details:
        counts[d['provider']] = counts.get(d['provider'], 0) + 1
    rep = {'visual': 'image', 'scenes': len(idx), 'used': len(got), 'counts': counts,
           'fallback_all': fallback_all, 'seconds': round(time.time() - t0, 1), 'details': details}
    with open(os.path.join(idir, 'report.json'), 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    parts = ', '.join(f"{'çizim' if k == 'drawn' else k} {v}" for k, v in counts.items())
    print(f'images: {len(got)}/{len(idx)} ({parts})' + ('  -> tümü çizime düştü' if fallback_all else ''), flush=True)
    return rep


# ------------------------------------------------------------------ katman yerleşimi
def _cover(im, w, h, focus=(0.5, 0.5)):
    k = max(w / im.width, h / im.height)
    r = im.resize((max(w, round(im.width * k)), max(h, round(im.height * k))), Image.LANCZOS)
    x = min(max(0, round(r.width * focus[0] - w / 2)), r.width - w)
    y = min(max(0, round(r.height * focus[1] - h / 2)), r.height - h)
    return r.crop((x, y, x + w, y + h))


def _row_shade():
    """Satır başına karartma katsayısı (katman koordinatı). Alt altyazı bandı ve üst arayüz okunur kalsın."""
    fy = np.arange(LH, dtype=np.float32) - OY        # çerçeve y
    k = np.ones(LH, dtype=np.float32)
    k = np.where(fy < 300, 0.85 + 0.15 * np.clip((fy - 200) / 100, 0, 1), k)
    k = np.where(fy >= 1150, 1.0 - 0.45 * np.clip((fy - 1150) / 770, 0, 1), k)
    return k[:, None, None]


def layer(path, im_spec=None):
    """Görseli motorun katman boyutuna (LW x LH) 'kart' düzeniyle yerleştirir; RGB döndürür."""
    im_spec = im_spec or {}
    src = Image.open(path).convert('RGB')
    fc = im_spec.get('focus') or [0.5, 0.45]
    if src.width / src.height <= 0.8:            # dikey görsel: doğrudan kapla
        out = _cover(src, LW, LH, fc)
    else:                                        # kare/yatay: bulanık arka + net kart
        bg = _cover(src, LW, LH, fc).filter(ImageFilter.GaussianBlur(40))
        bg = Image.fromarray((np.asarray(bg, dtype=np.float32) * 0.45).astype(np.uint8))
        ch = round(src.height * LW / src.width)
        card = src.resize((LW, ch), Image.LANCZOS)
        fade = min(160, ch // 4)
        m = np.full((ch, LW), 255, np.float32)
        m[ch - fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None]
        bg.paste(card, (0, OY - 40), Image.fromarray(m.astype(np.uint8)))  # kamera kaydığında üstte boşluk kalmasın
        out = bg
    a = np.asarray(out, dtype=np.float32) * _row_shade()
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
