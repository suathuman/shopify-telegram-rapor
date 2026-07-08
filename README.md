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

### 1) Shopify Custom App Oluştur

1. Shopify Admin paneline gir → **Settings → Apps and sales channels → Develop apps**.
2. "Allow custom app development" kapalıysa aç.
3. **Create an app** → bir isim ver (örn. `Performans Raporu Botu`).
4. **Configure Admin API scopes** kısmında şu izinleri aç:
   - `read_orders`
   - `read_products`
   - `read_inventory`
   - `read_analytics` (varsa; dönüşüm oranı/trafik verisi için)
5. **Install app** butonuna bas, ardından **Admin API access token**'ı kopyala
   (`shpat_...` ile başlar — sadece bir kere gösterilir, kaydet).
6. Mağaza domainini not et: `magazaadi.myshopify.com` (tarayıcı adres çubuğundan görebilirsin).

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
ile şu 4 secret'ı ekle:

| Secret adı              | Değer                                   |
|--------------------------|------------------------------------------|
| `SHOPIFY_STORE_DOMAIN`   | `magazaadi.myshopify.com`                |
| `SHOPIFY_ACCESS_TOKEN`   | Adım 1'de aldığın `shpat_...` token      |
| `TELEGRAM_BOT_TOKEN`     | Adım 2'de aldığın bot token               |
| `TELEGRAM_CHAT_ID`       | Adım 2'de bulduğun chat id                |

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
export SHOPIFY_ACCESS_TOKEN="shpat_..."
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
