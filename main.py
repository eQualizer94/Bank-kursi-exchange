import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

def fmt(val):
    try:
        n = float(str(val).replace(" ", "").replace(",", "."))
        return f"{n:,.0f}".replace(",", " ")
    except:
        return None

# --- HAR BIR BANKNING RASMIY SAYTI VA API-LARI ---

def get_kapitalbank():
    try:
        url = "https://kapitalbank.uz/api/currency/index.php"
        r = requests.get(url, headers=HEADERS, timeout=7).json()
        for item in r.get("data", []):
            if item.get("code") == "USD":
                return {"bank": "Kapitalbank", "buy": fmt(item.get("buy")), "sell": fmt(item.get("sell"))}
    except:
        pass
    return None

def get_anorbank():
    try:
        url = "https://backend.anorbank.uz/api/v1/currency"
        r = requests.get(url, headers=HEADERS, timeout=7).json()
        for item in r.get("data", []):
            if item.get("code") == "USD":
                return {"bank": "Anorbank", "buy": fmt(item.get("buy_price")), "sell": fmt(item.get("sell_price"))}
    except:
        pass
    return None

def get_tbc():
    try:
        url = "https://api.tbcbank.uz/v1/currencie-rates"
        r = requests.get(url, headers=HEADERS, timeout=7).json()
        for item in r.get("data", []):
            if item.get("currency") == "USD":
                return {"bank": "TBC Bank", "buy": fmt(item.get("buy")), "sell": fmt(item.get("sell"))}
    except:
        pass
    return None

def get_nbu():
    try:
        url = "https://nbu.uz/uz/exchange-rates/json/"
        r = requests.get(url, headers=HEADERS, timeout=7).json()
        for item in r:
            if item.get("code") == "USD":
                return {"bank": "Milliy Bank (NBU)", "buy": fmt(item.get("nbu_buy_price")), "sell": fmt(item.get("nbu_cell_price"))}
    except:
        pass
    return None

def get_ipakyoli():
    try:
        url = "https://ipakyulibank.uz/api/exchange-rates"
        r = requests.get(url, headers=HEADERS, timeout=7).json()
        for item in r:
            if item.get("code") == "USD":
                return {"bank": "Ipak Yo'li Bank", "buy": fmt(item.get("buy")), "sell": fmt(item.get("sell"))}
    except:
        pass
    return None

def get_sqb():
    try:
        url = "https://sqb.uz/api/currency-rates/"
        r = requests.get(url, headers=HEADERS, timeout=7).json()
        for item in r:
            if item.get("code") == "USD":
                return {"bank": "SQB (O'zsanoatqurilishbank)", "buy": fmt(item.get("buy_rate")), "sell": fmt(item.get("sell_rate"))}
    except:
        pass
    return None

def get_hamkorbank():
    try:
        url = "https://hamkorbank.uz/api/currency/"
        r = requests.get(url, headers=HEADERS, timeout=7).json()
        for item in r.get("rates", []):
            if item.get("currency") == "USD":
                return {"bank": "Hamkorbank", "buy": fmt(item.get("buy")), "sell": fmt(item.get("sell"))}
    except:
        pass
    return None

def get_cbu_rates():
    """Markaziy Bank rasmiy kursi"""
    try:
        url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
        r = requests.get(url, headers=HEADERS, timeout=7).json()
        res = {}
        for item in r:
            if item.get("Ccy") in ["USD", "EUR", "RUB"]:
                res[item["Ccy"]] = {"rate": item["Rate"], "diff": item["Diff"]}
        return res
    except:
        pass
    
    # Agar CBU xorijiy IP ni bloklasa, global API zaxirasi
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        r = requests.get(url, timeout=7).json()
        uzs = r.get("rates", {}).get("UZS")
        if uzs:
            return {"USD": {"rate": f"{uzs:,.0f}".replace(",", " "), "diff": "0"}}
    except:
        pass
    return None

def fetch_all_banks():
    bank_funcs = [
        get_kapitalbank,
        get_anorbank,
        get_tbc,
        get_nbu,
        get_ipakyoli,
        get_sqb,
        get_hamkorbank
    ]
    results = []
    # Barcha banklarni parallel (tezkor) tekshirish
    with ThreadPoolExecutor(max_workers=5) as executor:
        for res in executor.map(lambda f: f(), bank_funcs):
            if res and res.get("buy") and res.get("sell"):
                results.append(res)
    return results

def create_message():
    cbu = get_cbu_rates()
    banks = fetch_all_banks()
    now_str = datetime.now().strftime("%d.%m.%Y | %H:%M")

    msg = f"🏦 <b>O'zbekiston Valyuta Kurslari</b>\n"
    msg += f"🕒 <i>Vaqt: {now_str}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if cbu:
        msg += "🏛 <b>Markaziy Bank rasmiy kursi:</b>\n"
        for ccy, info in cbu.items():
            diff = info.get("diff", "0")
            diff_sign = "+" if not str(diff).startswith("-") else ""
            diff_text = f" (<i>{diff_sign}{diff}</i>)" if diff != "0" else ""
            msg += f"• <b>1 {ccy}</b>: {info['rate']} so'm{diff_text}\n"
        msg += "\n"

    if banks:
        msg += f"💵 <b>Tijorat banklari USD kursi ({len(banks)} ta bank):</b>\n"
        msg += "<i>Bank nomi | Olish / Sotish</i>\n"
        msg += "───────────────────\n"
        for idx, b in enumerate(banks, 1):
            msg += f"<b>{idx}. {b['bank']}</b>: {b['buy']} / {b['sell']} so'm\n"
    else:
        msg += "⚠️ <i>Bank serverlariga ulanishda vaqtinchalik xatolik. Keyingi soatda qayta ishga tushadi.</i>\n"

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
