# Oikotie Property Tracker

A tool to track real estate listings on Oikotie.fi. It scrapes search results, enriches them with details (high-res images, maintenance fees, toilet counts), geocodes addresses, and tracks price changes over time.

## Features

- **Automated Scraping**: Uses Selenium to scrape search results from Oikotie.fi.
- **Data Enrichment**: Visits individual listing pages to extract more detailed information.
- **Geolocation**: Automatically geocodes addresses to display on a map (integrated in dashboard).
- **Price Tracking**: Keeps a history of price changes for each listing.
- **Dashboard**: A Flask-based web interface to view results, statistics, and trigger updates.

## Prerequisites

- **Python 3.x**
- **Google Chrome**: Needed for Selenium headless mode.
- **ChromeDriver**: Ensure you have a compatible ChromeDriver installed and in your PATH (Selenium 4.x may manage this automatically).

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd oikotie
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    # OR
    make install
    ```

## Configuration

The scraper uses `config.txt` to determine what to search for.

1.  Open `config.txt`.
2.  Paste the full Oikotie search URL you want to track.
    - Example: `https://asunnot.oikotie.fi/myytavat-asunnot?cardType=100&price%5Bmax%5D=600000...`

## Usage

### 1. Run the Dashboard
The dashboard is the main interface for the project.

```bash
python app.py
# OR
make run
```
- The dashboard will be available at `http://localhost:5001`.
- Click the **Refresh** button on the dashboard to trigger a new scrape.

### 2. Run the Scraper Standalone
If you want to run the scraper without the web interface:

```bash
python3 src/scrapers/scraper_selenium.py
# OR
make scrape
```
- Scraped data is stored as JSON files in the `data/` directory.

### 3. Cleanup and Maintenance

If you find that some listings from outside your preferred areas are showing up (which can happen if Oikotie includes "Nearby" results), you can clean them up:

- **Via Dashboard**: The **Refresh** process automatically runs a cleanup based on your `config.txt` filters.
- **Via Command Line**: Run `make cleanup` to remove any listings that don't match your current configuration.
- **Resetting Data**: If you want to start fresh, run `make purge`. **Warning**: This deletes all collected data and history.

## Project Structure

- `app.py`: Flask web application.
- `src/scrapers/`: Core scraper scripts.
- `src/utils/`: Common utility modules (storage, config).
- `src/analytics/`: Data processing scripts.
- `scripts/`: Maintenance and cleanup scripts.
- `data/`: Directory where all listings and history are stored.
- `templates/`: HTML templates for the dashboard.
- `static/`: Static assets (CSS/JS) for the dashboard.

## Development

- To modify the geocoding logic, see `src/scrapers/scraper_selenium.py`.
- To adjust how data is stored, see `src/utils/storage.py`.
- To tweak the dashboard UI, edit `templates/index.html`.
