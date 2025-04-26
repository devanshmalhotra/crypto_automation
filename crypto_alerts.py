import requests
import time
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------ CONFIG ------------------

api_key = "YOUR_CRYPTOCOMPARE_API_KEY"
alert_threshold = 6  # % change
sender_email = "devanshmalhotra98@gmail.com"
sender_password = "ragh uncj zykf uwik"  # Use app password if Gmail 2FA is on
receiver_email = "devanshmalhotra98@gmail.com"

# Static list of coins
static_symbols =["ALCH", "ZEREBRO", "ALPACA", "RARE", "BIO", "WIF", "NKN", "VOXEL", "BAN", "SHELL",
    "AI16Z", "GRIFFAIN", "MOODENG", "CHILLGUY", "HMSTR", "ZEN", "MUBARAK", "CETUS",
    "GRASS", "SPX", "SOL", "ARC", "PNUT", "GAS", "PIXEL", "SUPER", "XRP", "STRK",
    "ENJ", "BTCDOM", "LUMIA", "THETA", "ANKR", "BLUR", "MEW", "ATOM", "RONIN",
    "MAGIC", "1000PEPE", "TRB", "PIPPIN", "ALPHA", "HIPPO", "DF", "KOMA", "EIGEN",
    "FORTH", "GALA", "SAFE", "ARK", "DUSK", "VTHO", "AAVE", "MASK",
    # new added ones
    "ETH", "BTC", "TRUMP", "SUI", "DOGE", "LAYER", "FARTCOIN", "ADA", "VIRTUAL",
    "1000BONK", "WLD", "TURBO", "BNB", "ENA", "AVAX", "ONDO", "LINK", "1000SHIB",
    "FET", "TRX", "AIXBT", "LEVER", "CRV", "NEIRO", "TAO", "LTC", "ETHW", "BCH",
    "FLM", "BSV", "POPCAT", "NEAR", "FIL", "DOT", "PENGU", "UNI", "EOS", "ORDI",
    "S", "SYN", "OM", "APT", "XLM", "TIA", "HBAR", "OP", "INJ", "NEIROETH", "MELANIA",
    "ORCA", "MYRO", "TON", "ARB", "KAITO", "BRETT", "BIGTIME", "1000FLOKI", "BSW",
    "ETC", "HIFI", "1000SATS", "PEOPLE", "SAGA", "BOME", "GOAT", "RENDER", "PENDLE",
    "LDO", "ARPA", "SAND", "ACT", "ARKM", "ENS", "SWELL", "SEI", "CAKE", "JUP",
    "RAYSOL", "ALGO", "ZRO", "SWARMS", "VINE", "PARTI", "BANANA", "STX", "POL", "MEME"
]

# ------------------ EMAIL FUNCTION ------------------

def send_email_alert(alerts, sender_email, sender_password, receiver_email):
    subject = "🚨 Crypto Price Alert: 30-min Movers"
    body = "The following crypto pairs moved more than 6% in the last 30 minutes:\n\n"
    for symbol, change in alerts:
        body += f"{symbol}: {change:.2f}%\n"

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

# ------------------ CRYPTO FUNCTIONS ------------------

def get_price(api_key, symbol, quote='USDT'):
    url = "https://min-api.cryptocompare.com/data/price"
    params = {'fsym': symbol, 'tsyms': quote, 'api_key': api_key}
    response = requests.get(url, params=params)
    data = response.json()
    return data.get(quote)

def get_historical_price(api_key, symbol, quote='USDT', minutes_back=30):
    url = "https://min-api.cryptocompare.com/data/v2/histominute"
    params = {'fsym': symbol, 'tsym': quote, 'limit': minutes_back, 'api_key': api_key}
    response = requests.get(url, params=params)
    data = response.json()

    if data.get("Response") != "Success":
        return None

    prices = data["Data"]["Data"]
    if prices:
        return prices[0]['close']
    return None

def get_30min_movers(api_key, symbols, quote='USDT', alert_threshold=6):
    movers = []
    alerts = []

    for symbol in symbols:
        try:
            price_now = get_price(api_key, symbol, quote)
            time.sleep(1)  # To respect rate limits
            price_30min_ago = get_historical_price(api_key, symbol, quote, minutes_back=30)
            if not price_now or not price_30min_ago:
                continue

            change = ((price_now - price_30min_ago) / price_30min_ago) * 100
            movers.append({'symbol': symbol, 'price_now': price_now, 'price_30min_ago': price_30min_ago, 'change (%)': change})

            if abs(change) >= alert_threshold:
                alerts.append((symbol, change))
        except Exception as e:
            print(f"⚠️ Error processing {symbol}: {e}")

    df = pd.DataFrame(movers).sort_values(by='change (%)', ascending=False)
    return df, alerts

# ------------------ MAIN ------------------

def main_job():
    print(f"\n🕒 Running check at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    df, alerts = get_30min_movers(api_key, static_symbols, alert_threshold=alert_threshold)

    if not df.empty:
        print("\n🔝 Top Movers (30 min):")
        print(df[['symbol', 'change (%)']].head(10))
    else:
        print("\n📭 No price data available.")

    if alerts:
        print("\n🚨 Alerts triggered:")
        for symbol, change in alerts:
            print(f"{symbol}: {change:.2f}%")
        send_email_alert(alerts, sender_email, sender_password, receiver_email)
    else:
        print("\n✅ No alerts triggered.")

if __name__ == "__main__":
    main_job()
