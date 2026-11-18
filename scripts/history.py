#!/usr/bin/env python3
"""history.json ve metrics.json yardımcı aracı.

  python scripts/history.py recent [-n 6]          # son N hikâyenin özeti + SEÇİM KISITLARI
  python scripts/history.py topics                 # tüm işlenmiş konular (çakışma kontrolü için)
  python scripts/history.py add stories/<slug>/story.json --slot 12:00 \
        --topic "Kısa konu özeti" --structure "soğuk açılış → harita → veri → ters köşe" \
        [--subject "..."] [--source URL ...] [--date YYYY-MM-DD]
  python scripts/history.py metrics set <slug> --views 1100 --stayed 22.3 [--avd 33] [--apv 52] [--subs 1] [--likes N] [--day 7]
  python scripts/history.py metrics report

"add" komutu kategori, kanca kalıbı, özne, açılış cümleleri ve backdrop/aktör/overlay/fx/mood bilgilerini
story.json'dan OTOMATİK çıkarır; --source verilmezse açıklamadaki bağlantılar kaynak olarak alınır.
--animal eski adıdır (--subject ile aynı), artık zorunlu değildir.

metrics.json yalnız insan/asistan tarafından yazılır; bot (iş akışı) ona dokunmaz.
"""
import argparse, datetime, json, os, re, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, 'history.json')
METRICS = os.path.join(ROOT, 'metrics.json')

# Kategori -> 14 videodaki hedef pay
CATEGORIES = {'hayvan': 4, 'hayatta-kalma': 3, 'tarih': 3, 'bilim': 2, 'doga': 1, 'tuhaf-olay': 1}
HOOKS = ('yanlis-kahraman', 'imkansiz-olcu', 'ters-sonuc', 'gizli-kimlik', 'tek-karar', 'yanlis-bilinen',
         'gizem', 'kucuk-neden')
# Kategori/kanca alanları eklenmeden önce üretilmiş kayıtlar (eski kurallarla üretilen her kayıt hayvandır)
LEGACY = {'wojtek': {'category': 'hayvan', 'hook': 'gizli-kimlik'},
          'togo': {'category': 'hayvan', 'hook': 'yanlis-kahraman'},
          'godwit-rekor': {'category': 'hayvan', 'hook': 'imkansiz-olcu'}}
CAT_WINDOW, CAT_MAX, HOOK_WINDOW, TARGET_N = 6, 2, 3, 14


def normalize(e):
    """Eski kayıtlarda eksik alanları bellekte tamamlar (dosyaya yalnız bir sonraki 'add' ile yazılır)."""
    leg = LEGACY.get(e.get('slug'), {})
    if not e.get('category'):
        e['category'] = leg.get('category', 'hayvan')
    if not e.get('hook'):
        e['hook'] = leg.get('hook', 'bilinmiyor')
    if not e.get('subject'):
        e['subject'] = e.get('animal', '?')
    return e


def load():
    if not os.path.exists(HIST):
        return {'version': 1, 'entries': []}
    h = json.load(open(HIST, encoding='utf-8'))
    h.setdefault('entries', [])
    for e in h['entries']:
        normalize(e)
    return h


def save(h):
    with open(HIST, 'w', encoding='utf-8') as f:
        json.dump(h, f, ensure_ascii=False, indent=1)
        f.write('\n')


def _voice_of(story):
    """"karma" -> the Edge voice the engine will pick (ahmet/emel), so metrics can compare voices."""
    v = story.get('voice') or 'karma'
    if v != 'karma':
        return v
    try:
        sys.path.insert(0, ROOT)
        from engine.voice import pick_karma
        return pick_karma(story.get('slug', ''), HIST)
    except Exception:
        return v


