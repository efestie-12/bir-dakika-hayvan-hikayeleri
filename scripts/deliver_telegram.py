#!/usr/bin/env python3
"""Hazır videoyu + YouTube başlık/açıklama/etiketlerini Telegram botu ile gönderir.

  python scripts/deliver_telegram.py stories/<slug>/story.json out/<slug>.mp4 [--dry-run]

Ortam değişkenleri: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  (--dry-run için gerekmez)

- Telegram botları en fazla 50 MB dosya gönderebilir. Video bunu aşarsa ffmpeg ile
  (H.264, 1080x1920 korunarak) hedef boyutun altına küçültülür.
- Gönderim: 1) video (sendVideo, caption = başlık)  2) BAŞLIK  3) AÇIKLAMA  4) ETİKETLER
  Başlık/açıklama/etiketler kod bloğu olarak gönderilir: Telegram'da üzerine dokununca kopyalanır.
- Sadece Python standart kütüphanesi kullanılır (urllib).
"""
import argparse, html, json, mimetypes, os, subprocess, sys, time, urllib.error, urllib.request, uuid

API = 'https://api.telegram.org/bot{token}/{method}'
MB = 1024 * 1024
TG_LIMIT_MB = 49.0      # Telegram bot sınırı 50 MB; güvenlik payı
TARGET_MB = 45.0        # küçültme hedefi
MSG_LIMIT = 4096        # Telegram mesaj sınırı (karakter)
CHUNK = 3500            # HTML kaçışlarına ve başlıklara pay bırakarak bölme boyu


# ------------------------------------------------------------------ yardımcılar
def log(*a):
    print(*a, flush=True)


def probe(path):
    """(süre sn, genişlik, yükseklik) döndürür."""
    try:
        out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                              'stream=width,height:format=duration', '-of', 'json', path],
                             capture_output=True, text=True, check=True).stdout
        j = json.loads(out)
        st = (j.get('streams') or [{}])[0]
        return float(j['format']['duration']), int(st.get('width', 1080)), int(st.get('height', 1920))
    except Exception as ex:
        log(f'UYARI: ffprobe çalışmadı ({ex}); varsayılan değerler kullanılıyor.')
        return 60.0, 1080, 1920


def size_mb(p):
    return os.path.getsize(p) / MB


def ffmpeg(args):
    cmd = ['ffmpeg', '-y', '-loglevel', 'error'] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('ffmpeg hatası: ' + r.stderr.strip()[-600:])


def shrink(src, dst, target_mb=TARGET_MB, workdir=None):
    """Videoyu target_mb altına küçültür. Önce CRF artırarak, olmazsa 2 geçişli bitrate ile."""
    dur, _, _ = probe(src)
    vf = 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1'
    common = ['-vf', vf, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
              '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart']
    for crf in (28, 31, 34):
        log(f'  küçültme: CRF {crf} deneniyor...')
        ffmpeg(['-i', src] + common + ['-preset', 'medium', '-crf', str(crf), dst])
        log(f'    -> {size_mb(dst):.1f} MB')
        if size_mb(dst) <= target_mb:
            return dst
    # 2 geçişli hedef bitrate
    kbps = int((target_mb * 0.95 * MB * 8) / dur / 1000) - 128
    kbps = max(300, kbps)
    log(f'  küçültme: 2 geçişli hedef bitrate {kbps} kb/s...')
    wd = workdir or os.path.dirname(os.path.abspath(dst))
    plog = os.path.join(wd, f'ffpass-{uuid.uuid4().hex[:8]}')
    ffmpeg(['-i', src, '-vf', vf, '-c:v', 'libx264', '-preset', 'medium', '-b:v', f'{kbps}k',
            '-pass', '1', '-passlogfile', plog, '-an', '-f', 'mp4', os.devnull])
    ffmpeg(['-i', src] + common + ['-preset', 'medium', '-b:v', f'{kbps}k', '-maxrate', f'{int(kbps * 1.3)}k',
                                   '-bufsize', f'{kbps * 2}k', '-pass', '2', '-passlogfile', plog, dst])
    for f in os.listdir(wd):
        if f.startswith(os.path.basename(plog)):
            os.remove(os.path.join(wd, f))
    log(f'    -> {size_mb(dst):.1f} MB')
    if size_mb(dst) > TG_LIMIT_MB:
        raise RuntimeError(f'Video küçültülemedi: {size_mb(dst):.1f} MB > {TG_LIMIT_MB} MB')
    return dst


def split_text(text, n=CHUNK):
    """Metni satır sınırlarından n karakterlik parçalara böler."""
    parts, cur = [], ''
    for line in text.split('\n'):
        while len(line) > n:  # tek satır çok uzunsa zorla böl
            if cur:
                parts.append(cur)
                cur = ''
            parts.append(line[:n])
            line = line[n:]
        if len(cur) + len(line) + 1 > n:
            parts.append(cur)
            cur = line
        else:
            cur = line if not cur else cur + '\n' + line
    if cur or not parts:
        parts.append(cur)
    return parts


