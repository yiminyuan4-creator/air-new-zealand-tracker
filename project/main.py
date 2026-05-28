#!/usr/bin/env python3
import os
import sqlite3
import time
import random
import requests
from datetime import datetime, timedelta
from typing import List, Dict

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

class AirNewZealandApiClient:
    def __init__(self):
        self.scraped_at = datetime.now().isoformat()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-NZ,en;q=0.9',
            'Origin': 'https://www.airnewzealand.co.nz',
            'Referer': 'https://www.airnewzealand.co.nz/'
        }

    def fetch_prices(self, departure: str, arrival: str, date_str: str) -> List[Dict]:
        flights = []
        api_url = "https://www.airnewzealand.co.nz/api/v1/fare-search/search"
        
        payload = {
            "product": "RETAIL",
            "searchType": "ONEWAY",
            "segments": [{
                "origin": departure,
                "destination": arrival,
                "departureDate": date_str
            }],
            "passengers": [{"type": "ADULT", "count": 1}],
            "cabinClass": "ECONOMY",
            "loyaltyProgram": "AIRPOINTS"
        }
        
        try:
            response = requests.post(api_url, json=payload, headers=self.headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'outbound' in data and 'journeys' in data['outbound']:
                    for journey in data['outbound']['journeys']:
                        price_struct = journey.get('price', {})
                        price = price_struct.get('amount')
                        if price is None:
                            continue
                            
                        segments = journey.get('segments', [])
                        f_num = "-".join([seg.get('flightNumber', '') for seg in segments if seg.get('flightNumber')])
                        if not f_num: 
                            f_num = f"NZ-联运-{departure}-{arrival}"
                            
                        flights.append({
                            'flight_number': f_num,
                            'departure_code': departure,
                            'arrival_code': arrival,
                            'departure_date': date_str,
                            'price': float(price),
                            'currency': price_struct.get('currencyCode', 'NZD'),
                            'cabin_class': 'ECONOMY',
                            'scraped_at': self.scraped_at
                        })
        except Exception:
            pass
        return flights

def main():
    db = FlightDatabase(DATABASE)
    client = AirNewZealandApiClient()
    
    for departure, arrival in ROUTES:
        for days_ahead in range(1, SCRAPE_DAYS + 1):
            target_date = (datetime.now() + timedelta(days=days_ahead)).date()
            date_str = str(target_date)
            
            flights = client.fetch_prices(departure, arrival, date_str)
            for flight in flights:
                db.insert_flight(flight)
                
            time.sleep(random.uniform(1.5, 3.5))
            
    return 0

if __name__ == '__main__':
    exit(main())
