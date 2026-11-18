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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from history import CATEGORIES, HOOKS, load as load_history  # noqa: E402

VOICES = ('fahrettin', 'dfki', 'fettah')
CAP_STYLES = ('cap', 'big')
TITLE_MAX = 70
TAGS_MAX_CHARS = 500
DUR_MIN, DUR_MAX = 45.0, 75.0
FRAME_W = 1080
BAR_ICONS = ('husky', 'cat', 'horse', 'elephant', 'bird', 'none')
# Yeni format kuralları gelmeden yayınlanmış hikâyeler: yeni HATA'lar bunlarda UYARI'ya iner
LEGACY_SLUGS = ('godwit-rekor',)
AI_DESC_LINE = 'Görseller yapay zekâ ile üretilmiştir.'
VISUAL_MODES = ('image', 'drawn')
IMAGE_FREE_PRESETS = ('plain_dark', 'plain_warm', 'map_dark')

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
        self.legacy = False

    def e(self, msg):
        self.err.append(msg)

    def w(self, msg):
        self.warn.append(msg)

    def ne(self, msg):
        """Yeni format kuralı hatası: eski hikâyelerde (LEGACY_SLUGS) uyarıya iner."""
        if self.legacy:
            self.warn.append('(eski hikâye) ' + msg)
        else:
            self.err.append(msg)


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
        if o.get('icon') and o['icon'] not in BAR_ICONS:
            r.w(f'{where}: bars.icon "{o["icon"]}" tanınmıyor, husky çizilecek. Geçerli: {", ".join(BAR_ICONS)}')
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


# ------------------------------------------------------------------ format kuralları (CLAUDE.md §2-§7, K1-K24)
SEC_PER_CHAR_AT, LEAD_IN = 0.055, 0.35
TR_MONTHS = ('ocak', 'şubat', 'mart', 'nisan', 'mayıs', 'haziran', 'temmuz', 'ağustos', 'eylül', 'ekim',
             'kasım', 'aralık')
RE_YEAR_TTS = re.compile(r'\b(bin (iki |üç |dört |beş |altı |yedi |sekiz |dokuz )?yüz|iki bin)\b')
RE_YEAR_CAP = re.compile(r'\b(1\d{3}|20\d{2})\b')
RE_MONTH = re.compile(r'\b(' + '|'.join(TR_MONTHS) + r')\b')
_NUMW = r'(?:on|yirmi|otuz|kırk|elli|altmış|yetmiş|seksen|doksan|yüz|bin|iki|üç|dört|beş|altı|yedi|sekiz|dokuz)'
# Başlıkta "sayı + birim" (ör. "133 gün", "on bir gün"): rekor/sonuç başlıkta veriliyor olabilir (CLAUDE.md §7).
# Tek başına "bir" sayılmaz ("bir gün" deyimi yanlış uyarı vermesin).
RE_TITLE_MEASURE = re.compile(r'(?<!\w)(\d[\d.,]*|' + _NUMW + r'(?:\s+(?:bir|' + _NUMW[3:-1] + r'))*)\s+'
                              r'(gün|saat|yıl|hafta|dakika|saniye|kilometre|km|metre|mil|derece)(?!\w)')
BANNED_WORDS = (r'\bşok\b', r'\binanamayacaksınız', r'\bkimse bilmiyor', r'\byasaklanan', r'açıklayamıyor',
                r'\bölüm', r'\böldü', r'\bceset', r'\bkatliam')


def trlower(s):
    return str(s).replace('I', 'ı').replace('İ', 'i').lower()


def words(s):
    return [w for w in re.split(r'\s+', str(s).strip()) if re.search(r'\w', w)]


