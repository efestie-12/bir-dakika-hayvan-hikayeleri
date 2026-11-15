# CLAUDE.md — "Bir Dakika!" günlük hikâye ajanı

Bu depo, YouTube kanalı **"Bir Dakika!"** için gerçek ve doğrulanmış hayvan hikâyelerinden
dikey Shorts videoları (1080x1920, ~60 sn, Türkçe seslendirme) üretir. GitHub Actions günde 2 kez
(12:00 ve 19:00, İstanbul) seni çalıştırır. Senin işin **storyboard hazırlamak**; render, Telegram
teslimi ve git commit/push iş akışının sonraki adımlarında otomatik yapılır.

## 0. Kesin kurallar

- Bu çalıştırmada **TEK** yeni hikâye hazırla: `stories/<slug>/story.json`.
- **Tam render YAPMA** (`--stills` dışında `engine.build` çalıştırma). **git commit / push YAPMA.**
- `engine/`, `scripts/`, `.github/`, `assets/` dosyalarını **değiştirme**. Yalnızca şunlara yazabilirsin:
  `stories/<yeni-slug>/story.json`, `history.json` (yalnızca `scripts/history.py add` ile), `pronunciations.json` (yeni telaffuz ekleme).
- Gizli anahtar/token yazdırma veya dosyaya koyma.
- Kullanıcıya soru sorma; makul karar ver ve devam et.
- Ortam değişkenleri: `SLOT` (12:00 / 19:00 / manual), `TODAY` (YYYY-AA-GG).

## 1. İş akışı (sırayla)

1. **Geçmişi oku**
   `python scripts/history.py topics` (tüm konular) ve `python scripts/history.py recent -n 5` (son 5 tarz).
2. **Konu seç** (bkz. §2). İşlenmiş bir hayvan/olayla çakışmamalı. Aynı gün iki slot aynı hikâyeyi seçemez —
   history.json'da bugünün tarihli kaydı varsa onun hayvan türünden ve temasından da uzak dur.
3. **Araştır ve doğrula** (bkz. §3): WebSearch + WebFetch ile **en az 2 bağımsız güvenilir kaynak**.
4. **Senaryoyu yaz** (bkz. §4-§5): 6-10 sahne, 55-65 sn, Türkçe.
5. **`stories/<slug>/story.json` yaz.** slug: küçük harf, rakam, tire; Türkçe karakter yok (ör. `hachiko`, `laika-uzay`).
   Yabancı isimler Türkçe sesle yanlış okunuyorsa story içinde `"pron": {"Seppala": "Seppala"}` ekle veya
   kalıcı olanları `pronunciations.json`'a ekle (anahtar: metindeki yazım, değer: Türkçe okunuşu).
6. **Doğrula:** `python scripts/validate_story.py stories/<slug>/story.json` → HATA varsa düzelt, tekrar çalıştır.
   UYARIları da mümkünse gider (özellikle süre, metin taşması, tts içinde rakam).
7. **Kareleri üret ve GÖR:**
   `python -m engine.build stories/<slug>/story.json --stills 1.5,4.0`
   Kareler `work/<slug>/stills/NN_<sahne>_<t>.png`. Her kareyi **Read ile aç ve bak**. Kontrol listesi:
   - Metin ekrandan taşıyor mu? Overlay'ler üst üste biniyor mu? Altyazı bandıyla (y≈1150-1790) çakışıyor mu?
   - Aktörler zeminin üstünde mi (havada/gömülü değil mi), ekran dışında mı kaldı?
   - Kontrast yeterli mi (koyu siluet koyu zeminde kaybolmuyor mu → `rim` ekle)?
   - Sahneler birbirinin kopyası gibi mi görünüyor?
   Sorun varsa story.json'u düzelt ve stills'i yeniden üret. (Seslendirme süresi de çıktıda `total` olarak yazar:
   **50-68 sn** aralığında değilse metni kısalt/uzat.)
8. **Kaydet:**
   ```
   python scripts/history.py add stories/<slug>/story.json --slot "$SLOT" \
     --animal "<hayvan türü>" --topic "<1-2 cümle konu özeti>" \
     --structure "<anlatım yapısı, ör. soğuk açılış → harita → sayaç → ters köşe>" \
     --source <url1> --source <url2>
   ```
   (backdrop/aktör/overlay/fx/mood bilgileri otomatik çıkarılır.)
