# Reef Watch

A Streamlit application for visualizing coral reef health data from NOAA's Coral Reef Watch program.

## Overview

This project scrapes real-time coral reef monitoring data from [NOAA Coral Reef Watch](https://coralreefwatch.noaa.gov/product/vs/map.php) and provides interactive visualizations to explore global coral bleaching conditions and thermal stress levels.

## Technologies

- **Data Collection**: Web scraping with BeautifulSoup and Selenium
- **Data Processing**: NumPy and Pandas
- **Web Interface**: Streamlit
- **Visualization**: PyVista (3D geospatial visualization)
- **Data Analysis**: Regular expressions for parsing, statistical analysis
- **Data Presistence**: Uses a MongoDB to hold and store scrapped data long term

## Project Structure

```
reef-streamlit/
├── mongo/                                # MongoDB data management
│   ├── db_utils.py                       # Database connection & utilities
│   ├── load_historical_data.py           # One-time historical load
│   ├── load_daily_data.py                # Daily incremental updates
│   └── __init__.py
├── data_scraper/                         # Web scraping modules
│   ├── scraper.py
│   ├── historical_loader.py
│   └── utils.py
├── streamlit_app/                        # Streamlit application
│   ├── app.py
│   ├── pages/
│   └── requirements.txt
├── historical_data/                      # CSV data files from NOAA
│   ├── _station_location.csv             # Station metadata (name, lat/lon)
│   └── *.csv                             # 363 station data files
├── docker-compose.yml                    # MongoDB container orchestration
└── Project.ipynb                         # Project planning and exploration
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r streamlit_app/requirements.txt
   ```

2. Run the Streamlit app:
   ```bash
   streamlit run streamlit_app/app.py
   ```

## Data Source

Data is sourced from [NOAA Coral Reef Watch](https://coralreefwatch.noaa.gov/), which provides near-real-time satellite monitoring of coral bleaching worldwide.

## Data Scraping Features

### Regular Data Collection (`scraper.py`)
The main scraper for daily/weekly data collection:
- Automatically scrapes NOAA Coral Reef Watch data from multiple station pages
- Converts txt files directly to CSV format
- **Date filtering**: Only collect data after a specific date using the optional `start_date` parameter
- Supports both space-separated and comma-separated data formats

**Usage:**
```bash
# Scrape all available data (should use historical_loader.py)
python data_scraper/scraper.py

# Scrape only data after a specific date (useful for incremental updates)
python data_scraper/scraper.py 2026-04-14
```

**Scraped data includes:**
- Main NOAA virtual station page
- Florida Keys, Flower Garden Banks, USVI, Puerto Rico, Samoas, Guam, Rota, Saipan/Tinian/Aguijan stations

### Historical Data Loading (`historical_load.py`)
For bulk historical data processing:
- Scrapes and processes historical NOAA txt files
- When `update_locations=True`, automatically:
  - Extracts station metadata (name, latitude, longitude) from NOAA txt files
  - Stores station information in `historical_data/_station_location.csv`
  - **Tracks the source filename** for each station, enabling data lineage tracking and debugging
  - Deduplicates stations and alphabetizes the master list with `reindex_station_locations()`

The `_station_location.csv` includes:
- **Station Name**: Station identifier
- **Longitude**: Station longitude coordinate
- **Latitude**: Station latitude coordinate
- **Filename**: Source txt file the station data came from

## MongoDB Database Management

Reef data is stored in MongoDB for long-term persistence and efficient querying. The `mongo/` module provides utilities for loading and managing this data.

### Database Setup

Start MongoDB using Docker:
```bash
docker-compose up -d mongodb
```

This creates a MongoDB instance at `mongodb://localhost:27017` with database name `reef_data`.

### Loading Historical Data (One-Time Setup)

Load all 363 CSV station files into MongoDB:
```bash
# Load all historical data
python -m mongo.load_historical_data

# Clear existing data and reload
python -m mongo.load_historical_data --clear
```

This loads ~5.4M records across 363 coral reef monitoring stations worldwide. As of Apr 21, 2026

### Daily Data Updates

Set up incremental daily updates using the daily loader:
```bash
python -m mongo.load_daily_data
```

**Recommended cron job** (runs daily at 2 AM):
```bash
0 2 * * * cd /path/to/reef-streamlit && source reef-env/bin/activate && python -m mongo.load_daily_data
```

### Querying Data from Streamlit

The `mongo.db_utils` module provides utilities for querying:
```python
from mongo.db_utils import get_all_stations, get_station_data, get_data_summary

# Get database summary
summary = get_data_summary()
# Returns: {total_records, unique_stations, oldest_record, newest_record}

# Get all station locations
stations = get_all_stations()

# Get measurements for a specific station
data = get_station_data("Aruba, Curacao, and Bonaire")
```
