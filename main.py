import os
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8,en;q=0.7"
}

def clean_num(val):
    try:
        n = float(str(val).replace(" ", "").replace(",", "."))
        return f"{n:,.0f}".replace(",", " ")
    except:
        return None

def get_rates_data():
    """Tijorat banklari va CBU kurslarini barqaror ochiq manbadan olish"""
    banks_data = []
    cbu_data = {}

    # 1. O'zbekiston Milliy Banki (NBU) ochiq barcha banklar/valyutalar ochiq JSON manbasi
    try:
        url = "https://nbu.uz/uz/exchange-rates/json/"
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            for item in r.json():
                code = item.get("code")
                if code in ["USD", "EUR", "RUB"]:
                    cbu_data[code] = {
                        "rate": clean_num(item.get("cb_price")),
                        "diff": item.get("diff", "0")
                    }
                if code == "USD":
                    buy = clean_num(item.get("nbu_buy_price"))
                    sell = clean_num(item.get("nbu_cell_price"))
                    if buy and sell:
                        banks_data.append({"bank": "O'zmilliybank (NBU)", "buy": buy, "sell": sell})
    except Exception as e:
        print("NBU xatosi:", e)

    # 2. O'zbekiston ochiq kurslar agregatori (GitHub IP'larini bloklamaydi)
    try:
        url = "https://raw.githubusercontent.com/uzbekistan-currency/rates/main/rates.json"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for b in data.get("banks", []):
                banks_data.append({
                    "bank": b.get("name"),
                    "buy": clean_num(b.get("buy")),
                    "sell": clean_num(b.get("sell"))
                })
    except:
        pass

    # 3. Agar yuqoridagi agregat bo'sh kelsa, banklarning yengil mobil gatewaylaridan tekshirish
    if len(banks_data) <= 1:
        fallback_urls = [
            ("Kapitalbank", "https://api.kapitalbank.uz/v1/currency/rates"),
            ("Anorbank", "https://api.anorbank.uz/api/v1/currency"),
            ("Ipak Yo'li", "https://ipakyulibank.uz/api/exchange-rates"),
            ("Hamkorbank", "https://hamkorbank.uz/api/currency/"),
            ("Infinbank", "https://infinbank.com/api/v1/rates/"),
            ("Aloqabank", "https://aloqabank.uz/api/currency/"),
            ("Agrobank", "https://agrobank.uz/api/currency/")
        ]
        
        for name, api in fallback_urls:
            try:
                res = requests.get(api, headers=HEADERS, timeout=5)
                if res.status_code == 200:
                    dt = res.json()
                    # Har xil JSON tuzilmalaridan USD kurslarini ajratib olish
                    b_str = str(dt)
                    if "USD" in b_str:
                        # standart qidiruv
                        items = dt if isinstance(dt, list) else dt.get("data", dt.get("rates", []))
                        if isinstance(items, list):
                            for row in items:
                                if any(row.get(k) == "USD" for k in ["code", "currency", "ccy"]):
                                    buy = clean_num(row.get("buy") or row.get("buy_price") or row.get("buy_rate"))
                                    sell = clean_num(row.get("sell") or row.get("sell_price") or row.get("sell_rate"))
                                    if buy and sell:
                                        banks_data.append({"bank": name, "buy": buy, "sell": sell})
                                        break
            except:
                continue

    # Markaziy Bank kursini to'ldirish (agar NBU berolmagan bo'lsa)
    if not cbu_data.get("USD"):
        try:
            r = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/", headers=HEADERS, timeout=10)
            if r.status_code == 200:
                for item in r.json():
                    if item.get("Ccy") in ["USD", "EUR", "RUB"]:
                        cbu_data[item["Ccy"]] = {
                            "rate": clean_num(item.get("Rate")),
                            "diff": item.get("Diff")
                        }
        except:
            pass

    return cbu_data, banks_data

def create_message():
    cbu, banks = get_rates_data()
    now_str = datetime.now().strftime("%d.%m.%Y | %H:%M")

    msg = f"🏦 <b>O'zbekiston Valyuta Kurslari</b>\n"
    msg += f"🕒 <i>Vaqt: {now_str}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if cbu:
        msg += "🏛 <b>Markaziy Bank rasmiy kursi:</b>\n"
        for ccy in ["USD", "EUR", "RUB"]:
            info = cbu.get(ccy)
            if info and info.get("rate"):
                diff = str(info.get("diff", "0"))
                sign = "+" if not diff.startswith("-") and diff != "0" else ""
                msg += f"• <b>1 {ccy}</b>: {info['rate']} so'm (<i>{sign}{diff}</i>)\n"
        msg += "\n"

    if banks:
        msg += f"💵 <b>Tijorat banklari USD kursi:</b>\n"
        msg += "<i>Bank nomi | Olish / Sotish</i>\n"
        msg += "───────────────────\n"
        # Qaytarilmasligi uchun
        seen = set()
        count = 1
        for b in banks:
            b_name = b["bank"]
            if b_name not in seen and b.get("buy") and b.get("sell"):
                seen.add(b_name)
                msg += f"<b>{count}. {b_name}</b>: {b['buy']} / {b['sell']} so'm\n"
                count += 1
    else:
        msg += "ℹ️ <i>Banklar kurslari yangilanmoqda...</i>\n"

    msg += "\n🔄 <i>Kurslar har 2 soatda avtomatik yangilanadi.</i>\n"
    msg += f"📢 {CHANNEL_ID}"
    return msg

def send_telegram(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload, timeout=15)

if __name__ == "__main__":
    msg = create_message()
    send_telegram(msg)
