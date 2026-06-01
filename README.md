# Air New Zealand Flight Tracker

A real-time flight data scraper for Air New Zealand flights from Auckland to major destinations.

## Features

- ✈️ **Real-time flight scraping** - Scrapes actual flight data from Auckland to:
  - Changsha (CSX)
  - Sydney (SYD)
  - Wellington (WLG)
  - New York (NYC)
  - Melbourne (MEL)

- 💾 **Data persistence** - Supports CSV and JSON formats
- 📊 **Data analytics** - Provides flight statistics and analysis
- ⏰ **Automated scheduling** - Supports automatic periodic scraping
- 🔄 **Error handling** - Automatic retry mechanism for robust data collection

## Project Structure

```
air-new-zealand-tracker/
├── config.py              # Project configuration
├── flight_scraper.py      # Main scraper program
├── scheduler.py           # Scheduled task executor
├── data_analyzer.py       # Data analysis tool
├── requirements.txt       # Project dependencies
├── README.md             # This file
├── data/                 # Data storage directory
│   ├── flight_data.csv   # CSV format data
│   └── flight_data.json  # JSON format data
└── logs/                 # Logs directory
    └── flight_scraper.log # Scraper logs
```

## Requirements

- Python 3.8+
- Google Chrome browser (for Selenium)
- ChromeDriver (matching your Chrome version)

## Installation and Usage

### 1. Clone the repository

```bash
git clone https://github.com/yiminyuan4-creator/air-new-zealand-tracker.git
cd air-new-zealand-tracker
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Download ChromeDriver

Download ChromeDriver from [official site](https://chromedriver.chromium.org/) matching your Chrome version and place it in your project directory or system PATH.

### 4. Run the scraper

#### Option 1: Single scrape

```bash
python flight_scraper.py
```

This will:
- Scrape flight data for the next 7 days across all routes
- Save results to `data/flight_data.csv` and `data/flight_data.json`
- Generate detailed logs

#### Option 2: Scheduled automatic scraping

```bash
python scheduler.py
```

This will:
- Execute one scrape immediately
- Then automatically run every 6 hours (configurable in `config.py`)

### 5. Analyze data

```bash
python data_analyzer.py
```

This will:
- Display flight data summary
- Show statistics by route
- Calculate price statistics
- Generate detailed analysis report to `data/flight_analysis_report.json`

## Configuration

Edit `config.py` to customize:

```python
# Routes to monitor
ROUTES = [
    {"departure": "AKL", "arrival": "CSX", ...},
    # ...
]

# Browser settings
HEADLESS_BROWSER = True           # Use headless browser
BROWSER_TIMEOUT = 30              # Timeout in seconds
RETRY_ATTEMPTS = 3                # Retry failed requests

# Scheduling interval (hours)
SCRAPE_INTERVAL_HOURS = 6
```

## Data Output Format

### CSV Format

```csv
departure_code,arrival_code,departure_time,arrival_time,duration,airline,price,currency,stops,scraped_at,departure_name,arrival_name
AKL,SYD,06:15,07:45,1h 30m,Air New Zealand,NZ$199.00,NZD,0,2026-06-01T10:30:00,Auckland,Sydney
```

### JSON Format

```json
[
  {
    "departure_code": "AKL",
    "arrival_code": "SYD",
    "departure_time": "06:15",
    "arrival_time": "07:45",
    "duration": "1h 30m",
    "airline": "Air New Zealand",
    "price": "NZ$199.00",
    "currency": "NZD",
    "stops": 0,
    "aircraft": null,
    "scraped_at": "2026-06-01T10:30:00",
    "departure_name": "Auckland",
    "arrival_name": "Sydney"
  }
]
```

## Logs

Log file location: `logs/flight_scraper.log`

Contains:
- Scraper startup/shutdown times
- Page loading status
- Data parsing progress
- Errors and exceptions

## Troubleshooting

### Q: Scraper cannot find elements?
A: The website structure may have changed. Update CSS selectors in `flight_scraper.py`:
1. Open browser developer tools (F12)
2. Inspect relevant elements
3. Update the selectors in the code

### Q: Scraper timeout?
A: Increase `BROWSER_TIMEOUT` in `config.py`

### Q: How to modify scrape frequency and dates?
A: Edit the `search_dates` parameter in `scrape_all_routes()` method

## Important Notes

⚠️ **Disclaimer**:
- Respect the website's `robots.txt` and terms of service
- Do not scrape at excessive frequency; recommend 6+ hours between requests
- Use only for learning and research purposes
- Obtain website owner consent before scraping

## License

MIT License

## Contact

For issues or suggestions, please submit an Issue or Pull Request.

---

**Last Updated**: June 1, 2026  
**Version**: 1.0.0