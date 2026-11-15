# Kurulum — "Bir Dakika!" otomatik video sistemi

Sistem her gün **12:00** ve **19:00**'da (İstanbul) GitHub'da kendiliğinden çalışır: Claude yeni bir gerçek
hikâye (hayvan, insan, tarih, bilim, doğa) seçip doğrular, video üretilir ve **Telegram'a** video + başlık + açıklama + etiketler gelir.
Sen yalnızca telefondan YouTube'a yüklersin. Tamamı ücretsizdir (Claude Pro aboneliğin dışında).

Toplam kurulum: ~20 dakika.

---

## 1. GitHub deposu

1. https://github.com adresinde hesap aç (varsa giriş yap).
2. Sağ üstte **+ → New repository**.
   - Repository name: `bir-dakika-hayvan-hikayeleri`
   - **Public** seç (public depolarda Actions dakikası ücretsiz ve sınırsızdır).
   - "Add a README" işaretleme → **Create repository**.
3. Dosyaları yükle — iki yoldan biri:

   **a) Web arayüzü (en kolay):** `bir-dakika-proje.zip` dosyasını bilgisayarında aç. Depo sayfasında
   **uploading an existing file** bağlantısına tıkla, klasörün **içindeki her şeyi** (engine, scripts, stories,
   assets, docs, .github, CLAUDE.md, history.json …) sürükle-bırak → **Commit changes**.
   > Not: `.github` gizli klasördür; görünmüyorsa bilgisayarında gizli dosyaları göster. Web arayüzü klasör
   > yüklemeyi desteklemezse (b) yolunu kullan.

   **b) Git komutları:**
   ```bash
   cd bir-dakika-proje
   git init -b main
   git add .
   git commit -m "İlk kurulum"
   git remote add origin https://github.com/KULLANICI_ADIN/bir-dakika-hayvan-hikayeleri.git
   git push -u origin main
   ```

## 2. Telegram botu

