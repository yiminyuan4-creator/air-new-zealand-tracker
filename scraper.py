import logging
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from config import ROUTES, URL, TIMEOUT, RETRIES, HEADLESS
from db import init_db, save

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

class Scraper:
    def __init__(self):
        init_db()
        self.driver = self._setup_browser()
    
    def _setup_browser(self):
        opts = webdriver.ChromeOptions()
        if HEADLESS:
            opts.add_argument('--headless')
        opts.add_argument('--no-sandbox')
        opts.add_argument('user-agent=Mozilla/5.0')
        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(TIMEOUT)
        return driver
    
    def search(self, dept, arrv, date):
        for attempt in range(RETRIES):
            try:
                log.info(f"Search: {dept}->{arrv} {date} (attempt {attempt+1})")
                self.driver.get(f"{URL}/booking/flights")
                WebDriverWait(self.driver, TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)
                flights = self._parse(dept, arrv, date)
                for f in flights:
                    save(**f)
                log.info(f"Found {len(flights)} flights")
                return flights
            except Exception as e:
                log.error(f"Error: {e}")
                if attempt == RETRIES - 1:
                    return []
                time.sleep(2)
        return []
    
    def _parse(self, dept, arrv, date):
        flights = []
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            # Parse flight elements - adapt to actual website
        except:
            pass
        return flights
    
    def run(self, days=7):
        for i in range(1, days + 1):
            d = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            for r in ROUTES:
                self.search(r['dept'], r['arrv'], d)
    
    def close(self):
        if self.driver:
            self.driver.quit()

if __name__ == "__main__":
    s = Scraper()
    try:
        s.run(days=7)
    finally:
        s.close()
