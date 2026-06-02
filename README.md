# Air NZ Flight Price Tracker

A small Streamlit dashboard that tracks Air New Zealand fares from Auckland to selected cities and stores timestamped results in SQLite.

## Demo

- Dashboard: deploy `src/app.py` on Streamlit Community Cloud
- Source code: this repository

## What it does

- Scrapes future flight prices for Auckland to Changsha, Wellington, Melbourne, Sydney, and New York
- Saves every result with a scrape timestamp in `flights.db`
- Shows two interactive charts:
  - prices for different departure times on the same route and date
  - price history for the same selected flight across scrape times

## Run locally

```bash
pip install -r requirements.txt
python src/scraper.py --days 30
streamlit run src/app.py
```

## Automation

GitHub Actions runs the scraper daily and commits the updated SQLite database.
