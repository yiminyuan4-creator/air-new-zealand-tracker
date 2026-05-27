#!/usr/bin/env python3
"""
New Zealand Airways Flight Price Scraper
Automatically scrapes flight prices and stores in SQLite database with timestamps
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import requests
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flight routes configuration
ROUTES = [
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

DATABASE = 'flights.db'
SCRAPE_DAYS = 365  # Scrape 365 days into the future


class FlightDatabase:
    """Manages SQLite database operations for flight data"""
    
    def __init__(self, db_path: str = DATABASE):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with flights table if it doesn't exist"""
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
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_route_date_scraped 
            ON flights(departure_code, arrival_code, departure_date, scraped_at)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_departure_date 
            ON flights(departure_date)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_flight_number 
            ON flights(flight_number)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def insert_flight(self, flight_data: Dict) -> bool:
        """Insert flight data into database, ignoring duplicates"""
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
            logger.error(f"Error inserting flight data: {e}")
            return False
    
    def get_flight_price_history(self, flight_number: str, departure_date: str) -> List[Tuple]:
        """Get price history for a specific flight and departure date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT scraped_at, price, currency, cabin_class
            FROM flights
            WHERE flight_number = ? AND departure_date = ?
            ORDER BY scraped_at ASC
        ''', (flight_number, departure_date))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_route_prices_by_date(self, departure_code: str, arrival_code: str, 
                                 scraped_at_date: str) -> List[Tuple]:
        """Get all flights for a route with prices on a specific scrape date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT departure_date, flight_number, price, currency
            FROM flights
            WHERE departure_code = ? AND arrival_code = ? 
                AND DATE(scraped_at) = ?
            ORDER BY departure_date ASC, price ASC
        ''', (departure_code, arrival_code, scraped_at_date))
        
        results = cursor.fetchall()
        conn.close()
        return results


class FlightScraper:
    """Scrapes flight prices from Air New Zealand (Demo/Mock implementation)"""
    
    def __init__(self):
        self.scraped_at = datetime.now().isoformat()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def generate_mock_flights(self, departure: str, arrival: str, 
                            days_ahead: int) -> List[Dict]:
        """
        Generate mock flight data for demonstration
        In production, this would scrape actual data from Air New Zealand API/website
        """
        flights = []
        departure_date = (datetime.now() + timedelta(days=days_ahead)).date()
        
        # Generate 2-4 flights per day for each route
        num_flights = random.randint(2, 4)
        
        for i in range(num_flights):
            flight_number = f'NZ{random.randint(100, 999)}'
            departure_hour = random.randint(6, 22)
            departure_time = f'{departure_hour:02d}:{random.randint(0, 59):02d}'
            
            # Price varies based on route distance and demand
            base_price = self._calculate_base_price(departure, arrival)
            price = base_price + random.uniform(-100, 200)
            
            flights.append({
                'flight_number': flight_number,
                'departure_code': departure,
                'arrival_code': arrival,
                'departure_date': str(departure_date),
                'departure_time': departure_time,
                'arrival_time': f'{(departure_hour + random.randint(2, 15)) % 24:02d}:{random.randint(0, 59):02d}',
                'duration': f'{random.randint(2, 16)}h {random.randint(0, 59):02d}m',
                'price': round(max(price, 100), 2),
                'currency': 'NZD',
                'cabin_class': 'ECONOMY',
                'scraped_at': self.scraped_at
            })
        
        return flights
    
    def _calculate_base_price(self, departure: str, arrival: str) -> float:
        """Calculate base price based on route"""
        # Mock pricing: domestic vs international
        domestic_routes = {('AKL', 'WLG'), ('WLG', 'AKL'), ('AKL', 'SYD'), ('SYD', 'AKL'), 
                          ('WLG', 'SYD'), ('SYD', 'WLG')}
        
        if (departure, arrival) in domestic_routes:
            return 250.0  # Domestic base price
        return 800.0  # International base price
    
    def scrape_all_routes(self) -> List[Dict]:
        """Scrape flights for all routes and dates"""
        all_flights = []
        
        logger.info(f"Starting scrape at {self.scraped_at}")
        logger.info(f"Scraping {len(ROUTES)} routes for {SCRAPE_DAYS} days")
        
        for departure, arrival in ROUTES:
            logger.info(f"Scraping route {departure} -> {arrival}")
            
            for days_ahead in range(SCRAPE_DAYS):
                try:
                    flights = self.generate_mock_flights(departure, arrival, days_ahead)
                    all_flights.extend(flights)
                except Exception as e:
                    logger.error(f"Error scraping {departure}->{arrival} for day {days_ahead}: {e}")
                    continue
            
            logger.info(f"Completed {departure} -> {arrival}")
        
        logger.info(f"Scraped total {len(all_flights)} flights")
        return all_flights


def main():
    """Main execution function"""
    try:
        # Initialize database
        db = FlightDatabase(DATABASE)
        
        # Scrape flights
        scraper = FlightScraper()
        flights = scraper.scrape_all_routes()
        
        # Store in database
        inserted_count = 0
        for flight in flights:
            if db.insert_flight(flight):
                inserted_count += 1
        
        logger.info(f"Successfully inserted {inserted_count} new flight records")
        logger.info(f"Scrape completed at {datetime.now().isoformat()}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Fatal error in scraper: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())
