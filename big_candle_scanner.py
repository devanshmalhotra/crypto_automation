import requests
import json

# Public API endpoint for futures instruments (no auth required)
url = "https://api.coindcx.com/exchange/v1/derivatives/futures/data/instrument"

try:
    response = requests.get(url)
    response.raise_for_status()  # Raise error for bad status codes
    data = response.json()
    
    # Extract pairs; data is typically a list of instrument dicts
    if isinstance(data, list):
        pairs = [item.get('pair', 'N/A') for item in data if item.get('status') == 'active']
    else:
        pairs = [data.get('pair', 'N/A')] if data.get('status') == 'active' else []
    
    print("Active Futures Pairs on CoinDCX:")
    for pair in pairs:
        print(pair)
    
    # Optional: Save to JSON file
    with open('coindcx_futures_pairs.json', 'w') as f:
        json.dump(pairs, f, indent=2)
    print(f"\nTotal pairs: {len(pairs)}. Saved to coindcx_futures_pairs.json")

except requests.exceptions.RequestException as e:
    print(f"Error fetching data: {e}")
except json.JSONDecodeError:
    print("Invalid JSON response from API")
