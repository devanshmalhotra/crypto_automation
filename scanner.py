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
# STATIC SYMBOLS (BASE SYMBOLS)
# =========================
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
# DISCOVER VALID USDT-SWAPS
# =========================
def get_all_usdt_swaps():
    r = requests.get(INSTRUMENTS_URL, params={"instType": "SWAP"}, timeout=10)
    r.raise_for_status()
    return {
        i["instId"] for i in r.json()["data"]
        if i["settleCcy"] == "USDT"
    }

# =========================
# TOP 100 BY VOLUME
# =========================
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
# STATIC SYMBOL MAPPING
# =========================
def map_static_symbols(valid_swaps):
    mapped = []
    skipped = []

    for sym in static_symbols:
        inst = f"{sym}-USDT-SWAP"
        if inst in valid_swaps:
            mapped.append(inst)
        else:
            skipped.append(sym)

    print(f"ℹ️ Static symbols mapped: {len(mapped)}")
    print(f"⚠️ Static symbols skipped (not on OKX): {len(skipped)}")

    return mapped

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

    return all([
        last["close"] > last["open"],
        last["body"] >= 2.5 * last["avg_body"],
        last["body"] >= 0.65 * last["range"],
        last["volume"] >= 1.8 * last["vol_sma"],
        last["close"] > last["ema9"] > last["ema21"],
        df["ema21"].iloc[-1] > df["ema21"].iloc[-2],
        last["range"] >= 1.8 * last["atr"],
        last["close"] > df["high"].iloc[-16:-1].max()
    ])

# =========================
# MAIN
# =========================
def run_scan():
    print("🔍 OKX 30m Impulse Scanner (Top 100 + Static)\n")

    valid_swaps = get_all_usdt_swaps()
    top100 = get_top_100_by_volume(valid_swaps)
    static_mapped = map_static_symbols(valid_swaps)

    symbols = sorted(set(top100 + static_mapped))
    print(f"✅ Total pairs scanned: {len(symbols)}\n")

    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol)
            impulse = detect_impulse(df)

            if impulse:
                print(f"{symbol} → 🚀 IMPULSE FOUND")
                send_email(
                    subject=f"🚀 30m IMPULSE BULL | {symbol}",
                    body=f"Impulse candle detected on {symbol}\nTimeframe: 30m\nExchange: OKX"
                )
            else:
                print(f"{symbol} → ❌ no impulse")

        except Exception as e:
            print(f"{symbol} → ⚠️ error: {e}")

        sleep(0.25)

# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    run_scan()
