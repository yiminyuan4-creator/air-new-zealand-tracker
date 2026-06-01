import os

ORIGIN = os.getenv("ORIGIN", "AKL")

ROUTES = [
    {"dept": ORIGIN, "arrv": "CSX", "name": "Changsha"},
    {"dept": ORIGIN, "arrv": "WLG", "name": "Wellington"},
    {"dept": ORIGIN, "arrv": "MEL", "name": "Melbourne"},
    {"dept": ORIGIN, "arrv": "SYD", "name": "Sydney"},
    {"dept": ORIGIN, "arrv": "NYC", "name": "New York"},
]

BOOKING_URL = "https://flightbookings.airnewzealand.co.nz/vbook/actions/ext-search"
DB_PATH = os.getenv("DB_PATH", "flights.db")
DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "7"))
TIMEOUT = int(os.getenv("TIMEOUT", "45"))
RETRIES = int(os.getenv("RETRIES", "2"))
HEADLESS = os.getenv("HEADLESS", "true").lower() != "false"
CURRENCY = os.getenv("CURRENCY", "NZD")
REQUEST_DELAY_MIN = float(os.getenv("REQUEST_DELAY_MIN", "20"))
REQUEST_DELAY_MAX = float(os.getenv("REQUEST_DELAY_MAX", "45"))
DEBUG_HTML = os.getenv("DEBUG_HTML", "false").lower() == "true"