1. Telegram'da **@BotFather**'ı aç → `/newbot` yaz.
2. Bota bir ad (ör. `Bir Dakika Teslimat`) ve `bot` ile biten bir kullanıcı adı ver (ör. `birdakika_teslim_bot`).
3. BotFather'ın verdiği **token**'ı kopyala (ör. `123456789:AAH...`). Bu bir şifredir, kimseyle paylaşma.
4. Yeni botunu Telegram'da aç ve **Başlat**'a bas, sonra herhangi bir mesaj yaz (ör. `merhaba`).
5. Tarayıcıda şu adresi aç (TOKEN yerine kendi token'ını yaz):
   `https://api.telegram.org/botTOKEN/getUpdates`
6. Çıkan metinde `"chat":{"id":123456789,...` kısmındaki sayı senin **chat id**'ndir. Kopyala.
   (Boş `"result":[]` görürsen bota tekrar mesaj at ve sayfayı yenile.)

## 3. Claude Pro token'ı

1. Bilgisayarına Claude Code kur (Node.js 18+ gerekir): `npm install -g @anthropic-ai/claude-code`
2. Terminalde: `claude setup-token`
3. Tarayıcıda Claude Pro hesabınla giriş yapıp onayla. Terminalde `sk-ant-oat...` ile başlayan uzun bir
   **token** çıkar → kopyala. (Token yaklaşık 1 yıl geçerlidir.)

> Her çalıştırma Claude Pro kullanım kotandan yer (günde 2 kısa oturum). Aynı saatlerde Claude'u yoğun
> kullanıyorsan kota dolabilir; bu durumda o çalıştırma hata verir ve Telegram'a bildirim gelir.

## 4. Secrets (gizli anahtarlar)

Depo sayfasında **Settings → Secrets and variables → Actions → New repository secret** ile şu üçünü ekle:

| Name | Value |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | 3. adımdaki `sk-ant-oat...` token |
| `TELEGRAM_BOT_TOKEN` | 2. adımdaki BotFather token'ı |
| `TELEGRAM_CHAT_ID` | 2. adımdaki chat id (sadece sayı) |

## 5. Actions'ı etkinleştir ve ilk test

1. Depoda **Actions** sekmesine gir. Uyarı çıkarsa **I understand my workflows, go ahead and enable them**.
2. **Settings → Actions → General → Workflow permissions** bölümünde **Read and write permissions** seç → Save.
3. **Actions → Günlük video → Run workflow** → slot: `manual` → **Run workflow**.
4. ~20-30 dakika sonra Telegram'a video ve 3 mesaj (BAŞLIK / AÇIKLAMA / ETİKETLER) gelir.
   Çalışmanın adımlarını Actions sayfasında canlı izleyebilirsin.

Bundan sonra her gün 12:00 ve 19:00 civarında kendiliğinden çalışır (GitHub zamanlamayı 5-30 dk geciktirebilir,
bu normaldir). Not: Depoda 60 gün hiç hareket olmazsa GitHub zamanlanmış işleri durdurur; sistem her gün commit
attığı için bu normalde olmaz.

## 6. Her gün: YouTube'a yükleme (2 dakika)

1. Telegram'daki videoyu aç → **⋮ → Galeriye kaydet / Save to Gallery**.
2. YouTube uygulaması → **+ → Video yükle / Short oluştur** → kaydettiğin videoyu seç
   (dikey ve 60 sn civarı olduğu için otomatik **Shorts** olur. 60 sn'yi biraz aşsa da 3 dakikaya kadar Shorts sayılır).
   Bilgisayardan: https://studio.youtube.com → **Oluştur → Video yükle**.
3. **Başlık:** Telegram'daki BAŞLIK mesajında başlığın üzerine dokun → kopyalanır → yapıştır.
4. **Açıklama:** AÇIKLAMA mesajındaki kutunun üzerine dokun / kopyala → yapıştır.
5. **Etiketler** (Studio'da "Daha fazla göster → Etiketler"): ETİKETLER mesajını kopyala → yapıştır.
6. **Kitle:** "Hayır, çocuklara özel değil" (hikâye çocuklara yönelik değilse).
7. **Değiştirilmiş veya yapay içerik (Altered/synthetic content):**
   - Telegram notunda "🖼 Yapay zekâ görselleri var" yazıyorsa **her zaman "Evet"** işaretle. Bu videolar gerçek
     bir olayı gerçekçi görünen yapay görsellerle canlandırır; bildirim videonun erişimini düşürmez.
   - Not yoksa (çizim videoları): açıkça çizim/animasyon olduğu için bildirim genellikle zorunlu değildir;
     emin değilsen yine "Evet" işaretle.
   Açıklamadaki "Görseller temsilidir" ve "Görseller yapay zekâ ile üretilmiştir" satırlarını silme.
8. **Yayınla.** (İstersen Studio'da yayın saatini planlayabilirsin.)

## 7. (İsteğe bağlı) Gerçekçi yapay zekâ görselleri — ücretsiz

Bu adım atlanırsa videolar eskisi gibi çizimle üretilir. Açarsan sahne arka planları FLUX ile üretilir;
üretim başarısız olursa sistem kendiliğinden yedek servise (Pollinations), o da olmazsa çizime döner, video yine gelir.

1. https://dash.cloudflare.com adresinde ücretsiz hesap aç (e-posta + şifre) ve e-postanı doğrula.
2. Sol menüden **AI → Workers AI** sayfasını aç → **Use REST API** düğmesine bas.
3. **API token:** aynı sayfada **Create a Workers AI API Token** → bilgileri değiştirmeden **Create API Token** →
   **Copy API Token** ile kopyala (yalnız bir kez gösterilir; bu bir şifredir, kimseyle paylaşma).
   (Elle token oluşturursan yalnız "Workers AI - Read" ve "Workers AI - Edit" izinlerini ver, başka izin verme.)
4. **Account ID:** aynı sayfada **Get Account ID** altındaki değeri kopyala.
5. GitHub deposunda **Settings → Secrets and variables → Actions → New repository secret** ile ekle:

   | Name | Value |
   |---|---|
   | `CLOUDFLARE_ACCOUNT_ID` | 4. adımdaki Account ID |
   | `CLOUDFLARE_API_TOKEN` | 3. adımdaki token |

6. Aynı sayfada **Variables** sekmesi → **New repository variable**: Name `BD_VISUAL_MODE`, Value:
   - `alternate` — ayın tek günleri yapay zekâ, çift günleri çizim (**önerilen başlangıç**; 2 hafta karşılaştır),
   - `image` — her video yapay zekâ görselli,
   - `drawn` — kapalı (değişken hiç yoksa da kapalıdır).
7. **Actions → Günlük video → Run workflow** ile dene (tek günlerden birinde, ya da geçici olarak `image` yaz).
   "Videoyu üret" adımının günlüğünde `images: 6/7 (cloudflare 6, çizim 1)` gibi bir satır görmelisin;
   Telegram notunda da "🖼 Yapay zekâ görselleri var" uyarısı çıkar → yüklerken §6 madde 7'yi uygula.

**Kota:** Cloudflare'in ücretsiz planında günde 10.000 "Neuron" hakkı var (her gün 03:00'te, İstanbul saatiyle,
sıfırlanır). FLUX schnell'in 1024x1024 bir görseli (4 adım) yaklaşık 58 Neuron tutar → günde **yaklaşık 170
görsel**. Sistem günde en fazla ~60 görsel kullanır (video başına üst sınır 30). Kota biterse ya da Cloudflare
yanıt vermezse yedek servis, o da olmazsa çizim devreye girer. Ücret çıkmaz: ücretsiz planda kota aşımı
faturalanmaz, yalnız istek reddedilir.

Kapatmak için `BD_VISUAL_MODE` değerini `drawn` yap. Not: FLUX.1 schnell modeli Apache 2.0 lisanslıdır; para
kazanma aşamasına gelmeden Cloudflare model sayfasındaki kullanım şartlarına bir kez göz at.

## 8. Sorun giderme

| Belirti | Çözüm |
|---|---|
| Telegram'a hiçbir şey gelmiyor | Actions sekmesinde son çalıştırmaya bak. Kırmızıysa hangi adımın kırmızı olduğuna tıkla. Bota en az bir kez mesaj attığından ve `TELEGRAM_CHAT_ID`'nin doğru (sadece sayı) olduğundan emin ol. |
| "Bir Dakika! — videosu üretilemedi" mesajı geldi | Mesajdaki bağlantıyı aç, kırmızı adımı incele. Geçici hatalarda **Re-run jobs** ile yeniden çalıştır. |
| Claude adımı "authentication / invalid token" hatası | Token süresi dolmuş/iptal edilmiş: bilgisayarda `claude setup-token` ile yenisini al, `CLAUDE_CODE_OAUTH_TOKEN` secret'ını güncelle. |
| Claude adımı "usage limit / rate limit" | Pro kotası dolmuş; birkaç saat sonra **Run workflow** ile elle çalıştır. |
| "Claude yeni bir story.json üretmedi" | Claude adımının günlüğüne bak; genelde kota veya ağ sorunu. Yeniden çalıştır. |
| "story.json doğrula" kırmızı | Claude geçersiz bir storyboard yazdı. Yeniden çalıştırmak genelde yeter. Günlükte HATA satırları Türkçe yazar. |
| "Videoyu üret" kırmızı | Render hatası (çoğunlukla bellek/zaman). Yeniden çalıştır; tekrarlarsa günlüğü paylaş. |
| Push hatası | Settings → Actions → General → **Read and write permissions** açık olmalı. |
| Telegram'da video gelmiş ama sonra mesajlar yok | Nadiren Telegram sınırı; Actions'ta "Telegram'a gönder" adımının günlüğüne bak. Video ayrıca 7 gün boyunca çalıştırma sayfasında **Artifacts** altında indirilebilir. |
| Aynı hikâye tekrar geldi | `history.json`'a bak; o kayıt eksikse elle ekleyip commit et. |
| Günlükte `images: 0/N` ya da "tümü çizime düştü" | Cloudflare secret'larını (§7) ve kotayı kontrol et; video çizimle üretilmiştir, sorun yok. "HTTP 401/403" = token yanlış/izinsiz; "HTTP 429" = günlük kota doldu. |
| Yapay zekâ görselleri bozuk/tutarsız | `BD_VISUAL_MODE`'u `drawn` yap, örnek videoyu paylaş. |

## 9. Güncelleme paketi: "gerçek hikâyeler" + görsel hattı (Kasım 2026)

Bu paket konu alanını hayvandan gerçek hikâyelere (hayvan, hayatta kalma, tarih, bilim, doğa, tuhaf olay)
genişletir, açılış (kanca) ve kapanış kurallarını değiştirir, yapay zekâ görsel hattını **kapalı** olarak ekler.

1. Yüklemeyi **12:00-12:45 ve 19:00-19:45 dışında** yap (bot çalışırken commit çakışmasın).
2. GitHub → depo → **Add file → Upload files** → zip'ten çıkan `engine`, `scripts`, `stories` klasörlerini ve
   `CLAUDE.md`, `SETUP.md`, `metrics.json` dosyalarını sürükle (klasör yapısı korunur) → **Commit changes**.
3. `.github/workflows/daily.yml` gizli klasördedir: GitHub'da bu dosyayı aç → kalem simgesi → tüm içeriği sil →
   paketteki `daily.yml` içeriğini yapıştır → **Commit changes**. (Atlanırsa yeni konu kuralları yine çalışır ama
   görsel hattı hiç açılamaz.)
4. **`history.json` yükleme** — bot onu günde iki kez günceller; eski kayıtlar yeni kod tarafından kendiliğinden tamamlanır.
5. **Actions → Günlük video → Run workflow → manual** ile bir deneme yap. Telefonda ilk yeni videoda
   "TAKİP ET" yazısının ekranın ortasında göründüğünü kontrol et.
6. Görselleri açmak istersen §7'yi uygula (2 secret + 1 değişken). İstemezsen hiçbir şey yapma.

Haftalık ölçüm: her pazar, yayınlanalı 3 gün olmuş videolar için Studio'dan şu satırı asistana ilet:
`slug | görüntüleme | izlemeye devam % | ort. izlenme süresi (sn) | ort. izlenme % | bu videodan abone`.
Asistan bunları `python scripts/history.py metrics set ...` ile `metrics.json`'a işler.

## Opsiyonel: İleride tam otomatik yükleme

YouTube Data API ile doğrudan yükleme mümkündür ama API projesinin **YouTube denetiminden (audit) geçmesi**
gerekir; denetimsiz projelerin yüklediği videolar otomatik olarak **gizli** kalır. İleride istersen:
Google Cloud'da proje aç → YouTube Data API v3'ü etkinleştir → OAuth izin ekranını yayımla → "YouTube API
Services – Audit and Quota Extension" formunu doldur. Onay gelince workflow'a bir yükleme adımı eklenebilir.
Şu an bunun için kod yoktur; mevcut sistem Telegram üzerinden yarı otomatik çalışır.
