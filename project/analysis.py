#!/usr/bin/env python3
import os
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Tuple
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE = 'flights.db'

# =========================================================================
# GLOBAL FILTERS (Adjust these values to control your chart output)
# =========================================================================
FILTER_FLIGHT_NUMBER = "NZ289"
FILTER_DEPARTURE_DATE = "2026-06-15"
FILTER_DEPARTURE_CODE = "AKL"
FILTER_ARRIVAL_CODE = "PVG"
# =========================================================================

class FlightAnalyzer:
    def __init__(self, db_path: str = DATABASE):
        self.db_path = db_path
        self.plots_dir = os.getcwd()
    
    def _query_db(self, sql: str, params: Tuple = ()) -> List[Tuple]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return []

    def _sanitize_filename(self, name: str) -> str:
        return ''.join(c if c.isalnum() or c in ('-', '_') else '_' for c in name)

    def plot_price_history(self, flight_number: str, departure_date: str) -> str:
        sql = '''
            SELECT scraped_at, price
            FROM flights
            WHERE flight_number = ? AND departure_date = ?
            ORDER BY scraped_at ASC
        '''
        rows = self._query_db(sql, (flight_number, departure_date))
        if not rows:
            logger.warning(f"No price history found for {flight_number} on {departure_date}")
            return ''

        scraped_dates = []
        prices = []
        for scraped_at, price in rows:
            try:
                scraped_dates.append(datetime.fromisoformat(scraped_at))
            except Exception:
                continue
            prices.append(price)

        if not scraped_dates:
            return ''

        try:
            dep_date = datetime.fromisoformat(departure_date).date()
            days_before = [(dep_date - d.date()).days for d in scraped_dates]
        except Exception:
            days_before = list(range(len(scraped_dates)))

        points = sorted(zip(days_before, prices))
        x, y = zip(*points)

        plt.figure(figsize=(8,4))
        if len(rows) == 1:
            plt.scatter(x, y, color='#ff4757', s=120, label=f'Initial Price: ${y[0]}')
            plt.title(f'Initial Price Point: {flight_number} ({departure_date})')
        else:
            plt.plot(x, y, marker='o', linestyle='-', color='#1e90ff', label='Price Trend')
            plt.title(f'Price History: {flight_number} ({departure_date})')
            
        plt.gca().invert_xaxis()
        plt.xlabel('Days Before Departure')
        plt.ylabel('Price (NZD)')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.5)

        filename = f"{self._sanitize_filename(f'{flight_number}_{departure_date}')}.png"
        path = os.path.join(self.plots_dir, filename)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        logger.info(f"Saved trend chart to: {path}")
        return path

    def plot_route_date_comparison(self, departure_code: str, arrival_code: str, scraped_at_date: str) -> str:
        sql = '''
            SELECT departure_date, price
            FROM flights
            WHERE departure_code = ? AND arrival_code = ? AND DATE(scraped_at) = ?
            ORDER BY departure_date ASC
        '''
        rows = self._query_db(sql, (departure_code, arrival_code, scraped_at_date))
        if not rows:
            return ''

        from collections import defaultdict
        by_date = defaultdict(list)
        for dep_date, price in rows:
            by_date[dep_date].append(price)

        dates = sorted(by_date.keys())
        min_prices = [min(by_date[d]) for d in dates]
        avg_prices = [round(sum(by_date[d]) / len(by_date[d]), 2) for d in dates]

        if not dates:
            return ''

        plt.figure(figsize=(10,4))
        if len(dates) == 1:
            plt.scatter(dates, min_prices, color='#ff4757', s=120, label='Min Price')
            plt.scatter(dates, avg_prices, color='#2ed573', marker='x', s=120, label='Avg Price')
            plt.title(f'Initial Route Snapshot: {departure_code}->{arrival_code} ({scraped_at_date})')
        else:
            plt.plot(dates, min_prices, marker='o', color='#1e90ff', label='Min Price')
            plt.plot(dates, avg_prices, marker='x', color='#2ed573', label='Avg Price')
            plt.title(f'Route Comparison: {departure_code}->{arrival_code} ({scraped_at_date})')
            
        plt.xticks(rotation=45)
        plt.xlabel('Departure Date')
        plt.ylabel('Price (NZD)')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.5)

        filename = f"{self._sanitize_filename(f'{departure_code}_{arrival_code}_{scraped_at_date}')}.png"
        path = os.path.join(self.plots_dir, filename)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        logger.info(f"Saved comparison chart to: {path}")
        return path
    
    def analyze_price_history(self, flight_number: str, departure_date: str) -> Dict:
        sql = '''
            SELECT scraped_at, price, currency, cabin_class
            FROM flights
            WHERE flight_number = ? AND departure_date = ?
            ORDER BY scraped_at ASC
        '''
        results = self._query_db(sql, (flight_number, departure_date))
        if not results:
            return {'flight_number': flight_number, 'departure_date': departure_date, 'status': 'no_data'}
        
        history = []
        min_price = float('inf')
        max_price = 0
        min_price_date = None
        
        for scraped_at, price, currency, cabin_class in results:
            days_before = self._calculate_days_before(departure_date, scraped_at)
            history.append({
                'scraped_at': scraped_at,
                'price': price,
                'currency': currency,
                'cabin_class': cabin_class,
                'days_before_departure': days_before
            })
            if price < min_price:
                min_price = price
                min_price_date = scraped_at
            max_price = max(max_price, price)
        
        return {
            'flight_number': flight_number,
            'departure_date': departure_date,
            'history': history,
            'min_price': min_price,
            'max_price': max_price,
            'price_range': max_price - min_price,
            'best_booking_date': min_price_date,
            'total_observations': len(history)
        }
    
    def analyze_route_date_comparison(self, departure_code: str, arrival_code: str, scraped_at_date: str) -> Dict:
        detailed_results = self._query_db(f'''
            SELECT departure_date, flight_number, price, currency, departure_time
            FROM flights
            WHERE departure_code = ? AND arrival_code = ? AND DATE(scraped_at) = ?
            ORDER BY departure_date ASC, price ASC
        ''', (departure_code, arrival_code, scraped_at_date))
        
        if not detailed_results:
            return {'status': 'no_data'}

        date_prices = {}
        for dep_date, flight_num, price, currency, dep_time in detailed_results:
            if dep_date not in date_prices:
                date_prices[dep_date] = []
            date_prices[dep_date].append({'price': price})
        
        date_stats = []
        for dep_date in sorted(date_prices.keys()):
            prices = [f['price'] for f in date_prices[dep_date]]
            date_stats.append({
                'departure_date': dep_date,
                'min_price': min(prices),
                'max_price': max(prices),
                'avg_price': round(sum(prices) / len(prices), 2)
            })
        
        cheapest_date_stat = min(date_stats, key=lambda x: x['min_price'])
        return {
            'departure_code': departure_code,
            'arrival_code': arrival_code,
            'scraped_at_date': scraped_at_date,
            'date_comparison': date_stats,
            'cheapest_date': cheapest_date_stat['departure_date'],
            'cheapest_date_min_price': cheapest_date_stat['min_price'],
            'best_value_date': min(date_stats, key=lambda x: x['avg_price'])
        }
    
    def _calculate_days_before(self, departure_date: str, scraped_at: str) -> int:
        try:
            dep_date = datetime.fromisoformat(departure_date).date()
            scrape_date = datetime.fromisoformat(scraped_at).date()
            return (dep_date - scrape_date).days
        except:
            return 0
    
    def generate_report_dimension_a(self) -> str:
        report = "========================================================================\n"
        report += "ANALYSIS DIMENSION A: FLIGHT PRICE HISTORY\n"
        report += "========================================================================\n"
        analysis = self.analyze_price_history(FILTER_FLIGHT_NUMBER, FILTER_DEPARTURE_DATE)
        if analysis.get('status') != 'no_data':
            report += f"Flight: {analysis['flight_number']} on {analysis['departure_date']}\n"
            report += f"  Min Price: {analysis['min_price']} NZD\n"
            report += f"  Max Price: {analysis['max_price']} NZD\n"
            report += f"  Price Range: {analysis['price_range']} NZD\n"
            report += f"  Best Booking Date: {analysis['best_booking_date']}\n"
            report += f"  Total Observations: {analysis['total_observations']}\n"
            self.plot_price_history(FILTER_FLIGHT_NUMBER, FILTER_DEPARTURE_DATE)
        return report
    
    def generate_report_dimension_b(self) -> str:
        most_recent_scrape_res = self._query_db('SELECT MAX(DATE(scraped_at)) FROM flights')
        if not most_recent_scrape_res or not most_recent_scrape_res[0][0]:
            return "No data available for Analysis Dimension B.\n"
        most_recent_scrape = most_recent_scrape_res[0][0]
        
        report = "========================================================================\n"
        report += "ANALYSIS DIMENSION B: ROUTE DATE COMPARISON\n"
        report += f"Analysis Date: {most_recent_scrape}\n"
        report += "========================================================================\n"
        analysis = self.analyze_route_date_comparison(FILTER_DEPARTURE_CODE, FILTER_ARRIVAL_CODE, most_recent_scrape)
        if analysis.get('status') != 'no_data':
            report += f"Route: {analysis['departure_code']} -> {analysis['arrival_code']}\n"
            report += f"  Cheapest Departure Date: {analysis['cheapest_date']}\n"
            report += f"  Cheapest Price: {analysis['cheapest_date_min_price']} NZD\n"
            report += f"  Best Value Date: {analysis['best_value_date']['departure_date']} (avg: {analysis['best_value_date']['avg_price']} NZD)\n"
            self.plot_route_date_comparison(FILTER_DEPARTURE_CODE, FILTER_ARRIVAL_CODE, most_recent_scrape)
        return report
    
    def generate_summary_stats(self) -> str:
        total_res = self._query_db('SELECT COUNT(*) FROM flights')
        total = total_res[0][0] if total_res else 0
        routes_res = self._query_db('SELECT COUNT(DISTINCT departure_code || arrival_code) FROM flights')
        routes = routes_res[0][0] if routes_res else 0
        date_range_res = self._query_db('SELECT MIN(departure_date), MAX(departure_date) FROM flights')
        date_range = date_range_res[0] if date_range_res else ('N/A', 'N/A')
        scrapes_res = self._query_db('SELECT COUNT(DISTINCT DATE(scraped_at)) FROM flights')
        scrapes = scrapes_res[0][0] if scrapes_res else 0
        price_stats_res = self._query_db('SELECT MIN(price), MAX(price), AVG(price) FROM flights')
        price_stats = price_stats_res[0] if price_stats_res else (0.0, 0.0, 0.0)
        
        report = "========================================================================\n"
        report += "DATABASE SUMMARY STATISTICS\n"
        report += "========================================================================\n"
        report += f"Total Flights in Database: {total}\n"
        report += f"Routes Covered: {routes}\n"
        report += f"Departure Date Range: {date_range[0]} to {date_range[1]}\n"
        report += f"Scrape Sessions: {scrapes}\n"
        report += f"Price Statistics:\n"
        report += f"  Minimum: ${price_stats[0] if price_stats[0] else 0.0:.2f} NZD\n"
        report += f"  Maximum: ${price_stats[1] if price_stats[1] else 0.0:.2f} NZD\n"
        report += f"  Average: ${price_stats[2] if price_stats[2] else 0.0:.2f} NZD\n"
        return report

def main():
    try:
        analyzer = FlightAnalyzer(DATABASE)
        summary = analyzer.generate_summary_stats()
        dim_a = analyzer.generate_report_dimension_a()
        dim_b = analyzer.generate_report_dimension_b()
        
        with open("analysis_report.txt", "w", encoding="utf-8") as f:
            f.write(summary + "\n" + dim_a + "\n" + dim_b)
            
        logger.info("Analysis completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    exit(main())
