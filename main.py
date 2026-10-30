import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "uz,ru;q=0.9,en;q=0.8"
}

def get_cbu_rates():
    """Markaziy Bank rasmiy ochiq API xizmati"""
    url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code == 200:
            data = res.json()
            rates = {}
            for item in data:
                ccy = item.get("Ccy")
                if ccy in ["USD", "EUR", "RUB"]:
                    rates[ccy] = {
                        "rate": item.get("Rate"),
                        "diff": item.get("Diff")
                    }
            return rates
    except Exception as e:
        print(f"CBU xatosi: {e}")
    return None

def clean_rate(val_str):
    """Matndan sonlarni tozalash"""
    cleaned = "".join(ch for ch in str(val_str) if ch.isdigit() or ch == ".")
    try:
        num = float(cleaned)
        if num > 1000:
            return f"{num:,.0f}".replace(",", " ")
    except ValueError:
        pass
    return None

def get_top_20_commercial_rates():
    """O'zbekistonning Top 20 tijorat banklarining USD kurslari"""
    banks_list = []
    
    # 1. Bank.uz sayti orqali O'zbekistondagi barcha banklar kurslarini jonli o'qish
    try:
        url = "https://bank.uz/uz/currency"
        res = requests.get(url, headers=HEADERS, timeout=25)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            
            # Yangi dizayndagi bank qatorlarini olish
            table_rows = soup.find_all("div", class_="table_row")
            for row in table_rows:
                title_elem = row.find("span", class_="bc-inner-block-left-text")
                if not title_elem:
                    continue
                bank_name = title_elem.get_text(strip=True)
                
                # Sotib olish va sotish ustunlari
                rate_spans = row.find_all("span", class_="medium-text")
                if len(rate_spans) >= 2:
                    buy = clean_rate(rate_spans[0].get_text(strip=True))
                    sell = clean_rate(rate_spans[1].get_text(strip=True))
                    if buy and sell:
                        banks_list.append({"bank": bank_name, "buy": buy, "sell": sell})
    except Exception as e:
        print(f"Bank.uz scraping xatosi: {e}")

    # 2. Zaxira: Depozit.uz agregatoridan olish
    if len(banks_list) < 5:
        try:
            depozit_url = "https://depozit.uz/currency/tashkent"
            res = requests.get(depozit_url, headers=HEADERS, timeout=25)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                rows = soup.find_all("tr")
                for r in rows:
                    name_el = r.find("a", class_="bank-name")
                    if not name_el:
                        continue
                    b_name = name_el.get_text(strip=True)
                    tds = r.find_all("td")
                    if len(tds) >= 3:
                        buy = clean_rate(tds[1].get_text(strip=True))
                        sell = clean_rate(tds[2].get_text(strip=True))
                        if buy and sell:
                            banks_list.append({"bank": b_name, "buy": buy, "sell": sell})
        except Exception as e:
            print(f"Depozit.uz xatosi: {e}")

    # Top 20 ta bankni saralab olish
    unique_banks = {}
    for item in banks_list:
        name = item["bank"].replace("ATB", "").replace("AJ", "").strip()
        if name not in unique_banks:
            unique_banks[name] = item

    return list(unique_banks.values())[:20]

def create_message():
    cbu = get_cbu_rates()
    banks = get_top_20_commercial_rates()
    now_str = datetime.now().strftime("%d.%m.%Y | %H:%M")

    msg = f"🏦 <b>O'zbekiston Valyuta Kurslari</b>\n"
    msg += f"🕒 <i>Vaqt: {now_str}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # Markaziy Bank qismi
    if cbu:
        msg += "🏛 <b>Markaziy Bank rasmiy kursi:</b>\n"
        for ccy, info in cbu.items():
            diff = info.get("diff", "0")
            diff_sign = "+" if not str(diff).startswith("-") else ""
            msg += f"• <b>1 {ccy}</b>: {info['rate']} so'm (<i>{diff_sign}{diff}</i>)\n"
        msg += "\n"

    # Tijorat banklari qismi
    if banks:
        msg += f"💵 <b>Tijorat banklari USD kursi ({len(banks)} ta bank):</b>\n"
        msg += "<i>Bank | Olish / Sotish</i>\n"
        msg += "───────────────────\n"
        for idx, b in enumerate(banks, 1):
            msg += f"<b>{idx}. {b['bank']}</b>: {b['buy']} / {b['sell']}\n"
    else:
        msg += "⚠️ <i>Tijorat banklari kurslarini yuklashda vaqtinchalik uzilish. Keyingi soatda qayta tekshiriladi.</i>\n"

    msg += "\n🔄 <i>Kurslar har 2 soatda avtomatik yangilanadi.</i>\n"
    msg += f"📢 {CHANNEL_ID}"
    return msg

def send_telegram(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Bot token yoki Channel ID topilmadi")
        return
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    r = requests.post(url, json=payload, timeout=20)
    print("Telegram javobi:", r.status_code, r.text)

if __name__ == "__main__":
    post_text = create_message()
    send_telegram(post_text)