9. Kısa bir özetle bitir (seçilen konu, kaynaklar, tahmini süre). Başka bir şey yapma.

## 2. Konu seçimi

- **Gerçek, belgelenmiş, doğrulanabilir** hayvan hikâyeleri: kahraman hayvanlar, savaş/keşif hayvanları,
  bilimsel rekorlar, olağanüstü göçler, sadakat hikâyeleri, kurtarma olayları, tarihe geçen tuhaf olaylar,
  bilim insanlarını şaşırtan davranışlar. Dünyanın her yerinden; Türkiye'den hikâyeler de olabilir.
- Dikkat çekici bir **kanca** ve **ters köşe/sürpriz** barındırmalı.
- Çeşitlilik: hayvan türünü, kıtayı, dönemi ve duyguyu (gerilim, hüzün, merak, mizah, hayranlık) son
  hikâyelerden farklı seç. Art arda iki köpek/savaş hikâyesi olmasın.
- Kaçın: doğrulanamayan viral hikâyeler, sahte/şüpheli "internet efsaneleri", hayvana zulmü ayrıntılı anlatan
  ya da şiddeti çekici gösteren içerikler, yaşayan kişiler hakkında olumsuz iddialar, tıbbi tavsiye.

## 3. Doğrulama kuralları

- Her ana iddia (tarih, yer, sayı, isim, sonuç) için **en az 2 bağımsız** kaynak (ör. ansiklopedi + müze/üniversite/
  resmi kurum/ulusal basın). Aynı metni kopyalayan siteler bağımsız sayılmaz.
- Tarih, sayı ve isimleri kaynaklarla **karşılaştır**; çelişki varsa ya en ihtiyatlı değeri kullan
  ("yaklaşık", "400 km'den fazla") ya da o ayrıntıyı **hiç kullanma**.
- Belirsiz/tartışmalı iddiayı videoya **KOYMA**. Efsane kısmı varsa "anlatılana göre" gibi ölçülü ifade kullan.
- Sayılar yuvarlanabilir ama abartılamaz. Uydurma diyalog, uydurma isim, uydurma sayı yok.
- Kullandığın kaynak URL'lerini açıklamadaki "Kaynaklar:" listesine ve `history.py add --source` ile kayda ekle.

## 4. Çeşitlilik (YouTube "inauthentic / mass-produced content" politikasına karşı)

Her video **gözle görülür biçimde farklı** olmalı. `python scripts/history.py recent -n 5` çıktısına bak ve:

- **Backdrop:** son 2 videonun açılış sahnesi backdrop'unu kullanma; videoda en az 4 farklı backdrop olsun ve
  en az 2 sahnede preset'i dict ile özelleştir (renk, sky, glow, far/mid/ground değiştir).
- **Aktörler:** son videodaki ana aktör kombinasyonunu tekrarlama (ör. husky+musher+team bir daha olmasın).
- **Overlay tarzı:** her videoda 1-2 "imza" veri görseli seç ve son 2 videoda imza olanı tekrar etme:
  bar grafik (`bars`), harita rotası (`route` + `map_dark`), gazete manşetleri (`newspapers`), sayaç (`counter`),
  dev rakam/metin (`big`), etiket+halka (`tag`), çatlak efekti (`cracks`).
- **Anlatım yapısı:** dönüşümlü kullan — soğuk açılış/ters köşe, kronolojik yolculuk, "ya şöyle olsaydı" sorusu,
  sayılarla geri sayım, karşılaştırma (iki hayvan/iki dönem), gizem → çözüm.
- **Müzik tonu** (`key`) ve mood dizisini değiştir; uygun düştüğünde farklı ses (`voice`) dene
  (`fahrettin` varsayılan; `dfki`, `fettah` de kurulu).
- Kamera hareketlerini (zoom in/out, pan yönü) sahneden sahneye değiştir.

## 5. Anlatım ve süre

