import requests
import json
from src.utils.config_parser import parse_config

def fetch_via_api():
    # 1. First request to main page to get cookies/tokens
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://asunnot.oikotie.fi/myytavat-asunnot"
    })
    
    # We need the params.
    # From config: "houses for selling on herttoniemi area and at least 4 rooms"
    # Parser gives params for URL query.
    # API might expect same params.
    
    with open('config.txt', 'r') as f:
        config_str = f.read()
    _, params = parse_config(config_str)
    
    # Base API params
    api_params = {
        'cardType': 100,
        'limit': 24,
        'offset': 0,
        'sortBy': 'published_desc', # Default sort
    }
    
    # Merge parser params
    # Note: Parser returns 'roomCount[]', 'buildingType[]' etc.
    # Requests handles list items if passed as list of tuples or list in dict?
    # requests params support keys with []
    
    combined_params = api_params.copy()
    combined_params.update(params)
    
    print("Combined Params:", combined_params)
    
    # Step 1: Hit the search page to prime the session
    print("Priming session...")
    main_url = "https://asunnot.oikotie.fi/myytavat-asunnot"
    resp_main = session.get(main_url)
    print(f"Main Page Status: {resp_main.status_code}")
    
    # Step 2: Call API
    api_url = "https://asunnot.oikotie.fi/api/cards"
    print(f"Calling API: {api_url}")
    
    resp_api = session.get(api_url, params=combined_params)
    print(f"API Status: {resp_api.status_code}")
    
    if resp_api.status_code == 200:
        data = resp_api.json()
        print(f"Got {len(data.get('cards', []))} cards.")
        print(json.dumps(data.get('cards', [])[:1], indent=2))
        return data.get('cards', [])
        
    elif resp_api.status_code == 401:
        print("401 Unauthorized. Access denied.")
    else:
        print(f"Failed: {resp_api.text[:200]}")
        
    return []

if __name__ == "__main__":
    fetch_via_api()
