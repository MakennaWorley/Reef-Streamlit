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
├── data_scraper/          # Web scraping modules
│   ├── scraper.py
│   ├── historical_loader.py
│   └── utils.py
├── streamlit_app/         # Streamlit application
│   ├── app.py
│   ├── pages/
│   └── requirements.txt
├── docker-compose.yml     # Container orchestration
└── Project.ipynb          # Project planning and exploration
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
