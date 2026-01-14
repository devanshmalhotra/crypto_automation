import requests
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# =======================
# CONFIG
# =======================
CANDLE_URL = "https://www.okx.com/api/v5/market/candles"
TICKER_URL = "https://www.okx.com/api/v5/market/tickers"
INSTRUMENTS_URL = "https://www.okx.com/api/v5/public/instruments"

INTERVAL = "30m"
CANDLE_LIMIT = 5
TOP_N = 100
ALERT_THRESHOLD = 10.0  # percent

# =======================
# EMAIL CONFIG (ENV VARS)
# =======================
sender_email = os.getenv("EMAIL_USER")
sender_password = os.getenv("EMAIL_PASS")
receiver_email = os.getenv("EMAIL_TO")

# =======================
# STATIC SYMBOLS (BASE)
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
# EMAIL FUNCTION (SAME STYLE)
# =======================
def send_email_alert(alerts):
    subject = "🚨 Crypto Price Alert: 30-min Movers"
    body = "The following crypto pairs moved more than 10% in the last 30 minutes:\n\n"

    for symbol, change in alerts:
        body += f"{symbol}: {change:.2f}%\n"

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
        print("📧 Email alert sent!")
    except Exception as e:
        print("⚠️ Failed to send email:", e)

# =======================
# OKX HELPERS
# =======================
def get_all_usdt_swaps():
    r = requests.get(INSTRUMENTS_URL, params={"instType": "SWAP"}, timeout=10)
    r.raise_for_status()
    return {
        i["instId"] for i in r.json()["data"]
        if i["settleCcy"] == "USDT"
    }

def get_top_100_by_volume(valid_swaps):
    r = requests.get(TICKER_URL, params={"instType": "SWAP"}, timeout=10)
    r.raise_for_status()

    volume_map = {
        t["instId"]: float(t["volCcy24h"])
        for t in r.json()["data"]
        if t["instId"] in valid_swaps
    }

    return [
        s[0] for s in sorted(
            volume_map.items(),
            key=lambda x: x[1],
            reverse=True
        )[:TOP_N]
    ]

def map_static_symbols(valid_swaps):
    mapped = []
    for sym in static_symbols:
        inst = f"{sym}-USDT-SWAP"
        if inst in valid_swaps:
            mapped.append(inst)
    return mapped

def fetch_last_30m_candle(inst_id):
    r = requests.get(
        CANDLE_URL,
        params={"instId": inst_id, "bar": INTERVAL, "limit": CANDLE_LIMIT},
        timeout=10
    )
    r.raise_for_status()
    last = r.json()["data"][0]  # newest candle
    return float(last[1]), float(last[4])

# =======================
# MAIN JOB (LIKE YOUR SCRIPT)
# =======================
def main_job():
    print("\n🕒 Running 30m OKX price shock scan...\n")

    valid_swaps = get_all_usdt_swaps()
    symbols = sorted(
        set(
            get_top_100_by_volume(valid_swaps)
            + map_static_symbols(valid_swaps)
        )
    )

    alerts = []

    for symbol in symbols:
        try:
            open_price, close_price = fetch_last_30m_candle(symbol)
            change = ((close_price - open_price) / open_price) * 100

            if abs(change) >= ALERT_THRESHOLD:
                print(f"🚨 {symbol}: {change:.2f}%")
                alerts.append((symbol, change))
            else:
                print(f"{symbol}: no major move")

        except Exception as e:
            print(f"⚠️ Error processing {symbol}: {e}")

        time.sleep(0.2)

    if alerts:
        print("\n🚨 Alerts triggered:")
        for symbol, change in alerts:
            print(f"{symbol}: {change:.2f}%")
        send_email_alert(alerts)
    else:
        print("\n✅ No alerts triggered.")

# =======================
# ENTRY
# =======================
if __name__ == "__main__":
    main_job()
