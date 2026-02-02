import requests
from bs4 import BeautifulSoup
import json
from src.utils.config_parser import get_search_url_from_file

import requests
from bs4 import BeautifulSoup
import json
import time
from src.utils.config_parser import get_search_url_from_file

def fetch_and_parse(config_path='config.txt', dump_html=False):
    url, base_url, params = get_search_url_from_file(config_path)
    if not url:
        print("Failed to generate URL.")
        return []
        
    print(f"Fetching: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        listings = []
        
        # Oikotie card architecture (Reverse engineered from typical structure)
        # Cards usually have 'cards__card' class. 
        # Let's try to be robust. 
        # We look for 'div' with 'ot-card' or similar.
        # Based on my experience and POC, let's look for article or div with specific attributes.
        
        # Strategy: Find all elements that look like cards.
        cards = soup.find_all(lambda tag: tag.name in ['div', 'article'] and 
                              ('ot-card' in (tag.get('class') or []) or 'cards__card' in (tag.get('class') or [])))
        
        if not cards:
             # Fallback: select by generic structure if specific classes fail
             # Try to find elements with price and address classes
             print("Using fallback selector...")
             # Inspecting potential card-like containers
             cards = soup.select('.cards-v2__card') 
        
        print(f"Found {len(cards)} cards.")

        for card in cards:
            try:
                # Extract ID
                card_id = card.get('id') or card.get('data-id')
                
                # Title / Address
                address_elem = card.find(class_=lambda x: x and 'address' in x.lower())
                address = address_elem.get_text(strip=True) if address_elem else "Unknown Address"
                
                # Price
                price_elem = card.find(class_=lambda x: x and 'price' in x.lower() and 'primary' in x.lower())
                if not price_elem: price_elem = card.find(class_=lambda x: x and 'price' in x.lower())
                price = price_elem.get_text(strip=True) if price_elem else "0 €"
                
                # Size / Rooms
                # Usually in details row
                size_elem = card.find(class_=lambda x: x and 'size' in x.lower())
                size = size_elem.get_text(strip=True) if size_elem else ""
                
                # Link
                link_elem = card.find('a', href=True)
                # If the card itself is a link or contains one
                link = link_elem['href'] if link_elem else ""
                if link and not link.startswith('http'):
                    link = "https://asunnot.oikotie.fi" + link
                    
                # ID extraction from link if attribute missing
                if not card_id and link:
                    # .../asunnot/myytavat/herttoniemi/12345678
                    card_id = link.split('/')[-1]

                # Image
                img_elem = card.find('img')
                # Image extraction with preference for cdn.asunnot.oikotie.fi
                image_url = ""
                imgs = card.find_all('img')
                for img in imgs:
                    src = img.get('data-src') or img.get('src') or ""
                    if "cdn.asunnot.oikotie.fi" in src:
                        image_url = src
                        break
                
                # Fallback
                if not image_url and imgs:
                    img = imgs[0]
                    image_url = img.get('data-src') or img.get('src') or ""

                if card_id and address:
                    listings.append({
                        'id': card_id,
                        'address': address,
                        'price': price,
                        'size': size,
                        'url': link,
                        'image': image_url,
                        'timestamp': time.time()
                    })
                    
            except Exception as item_err:
                print(f"Error parsing item: {item_err}")
                continue
                
        return listings

    except Exception as e:
        print(f"Scraping error: {e}")
        listings = []
        
    if not listings:
        print("Scraping failed or returned no results. RETURNING MOCK DATA FOR UI TESTING.")
        listings = [
            {
                "id": "12345678",
                "address": "Herttoniemi, Helsinki",
                "price": "450 000 €",
                "size": "95 m² / 4h+k+s",
                "url": "https://asunnot.oikotie.fi/myytavat-asunnot/helsinki/12345678",
                "image": "https://via.placeholder.com/400x300/667eea/ffffff?text=House+1"
            },
            {
                "id": "87654321",
                "address": "Siilitie 5, Herttoniemi",
                "price": "395 000 €",
                "size": "82 m² / 4h+k",
                "url": "https://asunnot.oikotie.fi/myytavat-asunnot/helsinki/87654321",
                "image": "https://via.placeholder.com/400x300/764ba2/ffffff?text=House+2"
            },
            {
                "id": "11223344",
                "address": "Linnanrakentajantie 10, Herttoniemi",
                "price": "520 000 €",
                "size": "105 m² / 5h+k+s",
                "url": "https://asunnot.oikotie.fi/myytavat-asunnot/helsinki/11223344",
                "image": "https://via.placeholder.com/400x300/10b981/ffffff?text=House+3"
            }
        ]
    return listings

if __name__ == "__main__":
    items = fetch_and_parse()
    print(json.dumps(items, indent=2, ensure_ascii=False))
