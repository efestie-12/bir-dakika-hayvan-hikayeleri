#!/usr/bin/env python3
"""story.json doğrulayıcı.

Kullanım:
  python scripts/validate_story.py stories/<slug>/story.json [--strict]

Hatalar  -> çıkış kodu 1 (video üretilmez).
Uyarılar -> çıkış kodu 0 (--strict verilirse uyarılar da hata sayılır).
"""
import argparse, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.backdrops import PRESETS          # noqa: E402
from engine.actors import TYPES as ACTOR_TYPES  # noqa: E402
from engine.overlays import BUILDERS, F, spaced  # noqa: E402
from engine.fx import KINDS as FX_KINDS       # noqa: E402
from engine.music import MOODS, SFX_TYPES, ROOTS  # noqa: E402

VOICES = ('fahrettin', 'dfki', 'fettah')
CAP_STYLES = ('cap', 'big')
TITLE_MAX = 70
TAGS_MAX_CHARS = 500
DUR_MIN, DUR_MAX = 45.0, 75.0
FRAME_W = 1080

# Her overlay türü için zorunlu alanlar
OVERLAY_REQ = {
    'chip': ['text'], 'counter': ['to'], 'big': ['text'], 'tag': ['text'], 'bars': ['items'],
    'route': ['points'], 'newspapers': ['items'], 'title': ['text'], 'outro': [], 'cracks': ['x', 'y'],
}

# Taslak tahmini süre (Togo ölçümünden: ~0.058 sn/karakter + boşluklar)
SEC_PER_CHAR, LINE_GAP, SCENE_GAP, FIXED, PAUSE = 0.058, 0.18, 0.2, 3.2, 0.5


def estimate_duration(story):
    chars = lines = pauses = 0
    for sc in story.get('scenes', []):
        for ln in sc.get('lines', []):
            t = str(ln.get('tts', ''))
            chars += len(t)
            lines += 1
            pauses += t.count('...')
    return chars * SEC_PER_CHAR + lines * LINE_GAP + len(story.get('scenes', [])) * SCENE_GAP + FIXED + pauses * PAUSE


def count_emoji(s):
    n = 0
    for ch in s:
        o = ord(ch)
        if o in (0x200D, 0xFE0F) or 0x1F3FB <= o <= 0x1F3FF:
            continue  # birleştirici / varyasyon / ten rengi karakterleri ayrı sayılmaz
        if o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF:
            n += 1
    return n


class Report:
    def __init__(self):
        self.err, self.warn = [], []

    def e(self, msg):
        self.err.append(msg)

    def w(self, msg):
        self.warn.append(msg)


def check_time(r, where, spec, n_lines):
    if spec is None or isinstance(spec, (int, float)):
        return
    p = str(spec).split(':')
    try:
        if p[0] == 'line':
            i = int(p[1])
            if len(p) > 2:
                float(p[2])
            if i >= n_lines:
                r.e(f'{where}: "{spec}" geçersiz — bu sahnede yalnızca {n_lines} satır var (0..{n_lines - 1}).')
            return
        if p[0] == 'end':
            float(p[1])
            return
        float(spec)
    except (ValueError, IndexError):
        r.e(f'{where}: zaman ifadesi anlaşılamadı: "{spec}" (sayı, "line:N", "line:N:0.5" veya "end:-1.5" olmalı).')


def text_width(text, font, size, spacing=0, stroke=0):
    return spaced(str(text), F(font, size), (255, 255, 255), spacing, stroke).width


def check_backdrop(r, where, b):
    if isinstance(b, str):
        if b not in PRESETS:
            r.e(f'{where}: bilinmeyen backdrop preset "{b}". Geçerli: {", ".join(PRESETS)}')
    elif isinstance(b, dict):
        if 'preset' in b:
            if b['preset'] not in PRESETS:
                r.e(f'{where}: bilinmeyen backdrop preset "{b["preset"]}". Geçerli: {", ".join(PRESETS)}')
        elif 'sky' not in b and 'map' not in b:
            r.e(f'{where}: backdrop sözlüğünde "preset", "sky" veya "map" anahtarlarından biri olmalı.')
        for k in ('far', 'mid', 'ground'):
            if k in b and not isinstance(b[k], dict):
                r.e(f'{where}: backdrop.{k} bir sözlük olmalı.')
    else:
        r.e(f'{where}: backdrop preset adı (metin) veya sözlük olmalı.')


