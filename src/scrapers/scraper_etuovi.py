from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

geolocator = Nominatim(user_agent="oikotie_tracker")

def parse_to_float(s):
    """Helper to extract numbers from Finnish formatted strings"""
    if not s or s == "N/A": return 0.0
    try:
        cleaned = s.replace('€', '').replace('m²', '').replace(' ', '').replace(',', '.').strip()
        return float(cleaned)
    except:
        return 0.0

def fetch_from_etuovi():
    """
    Fetches listings from Etuovi.fi for Herttoniemi, Herttoniemenranta, and Kulosaari.
    Returns a list of listings in the same format as Oikotie scraper.
    """
    
    # Build search URLs for each area
    # Etuovi uses different URL structure - we'll need to test and adjust
    base_urls = [
        "https://www.etuovi.com/myytavat-asunnot/helsinki/herttoniemi",
        "https://www.etuovi.com/myytavat-asunnot/helsinki/herttoniemenranta",
        "https://www.etuovi.com/myytavat-asunnot/helsinki/kulosaari"
    ]
    
    # Add filters: 4-7 rooms, max 600k
    # Note: Etuovi URL parameters may differ from Oikotie
    # This will need adjustment based on actual Etuovi URL structure
    
    print(f"Starting Etuovi fetch...")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        all_results = []
        seen_ids = set()
        
        for base_url in base_urls:
            print(f"\nFetching from: {base_url}")
            driver.get(base_url)
            time.sleep(3)  # Wait for page load
            
            # Try to find listing cards
            # Note: Etuovi uses different CSS selectors than Oikotie
            # Common patterns: .ListPage-item, .card, article, etc.
            selectors_to_try = [
                ".ListPage-item",
                ".search-result",
                "article",
                "[data-test-id='listing-card']",
                ".card"
            ]
            
            cards = []
            for selector in selectors_to_try:
                try:
                    found = driver.find_elements(By.CSS_SELECTOR, selector)
                    if found:
                        cards = found
                        print(f"Found {len(cards)} cards with selector: {selector}")
                        break
                except:
                    continue
            
            if not cards:
                print(f"No cards found for {base_url}")
                continue
            
            # Extract data from each card
            for idx, card in enumerate(cards):
                try:
                    # Get link
                    link_elem = card.find_element(By.TAG_NAME, "a")
                    link = link_elem.get_attribute("href") if link_elem else ""
                    
                    if not link:
                        continue
                    
                    # Extract ID from URL
                    # Etuovi URLs typically: https://www.etuovi.com/kohde/12345678
                    card_id = link.split('/')[-1] if link else f"etuovi_{idx}"
                    
                    if card_id in seen_ids:
                        continue
                    seen_ids.add(card_id)
                    
                    # Get card text
                    text = card.text
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    # Extract address (usually first meaningful line)
                    address = lines[0] if lines else "Unknown Address"
                    
                    # Extract price
                    price = "N/A"
                    for line in lines:
                        if '€' in line and 'm²' not in line:
                            price = line
                            break
                    
                    # Extract size
                    size = "N/A"
                    for line in lines:
                        if 'm²' in line and '€' not in line:
                            size = line
                            break
                    
                    # Extract rooms
                    rooms = "N/A"
                    for line in lines:
                        if 'h' in line.lower() and any(char.isdigit() for char in line):
                            rooms = line
                            break
                    
                    # Try to get image
                    image_url = ""
                    try:
                        img = card.find_element(By.TAG_NAME, "img")
                        image_url = img.get_attribute("src")
                    except:
                        pass
                    
                    # Calculate price per sqm
                    price_val = parse_to_float(price)
                    size_val = parse_to_float(size)
                    price_per_sqm = "N/A"
                    if price_val > 0 and size_val > 0:
                        calculated = price_val / size_val
                        price_per_sqm = f"{calculated:,.2f} €/m²".replace(',', ' ').replace('.', ',')
                    
                    # Geocode address
                    latitude = None
                    longitude = None
                    try:
                        location = geolocator.geocode(address, country_codes='fi', timeout=10)
                        if location:
                            latitude = location.latitude
                            longitude = location.longitude
                    except:
                        pass
                    
                    listing = {
                        'id': f"etuovi_{card_id}",  # Prefix to distinguish from Oikotie
                        'address': address,
                        'price': price,
                        'size': size,
                        'rooms': rooms,
                        'url': link,
                        'image': image_url,
                        'price_per_sqm': price_per_sqm,
                        'maintenance_fee': "N/A",  # Usually not on search cards
                        'open_house': "",
                        'latitude': latitude,
                        'longitude': longitude,
                        'sold': False,
                        'source': 'etuovi',
                        'timestamp': time.time()
                    }
                    
                    all_results.append(listing)
                    
                except Exception as e:
                    print(f"Error parsing card {idx}: {e}")
                    continue
        
        print(f"\nEtuovi fetch complete. Found {len(all_results)} listings.")
        return all_results
        
    except Exception as e:
        print(f"Etuovi scraping error: {e}")
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    listings = fetch_from_etuovi()
    print(f"\nTotal Etuovi listings: {len(listings)}")
    for listing in listings[:3]:  # Print first 3 as sample
        print(f"  - {listing['address']}: {listing['price']}")
