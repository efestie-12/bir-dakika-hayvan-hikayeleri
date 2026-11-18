# CLAUDE.md — "Bir Dakika!" günlük hikâye ajanı

Bu depo, YouTube kanalı **"Bir Dakika!"** için **inanılmaz ama gerçek** hikâyelerden (hayvan, insan, tarih,
bilim, doğa) dikey Shorts videoları (1080x1920, ~60 sn, Türkçe seslendirme) üretir. GitHub Actions günde 2 kez
(12:00 ve 19:00, İstanbul) seni çalıştırır. Senin işin **storyboard hazırlamak**; render, Telegram teslimi ve
git commit/push sonraki adımlarda otomatik yapılır.

> İş akışı istemi ya da başka bir dosya "hayvan hikâyesi" diyorsa o ifade eskidir. **Bu dosya geçerlidir:**
> konu yalnız hayvan değildir, kategoriyi §2'deki kurallar belirler.

## 0. Kesin kurallar

- Bu çalıştırmada **TEK** yeni hikâye hazırla: `stories/<slug>/story.json`.
- **Tam render YAPMA** (`--stills` dışında `engine.build` çalıştırma). **git commit / push YAPMA.**
- `engine/`, `scripts/`, `.github/`, `assets/` dosyalarını **değiştirme**. Yalnızca şunlara yazabilirsin:
  `stories/<yeni-slug>/story.json`, `history.json` (yalnızca `scripts/history.py add` ile), `pronunciations.json` (yeni telaffuz ekleme).
  `metrics.json` dosyasına dokunma (onu yalnız kullanıcı/asistan günceller).
- Gizli anahtar/token yazdırma veya dosyaya koyma.
- §2.1'deki yasak konuları seçme. Emin değilsen o konuyu bırak, başka aday seç.
- Kullanıcıya soru sorma; makul karar ver ve devam et.
- Ortam değişkenleri: `SLOT` (12:00 / 19:00 / manual), `TODAY` (YYYY-AA-GG), `VISUAL_MODE` (image / drawn; bkz. §11).

## 1. İş akışı (sırayla)

1. **Geçmişi oku**
   `python scripts/history.py topics` ve `python scripts/history.py recent -n 6`.
   Çıktının sonundaki **SEÇİM KISITLARI** bloğunu uygula: YASAK kategoriyi ve YASAK kanca kalıplarını kullanma,
   ÖNERİLEN kategorilerden birini seç.
2. **Konu seç** (bkz. §2): en az 3 aday bul, ele, birini seç. İşlenmiş bir konuyla çakışmamalı. Aynı gün
   history.json'da kayıt varsa onun kategorisinden, kıtasından ve döneminden uzak dur.
3. **Araştır ve doğrula** (bkz. §3): en az 2 farklı alan adından kaynak + zorunlu çürütme araması.
4. **Senaryoyu yaz** (bkz. §4-§7): 6-10 sahne, 55-65 sn, Türkçe. İlk sahne §5'teki kanca kurallarına uyar.
5. **`stories/<slug>/story.json` yaz.** slug: küçük harf, rakam, tire; Türkçe karakter yok (ör. `poon-lim`, `emu-savasi`).
   Yabancı isimler Türkçe sesle yanlış okunuyorsa story içinde `"pron": {"Seppala": "Seppala"}` ekle veya
   kalıcı olanları `pronunciations.json`'a ekle (anahtar: metindeki yazım, değer: Türkçe okunuşu).
6. **Doğrula:** `python scripts/validate_story.py stories/<slug>/story.json` → HATA varsa düzelt, tekrar çalıştır.
   UYARIları da mümkünse gider (özellikle kanca, süre, metin taşması, tts içinde rakam).
7. **Kareleri üret ve GÖR:**
   `python -m engine.build stories/<slug>/story.json --stills 0.3,1.5,4.0`
   Kareler `work/<slug>/stills/NN_<sahne>_<t>.png`. Her kareyi **Read ile aç ve bak** (§10 kontrol listesi).
   Kapanış çağrısı sahnenin sonunda belirir; son sahnenin CTA'sını görmek için süresine yakın bir zaman da ekle
   (ör. `--stills 0.3,1.5,4.0,5.5`; sahneden uzun zamanlar atlanır).
   - Metin ekrandan taşıyor mu? Overlay'ler üst üste biniyor mu? Altyazı bandıyla (y≈1150-1790) çakışıyor mu?
   - Aktörler zeminin üstünde mi (havada/gömülü değil mi), ekran dışında mı kaldı?
   - Kontrast yeterli mi (koyu siluet koyu zeminde kaybolmuyor mu → `rim` ekle)?
   - Sahneler birbirinin kopyası gibi mi görünüyor?
   Sorun varsa story.json'u düzelt ve stills'i yeniden üret. (Seslendirme süresi de çıktıda `total` olarak yazar:
   **50-68 sn** aralığında değilse metni kısalt/uzat.)
   `VISUAL_MODE=image` ise §11'deki kare kontrolünü de uygula.
