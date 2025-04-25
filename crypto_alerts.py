import requests
import pandas as pd
from datetime import datetime, timedelta

# -------- CONFIG --------
ALERT_THRESHOLD = 6  # % price change
TOP_N = 50           # Top volume pairs to check

# -------- HELPERS --------
def get_top_volume_symbols(limit=TOP_N):
    url = "https://min-api.cryptocompare.com/data/top/totalvolfull"
    params = {"limit": limit, "tsym": "USDT"}
    response = requests.get(url, params=params)
    data = response.json().get("Data", [])
    
    symbols = []
    for coin in data:
        info = coin.get("CoinInfo", {})
        if "Name" in info:
            symbols.append(info["Name"] + "USDT")
    return symbols

def get_30min_change(symbol):
    end_time = int(datetime.utcnow().timestamp())
    start_time = int((datetime.utcnow() - timedelta(minutes=30)).timestamp())

    url = f"https://min-api.cryptocompare.com/data/v2/histominute"
    params = {
        "fsym": symbol.replace("USDT", ""),
        "tsym": "USDT",
        "limit": 30,
        "toTs": end_time
    }

    response = requests.get(url, params=params)
    data = response.json().get("Data", {}).get("Data", [])

    if len(data) < 2:
        return None

    price_30min_ago = data[0]["close"]
    price_now = data[-1]["close"]
    change_pct = ((price_now - price_30min_ago) / price_30min_ago) * 100

    return round(change_pct, 2)

def main_job():
    symbols = get_top_volume_symbols()
    results = []

    for symbol in symbols:
        try:
            change = get_30min_change(symbol)
            if change is not None:
                results.append({
                    "symbol": symbol,
                    "change (%)": change
                })
        except Exception as e:
            print(f"Error checking {symbol}: {e}")

    df = pd.DataFrame(results)
    if df.empty:
        print("No data to show.")
        return

    df = df.sort_values(by="change (%)", ascending=False)
    movers = df[abs(df["change (%)"]) >= ALERT_THRESHOLD]

    print("\n📊 Top 30-Min Movers:")
    print(df.head(10).to_string(index=False))

    if not movers.empty:
        print("\n🚨 Alerts (>{}%)".format(ALERT_THRESHOLD))
        print(movers.to_string(index=False))
    else:
        print("\nNo alerts at this time.")

# -------- RUN ONCE --------
if __name__ == "__main__":
    main_job()
