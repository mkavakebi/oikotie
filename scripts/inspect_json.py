import json
import re

def inspect_json():
    with open("debug_page.html", "r") as f:
        content = f.read()
        
    # Look for var otAsunnot = {...};
    match = re.search(r'var otAsunnot\s*=\s*({.+?});', content)
    if match:
        json_str = match.group(1)
        try:
            data = json.loads(json_str)
            print("Keys in otAsunnot:", data.keys())
            if 'cards' in data:
                print(f"Found {len(data['cards'])} cards in JSON.")
            else:
                print("No 'cards' key found.")
                # recursive search for 'cards'
                def find_key(obj, key):
                   if key in obj: return obj[key]
                   for k, v in obj.items():
                       if isinstance(v, dict):
                           item = find_key(v, key)
                           if item: return item
                   return None
                   
                cards = find_key(data, 'cards')
                if cards:
                    print(f"Found cards deep in JSON: {len(cards)}")
                else:
                    print("Could not find 'cards' anywhere.")
                    
        except Exception as e:
            print(f"Error parsing JSON: {e}")
    else:
        print("Could not find otAsunnot variable.")

if __name__ == "__main__":
    inspect_json()
