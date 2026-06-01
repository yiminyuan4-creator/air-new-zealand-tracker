"""
Air New Zealand Flight Data Scraper
Scrapes real flight data for multiple routes from Auckland
"""

import logging
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict
import csv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd

from config import (
    ROUTES, AIR_NZ_URL, SEARCH_ENDPOINT, HEADLESS_BROWSER,
    BROWSER_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY, DATA_OUTPUT_DIR,
    CSV_OUTPUT_FILE, JSON_OUTPUT_FILE, LOG_DIR, LOG_FILE, LOG_LEVEL
)

# Setup logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, LOG_FILE)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AirNZFlightScraper:
    """Scraper for Air New Zealand flight data"""
    
    def __init__(self):
        """Initialize the scraper"""
        self.driver = None
        self.flights_data = []
        self.setup_browser()
        os.makedirs(DATA_OUTPUT_DIR, exist_ok=True)
    
    def setup_browser(self):
        """Setup Selenium WebDriver"""
        try:
            options = webdriver.ChromeOptions()
            if HEADLESS_BROWSER:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(BROWSER_TIMEOUT)
            logger.info("Browser setup successful")
        except Exception as e:
            logger.error(f"Failed to setup browser: {e}")
            raise
    
    def search_flights(self, departure: str, arrival: str, departure_date: str = None) -> List[Dict]:
        """
        Search for flights on Air New Zealand website
        
        Args:
            departure: Departure airport code (e.g., 'AKL')
            arrival: Arrival airport code (e.g., 'SYD')
            departure_date: Date in format 'YYYY-MM-DD' (optional, defaults to tomorrow)
        
        Returns:
            List of flight dictionaries
        """
        if departure_date is None:
            departure_date = (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')
        else:
            # Convert YYYY-MM-DD to DD/MM/YYYY if needed
            if len(departure_date.split('/')) == 3:
                day, month, year = departure_date.split('/')
                departure_date = f"{day}/{month}/{year}"
            else:
                d = datetime.strptime(departure_date, '%Y-%m-%d')
                departure_date = d.strftime('%d/%m/%Y')
        
        flights = []
        
        for attempt in range(RETRY_ATTEMPTS):
            try:
                logger.info(f"Searching flights: {departure} -> {arrival} on {departure_date} (Attempt {attempt + 1})")
                
                # Navigate to Air NZ booking page
                search_url = f"{AIR_NZ_URL}{SEARCH_ENDPOINT}"
                self.driver.get(search_url)
                
                # Wait for page to load
                WebDriverWait(self.driver, BROWSER_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Fill departure airport
                self._fill_airport_field("departure", departure)
                
                # Fill arrival airport
                self._fill_airport_field("arrival", arrival)
                
                # Fill departure date
                self._fill_date_field(departure_date)
                
                # Submit search
                self._submit_search()
                
                # Wait for results and parse
                flights = self._parse_flight_results(departure, arrival)
                logger.info(f"Found {len(flights)} flights")
                
                return flights
                
            except TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt == RETRY_ATTEMPTS - 1:
                    logger.error(f"Failed to search flights after {RETRY_ATTEMPTS} attempts")
                    return []
                import time
                time.sleep(RETRY_DELAY)
            except Exception as e:
                logger.error(f"Error searching flights: {e}")
                if attempt == RETRY_ATTEMPTS - 1:
                    return []
                import time
                time.sleep(RETRY_DELAY)
        
        return flights
    
    def _fill_airport_field(self, field_type: str, airport_code: str):
        """Fill airport field in search form"""
        try:
            # Look for departure or arrival input field
            selectors = [
                f"input[placeholder*='{field_type}']",
                f"input[name*='{field_type}']",
                f"input[id*='{field_type}']",
            ]
            
            field = None
            for selector in selectors:
                try:
                    field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if field:
                field.clear()
                field.send_keys(airport_code)
                logger.debug(f"Filled {field_type} field with {airport_code}")
            else:
                logger.warning(f"Could not find {field_type} field")
        except Exception as e:
            logger.warning(f"Error filling {field_type} field: {e}")
    
    def _fill_date_field(self, date_str: str):
        """Fill date field in search form"""
        try:
            selectors = [
                "input[type='date']",
                "input[placeholder*='date' i]",
                "input[name*='date' i]",
            ]
            
            date_field = None
            for selector in selectors:
                try:
                    date_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if date_field:
                date_field.clear()
                date_field.send_keys(date_str)
                logger.debug(f"Filled date field with {date_str}")
            else:
                logger.warning("Could not find date field")
        except Exception as e:
            logger.warning(f"Error filling date field: {e}")
    
    def _submit_search(self):
        """Submit the flight search form"""
        try:
            search_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            search_button.click()
            
            import time
            time.sleep(5)
            logger.debug("Search submitted")
        except Exception as e:
            logger.warning(f"Error submitting search: {e}")
    
    def _parse_flight_results(self, departure: str, arrival: str) -> List[Dict]:
        """Parse flight results from the page"""
        flights = []
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            flight_elements = soup.find_all(['div', 'li'], class_=lambda x: x and 'flight' in x.lower() if x else False)
            
            if not flight_elements:
                flight_elements = soup.find_all(class_=lambda x: x and 'result' in x.lower() if x else False)
            
            logger.debug(f"Found {len(flight_elements)} flight elements")
            
            for element in flight_elements:
                try:
                    flight_data = self._extract_flight_info(element, departure, arrival)
                    if flight_data:
                        flights.append(flight_data)
                except Exception as e:
                    logger.debug(f"Error extracting flight info: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing flight results: {e}")
        
        return flights
    
    def _extract_flight_info(self, element, departure: str, arrival: str) -> Dict:
        """Extract flight information from a flight element"""
        try:
            flight_info = {
                'departure_code': departure,
                'arrival_code': arrival,
                'departure_time': None,
                'arrival_time': None,
                'duration': None,
                'airline': 'Air New Zealand',
                'price': None,
                'currency': 'NZD',
                'stops': None,
                'aircraft': None,
                'scraped_at': datetime.now().isoformat(),
            }
            
            time_elements = element.find_all(class_=lambda x: x and 'time' in x.lower() if x else False)
            if len(time_elements) >= 2:
                flight_info['departure_time'] = time_elements[0].get_text(strip=True)
                flight_info['arrival_time'] = time_elements[1].get_text(strip=True)
            
            price_elements = element.find_all(class_=lambda x: x and 'price' in x.lower() if x else False)
            if price_elements:
                price_text = price_elements[0].get_text(strip=True)
                flight_info['price'] = price_text
            
            duration_elements = element.find_all(class_=lambda x: x and 'duration' in x.lower() if x else False)
            if duration_elements:
                flight_info['duration'] = duration_elements[0].get_text(strip=True)
            
            stops_text = element.get_text(lower=True)
            if 'non-stop' in stops_text or 'direct' in stops_text:
                flight_info['stops'] = 0
            elif 'stop' in stops_text:
                flight_info['stops'] = 1
            
            return flight_info if any(flight_info[k] for k in ['departure_time', 'price']) else None
            
        except Exception as e:
            logger.debug(f"Error extracting flight info: {e}")
            return None
    
    def scrape_all_routes(self, search_dates: List[str] = None) -> List[Dict]:
        """
        Scrape flights for all configured routes
        
        Args:
            search_dates: List of dates in format 'YYYY-MM-DD' (optional)
        
        Returns:
            List of all flight data
        """
        if search_dates is None:
            search_dates = [(datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 8)]
        
        all_flights = []
        
        for route in ROUTES:
            for date in search_dates:
                try:
                    flights = self.search_flights(
                        route['departure'],
                        route['arrival'],
                        date
                    )
                    
                    for flight in flights:
                        flight['departure_name'] = route['departure_name']
                        flight['arrival_name'] = route['arrival_name']
                    
                    all_flights.extend(flights)
                    
                except Exception as e:
                    logger.error(f"Error scraping route {route}: {e}")
                    continue
        
        self.flights_data = all_flights
        return all_flights
    
    def save_to_csv(self, filename: str = None):
        """Save scraped data to CSV file"""
        if filename is None:
            filename = os.path.join(DATA_OUTPUT_DIR, CSV_OUTPUT_FILE)
        
        try:
            if self.flights_data:
                df = pd.DataFrame(self.flights_data)
                df.to_csv(filename, index=False, encoding='utf-8')
                logger.info(f"Data saved to CSV: {filename}")
                logger.info(f"Total records: {len(self.flights_data)}")
            else:
                logger.warning("No flight data to save")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
    
    def save_to_json(self, filename: str = None):
        """Save scraped data to JSON file"""
        if filename is None:
            filename = os.path.join(DATA_OUTPUT_DIR, JSON_OUTPUT_FILE)
        
        try:
            if self.flights_data:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.flights_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Data saved to JSON: {filename}")
                logger.info(f"Total records: {len(self.flights_data)}")
            else:
                logger.warning("No flight data to save")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")


def main():
    """Main function to run the scraper"""
    scraper = None
    try:
        scraper = AirNZFlightScraper()
        
        logger.info("Starting flight scraper...")
        all_flights = scraper.scrape_all_routes()
        
        scraper.save_to_csv()
        scraper.save_to_json()
        
        logger.info(f"Scraping completed. Total flights found: {len(all_flights)}")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main()