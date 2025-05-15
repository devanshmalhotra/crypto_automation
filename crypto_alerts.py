import requests
import time
import datetime
import pandas as pd
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------ CONFIG ------------------

api_key = "YOUR_CRYPTOCOMPARE_API_KEY"
sender_email = "devanshmalhotra98@gmail.com"
sender_password = "ragh uncj zykf uwik"  # Use app password if Gmail 2FA is on
receiver_email = "devanshmalhotra98@gmail.com"
range_threshold_percent = 10.0
cooldown_hours = 8
cooldown_file = "cooldown_tracker.json"

static_symbols =[
    "ALCH", "ZEREBRO", "ALPACA", "RARE", "BIO", "WIF", "NKN", "VOXEL", "BAN", "SHELL",
    "AI16Z", "GRIFFAIN", "MOODENG", "CHILLGUY", "HMSTR", "ZEN", "MUBARAK", "CETUS",
    "GRASS", "SPX", "SOL", "ARC", "PNUT", "GAS", "PIXEL", "SUPER", "XRP", "STRK",
    "ENJ", "BTCDOM", "LUMIA", "THETA", "ANKR", "BLUR", "MEW", "ATOM", "RONIN",
    "MAGIC", "1000PEPE", "TRB", "PIPPIN", "ALPHA", "HIPPO", "DF", "KOMA", "EIGEN",
    "FORTH", "GALA", "SAFE", "ARK", "DUSK", "VTHO", "AAVE", "MASK",
    "TRUMP", "SUI", "DOGE", "LAYER", "FARTCOIN", "ADA", "VIRTUAL",
    "1000BONK", "WLD", "TURBO", "BNB", "ENA", "AVAX", "ONDO", "LINK", "1000SHIB",
    "FET", "TRX", "AIXBT", "LEVER", "CRV", "NEIRO", "TAO", "LTC", "ETHW", "BCH",
    "FLM", "BSV", "POPCAT", "NEAR", "FIL", "DOT", "PENGU", "UNI", "EOS", "ORDI",
    "S", "SYN", "OM", "APT", "XLM", "TIA", "HBAR", "OP", "INJ", "NEIROETH", "MELANIA",
    "ORCA", "MYRO", "TON", "ARB", "KAITO", "BRETT", "BIGTIME", "1000FLOKI", "BSW",
    "ETC", "HIFI", "1000SATS", "PEOPLE", "SAGA", "BOME", "GOAT", "RENDER", "PENDLE",
    "ARPA", "ACT", "ARKM", "SWELL", "SEI", "CAKE",
    "RAYSOL", "ALGO", "ZRO", "SWARMS", "VINE", "BANANA", "STX", "POL"
]

# ------------------ COOLDOWN UTILS ------------------

def load_cooldown_tracker():
    if os.path.exists(cooldown_file):
        with open(cooldown_file, 'r') as f:
            return json.load(f)
    return {}

def save_cooldown_tracker(tracker):
    with open(cooldown_file, 'w') as f:
        json.dump(tracker, f)

def is_in_cooldown(symbol, tracker):
    now = time.time()
    last_alert_time = tracker.get(symbol)
    if last_alert_time and now - last_alert_time < cooldown_hours * 3600:
        return True
    return False

# ------------------ EMAIL FUNCTION ------------------

def send_email_alert(breakouts):
    subject = "🚨 Crypto Breakout Alert (15h consolidation)"
    body = "These coins broke out of a 15-hour tight range (<5%) on the last closed hourly candle:\n\n"
    for symbol, direction in breakouts:
        body += f"{symbol}: {direction.upper()}\n"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("📧 Email alert sent!")
    except Exception as e:
        print("⚠️ Failed to send email:", e)

# ------------------ DATA FETCHING ------------------

def get_ohlcv_hourly(symbol, quote='USDT', limit=16):
    url = "https://min-api.cryptocompare.com/data/v2/histohour"
    params = {'fsym': symbol, 'tsym': quote, 'limit': limit, 'api_key': api_key}
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("Response") != "Success":
        return None
    return pd.DataFrame(data["Data"]["Data"])

# ------------------ STRATEGY LOGIC ------------------

def check_consolidation_and_breakout(df, threshold=10.0):
    recent = df.iloc[-16:-1]  # 15 candles before last candle
    high = recent['high'].max()
    low = recent['low'].min()
    range_pct = (high - low) / low * 100

    last_candle = df.iloc[-1]  # latest candle (could be still forming)

    if range_pct <= threshold:
        if last_candle['high'] > high:
            return "breakout_up"
        elif last_candle['low'] < low:
            return "breakout_down"
    return None

# ------------------ MAIN JOB ------------------

def main_job():
    print(f"\n🕒 Running breakout check at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    breakouts = []
    cooldown_tracker = load_cooldown_tracker()

    for symbol in static_symbols:
        if is_in_cooldown(symbol, cooldown_tracker):
            print(f"⏳ Skipping {symbol} (in cooldown)")
            continue

        try:
            df = get_ohlcv_hourly(symbol)
            time.sleep(0.75)  # Respect API rate limits
            if df is not None and len(df) >= 16:
                recent = df.iloc[-16:-1]
                high = recent['high'].max()
                low = recent['low'].min()
                range_pct = (high - low) / low * 100

                result = check_consolidation_and_breakout(df, threshold=range_threshold_percent)
                if result:
                    print(f"🚀 {symbol}: {result} (Range: {range_pct:.2f}%)")
                    breakouts.append((symbol, result))
                    cooldown_tracker[symbol] = time.time()
                else:
                    print(f"❌ {symbol}: No breakout detected (Range: {range_pct:.2f}%)")
            else:
                print(f"⚠️ {symbol}: Not enough data")
        except Exception as e:
            print(f"⚠️ Error processing {symbol}: {e}")

    if breakouts:
        send_email_alert(breakouts)
        save_cooldown_tracker(cooldown_tracker)
    else:
        print("✅ No new breakouts.")

if __name__ == "__main__":
    main_job()