def est_at(spec, lines):
    """Zaman ifadesinin yaklaşık saniyesi (seslendirme yapılmadan, ~0,055 sn/karakter)."""
    if spec is None:
        return 0.0
    if isinstance(spec, (int, float)):
        return float(spec)
    p = str(spec).split(':')
    try:
        if p[0] == 'line':
            n = min(int(p[1]), max(0, len(lines) - 1))
            fr = float(p[2]) if len(p) > 2 else 0.0
            ln = [len(str(l.get('tts', ''))) for l in lines]
            return LEAD_IN + sum(c * SEC_PER_CHAR_AT + 0.18 for c in ln[:n]) + fr * (ln[n] if ln else 0) * SEC_PER_CHAR_AT
        if p[0] == 'end':
            return 999.0
        return float(spec)
    except (ValueError, IndexError):
        return 999.0


def has_year(tts, cap=''):
    return bool(RE_YEAR_TTS.search(trlower(tts)) or RE_YEAR_CAP.search(str(cap)) or RE_YEAR_CAP.search(str(tts)))


def domain_of(url):
    host = re.sub(r'^https?://', '', url).split('/')[0].split(':')[0].lower()
    lab = [x for x in host.split('.') if x]
    if lab and lab[0] == 'www':
        lab = lab[1:]
    if len(lab) >= 3 and len(lab[-1]) == 2 and lab[-2] in ('co', 'com', 'gov', 'edu', 'org', 'ac', 'net', 'gen', 'bel', 'k12'):
        return '.'.join(lab[-3:])
    return '.'.join(lab[-2:])


