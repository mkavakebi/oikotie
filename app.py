from flask import Flask, render_template, request, redirect, url_for
from src.utils.storage import (get_all_listings, save_listing, get_dashboard_stats, 
                     set_last_update, get_last_update, cleanup_listings,
                     mark_visited, mark_removed, mark_favorite)
from src.scrapers.scraper_selenium import fetch_with_selenium, verify_listings
import threading
import time

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

@app.template_filter('datetimeformat')
def datetimeformat(value):
    if value is None:
        return "Never"
    return value # We handle the actual formatting in JS as well, but this makes it safe for Jinja

@app.route('/')
def index():
    listings = get_all_listings()
    stats = get_dashboard_stats()
    # Sort listings: active first, then sold. Within that, newest first.
    # False < True, so sorting by 'sold' puts False (Active) first.
    listings.sort(key=lambda x: (x.get('sold', False), -x.get('timestamp', 0)))
    
    last_update = get_last_update()
    return render_template('index.html', listings=listings, stats=stats, last_update=last_update, now=time.time())

@app.route('/refresh')
def refresh():
    # 1. Fetch new items from search
    new_items = fetch_with_selenium()
    found_ids = set()
    
    if new_items:
        for item in new_items:
            save_listing(item)
            found_ids.add(item['id'])
            
    # 2. Check for missing items (potentially sold/removed)

    
    all_local = get_all_listings()
    missing_items = []
    
    for item in all_local:
        if item['id'] not in found_ids and not item.get('sold'):
            missing_items.append(item)
            
    if missing_items:
        print(f"Found {len(missing_items)} missing items. Verifying status...")
        verified_items = verify_listings(missing_items)
        for item in verified_items:
            save_listing(item)
            
    # 3. Cleanup any items that are now out of bounds (config might have changed)
    removed_count, removed_ids = cleanup_listings()
    if removed_count > 0:
        print(f"Cleaned up {removed_count} out-of-bounds listings: {removed_ids}")
            
    set_last_update()
    return redirect(url_for('index'))

@app.route('/visited/<lid>', methods=['POST'])
def toggle_visited(lid):
    data = request.get_json()
    visited = data.get('visited', True)
    success = mark_visited(lid, visited)
    return {'success': success}

@app.route('/remove/<lid>', methods=['POST'])
def remove_listing(lid):
    success = mark_removed(lid, True)
    return {'success': success}

@app.route('/favorite/<lid>', methods=['POST'])
def toggle_favorite(lid):
    data = request.get_json()
    favorite = data.get('favorite', True)
    success = mark_favorite(lid, favorite)
    return {'success': success}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
