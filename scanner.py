import requests
import pandas as pd
from ta.volatility import AverageTrueRange
from time import sleep
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========================
# CONFIG
# =========================
CANDLE_URL = "https://www.okx.com/api/v5/market/candles"
TICKER_URL = "https://www.okx.com/api/v5/market/tickers"
INSTRUMENTS_URL = "https://www.okx.com/api/v5/public/instruments"

INTERVAL = "30m"
CANDLE_LIMIT = 120
TOP_N = 100

BODY_MULTIPLIER = 2.0   # <-- changed from 2.5 → 2.0
USE_ATR_FILTER = True  # set False if you want body-only

# =========================
# EMAIL CONFIG (SECRETS)
# =========================
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

# =========================
# EMAIL
# =========================
def send_email(subject, body):
    if not all([EMAIL_HOST, EMAIL_USER, EMAIL_PASS, EMAIL_TO]):
        return

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

# =========================
# SYMBOL DISCOVERY
# =========================
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

# =========================
# FETCH CANDLES
# =========================
def fetch_ohlcv(inst_id):
    r = requests.get(
        CANDLE_URL,
        params={"instId": inst_id, "bar": INTERVAL, "limit": CANDLE_LIMIT},
        timeout=10
    )
    r.raise_for_status()

    data = r.json()["data"]
    data.reverse()

    df = pd.DataFrame(data, columns=[
        "ts","open","high","low","close",
        "volume","volCcy","volCcyQuote","confirm"
    ])

    df[["open","high","low","close"]] = df[
        ["open","high","low","close"]
    ].astype(float)

    return df

# =========================
# BIG CANDLE LOGIC (ONLY)
# =========================
def detect_big_candle(df):
    df["body"] = abs(df["close"] - df["open"])
    df["avg_body"] = df["body"].rolling(20).mean()
    df["range"] = df["high"] - df["low"]

    last = df.iloc[-1]

    big_body = last["body"] >= BODY_MULTIPLIER * last["avg_body"]

    if not USE_ATR_FILTER:
        return big_body, last

    atr = AverageTrueRange(
        df["high"], df["low"], df["close"], 14
    ).average_true_range()

    big_range = last["range"] >= 2.0 * atr.iloc[-1]

    return big_body and big_range, last

# =========================
# MAIN
# =========================
def run_scan():
    print("🔍 OKX 30m BIG CANDLE SCANNER\n")

    valid_swaps = get_all_usdt_swaps()
    symbols = get_top_100_by_volume(valid_swaps)

    print(f"✅ Scanning {len(symbols)} pairs\n")

    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol)
            detected, last = detect_big_candle(df)

            if detected:
                direction = "BULL" if last["close"] > last["open"] else "BEAR"
                body_ratio = round(last["body"] / last["avg_body"], 2)

                print(f"{symbol} → 🚨 BIG {direction} CANDLE ({body_ratio}×)")

                send_email(
                    subject=f"🚨 BIG {direction} 30m CANDLE | {symbol}",
                    body=(
                        f"Big 30m candle detected\n\n"
                        f"Symbol    : {symbol}\n"
                        f"Direction : {direction}\n"
                        f"Body Size : {body_ratio} × avg(20)\n"
                        f"Timeframe : 30m\n"
                        f"Exchange  : OKX"
                    )
                )
            else:
                print(f"{symbol} → ❌ no big candle")

        except Exception as e:
            print(f"{symbol} → ⚠️ error: {e}")

        sleep(0.25)

# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    run_scan()
