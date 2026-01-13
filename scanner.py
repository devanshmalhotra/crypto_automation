import requests
import pandas as pd
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from time import sleep
import os

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
# FETCH TOP 100 USDT-SWAP BY VOLUME
# =========================
def get_top_usdt_swap_symbols():
    # 1. Get all USDT-SWAP instruments
    inst_params = {
        "instType": "SWAP"
    }
    inst_resp = requests.get(INSTRUMENTS_URL, params=inst_params, timeout=10)
    inst_resp.raise_for_status()

    instruments = inst_resp.json()["data"]
    usdt_swaps = [
        i["instId"] for i in instruments if i["settleCcy"] == "USDT"
    ]

    # 2. Get tickers (24h volume)
    tick_params = {
        "instType": "SWAP"
    }
    tick_resp = requests.get(TICKER_URL, params=tick_params, timeout=10)
    tick_resp.raise_for_status()

    tickers = tick_resp.json()["data"]

    volume_map = {}
    for t in tickers:
        if t["instId"] in usdt_swaps:
            volume_map[t["instId"]] = float(t["volCcy24h"])

    # 3. Sort by volume and take top N
    top_symbols = sorted(
        volume_map.items(),
        key=lambda x: x[1],
        reverse=True
    )[:TOP_N]

    return [s[0] for s in top_symbols]

# =========================
# FETCH CANDLES
# =========================
def fetch_ohlcv(inst_id):
    params = {
        "instId": inst_id,
        "bar": INTERVAL,
        "limit": CANDLE_LIMIT
    }

    r = requests.get(CANDLE_URL, params=params, timeout=10)
    r.raise_for_status()

    data = r.json()["data"]
    data.reverse()

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
# TELEGRAM (OPTIONAL)
# =========================
def send_telegram(msg):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": msg})

# =========================
# MAIN
# =========================
def run_scan():
    print("🔍 Fetching top 100 USDT-SWAP pairs by volume...\n")
    symbols = get_top_usdt_swap_symbols()
    print(f"✅ Loaded {len(symbols)} pairs\n")

    for symbol in symbols:
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

        sleep(0.25)  # safe rate limit

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    run_scan()
