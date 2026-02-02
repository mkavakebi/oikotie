from finscraper.spiders import OikotieApartment
import pandas as pd
import logging

def test_finscraper():
    # Enable logging to see what's happening
    logging.basicConfig(level=logging.DEBUG)
    
    print("Init spider...")
    # Try filtering by area immediately
    spider = OikotieApartment(area="Herttoniemi").scrape(n=10)
    
    print("Scraping done.")
    print(f"Type of result: {type(spider)}")
    
    # Wait, does scrape return the DF or the spider?
    # Usually wrapper.scrape() returns the DF.
    # Let's inspect 'spider' variable which captures the result
    if isinstance(spider, pd.DataFrame):
        print(f"Rows: {len(spider)}")
        print(spider.head())
    else:
        print("Result is not a DataFrame:", spider)

if __name__ == "__main__":
    test_finscraper()
