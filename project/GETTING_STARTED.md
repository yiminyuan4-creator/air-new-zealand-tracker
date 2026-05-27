# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Clone the Repository
```bash
git clone <your-repo-url>
cd <repo-name>
```

### Step 2: Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Run the Scraper
```bash
python main.py
```

This will create the `flights.db` database and scrape data for all routes.

**⏱️ First run may take several minutes** (20 routes × 365 days)

### Step 4: Analyze the Data
```bash
python analysis.py
```

Output will include:
- Database statistics
- Dimension A analysis report (single flight price history)
- Dimension B analysis report (route date comparison)

### Step 5: View the Database
```bash
sqlite3 flights.db

# At the sqlite3 prompt:
SELECT * FROM flights LIMIT 10;
.quit
```

## 📊 Local Development Workflow

### Modify Route Configuration

Edit `config.py`:

```python
FLIGHT_ROUTES = [
    ('AKL', 'WLG'),  # Add or remove routes
    ('AKL', 'SYD'),
]

SCRAPE_DAYS = 90  # Reduce days for faster testing
```

Then run `python main.py` again

### Customize Analysis

Edit analysis functions in `analysis.py` or create a new script:

```python
from analysis import FlightAnalyzer

analyzer = FlightAnalyzer('flights.db')

# Get price history for a specific flight
history = analyzer.analyze_price_history('NZ100', '2026-06-15')
print(history)

# Get date comparison for a specific route
comparison = analyzer.analyze_route_date_comparison('AKL', 'SYD', '2026-05-27')
print(comparison)
```

### Export Data

Use the export functions in `utils.py`:

```python
from utils import export_to_csv

# Export all data to CSV
export_to_csv('flights.db', 'flights_export.csv')

# Export a specific route
query = "SELECT * FROM flights WHERE departure_code='AKL' AND arrival_code='SYD'"
export_to_csv('flights.db', 'auckland_sydney.csv', query)
```

## 🔧 GitHub Setup

### 1. Enable Actions

In your GitHub repository settings:

**Settings → Actions → General**

- ✅ Enable local and third party Actions for this repository
- ✅ Allow all actions and reusable workflows
- ✅ Allow GitHub Actions to create and approve pull requests

### 2. Check Automated Runs

Go to the **Actions** tab:

- View the "Daily Flight Price Scraper" workflow
- Check logs of recent runs
- Verify that `flights.db` was properly committed

### 3. Manual Trigger

Click **Actions** → **Daily Flight Price Scraper** → **Run workflow** → **Run workflow**

## 📁 File Guide

| File | Purpose |
|------|---------|
| `main.py` | Core scraper script |
| `analysis.py` | Data analysis script |
| `config.py` | Configuration file |
| `utils.py` | Utility functions library |
| `requirements.txt` | Python dependencies |
| `flights.db` | SQLite database (auto-generated) |
| `.github/workflows/cron.yml` | GitHub Actions configuration |

## 🐛 Frequently Asked Questions

### Q1: "ModuleNotFoundError: No module named 'requests'"

**Solution**:
```bash
pip install -r requirements.txt
```

### Q2: First run is too slow

**Solution**: Modify `config.py` to reduce days:
```python
SCRAPE_DAYS = 30  # Change to 30 days
```

### Q3: "database is locked" error

**Solution**:
```bash
# Delete temporary files
rm -f flights.db-wal flights.db-shm

# Then run again
python main.py
```

### Q4: GitHub Actions shows red X

**Troubleshooting steps**:
1. Click the red X to view detailed logs
2. Check the error message
3. Common causes:
   - Dependencies not installed → Check `requirements.txt`
   - Insufficient permissions → Check GitHub Actions settings
   - Script error → Test locally with `python main.py`

### Q5: Database file is too large

**Solution**: Use the cleanup function from `utils.py`:

```python
from utils import cleanup_old_records

cleanup_old_records('flights.db', days_to_keep=180)  # Keep only 180 days of data
```

## 💡 Usage Recommendations

### Development Tips

1. **Test before deploying**: Test all changes locally first
2. **Incremental changes**: Modify one script at a time
3. **Check logs**: Review logs after each run

### Production Tips

1. **Regular backups**: Download and backup `flights.db` periodically
2. **Monitor size**: Check database size regularly
3. **Version control**: Track configuration changes in git

### Analysis Tips

1. **Wait for sufficient data**: Collect at least one week of data to see price trends
2. **Compare multiple dates**: Dimension B analysis requires data from multiple departure dates
3. **Pay attention to timestamps**: All analysis is based on the `scraped_at` timestamp

## 📞 Getting Help

### View Full Documentation
- See [README.md](README.md)

### Debug Information
- Check log messages output by scripts
- GitHub Actions logs are available in the Actions tab

### Customize Scripts
- Scripts have detailed comments
- You can customize the scraper logic as needed

---

**You're all set! Start exploring flight price data!** ✈️
