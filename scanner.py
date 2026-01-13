import requests
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from time import sleep

BASE_URL = "https://fapi.binance.com/fapi/v1/klines"
INTERVAL = "30m"
LIMIT = 100

SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    # add more USDT futures pairs here
]

def fetch_ohlcv(symbol):
    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "limit": LIMIT
    }
    r = requests.get(BASE_URL, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "_","_","_","_","_","_"
    ])

    df[["open","high","low","close","volume"]] = df[
        ["open","high","low","close","volume"]
    ].astype(float)

    return df

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

def run_scan():
    print("🔍 Scanning 30m impulse candles...\n")
    for symbol in SYMBOLS:
        try:
            df = fetch_ohlcv(symbol)
            if detect_impulse(df):
                print(f"🚀 IMPULSE BULL detected on {symbol}")
        except Exception as e:
            print(f"⚠️ {symbol}: {e}")
        sleep(0.2)  # polite rate limiting

if __name__ == "__main__":
    run_scan()