def check_format(r, story, scenes):
    slug = story.get('slug', '')
    cat, hook, subj = story.get('category'), story.get('hook'), story.get('subject')
    # K1-K3: kategori, kanca kalıbı, özne
    if cat not in CATEGORIES:
        r.ne(f'"category" zorunlu. Geçerli: {", ".join(CATEGORIES)}' + (f' (şu an "{cat}")' if cat else ''))
    if hook not in HOOKS:
        r.ne(f'"hook" (kanca kalıbı) zorunlu. Geçerli: {", ".join(HOOKS)}' + (f' (şu an "{hook}")' if hook else ''))
    if not isinstance(subj, str) or not subj.strip():
        r.ne('"subject" zorunlu: hikâyenin kısa öznesi (kişi/hayvan/olay).')

    title = story.get('youtube_title', '') or ''
    desc = story.get('description', '') or ''
    if scenes:
        s0 = scenes[0]
        l0 = s0.get('lines', []) or []
        # K4-K5: açılışta iri ekran yazısı
        bigs = [o for o in s0.get('overlays', []) or [] if o.get('type') == 'big']
        if not any(est_at(o.get('at'), l0) <= 1.0 for o in bigs):
            r.ne('İlk sahnede 0. saniyede iri ekran yazısı yok. {"type":"big","at":0,…} ekleyin (CLAUDE.md §5).')
        for o in bigs:
            txt = str(o.get('text', ''))
            y, size = o.get('y', 560), o.get('size', 120)
            if len(txt) > 16 or len(words(txt)) > 3 or size < 90 or not (300 <= y <= 800):
                r.w(f'Açılış yazısı "{txt}" uzun/küçük/yanlış yerde: en fazla 3 kelime, 16 karakter, size ≥ 90, y 320-520.')
        # K6-K9: kanca cümleleri
        if l0:
            t0 = str(l0[0].get('tts', ''))
            nw, nc = len(words(t0)), len(t0)
            if nw > 16 or nc > 110:
                r.ne(f'İlk cümle çok uzun ({nw} kelime, {nc} karakter). En fazla 12 kelime / 80 karakter.')
            elif nw > 12 or nc > 80:
                r.w(f'İlk cümle uzun ({nw} kelime, {nc} karakter); hedef 6-10 kelime.')
            # K10: tarihle başlayan açılış
            head_t = ' '.join(words(t0)[:4])
            head_c = ' '.join(words(l0[0].get('cap', t0))[:4])
            if RE_YEAR_TTS.search(trlower(head_t)) or RE_MONTH.search(trlower(head_t)) or RE_YEAR_CAP.search(head_c):
                r.w('İlk cümle tarihle başlıyor. Tarih/yer 2. sahnede chip overlay\'inde olsun.')
        if len(l0) != 2:
            r.w(f'İlk sahne 2 satır olmalı: kurulum + kırılma (şu an {len(l0)}).')
        tot = sum(len(str(l.get('tts', ''))) for l in l0)
        if tot > 130:
            r.w(f'Kanca ~7 sn\'yi aşıyor ({tot} karakter); kırılma cümlesi gecikiyor.')
        # K11: yalnız tarih/yer söyleyen kısa cümle (ilk iki sahne)
        for si in range(min(2, len(scenes))):
            for li, ln in enumerate(scenes[si].get('lines', []) or []):
                for sent in re.split(r'(?<=[.!?…])\s+', str(ln.get('tts', '')).strip()):
                    if sent and len(words(sent)) <= 6 and (has_year(sent) or RE_MONTH.search(trlower(sent))):
                        r.w(f'sahne[{si}].lines[{li}]: yalnız tarih/yer söyleyen cümle ("{sent}"). Silin; bilgiyi chip\'e taşıyın.')
        # K12-K14: ses vurgusu, kırılma vurgusu, hareket
        if not any(est_at(e.get('at'), l0) <= 3.0 for e in s0.get('sfx', []) or []):
            r.w('İlk 3 saniyede sfx yok. {"type":"impact","at":0.05,"gain":0.5} ekleyin.')
        if not (s0.get('flash') or s0.get('punch')):
            r.w('İlk sahnede kırılma vurgusu (flash/punch at "line:1") yok.')
        moving = any(a.get('motion', 'idle') != 'idle' or a.get('speed') for a in s0.get('actors', []) or []) or bool(s0.get('fx'))
        zoom = (s0.get('camera', {}) or {}).get('zoom', [1.0, 1.06])
        zd = abs(zoom[1] - zoom[0]) if isinstance(zoom, list) and len(zoom) == 2 else 0
        if not moving or zd < 0.08:
            r.w('İlk sahne durağan: hareketli aktör/fx ekleyin, kamera zoom farkı ≥ 0.10 olsun.')
        # K21 (ilk sahne)
        s0_text = ' '.join([str(l.get('tts', '')) + ' ' + str(l.get('cap', '')) for l in l0] + [str(o.get('text', '')) for o in bigs])
    else:
        s0_text = ''

    # K15-K17: kaynaklar
    if 'Kaynaklar:' not in desc:
        r.ne('Açıklamada "Kaynaklar:" başlığı yok.')
    doms = []
    for u in re.findall(r'https?://[^\s)>\]]+', desc):
        d = domain_of(u)
        if d and d not in doms:
            doms.append(d)
    if len(doms) < 2:
        r.ne(f'En az 2 farklı alan adından kaynak gerekli (şu an {len(doms)}).')
    elif all(d == 'wikipedia.org' for d in doms):
        r.w('Kaynakların hepsi Wikipedia; en az bir kurum/basın kaynağı ekleyin.')
    # K24: izleyiciye soru
    if not any(l.strip().endswith('?') for l in desc.splitlines()):
        r.w('Açıklamada izleyiciye soru yok (yorum için tek soru ekleyin).')

    # K18-K19: kapanış
    for si, sc in enumerate(scenes):
        for o in sc.get('overlays', []) or []:
            if o.get('type') != 'outro':
                continue
            cta = o.get('cta')
            if cta and 'hayvan' in trlower(cta):
                r.ne('outro.cta eski metni içeriyor. "cta"/"footer" alanlarını silin; motor varsayılanı kullanılır.')
            elif cta:
                r.w(f'sahne[{si}]: outro.cta yazılmış; silin, motor varsayılanı kullanılır.')
            ft = o.get('footer')
            if ft and not (story.get('visual') == 'image' and 'yapay zekâ' in trlower(ft)):
                r.w(f'sahne[{si}]: outro.footer yazılmış; silin (yalnız yapay zekâ görselli videoda CLAUDE.md §11\'deki metin yazılır).')
            if isinstance(o.get('y'), (int, float)) and o['y'] > 1600:
                r.w('outro.y Shorts arayüzünün altında kalır (y ≤ 1600 olmalı).')

    # K20-K22: başlık ve etiketler
    if len(title) > 60:
        r.w(f'Başlık 60 karakteri aşıyor ({len(title)}); akışta kesilebilir.')
    m = RE_TITLE_MEASURE.search(trlower(title))
    if m:
        r.w(f'Başlıkta sayı+birim var ("{m.group(0)}"): rekor/sonuç başlıkta verilmesin, merak boşluğu bırakın (CLAUDE.md §7).')
    # orta video takip çağrısı (ilk ve son sahne hariç; CLAUDE.md §6)
    if len(scenes) >= 3:
        mid = scenes[1:-1]
        if not any('takip' in trlower(l.get('tts', '')) for sc in mid for l in sc.get('lines', []) or []) and \
           not any('takip' in trlower(o.get('text', '')) for sc in mid for o in sc.get('overlays', []) or []):
            r.w('Orta sahnelerde takip çağrısı yok: videonun %60-75\'i civarında kısa bir "…takip et." satırı ve '
                '"TAKİP ET" big/tag yazısı ekleyin (CLAUDE.md §6).')
    for where, txt in (('Başlıkta', title), ('Kancada', s0_text)):
        low = trlower(txt)
        for pat in BANNED_WORDS:
            m = re.search(pat, low)
            if m:
                r.w(f'{where} kaçınılacak ifade: "{m.group(0)}".')
    tags = story.get('tags', []) if isinstance(story.get('tags'), list) else []
    if cat in CATEGORIES and cat != 'hayvan' and any(trlower(t).replace('â', 'a') == 'hayvan hikayeleri' for t in tags):
        r.w('Etiketlerde "hayvan hikayeleri" var ama kategori hayvan değil.')

    # K23: geçmişe göre tekrar (asıl kısıt history.py recent ile uygulanır; burada yalnız uyarı)
    try:
        ents = load_history()['entries']
    except Exception:
        ents = None
    if ents is not None and cat in CATEGORIES:
        idx = next((i for i, e in enumerate(ents) if e.get('slug') == slug), None)
        prev = ents[:idx] if idx is not None else ents
        if prev and prev[-1].get('category') == cat:
            r.w(f'Kategori "{cat}" bir önceki videoyla aynı.')
        if [e.get('category') for e in prev[-6:]].count(cat) >= 2:
            r.w(f'Kategori "{cat}" son 6 videoda zaten 2 kez kullanıldı.')
        if hook in HOOKS and hook in [e.get('hook') for e in prev[-3:]]:
            r.w(f'Kanca kalıbı "{hook}" son 3 videoda kullanıldı.')


