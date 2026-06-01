"""
Configuration file for Air New Zealand Flight Tracker
"""

# Route configuration
ROUTES = [
    # From Auckland to:
    {"departure": "AKL", "arrival": "CSX", "departure_name": "Auckland", "arrival_name": "Changsha"},
    {"departure": "AKL", "arrival": "SYD", "departure_name": "Auckland", "arrival_name": "Sydney"},
    {"departure": "AKL", "arrival": "WLG", "departure_name": "Auckland", "arrival_name": "Wellington"},
    {"departure": "AKL", "arrival": "NYC", "departure_name": "Auckland", "arrival_name": "New York"},
    {"departure": "AKL", "arrival": "MEL", "departure_name": "Auckland", "arrival_name": "Melbourne"},
]

# Air New Zealand website
AIR_NZ_URL = "https://www.airnewzealand.co.nz"
SEARCH_ENDPOINT = "/booking/flights"

# Scraper settings
HEADLESS_BROWSER = True
BROWSER_TIMEOUT = 30  # seconds
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

# Data storage
DATA_OUTPUT_DIR = "data"
CSV_OUTPUT_FILE = "flight_data.csv"
JSON_OUTPUT_FILE = "flight_data.json"

# Logging
LOG_DIR = "logs"
LOG_FILE = "flight_scraper.log"
LOG_LEVEL = "INFO"

# Scheduling
SCRAPE_INTERVAL_HOURS = 6  # Run scraper every 6 hours