def check_overlay(r, where, o, n_lines):
    t = o.get('type')
    if t not in BUILDERS:
        r.e(f'{where}: bilinmeyen overlay türü "{t}". Geçerli: {", ".join(BUILDERS)}')
        return
    for k in OVERLAY_REQ.get(t, []):
        if k not in o:
            r.e(f'{where}: "{t}" overlay için "{k}" alanı zorunlu.')
    for k in ('at', 'until', 'dur_to', 'fade_at'):
        if k in o:
            check_time(r, f'{where}.{k}', o[k], n_lines)
    # metin taşması kontrolü (yaklaşık; kesin kontrol için --stills ile kareye bakın)
    try:
        wd = None
        if t == 'big' and 'text' in o:
            wd = text_width(o['text'], 'InterDisplay-Black.otf', o.get('size', 120), o.get('spacing', 4), o.get('stroke', 8))
            cx = o.get('x', FRAME_W / 2)
            if cx - wd / 2 < 0 or cx + wd / 2 > FRAME_W:
                r.w(f'{where}: "big" metni "{o["text"]}" ekrandan taşıyor olabilir (genişlik ≈{wd}px, x={cx}). size küçültün veya x ayarlayın.')
            wd = None
        elif t == 'title' and 'text' in o:
            wd = text_width(o['text'], 'InterDisplay-Black.otf', o.get('size', 170), o.get('spacing', 22))
        elif t == 'chip' and 'text' in o:
            wd = text_width(o['text'], 'Inter-Bold.otf', 34, 4) + 66 + 64
        elif t == 'counter' and 'to' in o:
            wd = text_width(f'{int(o["to"]):,}'.replace(',', '.') + (' ' + o['unit'] if o.get('unit') else ''),
                            'InterDisplay-Black.otf', o.get('size', 150), 2, 8)
        elif t == 'tag' and 'text' in o and not o.get('follow'):
            w2 = text_width(o['text'], 'InterDisplay-Black.otf', o.get('size', 64), 6, 6)
            cx = o.get('x', 0)
            if cx - w2 / 2 < 0 or cx + w2 / 2 > FRAME_W:
                r.w(f'{where}: "tag" metni "{o["text"]}" ekrandan taşıyor olabilir (genişlik ≈{w2}px, x={cx}).')
        if wd and wd > FRAME_W - 20:
            r.w(f'{where}: "{t}" metni çok geniş (≈{wd}px > {FRAME_W}px). Kısaltın ya da size değerini düşürün.')
    except Exception as ex:  # font hatası vb. doğrulamayı durdurmasın
        r.w(f'{where}: metin genişliği ölçülemedi ({ex}).')
    if t == 'bars':
        for i, it in enumerate(o.get('items', [])):
            if 'name' not in it or 'value' not in it:
                r.e(f'{where}.items[{i}]: "name" ve "value" zorunlu.')
            elif not isinstance(it['value'], (int, float)):
                r.e(f'{where}.items[{i}]: "value" sayı olmalı.')
            if 'at' in it:
                check_time(r, f'{where}.items[{i}].at', it['at'], n_lines)
        if o.get('icon') and o['icon'] not in ('husky', 'cat', 'horse', 'elephant', 'bird'):
            r.w(f'{where}: bars.icon "{o["icon"]}" tanınmıyor, husky çizilecek. Geçerli: husky, cat, horse, elephant, bird')
    if t == 'route':
        pts = o.get('points', [])
        if len(pts) < 2:
            r.e(f'{where}: route en az 2 nokta içermeli.')
    if t == 'newspapers':
        for i, it in enumerate(o.get('items', [])):
            if 'headline' not in it:
                r.e(f'{where}.items[{i}]: "headline" zorunlu.')
    if t == 'tag' and o.get('follow') and 'x' not in o['follow']:
        r.e(f'{where}: tag.follow için x ve y zorunlu.')


