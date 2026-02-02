import json
import os
from src.utils.storage import LISTINGS_DIR, HISTORY_DIR, CHANGES_LOG_PATH, set_last_update

def generate_price_analytics():
    """Generates a summary of price analytics across all listings."""
    
    analytics = {
        'total_listings': 0,
        'listings_with_price_drops': 0,
        'listings_with_price_increases': 0,
        'total_price_changes': 0,
        'average_price_drop': 0,
        'average_price_increase': 0,
        'biggest_drops': [],
        'biggest_increases': [],
        'most_volatile': []
    }
    
    if not os.path.exists(LISTINGS_DIR):
        return analytics
    
    # Analyze all listings
    all_drops = []
    all_increases = []
    volatility_map = {}  # id -> number of changes
    
    for filename in os.listdir(LISTINGS_DIR):
        if not filename.endswith('.json'):
            continue
            
        analytics['total_listings'] += 1
        listing_id = filename.replace('.json', '')
        
        # Load listing
        with open(os.path.join(LISTINGS_DIR, filename), 'r') as f:
            listing = json.load(f)
        
        # Check for price drop flag
        if listing.get('price_drop'):
            analytics['listings_with_price_drops'] += 1
        
        # Load history to analyze changes
        history_path = os.path.join(HISTORY_DIR, f"{listing_id}_history.json")
        if not os.path.exists(history_path):
            continue
            
        with open(history_path, 'r') as f:
            history = json.load(f)
        
        if len(history) < 2:
            continue
        
        # Count total changes for this listing
        price_changes = 0
        for i in range(1, len(history)):
            if history[i]['price'] != history[i-1]['price']:
                price_changes += 1
        
        volatility_map[listing_id] = {
            'address': listing.get('address'),
            'changes': price_changes,
            'url': listing.get('url')
        }
        
        # Compare first and current price
        def parse_price(price_str):
            if not price_str or price_str == "N/A":
                return 0.0
            try:
                return float(price_str.replace('€', '').replace(' ', '').replace(',', '.').strip())
            except:
                return 0.0
        
        first_price = parse_price(history[0]['price'])
        current_price = parse_price(history[-1]['price'])
        
        if first_price > 0 and current_price > 0:
            diff = current_price - first_price
            diff_pct = (diff / first_price) * 100
            
            entry = {
                'id': listing_id,
                'address': listing.get('address'),
                'first_price': history[0]['price'],
                'current_price': history[-1]['price'],
                'difference': f"{diff:,.0f} €",
                'difference_pct': f"{diff_pct:.1f}%",
                'url': listing.get('url')
            }
            
            if diff < 0:
                all_drops.append((abs(diff), entry))
            elif diff > 0:
                all_increases.append((diff, entry))
                analytics['listings_with_price_increases'] += 1
    
    # Load price changes log
    if os.path.exists(CHANGES_LOG_PATH):
        with open(CHANGES_LOG_PATH, 'r') as f:
            changes = json.load(f)
            analytics['total_price_changes'] = len(changes)
    
    # Calculate averages
    if all_drops:
        analytics['average_price_drop'] = f"{sum(d[0] for d in all_drops) / len(all_drops):,.0f} €"
        # Sort and get top 5 biggest drops
        all_drops.sort(reverse=True)
        analytics['biggest_drops'] = [entry for _, entry in all_drops[:5]]
    
    if all_increases:
        analytics['average_price_increase'] = f"{sum(d[0] for d in all_increases) / len(all_increases):,.0f} €"
        # Sort and get top 5 biggest increases
        all_increases.sort(reverse=True)
        analytics['biggest_increases'] = [entry for _, entry in all_increases[:5]]
    
    # Get most volatile listings (top 5 by number of changes)
    volatile_list = sorted(volatility_map.items(), key=lambda x: x[1]['changes'], reverse=True)
    analytics['most_volatile'] = [
        {
            'id': lid,
            'address': data['address'],
            'num_changes': data['changes'],
            'url': data['url']
        }
        for lid, data in volatile_list[:5] if data['changes'] > 1
    ]
    
    return analytics

if __name__ == "__main__":
    analytics = generate_price_analytics()
    
    # Save to file
    output_path = 'data/price_analytics.json'
    with open(output_path, 'w') as f:
        json.dump(analytics, f, indent=2, ensure_ascii=False)
    
    set_last_update()
    print(f"Price analytics saved to {output_path}")
    print(f"Total listings: {analytics['total_listings']}")
    print(f"Listings with price drops: {analytics['listings_with_price_drops']}")
    print(f"Total price changes: {analytics['total_price_changes']}")