8. **Kaydet:**
   ```
   python scripts/history.py add stories/<slug>/story.json --slot "$SLOT" \
     --topic "<1-2 cümle konu özeti>" \
     --structure "<anlatım yapısı>" --source <url1> --source <url2>
   ```
   (kategori, kanca kalıbı, özne, açılış cümleleri ve tarz bilgileri story.json'dan otomatik alınır.)
9. Kısa bir özetle bitir (seçilen konu, kategori, kanca kalıbı, kaynaklar, tahmini süre). Başka bir şey yapma.

## 2. Konu havuzu

Format sabit: **gerçek, kaynaklı, ters köşeli, tek olay**. "İlginç bilgiler listesi" yapma; adı, yeri ve
zamanı belli **tek bir hikâye** anlat.

| `category` | kapsam | şart |
|---|---|---|
| `hayvan` | kahraman/rekor/tuhaf davranış, insanla kesişen hayvan hikâyeleri | tek, belgeli olay |
| `hayatta-kalma` | kaza, kayıp, kurtuluş, dayanıklılık, kurtarma | 20+ yıl önce ya da can kaybı yok; kişi olayı kendi anlatmış |
| `tarih` | unutulmuş kahraman, tek kararla değişen olay, yanlış bilinen tarih | çoğunlukla 1950 öncesi; taraf tutma |
| `bilim` | tesadüfi keşif, deney, icat, uzay, tıp tarihi | bugün kabul gören bulgu; sağlık tavsiyesi yok |
| `doga` | doğa olayı, coğrafi uç nokta, okyanus/iklim/jeoloji | kurumca ölçülmüş/kayıtlı |
| `tuhaf-olay` | belgelenmiş absürt olaylar | kimseyi aşağılamadan anlatılabilmeli |

**Kategori seçimi:** `history.py recent` çıktısındaki YASAK kategoriyi kullanma (bir önceki videonun kategorisi
ve son 6 videoda 2 kez geçmiş kategori). ÖNERİLEN listesinin ilkini tercih et.

**Aday bulma (WebSearch, en az 3 aday):**
- `"on this day" <ay> <gün> history` (bugünün tarihi fikir tohumudur; kancada tarih kullanma)
- `little-known true story <tema> site:smithsonianmag.com` (aynısı: atlasobscura.com, britannica.com,
  nationalgeographic.com, bbc.com, guinnessworldrecords.com, nps.gov, loc.gov, history.nasa.gov)
- `accidental discovery history of science <alan>`, `survivor account <olay türü> museum`,
  `forgotten hero <dönem> <ülke>`; Türkiye konuları için Türkçe arama + `site:edu.tr` / `site:gov.tr`.

**Eleme (hepsine "evet" değilse adayı at):**
1. Ters köşeyi tek cümleyle yazabiliyor muyum?
2. 2 farklı alan adından güvenilir kaynak var mı (§3)?
3. §2.1'e takılmıyor mu?
4. `history.py topics` ile çakışmıyor mu?
5. Mevcut aktör/backdrop ile gösterilebiliyor mu (gösterilemiyorsa veri sahneleriyle anlatılabiliyor mu)?

### 2.1 Yasak ve korumalı konular
**Seçme:** güncel siyaset, yaşayan siyasetçiler, partiler, seçimler, süren savaşlar, Türkiye'nin 1950 sonrası
siyasi olayları, din/mezhep/etnik tartışmalar, soykırım tartışmaları · sağlık/tıp tavsiyesi veya iddiası
(tedavi, diyet, takviye, alternatif tıp, aşı tartışması) · çocukların zarar gördüğü olaylar, istismar, intihar,
cinsel içerik · gerçek suç (cinayet, kaçırma, terör) · son 20 yılda can kaybı olan olaylar · son 2 yılda olmuş
her olay · komplo teorisi, paranormal, UFO · tehlikeli davranışı özendiren anlatım.
**Şartla:** yaşayan kişi yalnız kendi anlattığı/kabul ettiği, kamuya mal olmuş olayla; olumsuz niteleme, suç
isnadı, özel hayat (sağlık, aile, inanç, gelir) yok; kamu figürü olmayan yaşayan kişinin adını yazma.
Ölmüş kişiye hakaret/teşhis yok. Millet, din, cinsiyet, engellilik hakkında genelleme yok. Marka/şirket
hakkında olumsuz iddia yok. Savaş hikâyesinde taraf övme/yerme ve şiddet ayrıntısı yok.
Başlıkta ve ilk sahnede "ölüm, öldü, ceset, katliam" kelimelerini kullanma.

## 3. Doğrulama kuralları

- Her ana iddia (tarih, yer, sayı, isim, sonuç) için **en az 2 bağımsız** kaynak. Aynı metni kopyalayan siteler
  bağımsız sayılmaz.
- Kaynak kademeleri — **A:** müze, üniversite, resmî kurum/arşiv, hakemli yayın, Britannica, Guinness.
  **B:** köklü basın (BBC, Reuters, AP, Smithsonian Magazine, National Geographic, The Guardian, NYT).
  **C:** Wikipedia. **Sayılmaz:** listicle/içerik çiftliği siteleri, forum, sosyal medya, YouTube, yapay zekâ özeti.
- En az **2 farklı alan adı**; en az biri A ya da B. Wikipedia en fazla bir kaynak sayılır.
- **Çürütme araması zorunlu:** `"<olay>" myth OR debunked` ara. Hikâye efsaneyse ya çürütmeyi ters köşe yap
  (`yanlis-bilinen`) ya da konuyu bırak.
- **Zaman duyarlı iddia** ("hâlâ rekor", "bugün yaşıyor", "dünyanın en …"): son 12 ayda güncellenmiş kaynakla
  teyit et ya da tarihle sabitle ("2022'de rekor olarak kaydedildi"). Teyit yoksa şimdiki zaman kullanma.
- Tarih, sayı ve isimleri kaynaklarla **karşılaştır**; çelişki varsa ya en ihtiyatlı değeri kullan
  ("yaklaşık", "400 km'den fazla") ya da o ayrıntıyı **hiç kullanma**.
- Belirsiz/tartışmalı iddiayı videoya **KOYMA**. Efsane kısmı varsa "anlatılana göre" gibi ölçülü ifade kullan.
- Sayılar yuvarlanabilir ama abartılamaz. Uydurma diyalog, uydurma isim, uydurma sayı yok. Doğrudan alıntı
  yalnız A/B kaynağında birebir geçen tek kısa cümle olabilir.
- Kullandığın kaynak URL'lerini açıklamadaki "Kaynaklar:" listesine ve `history.py add --source` ile kayda ekle.

## 4. Çeşitlilik (YouTube "inauthentic / mass-produced content" politikasına karşı)

Her video **gözle görülür biçimde farklı** olmalı. `python scripts/history.py recent -n 6` çıktısına bak ve:

- **Kategori:** bir önceki videonun kategorisini kullanma; son 6 videoda aynı kategori en fazla 2 kez.
- **Kanca kalıbı:** son 3 videonun `hook` değerini kullanma.
- **Backdrop:** son 2 videonun açılış sahnesi backdrop'unu kullanma; videoda en az 4 farklı backdrop olsun ve
  en az 2 sahnede preset'i dict ile özelleştir (renk, sky, glow, far/mid/ground değiştir).
- **Aktörler:** son videodaki ana aktör kombinasyonunu tekrarlama (ör. husky+musher+team bir daha olmasın).
- **Overlay tarzı:** her videoda 1-2 "imza" veri görseli seç ve son 2 videoda imza olanı tekrar etme:
  bar grafik (`bars`), harita rotası (`route` + `map_dark`), zaman çizelgesi (`route` + `plain_dark`),
  gazete manşetleri (`newspapers`), sayaç (`counter`), dev rakam/metin (`big`), etiket+halka (`tag`), çatlak (`cracks`).
- **Anlatım yapısı:** dönüşümlü kullan — soğuk açılış/ters köşe, kronolojik yolculuk, "ya şöyle olsaydı" sorusu,
  sayılarla geri sayım, karşılaştırma (iki özne/iki dönem), gizem → çözüm.
- **Müzik tonu** (`key`) ve mood dizisini değiştir; uygun düştüğünde farklı ses (`voice`) dene
  (`fahrettin` varsayılan; `dfki`, `fettah` de kurulu).
- Kamera hareketlerini (zoom in/out, pan yönü) sahneden sahneye değiştir.

## 5. Kanca — ilk 7 saniye

İzleyicinin çoğu ilk saniyelerde kaydırıyor. İlk sahne videonun en önemli sahnesidir.

**Yapı (ilk sahne tam 2 satır):**
- Satır 0 — kurulum: izleyicinin bildiği somut bir şey ya da akıl almaz tek bir olgu. 6-10 kelime (en fazla 12).
- Satır 1 — kırılma: bunu ters çeviren 3-6 kelime, `style: "big"`. Cevabı verme, soruyu aç.
- İlk sahnenin toplam `tts` uzunluğu ≤ 130 karakter.
- İlk sahnede tarih/yıl/yer ile başlayan cümle YOK. Tarih ve yer 2. sahnede `chip` overlay'inde durur;
  "Ekim iki bin yirmi iki, Alaska." gibi ayrı bir cümle seslendirme. 2. sahne eylemle başlar.
- Kanca ne vaat ediyorsa video onu anlatır ve cevabı verir.
- **İlk sahne bir soru açar, cevabı sonraki sahnelerde gelir.** İzleyici ilk sahneden sonra "nasıl / neden /
  sonra ne oldu?" diye sormalı. Sonuç, rekor ya da son ilk sahnede söylenmez.

**Kalıp tercihi:** önce `yanlis-bilinen`, `yanlis-kahraman` ya da gizem tonlu `ters-sonuc` (sonucu söylemeyen,
"…haritada yoktu" gibi) dene; diğer kalıplar serbest ama §4 dönüşümüne uy. `imkansiz-olcu` ve `tek-karar`
kancalarında satır 0 sonucu/ne olduğunu açık etmez: ölçüyü ya da durumu verir, nasıl bittiğini saklar.

**Kalıp seç (`hook` alanı):**
| `hook` | mantık | örnek |
|---|---|---|
| `yanlis-kahraman` | herkesin bildiği asıl olan değil | "…bu köpeğin heykelini ziyaret ediyor." → "Ama asıl kahraman... o değildi." |
| `imkansiz-olcu` | akıl almaz sayı + zorlaştıran koşul | "Bu adam okyanusun ortasında bir salda tek başına kaldı." → "Ve günler geçti." |
| `ters-sonuc` | beklenenin tersi oldu | "Bir ordu, kuşlara savaş açtı." → "Sonrasını kimse beklemiyordu." |
| `gizli-kimlik` | göründüğü şey değil | "Bu orduda rütbeli bir subay var." → "Kendisi... bir penguen." |
| `tek-karar` | bir kişinin bir anlık kararı | "Ekranında beş füze görünüyordu." → "Düğmeye basmadı." |
| `yanlis-bilinen` | yaygın inanış yanlış | "Napolyon'u herkes kısa boylu bilir." → "Değildi." |
| `gizem` | belgeli ama nedeni tartışmalı | "Bir kadın sokakta dans etmeye başladı." → "Bir ay sonra yüzlerce kişi duramıyordu." |
| `kucuk-neden` | küçük tesadüf, dev sonuç | "Bir bilim insanı tabağını yıkamayı unuttu." → "Bu unutkanlık milyonlarca hayat kurtardı." |

(Örnekler yalnız kalıbı gösterir, doğrulanmamıştır; kullanacaksan §3'e göre doğrula.)

**Veriden öğrenilenler (2026-11-18, yayından beri "izlemeye devam eden" %, kanal ort. 18,9; KÜÇÜK ÖRNEK, n=7 —
kesin kural değil, eğilim):**
| video | kanca | görsel | kaldı % | görüntülenme |
|---|---|---|---|---|
| Hachiko "…ama sonunu hep yanlış anlattık" | `yanlis-bilinen` | AI | 28,9 | 729 |
| Surtsey "…Gördükleri şey haritada yoktu" | `ters-sonuc` | çizim | 24,3 | 669 |
| Togo "Herkesin kahramanı bir insan olmak zorunda değil..." | `yanlis-kahraman` | çizim | 21,4 | 1312 |
| Endurance "Gemileri buzda ezildi… ama kimse geride kalmadı" | `ters-sonuc` | AI | 20,6 | 322 |
| Godwit "Beş aylık kuş, on bir gün hiç konmadan uçtu" | `imkansiz-olcu` | çizim | 12,3 | 1020 |
| Petrov "Ekranda beş füze vardı... ama o inanmadı" | `tek-karar` | çizim | 12,3 | 467 |
| Emu "…kuşlara savaş açtı… ve çekildi" | `ters-sonuc` | çizim | 9,6 | 281 |

Okuma: görsel kip tek başına farkı açıklamıyor (aynı `ters-sonuc`: Surtsey 24,3 / Emu 9,6). Üstte kalanlar açık
bir soru/çözülmemiş gizem bırakıyor; alttakiler sonucu, rekor sayısını ya da sonu başlıkta/kancada veriyor.

**Yasak açılışlar:** "Biliyor muydunuz", "Bugün size…", "İnanamayacaksınız", selamlama, kanal adı, tarih/yer cümlesi.

**İlk sahnede zorunlu görsel/ses** (çalışan örnek: `stories/togo/story.json` ilk sahnesi):
- 0. saniyede iri ekran yazısı: `{"type":"big","text":"…","y":380,"size":…,"color":"white","at":0}`;
  kırılmada ikinci yazı: `{"type":"big","text":"…","color":"gold","at":"line:1"}`
  (aynı y'de ise ilkine `"until":"line:1"`; alt alta ise y farkı ~170).
  Yazı BÜYÜK HARF, satır başına en fazla 3 kelime / 16 karakter, y 320-520. Seslendirmeyi tekrarlama, özetle.
  **Boyut:** 9 karaktere kadar `size` 150, 10-12 karakter 120, 13-16 karakter 95-100 (daha büyüğü ekrandan taşar;
  doğrulayıcı taşmayı uyarır).
- `sfx`: `{"type":"impact","at":0.05,"gain":0.5}`, `{"type":"riser","at":"line:1","length":1.2}`,
  `{"type":"impact","at":"line:1","gain":1.0}`; ayrıca `flash` ve `punch` `at:"line:1"`.
- Hareket: hareketli aktör ya da `fx`; kamera zoom farkı en az 0.10. Aktörleri y > 650'de tut.

**İkinci kanca:** 20-30. saniyede tek cümleyle merakı yenile ("Ama asıl tehlike bu değildi.").

## 6. Anlatım ve süre

- Toplam **~55-65 sn** (validate tahmini 45-75 dışındaysa uyarır). Yaklaşık 850-1000 karakter seslendirme
  (orta video takip çağrısı ve kapanış cümlesi bu sınırın İÇİNDE; onlar için hikâyeden kısalt).
- **Orta: tırmanış** — tehlike/engel/merak artar (mood: build → tension → drive).
- **Son: sürpriz / ters köşe** — izleyicinin beklemediği gerçek.
- **Kapanış:** son sahnede `title` (kişi/olay adı + yıl) ve `outro`. `outro`'ya `cta`/`footer` YAZMA; motor
  varsayılanı kullanılır ("Her gün inanılmaz ama gerçek bir hikâye · TAKİP ET", footer "Bir Dakika! · Gerçek
  hikâye · Görseller temsilidir"). Son cümle kancaya geri dönsün VE takibe davet etsin: önce kancanın cevabını
  bağla, sonra kısa davet ("Artık gerçek kahramanı sen de biliyorsun. Yarın bir hikâye daha… takip et.").
  CTA y≈1040'ta çizilir: son sahnede bu bantta (y 990-1090) aktör/yazı olmasın; olacaksa `outro`'ya `"y": 960`
  gibi bir değer ver.
- **Orta video takip çağrısı (zorunlu, tek sefer):** abone dönüşümü zayıf (≈4.300 görüntülenmede 5 abone,
  2026-11-18). Videonun **%60-75**'i civarında (asla ilk 20 sn'de değil; son sahnede değil) normal bir sahnenin
  içine **tek kısa satır** ekle, 1,5-2,5 sn (≈25-40 karakter): `"Böyle hikâyeler her gün burada. Takip et."`
  ya da `"Bunun gibi hikâyeler için takip et."`. Hikâyenin akışını kesmesin; bir merak cümlesinden hemen
  sonra gelsin, ardından hikâye devam etsin. Aynı satıra ekranda yalnız mevcut motor özellikleriyle yazı:
  `{"type":"big","text":"TAKİP ET","y":…,"size":120,"color":"gold","at":"line:N","until":"line:N+1"}`
  (satır sahnenin sonuncusuysa `"until":"end:-0.1"`); y 300-1100 arasında, o sahnedeki diğer overlay'lerle ve
  aktörlerle çakışmayan bir yerde. `tag` da olur (ama `tag` sahne sonuna kadar kalır). Yeni ses/efekt türü yok.
- Ekranın alt ~290 pikseli (y > 1630) ve üst ~290 pikseli Shorts arayüzüyle kapanır; oraya önemli yazı koyma.
- Dil: sade, akıcı Türkçe; kısa cümleler. Ölçülü ifade; "en", "ilk", "tek" iddialarını yalnızca kaynak açıkça
  söylüyorsa kullan.
- `tts`: seslendirilecek metin. **Sayıları yazıyla** yaz ("bin dokuz yüz yirmi beş"), kısaltma kullanma ("km" değil
  "kilometre"). Uzun duraklama için `...` kullan (0,5 sn). Her satır noktalama ile bitsin.
- `cap`: ekrandaki altyazı (rakam kullanılabilir). Vurgulanacak kelimelerin başına `*` koy (altın renk).
  Bir satır en fazla ~90 karakter; uzunsa iki satıra böl. `style: "big"` = büyük, tamamı altın renk vurgulu satır.

## 7. Başlık, açıklama, etiketler

- **`youtube_title`**: Türkçe, ≤70 karakter (hedef ≤60), sonda tam 1 emoji, tamamı büyük harf değil.
  Somut özne + çelişki; **cevabı verme**; videoda karşılığı olmayan iddia yok.
  Yasak: "ŞOK", "İNANAMAYACAKSINIZ", "kimse bilmiyor", "yasaklanan", "bilim açıklayamıyor", "ölüm/öldü".
  Örnek: `Herkes Balto'yu biliyor… ama asıl kahraman o değildi 🐕`
- **Merak boşluğu (zorunlu):** başlık açık bir soru ya da çelişki kurar; **sonucu, rekor sayısını ya da sonu
  söylemez** ("…ve çekildi", "…ve kaybetti", "on bir gün hiç konmadan uçtu" gibi). Sayı kullanacaksan sonucu
  değil durumu anlatsın. **Öz-test:** başlığı okuyan kişi videoyu izlemeden "ne oldu?" sorusunun cevabını
  öğreniyorsa yeniden yaz. Eğilim için §5'teki "Veriden öğrenilenler" tablosuna bak.
  Kalıp örnekleri (konular kullanıldı, yalnız kalıbı gösterir; emoji kısaltma için yazılmadı):
  | ✗ sonucu veriyor | ✓ soruyu açıyor |
  |---|---|
  | `Bir ordu makineli tüfekle kuşlara savaş açtı… ve çekildi` | `Bir ordu kuşlara savaş açtı… sonrasını kimse beklemiyordu` |
  | `Beş aylık kuş, on bir gün hiç konmadan uçtu` | `Beş aylık bir kuş, hiç görmediği bir okyanusa açıldı` |
  | `Ekranda beş füze vardı… ama o inanmadı` | `Ekranda beş füze vardı… karar tek bir adamdaydı` |
  | `Bir adam 133 gün okyanusta bir salda yaşadı` | `Bir gemici okyanusta bir salda tek başına kaldı… peki sonra?` |
  İyi çalışan gerçek başlıklar: `…Gördükleri şey haritada yoktu` · `…ama sonunu hep yanlış anlattık`.
- **`description`** (bu sırayla): 1) 1-2 cümle, sonucu söylemeden. 2) boş satır + izleyiciye tek soru.
  3) boş satır + tam olarak `Görseller temsilidir, anlatılan olay gerçektir.` 4) boş satır + `Kaynaklar:` ve
  `- https://…` satırları (en az 2 farklı alan adı). 5) boş satır + `#shorts #gerçekhikaye` + 2-3 konu hashtag'i.