def validate(path):
    r = Report()
    try:
        story = json.load(open(path, encoding='utf-8'))
    except FileNotFoundError:
        r.e(f'Dosya bulunamadı: {path}')
        return r, None
    except json.JSONDecodeError as ex:
        r.e(f'JSON sözdizimi hatası: {ex}')
        return r, None

    # ---- üst düzey alanlar
    for k in ('slug', 'youtube_title', 'description', 'tags', 'scenes'):
        if k not in story or story[k] in (None, '', []):
            r.e(f'Zorunlu alan eksik veya boş: "{k}"')
    slug = story.get('slug', '')
    if slug and not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', slug):
        r.e(f'slug yalnızca küçük harf, rakam ve tire içermeli (Türkçe karakter yok): "{slug}"')
    folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if slug and folder != slug:
        r.e(f'slug ("{slug}") klasör adıyla ("{folder}") aynı olmalı.')
    if story.get('voice', 'fahrettin') not in VOICES:
        r.e(f'Bilinmeyen ses "{story.get("voice")}". Geçerli: {", ".join(VOICES)}')
    if story.get('key', 'Dm') not in ROOTS:
        r.w(f'Bilinmeyen müzik tonu "{story.get("key")}", Dm kullanılacak. Geçerli: {", ".join(ROOTS)}')
    if 'pron' in story and not (isinstance(story['pron'], dict) and all(isinstance(v, str) for v in story['pron'].values())):
        r.e('"pron" alanı {"Kelime": "okunuş"} biçiminde metin sözlüğü olmalı.')

    # ---- başlık
    title = story.get('youtube_title', '') or ''
    if len(title) > TITLE_MAX:
        r.e(f'Başlık çok uzun: {len(title)} karakter (en fazla {TITLE_MAX}).')
    ne = count_emoji(title)
    if ne != 1:
        r.w(f'Başlıkta tam 1 emoji olmalı (şu an {ne}).')
    if title and title.upper() == title and any(c.isalpha() for c in title):
        r.w('Başlığın tamamı büyük harf; clickbait gibi görünebilir.')

    # ---- açıklama
    desc = story.get('description', '') or ''
    if 'temsilidir' not in desc:
        r.e('Açıklamada "Görseller temsilidir, anlatılan olay gerçektir." notu bulunmalı.')
    if '#shorts' not in desc.lower():
        r.w('Açıklamada #shorts etiketi yok.')
    tags_in_desc = re.findall(r'#\w+', desc)
    if tags_in_desc and not (4 <= len(tags_in_desc) <= 6):
        r.w(f'Açıklamada #shorts + 3-5 hashtag önerilir (şu an {len(tags_in_desc)} hashtag).')
    if not re.search(r'https?://', desc):
        r.w('Açıklamada kaynak bağlantısı (http...) bulunamadı. "Kaynaklar:" listesi ekleyin.')
    if len(desc) > 5000:
        r.e(f'Açıklama YouTube sınırını aşıyor: {len(desc)} > 5000 karakter.')

    # ---- etiketler
    tags = story.get('tags', [])
    if not isinstance(tags, list) or not all(isinstance(t, str) and t.strip() for t in tags):
        r.e('"tags" boş olmayan metinlerden oluşan bir liste olmalı.')
    elif sum(len(t) for t in tags) + 2 * len(tags) > TAGS_MAX_CHARS:
        r.e(f'Etiketlerin toplam uzunluğu YouTube sınırını ({TAGS_MAX_CHARS}) aşıyor.')

    # ---- sahneler
    scenes = story.get('scenes', [])
    if not isinstance(scenes, list):
        r.e('"scenes" bir liste olmalı.')
        scenes = []
    ids = set()
    has_outro = False
    for si, sc in enumerate(scenes):
        sid = sc.get('id') or f'#{si}'
        where = f'sahne[{si}] "{sid}"'
        if not sc.get('id'):
            r.e(f'{where}: "id" zorunlu.')
        elif sc['id'] in ids:
            r.e(f'{where}: aynı id iki kez kullanılmış.')
        ids.add(sc.get('id'))
        if sc.get('mood', 'calm') not in MOODS:
            r.e(f'{where}: bilinmeyen mood "{sc.get("mood")}". Geçerli: {", ".join(MOODS)}')
        if 'wind' in sc and not (isinstance(sc['wind'], (int, float)) and 0 <= sc['wind'] <= 1.5):
            r.e(f'{where}: wind 0-1 arası sayı olmalı.')
        check_backdrop(r, f'{where}.backdrop', sc.get('backdrop', 'plain_dark'))
        lines = sc.get('lines', [])
        if not lines:
            r.e(f'{where}: en az bir seslendirme satırı ("lines") gerekli.')
        n = max(1, len(lines))
        for li, ln in enumerate(lines):
            lw = f'{where}.lines[{li}]'
            tts = ln.get('tts')
            if not isinstance(tts, str) or not tts.strip():
                r.e(f'{lw}: "tts" boş olamaz.')
                continue
            if re.search(r'\d', tts):
                r.w(f'{lw}: tts içinde rakam var ("{tts[:40]}…"). Seslendirme için sayıları yazıyla yazın (ör. "bin dokuz yüz yirmi beş").')
            if not re.search(r'[.!?…]\s*$', tts.strip()):
                r.w(f'{lw}: tts noktalama ile bitmiyor; tonlama doğal olmayabilir.')
            if ln.get('style', 'cap') not in CAP_STYLES:
                r.e(f'{lw}: style "cap" veya "big" olmalı.')
            cap = ln.get('cap', tts)
            if len(cap) > 120:
                r.w(f'{lw}: altyazı çok uzun ({len(cap)} karakter); ekranda 3+ satıra taşabilir. Kısaltın veya satırı bölün.')
        for k in ('fx',):
            for fxn in sc.get(k, []) or []:
                if fxn not in FX_KINDS:
                    r.e(f'{where}: bilinmeyen fx "{fxn}". Geçerli: {", ".join(FX_KINDS)}')
        for ai, a in enumerate(sc.get('actors', []) or []):
            aw = f'{where}.actors[{ai}]'
            if a.get('type') not in ACTOR_TYPES:
                r.e(f'{aw}: bilinmeyen aktör türü "{a.get("type")}". Geçerli: {", ".join(ACTOR_TYPES)}')
            for k in ('x', 'y'):
                if not isinstance(a.get(k), (int, float)):
                    r.e(f'{aw}: "{k}" sayı olarak zorunlu.')
            if a.get('motion', 'idle') not in ('idle', 'gallop', 'walk', 'fly'):
                r.e(f'{aw}: motion idle | gallop | walk | fly olmalı.')
            if 'at' in a:
                check_time(r, f'{aw}.at', a['at'], n)
        for oi, o in enumerate(sc.get('overlays', []) or []):
            check_overlay(r, f'{where}.overlays[{oi}]', o, n)
            if o.get('type') == 'outro':
                has_outro = True
        for ei, e in enumerate(sc.get('sfx', []) or []):
            if e.get('type') not in SFX_TYPES:
                r.e(f'{where}.sfx[{ei}]: bilinmeyen sfx "{e.get("type")}". Geçerli: {", ".join(SFX_TYPES)}')
            check_time(r, f'{where}.sfx[{ei}].at', e.get('at'), n)
        for key in ('punch', 'shake', 'flash'):
            for ki, p in enumerate(sc.get(key, []) or []):
                if 'at' not in p:
                    r.e(f'{where}.{key}[{ki}]: "at" zorunlu.')
                else:
                    check_time(r, f'{where}.{key}[{ki}].at', p['at'], n)
        cam = sc.get('camera', {}) or {}
        for k in ('zoom', 'pan', 'pany'):
            if k in cam and not (isinstance(cam[k], list) and len(cam[k]) == 2):
                r.e(f'{where}.camera.{k}: iki sayılık liste olmalı, ör. [1.0, 1.06].')
        if 'zoom' in cam and isinstance(cam['zoom'], list) and len(cam['zoom']) == 2 and min(cam['zoom']) < 1.0:
            r.w(f'{where}.camera.zoom 1.0 altında; kenarlarda boşluk görünebilir.')
    if scenes and not has_outro:
        r.w('Hiçbir sahnede "outro" overlay yok; kapanışta takip çağrısı olmalı.')
    if scenes and not (5 <= len(scenes) <= 12):
        r.w(f'Sahne sayısı {len(scenes)}; 6-10 arası önerilir.')

    est = estimate_duration(story)
    if not (DUR_MIN <= est <= DUR_MAX):
        r.w(f'Tahmini süre {est:.0f} sn; {DUR_MIN:.0f}-{DUR_MAX:.0f} sn aralığı dışında (hedef 55-65 sn).')
    return r, est


def main(argv=None):
    ap = argparse.ArgumentParser(description='story.json doğrulayıcı')
    ap.add_argument('story', nargs='+')
    ap.add_argument('--strict', action='store_true', help='uyarıları da hata say')
    a = ap.parse_args(argv)
    failed = False
    for path in a.story:
        r, est = validate(path)
        print(f'== {path}')
        if est is not None:
            print(f'   tahmini süre: ~{est:.0f} sn')
        for m in r.err:
            print(f'   HATA  : {m}')
        for m in r.warn:
            print(f'   UYARI : {m}')
        bad = bool(r.err) or (a.strict and r.warn)
        print('   SONUÇ : ' + ('BAŞARISIZ' if bad else 'GEÇTİ' + (' (uyarılarla)' if r.warn else '')))
        failed |= bool(bad)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
