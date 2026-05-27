# Air New Zealand Flight Price Tracker

Automatically scrape and analyze Air New Zealand flight prices, track price trends, and provide booking recommendations.

## 📋 Project Overview

This project periodically scrapes Air New Zealand flight prices, stores them in a SQLite database, and performs data analysis to help users find the best time to book flights.

### Key Features

✅ **Automated Scraping**: Automatically scrapes flight prices for multiple routes daily
✅ **Historical Data Preservation**: All scraped data includes timestamps and historical records are never overwritten
✅ **Two-Dimensional Analysis**:
  - **Dimension A**: Track price history of the same flight to find the cheapest booking time
  - **Dimension B**: Compare prices across different departure dates on the same route to find the best value travel dates
✅ **GitHub Actions Automation**: Runs automatically daily with results auto-committed to the repository

## 📍 Route Coverage

**Departure and Destination Combinations**:
- 🇳🇿 **Auckland (AKL)**
- 🇳🇿 **Wellington (WLG)**
- 🇦🇺 **Sydney (SYD)**
- 🇨🇳 **Changsha (CSX)**
- 🇺🇸 **New York (JFK)**

**Total of 20 routes** (bidirectional coverage)

## ⏰ Time Range

- Scraping range: All flights within 365 days from today onwards
- Auto-update: Runs daily at 02:00 UTC (10:00 NZST)

## 🗄️ Database Schema

### flights Table

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| flight_number | TEXT | Flight number |
| departure_code | TEXT | Departure airport code |
| arrival_code | TEXT | Arrival airport code |
| departure_date | TEXT | Departure date |
| departure_time | TEXT | Departure time |
| arrival_time | TEXT | Arrival time |
| duration | TEXT | Flight duration |
| price | REAL | Ticket price |
| currency | TEXT | Currency (default: NZD) |
| cabin_class | TEXT | Cabin class (default: ECONOMY) |
| scraped_at | TEXT | Scrape timestamp ⭐️ Key field |
| created_at | TIMESTAMP | Creation time |

**Key Design**:
- `UNIQUE` constraint ensures no duplicate records for the same flight, date, and scrape time
- Complete historical records enable time-series analysis

## 📊 Data Analysis

### Analysis Dimension A: Single Flight Price History

Find **when to book for the cheapest price**:

```
Analysis target: Specific flight number + specific departure date
Time dimension: From first scrape to departure date
Output: Price trend, minimum price, maximum price, best booking date
```

**Use case**:
- User has decided on a specific flight and wants to know when to book for the best price

### Analysis Dimension B: Route Date Comparison

Find **which departure date offers the best value**:

```
Analysis target: Specific route (departure → arrival)
Time dimension: Specific scrape time point, comparing multiple departure dates
Output: Daily minimum price, average price, best value date
```

**Use case**:
- User has chosen a route but has flexible dates; wants to find the cheapest departure date

## 🚀 Quick Start

### 1. Running Locally

#### Install dependencies
```bash
pip install -r requirements.txt
```

#### Run the scraper
```bash
python main.py
```

#### Analyze data
```bash
python analysis.py
```

### 2. Automated GitHub Actions

The project is configured with GitHub Actions to run automatically daily:

1. ✅ Executes `main.py` to scrape latest prices
2. ✅ Executes `analysis.py` to generate analysis reports
3. ✅ Auto-commits updated `flights.db` and analysis reports
4. ✅ Preserves run logs for review

**To view run logs**:
Go to GitHub repository → Actions tab → "Daily Flight Price Scraper" → View latest run

## 📁 Project Structure

```
.
├── main.py                          # Flight data scraper script
├── analysis.py                      # Data analysis script
├── requirements.txt                 # Python dependencies
├── flights.db                       # SQLite database (auto-generated)
├── analysis_report.txt              # Analysis report (auto-generated)
├── .github/
│   └── workflows/
│       └── cron.yml                 # GitHub Actions configuration
└── README.md                        # This file
```

## 🔧 Configuration

### main.py Core Configuration

```python
ROUTES = [...]              # Route list
DATABASE = 'flights.db'     # Database path
SCRAPE_DAYS = 365          # Number of days to scrape
```

### GitHub Actions Configuration

Edit `.github/workflows/cron.yml`:

```yaml
schedule:
  - cron: '0 2 * * *'  # Modify here to change run time
```

Cron format: `minute hour day month weekday`

## 📈 Analysis Examples

### Example: Dimension A Analysis Output

```
Flight: NZ100 on 2026-06-15
  Min Price: 450.50 NZD
  Max Price: 850.00 NZD
  Price Range: 399.50 NZD
  Best Booking Date: 2026-05-28 14:23:45.123456
  Total Observations: 15
```

**Interpretation**: For flight NZ100 on June 15, the lowest price was on May 28, approximately 18 days before departure.

### Example: Dimension B Analysis Output

```
Route: AKL → SYD
  Cheapest Departure Date: 2026-06-10
  Cheapest Price: 280.00 NZD
  Best Value Date: 2026-06-12 (avg: 320.50 NZD)
  Total Dates Analyzed: 30
```

**Interpretation**: For the same route, June 10 offers the cheapest price at $280 NZD, while June 12 has a slightly higher average price but more flight options.

## 🔐 GitHub Actions Permissions

Ensure your repository has the necessary permissions enabled:

1. ⚙️ Settings → Actions → General
2. Enable "Read and write permissions"
3. Enable "Allow GitHub Actions to create and approve pull requests"

## 📝 Important Notes

### Data Notes

- Current implementation uses **mock data** for demonstration (convenient for quick testing)
- **Production environment** requires integration with real airline APIs or web scraping
- All scraped data is fully preserved and never overwritten

### Legal Considerations

- ⚖️ Ensure compliance with target website's `robots.txt` and terms of service
- 🕐 Use reasonable request intervals to avoid overwhelming the server
- 📧 Contact website administrators for permission when necessary

### Performance

- First run will scrape large amounts of data (20 routes × 365 days)
- Database will grow over time (regular backups recommended)
- GitHub Actions has a 6-hour timeout limit; optimization may be needed for large datasets

## 📞 Troubleshooting

### Issue: GitHub Actions Timeout

**Solution**:
- Reduce SCRAPE_DAYS
- Optimize scraper logic performance
- Use concurrent requests

### Issue: Database Locked

**Solution**:
- Ensure no multiple scripts access `flights.db` simultaneously
- Manually delete `flights.db-wal` and `flights.db-shm` files

### Issue: Auto-commit Failed

**Solution**:
- Check repository permissions
- Verify GitHub token validity
- Review Actions logs for detailed error messages

## 🛠️ Feature Enhancement Suggestions

- [ ] Email notification integration (price drop alerts)
- [ ] Web dashboard (visualize price trends)
- [ ] Multi-currency support
- [ ] Flexible price alert system
- [ ] Export reports as PDF/Excel
- [ ] Integration with real airline APIs

## 📄 License

MIT License

## 🤝 Contributing

Feel free to submit Issues and Pull Requests!

---

**Last Updated**: 2026-05-27
