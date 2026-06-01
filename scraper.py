import argparse
import logging
import random
import re
import time
from datetime import date as date_cls
from datetime import datetime, timedelta
from urllib.parse import urlencode

from config import (
    BOOKING_URL,
    CURRENCY,
    DEBUG_HTML,
    DAYS_AHEAD,
    HEADLESS,
    REQUEST_DELAY_MAX,
    REQUEST_DELAY_MIN,
    RETRIES,
    ROUTES,
    TIMEOUT,
)
from db import init_db, save_many

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)


PRICE_RE = re.compile(r'(?:NZD\s*\$?\s*|\$\s*)([0-9][0-9,]*(?:\.\d{2})?)', re.I)
TIME_RE = re.compile(r'\b([01]?\d|2[0-3]):([0-5]\d)\s*([AP]M)?\b', re.I)
FLIGHT_RE = re.compile(r'\b(?:NZ|Air\s*New\s*Zealand)\s?(\d{1,4})\b', re.I)
STOP_RE = re.compile(r'\b(\d+)\s+stop', re.I)
BLOCK_RE = re.compile(r'captcha|access denied|too many requests|blocked|robot|unusual traffic', re.I)


class BlockedError(RuntimeError):
    pass


class Scraper:
    def __init__(self):
        init_db()
        self.driver = self._setup_browser()

    def _setup_browser(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        opts = Options()
        if HEADLESS:
            opts.add_argument('--headless=new')
        opts.page_load_strategy = 'eager'
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--window-size=1440,1800')
        opts.add_argument(
            'user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/124 Safari/537.36 AirNZPriceTracker/1.0'
        )
        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(TIMEOUT)
        return driver

    def _build_url(self, dept, arrv, departure_date):
        dt = datetime.strptime(departure_date, '%Y-%m-%d')
        params = {
            'adults': '1',
            'bookingClass': 'ECONOMY',
            'depart-from': dept,
            'depart-to': arrv,
            'doSearch': 'search',
            'internalRevenueSource': 'github flight tracker',
            'searchLegs[0].originPoint': dept,
            'searchLegs[0].destinationPoint': arrv,
            'searchLegs[0].tripStartDate': str(dt.day),
            'searchLegs[0].tripStartMonth': dt.strftime('%b').upper(),
            'searchType': 'flexible',
            'tripType': 'oneway',
        }
        return f'{BOOKING_URL}?{urlencode(params)}'

    def search(self, dept, arrv, date):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        source_url = self._build_url(dept, arrv, date)
        for attempt in range(RETRIES):
            try:
                log.info(f"Search: {dept}->{arrv} {date} (attempt {attempt+1})")
                self.driver.get(source_url)
                WebDriverWait(self.driver, TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                self._wait_for_results()
                scrape_ts = datetime.now().isoformat(timespec='seconds')
                flights = self._parse(dept, arrv, date, source_url, scrape_ts)
                save_many(flights)
                log.info(f"Found {len(flights)} flights")
                return flights
            except BlockedError:
                raise
            except Exception as e:
                log.exception(f"Error searching {dept}->{arrv} {date}: {e}")
                if attempt == RETRIES - 1:
                    return []
                self._sleep(backoff=attempt + 1)
        return []

    def _wait_for_results(self):
        end = time.time() + TIMEOUT
        while time.time() < end:
            text = self.driver.find_element("tag name", "body").text
            lowered = text.lower()
            if BLOCK_RE.search(lowered):
                raise BlockedError('Air NZ returned a bot/limit page; stopping to protect the IP.')
            if 'session expired' in lowered:
                raise RuntimeError('Air NZ session expired before results loaded')
            if PRICE_RE.search(text) and TIME_RE.search(text):
                return
            if 'no flights' in lowered or 'unable to find' in lowered:
                return
            time.sleep(1)

    def _parse(self, dept, arrv, departure_date, source_url, scrape_ts):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        flights = self._parse_airnz_leg_options(soup, dept, arrv, departure_date, source_url, scrape_ts)
        if flights:
            return flights

        cards = self._candidate_cards(soup)
        flights = []
        seen = set()

        for card in cards:
            flight = self._parse_card(card.get_text(' ', strip=True), dept, arrv, departure_date, source_url, scrape_ts)
            if not flight:
                continue
            key = (flight['date'], flight['time'], flight.get('flight_number'), flight['price'])
            if key in seen:
                continue
            seen.add(key)
            flights.append(flight)

        if not flights:
            log.warning("No parseable flights on %s", source_url)
            if DEBUG_HTML:
                self._save_debug_html(dept, arrv, departure_date)
        return flights

    def _parse_airnz_leg_options(self, soup, dept, arrv, departure_date, source_url, scrape_ts):
        flights = []
        for option in soup.select('[data-automation="leg-option"]'):
            departure = self._text(option, '[data-automation="leg-option-departure-time"]')
            arrival = self._text(option, '[data-automation="leg-option-arrival-time"]')
            duration = self._text(option, '[data-automation="leg-option-duration"]')
            flight_count = self._text(option, '[data-automation="leg-option-flight-count"]')
            flight_number = option.get('data-automation-flight-numbers')

            prices = []
            for cost in option.select('[data-automation^="leg-option-cost-"]'):
                price = self._extract_price(cost.get_text(' ', strip=True))
                if price is not None:
                    prices.append(price)
            if not prices:
                prices = [p for p in [self._extract_price(option.get_text(' ', strip=True))] if p is not None]

            departure_time = self._normalise_time(departure)
            if not departure_time or not prices:
                continue

            flights.append({
                'dept': dept,
                'arrv': arrv,
                'date': departure_date,
                'time': departure_time,
                'arrival_time': self._normalise_time(arrival),
                'flight_number': self._normalise_flight_number(flight_number),
                'price': min(prices),
                'currency': CURRENCY,
                'duration': self._normalise_duration(duration),
                'stops': self._stops_from_flight_count(flight_count),
                'airline': 'Air NZ',
                'source_url': source_url,
                'scrape_ts': scrape_ts,
            })
        return flights

    def _text(self, element, selector):
        found = element.select_one(selector)
        return ' '.join(found.get_text(' ', strip=True).split()) if found else ''

    def _candidate_cards(self, soup):
        selectors = [
            '[data-testid*="flight"]',
            '[class*="flight"]',
            '[class*="fare"]',
            '[class*="itinerary"]',
            '[class*="journey"]',
            'li',
            'tr',
        ]
        cards = []
        for selector in selectors:
            cards.extend(soup.select(selector))
        if cards:
            return cards
        return [soup.body or soup]

    def _parse_card(self, text, dept, arrv, departure_date, source_url, scrape_ts):
        if not text or len(text) < 8:
            return None
        price = self._extract_price(text)
        times = self._extract_times(text)
        if price is None or not times:
            return None

        departure_time = times[0]
        arrival_time = times[1] if len(times) > 1 else None
        flight_match = FLIGHT_RE.search(text)
        stops_match = STOP_RE.search(text)

        return {
            'dept': dept,
            'arrv': arrv,
            'date': departure_date,
            'time': departure_time,
            'arrival_time': arrival_time,
            'flight_number': self._normalise_flight_number(f"NZ{flight_match.group(1)}" if flight_match else None),
            'price': price,
            'currency': CURRENCY,
            'duration': self._normalise_duration(self._extract_duration(text)),
            'stops': int(stops_match.group(1)) if stops_match else (0 if 'non-stop' in text.lower() or 'direct' in text.lower() else None),
            'airline': 'Air NZ',
            'source_url': source_url,
            'scrape_ts': scrape_ts,
        }

    def _extract_price(self, text):
        matches = PRICE_RE.findall(text)
        if not matches:
            return None
        prices = [float(m.replace(',', '')) for m in matches]
        plausible = [p for p in prices if 20 <= p <= 20000]
        return min(plausible) if plausible else None

    def _extract_times(self, text):
        times = []
        for match in TIME_RE.finditer(text):
            times.append(self._normalise_time(match.group(0)))
        return [t for t in times if t]

    def _normalise_time(self, text):
        match = TIME_RE.search(text or '')
        if not match:
            return None
        hour = int(match.group(1))
        minute = int(match.group(2))
        marker = (match.group(3) or '').upper()
        if marker == 'PM' and hour != 12:
            hour += 12
        elif marker == 'AM' and hour == 12:
            hour = 0
        return f'{hour:02d}:{minute:02d}'

    def _normalise_flight_number(self, value):
        if not value:
            return None
        match = FLIGHT_RE.search(value)
        if match:
            return f"NZ{int(match.group(1)):04d}"
        return value.strip()

    def _extract_duration(self, text):
        match = re.search(r'\b(\d{1,2}\s*h(?:ours?)?\s*(?:\d{1,2}\s*m(?:in(?:utes?)?)?)?)\b', text, re.I)
        return match.group(1) if match else None

    def _normalise_duration(self, text):
        if not text:
            return None
        value = text.replace('hours', 'h').replace('hour', 'h').replace('minutes', 'm').replace('minute', 'm')
        value = re.sub(r'\s+', ' ', value).strip()
        return re.sub(r'(\d)\s+([hm])\b', r'\1\2', value)

    def _stops_from_flight_count(self, text):
        match = re.search(r'\b(\d+)\s+flights?\b', text or '', re.I)
        return max(int(match.group(1)) - 1, 0) if match else None

    def _sleep(self, backoff=1):
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX) * backoff
        log.info("Waiting %.1fs before the next Air NZ request", delay)
        time.sleep(delay)

    def _save_debug_html(self, dept, arrv, departure_date):
        filename = f"debug_{dept}_{arrv}_{departure_date}.html"
        with open(filename, "w", encoding="utf-8") as fh:
            fh.write(self.driver.page_source)
        log.info("Saved debug HTML to %s", filename)

    def run(self, days=7, routes=None, dates=None):
        routes = routes or ROUTES
        dates = dates or [
            (date_cls.today() + timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range(1, days + 1)
        ]
        total = 0
        jobs = [
            (r['dept'], r['arrv'], departure_date)
            for departure_date in dates
            for r in routes
        ]
        for index, (dept, arrv, departure_date) in enumerate(jobs, start=1):
            total += len(self.search(dept, arrv, departure_date))
            if index < len(jobs):
                self._sleep()
        log.info("Saved %s flight price records", total)
        return total

    def close(self):
        if getattr(self, 'driver', None):
            self.driver.quit()


def parse_args():
    parser = argparse.ArgumentParser(description='Scrape Air NZ flight prices into SQLite.')
    parser.add_argument('--days', type=int, default=DAYS_AHEAD, help='Number of future departure days to scrape.')
    parser.add_argument(
        '--date',
        action='append',
        metavar='YYYY-MM-DD',
        help='Scrape one exact departure date. Can be passed more than once.',
    )
    parser.add_argument(
        '--route',
        action='append',
        metavar='AKL:WLG',
        help='Limit scraping to one route. Can be passed more than once.',
    )
    return parser.parse_args()


def selected_routes(route_args):
    if not route_args:
        return ROUTES
    routes = []
    for route in route_args:
        try:
            dept, arrv = route.upper().split(':', 1)
        except ValueError as exc:
            raise SystemExit(f"Invalid --route value {route!r}; use AKL:WLG.") from exc
        routes.append({'dept': dept, 'arrv': arrv})
    return routes


def selected_dates(date_args):
    if not date_args:
        return None
    dates = []
    for value in date_args:
        try:
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError as exc:
            raise SystemExit(f"Invalid --date value {value!r}; use YYYY-MM-DD.") from exc
        dates.append(value)
    return dates


if __name__ == "__main__":
    args = parse_args()
    s = Scraper()
    try:
        total = s.run(days=args.days, routes=selected_routes(args.route), dates=selected_dates(args.date))
        if total == 0:
            raise SystemExit("No flight prices were saved; Air NZ markup or search availability may have changed.")
    finally:
        s.close()
