# Bir Dakika! — gerçek hayvan hikâyeleri (otomatik Shorts üretimi)

Her gün 2 kez (12:00 ve 19:00, İstanbul) GitHub Actions üzerinde:

1. **Claude** (`CLAUDE.md` talimatlarıyla) yeni bir gerçek hayvan hikâyesi seçer, en az 2 kaynakla doğrular ve
   `stories/<slug>/story.json` storyboard'unu yazar, `history.json`'a kaydeder.
2. `scripts/validate_story.py` storyboard'u denetler.
3. `engine/` 1080x1920, ~60 sn'lik videoyu üretir (Piper Türkçe ses, prosedürel çizim, sentez müzik).
4. `scripts/deliver_telegram.py` videoyu + başlık/açıklama/etiketleri Telegram'a gönderir.
5. Yeni hikâye ve geçmiş depoya commit edilir.

YouTube'a yükleme elle yapılır (bkz. **SETUP.md**).

## Klasörler
| yol | içerik |
|---|---|
| `engine/` | video motoru (`python -m engine.build stories/<slug>/story.json --out out/<slug>.mp4`, hızlı kareler: `--stills 1.5,4.0`) |
| `stories/` | storyboard'lar (örnek: `stories/togo/story.json`) |
| `scripts/` | `validate_story.py`, `history.py`, `deliver_telegram.py`, `fetch_voice.sh` |
| `assets/fonts/` | Inter (SIL OFL 1.1) ve DejaVu Serif (Bitstream Vera lisansı) fontları — lisanslar klasörde |
| `docs/catalog/` | backdrop ve aktör katalog görselleri |
| `history.json` | yapılan hikâyeler (konu tekrarını ve tarz tekrarını önlemek için) |
| `pronunciations.json` | Türkçe TTS telaffuz düzeltmeleri |
| `.github/workflows/daily.yml` | zamanlanmış iş akışı |

## Yerelde çalıştırma
```bash
sudo apt-get install ffmpeg
pip install -r requirements.txt
bash scripts/fetch_voice.sh fahrettin          # ~/tts altına ses modeli
python scripts/validate_story.py stories/togo/story.json
python -m engine.build stories/togo/story.json --stills 1.5,4.0   # work/togo/stills/*.png
python -m engine.build stories/togo/story.json --out out/togo.mp4  # tam render (~5-10 dk)
python scripts/deliver_telegram.py stories/togo/story.json out/togo.mp4 --dry-run
```

## GitHub Actions dakikaları
- Depo **public** ise standart runner dakikaları **ücretsiz ve sınırsızdır** (varsayılan kurulum budur).
- Depo **private** olursa ücretsiz plan **2000 dk/ay** ile sınırlıdır. Bir çalıştırma ≈ 20-25 dk
  (kurulum ~3, Claude ~8-12, render ~8-10, teslim ~1) → günde 2 video × ~25 dk × 30 gün ≈ **1500 dk/ay**.
  Sınırın altında kalır ama pay azdır; uzun/başarısız tekrar çalıştırmalar sınırı aşabilir.
- Claude adımı Claude Pro aboneliğinin kullanım kotasını kullanır (ek ücret yok).
