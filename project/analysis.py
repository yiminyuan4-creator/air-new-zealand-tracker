#!/usr/bin/env python3
import os
import sqlite3
import logging
import argparse
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

    def plot_smart_trends(self, dep_code: str, arr_code: str, dep_date: str) -> str:
        """
        Dynamically filters database records for any flights matching the route
        and departure date, creating distinct visualization lines.
        """
        sql = '''
            SELECT flight_number, scraped_at, price
            FROM flights
            WHERE departure_code = ? AND arrival_code = ? AND departure_date = ?
            ORDER BY flight_number ASC, scraped_at ASC
        '''
        rows = self._query_db(sql, (dep_code, arr_code, dep_date))
        if not rows:
            logger.warning(f"No records discovered for {dep_code}->{arr_code} on {dep_date}")
            return ''

        flight_data = {}
        for flight_num, scraped_at, price in rows:
            if flight_num not in flight_data:
                flight_data[flight_num] = {'dates': [], 'prices': []}
            try:
                flight_data[flight_num]['dates'].append(datetime.fromisoformat(scraped_at))
                flight_data[flight_num]['prices'].append(price)
            except Exception:
                continue

        plt.figure(figsize=(9, 5))
        has_plots = False

        for flight_num, data in flight_data.items():
            scraped_dates = data['dates']
            prices = data['prices']
            if not scraped_dates:
                continue
                
            has_plots = True
            try:
                target_dt = datetime.fromisoformat(dep_date).date()
                days_before = [(target_dt - d.date()).days for d in scraped_dates]
            except Exception:
                days_before = list(range(len(scraped_dates)))

            points = sorted(zip(days_before, prices))
            x, y = zip(*points)

            if len(scraped_dates) == 1:
                plt.scatter(x, y, s=120, label=f'{flight_num} (Initial: ${y[0]})')
            else:
                plt.plot(x, y, marker='o', linestyle='-', label=f'{flight_num} Trend')

        if not has_plots:
            plt.close()
            return ''

        plt.gca().invert_xaxis()
        plt.xlabel('Days Before Departure')
        plt.ylabel('Price (NZD)')
        plt.title(f'Flight Price Dynamics: {dep_code} -> {arr_code} ({dep_date})')
        plt.legend(loc='best')
        plt.grid(True, linestyle='--', alpha=0.5)

        filename = f"{self._sanitize_filename(f'{dep_code}_{arr_code}_{dep_date}')}.png"
        path = os.path.join(self.plots_dir, filename)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        logger.info(f"Generated smart visualization at: {path}")
        return path

    def generate_summary_stats(self) -> str:
        total_res = self._query_db('SELECT COUNT(*) FROM flights')
        total = total_res[0][0] if total_res else 0
        routes_res = self._query_db('SELECT COUNT(DISTINCT departure_code || arrival_code) FROM flights')
        routes = routes_res[0][0] if routes_res else 0
        date_range_res = self._query_db('SELECT MIN(departure_date), MAX(departure_date) FROM flights')
        date_range = date_range_res[0] if date_range_res else ('N/A', 'N/A')
        
        report = "========================================================================\n"
        report += "DATABASE TRACKING INFRASTRUCTURE STATISTICS\n"
        report += "========================================================================\n"
        report += f"Total Records Maintained: {total}\n"
        report += f"Unique Route Sectors: {routes}\n"
        report += f"Active Booking Horizon: {date_range[0]} to {date_range[1]}\n"
        return report

def main():
    try:
        parser = argparse.ArgumentParser(description="Flight Price Data Analysis Engine")
        parser.add_argument("--date", type=str, default="2026-06-15", help="Target departure date")
        parser.add_argument("--dep", type=str, default="AKL", help="Departure airport code")
        parser.add_argument("--arr", type=str, default="PVG", help="Arrival airport code")
        args = parser.parse_args()

        analyzer = FlightAnalyzer(DATABASE)
        summary = analyzer.generate_summary_stats()
        
        report_meta = f"\nTarget Sector Selection: {args.dep} -> {args.arr} on {args.date}\n"
        analyzer.plot_smart_trends(args.dep, args.arr, args.date)
        
        with open("analysis_report.txt", "w", encoding="utf-8") as f:
            f.write(summary + report_meta)
            
        logger.info("Smart framework analytics executed successfully.")
        return 0
    except Exception as e:
        logger.error(f"Execution fault: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    exit(main())