- Toplam **~55-65 sn** (validate tahmini 45-75 dışındaysa uyarır). Yaklaşık 850-1000 karakter seslendirme.
- **İlk 2 sn kanca:** ilk satır kısa ve merak uyandırıcı ("Bu kedi bir geminin kaptanından daha çok sefere çıktı.").
  İlk sahnede `punch` + `flash` + `impact` sfx ile vurgu.
- **Orta: tırmanış** — tehlike/engel/merak artar (mood: build → tension → drive).
- **Son: sürpriz / ters köşe** — izleyicinin beklemediği gerçek.
- **Kapanış:** son sahnede `title` (hayvanın adı + yıllar) ve `outro` overlay; tek cümlelik duygusal kapanış.
  `outro`'nun varsayılan metni zaten kanal kimliğidir (CTA: "Her gün gerçek bir hayvan hikâyesi için TAKİP ET",
  footer: "Bir Dakika! · Gerçek hikâye · Görseller temsilidir"); `cta`/`footer` vermezsen bunlar kullanılır.
- Dil: sade, akıcı Türkçe; kısa cümleler. Ölçülü ifade; "en", "ilk", "tek" iddialarını yalnızca kaynak açıkça
  söylüyorsa kullan.
- `tts`: seslendirilecek metin. **Sayıları yazıyla** yaz ("bin dokuz yüz yirmi beş"), kısaltma kullanma ("km" değil
  "kilometre"). Uzun duraklama için `...` kullan (0,5 sn). Her satır noktalama ile bitsin.
- `cap`: ekrandaki altyazı (rakam kullanılabilir). Vurgulanacak kelimelerin başına `*` koy (altın renk).
  Bir satır en fazla ~90 karakter; uzunsa iki satıra böl. `style: "big"` = büyük, tamamı altın renk vurgulu satır.

## 6. Başlık, açıklama, etiketler

- **`youtube_title`**: Türkçe, **≤70 karakter**, merak uyandıran ama clickbait olmayan, **tam 1 emoji**,
  doğru olmayan hiçbir iddia yok, tamamı büyük harf değil. Örnek: `Herkes Balto'yu biliyor… ama asıl kahraman o değildi 🐕`
- **`description`** (bu sırayla):
  1. 1-3 cümle özet (spoiler vermeden merak uyandır).
  2. Boş satır, sonra tam olarak: `Görseller temsilidir, anlatılan olay gerçektir.`
  3. Boş satır, `Kaynaklar:` ve altında `- https://...` satırları (en az 2).
  4. Boş satır, `#shorts` + 3-5 konu hashtag'i (ör. `#shorts #kedi #gerçekhikaye #tarih`).
- **`tags`**: 8-15 etiket; hayvanın adı, türü, olay, yer, "gerçek hikaye", "hayvan hikayeleri", "Bir Dakika", "shorts".

## 7. Storyboard şeması

Çalışan tam örnek: **`stories/togo/story.json`** (9 sahne) — yazmadan önce oku.
Görsel katalog: `docs/catalog/backdrops.png` (12 preset, aşağıdaki sırayla soldan sağa),
`docs/catalog/actors.png` (örnek aktörler). Gerekirse Read ile bak.

```jsonc
{
  "slug": "ornek-slug",              // klasör adıyla aynı
  "voice": "fahrettin",              // fahrettin | dfki | fettah
  "key": "Dm",                       // müzik tonu: Am Bm Cm Dm Em Fm Gm
  "youtube_title": "...", "description": "...", "tags": ["..."],
  "pron": {"Yabancıİsim": "Okunuşu"},  // opsiyonel
  "scenes": [ {
    "id": "acilis",                  // benzersiz
    "mood": "wonder",                // calm | wonder | build | tension | drive | warm | resolve | data
    "wind": 0.6,                     // 0-1 rüzgâr sesi (opsiyonel)
    "backdrop": "night_city",        // preset adı VEYA {"preset": "...", ...üzerine yazılacak anahtarlar}
    "aurora": 1.0,                   // kutup ışığı gücü (opsiyonel, 0.4-1.2)
    "fx": ["snow"],                  // parçacık efektleri
    "camera": {"zoom": [1.0, 1.1], "pan": [-30, 30], "pany": [20, -20]},  // sahne boyunca baş→son
    "actors": [ {...} ],
    "overlays": [ {...} ],
    "punch": [{"at": "line:1", "amount": 0.08}],   // ani zoom vurgusu
    "shake": [{"at": "line:2:0.45", "dur": 0.6, "amp": 18}],
    "flash": [{"at": "line:1", "dur": 0.12}],
    "sfx":   [{"type": "impact", "at": "line:1", "gain": 0.8}],
    "lines": [ {"tts": "Seslendirilecek metin.", "cap": "Ekrandaki *altyazı*", "style": "cap"} ]
  } ]
}
```

