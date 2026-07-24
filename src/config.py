import os

ORIGIN = os.getenv("ORIGIN", "AKL")

CITY_NAMES = {
    "AKL": "Auckland",
    "CSX": "Changsha",
    "WLG": "Wellington",
    "MEL": "Melbourne",
    "SYD": "Sydney",
    "NYC": "New York",
}

ROUTES = [
    {"dept": ORIGIN, "arrv": code, "name": CITY_NAMES[code]}
    for code in ("CSX", "WLG", "MEL", "SYD", "NYC")
]

BOOKING_URL = "https://flightbookings.airnewzealand.co.nz/vbook/actions/ext-search"
DB_PATH = os.getenv("DB_PATH", "flights.db")
DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "30"))
START_DAYS_AHEAD = int(os.getenv("START_DAYS_AHEAD", "3"))
MAX_SEARCHES_PER_RUN = int(os.getenv("MAX_SEARCHES_PER_RUN", "50"))
TIMEOUT = int(os.getenv("TIMEOUT", "45"))
RETRIES = int(os.getenv("RETRIES", "3"))
HEADLESS = os.getenv("HEADLESS", "true").lower() != "false"
CHROME_BINARY = os.getenv("CHROME_BINARY")
CURRENCY = os.getenv("CURRENCY", "NZD")
REQUEST_DELAY_MIN = float(os.getenv("REQUEST_DELAY_MIN", "20"))
REQUEST_DELAY_MAX = float(os.getenv("REQUEST_DELAY_MAX", "45"))
DEBUG_HTML = os.getenv("DEBUG_HTML", "false").lower() == "true"
