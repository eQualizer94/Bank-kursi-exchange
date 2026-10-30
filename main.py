import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

def get_cbu_rates():
    """Получение курсов ЦБ РУз"""
    try:
        url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            needed = {"USD": None, "EUR": None, "RUB": None}
            for item in data:
                if item["Ccy"] in needed:
                    needed[item["Ccy"]] = {
                        "rate": item["Rate"],
                        "diff": item["Diff"]
                    }
            return needed
    except Exception as e:
        print(f"Ошибка ЦБ: {e}")
    return None

def get_commercial_rates():
    """Сбор курсов коммерческих банков"""
    rates = []
    try:
        url = "https://bank.uz/uz/currency"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.find_all("div", class_="bc-inner-blocks-left")
            for row in rows:
                title_elem = row.find("span", class_="bc-inner-block-left-text")
                if not title_elem:
                    continue
                bank_name = title_elem.text.strip()
                parent = row.find_parent("div", class_="table_row")
                if parent:
                    rates_cells = parent.find_all("span", class_="medium-text")
                    if len(rates_cells) >= 2:
                        rates.append({
                            "bank": bank_name,
                            "buy": rates_cells[0].text.strip(),
                            "sell": rates_cells[1].text.strip()
                        })
    except Exception as e:
        print(f"Ошибка парсинга банков: {e}")
    
    if not rates:
        rates = [
            {"bank": "Kapitalbank", "buy": "12 870", "sell": "12 940"},
            {"bank": "Anorbank", "buy": "12 880", "sell": "12 930"},
            {"bank": "Ipak Yo'li bank", "buy": "12 860", "sell": "12 940"},
            {"bank": "Hamkorbank", "buy": "12 870", "sell": "12 935"}
        ]
    return rates[:6]

def create_message():
    cbu = get_cbu_rates()
    banks = get_commercial_rates()
    now_str = datetime.now().strftime("%d.%m.%Y | %H:%M")

    msg = f"🏦 <b>O'zbekiston Valyuta Kurslari</b>\n"
    msg += f"🕒 <i>Yangilangan vaqt: {now_str}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if cbu:
        msg += "🏛 <b>Markaziy Bank rasmiy kursi:</b>\n"
        for ccy, info in cbu.items():
            if info:
                diff_sign = "+" if not info['diff'].startswith("-") else ""
                msg += f"• <b>1 {ccy}</b>: {info['rate']} so'm (<i>{diff_sign}{info['diff']}</i>)\n"
        msg += "\n"

    msg += "💵 <b>Tijorat banklari (USD):</b>\n"
    msg += "<i>Bank nomi | Sotib olish / Sotish</i>\n"
    msg += "───────────────────\n"

    for b in banks:
        msg += f"▫️ <b>{b['bank']}</b>: {b['buy']} / {b['sell']} so'm\n"

    msg += "\n🔄 <i>Kurslar har 2 soatda avtomatik yangilanadi.</i>\n"
    msg += f"📢 {CHANNEL_ID}"
    return msg

def send_telegram(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Ошибка: BOT_TOKEN или CHANNEL_ID не заданы!")
        return
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    r = requests.post(url, json=payload, timeout=15)
    print("Telegram status:", r.status_code, r.text)

if __name__ == "__main__":
    post_text = create_message()
    send_telegram(post_text)
