import requests
import pandas as pd
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from time import sleep
import os

# =========================
# CONFIG
# =========================
BASE_URL = "https://www.okx.com/api/v5/market/candles"
INTERVAL = "30m"
LIMIT = 120  # enough history for indicators + buffer

SYMBOLS = [
    "BTC-USDT-SWAP",
    "ETH-USDT-SWAP",
    # add more OKX USDT perpetual pairs if needed
]

# =========================
# DATA FETCH
# =========================
def fetch_ohlcv(inst_id):
    params = {
        "instId": inst_id,
        "bar": INTERVAL,
        "limit": LIMIT
    }

    r = requests.get(BASE_URL, params=params, timeout=10)
    r.raise_for_status()

    data = r.json()["data"]
    data.reverse()  # oldest → newest

    df = pd.DataFrame(data, columns=[
        "ts", "open", "high", "low", "close",
        "volume", "volCcy", "volCcyQuote", "confirm"
    ])

    df[["open", "high", "low", "close", "volume"]] = df[
        ["open", "high", "low", "close", "volume"]
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
        last["close"] > last["open"],                            # bull candle
        last["body"] >= 2.5 * last["avg_body"],                  # big body
        last["body"] >= 0.65 * last["range"],                    # clean body
        last["volume"] >= 1.8 * last["vol_sma"],                 # volume spike
        last["close"] > last["ema9"] > last["ema21"],            # trend
        df["ema21"].iloc[-1] > df["ema21"].iloc[-2],             # ema21 rising
        last["range"] >= 1.8 * last["atr"],                      # volatility
        last["close"] > df["high"].iloc[-16:-1].max()            # structure break
    ]

    return all(conditions)

# =========================
# TELEGRAM ALERT (OPTIONAL)
# =========================
def send_telegram(msg):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": msg})

# =========================
# MAIN SCAN LOOP
# =========================
def run_scan():
    print("🔍 OKX 30m Impulse Scanner running...\n")

    for symbol in SYMBOLS:
        try:
            df = fetch_ohlcv(symbol)
            impulse = detect_impulse(df)

            if impulse:
                print(f"{symbol} → 🚀 IMPULSE FOUND")
                send_telegram(f"🚀 30m IMPULSE BULL | {symbol}")
            else:
                print(f"{symbol} → ❌ no impulse")

        except Exception as e:
            print(f"{symbol} → ⚠️ error: {e}")

        sleep(0.3)  # polite rate limit

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    run_scan()
