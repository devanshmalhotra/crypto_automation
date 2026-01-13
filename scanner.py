import requests
import pandas as pd
from ta.trend import EMAIndicator
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

# =========================
# EMAIL CONFIG (FROM SECRETS)
# =========================
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT="587"
EMAIL_USER="devanshmalhotra98@gmail.com"
EMAIL_PASS="ragh uncj zykf uwik"
EMAIL_TO="devanshmalhotra98@gmail.com"


# =========================
# EMAIL FUNCTION
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
# FETCH TOP 100 USDT-SWAP
# =========================
def get_top_usdt_swap_symbols():
    inst_resp = requests.get(
        INSTRUMENTS_URL,
        params={"instType": "SWAP"},
        timeout=10
    )
    inst_resp.raise_for_status()

    instruments = inst_resp.json()["data"]
    usdt_swaps = {i["instId"] for i in instruments if i["settleCcy"] == "USDT"}

    tick_resp = requests.get(
        TICKER_URL,
        params={"instType": "SWAP"},
        timeout=10
    )
    tick_resp.raise_for_status()

    tickers = tick_resp.json()["data"]

    volume_map = {
        t["instId"]: float(t["volCcy24h"])
        for t in tickers
        if t["instId"] in usdt_swaps
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
        "ts", "open", "high", "low", "close",
        "volume", "volCcy", "volCcyQuote", "confirm"
    ])

    df[["open","high","low","close","volume"]] = df[
        ["open","high","low","close","volume"]
    ].astype(float)

    return df

# =========================
# IMPULSE LOGIC
# =========================
def detect_impulse(df):
    df["body"] = abs(df["close"] - df["open"])
    df["range"] = df["high"] - df["low"]
    df["avg_body"] = df["body"].rolling(20).mean()
    df["vol_sma"] = df["volume"].rolling(20).mean()

    df["ema9"] = EMAIndicator(df["close"], 9).ema_indicator()
    df["ema21"] = EMAIndicator(df["close"], 21).ema_indicator()

    atr = AverageTrueRange(df["high"], df["low"], df["close"], 14)
    df["atr"] = atr.average_true_range()

    last = df.iloc[-1]

    conditions = [
        last["close"] > last["open"],
        last["body"] >= 2.5 * last["avg_body"],
        last["body"] >= 0.65 * last["range"],
        last["volume"] >= 1.8 * last["vol_sma"],
        last["close"] > last["ema9"] > last["ema21"],
        df["ema21"].iloc[-1] > df["ema21"].iloc[-2],
        last["range"] >= 1.8 * last["atr"],
        last["close"] > df["high"].iloc[-16:-1].max()
    ]

    return all(conditions)

# =========================
# MAIN SCAN LOOP
# =========================
def run_scan():
    print("🔍 OKX 30m Impulse Scanner (Top 100 by Volume)\n")

    symbols = get_top_usdt_swap_symbols()
    print(f"✅ Loaded {len(symbols)} pairs\n")

    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol)
            impulse = detect_impulse(df)

            if impulse:
                print(f"{symbol} → 🚀 IMPULSE FOUND")

                send_email(
                    subject=f"🚀 30m IMPULSE BULL detected on {symbol}",
                    body=(
                        f"Impulse Bull Candle detected\n\n"
                        f"Symbol: {symbol}\n"
                        f"Timeframe: 30m\n"
                        f"Exchange: OKX\n\n"
                        f"Check chart for pullback or continuation setup."
                    )
                )
            else:
                print(f"{symbol} → ❌ no impulse")

        except Exception as e:
            print(f"{symbol} → ⚠️ error: {e}")

        sleep(0.25)

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    run_scan()