def style_of(story, work=None):
    bd, ac, ov, fx, moods = [], [], [], [], []
    scenes = story.get('scenes', [])
    for sc in scenes:
        b = sc.get('backdrop', 'plain_dark')
        name = b if isinstance(b, str) else (b.get('preset') or ('map' if b.get('map') else 'custom'))
        if name not in bd:
            bd.append(name)
        for a in sc.get('actors', []) or []:
            if a.get('type') not in ac:
                ac.append(a.get('type'))
        for o in sc.get('overlays', []) or []:
            if o.get('type') not in ov:
                ov.append(o.get('type'))
        for f in sc.get('fx', []) or []:
            if f not in fx:
                fx.append(f)
        moods.append(sc.get('mood', 'calm'))
    st = {'backdrops': bd, 'actors': ac, 'overlays': ov, 'fx': fx, 'moods': moods,
          'key': story.get('key', 'Dm'), 'voice': _voice_of(story), 'scenes': len(scenes)}
    if scenes:
        b0 = scenes[0].get('backdrop', 'plain_dark')
        st['opening_backdrop'] = b0 if isinstance(b0, str) else (b0.get('preset') or 'custom')
        st['hook_overlay'] = [o.get('text', '') for o in scenes[0].get('overlays', []) or [] if o.get('type') == 'big']
    visual = story.get('visual', 'drawn')
    st['visual'] = visual
    st['images'] = sum(1 for sc in scenes if sc.get('image')) if visual == 'image' else 0
    if visual == 'image' and work:
        rp = os.path.join(work, 'images', 'report.json')
        if os.path.exists(rp):
            try:
                st['image_report'] = json.load(open(rp, encoding='utf-8')).get('counts', {})
            except (OSError, ValueError):
                pass
    return st


def _opening(e):
    bd = e.get('style', {}).get('opening_backdrop')
    if bd:
        return bd
    bds = e.get('style', {}).get('backdrops') or ['?']
    return bds[0]


def constraints(entries):
    """SEÇİM KISITLARI: yasak/önerilen kategoriler ve yasak kanca kalıpları."""
    last6 = [e['category'] for e in entries[-CAT_WINDOW:]][::-1]
    banned = {}
    if entries:
        banned[entries[-1]['category']] = ['bir önceki video']
    for c in set(last6):
        n = last6.count(c)
        if n >= CAT_MAX:
            banned.setdefault(c, []).append(f'son {CAT_WINDOW}\'da {n} kez')
    last14 = [e['category'] for e in entries[-TARGET_N:]]
    share = {c: (last14.count(c) / len(last14) if last14 else 0.0) for c in CATEGORIES}
    order = list(CATEGORIES)
    rec = sorted((c for c in CATEGORIES if c not in banned),
                 key=lambda c: (-(CATEGORIES[c] / TARGET_N - share[c]), -CATEGORIES[c], order.index(c)))
    hooks = []
    for e in entries[::-1]:
        if len(hooks) >= HOOK_WINDOW:
            break
        if e.get('hook') in HOOKS and e['hook'] not in hooks:
            hooks.append(e['hook'])
    return {'last6': last6, 'banned': banned, 'recommended': rec, 'banned_hooks': hooks,
            'openings': [_opening(e) for e in entries[-2:]][::-1]}


def cmd_recent(a):
    h = load()
    ents = h['entries'][-a.n:]
    if not ents:
        print('history.json boş.')
        return
    for e in reversed(ents):
        s = e.get('style', {})
        print(f"- {e.get('date')} [{e.get('slot')}] {e.get('slug')} | {e.get('subject', '?')} | {e.get('title')}")
        print(f"    kategori : {e.get('category')} | kanca: {e.get('hook')}")
        if e.get('hook_text'):
            print(f"    açılış   : {e['hook_text']}")
        print(f"    konu     : {e.get('topic')}")
        print(f"    yapı     : {e.get('structure', '-')}")
        print(f"    backdrop : {', '.join(s.get('backdrops', []))}")
        print(f"    aktörler : {', '.join(map(str, s.get('actors', [])))}")
        print(f"    overlay  : {', '.join(s.get('overlays', []))}")
        print(f"    fx/ton/ses: {', '.join(s.get('fx', [])) or '-'} / {s.get('key')} / {s.get('voice')}")
        if s.get('visual') == 'image':
            rep = s.get('image_report') or {}
            used = sum(v for k, v in rep.items() if k != 'drawn') if rep else s.get('images', 0)
            print(f"    görsel   : image ({used}/{s.get('images', 0)})")
    c = constraints(h['entries'])
    today = os.environ.get('TODAY') or datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=3))).strftime('%Y-%m-%d')
    same_day = [e for e in h['entries'] if e.get('date') == today]
    print('\n== SEÇİM KISITLARI (bu video için) ==')
    print(f"Son {CAT_WINDOW} kategori        : {', '.join(c['last6']) or '-'}")
    print('YASAK kategori        : ' + ('; '.join(f"{k} ({', '.join(v)})" for k, v in c['banned'].items()) or '-'))
    print(f"ÖNERİLEN kategori     : {', '.join(c['recommended'])}")
    print(f"YASAK kanca kalıpları : {', '.join(c['banned_hooks']) or '-'}")
    print(f"Son 2 açılış backdrop : {', '.join(c['openings']) or '-'}")
    if same_day:
        print('Bugünkü kayıt(lar)    : ' + '; '.join(f"{e.get('slug')} [{e.get('category')}] {e.get('subject')}"
                                                       for e in same_day)
              + ' → farklı kategori VE farklı kıta/dönem seç')