**Zaman ifadeleri (`at`, `until`, `dur_to`, `fade_at`):** sahne başından saniye (`1.5`), `"line:N"` (N. satırın
başı, 0'dan), `"line:N:0.7"` (N. satırın %70'i), `"end:-1.5"` (sahne bitiminden 1,5 sn önce).
Sahne süresi seslendirmeden otomatik hesaplanır.

**Koordinatlar:** çerçeve 1080x1920 (x sağa, y aşağı). Zemin çizgisi çoğu preset'te y≈1200-1260.
Altyazı bandı y≈1150-1790 (merkez 1470) → overlay'leri y 200-1100 arasına koy. Outro y 1680/1790'da çizilir.

### Backdrop preset'leri (`engine/backdrops.py` → PRESETS)
| preset | görünüm |
|---|---|
| `night_city` | gece, yıldızlar, ışıklı şehir silueti, çıplak ağaçlar |
| `snow_village` | karlı köy evleri, çam ağaçları, beyaz zemin |
| `ice_night` | yıldızlı kutup gecesi, çam ormanı, buz kütleli zemin, aurora açık |
| `desert_sunset` | çöl gün batımı, büyük güneş, kumul sırtları |
| `savanna_sunset` | savan gün batımı, akasya ağaçları |
| `ocean_dusk` | alacakaranlıkta deniz ufku, su yansımaları |
| `forest_dawn` | şafakta iki katmanlı çam ormanı |
| `mountain_dawn` | şafakta dağ sırtları |
| `station_dusk` | alacakaranlıkta pencere ışıksız şehir/istasyon silueti, düz zemin |
| `map_dark` | koyu harita (ızgara, kara parçası, nehir) — `route` overlay için |
| `plain_dark` | düz koyu mavi arka plan — veri/grafik sahneleri |
| `plain_warm` | düz sıcak kahverengi arka plan — gazete/kapanış sahneleri |

Dict ile özelleştirme anahtarları: `sky` [[y,"#hex"],...], `glow` [x,y,r,"#hex",güç,basıklık], `stars` (adet),
`moon` [x,y,r], `sun` [x,y,r,"#hex"],
`far` {type: city|ridge|spruce|none, color, y, amp, f1, win, hmin, hmax, h0, h1, step},
`mid` {type: bare_trees|spruce|houses|acacia|rocks|none, color, y, xs, h, h0, h1, step, snow},
`ground` {type: ridge|flat|water|ice|none, color, color2, y, amp}, `fg` {color, y} (ön plan şeridi),
`map` {land:[[x,y],...], river:[[x,y],...], coast_from, land_color} (kendi haritanı çizmek için; kıyı şeklini
hikâyenin coğrafyasına kabaca benzet).

### Aktör türleri (`engine/actors.py` → TYPES)
Ortak anahtarlar: `type`, `x`, `y` (ayak noktası, zorunlu), `h` (yükseklik px), `d` (1 sağa, -1 sola bakar),
`color` (gövde), `rim` (kenar ışığı rengi — koyu zeminde mutlaka kullan), `motion` (idle|gallop|walk|fly),
`speed` (px/sn, + sağa), `at` (görünme zamanı), `factor` (paralaks, varsayılan 0.6).

| tür | açıklama ve ek anahtarlar |
|---|---|
| `husky` | kızak köpeği / genel köpek (gallop animasyonu) |
| `cat` | kedi; `pose`: sit (varsayılan) — motion verilirse yürür |
| `horse` | at; `head_down` |
| `bird` | kuş (fly = kanat çırpma) |
| `elephant` | fil (walk) |
| `bear` | ayı; `pose`: stand, sit, walk, carry, attention, grapple, shell; `cap`, `lift` |
| `person` | insan; `hat`: none, hat, cap, hood; `arm`: down, wave, point, hold, pocket; `coat` |
| `soldier` | asker; `pose`: down, salute, hold, reach, shoulder, wave; `hat`: helmet, cap; `rifle` |
| `team` | köpek kızağı ekibi; `n`, `gap`, `sled_w` |
| `musher` | kızak sürücüsü; `lean` |
| `rock` | kaya/kaide; `w` genişlik |
| `lamp` | sokak lambası |

