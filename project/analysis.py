#!/usr/bin/env python3
"""
Flight Price Analysis Module
Analyzes price trends and comparisons from scraped flight data
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE = 'flights.db'


import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class FlightAnalyzer:
    """Analyzes flight price data from SQLite database and generates plots"""
    
    def __init__(self, db_path: str = DATABASE):
        self.db_path = db_path
        self.plots_dir = os.path.join(os.getcwd(), 'analysis_plots')
        os.makedirs(self.plots_dir, exist_ok=True)
    
    def _query_db(self, sql: str, params: Tuple = ()) -> List[Tuple]:
        """Execute query and return results"""
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
        """Return a filesystem-safe filename"""
        return ''.join(c if c.isalnum() or c in ('-', '_') else '_' for c in name)

    def plot_price_history(self, flight_number: str, departure_date: str) -> str:
        """
        Generate a line chart for price history of a specific flight.
        Returns the path to the saved PNG or empty string if not created.
        """
        sql = '''
            SELECT scraped_at, price
            FROM flights
            WHERE flight_number = ? AND departure_date = ?
            ORDER BY scraped_at ASC
        '''
        rows = self._query_db(sql, (flight_number, departure_date))
        if not rows or len(rows) < 2:
            return ''

        scraped_dates = []
        prices = []
        for scraped_at, price in rows:
            try:
                scraped_dates.append(datetime.fromisoformat(scraped_at))
            except Exception:
                continue
            prices.append(price)

        if len(scraped_dates) < 2:
            return ''

        # Calculate days before departure for x-axis
        try:
            dep_date = datetime.fromisoformat(departure_date).date()
            days_before = [(dep_date - d.date()).days for d in scraped_dates]
        except Exception:
            days_before = list(range(len(scraped_dates)))

        # Sort by days_before
        points = sorted(zip(days_before, prices))
        x, y = zip(*points)

        plt.figure(figsize=(8,4))
        plt.plot(x, y, marker='o', linestyle='-')
        plt.gca().invert_xaxis()
        plt.xlabel('Days before departure')
        plt.ylabel('Price (NZD)')
        plt.title(f'Price history for {flight_number} on {departure_date}')
        plt.grid(True)

        filename = f"{self._sanitize_filename(f'{flight_number}_{departure_date}')}.png"
        path = os.path.join(self.plots_dir, filename)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        logger.info(f"Saved plot: {path}")
        return path

    def plot_route_date_comparison(self, departure_code: str, arrival_code: str, scraped_at_date: str) -> str:
        """
        Generate a comparison line chart for min/avg prices across departure dates
        at a specific scrape time. Returns the filepath or empty string.
        """
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
        plt.plot(dates, min_prices, marker='o', label='Min Price')
        plt.plot(dates, avg_prices, marker='x', label='Avg Price')
        plt.xticks(rotation=45)
        plt.xlabel('Departure date')
        plt.ylabel('Price (NZD)')
        plt.title(f'Route {departure_code}→{arrival_code} prices on {scraped_at_date}')
        plt.legend()
        plt.grid(True)

        filename = f"{self._sanitize_filename(f'{departure_code}_{arrival_code}_{scraped_at_date}')}.png"
        path = os.path.join(self.plots_dir, filename)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        logger.info(f"Saved plot: {path}")
        return path
    
    def analyze_price_history(self, flight_number: str, departure_date: str) -> Dict:
        """
        Analysis Dimension A: Price trend for same flight over time
        Shows when to book for cheapest price (days in advance)
        """
        sql = '''
            SELECT scraped_at, price, currency, cabin_class
            FROM flights
            WHERE flight_number = ? AND departure_date = ?
            ORDER BY scraped_at ASC
        '''
        
        results = self._query_db(sql, (flight_number, departure_date))
        
        if not results:
            return {'flight_number': flight_number, 'departure_date': departure_date, 
                    'status': 'no_data'}
        
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
    
    def analyze_route_date_comparison(self, departure_code: str, arrival_code: str, 
                                       scraped_at_date: str) -> Dict:
        """
        Analysis Dimension B: Compare prices for different departure dates
        on same route at same scrape time (which day is cheapest)
        """
        sql = '''
            SELECT departure_date, flight_number, price, currency, COUNT(*) as num_flights
            FROM flights
            WHERE departure_code = ? AND arrival_code = ? AND DATE(scraped_at) = ?
            GROUP BY departure_date
            ORDER BY departure_date ASC
        '''
        
        results = self._query_db(sql, (departure_code, arrival_code, scraped_at_date))
        
        if not results:
            return {
                'departure_code': departure_code,
                'arrival_code': arrival_code,
                'scraped_at_date': scraped_at_date,
                'status': 'no_data'
            }
        
        # Get detailed prices for each departure date
        detailed_results = self._query_db(f'''
            SELECT departure_date, flight_number, price, currency, departure_time
            FROM flights
            WHERE departure_code = ? AND arrival_code = ? AND DATE(scraped_at) = ?
            ORDER BY departure_date ASC, price ASC
        ''', (departure_code, arrival_code, scraped_at_date))
        
        # Group by departure date
        date_prices: Dict[str, List] = {}
        for dep_date, flight_num, price, currency, dep_time in detailed_results:
            if dep_date not in date_prices:
                date_prices[dep_date] = []
            date_prices[dep_date].append({
                'flight_number': flight_num,
                'price': price,
                'currency': currency,
                'departure_time': dep_time
            })
        
        # Calculate stats for each date
        date_stats = []
        for dep_date in sorted(date_prices.keys()):
            prices = [f['price'] for f in date_prices[dep_date]]
            date_stats.append({
                'departure_date': dep_date,
                'min_price': min(prices),
                'max_price': max(prices),
                'avg_price': round(sum(prices) / len(prices), 2),
                'num_flights': len(prices),
                'cheapest_flights': sorted(date_prices[dep_date], key=lambda x: x['price'])[:3]
            })
        
        # Find cheapest date
        cheapest_date_stat = min(date_stats, key=lambda x: x['min_price'])
        
        return {
            'departure_code': departure_code,
            'arrival_code': arrival_code,
            'scraped_at_date': scraped_at_date,
            'date_comparison': date_stats,
            'cheapest_date': cheapest_date_stat['departure_date'],
            'cheapest_date_min_price': cheapest_date_stat['min_price'],
            'best_value_date': self._find_best_value_date(date_stats)
        }
    
    def _find_best_value_date(self, date_stats: List[Dict]) -> Dict:
        """Find date with best average value"""
        return min(date_stats, key=lambda x: x['avg_price'])
    
    def _calculate_days_before(self, departure_date: str, scraped_at: str) -> int:
        """Calculate days between scrape date and departure date"""
        from datetime import datetime
        
        try:
            dep_date = datetime.fromisoformat(departure_date).date()
            scrape_date = datetime.fromisoformat(scraped_at).date()
            return (dep_date - scrape_date).days
        except:
            return 0
    
    def generate_report_dimension_a(self) -> str:
        """
        Generate comprehensive report for Analysis Dimension A
        (Price history for specific flights) and produce plots
        """
        # Get unique flight-date combinations
        sql = '''
            SELECT DISTINCT flight_number, departure_date
            FROM flights
            WHERE scraped_at IN (
                SELECT scraped_at FROM flights 
                ORDER BY scraped_at DESC LIMIT 10
            )
            LIMIT 50
        '''
        
        results = self._query_db(sql)
        
        report = "=" * 80 + "\n"
        report += "ANALYSIS DIMENSION A: FLIGHT PRICE HISTORY\n"
        report += "When to book for cheapest price (days in advance)\n"
        report += "=" * 80 + "\n\n"
        
        for flight_num, dep_date in results:
            analysis = self.analyze_price_history(flight_num, dep_date)
            
            if analysis.get('status') == 'no_data':
                continue
            
            report += f"Flight: {analysis['flight_number']} on {analysis['departure_date']}\n"
            report += f"  Min Price: {analysis['min_price']} NZD\n"
            report += f"  Max Price: {analysis['max_price']} NZD\n"
            report += f"  Price Range: {analysis['price_range']} NZD\n"
            report += f"  Best Booking Date: {analysis['best_booking_date']}\n"
            report += f"  Total Observations: {analysis['total_observations']}\n"
            
            # Generate plot for this flight-date
            plot_path = self.plot_price_history(flight_num, dep_date)
            if plot_path:
                report += f"  Plot: {plot_path}\n"
            report += "\n"
        
        return report
    
    def generate_report_dimension_b(self) -> str:
        """
        Generate comprehensive report for Analysis Dimension B
        (Route comparison across different departure dates) and produce plots
        """
        # Get unique routes from most recent scrape
        sql = '''
            SELECT DISTINCT departure_code, arrival_code
            FROM flights
            WHERE scraped_at = (SELECT MAX(scraped_at) FROM flights)
            LIMIT 20
        '''
        
        results = self._query_db(sql)
        most_recent_scrape = self._query_db('SELECT MAX(DATE(scraped_at)) FROM flights')[0][0]
        
        report = "=" * 80 + "\n"
        report += "ANALYSIS DIMENSION B: ROUTE DATE COMPARISON\n"
        report += "Which departure date has cheapest prices on same route\n"
        report += f"Analysis Date: {most_recent_scrape}\n"
        report += "=" * 80 + "\n\n"
        
        for dep_code, arr_code in results:
            analysis = self.analyze_route_date_comparison(dep_code, arr_code, most_recent_scrape)
            
            if analysis.get('status') == 'no_data':
                continue
            
            report += f"Route: {analysis['departure_code']} → {analysis['arrival_code']}\n"
            report += f"  Cheapest Departure Date: {analysis['cheapest_date']}\n"
            report += f"  Cheapest Price: {analysis['cheapest_date_min_price']} NZD\n"
            report += f"  Best Value Date: {analysis['best_value_date']['departure_date']} "
            report += f"(avg: {analysis['best_value_date']['avg_price']} NZD)\n"
            report += f"  Total Dates Analyzed: {len(analysis['date_comparison'])}\n"
            # Generate plot for this route at the most recent scrape
            plot_path = self.plot_route_date_comparison(dep_code, arr_code, most_recent_scrape)
            if plot_path:
                report += f"  Plot: {plot_path}\n"
            report += "\n"
        
        return report
    
    def generate_summary_stats(self) -> str:
        """Generate overall database statistics"""
        stats = {}
        
        # Total flights
        total = self._query_db('SELECT COUNT(*) FROM flights')[0][0]
        stats['total_flights'] = total
        
        # Routes covered
        routes = self._query_db(
            'SELECT COUNT(DISTINCT departure_code, arrival_code) FROM flights'
        )[0][0]
        stats['routes_covered'] = routes
        
        # Date range
        date_range = self._query_db(
            'SELECT MIN(departure_date), MAX(departure_date) FROM flights'
        )[0]
        stats['date_range'] = date_range
        
        # Scrapes conducted
        scrapes = self._query_db(
            'SELECT COUNT(DISTINCT DATE(scraped_at)) FROM flights'
        )[0][0]
        stats['scrapes_conducted'] = scrapes
        
        # Price statistics
        price_stats = self._query_db(
            'SELECT MIN(price), MAX(price), AVG(price) FROM flights'
        )[0]
        
        report = "=" * 80 + "\n"
        report += "DATABASE SUMMARY STATISTICS\n"
        report += "=" * 80 + "\n\n"
        report += f"Total Flights in Database: {stats['total_flights']}\n"
        report += f"Routes Covered: {stats['routes_covered']}\n"
        report += f"Departure Date Range: {stats['date_range'][0]} to {stats['date_range'][1]}\n"
        report += f"Scrape Sessions: {stats['scrapes_conducted']}\n"
        report += f"\nPrice Statistics:\n"
        report += f"  Minimum: ${price_stats[0]:.2f} NZD\n"
        report += f"  Maximum: ${price_stats[1]:.2f} NZD\n"
        report += f"  Average: ${price_stats[2]:.2f} NZD\n"
        
        return report


def main():
    """Main execution function"""
    try:
        analyzer = FlightAnalyzer(DATABASE)
        
        print("\n" + analyzer.generate_summary_stats() + "\n")
        print(analyzer.generate_report_dimension_a() + "\n")
        print(analyzer.generate_report_dimension_b() + "\n")
        
        logger.info("Analysis completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())
