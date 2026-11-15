#!/usr/bin/env python3
"""history.json yardımcı aracı.

  python scripts/history.py recent [-n 5]          # son N hikâyenin konu + tarz özeti
  python scripts/history.py topics                 # tüm işlenmiş konular (çakışma kontrolü için)
  python scripts/history.py add stories/<slug>/story.json --slot 12:00 \
        --animal "köpek" --topic "Kısa konu özeti" --structure "soğuk açılış → harita → veri → ters köşe" \
        [--source URL ...] [--date YYYY-MM-DD]

"add" komutu backdrop/aktör/overlay/fx/mood bilgilerini story.json'dan OTOMATİK çıkarır;
--source verilmezse açıklamadaki bağlantılar kaynak olarak alınır.
"""
import argparse, datetime, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, 'history.json')


def load():
    if not os.path.exists(HIST):
        return {'version': 1, 'entries': []}
    return json.load(open(HIST, encoding='utf-8'))


def save(h):
    with open(HIST, 'w', encoding='utf-8') as f:
        json.dump(h, f, ensure_ascii=False, indent=1)
        f.write('\n')


def style_of(story):
    bd, ac, ov, fx, moods = [], [], [], [], []
    for sc in story.get('scenes', []):
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
    return {'backdrops': bd, 'actors': ac, 'overlays': ov, 'fx': fx, 'moods': moods,
            'key': story.get('key', 'Dm'), 'voice': story.get('voice', 'fahrettin'), 'scenes': len(story.get('scenes', []))}


def cmd_recent(a):
    h = load()
    ents = h['entries'][-a.n:]
    if not ents:
        print('history.json boş.')
        return
    for e in reversed(ents):
        s = e.get('style', {})
        print(f"- {e.get('date')} [{e.get('slot')}] {e.get('slug')} | {e.get('animal', '?')} | {e.get('title')}")
        print(f"    konu     : {e.get('topic')}")
        print(f"    yapı     : {e.get('structure', '-')}")
        print(f"    backdrop : {', '.join(s.get('backdrops', []))}")
        print(f"    aktörler : {', '.join(map(str, s.get('actors', [])))}")
        print(f"    overlay  : {', '.join(s.get('overlays', []))}")
        print(f"    fx/ton/ses: {', '.join(s.get('fx', [])) or '-'} / {s.get('key')} / {s.get('voice')}")


def cmd_topics(a):
    for e in load()['entries']:
        print(f"- {e.get('slug')}: {e.get('animal', '?')} — {e.get('topic')}")


def cmd_add(a):
    story = json.load(open(a.story, encoding='utf-8'))
    h = load()
    slug = story['slug']
    if any(e.get('slug') == slug for e in h['entries']):
        sys.exit(f'HATA: "{slug}" zaten history.json içinde var. Farklı bir slug/konu seçin.')
    sources = a.source or re.findall(r'https?://\S+', story.get('description', ''))
    entry = {
        'slug': slug,
        'date': a.date or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime('%Y-%m-%d'),
        'slot': a.slot,
        'title': story.get('youtube_title', ''),
        'animal': a.animal,
        'topic': a.topic,
        'structure': a.structure,
        'sources': sources,
        'style': style_of(story),
        'status': 'hazırlandı',
    }
    h['entries'].append(entry)
    save(h)
    print(f'history.json güncellendi: {slug} ({len(sources)} kaynak)')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('recent')
    r.add_argument('-n', type=int, default=5)
    r.set_defaults(fn=cmd_recent)
    t = sub.add_parser('topics')
    t.set_defaults(fn=cmd_topics)
    d = sub.add_parser('add')
    d.add_argument('story')
    d.add_argument('--slot', default=os.environ.get('SLOT', 'manual'))
    d.add_argument('--animal', required=True)
    d.add_argument('--topic', required=True)
    d.add_argument('--structure', required=True)
    d.add_argument('--source', action='append')
    d.add_argument('--date')
    d.set_defaults(fn=cmd_add)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
