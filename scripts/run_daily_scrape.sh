#!/bin/bash

# Daily Oikotie Scraper Script
# This script runs the scraper to refresh property listings

# Change to project directory
cd /Users/morteza.kavakebi/PycharmProjects/oikotie

# Activate virtual environment
source venv/bin/activate
export PYTHONPATH="/Users/morteza.kavakebi/PycharmProjects/oikotie"

# Run the scraper
python3 src/scrapers/scraper_selenium.py

# Optional: Generate analytics after scraping
python3 src/analytics/generate_analytics.py

# Send Telegram summary
python3 src/utils/telegram_notifier.py

# Log completion
echo "$(date): Daily scrape completed" >> /Users/morteza.kavakebi/PycharmProjects/oikotie/data/scrape.log
