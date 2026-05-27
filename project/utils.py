"""
Utility functions for the Flight Price Scraper
"""

from datetime import datetime, timedelta
from typing import Optional
import sqlite3
import logging

logger = logging.getLogger(__name__)


def get_departure_date_range(start_days: int = 0, end_days: int = 365):
    """
    Generate a range of departure dates
    
    Args:
        start_days: Start offset from today (default: 0 = today)
        end_days: End offset from today (default: 365 = 1 year)
    
    Returns:
        List of date strings in YYYY-MM-DD format
    """
    start_date = datetime.now().date() + timedelta(days=start_days)
    end_date = datetime.now().date() + timedelta(days=end_days)
    
    date_range = []
    current = start_date
    
    while current <= end_date:
        date_range.append(str(current))
        current += timedelta(days=1)
    
    return date_range


def format_currency(amount: float, currency: str = 'NZD', decimals: int = 2) -> str:
    """Format amount as currency string"""
    return f"${amount:,.{decimals}f} {currency}"


def calculate_days_until(target_date: str) -> int:
    """
    Calculate days from today until target date
    
    Args:
        target_date: Date string in YYYY-MM-DD format
    
    Returns:
        Number of days (negative if in past)
    """
    try:
        target = datetime.fromisoformat(target_date).date()
        today = datetime.now().date()
        return (target - today).days
    except ValueError:
        logger.error(f"Invalid date format: {target_date}")
        return 0


def calculate_days_before_from_iso(departure_date: str, scraped_at: str) -> int:
    """
    Calculate days between scrape timestamp and departure date
    
    Args:
        departure_date: Departure date in YYYY-MM-DD format
        scraped_at: ISO format timestamp
    
    Returns:
        Number of days before departure
    """
    try:
        dep_date = datetime.fromisoformat(departure_date).date()
        scrape_date = datetime.fromisoformat(scraped_at).date()
        return (dep_date - scrape_date).days
    except ValueError:
        logger.error(f"Invalid date format")
        return 0


def get_database_stats(db_path: str) -> dict:
    """Get basic statistics from the flight database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total records
        cursor.execute('SELECT COUNT(*) FROM flights')
        stats['total_flights'] = cursor.fetchone()[0]
        
        # Date range
        cursor.execute('SELECT MIN(departure_date), MAX(departure_date) FROM flights')
        min_date, max_date = cursor.fetchone()
        stats['earliest_departure'] = min_date
        stats['latest_departure'] = max_date
        
        # Number of scrapes
        cursor.execute('SELECT COUNT(DISTINCT DATE(scraped_at)) FROM flights')
        stats['scrape_sessions'] = cursor.fetchone()[0]
        
        # Routes
        cursor.execute('SELECT COUNT(DISTINCT departure_code, arrival_code) FROM flights')
        stats['routes'] = cursor.fetchone()[0]
        
        # Price range
        cursor.execute('SELECT MIN(price), MAX(price), AVG(price) FROM flights')
        min_price, max_price, avg_price = cursor.fetchone()
        stats['min_price'] = min_price
        stats['max_price'] = max_price
        stats['avg_price'] = avg_price
        
        conn.close()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {}


def get_price_trend(db_path: str, flight_number: str, departure_date: str) -> list:
    """
    Get price trend for a specific flight
    
    Returns list of tuples: (scraped_at, price, days_before_departure)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT scraped_at, price
            FROM flights
            WHERE flight_number = ? AND departure_date = ?
            ORDER BY scraped_at ASC
        ''', (flight_number, departure_date))
        
        results = []
        for scraped_at, price in cursor.fetchall():
            days_before = calculate_days_before_from_iso(departure_date, scraped_at)
            results.append((scraped_at, price, days_before))
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"Error getting price trend: {e}")
        return []


def export_to_csv(db_path: str, csv_path: str, query: Optional[str] = None):
    """Export flight data to CSV file"""
    try:
        import csv
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if query is None:
            query = 'SELECT * FROM flights ORDER BY departure_date, flight_number'
        
        cursor.execute(query)
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        
        logger.info(f"Exported {len(rows)} rows to {csv_path}")
        conn.close()
        
        return len(rows)
        
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        return 0


def cleanup_old_records(db_path: str, days_to_keep: int = 180):
    """
    Delete flight records older than specified days
    Only keeps the specified database size trimmed
    
    Args:
        db_path: Path to SQLite database
        days_to_keep: Number of days of data to retain
    """
    try:
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM flights WHERE scraped_at < ?', (cutoff_date,))
        old_count = cursor.fetchone()[0]
        
        cursor.execute('DELETE FROM flights WHERE scraped_at < ?', (cutoff_date,))
        conn.commit()
        
        logger.info(f"Deleted {old_count} old records (scraped before {cutoff_date})")
        
        conn.close()
        return old_count
        
    except Exception as e:
        logger.error(f"Error cleaning up old records: {e}")
        return 0


def validate_database(db_path: str) -> bool:
    """Validate database integrity"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Run integrity check
        cursor.execute('PRAGMA integrity_check')
        result = cursor.fetchone()[0]
        
        if result == 'ok':
            logger.info("Database integrity check passed")
            conn.close()
            return True
        else:
            logger.error(f"Database integrity issue: {result}")
            conn.close()
            return False
            
    except Exception as e:
        logger.error(f"Error validating database: {e}")
        return False


def optimize_database(db_path: str):
    """Optimize database for better performance"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vacuum and analyze
        cursor.execute('VACUUM')
        cursor.execute('ANALYZE')
        
        conn.commit()
        conn.close()
        
        logger.info("Database optimization completed")
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
