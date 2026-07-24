# Air NZ Flight Price Tracker

A small Streamlit dashboard that tracks Air New Zealand fares from Auckland to selected cities and stores timestamped results in SQLite.

## Demo

- Dashboard: deploy `src/app.py` on Streamlit Community Cloud
- Source code: this repository

## What it does

- Scrapes future flight prices for Auckland to Changsha, Wellington, Melbourne, Sydney, and New York
- Saves every result with a scrape timestamp in `flights.db`
- Shows two interactive charts:
  - lowest saved price by booking lead time for one route and departure date
  - latest lowest saved price by departure date for one route

## Run locally

```bash
pip install -r requirements.txt
python src/scraper.py --days 30
streamlit run src/app.py
```

## Automation

GitHub Actions runs the scraper daily, checks the parser tests, and commits the updated SQLite database.
The default run checks 50 route/date searches per day from a rolling 30-day window to keep the scraper fast and conservative.
