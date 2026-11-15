# Kurulum — "Bir Dakika!" otomatik video sistemi

Sistem her gün **12:00** ve **19:00**'da (İstanbul) GitHub'da kendiliğinden çalışır: Claude yeni bir gerçek hayvan
hikâyesi seçip doğrular, video üretilir ve **Telegram'a** video + başlık + açıklama + etiketler gelir.
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
7. **Değiştirilmiş veya yapay içerik (Altered/synthetic content) ifşası:** Videolar açıkça çizim/animasyon
   siluetlerdir ve gerçek bir kişiyi taklit etmez; YouTube'un kuralına göre bu tür **açıkça gerçek dışı animasyonlar
   için ifşa genellikle zorunlu değildir**. Yine de içerik gerçekçi görünen yapay görüntü/ses içeriyorsa veya emin
   değilsen **"Evet"** işaretle — bu videonun erişimini düşürmez. Açıklamadaki "Görseller temsilidir" notunu silme.
8. **Yayınla.** (İstersen Studio'da yayın saatini planlayabilirsin.)

## 7. Sorun giderme

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

## Opsiyonel: İleride tam otomatik yükleme

YouTube Data API ile doğrudan yükleme mümkündür ama API projesinin **YouTube denetiminden (audit) geçmesi**
gerekir; denetimsiz projelerin yüklediği videolar otomatik olarak **gizli** kalır. İleride istersen:
Google Cloud'da proje aç → YouTube Data API v3'ü etkinleştir → OAuth izin ekranını yayımla → "YouTube API
Services – Audit and Quota Extension" formunu doldur. Onay gelince workflow'a bir yükleme adımı eklenebilir.
Şu an bunun için kod yoktur; mevcut sistem Telegram üzerinden yarı otomatik çalışır.
