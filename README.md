# Flight Price Tracker

Lightweight flight price tracker for Air New Zealand using SQLite and Streamlit.

## Features

- **SQLite Database**: All data with timestamps
- **Price Curves**: Track price changes over time
- **Interactive Dashboard**: Streamlit + Plotly
- **Minimal**: 6 Python files, essential dependencies only

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Scrape
python scraper.py

# View dashboard
streamlit run app.py
```

## Files

- `scraper.py` - Flight scraper
- `db.py` - SQLite operations
- `analyzer.py` - Data analysis
- `app.py` - Streamlit dashboard
- `config.py` - Configuration
- `requirements.txt` - Dependencies

## Database

```
flights table:
- dept: Departure airport
- arrv: Arrival airport
- date: Flight date (YYYY-MM-DD)
- time: Departure time (HH:MM)
- price: Price in NZD
- ts: Timestamp (query time)
```

## Dashboard Features

### Route Prices
View price trends for all flights on a route

### Flight History
Track price changes for a specific flight

### Stats
Database statistics and route breakdown

## Example

```python
from analyzer import Analyzer

# Get flight price history
history = Analyzer.flight_history('AKL', 'CSX', '2026-12-13', '14:30')

# Get route prices
routes = Analyzer.route_prices('AKL', 'CSX', '2026-12-13')

# Get summary
summary = Analyzer.summary()
```

## License

MIT
