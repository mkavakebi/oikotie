import os
import json
import glob
from src.utils.config_parser import get_search_url_from_file, get_allowed_locations

DATA_DIR = 'data'
LISTINGS_DIR = os.path.join(DATA_DIR, 'listings')
HISTORY_DIR = os.path.join(DATA_DIR, 'history')

def cleanup():
    # 1. Get allowed locations from config
    url, base_url, params = get_search_url_from_file('config.txt')
    allowed_locations = get_allowed_locations(params)
    
    if not allowed_locations:
        print("No location filters found in config.txt. Skipping cleanup.")
        return

    print(f"Allowed locations: {allowed_locations}")
    
    # 2. Iterate through all listings
    files = glob.glob(os.path.join(LISTINGS_DIR, "*.json"))
    removed_count = 0
    
    for fpath in files:
        try:
            with open(fpath, 'r') as f:
                listing = json.load(f)
            
            address = listing.get('address', '').lower()
            match_found = False
            for loc in allowed_locations:
                if loc.lower() in address:
                    match_found = True
                    break
            
            if not match_found:
                print(f"Removing {listing['id']}: {listing.get('address')} (Not in allowed locations)")
                
                # Delete listing file
                if os.path.exists(fpath):
                    os.remove(fpath)
                
                # Delete history file if exists
                lid = listing['id']
                hpath = os.path.join(HISTORY_DIR, f"{lid}_history.json")
                if os.path.exists(hpath):
                    os.remove(hpath)
                
                removed_count += 1
                
        except Exception as e:
            print(f"Error processing {fpath}: {e}")

    print(f"\nCleanup finished. Removed {removed_count} out-of-bounds listings.")

if __name__ == "__main__":
    cleanup()
