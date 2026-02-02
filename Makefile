VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

.PHONY: run scrape install clean help

# Check if venv exists, otherwise fallback to system python
ifeq ($(wildcard $(VENV)),)
    PYTHON = python3
    PIP = pip3
endif

help:
	@echo "Available commands:"
	@echo "  make run      - Start the Flask dashboard on port 5001"
	@echo "  make scrape   - Run the scraper manually to update listings"
	@echo "  make cleanup  - Remove listings that are out of bounds"
	@echo "  make install  - Install dependencies from requirements.txt"
	@echo "  make clean    - Remove python cache files"
	@echo "  make purge    - Remove ALL listings and history (DANGER)"

run:
	$(PYTHON) app.py

scrape:
	$(PYTHON) src/scrapers/scraper_selenium.py

cleanup:
	$(PYTHON) scripts/cleanup_locations.py

install:
	$(PIP) install -r requirements.txt

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

purge:
	rm -rf data/listings/*.json
	rm -rf data/history/*.json
	rm -f data/price_changes.json
	rm -f data/metadata.json
