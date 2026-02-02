from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.utils.config_parser import get_search_url_from_file, get_allowed_locations
from src.utils.storage import get_all_listings, LISTINGS_DIR, set_last_update
import time
import os
import json
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

geolocator = Nominatim(user_agent="oikotie_tracker")

def parse_to_float(s):
    """Helper to extract numbers from Finnish formatted strings (e.g., '468 000 €' or '75,5 m²')"""
    if not s or s == "N/A": return 0.0
    try:
        # Remove spaces, €, m², then replace comma with dot
        cleaned = s.replace('€', '').replace('m²', '').replace(' ', '').replace(',', '.').strip()
        return float(cleaned)
    except:
        return 0.0

def fetch_with_selenium():
    url, base_url, params = get_search_url_from_file('config.txt')
    allowed_locations = get_allowed_locations(params)
    
    if not url:
        print("Invalid config")
        return []

    print(f"Starting fetch from: {url}")

    options = Options()
    options.add_argument("--headless=new") # Modern headless mode
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    
    try:
        all_results = []
        seen_ids = set()
        
        # --- PHASE 1: Collect Listings from Search Page(s) ---
        page = 1
        max_pages = 5 # Safety limit
        
        while page <= max_pages:
            sep = '&' if '?' in url else '?'
            current_url = f"{url}{sep}pagination={page}"
            print(f"\n[Page {page}] Loading URL: {current_url}")
            
            driver.get(current_url)
            
            # Cookie banner handling (only on page 1)
            if page == 1:
                try:
                    print("Looking for cookie iframe...")
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    cookie_iframe = None
                    for ifr in iframes:
                        src = ifr.get_attribute("src")
                        if src and "cmpv2" in src:
                            cookie_iframe = ifr
                            break
                    
                    if cookie_iframe:
                        driver.switch_to.frame(cookie_iframe)
                        accept_btn = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Hyväksy kaikki')]"))
                        )
                        try:
                            accept_btn.click()
                        except:
                            driver.execute_script("arguments[0].click();", accept_btn)
                        driver.switch_to.default_content()
                        time.sleep(2)
                except Exception as e:
                    print(f"Cookie banner error (skipping): {e}")
                    driver.switch_to.default_content()

            print(f"Waiting for cards on page {page}...")
            selectors_to_try = [".cards__card", ".ot-card", "[data-test-id='card']", "article[class*='card']", "div[class*='card']"]
            cards_loaded = False
            for selector in selectors_to_try:
                try:
                    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    cards_loaded = True
                    break
                except:
                    continue
            
            if not cards_loaded:
                print(f"No cards found on page {page}. Ending search.")
                break
            
            # Extract basic info from cards on this page
            cards_elems = []
            for selector in selectors_to_try:
                found = driver.find_elements(By.CSS_SELECTOR, selector)
                if found:
                    cards_elems = found
                    break
            
            print(f"Found {len(cards_elems)} cards on page {page}.")
            
            page_listings_count = 0
            for idx, card in enumerate(cards_elems):
                try:
                    href_elems = card.find_elements(By.TAG_NAME, "a")
                    link = href_elems[0].get_attribute("href") if href_elems else ""
                    
                    if not link or 'myytavat-asunnot' not in link:
                        continue
                    
                    card_id = link.split('/')[-1] if link else f"card_{idx}"
                    if card_id in seen_ids:
                        continue
                    seen_ids.add(card_id)
                    page_listings_count += 1
                    
                    text = card.text
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    # Skip promotional labels like "Plus" or "Uusi" if they are at the top
                    address = "Unknown Address"
                    skip_labels = ["Plus", "Uusi", "Uutuus", "Nostettu", "Samankaltaisia asuntoja lähialueilta"]
                    for line in lines:
                        if line not in skip_labels:
                            address = line
                            break
                    
                    if "Samankaltaisia" in address:
                        continue
                        
                    # Filter by allowed locations (if configured)
                    # This prevents picking up "Nearby" or generic ad listings
                    if allowed_locations:
                        # address format: "Street, Area, City"
                        # allowed_locations format: ["Herttoniemi", "Kulosaari"]
                        # Check if any allowed location is in the address
                        # Case insensitive check
                        addr_lower = address.lower()
                        match_found = False
                        for loc in allowed_locations:
                            if loc.lower() in addr_lower:
                                match_found = True
                                break
                        
                        if not match_found:
                            print(f"Skipping {card_id} (Address '{address}' not in allowed locations)")
                            continue
                    
                    # Basic price extraction (fallback)
                    price = "N/A"
                    for line in lines:
                        if '€' in line and '/m²' not in line:
                            price = line
                            break
                    
                    # Size extraction
                    size = "N/A"
                    for line in lines:
                        if 'm²' in line and '€/m²' not in line:
                            size = line
                            break
                    
                    # 1. Open House extraction from badges
                    open_house = ""
                    try:
                        badge_elems = card.find_elements(By.CSS_SELECTOR, ".card-badges badge, .ot-card__badge, [class*='badge']")
                        for b in badge_elems:
                            b_text = b.text.strip()
                            if 'Esittely' in b_text or 'Ensi-esittely' in b_text:
                                open_house = b_text
                                break
                    except:
                        pass

                    # 2. Image extraction from card (using picture tag as requested)
                    image_url = ""
                    try:
                        # Try to find the picture tag first
                        picture = card.find_element(By.TAG_NAME, "picture")
                        img_elem = picture.find_element(By.TAG_NAME, "img")
                        image_url = img_elem.get_attribute("src")
                    except:
                        try:
                            # Fallback to any img tag if picture is missing
                            img_elem = card.find_element(By.TAG_NAME, "img")
                            image_url = img_elem.get_attribute("src")
                        except:
                            pass

                    # 3. Calculate Price per Sqm locally
                    price_val = parse_to_float(price)
                    size_val = parse_to_float(size)
                    price_per_sqm = "N/A"
                    if price_val > 0 and size_val > 0:
                        calculated = price_val / size_val
                        # Finnish friendly formatting: space for thousands, comma for decimal
                        price_per_sqm = f"{calculated:,.2f} €/m²".replace(',', ' ').replace('.', ',')

                    all_results.append({
                        'id': card_id,
                        'address': address,
                        'price': price,
                        'size': size,
                        'url': link,
                        'open_house': open_house,
                        'image': image_url, 
                        'price_per_sqm': price_per_sqm,
                        'maintenance_fee': "N/A",
                        'toilets': "N/A",
                        'latitude': None,
                        'longitude': None,
                        'sold': False,
                        'timestamp': time.time()
                    })
                except Exception as e:
                    print(f"Error parsing card {idx} on page {page}: {e}")
                    continue
            
            print(f"Added {page_listings_count} new listings from page {page}.")
            if page_listings_count == 0:
                print("No new listings on this page. Stopping pagination.")
                break
            page += 1

        # --- PHASE 2: Visit Detail Pages ---
        print(f"\nPhase 1 Complete. Found {len(all_results)} listings total across {page-1} pages.")
        
        all_local = get_all_listings()
        local_data_map = {str(item['id']): item for item in all_local}
        
        final_results = []
        to_fetch_details = []

        for listing in all_results:
            lid = str(listing['id'])
            existing = local_data_map.get(lid)
            
            needs_update = True
            if existing:
                # Compare critical info from card vs stored
                price_match = existing.get('price') == listing['price']
                # Relaxed open house matching: if card says "Esittely" and we have a specific date, it's a match
                oh_match = (existing.get('open_house') == listing['open_house'])
                if not oh_match and listing['open_house'] in ["Esittely", "Ensi-esittely"] and existing.get('open_house'):
                    oh_match = True
                
                has_fee = existing.get('maintenance_fee') and existing.get('maintenance_fee') != "N/A"
                has_coords = existing.get('latitude') is not None and existing.get('longitude') is not None
                
                if price_match and oh_match and has_fee and has_coords:
                    needs_update = False
                    # Merge existing enriched data into our results
                    listing.update({
                        'maintenance_fee': existing.get('maintenance_fee', "N/A"),
                        'toilets': existing.get('toilets', "N/A"),
                        'latitude': existing.get('latitude'),
                        'longitude': existing.get('longitude'),
                        'sold': existing.get('sold', False),
                        'timestamp': existing.get('timestamp', listing['timestamp'])
                    })
                    # Keep high-res image if we already have it
                    if existing.get('image') and existing['image'].startswith('http') and 'galleria' in existing['image']:
                         listing['image'] = existing['image']
                         
                    print(f"Skipping details for {lid} (Up to date with fee)")
                elif price_match and oh_match and not has_fee:
                    print(f"Update needed for {lid} (No maintenance fee stored yet)")
                else:
                    print(f"Update needed for {lid} (Price or Open House changed: '{existing.get('open_house')}' -> '{listing['open_house']}')")
            else:
                print(f"Update needed for {lid} (New listing)")

            if needs_update:
                if existing and 'timestamp' in existing:
                    listing['timestamp'] = existing['timestamp']
                to_fetch_details.append(listing)
            else:
                final_results.append(listing)

        if to_fetch_details:
            print(f"Phase 2: Visiting detail pages for {len(to_fetch_details)} listings...")
            for i, listing in enumerate(to_fetch_details):
                print(f"[{i+1}/{len(to_fetch_details)}] Fetching details for {listing['id']}...")
                process_detail_page(driver, listing)
                final_results.append(listing)
        else:
            print("Phase 2: All listings up to date. Skipping detail page visits.")

        print(f"Successfully processed {len(final_results)} listings.")
        return final_results
        
    except Exception as e:
        print(f"Selenium scraping error: {e}")
        return []
    finally:
        driver.quit()

