import requests
import json

url = "https://api.coindcx.com/exchange/v1/derivatives/futures/data/instrument"

try:
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    # Handle dict structure: data['instrument'] is the single active instrument
    if isinstance(data, dict) and 'instrument' in data:
        instrument = data['instrument']
        pair = instrument.get('pair')
        status = instrument.get('status')
        print(f"Futures Instrument Details:")
        print(f"Pair: {pair}")
        print(f"Status: {status}")
        print(f"Kind: {instrument.get('kind')}")
        print(f"Settle Currency: {instrument.get('settle_currency_short_name')}")
        pairs = [pair] if status == 'active' else []
    else:
        pairs = []
        print("Unexpected response structure")
    
    print(f"\nActive Futures Pairs: {pairs}")
    print(f"Total: {len(pairs)}")

    # Save to JSON
    with open('coindcx_futures_instrument.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("Full data saved to coindcx_futures_instrument.json")

except requests.exceptions.RequestException as e:
    print(f"Error fetching data: {e}")
except json.JSONDecodeError:
    print("Invalid JSON response")