- **`tags`**: 8-15 etiket; kişi/olay adı, yer, yıl, kategori kelimesi, "gerçek hikaye", "inanılmaz ama gerçek",
  "Bir Dakika", "shorts". "hayvan hikayeleri" yalnız `category` `hayvan` ise.

## 8. Storyboard şeması

Çalışan tam örnek: **`stories/togo/story.json`** (9 sahne) — yazmadan önce oku.
Görsel katalog: `docs/catalog/backdrops.png` (12 preset, aşağıdaki sırayla soldan sağa),
`docs/catalog/actors.png` (örnek aktörler; `ship`/`train`/`truck`/`tent` katalogda yok). Gerekirse Read ile bak.

```jsonc
{
  "slug": "ornek-slug",              // klasör adıyla aynı
  "category": "tarih",               // ZORUNLU: hayvan | hayatta-kalma | tarih | bilim | doga | tuhaf-olay
  "hook": "ters-sonuc",              // ZORUNLU: §5'teki kalıp id'si
  "subject": "1932 Emu Savaşı, Avustralya",   // ZORUNLU: kısa özne (kişi/hayvan/olay)
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
(`visual`, `image_style` ve sahne `image` alanları yalnız §11 için.)

**Zaman ifadeleri (`at`, `until`, `dur_to`, `fade_at`):** sahne başından saniye (`1.5`), `"line:N"` (N. satırın
başı, 0'dan), `"line:N:0.7"` (N. satırın %70'i), `"end:-1.5"` (sahne bitiminden 1,5 sn önce).
Sahne süresi seslendirmeden otomatik hesaplanır.

**Koordinatlar:** çerçeve 1080x1920 (x sağa, y aşağı). Zemin çizgisi çoğu preset'te y≈1200-1260.
Altyazı bandı y≈1150-1790 (merkez 1470) → overlay'leri y 300-1100 arasına koy. Outro: CTA y 1040, footer y 1610.

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
| `rock` | kaya/kaide/masa; `w` genişlik |
| `lamp` | sokak lambası |
| `ship` | gemi; `x` orta, `y` su çizgisi (ocean_dusk'ta ≈1135-1150); `w` (yoksa h×1.8), `lights` |
| `train` | lokomotif + vagon; `x` orta, `y` ray; `cars` (2), `w`, `lights` |
| `truck` | kamyon; `x` orta; `w` |
| `tent` | çadır; `x` orta; `w`, `lit` (ışıklı yüz rengi) |

`ship`/`train`/`truck`/`tent` için `d` etkisizdir; hareket için `speed` kullan.
Kadın/çocuk/kalabalık silueti yok: farklı `h`, `hat`, `arm` ile 3-5 `person` yan yana = kalabalık.

Listede olmayan bir hayvan ya da nesne (uçak, roket, otomobil, bina içi…) gerekiyorsa: en yakın siluet + `tag`
etiketi kullan ya da nesneyi hiç gösterme, aktörsüz veri sahnesiyle (`big`, `counter`, `route`, `bars`) anlat.
Denizde insan gösterme (`person` su üstünde duruyor gibi görünür; `ship` kullan). Motoru değiştirme.

### Overlay türleri (`engine/overlays.py` → BUILDERS)
| tür | ne yapar | anahtarlar |
|---|---|---|
| `chip` | sol üstte yer/tarih rozeti | `text`, `y`(250), `dot` renk, `at` |
| `counter` | sayan büyük rakam | `to`, `unit`, `label`, `y`, `size`(150), `color`, `dur`, `at` |
| `big` | zıplayarak gelen büyük metin | `text`, `sub`, `x`, `y`, `size`(120), `color`, `stroke`, `spacing`, `at`, `until` |
| `tag` | etiket (+opsiyonel halka) | `text`, `sub`, `x`, `y`, `size`, `color`, `ring` [x,y,r], `follow` {actor, x, y, r}, `at` |
| `bars` | yatay bar grafik | `title`, `unit`, `max`, `y0`(640), `gap`(320), `icon` (husky/cat/horse/elephant/bird/**none** — hayvan dışı konularda `none`), `items` [{name, value, color, at}] |
| `route` | haritada ilerleyen rota / zaman çizelgesi | `points` [[x,y,"AD"?],...], `total` (km sayacı), `at`, `dur` veya `dur_to`, `labels` [{text,x,y,size}] |
| `newspapers` | uçarak gelen gazete manşetleri | `items` [{headline ("\n" ile 2 satır), sub}], `masthead`, `date`, `step`, `fade_at`, `dim` |
| `title` | kapanış başlığı | `text`, `sub`, `y`, `size`(170), `color`, `spacing`, `at` |
| `outro` | takip çağrısı + footer + sona karartma | `y` (CTA, 1040), `footer_y` (1610), `at`; `cta`/`footer` YAZMA (§6; tek istisna §11) |
| `cracks` | buz/cam çatlağı efekti | `x`, `y`, `n`, `length`, `seed`, `dur`, `water` {width}, `at` |

Renkler: `gold`, `ice`, `white`, `red`, `grey`, `mint`, `cream` veya `"#rrggbb"`.
`bars` öğe adları kısa olsun (en fazla ~10 karakter): ad solda, değer sağda aynı satırda yazılır, uzun ad değerle çakışır.
Gazete manşetleri dönemin dilinde (çoğunlukla İngilizce) olabilir ama **gerçek manşet gibi sunma**; temsili olduğu
açık olsun ve uydurma alıntı yapma (genel ifadeler kullan).

### Reçeteler (kareleri üretilip denendi; motor değişmeden yeni sahne türleri)
```jsonc
// UZAY (sun = ay/gezegen diski; renk: ay "#c9ccd6", Dünya "#3b6ea8", Mars "#b5553a")
{"preset": "plain_dark", "sky": [[-200, "#02030a"], [1920, "#0a0f22"]], "stars": 380,
 "glow": [300, 500, 500, "#22306a", 0.6, 1.0], "sun": [800, 560, 150, "#c9ccd6"]}

