"""
Data analyzer for flight data
Provides statistics and analysis of collected flight data
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, List
import pandas as pd

from config import DATA_OUTPUT_DIR, CSV_OUTPUT_FILE, LOG_DIR, LOG_FILE, LOG_LEVEL

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


class FlightDataAnalyzer:
    """Analyzer for flight data"""
    
    def __init__(self, csv_file: str = None):
        """
        Initialize the analyzer
        
        Args:
            csv_file: Path to CSV file with flight data
        """
        if csv_file is None:
            csv_file = os.path.join(DATA_OUTPUT_DIR, CSV_OUTPUT_FILE)
        
        self.csv_file = csv_file
        self.df = None
        self.load_data()
    
    def load_data(self):
        """Load flight data from CSV"""
        try:
            if os.path.exists(self.csv_file):
                self.df = pd.read_csv(self.csv_file)
                logger.info(f"Loaded {len(self.df)} flight records")
            else:
                logger.warning(f"File not found: {self.csv_file}")
                self.df = pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.df = pd.DataFrame()
    
    def get_summary_statistics(self) -> Dict:
        """Get summary statistics of the data"""
        if self.df.empty:
            return {}
        
        stats = {
            'total_flights': len(self.df),
            'unique_routes': len(self.df[['departure_code', 'arrival_code']].drop_duplicates()),
            'unique_departure_cities': self.df['departure_code'].nunique(),
            'unique_arrival_cities': self.df['arrival_code'].nunique(),
            'date_range': {
                'from': self.df['scraped_at'].min() if 'scraped_at' in self.df else None,
                'to': self.df['scraped_at'].max() if 'scraped_at' in self.df else None,
            }
        }
        
        return stats
    
    def get_flights_by_route(self) -> Dict[str, int]:
        """Get number of flights per route"""
        if self.df.empty:
            return {}
        
        route_counts = self.df.groupby(['departure_code', 'arrival_code']).size().to_dict()
        return {f"{k[0]}->{k[1]}": v for k, v in route_counts.items()}
    
    def get_price_statistics(self) -> Dict:
        """Get price statistics"""
        if self.df.empty:
            return {}
        
        stats = {}
        
        try:
            if 'price' in self.df.columns:
                prices = pd.to_numeric(
                    self.df['price'].str.replace(r'[^\d.]', '', regex=True),
                    errors='coerce'
                )
                
                if prices.notna().any():
                    stats = {
                        'min_price': prices.min(),
                        'max_price': prices.max(),
                        'avg_price': prices.mean(),
                        'median_price': prices.median(),
                        'currency': 'NZD'
                    }
        except Exception as e:
            logger.warning(f"Error calculating price statistics: {e}")
        
        return stats
    
    def get_route_analysis(self, departure: str = None, arrival: str = None) -> Dict:
        """
        Get detailed analysis for a specific route
        
        Args:
            departure: Departure airport code (optional)
            arrival: Arrival airport code (optional)
        
        Returns:
            Analysis dictionary
        """
        if self.df.empty:
            return {}
        
        df_filtered = self.df
        
        if departure:
            df_filtered = df_filtered[df_filtered['departure_code'] == departure.upper()]
        
        if arrival:
            df_filtered = df_filtered[df_filtered['arrival_code'] == arrival.upper()]
        
        analysis = {
            'total_flights': len(df_filtered),
            'unique_dates': df_filtered['scraped_at'].nunique() if 'scraped_at' in df_filtered else 0,
            'direct_flights': len(df_filtered[df_filtered['stops'] == 0]) if 'stops' in df_filtered else 0,
            'flights_with_stops': len(df_filtered[df_filtered['stops'] > 0]) if 'stops' in df_filtered else 0,
        }
        
        return analysis
    
    def export_summary_report(self, output_file: str = None):
        """Export a summary report as JSON"""
        if output_file is None:
            output_file = os.path.join(DATA_OUTPUT_DIR, 'flight_analysis_report.json')
        
        try:
            report = {
                'generated_at': datetime.now().isoformat(),
                'summary': self.get_summary_statistics(),
                'flights_by_route': self.get_flights_by_route(),
                'price_statistics': self.get_price_statistics(),
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Report exported to {output_file}")
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
    
    def display_summary(self):
        """Display summary in console"""
        stats = self.get_summary_statistics()
        
        print("\n" + "="*60)
        print("FLIGHT DATA SUMMARY")
        print("="*60)
        
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        print("\nFlights by Route:")
        print("-"*60)
        for route, count in self.get_flights_by_route().items():
            print(f"  {route}: {count} flights")
        
        print("\nPrice Statistics:")
        print("-"*60)
        price_stats = self.get_price_statistics()
        for key, value in price_stats.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
        print("\n" + "="*60 + "\n")


def main():
    """Main function to run the analyzer"""
    analyzer = FlightDataAnalyzer()
    analyzer.display_summary()
    analyzer.export_summary_report()


if __name__ == "__main__":
    main()