import requests
import json

# Get all market details
url = "https://api.coindcx.com/exchange/v1/markets_details"

try:
    response = requests.get(url)
    response.raise_for_status()
    markets = response.json()
    
    # Filter futures pairs: typically B-<BASE>_USDT perpetuals (adjust filter as needed)
    futures_pairs = []
    for market in markets:
        pair = market.get('market', '')
        if pair.startswith('B-') and pair.endswith('_USDT') and 'perpetual' in market.get('description', '').lower():
            futures_pairs.append({
                'pair': pair,
                'base_currency': market.get('base_currency', ''),
                'quote_currency': market.get('quote_currency', ''),
                'status': market.get('status', 'unknown')
            })
    
    print("All Potential Futures Pairs on CoinDCX:")
    for fp in futures_pairs:
        print(f"- {fp['pair']} ({fp['base_currency']}/{fp['quote_currency']}) - Status: {fp['status']}")
    
    print(f"\nTotal futures-like pairs: {len(futures_pairs)}")
    
    # Save full list
    with open('coindcx_futures_pairs.json', 'w') as f:
        json.dump(futures_pairs, f, indent=2)
    print("Saved to coindcx_futures_pairs.json")

except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