def cmd_topics(a):
    for e in load()['entries']:
        print(f"- {e.get('slug')}: [{e.get('category')}] {e.get('subject', '?')} — {e.get('topic')}")


def hook_text(story):
    sc = (story.get('scenes') or [{}])[0]
    return ' / '.join(f'"{ln.get("tts", "")}"' for ln in sc.get('lines', []))


def cmd_add(a):
    story = json.load(open(a.story, encoding='utf-8'))
    h = load()
    slug = story['slug']
    if any(e.get('slug') == slug for e in h['entries']):
        sys.exit(f'HATA: "{slug}" zaten history.json içinde var. Farklı bir slug/konu seçin.')
    sources = a.source or re.findall(r'https?://\S+', story.get('description', ''))
    category = story.get('category') or '?'
    if category == '?':
        print('UYARI: story.json içinde "category" yok; kayda "?" yazıldı.', file=sys.stderr)
    subject = a.subject or (a.animal if a.animal and a.animal != '?' else None) or story.get('subject') or a.animal or '?'
    work = os.path.join(ROOT, 'work', slug)
    entry = {
        'slug': slug,
        'date': a.date or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime('%Y-%m-%d'),
        'slot': a.slot,
        'title': story.get('youtube_title', ''),
        'category': category,
        'hook': story.get('hook') or 'bilinmiyor',
        'subject': subject,
        'hook_text': hook_text(story),
        'topic': a.topic,
        'structure': a.structure,
        'sources': sources,
        'style': style_of(story, work),
        'status': 'hazırlandı',
    }
    h['entries'].append(entry)
    save(h)
    print(f'history.json güncellendi: {slug} [{category}/{entry["hook"]}] ({len(sources)} kaynak)')


# ------------------------------------------------------------------ metrics.json
def load_metrics():
    if not os.path.exists(METRICS):
        return {'version': 1, 'videos': {}}
    return json.load(open(METRICS, encoding='utf-8'))


