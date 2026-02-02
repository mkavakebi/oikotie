import requests

def test_oikotie_access():
    # Testing if 'text' parameter works for generic search without ID
    url = "https://asunnot.oikotie.fi/myytavat-asunnot?text=Herttoniemi"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Final URL: {response.url}")
        
        if response.status_code == 200:
            print("Successfully accessed!")
            if "Herttoniemi" in response.text and "asunnot" in response.text:
                print("Found 'Herttoniemi' and 'asunnot' in response - text search likely works!")
            else:
                 print("Response content ambiguous.")
        else:
            print("Failed to access.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_oikotie_access()
