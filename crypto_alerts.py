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
sender_password = "ragh uncj zykf uwik"
receiver_email = "devanshmalhotra98@gmail.com"
range_threshold_percent = 5.0
cooldown_hours = 8
cooldown_file = "cooldown_tracker.json"

static_symbols = [ ... ]  # your full list goes here

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

def check_consolidation_and_breakout(df, threshold=5.0):
    recent = df.iloc[-16:-1]  # 15 candles before last closed
    last_closed = df.iloc[-1]  # last *closed* candle
    high = recent['high'].max()
    low = recent['low'].min()
    range_pct = (high - low) / low * 100

    if range_pct <= threshold:
        if last_closed['close'] > high:
            return "breakout_up"
        elif last_closed['close'] < low:
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
            time.sleep(0.75)
            if df is not None and len(df) >= 16:
                result = check_consolidation_and_breakout(df)
                if result:
                    print(f"🚀 {symbol}: {result}")
                    breakouts.append((symbol, result))
                    cooldown_tracker[symbol] = time.time()
        except Exception as e:
            print(f"⚠️ Error processing {symbol}: {e}")

    if breakouts:
        send_email_alert(breakouts)
        save_cooldown_tracker(cooldown_tracker)
    else:
        print("✅ No new breakouts.")

if __name__ == "__main__":
    main_job()
