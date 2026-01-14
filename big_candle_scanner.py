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

BODY_MULTIPLIER = 2.0
USE_ATR_FILTER = True

# =========================
# EMAIL CONFIG (ENV VARS)
# =========================
sender_email = "devanshmalhotra98@gmail.com"
sender_password = "cigl vjac hfxl wrwv"  # Use app password if Gmail 2FA is on
receiver_email = "devanshmalhotra98@gmail.com"

# =========================
# EMAIL (AGGREGATED)
# =========================
def send_email_alert(alerts):
    if not alerts:
        return

    subject = "🚨 Crypto Big Candle Alert (30m)"
    body = "The following crypto pairs formed BIG candles in the last 30 minutes:\n\n"

    for symbol, direction, ratio in alerts:
        body += f"{symbol}: {direction} ({ratio}× avg body)\n"

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
# BIG CANDLE LOGIC
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

    alerts = []  # <-- COLLECT ALL ALERTS

    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol)
            detected, last = detect_big_candle(df)

            if detected:
                direction = "BULL" if last["close"] > last["open"] else "BEAR"
                body_ratio = round(last["body"] / last["avg_body"], 2)

                print(f"{symbol} → 🚨 BIG {direction} CANDLE ({body_ratio}×)")
                alerts.append((symbol, direction, body_ratio))
            else:
                print(f"{symbol} → ❌ no big candle")

        except Exception as e:
            print(f"{symbol} → ⚠️ error: {e}")

        sleep(0.25)

    # ✅ SEND ONE EMAIL AT END
    if alerts:
        send_email_alert(alerts)
    else:
        print("\n✅ No big candles detected.")

# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    run_scan()
