import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from src.scrapers.scraper_selenium import process_detail_page
from src.utils.storage import save_listing, LISTINGS_DIR

def bulk_update():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)
    
    files = [f for f in os.listdir(LISTINGS_DIR) if f.endswith('.json')]
    print(f"Found {len(files)} listings to process.")
    
    for i, filename in enumerate(files):
        file_path = os.path.join(LISTINGS_DIR, filename)
        with open(file_path, 'r') as f:
            listing = json.load(f)
        
        # Only update if N/A or missing
        if listing.get('toilets') == "N/A" or 'toilets' not in listing:
            print(f"[{i+1}/{len(files)}] Updating {listing['id']}...")
            try:
                process_detail_page(driver, listing)
                save_listing(listing)
                # Small sleep to be nice
                time.sleep(1)
            except Exception as e:
                print(f"Error updating {listing['id']}: {e}")
        else:
            print(f"[{i+1}/{len(files)}] {listing['id']} already has toilet info: {listing['toilets']}")

    driver.quit()

if __name__ == "__main__":
    bulk_update()