def process_detail_page(driver, listing):
    """Visits the listing URL and enriches it with details."""
    try:
        driver.get(listing['url'])
        time.sleep(1.5) # Slight delay to be polite and let JS render
        
        # Check for sold/removed status
        try:
            page_text_lower = driver.find_element(By.TAG_NAME, "body").text.lower()
            if "kohde on poistunut" in page_text_lower or "myyty" in page_text_lower:
                listing['sold'] = True
                listing['open_house'] = "" # Clear open house if sold
        except:
            pass

        # 1. Extract High-Res Image from Galleria
        try:
            # Look for galleria stage
            stage = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "galleria-stage"))
            )
            img = stage.find_element(By.TAG_NAME, "img")
            src = img.get_attribute("src")
            if src:
                listing['image'] = src
        except:
            # Fallback on detail page: try generic large image or og:image
            try:
                og_img = driver.find_element(By.CSS_SELECTOR, "meta[property='og:image']")
                if og_img:
                        listing['image'] = og_img.get_attribute("content")
            except:
                pass
        
        # 2. Extract Details from Definition Lists (dl > dt, dd)
        try:
            dt_elems = driver.find_elements(By.TAG_NAME, "dt")
            for dt in dt_elems:
                try:
                    key = dt.get_attribute("textContent").strip().lower()
                    dd = dt.find_element(By.XPATH, "following-sibling::dd")
                    value = dd.get_attribute("textContent").strip()
                    
                    if "neliöhinta" in key:
                        listing['price_per_sqm'] = value
                    elif "hoitovastike" in key:
                        listing['maintenance_fee'] = value
                    elif "huoneiston kokoonpano" in key:
                        # Extract toilet info from the composition string
                        toilet_info = extract_toilet_from_text(value)
                        if toilet_info:
                            listing['toilets'] = toilet_info
                except:
                    continue
        except Exception as detail_err:
                print(f"Error extracting details table: {detail_err}")

        # 2.5 Extract from main description if not found yet
        if not listing.get('toilets') or listing['toilets'] == "N/A":
            try:
                desc_elem = driver.find_element(By.CSS_SELECTOR, ".paragraph--keep-formatting")
                if desc_elem:
                    toilet_info = extract_toilet_from_text(desc_elem.text)
                    if toilet_info:
                        listing['toilets'] = toilet_info
            except:
                pass

        # 3. Extract Open House Info from Detail Page
        try:
            scripts = driver.find_elements(By.CSS_SELECTOR, "script[type='application/ld+json']")
            oh_info = []
            for script in scripts:
                try:
                    inner_html = script.get_attribute('innerHTML')
                    data = json.loads(inner_html)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict) and item.get('@type') == 'Event':
                            name = item.get('name', '')
                            start = item.get('startDate', '')
                            if start:
                                try:
                                    dt_obj = datetime.fromisoformat(start.replace('Z', '+00:00'))
                                    oh_info.append(f"{dt_obj.strftime('%d.%m. klo %H:%M')}")
                                except:
                                    if name: oh_info.append(name)
                    if oh_info:
                        listing['open_house'] = ", ".join(oh_info)
                        break
                except:
                    continue

            if not listing.get('open_house'):
                viewing_elements = driver.find_elements(By.CSS_SELECTOR, "ul.public-viewings li.public-viewings__item")
                if viewing_elements:
                    viewings = []
                    for ve in viewing_elements:
                        try:
                            date_text = ve.find_element(By.TAG_NAME, "b").text.strip()
                            time_info = ve.find_element(By.CLASS_NAME, "public-viewings__item-content").text.strip()
                            viewings.append(f"{date_text} {time_info}")
                        except:
                            continue
                    if viewings:
                        listing['open_house'] = " | ".join(viewings)
        except Exception as oh_err:
            print(f"Error extracting open house info: {oh_err}")

        # 4. Geocode Address if not found in page
        if not listing.get('latitude') or not listing.get('longitude'):
            try:
                addr = listing['address']
                if '●' in addr:
                    addr = addr.split('●')[0].strip()
                
                location = geolocator.geocode(addr, country_codes='fi', timeout=10)
                if location:
                    listing['latitude'] = location.latitude
                    listing['longitude'] = location.longitude
                else:
                    if ',' in addr:
                        parts = addr.split(',')
                        city = parts[-1].strip()
                        street = parts[0].strip()
                        location = geolocator.geocode(f"{street}, {city}", country_codes='fi', timeout=10)
                        if location:
                            listing['latitude'] = location.latitude
                            listing['longitude'] = location.longitude
            except (GeocoderTimedOut, Exception) as geo_err:
                print(f"Geocoding error for {listing['address']}: {geo_err}")

    except Exception as e:
        print(f"Failed to load details for {listing['id']}: {e}")

