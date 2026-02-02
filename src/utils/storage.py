import json
import os
import glob
from datetime import datetime
import time

DATA_DIR = 'data'
LISTINGS_DIR = os.path.join(DATA_DIR, 'listings')
HISTORY_DIR = os.path.join(DATA_DIR, 'history')
METADATA_PATH = os.path.join(DATA_DIR, 'metadata.json')
CHANGES_LOG_PATH = os.path.join(DATA_DIR, 'price_changes.json')


def set_last_update():
    """Saves the current timestamp as the last update time."""
    data = {'last_update': time.time()}
    with open(METADATA_PATH, 'w') as f:
        json.dump(data, f)

def get_last_update():
    """Returns the last update timestamp."""
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, 'r') as f:
                data = json.load(f)
                return data.get('last_update')
        except:
            pass
    return None

def save_listing(listing):
    """Saves the current listing state and updates history."""
    lid = listing['id']
    listing_path = os.path.join(LISTINGS_DIR, f"{lid}.json")
    history_path = os.path.join(HISTORY_DIR, f"{lid}_history.json")
    
    # 1. Load existing listing to check for changes
    old_listing = None
    if os.path.exists(listing_path):
        with open(listing_path, 'r') as f:
            old_listing = json.load(f)
            
    # 2. Save current listing (overwrite with latest data)
    with open(listing_path, 'w') as f:
        json.dump(listing, f, indent=2, ensure_ascii=False)
        
    # 3. Update history if price changed or it's new
    timestamp = datetime.now().isoformat()
    entry = {
        'timestamp': timestamp,
        'price': listing.get('price'),
        'image': listing.get('image'), # Keep track if image changes
        'open_house': listing.get('open_house'), # Track if open house added
        'price_per_sqm': listing.get('price_per_sqm'),
        'maintenance_fee': listing.get('maintenance_fee')
    }
    
    history = []
    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            history = json.load(f)
            
    # Only append if something meaningful changed or it's the first entry
    is_new = not history
    price_changed = bool(history and history[-1]['price'] != entry['price'])
    open_house_changed = bool(history and history[-1].get('open_house') != entry['open_house'])

    if is_new or price_changed or open_house_changed:
        history.append(entry)
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
            
        # Log to consolidated price changes file if price changed
        if price_changed and len(history) >= 2:
            # Calculate price difference
            def parse_price(price_str):
                if not price_str or price_str == "N/A":
                    return 0.0
                try:
                    return float(price_str.replace('€', '').replace(' ', '').replace(',', '.').strip())
                except:
                    return 0.0
            
            old_price_val = parse_price(history[-2]['price'])
            new_price_val = parse_price(entry['price'])
            price_diff = new_price_val - old_price_val
            price_diff_pct = (price_diff / old_price_val * 100) if old_price_val > 0 else 0
            
            change_entry = {
                'id': lid,
                'address': listing.get('address'),
                'old_price': history[-2]['price'],
                'new_price': entry['price'],
                'price_difference': f"{price_diff:,.0f} €",
                'price_difference_pct': f"{price_diff_pct:.1f}%",
                'size': listing.get('size'),
                'price_per_sqm': listing.get('price_per_sqm'),
                'timestamp': timestamp,
                'url': listing.get('url')
            }
            
            changes = []
            if os.path.exists(CHANGES_LOG_PATH):
                try:
                    with open(CHANGES_LOG_PATH, 'r') as cf:
                        changes = json.load(cf)
                except:
                    pass
            
            changes.append(change_entry)
            with open(CHANGES_LOG_PATH, 'w') as cf:
                json.dump(changes, cf, indent=2, ensure_ascii=False)
    
    # 4. Detect if this listing has had a price drop (current < first recorded)
    if len(history) >= 2:
        def parse_price(price_str):
            if not price_str or price_str == "N/A":
                return 0.0
            try:
                return float(price_str.replace('€', '').replace(' ', '').replace(',', '.').strip())
            except:
                return 0.0
        
        first_price = parse_price(history[0]['price'])
        current_price = parse_price(listing.get('price', 'N/A'))
        
        listing['price_drop'] = (current_price < first_price and current_price > 0 and first_price > 0)
    else:
        listing['price_drop'] = False
    
    # Re-save listing with price_drop flag
    with open(listing_path, 'w') as f:
        json.dump(listing, f, indent=2, ensure_ascii=False)

