import requests
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# =======================
# CONFIG
# =======================
CANDLE_URL = "https://www.okx.com/api/v5/market/candles"
TICKER_URL = "https://www.okx.com/api/v5/market/tickers"
INSTRUMENTS_URL = "https://www.okx.com/api/v5/public/instruments"

INTERVAL = "30m"
TOP_N = 300

IMPULSE_THRESHOLD = 5.0   # 🔥 6% in one 30m candle

REQUEST_TIMEOUT = 10
SLEEP_BETWEEN_CALLS = 0.2

# =======================
# EMAIL CONFIG
# =======================
sender_email = "devanshmalhotra98@gmail.com"
sender_password = "cigl vjac hfxl wrwv"
receiver_email = "devanshmalhotra98@gmail.com"

# =======================
# STATIC SYMBOLS
# =======================
static_symbols = [
    "ALCH","ZEREBRO","ALPACA","RARE","BIO","WIF","NKN","VOXEL","BAN","SHELL",
    "AI16Z","GRIFFAIN","MOODENG","CHILLGUY","HMSTR","ZEN","MUBARAK","CETUS",
    "GRASS","SPX","SOL","ARC","PNUT","GAS","PIXEL","SUPER","XRP","STRK",
    "ENJ","BTCDOM","LUMIA","THETA","ANKR","BLUR","MEW","ATOM","RONIN",
    "MAGIC","1000PEPE","TRB","PIPPIN","ALPHA","HIPPO","DF","KOMA","EIGEN",
    "FORTH","GALA","SAFE","ARK","DUSK","VTHO","AAVE","MASK",
    "TRUMP","SUI","DOGE","LAYER","FARTCOIN","ADA","VIRTUAL",
    "1000BONK","WLD","TURBO","BNB","ENA","AVAX","ONDO","LINK","1000SHIB",
    "FET","TRX","AIXBT","LEVER","CRV","NEIRO","TAO","LTC","ETHW","BCH",
    "FLM","BSV","POPCAT","NEAR","FIL","DOT","PENGU","UNI","EOS","ORDI",
    "S","SYN","OM","APT","XLM","TIA","HBAR","OP","INJ","NEIROETH","MELANIA",
    "ORCA","MYRO","TON","ARB","KAITO","BRETT","BIGTIME","1000FLOKI","BSW",
    "ETC","HIFI","1000SATS","PEOPLE","SAGA","BOME","GOAT","RENDER","PENDLE",
    "ARPA","ACT","ARKM","SWELL","SEI","CAKE",
    "RAYSOL","ALGO","ZRO","SWARMS","VINE","BANANA","STX","POL"
]

# =======================
# EMAIL FUNCTION
# =======================
def send_email_alert(impulses, summary):
    subject = "🚨 Crypto 30m Impulse Alerts (≥ 6%)"
    body = "🚨 IMPULSE BREAKOUTS (Single 30m ≥ 6%)\n\n"

    for sym, chg in impulses:
        body += f"{sym}: {chg:.2f}%\n"

    body += "\n📊 SUMMARY\n"
    body += summary

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("📧 Email sent")
    except Exception as e:
        print("⚠️ Email failed:", e)

# =======================
# OKX HELPERS
# =======================
def get_all_usdt_swaps():
    r = requests.get(INSTRUMENTS_URL, params={"instType": "SWAP"}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return {
        i["instId"]
        for i in r.json()["data"]
        if i["settleCcy"] == "USDT"
    }

def get_top_by_volume(valid_swaps):
    r = requests.get(TICKER_URL, params={"instType": "SWAP"}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()

    volume_map = {
        t["instId"]: float(t["volCcy24h"])
        for t in r.json()["data"]
        if t["instId"] in valid_swaps
    }

    return [
        s[0] for s in sorted(volume_map.items(), key=lambda x: x[1], reverse=True)[:TOP_N]
    ]

def map_static_symbols(valid_swaps):
    return [
        f"{s}-USDT-SWAP"
        for s in static_symbols
        if f"{s}-USDT-SWAP" in valid_swaps
    ]

def fetch_last_candle_change(inst_id):
    r = requests.get(
        CANDLE_URL,
        params={"instId": inst_id, "bar": INTERVAL, "limit": 1},
        timeout=REQUEST_TIMEOUT
    )
    r.raise_for_status()

    c = r.json()["data"][0]
    open_p = float(c[1])
    close_p = float(c[4])

    return ((close_p - open_p) / open_p) * 100

# =======================
# MAIN JOB
# =======================
def main_job():
    start_time = datetime.utcnow()
    print("\n🕒 Starting 30m impulse scan (≥ 6%)\n")

    valid_swaps = get_all_usdt_swaps()
    symbols = sorted(set(get_top_by_volume(valid_swaps) + map_static_symbols(valid_swaps)))

    impulse_alerts = []
    processed = 0
    errors = 0

    for symbol in symbols:
        processed += 1
        try:
            change = fetch_last_candle_change(symbol)

            if abs(change) >= IMPULSE_THRESHOLD:
                print(f"🚨 IMPULSE {symbol}: {change:.2f}%")
                impulse_alerts.append((symbol, change))
            else:
                print(f"{symbol}: {change:.2f}%")

        except Exception as e:
            errors += 1
            print(f"⚠️ {symbol} error: {e}")

        time.sleep(SLEEP_BETWEEN_CALLS)

    duration = (datetime.utcnow() - start_time).seconds

    summary = (
        f"Scan Time (UTC): {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Symbols Scanned: {processed}\n"
        f"Impulse Alerts: {len(impulse_alerts)}\n"
        f"Errors: {errors}\n"
        f"Runtime: {duration} seconds\n"
    )

    print("\n📊 SCAN SUMMARY")
    print(summary)

    if impulse_alerts:
        send_email_alert(impulse_alerts, summary)
    else:
        print("✅ No impulses detected")

# =======================
# ENTRY
# =======================
if __name__ == "__main__":
    main_job()