def verify_listings(listings):
    """Verifies the status of specific listings by visiting their URLs."""
    if not listings:
        return []
        
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    print(f"Verifying {len(listings)} listings...")
    
    try:
        for i, listing in enumerate(listings):
            print(f"[{i+1}/{len(listings)}] Verifying {listing['id']}...")
            process_detail_page(driver, listing)
            # listing['timestamp'] = time.time()  # Removed to preserve original age
            
    except Exception as e:
        print(f"Verification error: {e}")
    finally:
        driver.quit()
        
    return listings

def extract_toilet_from_text(text):
    """Helper to extract toilet information from a Finnish text string."""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Check for "erillinen wc" (separate toilet)
    has_separate = "erillinen wc" in text_lower or "erill. wc" in text_lower
    
    # Check for multiple toilets
    # Patterns like "2 wc", "kaksi wc:tä", "3 x wc"
    import re
    multi_patterns = [
        r'(\d+)\s*(?:x|kpl)?\s*wc',
        r'(kaksi|kolme|neljä)\s*wc:tä',
        r'wc:itä\s*(\d+)',
    ]
    
    found_count = None
    for pattern in multi_patterns:
        match = re.search(pattern, text_lower)
        if match:
            found_count = match.group(1)
            # Convert text numbers to digits
            num_map = {"kaksi": "2", "kolme": "3", "neljä": "4"}
            found_count = num_map.get(found_count, found_count)
            break
            
    # If no explicit count like "2 wc", but "wc" mentioned multiple times
    if not found_count:
        wc_count = text_lower.count('wc')
        if wc_count >= 2:
            found_count = str(wc_count)

    if has_separate and found_count and int(found_count) > 1:
        return f"{found_count} WC (sis. erillinen WC)"
    elif has_separate:
        return "Erillinen WC"
    elif found_count:
        return f"{found_count} WC"
        
    return None

if __name__ == "__main__":
    listings = fetch_with_selenium()
    print(f"\nTotal listings: {len(listings)}")
    set_last_update()
    # Just print IDs to summary
    ids = [l['id'] for l in listings]
    print(f"Listing IDs: {ids}")
