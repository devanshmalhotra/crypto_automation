import requests
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =======================
# CONFIG
# =======================
CANDLE_URL = "https://www.okx.com/api/v5/market/candles"
TICKER_URL = "https://www.okx.com/api/v5/market/tickers"
INSTRUMENTS_URL = "https://www.okx.com/api/v5/public/instruments"

INTERVAL = "30m"
TOP_N = 100

IMPULSE_THRESHOLD = 10.0      # single candle %
TREND_THRESHOLD = 10.0        # 3-candle cumulative %

REQUEST_TIMEOUT = 10
SLEEP_BETWEEN_CALLS = 0.2

# =======================
# EMAIL CONFIG
# =======================
sender_email = "devanshmalhotra98@gmail.com"
sender_password = "cigl vjac hfxl wrwv"   # Gmail app password
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
def send_email_alert(impulses, trends):
    subject = "🚨 Crypto 30m Momentum Alerts"
    body = ""

    if impulses:
        body += "🚨 IMPULSE BREAKOUTS (Single 30m ≥ 10%)\n"
        for sym, chg in impulses:
            body += f"{sym}: {chg:.2f}%\n"
        body += "\n"

    if trends:
        body += "📈 TREND EXPANSIONS (3 × 30m ≥ 10%)\n"
        for sym, chg in trends:
            body += f"{sym}: {chg:.2f}%\n"

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
    r = requests.get(
        INSTRUMENTS_URL,
        params={"instType": "SWAP"},
        timeout=REQUEST_TIMEOUT
    )
    r.raise_for_status()
    return {
        i["instId"]
        for i in r.json()["data"]
        if i["settleCcy"] == "USDT"
    }

def get_top_100_by_volume(valid_swaps):
    r = requests.get(
        TICKER_URL,
        params={"instType": "SWAP"},
        timeout=REQUEST_TIMEOUT
    )
    r.raise_for_status()

    data = r.json()
    if data.get("code") != "0":
        raise RuntimeError(data)

    volume_map = {
        t["instId"]: float(t["volCcy24h"])
        for t in data["data"]
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
    return [
        f"{s}-USDT-SWAP"
        for s in static_symbols
        if f"{s}-USDT-SWAP" in valid_swaps
    ]

def fetch_last_3_candle_changes(inst_id):
    r = requests.get(
        CANDLE_URL,
        params={"instId": inst_id, "bar": INTERVAL, "limit": 3},
        timeout=REQUEST_TIMEOUT
    )
    r.raise_for_status()

    data = r.json()
    if data.get("code") != "0":
        raise RuntimeError(data)

    candles = data["data"]
    candles.reverse()  # oldest → newest

    changes = []
    for c in candles:
        open_p = float(c[1])
        close_p = float(c[4])
        changes.append(((close_p - open_p) / open_p) * 100)

    return changes

# =======================
# MAIN JOB
# =======================
def main_job():
    print("\n🕒 Running two-mode 30m OKX scan...\n")

    valid_swaps = get_all_usdt_swaps()
    symbols = sorted(set(
        get_top_100_by_volume(valid_swaps) +
        map_static_symbols(valid_swaps)
    ))

    impulse_alerts = []
    trend_alerts = []

    for symbol in symbols:
        try:
            c1, c2, c3 = fetch_last_3_candle_changes(symbol)

            total_move = c1 + c2 + c3
            same_dir = (
                (c1 > 0 and c2 > 0 and c3 > 0) or
                (c1 < 0 and c2 < 0 and c3 < 0)
            )
            max_single = max(abs(c1), abs(c2), abs(c3))

            # MODE 1 — IMPULSE
            if abs(c3) >= IMPULSE_THRESHOLD:
                print(f"🚨 IMPULSE {symbol}: {c3:.2f}%")
                impulse_alerts.append((symbol, c3))

            # MODE 2 — TREND
            elif (
                abs(total_move) >= TREND_THRESHOLD and
                same_dir and
                max_single < IMPULSE_THRESHOLD
            ):
                print(f"📈 TREND {symbol}: {total_move:.2f}%")
                trend_alerts.append((symbol, total_move))

            else:
                print(f"{symbol}: no signal")

        except Exception as e:
            print(f"⚠️ {symbol} error: {e}")

        time.sleep(SLEEP_BETWEEN_CALLS)

    if impulse_alerts or trend_alerts:
        send_email_alert(impulse_alerts, trend_alerts)
    else:
        print("\n✅ No alerts triggered")

# =======================
# ENTRY
# =======================
if __name__ == "__main__":
    main_job()