Bu listede olmayan bir hayvan gerekiyorsa en yakın siluet + `tag` etiketi + anlatımla çöz
(ör. kurt → `husky`, köpek türleri → `husky`, büyükbaş → `horse`/`elephant` değil; uygun değilse aktörsüz
veri sahnesi kullan). Motoru değiştirme.

### Overlay türleri (`engine/overlays.py` → BUILDERS)
| tür | ne yapar | anahtarlar |
|---|---|---|
| `chip` | sol üstte yer/tarih rozeti | `text`, `y`(250), `dot` renk, `at` |
| `counter` | sayan büyük rakam | `to`, `unit`, `label`, `y`, `size`(150), `color`, `dur`, `at` |
| `big` | zıplayarak gelen büyük metin | `text`, `sub`, `x`, `y`, `size`(120), `color`, `stroke`, `spacing`, `at`, `until` |
| `tag` | etiket (+opsiyonel halka) | `text`, `sub`, `x`, `y`, `size`, `color`, `ring` [x,y,r], `follow` {actor, x, y, r}, `at` |
| `bars` | yatay bar grafik | `title`, `unit`, `max`, `y0`(640), `gap`(320), `icon` (husky/cat/horse/elephant/bird), `items` [{name, value, color, at}] |
| `route` | haritada ilerleyen rota | `points` [[x,y,"AD"?],...], `total` (km sayacı), `at`, `dur` veya `dur_to`, `labels` [{text,x,y,size}] |
| `newspapers` | uçarak gelen gazete manşetleri | `items` [{headline ("\n" ile 2 satır), sub}], `masthead`, `date`, `step`, `fade_at`, `dim` |
| `title` | kapanış başlığı | `text`, `sub`, `y`, `size`(170), `color`, `spacing`, `at` |
| `outro` | takip çağrısı + footer + sona karartma | `cta`, `footer` (verilmezse kanal varsayılanı), `at` |
| `cracks` | buz/cam çatlağı efekti | `x`, `y`, `n`, `length`, `seed`, `dur`, `water` {width}, `at` |

Renkler: `gold`, `ice`, `white`, `red`, `grey`, `mint`, `cream` veya `"#rrggbb"`.
Gazete manşetleri dönemin dilinde (çoğunlukla İngilizce) olabilir ama **gerçek manşet gibi sunma**; temsili olduğu
açık olsun ve uydurma alıntı yapma (genel ifadeler kullan).

### Efektler, müzik ve sesler
- `fx` (`engine/fx.py` → KINDS): `snow`, `blizzard`, `embers`, `motes`, `rain`, `dust`
- `mood` (`engine/music.py` → MOODS): `calm`, `wonder`, `build` (sonda riser), `tension`, `drive`, `warm`, `resolve`, `data`
- `sfx` (`engine/music.py` → SFX_TYPES): `impact` (`gain`), `riser` (`length`; `at` = riser'in BİTTİĞİ an),
  `crack`, `whoosh`, `swish`, `tom`
- Sahne geçişlerinde whoosh otomatik eklenir.

## 8. history.json şeması

```jsonc
{ "version": 1, "entries": [ {
  "slug": "togo", "date": "2026-11-15", "slot": "12:00 | 19:00 | manual",
  "title": "YouTube başlığı", "animal": "köpek (Sibirya kurdu)",
  "topic": "1-2 cümle konu özeti", "structure": "anlatım yapısı",
  "sources": ["https://...", "https://..."],
  "style": { "backdrops": [...], "actors": [...], "overlays": [...], "fx": [...], "moods": [...],
             "key": "Dm", "voice": "fahrettin", "scenes": 9 },
  "status": "hazırlandı"
} ] }
```
Kayıt yalnızca `python scripts/history.py add ...` ile eklenir; elle düzenleme yapma.
