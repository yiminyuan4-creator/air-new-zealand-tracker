"""
Configuration file for Air New Zealand Flight Price Scraper
Edit this file to customize the scraper behavior
"""

# Database configuration
DATABASE_PATH = 'flights.db'

# Flight routes to scrape
# Format: (departure_code, arrival_code)
FLIGHT_ROUTES = [
    ('AKL', 'WLG'),
    ('AKL', 'SYD'),
    ('AKL', 'CSX'),
    ('AKL', 'JFK'),
    ('WLG', 'AKL'),
    ('WLG', 'SYD'),
    ('WLG', 'CSX'),
    ('WLG', 'JFK'),
    ('SYD', 'AKL'),
    ('SYD', 'WLG'),
    ('SYD', 'CSX'),
    ('SYD', 'JFK'),
    ('CSX', 'AKL'),
    ('CSX', 'WLG'),
    ('CSX', 'SYD'),
    ('CSX', 'JFK'),
    ('JFK', 'AKL'),
    ('JFK', 'WLG'),
    ('JFK', 'SYD'),
    ('JFK', 'CSX'),
]

# Scraping configuration
SCRAPE_DAYS = 365  # Number of days into the future to scrape
CABIN_CLASS = 'ECONOMY'  # Default cabin class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
CURRENCY = 'NZD'  # Currency code

# Logging configuration
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Request configuration
REQUEST_TIMEOUT = 30  # seconds
REQUEST_RETRIES = 3
REQUEST_RETRY_DELAY = 5  # seconds

# Base prices for mock data (when using demo scraper)
DOMESTIC_BASE_PRICE = 250.0  # NZD
INTERNATIONAL_BASE_PRICE = 800.0  # NZD

# Analysis configuration
ANALYSIS_LOOKBACK_DAYS = 90  # Days to include in trend analysis
PRICE_ALERT_THRESHOLD = 0.10  # Alert if price drops more than 10%

# Airport codes
AIRPORT_CODES = {
    'AKL': 'Auckland, New Zealand',
    'WLG': 'Wellington, New Zealand',
    'SYD': 'Sydney, Australia',
    'CSX': 'Changsha, China',
    'JFK': 'New York, USA',
}