def build_messages(story):
    """Gönderilecek metin mesajlarını (HTML) döndürür."""
    title = story.get('youtube_title', '').strip()
    desc = story.get('description', '').strip()
    tags = story.get('tags', [])
    msgs = [f'<b>BAŞLIK:</b>\n<code>{html.escape(title, quote=False)}</code>']
    parts = split_text(desc)
    for i, p in enumerate(parts):
        head = 'AÇIKLAMA:' if len(parts) == 1 else f'AÇIKLAMA ({i + 1}/{len(parts)}):'
        msgs.append(f'<b>{head}</b>\n<pre>{html.escape(p, quote=False)}</pre>')
    tag_text = ', '.join(t.strip() for t in tags)
    for i, p in enumerate(split_text(tag_text)):
        msgs.append(f'<b>ETİKETLER:</b>\n<pre>{html.escape(p, quote=False)}</pre>')
    for m in msgs:
        assert len(m) <= MSG_LIMIT, 'mesaj sınırı aşıldı'
    return msgs


# ------------------------------------------------------------------ Telegram API
def _request(token, method, fields, files=None, timeout=300):
    url = API.format(token=token, method=method)
    if files:
        boundary = '----bd' + uuid.uuid4().hex
        body = bytearray()
        for k, v in fields.items():
            body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k, path in files.items():
            fn = os.path.basename(path)
            ct = mimetypes.guess_type(fn)[0] or 'application/octet-stream'
            body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'
                     f'Content-Type: {ct}\r\n\r\n').encode()
            with open(path, 'rb') as f:
                body += f.read()
            body += b'\r\n'
        body += f'--{boundary}--\r\n'.encode()
        req = urllib.request.Request(url, data=bytes(body), method='POST',
                                     headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    else:
        req = urllib.request.Request(url, data=json.dumps(fields).encode(), method='POST',
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def call(token, method, fields, files=None, tries=4):
    last = None
    for k in range(tries):
        try:
            res = _request(token, method, fields, files)
            if res.get('ok'):
                return res['result']
            last = res.get('description')
        except urllib.error.HTTPError as ex:
            try:
                res = json.loads(ex.read().decode())
            except Exception:
                res = {'description': str(ex)}
            last = res.get('description', str(ex))
            ra = (res.get('parameters') or {}).get('retry_after')
            if ex.code == 429 and ra:
                time.sleep(int(ra) + 1)
                continue
            if ex.code in (400, 401, 403, 404, 413):
                break  # tekrar denemek işe yaramaz
        except Exception as ex:  # ağ hatası, zaman aşımı
            last = str(ex)
        time.sleep(3 * (k + 1))
    # token'ı asla yazdırma
    raise RuntimeError(f'Telegram {method} başarısız: {last}')


# ------------------------------------------------------------------ ana akış
def main(argv=None):
    ap = argparse.ArgumentParser(description='Videoyu Telegram ile teslim et')
    ap.add_argument('story')
    ap.add_argument('video')
    ap.add_argument('--dry-run', action='store_true', help='ağ çağrısı yapmadan neyin gönderileceğini yazdır')
    ap.add_argument('--limit-mb', type=float, default=TG_LIMIT_MB, help='bu boyutu aşarsa küçült (varsayılan 49)')
    ap.add_argument('--target-mb', type=float, default=TARGET_MB, help='küçültme hedefi (varsayılan 45)')
    ap.add_argument('--note', default='', help='videonun altına eklenecek kısa not (ör. slot bilgisi)')
    a = ap.parse_args(argv)

    try:
        story = json.load(open(a.story, encoding='utf-8'))
    except Exception as ex:
        log(f'HATA: story.json okunamadı: {ex}')
        return 2
    if not os.path.isfile(a.video):
        log(f'HATA: video bulunamadı: {a.video}')
        return 2

    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not a.dry_run and (not token or not chat):
        log('HATA: TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID ortam değişkenleri tanımlı olmalı.')
        return 2

    video = a.video
    mb = size_mb(video)
    log(f'Video: {video} ({mb:.1f} MB)')
    if mb > a.limit_mb:
        dst = os.path.splitext(video)[0] + '.telegram.mp4'
        log(f'Video {a.limit_mb:.0f} MB sınırını aşıyor, küçültülüyor -> {dst}')
        try:
            shrink(video, dst, a.target_mb)
        except Exception as ex:
            log(f'HATA: {ex}')
            return 3
        video = dst
        if size_mb(video) > a.limit_mb:
            log(f'HATA: küçültülmüş video hâlâ {size_mb(video):.1f} MB.')
            return 3

    dur, w, h = probe(video)
    title = story.get('youtube_title', '').strip()
    caption = f'🎬 {title}'
    if a.note:
        caption += f'\n{a.note}'
    caption = caption[:1024]
    msgs = build_messages(story)

    if a.dry_run:
        log('\n--- DRY RUN: ağ çağrısı yapılmadı ---')
        log(f'1) sendVideo: {os.path.basename(video)} | {size_mb(video):.1f} MB | {w}x{h} | {dur:.1f} sn | supports_streaming')
        log(f'   caption: {caption!r}')
        for i, m in enumerate(msgs, 2):
            log(f'{i}) sendMessage (HTML, {len(m)} karakter):\n{m}\n')
        return 0

    log('Video gönderiliyor...')
    call(token, 'sendVideo', {'chat_id': chat, 'caption': caption, 'supports_streaming': 'true',
                              'width': str(w), 'height': str(h), 'duration': str(int(round(dur)))},
         files={'video': video})
    for m in msgs:
        call(token, 'sendMessage', {'chat_id': chat, 'text': m, 'parse_mode': 'HTML',
                                    'disable_web_page_preview': True})
    log(f'Tamam: video + {len(msgs)} mesaj gönderildi.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as ex:
        log(f'HATA: {ex}')
        sys.exit(1)