# ------------------------------------------------------------------ yapay zekâ görselleri (CLAUDE.md §11, K25-K37)
def _rx(words_):
    return re.compile(r'\b(' + '|'.join(words_) + r')\b', re.I)


IMG_BANNED_FAKE = _rx([r'black and white', r'b&w', r'monochrome', r'sepia', r'vintage photo(graph)?s?', r'old photo(graph)?s?',
                       r'archival', r'archive photos?', r'daguerreotypes?', r'newsreel', r'press photos?', r'found footage',
                       r'black-and-white', r'grayscale', r'greyscale'])
IMG_BANNED_CONTENT = _rx([r'child', r'children', r'kids?', r'boys?', r'girls?', r'bab(y|ies)', r'toddlers?', r'blood(y)?',
                          r'gore', r'corpses?', r'dead bod(y|ies)', r'wounds?', r'wounded', r'nude', r'naked'])
IMG_BANNED_IDENT = _rx([r'looks? like', r'portrait of', r'celebrit(y|ies)', r'president', r'logos?', r'flag of', r'brands?'])
IMG_PEOPLE = _rx([r'man', r'men', r'woman', r'women', r'person', r'people', r'sailors?', r'soldiers?', r'scientists?',
                  r'doctors?', r'pilots?', r'explorers?', r'workers?', r'crowd', r'fisherm[ae]n', r'astronauts?', r'nurses?'])
