# Shopify → Telegram Günlük Performans Raporu

Her sabah 08:00'de (Türkiye saati) Shopify mağazandaki son 24 saatlik satış performansını
(ciro, sipariş sayısı, en çok satan ürünler, sipariş listesi, düşük stok uyarıları)
Telegram'a otomatik mesaj olarak gönderen basit bir bot.

Sistem [GitHub Actions](https://github.com/features/actions) üzerinde ücretsiz çalışır —
sunucu kurmana gerek yok. `report.py` her gün otomatik tetiklenir, Shopify'dan veri çeker
ve Telegram'a mesaj atar.

## Nasıl çalışıyor?

```
GitHub Actions (her gun 08:00 TR) --> report.py --> Shopify Admin API'den veri cek
                                                  --> Telegram Bot API'ye mesaj gonder
```

## Kurulum Adım Adım

### 1) Shopify Custom App Oluştur (Dev Dashboard)

Shopify artık custom app'leri **Dev Dashboard** üzerinden oluşturuyor (eski
"Settings → Develop apps" akışı yeni mağazalarda kapalı olabilir).

1. Mağaza admin panelinde **Settings → Apps and sales channels → Develop apps**'e git
   — seni otomatik **Dev Dashboard**'a yönlendirebilir, sorun değil.
2. **Create an app** → bir isim ver (örn. `Performans Raporu Botu`).
3. Uygulama sayfasında **Ayarlar (Settings)** sekmesine git → **Uygulamayı yükle**
   diyerek uygulamayı kendi mağazana kur.
4. Yine **Ayarlar** içinde (ya da "Configuration"da) **Kapsamlar (Scopes)** alanına
   şunu virgülle ayırarak yaz:
   ```
   read_orders,read_products,read_inventory,read_analytics
   ```
   (`read_all_orders` gibi özel/onay gerektiren scope'ları KULLANMA — reddedilir.)
5. Kaydet. **İstemci Kimliği (Client ID)** ve **Gizli anahtar (Client Secret,
   `shpss_...`)** değerlerini kopyala — bunlar `SHOPIFY_CLIENT_ID` ve
   `SHOPIFY_CLIENT_SECRET` olarak kullanılacak.
6. Mağaza domainini not et: `magazaadi.myshopify.com`.

`report.py` her çalıştığında bu Client ID + Client Secret ile (client credentials
grant) 24 saatlik geçici bir Admin API access token alır — statik bir `shpat_`
token'ı elle kopyalamana gerek yok.

### 2) Telegram Bot Oluştur

1. Telegram'da **@BotFather**'ı aç, `/newbot` yaz.
2. Bot için bir isim ve kullanıcı adı belirle (kullanıcı adı `_bot` ile bitmeli).
3. BotFather sana bir **token** verecek (örn. `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`) — kaydet.
4. Raporun geleceği yer:
   - **Kendi hesabına** gelsin istiyorsan: botuna Telegram'dan `/start` yaz (bir mesaj gönder).
   - **Bir kanala** gelsin istiyorsan: botu o kanala admin olarak ekle.
5. `chat_id`'yi öğrenmek için tarayıcıda şu adresi aç (TOKEN'ı kendi token'ınla değiştir):
   `https://api.telegram.org/botTOKEN/getUpdates`
   Gönderdiğin mesajın içinde `"chat":{"id": 123456789, ...}` şeklinde bir alan göreceksin —
   o sayı senin `chat_id`'n.

### 3) Kodu GitHub'a Yükle

Bu klasördeki dosyaları bir GitHub reposuna push et (henüz yapılmadıysa birlikte yapacağız).

### 4) GitHub Secrets Ekle

Repo sayfasında **Settings → Secrets and variables → Actions → New repository secret**
ile şu 5 secret'ı ekle:

| Secret adı               | Değer                                     |
|---------------------------|--------------------------------------------|
| `SHOPIFY_STORE_DOMAIN`    | `magazaadi.myshopify.com`                  |
| `SHOPIFY_CLIENT_ID`       | Adım 1'de aldığın İstemci Kimliği          |
| `SHOPIFY_CLIENT_SECRET`   | Adım 1'de aldığın Gizli anahtar (`shpss_...`) |
| `TELEGRAM_BOT_TOKEN`      | Adım 2'de aldığın bot token                 |
| `TELEGRAM_CHAT_ID`        | Adım 2'de bulduğun chat id                  |

### 5) Test Et

1. GitHub repo sayfasında **Actions** sekmesine git.
2. **Gunluk Performans Raporu** workflow'unu seç.
3. **Run workflow** butonuna basıp manuel tetikle.
4. Birkaç saniye içinde Telegram'a mesaj gelmeli. Gelmezse **Actions** sekmesindeki
   log çıktısına bak — hata mesajı hangi adımda takıldığını gösterir.

Her şey doğruysa, sistem artık her gün otomatik olarak TR saatiyle 08:00'de çalışacak.

## Yerelde (bilgisayarında) Test Etme (opsiyonel)

```bash
pip install -r requirements.txt

export SHOPIFY_STORE_DOMAIN="magazaadi.myshopify.com"
export SHOPIFY_CLIENT_ID="..."
export SHOPIFY_CLIENT_SECRET="shpss_..."
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."

python report.py
```

## Notlar

- **Dönüşüm oranı / trafik verisi**: Bu veri Shopify'ın plan seviyesine göre API üzerinden
  kısıtlı olabilir. Eğer `read_analytics` scope'u ile veri gelmiyorsa, bu bölüm rapora
  eklenmeden ilerlenir; istersen ileride ShopifyQL Analytics API entegrasyonu ekleyebiliriz.
- **Düşük stok eşiği**: `report.py` içinde `LOW_STOCK_THRESHOLD = 5` değeri — istediğin
  sayıya değiştirebilirsin.
- **Saat dilimi**: Cron `0 5 * * *` (UTC) olarak ayarlı, Türkiye UTC+3 sabit olduğu için
  (yaz saati uygulaması yok) bu her zaman 08:00 TR'ye denk gelir.