// FIRTINALI / GECE DENİZ  (fx: ["rain"]; gemi: {"type":"ship","x":540,"y":1135,"h":260,"rim":"#9fb8d8","speed":12})
{"preset": "ocean_dusk", "sky": [[-200, "#05070d"], [700, "#141c2a"], [1130, "#3a4656"]],
 "glow": [540, 1100, 500, "#56627e", 0.4, 0.5], "ground": {"color": "#0a1018", "color2": "#55606c"}}

// KUTUP / GÜNDÜZ KAR  (fx: ["snow"]; aktör rengi koyu "#1c2430", rim gerekmez)
{"preset": "mountain_dawn", "sky": [[-200, "#8fb4d8"], [700, "#c9dcea"], [1150, "#f2f5f8"]],
 "glow": [540, 900, 600, "#ffffff", 0.5, 0.8], "far": {"color": "#b8c8d8"}, "mid": {"color": "#8ea2b8"},
 "ground": {"color": "#e8eef4"}, "fg": {"color": "#cfd9e4", "y": 1300}}

// İÇ MEKÂN / LABORATUVAR  (masa = rock, lamba = lamp; fx: ["motes"])
{"preset": "plain_warm", "sky": [[-200, "#0d0a07"], [900, "#2a1d10"], [1210, "#3a2a18"], [1215, "#120c07"], [1920, "#0a0705"]],
 "glow": [540, 760, 520, "#ffc46a", 0.55, 1.0]}
