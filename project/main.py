#!/usr/bin/env python3
import os
import sys
import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    os.system(f"{sys.executable} -m pip install playwright")
    os.system(f"{sys.executable} -m playwright install chromium")
    from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ROUTES = [
    ('AKL', 'CSX'),
    ('CSX', 'AKL')
]
DATABASE = 'flights.db'
SCRAPE_DAYS = 30

class FlightDatabase:
    def __init__(self, db_path: str = DATABASE):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_number TEXT NOT NULL,
                departure_code TEXT NOT NULL,
                arrival_code TEXT NOT NULL,
                departure_date TEXT NOT NULL,
                departure_time TEXT,
                arrival_time TEXT,
                duration TEXT,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'NZD',
                cabin_class TEXT DEFAULT 'ECONOMY',
                scraped_at TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(flight_number, departure_date, scraped_at, cabin_class)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_route_date_scraped ON flights(departure_code, arrival_code, departure_date, scraped_at)')
        conn.commit()
        conn.close()
    
    def insert_flight(self, flight_data: Dict) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO flights 
                (flight_number, departure_code, arrival_code, departure_date, 
                 departure_time, arrival_time, duration, price, currency, 
                 cabin_class, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                flight_data['flight_number'],
                flight_data['departure_code'],
                flight_data['arrival_code'],
                flight_data['departure_date'],
                flight_data.get('departure_time'),
                flight_data.get('arrival_time'),
                flight_data.get('duration'),
                flight_data['price'],
                flight_data.get('currency', 'NZD'),
                flight_data.get('cabin_class', 'ECONOMY'),
                flight_data['scraped_at']
            ))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"DB Error: {e}")
            return False

class RealFlightScraper:
    def __init__(self):
        self.scraped_at = datetime.now().isoformat()
        
    def scrape_real_prices(self, departure: str, arrival: str, date_str: str) -> List[Dict]:
        flights = []
        url = f"https://www.airnewzealand.co.nz/flights/en-nz/{departure}-to-{arrival}?v=1&outboundDate={date_str}&searchType=oneway&adults=1"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            try:
                page.goto(url, timeout=60000)
                page.wait_for_selector(".flight-card-container, .pricing-grid, .flight-option", timeout=30000)
                time.sleep(5)
                
                cards = page.query_selector_all(".flight-card-container, .flight-option")
                for card in cards:
                    try:
                        f_num_el = card.query_selector(".flight-number, .flight-code")
                        f_num = f_num_el.inner_text().strip() if f_num_el else f"NZ_联运_{departure}_{arrival}"
                        
                        price_el = card.query_selector(".price-amount, .amount, .formatted-price")
                        if not price_el:
                            continue
                        price_raw = price_el.inner_text().replace("$", "").replace(",", "").strip()
                        price = float(price_raw)
                        
                        dep_time_el = card.query_selector(".departure-time, .dep-time")
                        dep_time = dep_time_el.inner_text().strip() if dep_time_el else None
                        
                        arr_time_el = card.query_selector(".arrival-time, .arr-time")
                        arr_time = arr_time_el.inner_text().strip() if arr_time_el else None
                        
                        duration_el = card.query_selector(".duration, .flight-duration")
                        duration = duration_el.inner_text().strip() if duration_el else None
                        
                        flights.append({
                            'flight_number': f_num,
                            'departure_code': departure,
                            'arrival_code': arrival,
                            'departure_date': date_str,
                            'departure_time': dep_time,
                            'arrival_time': arr_time,
                            'duration': duration,
                            'price': price,
                            'currency': 'NZD',
                            'cabin_class': 'ECONOMY',
                            'scraped_at': self.scraped_at
                        })
                    except Exception:
                        continue
            except Exception as e:
                logger.error(f"Failed to load {departure}->{arrival} on {date_str}: {e}")
            finally:
                browser.close()
                
        return flights

def main():
    db = FlightDatabase(DATABASE)
    scraper = RealFlightScraper()
    inserted_count = 0
    
    for departure, arrival in ROUTES:
        for days_ahead in range(1, SCRAPE_DAYS + 1):
            target_date = (datetime.now() + timedelta(days=days_ahead)).date()
            date_str = str(target_date)
            
            logger.info(f"Fetching real assets for {departure} -> {arrival} on {date_str}")
            flights = scraper.scrape_real_prices(departure, arrival, date_str)
            
            for flight in flights:
                if db.insert_flight(flight):
                    inserted_count += 1
            time.sleep(random.uniform(2, 5) if 'random' in globals() else 3)
            
    logger.info(f"Pipeline finished. Inserted {inserted_count} real data entries.")
    return 0

if __name__ == '__main__':
    exit(main())