def save_metrics(m):
    with open(METRICS, 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
        f.write('\n')


def cmd_metrics_set(a):
    m = load_metrics()
    hist = {e['slug']: e for e in load()['entries']}
    v = m['videos'].setdefault(a.slug, {'published': (hist.get(a.slug) or {}).get('date'), 'reads': []})
    if a.published:
        v['published'] = a.published
    read = {'day': a.day, 'views': a.views, 'stayed': a.stayed, 'avd': a.avd, 'apv': a.apv, 'subs': a.subs}
    if a.likes is not None:
        read['likes'] = a.likes
    if a.day is not None:  # aynı günün okuması varsa yenisiyle değiştir
        v['reads'] = [r for r in v['reads'] if r.get('day') != a.day]
    v['reads'].append(read)
    save_metrics(m)
    print(f'metrics.json güncellendi: {a.slug} ({len(v["reads"])} okuma)')


def _med(xs):
    xs = [x for x in xs if x is not None]
    return f'{statistics.median(xs):.1f}' if xs else '-'


def cmd_metrics_report(a):
    m = load_metrics()
    hist = {e['slug']: e for e in load()['entries']}
    rows = []
    for slug, v in m.get('videos', {}).items():
        if not v.get('reads'):
            continue
        r = v['reads'][-1]
        e = hist.get(slug, {})
        st = e.get('style', {})
        views, subs = r.get('views'), r.get('subs')
        rows.append({'slug': slug, 'date': v.get('published') or e.get('date'), 'slot': e.get('slot', '?'),
                     'category': e.get('category', '?'), 'hook': e.get('hook', '?'),
                     'visual': st.get('visual', 'drawn'), 'voice': st.get('voice', '?'),
                     'views': views, 'stayed': r.get('stayed'), 'avd': r.get('avd'), 'apv': r.get('apv'),
                     'subs': subs, 'spk': (subs * 1000 / views) if views and subs is not None else None,
                     'day': r.get('day')})
    if not rows:
        print('metrics.json boş. Örnek: python scripts/history.py metrics set togo --views 1100 --stayed 22.3')
        return
    f = lambda x, p='': '-' if x is None else (f'{x:.1f}{p}' if isinstance(x, float) else f'{x}{p}')
    print(f"{'slug':<22}{'tarih':<12}{'slot':<8}{'kategori':<15}{'kanca':<17}{'görsel':<8}{'ses':<10}"
          f"{'görünt.':>8}{'kaldı%':>8}{'ort.sn':>8}{'ort.%':>7}{'abone':>6}{'ab/1k':>7}")
    for r in rows:
        print(f"{r['slug']:<22}{str(r['date']):<12}{r['slot']:<8}{r['category']:<15}{r['hook']:<17}{r['visual']:<8}"
              f"{r['voice']:<10}{f(r['views']):>8}{f(r['stayed']):>8}{f(r['avd']):>8}{f(r['apv']):>7}"
              f"{f(r['subs']):>6}{f(r['spk']):>7}")
    for key, name in (('hook', 'kanca kalıbı'), ('category', 'kategori'), ('visual', 'görsel kipi')):
        print(f'\n-- {name} bazında (ortanca) --')
        groups = {}
        for r in rows:
            groups.setdefault(r[key], []).append(r)
        for g, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            print(f"{g:<18} n={len(rs):<3} kaldı% {_med([r['stayed'] for r in rs]):>6}   "
                  f"abone/1000 {_med([r['spk'] for r in rs]):>6}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('recent')
    r.add_argument('-n', type=int, default=6)
    r.set_defaults(fn=cmd_recent)
    t = sub.add_parser('topics')
    t.set_defaults(fn=cmd_topics)
    d = sub.add_parser('add')
    d.add_argument('story')
    d.add_argument('--slot', default=os.environ.get('SLOT', 'manual'))
    d.add_argument('--subject', help='kısa özne (story.json "subject" alanını ezer)')
    d.add_argument('--animal', help='eski ad; --subject ile aynı (isteğe bağlı)')
    d.add_argument('--topic', required=True)
    d.add_argument('--structure', required=True)
    d.add_argument('--source', action='append')
    d.add_argument('--date')
    d.set_defaults(fn=cmd_add)
    m = sub.add_parser('metrics')
    msub = m.add_subparsers(dest='mcmd', required=True)
    ms = msub.add_parser('set')
    ms.add_argument('slug')
    ms.add_argument('--views', type=int, required=True)
    ms.add_argument('--stayed', type=float, required=True, help='"izlemeye devam edenler" yüzdesi')
    ms.add_argument('--avd', type=float, help='ortalama izlenme süresi (sn)')
    ms.add_argument('--apv', type=float, help='ortalama izlenme yüzdesi')
    ms.add_argument('--subs', type=int, help='bu videodan gelen abone')
    ms.add_argument('--likes', type=int)
    ms.add_argument('--day', type=int, help='yayından kaç gün sonra okundu')
    ms.add_argument('--published', help='yayın tarihi YYYY-AA-GG')
    ms.set_defaults(fn=cmd_metrics_set)
    mr = msub.add_parser('report')
    mr.set_defaults(fn=cmd_metrics_report)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