// aktörler: {"type":"rock","x":700,"y":1215,"h":150,"w":520}, {"type":"person","x":330,"y":1215,"h":420,"arm":"hold","rim":"#ffc46a"},
//           {"type":"lamp","x":900,"y":1068,"h":230};  nesne vurgusu: {"type":"tag","text":"KÜFLÜ TABAK","x":700,"y":760}

// ZAMAN ÇİZELGESİ  (backdrop "plain_dark"; total verme)
{"type": "route", "points": [[140, 760, "1961"], [420, 760, "1966"], [700, 760, "1969"], [940, 760, "1972"]], "at": 0.3, "dur": 4.0}
// altına olay satırları: {"type":"chip","text":"1969 · AY'A İNİŞ","y":990,"at":1.6,"dot":"gold"}  (y: 900, 990, 1080)

// HAYVANSIZ BAR GRAFİK
{"type": "bars", "title": "KİM NE KADAR?", "unit": "gün", "icon": "none", "items": [...]}
```

### Efektler, müzik ve sesler
- `fx` (`engine/fx.py` → KINDS): `snow`, `blizzard`, `embers`, `motes`, `rain`, `dust`
- `mood` (`engine/music.py` → MOODS): `calm`, `wonder`, `build` (sonda riser), `tension`, `drive`, `warm`, `resolve`, `data`
- `sfx` (`engine/music.py` → SFX_TYPES): `impact` (`gain`), `riser` (`length`; `at` = riser'in BİTTİĞİ an),
  `crack`, `whoosh`, `swish`, `tom`
- Sahne geçişlerinde whoosh otomatik eklenir.

## 9. history.json şeması

```jsonc
{ "version": 1, "entries": [ {
  "slug": "togo", "date": "2026-11-15", "slot": "12:00 | 19:00 | manual",
  "title": "YouTube başlığı",
  "category": "hayvan", "hook": "yanlis-kahraman", "subject": "Togo (kızak köpeği), 1925 serum koşusu",
  "hook_text": "\"İlk sahne satır 0\" / \"satır 1\"",
  "topic": "1-2 cümle konu özeti", "structure": "anlatım yapısı",
  "sources": ["https://...", "https://..."],
  "style": { "backdrops": [...], "actors": [...], "overlays": [...], "fx": [...], "moods": [...],
             "key": "Dm", "voice": "fahrettin", "scenes": 9, "opening_backdrop": "night_city",
             "hook_overlay": ["ASIL KAHRAMAN?", "O DEĞİLDİ"], "visual": "drawn", "images": 0 },
  "status": "hazırlandı"
} ] }
```
Kayıt yalnızca `python scripts/history.py add ...` ile eklenir; elle düzenleme yapma. Eski kayıtlardaki eksik
`category`/`hook`/`subject` alanlarını `history.py` kendisi tamamlar (eski `animal` alanı = özne).

## 10. Kontrol listeleri

**Yazmadan önce (hepsi "evet" olmalı):**
- [ ] Kategori YASAK listesinde değil; kanca kalıbı son 3 videoda yok.
- [ ] Konu §2.1'e takılmıyor; yaşayan kişi varsa şartlara uyuyor.
- [ ] 2 farklı alan adından kaynak var; en az biri A/B; çürütme aramasını yaptım.
- [ ] Ters köşeyi tek cümleyle yazabiliyorum ve video o cevabı veriyor.
- [ ] İlk sahne 2 satır; tarih/yer ile başlamıyor; 0. saniyede `big` yazı var.
- [ ] 2. sahnede tarih/yer `chip` içinde, ayrı cümle olarak seslendirilmiyor.
- [ ] Başlık cevabı vermiyor (§7 merak boşluğu öz-testi: sonuç/rekor sayısı/son başlıkta yok);
      `outro` içinde `cta`/`footer` yok (§11 istisnası hariç).
- [ ] İlk sahne bir soru açıyor, cevabı sonraki sahnelerde geliyor.
- [ ] Orta video takip çağrısı var: %60-75 civarında tek kısa satır ("…takip et.") + aynı satıra `big`/`tag`
      "TAKİP ET"; ilk 20 sn'de ve son sahnede değil. Son cümle kancaya bağlanıp takibe davet ediyor.
- [ ] (image) Her görselli sahnede yedek backdrop var; promptlarda yasak kelime yok.

**Karelere baktıktan sonra** (`--stills 0.3,1.5,4.0`):
- [ ] `00_*_0.3.png`: iri yazı okunuyor, taşmıyor, aktörün üstüne binmiyor.
- [ ] Hiçbir önemli yazı y < 290 ya da y > 1630 bölgesinde değil (altyazı ve footer hariç).
- [ ] Son sahne: `title`, CTA (y≈1040) ve altyazı birbirine ve aktörlere değmiyor.
- [ ] Aktörler zeminde; koyu zeminde `rim` var; açık zeminde aktör rengi koyu.
- [ ] Sahneler birbirinin kopyası değil; en az 4 farklı backdrop.
- [ ] `total` 50-68 sn.
- [ ] Takip çağrısı karesi (`--stills` ile o satırın zamanı): "TAKİP ET" yazısı y 300-1100'de, başka overlay'e,
      aktöre ve altyazıya değmiyor; satır 1,5-2,5 sn.
- [ ] (image) Bozuk görsel kalmadı; yeniden üretim sayısı sınırı aşmadı.

## 11. Yapay zekâ görselleri (yalnız `VISUAL_MODE=image` iken)

Ortam değişkeni `VISUAL_MODE` `image` ise bu bölümü uygula. `drawn` ise ya da tanımlı değilse story.json'a
`visual`, `image_style` ve `image` alanlarını YAZMA; bu bölümü atla.

**Kurulum (story.json):**
- Üst düzey: `"visual": "image"` ve
  `"image_style": {"seed": <4-6 haneli sayı>, "subject": "<ana öznenin 12-25 kelimelik İngilizce tarifi>",
  "setting": "<dönem, yer, mevsim>"}`.
- 4-7 sahneye `"image": {"prompt": "..."}` ekle. İlk ve son sahne görselli olsun.
  (`seed` alanları geçerli kalır ama görseli belirlemez — Cloudflare modeli tohumu yok sayar; yalnız önbellek
  anahtarını ve test/mock görselini etkiler.)
  İsteğe bağlı: `"seed"` (sahne tohumu; yoksa image_style.seed + sahne sırası), `"focus": [0.5, 0.45]`
  (kırpma merkezi), `"actors": true` (çizim aktörlerini görselin üstüne de çiz).
- Veri sahneleri (`bars`, `route`, `map_dark`, `plain_dark` üstünde `counter`/`big`, `newspapers`) görselsiz kalır.
  Görselsiz sahnede manzara preset'i ve siluet aktör kullanma; yalnız `plain_dark` / `plain_warm` / `map_dark`.
- **Her görselli sahnede `backdrop` (ve gerekiyorsa `actors`) yine yazılır:** görsel üretilemezse o çizilir.
  Yedek sade olabilir (bir preset + bir aktör) ama doğrulamadan geçmeli.
- Görselli sahnede aktörler çizilmez (`"image": {"actors": true}` yazmadıkça). `tag.follow` kullanma.
- Görsel karenin üst kısmına kart olarak yerleşir, alt kısım koyulaşır; altyazı ve açılış yazısı okunur kalır.

**Prompt yazımı (İngilizce, 25-60 kelime, tek cümle ya da iki kısa cümle):**
- Sıra: özne → eylem/duruş → mekân → ışık/hava → çekim açısı. Örnek:
  `{subject} standing on cracked sea ice at night, wind-blown snow, faint green aurora, {setting}, wide shot from the side`
- Ana özneyi her sahnede `{subject}` ile yaz; tarifi elle yeniden yazma. Dönem/yer için `{setting}` kullan.
  Başka yer tutucu (`{hero}` vb.) yok.
- Stil kelimesi ekleme (motor "cinematic documentary photograph…" önekini kendisi ekler).
- Ana özne en fazla 4-5 sahnede görünsün; diğerleri mekân, nesne, el, manzara olsun.
- Hayvan: ırkı yaz, "one" de, orta ya da uzak plan seç.
- İnsan: şu kalıplardan biri ZORUNLU — `seen from behind`, `in silhouette`, `distant figure`,
  `face not visible`, `hands only close-up`. Kıyafeti her sahnede aynı kelimelerle yaz.
- Yazı üreten şeyleri isteme: tabela, gazete, kitap, ekran, etiket, harita, mektup.
- Kompozisyon: özne ortada ve karenin üst-orta kısmında; alt kısım sade (altyazı oraya gelir).
- Tüm sahnelerde aynı ışık ailesi (hep "blue hour" ya da hep "overcast daylight" gibi).
- Dönem hatasına karşı modern nesne çağrıştıran kelimelerden kaçın (`street`, `city`, `car`, `phone`);
  gerekirse `no modern objects` ekle.

**YASAK (doğrulayıcı reddeder):**
- Gerçek kişi adı, ünlü, siyasetçi, "looks like …"; gerçek hayvanın adı; marka, logo, bayrak.
- `black and white`, `sepia`, `vintage photo`, `archival`, `old photograph`, `newsreel`, `press photo`:
  tarihî sahneleri renkli canlandırma olarak yaz, gerçek arşiv fotoğrafı taklidi yapma.
- Çocuk (`child`, `kid`, `boy`, `girl`, `baby`), kan, yara, ceset, çıplaklık, silahın birine doğrultulması.

**Açıklama ve kapanış:**
- `description` içinde "Görseller temsilidir, anlatılan olay gerçektir." satırının hemen altına tam olarak:
  `Görseller yapay zekâ ile üretilmiştir.`
- `outro` içine tam olarak:
  `"footer": "Bir Dakika! · Gerçek hikâye · Görseller yapay zekâ ile üretildi, temsilidir"` (`cta` yazma).

**Kare kontrolü (`--stills 0.3,1.5,4.0`; çıktıda `images: 6/7 (...)` satırına bak):**
Her görselli sahnenin karesini Read ile aç. Şunlardan biri varsa o sahneyi YENİDEN ÜRET:
- fazla/eksik/yamuk uzuv, erimiş yüz, iki başlı ya da çoğalmış hayvan,
- harf, rakam, filigran, imza benzeri kalıntı,
- yanlış tür/ırk ya da `subject` tarifine açıkça uymayan özne,
- döneme uymayan nesne (otomobil, telefon, modern bina),
- tanınabilir gerçek bir kişiye benzeyen net yüz,
- siyah-beyaz ya da eski fotoğraf görünümü,
- özne altyazı bandının (karenin alt üçte biri) içinde kalıyor.
Cloudflare modeli tohumu kullanmadığı için `seed` görseli kontrol etmez. Yeniden üretmek için o sahnenin
promptunu hafifçe yeniden yaz (kompozisyon/açı/ışık kelimelerini değiştir ya da sadeleştir); değişen prompt yeni
önbellek anahtarı alır. Sonra stills'i tekrar çalıştır (değişmeyen sahneler önbellekten gelir). **Sahne başına en fazla 2,
video başına en fazla 6 yeniden üretim.**
Hâlâ bozuksa o sahneden `image` alanını sil ve sahneyi `plain_dark` üstünde veri sahnesine çevir.
Çıktıda `images: 0/N` ya da "tümü çizime düştü" yazıyorsa sağlayıcılar yanıt vermiyordur: yeniden deneme,
`visual` alanını `"drawn"` yap, `image` / `image_style` alanlarını ve yapay zekâ cümlelerini (açıklama satırı ve
`outro.footer`) kaldır, yedek sahnelerin karelerine `--stills 1.5 --no-images` ile bir kez bak ve devam et.

**Asla:** API anahtarlarını yazdırma, `env` çıktısı alma, görsel sağlayıcılarına kendin `curl` atma.
