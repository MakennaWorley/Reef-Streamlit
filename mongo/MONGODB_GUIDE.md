# Loading Data into MongoDB

This guide shows you how to load your historical reef data from CSV files into MongoDB.

## Quick Start (3 Steps)

### Step 1: Start MongoDB with Docker
```bash
docker-compose up -d mongodb
```

Wait a moment for MongoDB to start, then verify it's running:
```bash
docker-compose ps
```

You should see `mongodb` with status `Up`.

### Step 2: Load Your Data
From the project root directory:
```bash
source reef-env/bin/activate      # Activate virtual environment
python data_scraper/load_historical_data.py  # Load all CSV data
```

You should see output like:
```
======================================================================
Loading Reef Data into MongoDB
======================================================================

Found 125 CSV files

Loading data...
  [  1/125] abc_islands:          500 records
  [  2/125] abrolhos_reefs:       324 records
  ...
  [125/125] yourfile.csv:         189 records

Creating indexes...
✓ Created index on 'station' field
✓ Created index on date fields

======================================================================
Load Complete!
======================================================================

Total records loaded: 48,234
Unique stations: 125
Total records: 48,234
Date range: 1990-01-01 to 2024-12-31
```

---

## What Was Created

I created three files for you:

### 1. `data_scraper/db_utils.py` - MongoDB Connection Utilities
Functions to connect to MongoDB and query data:
- `get_mongo_client()` - Connect to MongoDB
- `get_collection()` - Get the measurements collection
- `insert_records()` - Insert data
- `get_all_stations()` - Get list of all stations
- `get_station_data(station_name)` - Get data for a specific station
- `get_data_summary()` - Get statistics about your data

### 2. `data_scraper/load_historical_data.py` - Data Loader Script
Reads all CSV files from `historical_data/` and loads them into MongoDB.

Usage:
```bash
# Load all data
python data_scraper/load_historical_data.py

# Clear existing data and reload
python data_scraper/load_historical_data.py --clear

# Load from custom directory
python data_scraper/load_historical_data.py --directory /path/to/csvs
```

---

## How the Data Is Organized

Your MongoDB database `reef_data` contains two collections:

### Collection 1: `measurements`
Contains all reef measurement data with station location info:
```json
{
  "_id": ObjectId(...),
  "station_name": "Aruba, Curacao, and Bonaire",
  "longitude": -69.125,
  "latitude": 12.3,
  "year": 2024,
  "month": 3,
  "day": 15,
  "temperature": 25.3,
  "salinity": 35.2,
  "depth": 12.5,
  ...
}
```

**Each measurement record has:**
- **station_name**: Human-readable station name (from _station_location.csv)
- **longitude/latitude**: Station coordinates (for mapping)
- **year, month, day**: Date of measurement
- All other columns: Measurement values (temperature, salinity, etc.)

### Collection 2: `stations`
Contains station location metadata for placing markers on maps:
```json
{
  "_id": ObjectId(...),
  "station_name": "Aruba, Curacao, and Bonaire",
  "longitude": -69.125,
  "latitude": 12.3
}
```

**Structure:**
- **station_name**: Unique station name
- **longitude**: Longitude coordinate
- **latitude**: Latitude coordinate

---

## Common Queries in Your Code

### Get a list of all stations with location data
```python
from data_scraper.db_utils import get_all_stations
stations = get_all_stations()
# Returns:
# [
#   {"station_name": "Aruba, Curacao, and Bonaire", "longitude": -69.125, "latitude": 12.3},
#   {"station_name": "Bermuda", "longitude": -64.825, "latitude": 32.35},
#   ...
# ]
```

### Get all data for one station
```python
from data_scraper.db_utils import get_station_data
import pandas as pd

data = get_station_data("Aruba, Curacao, and Bonaire")
df = pd.DataFrame(data)  # Convert to DataFrame
# Each row includes: station_name, longitude, latitude, year, month, day, measurements...
```

### Get database summary
```python
from data_scraper.db_utils import get_data_summary
summary = get_data_summary()
# {
#   'total_records': 48234,
#   'unique_stations': 125,
#   'oldest_record': '1990-01-01',
#   'newest_record': '2024-12-31'
# }
```

### Filter data by station and date range
```python
from data_scraper.db_utils import get_collection
import pandas as pd

collection = get_collection()

# Get data for a specific station and date range
data = list(collection.find({
    "station_name": "Aruba, Curacao, and Bonaire",
    "year": 2024,
    "month": {"$gte": 6, "$lte": 8}  # June-August
}))

df = pd.DataFrame(data)
```

### Get all stations within a geographic region
```python
from data_scraper.db_utils import get_collection

collection = get_collection()

# Get records within a bounding box (lon/lat range)
data = list(collection.find({
    "longitude": {"$gte": -70, "$lte": -60},  # Caribbean region
    "latitude": {"$gte": 10, "$lte": 20}
}))

df = pd.DataFrame(data)
```

### Direct MongoDB queries for advanced analysis
```python
from data_scraper.db_utils import get_collection

collection = get_collection()

# Calculate average temperature by station
avg_temps = list(collection.aggregate([
    {
        "$group": {
            "_id": "$station_name",
            "avg_temp": {"$avg": "$temperature"},
            "lon": {"$first": "$longitude"},
            "lat": {"$first": "$latitude"}
        }
    },
    {"$sort": {"avg_temp": -1}}
]))

# Result:
# [
#   {"_id": "Station A", "avg_temp": 26.5, "lon": -70, "lat": 15},
#   {"_id": "Station B", "avg_temp": 25.2, "lon": -65, "lat": 18},
#   ...
# ]
```

---

## Troubleshooting

### "Failed to connect to MongoDB"
Make sure MongoDB is running:
```bash
docker-compose ps
docker-compose up -d mongodb
```

### "ModuleNotFoundError: No module named 'pymongo'"
Install it:
```bash
pip install pymongo
```

### "No records were loaded"
Check that your CSV files have the expected columns (YYYY, MM, DD):
```bash
head historical_data/abc_islands.csv
```

### Want to reload data?
Clear and reload:
```bash
python data_scraper/load_historical_data.py --clear
```

This will delete all existing data and reload from CSVs.

---

## What's Next?

1. **Create visualizations** with the data in `streamlit_app/app.py` (maps, charts, etc.)
2. **Set up real-time data scraping** that automatically updates MongoDB
3. **Deploy** with Docker: `docker-compose up`

Enjoy your reef data! 🌊🪸