IMG_ANON = _rx([r'from behind', r'seen from behind', r'silhouetted?', r'distant figures?', r'face not visible',
                r'hands only', r'back view', r'faces? hidden'])
RE_PLACEHOLDER = re.compile(r'\{([^{}]*)\}')


def expand_prompt(prompt, style):
    return RE_PLACEHOLDER.sub(lambda m: str(style.get(m.group(1), m.group(0))), str(prompt))


def check_images(r, story, scenes):
    visual = story.get('visual')
    style = story.get('image_style')
    img_idx = [i for i, sc in enumerate(scenes) if sc.get('image') is not None]
    # K25-K26
    if visual is not None and visual not in VISUAL_MODES:
        r.ne('"visual" yalnız "image" ya da "drawn" olabilir.')
        return
    if visual != 'image':
        for i in img_idx:
            r.ne(f'Çizim kipinde "image" alanı kullanılamaz (sahne[{i}]). Alanı silin ya da "visual": "image" yazın.')
        if style is not None:
            r.ne('Çizim kipinde "image_style" alanı kullanılamaz. Alanı silin ya da "visual": "image" yazın.')
        return
    # K27
    if not isinstance(style, dict):
        r.ne('"visual": "image" iken "image_style" {seed, subject, setting} zorunlu.')
        style = {}
    if not isinstance(style.get('seed'), int) or isinstance(style.get('seed'), bool) or not (1 <= style.get('seed', 0) <= 999999):
        r.ne('image_style.seed 1-999999 arası tam sayı olmalı.')
    if len(words(style.get('subject', ''))) < 8:
        r.ne('image_style.subject en az 8 kelimelik İngilizce tarif olmalı.')
    if not str(style.get('setting', '')).strip():
        r.w('image_style.setting boş; dönem, yer ve mevsimi yazın (ör. "1920s Alaska, deep winter").')
    for k in ('subject', 'setting'):
        v = str(style.get(k, ''))
        for rx in (IMG_BANNED_FAKE, IMG_BANNED_CONTENT, IMG_BANNED_IDENT):
            m = rx.search(v)
            if m:
                r.ne(f'image_style.{k} yasak ifade içeriyor: "{m.group(0)}".')
    if not (4 <= len(img_idx) <= 7):
        r.w(f'Görselli sahne sayısı {len(img_idx)}; 4-7 olmalı.')
    if scenes and (0 not in img_idx or len(scenes) - 1 not in img_idx):
        r.w('Yapay zekâ görselli videoda ilk ve son sahne görselli olmalı.')
    names = set()
    for src in (story.get('subject', ''), story.get('youtube_title', '')):
        for w_ in re.findall(r"[A-ZÇĞİÖŞÜ][\wçğıöşüâîû]{3,}", str(src)):
            names.add(w_.split("'")[0])
    for i, sc in enumerate(scenes):
        im = sc.get('image')
        if im is None:
            # K36
            b = sc.get('backdrop', 'plain_dark')
            pre = b if isinstance(b, str) else b.get('preset', 'custom')
            if pre not in IMAGE_FREE_PRESETS or sc.get('actors'):
                r.w(f'sahne[{i}]: görselli videoda görselsiz sahne düz zeminli veri sahnesi olmalı (plain_dark/plain_warm/map_dark, aktörsüz).')
            continue
        where = f'sahne[{i}].image'
        if not isinstance(im, dict):
            r.ne(f'{where} bir sözlük olmalı: {{"prompt": "..."}}.')
            continue
        pr = im.get('prompt')
        # K28
        if not isinstance(pr, str) or len(pr.strip()) < 40:
            r.ne(f'{where}.prompt boş ya da çok kısa (en az 40 karakter).')
            pr = pr if isinstance(pr, str) else ''
        elif len(pr) > 600:
            r.ne(f'{where}.prompt çok uzun ({len(pr)} karakter; en fazla 600).')
        if 'seed' in im and (not isinstance(im['seed'], int) or isinstance(im['seed'], bool)):
            r.ne(f'{where}.seed tam sayı olmalı.')
        fc = im.get('focus')
        if fc is not None and not (isinstance(fc, list) and len(fc) == 2 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in fc)):
            r.ne(f'{where}.focus 0-1 arası iki sayılık liste olmalı, ör. [0.5, 0.45].')
        # K37
        for ph in RE_PLACEHOLDER.findall(pr):
            if ph not in ('subject', 'setting') or not str(style.get(ph, '')).strip():
                r.ne(f'{where}.prompt bilinmeyen yer tutucu içeriyor: "{{{ph}}}".')
        full = expand_prompt(pr, style)
        # K29
        for rx in (IMG_BANNED_FAKE, IMG_BANNED_CONTENT, IMG_BANNED_IDENT):
            m = rx.search(pr)
            if m:
                r.ne(f'{where}.prompt yasak ifade içeriyor: "{m.group(0)}". Tarihî sahneleri renkli canlandırma olarak yazın; '
                     'çocuk, kan, yara, marka/logo/bayrak, gerçek kişi yazmayın.')
        # K30
        if re.search(r'[^\x00-\x7f]', pr):
            r.w(f'{where}.prompt İngilizce olmalı (ASCII dışı karakter var).')
        # K31
        if IMG_PEOPLE.search(full) and not IMG_ANON.search(full):
            r.w(f'sahne[{i}]: insan içeren prompt yüzü gizleyen bir kalıp içermiyor (seen from behind, in silhouette…).')
        # K32
        for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]{3,})\b", pr):
            if m.group(1) in names:
                r.w(f'{where}.prompt içinde özel isim olabilir: "{m.group(1)}". Gerçek kişi/hayvan adı yazmayın.')
        # K34
        if 'backdrop' not in sc:
            r.w(f'sahne[{i}]: görsel üretilemezse çizilecek yedek "backdrop" yok (plain_dark kullanılacak).')
        # K35
        if not im.get('actors'):
            for o in sc.get('overlays', []) or []:
                if o.get('type') == 'tag' and o.get('follow'):
                    r.ne(f'sahne[{i}]: tag.follow görselli sahnede çalışmaz (aktör çizilmiyor).')
    # K33
    desc = story.get('description', '') or ''
    if AI_DESC_LINE not in desc:
        r.ne(f'Yapay zekâ görselli videoda açıklamaya "{AI_DESC_LINE}" satırı zorunlu.')
    outros = [o for sc in scenes for o in sc.get('overlays', []) or [] if o.get('type') == 'outro']
    if outros and not any('yapay zekâ' in trlower(o.get('footer', '')) for o in outros):
        r.ne('Yapay zekâ görselli videoda outro.footer tam olarak '
             '"Bir Dakika! · Gerçek hikâye · Görseller yapay zekâ ile üretildi, temsilidir" olmalı.')


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
    r.legacy = slug in LEGACY_SLUGS
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
    try:
        check_format(r, story, scenes)
        check_images(r, story, scenes)
    except Exception as ex:  # doğrulayıcının kendi hatası günün videosunu durdurmasın
        r.w(f'Format kontrolleri tamamlanamadı ({type(ex).__name__}: {ex}).')
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
