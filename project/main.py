#!/usr/bin/env python3
import os
import sys
import sqlite3
import json
import time
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    os.system(f"{sys.executable} -m pip install playwright")
    os.system(f"{sys.executable} -m playwright install chromium")
    from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ROUTES = [('AKL', 'CSX'), ('CSX', 'AKL')]
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
                UNIQUE(flight_number, departure_date, scraped_at, cabin_class)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_query ON flights(departure_code, arrival_code, departure_date, scraped_at)')
        conn.commit()
        conn.close()
    
    def insert_flight(self, flight_data: Dict) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO flights 
                (flight_number, departure_code, arrival_code, departure_date, 
                 departure_time, arrival_time, duration, price, currency, cabin_class, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                flight_data['flight_number'], flight_data['departure_code'], flight_data['arrival_code'],
                flight_data['departure_date'], flight_data.get('departure_time'), flight_data.get('arrival_time'),
                flight_data.get('duration'), flight_data['price'], flight_data.get('currency', 'NZD'),
                flight_data.get('cabin_class', 'ECONOMY'), flight_data['scraped_at']
            ))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception:
            return False

class ApiFlightScraper:
    def __init__(self):
        self.scraped_at = datetime.now().isoformat()

    def scrape_via_api(self, departure: str, arrival: str, date_str: str) -> List[Dict]:
        flights = []
        url = f"https://www.airnewzealand.co.nz/flights/en-nz/{departure}-to-{arrival}?v=1&outboundDate={date_str}&searchType=oneway&adults=1"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            def handle_response(response):
                if "api/v1/fare-search" in response.url or "v2/search" in response.url:
                    try:
                        data = response.json()
                        if 'outbound' in data and 'journeys' in data['outbound']:
                            for journey in data['outbound']['journeys']:
                                price = journey.get('price', {}).get('amount')
                                if not price: continue
                                
                                f_num = "-".join([seg.get('flightNumber', '') for seg in journey.get('segments', [])])
                                if not f_num: f_num = f"NZ-联运-{departure}-{arrival}"
                                
                                flights.append({
                                    'flight_number': f_num,
                                    'departure_code': departure,
                                    'arrival_code': arrival,
                                    'departure_date': date_str,
                                    'price': float(price),
                                    'currency': journey.get('price', {}).get('currencyCode', 'NZD'),
                                    'cabin_class': 'ECONOMY',
                                    'scraped_at': self.scraped_at
                                })
                    except Exception:
                        pass

            page.on("response", handle_response)
            
            try:
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            finally:
                browser.close()
                
        return flights

def main():
    db = FlightDatabase(DATABASE)
    scraper = ApiFlightScraper()
    inserted_count = 0
    
    for departure, arrival in ROUTES:
        for days_ahead in range(1, 8):
            target_date = (datetime.now() + timedelta(days=days_ahead)).date()
            date_str = str(target_date)
            
            flights = scraper.scrape_via_api(departure, arrival, date_str)
            for flight in flights:
                if db.insert_flight(flight):
                    inserted_count += 1
            time.sleep(random.uniform(3, 6))
            
    return 0

if __name__ == '__main__':
    exit(main())
