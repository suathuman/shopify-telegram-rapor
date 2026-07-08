"""
Shopify -> Telegram Gunluk Performans Raporu

Bu script:
1) Shopify magazasindan son 24 saatteki siparisleri ve stok bilgisini ceker
2) Ozet istatistikleri (ciro, siparis sayisi, sepet ortalamasi, top urunler, dusuk stok) hesaplar
3) Sonucu Telegram'a mesaj olarak gonderir

Gerekli ortam degiskenleri (GitHub Actions secrets uzerinden gelir):
  SHOPIFY_STORE_DOMAIN   -> orn: mystore.myshopify.com
  SHOPIFY_ACCESS_TOKEN   -> orn: shpat_xxxxxxxxxxxx
  TELEGRAM_BOT_TOKEN     -> BotFather'dan alinan token
  TELEGRAM_CHAT_ID       -> mesajin gonderilecegi chat/kanal id'si
"""

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests

SHOPIFY_STORE_DOMAIN = os.environ.get("SHOPIFY_STORE_DOMAIN", "")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SHOPIFY_API_VERSION = "2024-10"
LOW_STOCK_THRESHOLD = 5


def require_env():
    missing = [
        name
        for name, value in [
            ("SHOPIFY_STORE_DOMAIN", SHOPIFY_STORE_DOMAIN),
            ("SHOPIFY_ACCESS_TOKEN", SHOPIFY_ACCESS_TOKEN),
            ("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
            ("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID),
        ]
        if not value
    ]
    if missing:
        print(f"HATA: eksik ortam degiskenleri: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def shopify_get(path, params=None):
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/{path}"
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_last_24h_orders():
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    data = shopify_get(
        "orders.json",
        params={
            "status": "any",
            "created_at_min": since,
            "limit": 250,
        },
    )
    return data.get("orders", [])


def fetch_low_stock_variants(threshold=LOW_STOCK_THRESHOLD):
    """En dusuk stoklu ilk birkac varyanti bulur (basit yaklasim: products.json uzerinden)."""
    low_stock = []
    data = shopify_get("products.json", params={"limit": 250})
    for product in data.get("products", []):
        for variant in product.get("variants", []):
            qty = variant.get("inventory_quantity")
            if qty is not None and qty <= threshold:
                low_stock.append(
                    {
                        "title": product.get("title", "?"),
                        "variant": variant.get("title", ""),
                        "qty": qty,
                    }
                )
    low_stock.sort(key=lambda x: x["qty"])
    return low_stock[:10]


def build_summary(orders):
    total_revenue = sum(float(o.get("total_price", 0) or 0) for o in orders)
    order_count = len(orders)
    aov = total_revenue / order_count if order_count else 0

    product_sales = defaultdict(lambda: {"qty": 0, "revenue": 0.0})
    for order in orders:
        for item in order.get("line_items", []):
            key = item.get("title", "?")
            product_sales[key]["qty"] += item.get("quantity", 0)
            product_sales[key]["revenue"] += float(item.get("price", 0) or 0) * item.get("quantity", 0)

    top_products = sorted(product_sales.items(), key=lambda kv: kv[1]["qty"], reverse=True)[:5]

    return {
        "total_revenue": total_revenue,
        "order_count": order_count,
        "aov": aov,
        "top_products": top_products,
    }


def format_currency(amount):
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_message(summary, orders, low_stock):
    today = datetime.now(timezone(timedelta(hours=3))).strftime("%d.%m.%Y")
    lines = [f"*Gunluk Performans Raporu* - {today}", ""]

    lines.append("*Ozet (son 24 saat)*")
    lines.append(f"Toplam Ciro: {format_currency(summary['total_revenue'])}")
    lines.append(f"Siparis Sayisi: {summary['order_count']}")
    lines.append(f"Ortalama Sepet Tutari: {format_currency(summary['aov'])}")
    lines.append("")

    lines.append("*En Cok Satan Urunler*")
    if summary["top_products"]:
        for title, stats in summary["top_products"]:
            lines.append(f"- {title}: {stats['qty']} adet ({format_currency(stats['revenue'])})")
    else:
        lines.append("Bu araliktan satis bulunamadi.")
    lines.append("")

    lines.append("*Siparis Listesi*")
    if orders:
        for order in orders[:20]:
            name = order.get("name", "?")
            total = format_currency(float(order.get("total_price", 0) or 0))
            customer = order.get("customer") or {}
            customer_name = (
                f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
                or "Misafir"
            )
            lines.append(f"- {name} | {customer_name} | {total}")
        if len(orders) > 20:
            lines.append(f"... ve {len(orders) - 20} siparis daha")
    else:
        lines.append("Son 24 saatte siparis yok.")
    lines.append("")

    lines.append("*Dusuk Stok Uyarilari*")
    if low_stock:
        for item in low_stock:
            variant_label = f" ({item['variant']})" if item["variant"] and item["variant"] != "Default Title" else ""
            lines.append(f"- {item['title']}{variant_label}: {item['qty']} adet kaldi")
    else:
        lines.append("Dusuk stoklu urun bulunamadi.")

    return "\n".join(lines)


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
        },
        timeout=30,
    )
    if not response.ok:
        print(f"Telegram gonderim hatasi: {response.status_code} {response.text}", file=sys.stderr)
        response.raise_for_status()


def main():
    require_env()
    try:
        orders = fetch_last_24h_orders()
    except requests.RequestException as exc:
        print(f"Shopify siparis verisi cekilirken hata: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        low_stock = fetch_low_stock_variants()
    except requests.RequestException as exc:
        print(f"Stok verisi cekilirken hata (rapor stoksuz devam edecek): {exc}", file=sys.stderr)
        low_stock = []

    summary = build_summary(orders)
    message = build_message(summary, orders, low_stock)

    try:
        send_telegram_message(message)
    except requests.RequestException:
        sys.exit(1)

    print("Rapor basariyla gonderildi.")


if __name__ == "__main__":
    main()
