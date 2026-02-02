import re
import json
import requests

def parse_config(config_str):
    """
    Parses a natural language configuration string into Oikotie search parameters.
    Returns a BASE_URL and a dictionary of query parameters.
    """
    config_str = config_str.lower()
    
    # Base URL for "selling" vs "renting"
    base_url = "https://asunnot.oikotie.fi/myytavat-asunnot" # Default to selling
    card_type = 100 # 100 = sale, 101 = rent
    
    if "rent" in config_str or "renting" in config_str or "vuokra" in config_str:
        base_url = "https://asunnot.oikotie.fi/vuokrattavat-asunnot"
        card_type = 101
    
    params = {}
    
    # Location logic - Look for words after "on", "in", "at"
    # Basic heuristic: find "on X area" or "in X"
    location_match = re.search(r'(?:on|in|at)\s+(.+?)\s+(?:area|district|region)', config_str)
    if not location_match:
         location_match = re.search(r'(?:on|in|at)\s+(\w+)', config_str)
         
    if location_match:
        location = location_match.group(1).strip()
        # Use 'text' parameter for free-text location search which works well
        params['text'] = location
        
    # Room logic
    # "at least X rooms" -> 4,5,6,7,8,9
    # "X rooms" -> X
    rooms = []
    min_rooms_match = re.search(r'at least (\d+)\s*rooms?', config_str)
    exact_rooms_match = re.search(r'(\d+)\s*rooms?', config_str)
    
    if min_rooms_match:
        min_rooms = int(min_rooms_match.group(1))
        # Oikotie allows 1 to ~9. Let's add up to 9.
        for r in range(min_rooms, 10):
            rooms.append(r)
    elif exact_rooms_match:
        rooms.append(int(exact_rooms_match.group(1)))
        
    if rooms:
        params['roomCount[]'] = rooms

    # House Type logic
    # "house" -> omakotitalo (type[]=1), rivitalo (type[]=2), paritalo (type[]=4) ?
    # "apartment" -> kerrostalo (type[]=3)
    # If generic "houses" mentioned, usually implies landed property but can be generic.
    # Let's try to map common types.
    # Oikotie mapping (approximate):
    # 1 = Omakotitalo (Detached house)
    # 2 = Rivitalo (Row house)
    # 3 = Kerrostalo (Apartment block)
    # 4 = Paritalo (Semi-detached)
    # 32 = Erillistalo (Detached house in housing co-op)
    # Let's map "houses" to multiple types to be safe, or just leave empty for 'all'.
    # User said "houses", could mean Omakotitalo/Paritalo/Rivitalo.
    building_types = []
    if "house" in config_str or "houses" in config_str:
        building_types.extend([1, 2, 4, 32]) # Common "house" types
    elif "apartment" in config_str or "flat" in config_str:
        building_types.append(3)
        
    if building_types:
        params['buildingType[]'] = building_types

    return base_url, params

def get_search_url_from_file(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip()
        
        # Check if the content is already a full URL
        if content.startswith('http://') or content.startswith('https://'):
            # Parse the URL to extract base and params
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(content)
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Convert query string to params dict
            params = {}
            query_params = parse_qs(parsed.query)
            for key, value in query_params.items():
                # If only one value, unwrap from list
                if len(value) == 1:
                    params[key] = value[0]
                else:
                    params[key] = value
            
            return content, base_url, params
        else:
            # Parse as natural language
            base_url, params = parse_config(content)
            
            # Construct full URL for debugging/reference
            req = requests.Request('GET', base_url, params=params)
            prepped = req.prepare()
            return prepped.url, base_url, params
    except Exception as e:
        print(f"Error parsing config: {e}")
        return None, None, None

def get_allowed_locations(params):
    """
    Extracts a list of allowed location names from params.
    Returns None if no specific location filter is found (meaning all locations allowed).
    """
    locations = []
    
    # 1. Check 'locations' param (JSON list)
    if params and 'locations' in params:
        val = params['locations']
        # If it's a string representation of a list, parse it
        if isinstance(val, str) and val.strip().startswith('['):
            try:
                data = json.loads(val)
                # data is like [[1681, 4, "Herttoniemi, Helsinki"], ...]
                for item in data:
                    if len(item) >= 3:
                        name = item[2]
                        # "Herttoniemi, Helsinki" -> "Herttoniemi"
                        simple_name = name.split(',')[0].strip()
                        locations.append(simple_name)
            except:
                pass
    
    # 2. Check 'text' param (free text search)
    if params and 'text' in params:
        locations.append(params['text'])
        
    return locations if locations else None
