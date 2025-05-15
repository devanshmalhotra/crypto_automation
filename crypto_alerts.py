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

range_threshold_percent = 10.0  # Narrow range threshold (10%)
volume_threshold = 1000  # Minimum volume for volume filter alerts
cooldown_hours = 8
cooldown_file = "cooldown_tracker.json"

static_symbols = [
    # Your list of 100 coins
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

# ------------------ EMAIL FUNCTION ------------------

def send_email_alert(alerts, sender_email, sender_password, receiver_email, subject_prefix):
    subject = f"🚨 Crypto Alert: {subject_prefix} Breakouts Detected"
    body = f"The following crypto pairs triggered breakouts:\n\n"
    for symbol, direction, volume, range_pct in alerts:
        body += f"{symbol}: Breakout {direction.upper()}, Volume: {volume:.0f}, Range: {range_pct:.2f}%\n"

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
        print(f"📧 Email alert sent for {subject_prefix} breakouts!")
    except Exception as e:
        print("⚠️ Failed to send email:", e)

# ------------------ COOLDOWN HANDLER ------------------

def load_cooldown():
    if os.path.exists(cooldown_file):
        with open(cooldown_file, 'r') as f:
            return json.load(f)
    else:
        return {}

def save_cooldown(cooldown_data):
    with open(cooldown_file, 'w') as f:
        json.dump(cooldown_data, f)

def is_in_cooldown(symbol, cooldown_data):
    if symbol not in cooldown_data:
        return False
    last_alert_time = datetime.datetime.fromisoformat(cooldown_data[symbol])
    return (datetime.datetime.utcnow() - last_alert_time).total_seconds() < cooldown_hours * 3600

def update_cooldown(symbol, cooldown_data):
    cooldown_data[symbol] = datetime.datetime.utcnow().isoformat()

# ------------------ CRYPTO FUNCTIONS ------------------

def get_hourly_candles(symbol, limit=20, aggregate=1, exchange=''):
    url = "https://min-api.cryptocompare.com/data/v2/histohour"
    params = {
        'fsym': symbol,
        'tsym': 'USDT',
        'limit': limit,
        'aggregate': aggregate,
        'e': exchange,
        'api_key': api_key
    }
    response = requests.get(url, params=params)
    data = response.json()

    if data.get("Response") != "Success":
        print(f"⚠️ Failed to fetch candles for {symbol}: {data.get('Message')}")
        return None

    df = pd.DataFrame(data["Data"]["Data"])
    return df

def check_consolidation_and_breakout(df, threshold=10.0, volume_threshold=0):
    if df is None or len(df) < 17:
        return None  # Not enough data

    recent = df.iloc[-16:-1]  # 15 candles before latest
    high = recent['high'].max()
    low = recent['low'].min()
    range_pct = (high - low) / low * 100

    last_candle = df.iloc[-1]  # latest candle (may be still forming)

    if range_pct <= threshold:
        breakout_up = last_candle['high'] > high
        breakout_down = last_candle['low'] < low
        volume_ok = last_candle['volumefrom'] >= volume_threshold

        if breakout_up or breakout_down:
            return {
                'breakout': 'up' if breakout_up else 'down',
                'volume': last_candle['volumefrom'],
                'volume_ok': volume_ok,
                'range_pct': range_pct,
                'high': high,
                'low': low
            }
    return None

# ------------------ MAIN ------------------

def main_job():
    print(f"\n🕒 Running check at {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    cooldown_data = load_cooldown()

    signals_with_volume = []
    signals_without_volume = []

    for symbol in static_symbols:
        df = get_hourly_candles(symbol)
        if df is None:
            print(f"⚠️ Skipping {symbol} due to data fetch issue.")
            continue

        result = check_consolidation_and_breakout(df, threshold=range_threshold_percent, volume_threshold=volume_threshold)
        if result:
            in_cooldown = is_in_cooldown(symbol, cooldown_data)
            print(f"{symbol}: Range={result['range_pct']:.2f}%, Breakout={result['breakout']}, Volume={result['volume']:.0f} {'(Cooldown active)' if in_cooldown else ''}")

            if not in_cooldown:
                signal_info = (symbol, result['breakout'], result['volume'], result['range_pct'])
                signals_without_volume.append(signal_info)
                if result['volume_ok']:
                    signals_with_volume.append(signal_info)
                update_cooldown(symbol, cooldown_data)
            else:
                print(f" - Alert suppressed due to cooldown.")

        else:
            # No breakout or range too wide
            if df is not None and len(df) >= 16:
                recent = df.iloc[-16:-1]
                high = recent['high'].max()
                low = recent['low'].min()
                range_pct = (high - low) / low * 100
                print(f"{symbol}: No breakout. Range={range_pct:.2f}% > {range_threshold_percent}% or no breakout candle.")

    save_cooldown(cooldown_data)

    # Send alerts if any
    if signals_without_volume:
        send_email_alert(signals_without_volume, sender_email, sender_password, receiver_email, "All Volume")
    else:
        print("✅ No alerts triggered without volume filter.")

    if signals_with_volume:
        send_email_alert(signals_with_volume, sender_email, sender_password, receiver_email, "With Volume Filter")
    else:
        print("✅ No alerts triggered with volume filter.")

if __name__ == "__main__":
    main_job()