def get_dashboard_stats():
    """Calculates statistics for the dashboard."""
    stats = {
        'total': 0,
        'new_this_week': 0,
        'price_drops': 0,
        'open_houses': 0
    }
    
    if not os.path.exists(LISTINGS_DIR):
        return stats
        
    files = [f for f in os.listdir(LISTINGS_DIR) if f.endswith('.json')]
    
    now = time.time()
    week_seconds = 7 * 24 * 60 * 60
    
    actual_listings = []
    for filename in files:
        file_path = os.path.join(LISTINGS_DIR, filename)
        try:
            with open(file_path, 'r') as f:
                listing = json.load(f)
                # Ignore soft-deleted listings
                if listing.get('removed'):
                    continue
                actual_listings.append(listing)
                
            stats['total'] += 1
                
            # Check if new this week (using first history entry timestamp)
            lid = listing['id']
            history_path = os.path.join(HISTORY_DIR, f"{lid}_history.json")
            
            if os.path.exists(history_path):
                try:
                    with open(history_path, 'r') as hf:
                        history = json.load(hf)
                        if history and len(history) > 0:
                            # Parse first entry timestamp
                            first_timestamp_str = history[0].get('timestamp')
                            if first_timestamp_str:
                                first_dt = datetime.fromisoformat(first_timestamp_str)
                                first_timestamp = first_dt.timestamp()
                                
                                if now - first_timestamp < week_seconds:
                                    stats['new_this_week'] += 1
                except:
                    pass
                
            # Check open house - only count if not sold and has a truthy value
            if listing.get('open_house') and not listing.get('sold', False):
                # Optional: Filter out past open houses if the string contains a date
                oh_str = listing.get('open_house')
                is_upcoming = True
                try:
                    import re
                    # Look for date patterns like 18.01.
                    match = re.search(r'(\d{1,2})\.(\d{1,2})\.', oh_str)
                    if match:
                        day = int(match.group(1))
                        month = int(match.group(2))
                        now_dt = datetime.now()
                        year = now_dt.year
                        if now_dt.month == 12 and month == 1: year += 1
                        elif now_dt.month == 1 and month == 12: year -= 1
                        
                        # Set to end of day
                        oh_date = datetime(year, month, day, 23, 59)
                        if oh_date < now_dt:
                            is_upcoming = False
                except:
                    pass
                
                if is_upcoming and not listing.get('visited'):
                    stats['open_houses'] += 1
                
            # Check price drops using history
            lid = listing['id']
            history_path = os.path.join(HISTORY_DIR, f"{lid}_history.json")
            if os.path.exists(history_path):
                with open(history_path, 'r') as hf:
                    history = json.load(hf)
                    if len(history) > 1:
                        # Simple check: compare first recorded price with current
                        # Or checking if ANY drop happened. Let's check if current is lower than first
                        try:
                             first_price = float(history[0]['price'].replace('€', '').replace(' ', '').replace(',', '.').strip()) if history[0]['price'] != 'N/A' else 0
                             current_price = float(listing['price'].replace('€', '').replace(' ', '').replace(',', '.').strip()) if listing['price'] != 'N/A' else 0
                             if first_price > current_price and current_price > 0:
                                 stats['price_drops'] += 1
                        except:
                            pass
                            
        except Exception as e:
            print(f"Error processing stats for {filename}: {e}")
            
    return stats

def get_all_listings():
    """Returns a list of all current listing objects."""
    files = glob.glob(os.path.join(LISTINGS_DIR, "*.json"))
    listings = []
    for fpath in files:
        try:
            with open(fpath, 'r') as f:
                listing = json.load(f)
                if not listing.get('removed'):
                    listings.append(listing)
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
    return listings

def mark_visited(lid, visited=True):
    """Marks a listing as visited."""
    listing_path = os.path.join(LISTINGS_DIR, f"{lid}.json")
    if os.path.exists(listing_path):
        with open(listing_path, 'r') as f:
            listing = json.load(f)
        listing['visited'] = visited
        with open(listing_path, 'w') as f:
            json.dump(listing, f, indent=2, ensure_ascii=False)
        return True
    return False

def mark_removed(lid, removed=True):
    """Marks a listing as removed (soft delete)."""
    listing_path = os.path.join(LISTINGS_DIR, f"{lid}.json")
    if os.path.exists(listing_path):
        with open(listing_path, 'r') as f:
            listing = json.load(f)
        listing['removed'] = removed
        with open(listing_path, 'w') as f:
            json.dump(listing, f, indent=2, ensure_ascii=False)
        return True
    return False

def mark_favorite(lid, favorite=True):
    """Marks a listing as favorite."""
    listing_path = os.path.join(LISTINGS_DIR, f"{lid}.json")
    if os.path.exists(listing_path):
        with open(listing_path, 'r') as f:
            listing = json.load(f)
        listing['favorite'] = favorite
        with open(listing_path, 'w') as f:
            json.dump(listing, f, indent=2, ensure_ascii=False)
        return True
    return False

def get_history(lid):
    history_path = os.path.join(HISTORY_DIR, f"{lid}_history.json")
    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            return json.load(f)
    return []

def cleanup_listings():
    """Removes listings that are out of bounds according to the config."""
    from src.utils.config_parser import get_search_url_from_file, get_allowed_locations
    
    url, base_url, params = get_search_url_from_file('config.txt')
    allowed_locations = get_allowed_locations(params)
    
    if not allowed_locations:
        return 0, []

    listings = get_all_listings()
    removed_ids = []
    
    for listing in listings:
        address = listing.get('address', '').lower()
        match_found = False
        for loc in allowed_locations:
            if loc.lower() in address:
                match_found = True
                break
        
        if not match_found:
            lid = listing['id']
            # Delete listing file
            fpath = os.path.join(LISTINGS_DIR, f"{lid}.json")
            if os.path.exists(fpath):
                os.remove(fpath)
            
            # Delete history file
            hpath = os.path.join(HISTORY_DIR, f"{lid}_history.json")
            if os.path.exists(hpath):
                os.remove(hpath)
            
            removed_ids.append(lid)
            
    return len(removed_ids), removed_ids
