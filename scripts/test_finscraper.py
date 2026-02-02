from finscraper.spiders import OikotieApartment
import pandas as pd

def test_finscraper():
    # Initialize spider
    # It seems to verify if it works without arguments first
    try:
        spider = OikotieApartment()
        print("Spider initialized.")
        
        # scrape() usually takes 'limit' or specific filters.
        # Let's try to pass our scraped URL parameters if possible, or see what arguments 'scrape' takes.
        # But first, a simple blind scrape to check functionality.
        df = spider.scrape(n=10)
        print(f"Scraped {len(df)} items.")
        print(df.head())
        print(df.columns)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_finscraper()
