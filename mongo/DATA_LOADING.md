# Data Loading Guide

## Two Different Loaders

You have **two separate scripts** for different purposes:

### 1. `load_historical_data.py` - HISTORICAL LOADING
**Purpose:** One-time setup to load ALL your historical data into the database

**What it does:**
- Reads all ~363 CSV files from `historical_data/`
- Loads every row of historical measurements
- Creates the stations collection with coordinates
- Sets up database indexes
- Takes 20+ minutes (one-time only)

**When to use:**
- First time setting up your database
- When you want to reset with fresh data

**Command:**
```bash
# Load all data
python mongo/load_historical_data.py

# Clear database first, then load all data
python mongo/load_historical_data.py --clear
```

**Example output:**
```
================================================================================
LOADING HISTORICAL DATA - ONE TIME SETUP
================================================================================

Loading station metadata...
✓ Loaded metadata for 363 stations
Found 363 CSV files

Loading data...
  [  1/363] Aruba, Curacao, and Bonaire:    500 records
  [  2/363] Bermuda:                        450 records
  ...
  [363/363] Yucatan Peninsula:              512 records

Loading station locations...
✓ Loaded 363 station locations

Creating indexes...
✓ Created index on 'station_name' field
✓ Created index on date fields

================================================================================
HISTORICAL LOAD COMPLETE ✓
================================================================================

Total records loaded: 48,234
```

---

### 2. `load_daily_data.py` - DAILY LOADING
**Purpose:** Regular updates to add just TODAY's data for all stations

**What it does:**
- Scrapes today's data from all 363 stations
- Adds only NEW measurements to the database
- Does NOT delete existing data
- Updates station coordinates if they changed

**When to use:**
- Every day (or multiple times per day)
- To keep your database current with latest observations

**Command:**
```bash
# Load today's data
python mongo/load_daily_data.py
```

**Example output:**
```
================================================================================
DAILY DATA LOAD
================================================================================

Time: 2024-04-21 02:15:30

Scraping data for all 363 stations...
Inserting 363 new measurements...
✓ Inserted 363 measurement records

Updating 0 station locations...

================================================================================
DAILY LOAD COMPLETE ✓
================================================================================

Total measurements added today: 363
```

---

## Setup Instructions

### Step 1: Initial Historical Load (First Time Only)
```bash
source reef-env/bin/activate
python mongo/load_historical_data.py --clear
```

This loads all your ~48,000 historical measurements into MongoDB.

### Step 2: Set Up Daily Loads (Automated)

Edit your crontab to run daily loads automatically:

```bash
crontab -e
```

Add this line to run daily at 2 AM:
```cron
0 2 * * * cd /Users/makennaworley/Desktop/GitHubCode/reef-streamlit && source reef-env/bin/activate && python mongo/load_daily_data.py >> /tmp/reef_daily_load.log 2>&1
```

Or run daily at multiple times (e.g., every 6 hours):
```cron
0 0,6,12,18 * * * cd /Users/makennaworley/Desktop/GitHubCode/reef-streamlit && source reef-env/bin/activate && python mongo/load_daily_data.py >> /tmp/reef_daily_load.log 2>&1
```

Check logs:
```bash
tail -f /tmp/reef_daily_load.log
```

---

## Database Structure After Both Loads

### Collections in `reef_data` database:

**measurements** (48,000+ records)
- Contains all historical + daily data
- Each row is one measurement from one station on one day
- Fields: station_name, longitude, latitude, year, month, day, + measurement columns

**stations** (363 records)
- One record per station
- Fields: station_name, longitude, latitude
- Used for placing markers on maps

---

## Next Steps

Now that you have clear separation:

1. **Implement the scraper** in `load_daily_data.py`'s `scrape_daily_data()` function
2. **Test the daily loader** manually first
3. **Set up cron job** to automate daily loads
4. **Build your Streamlit app** to query and visualize the data using the `mongo.db_utils` functions
