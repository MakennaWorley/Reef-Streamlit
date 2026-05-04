# Reef Watch

An interactive Streamlit dashboard for exploring global coral reef health monitoring data from NOAA's Coral Reef Watch program. Visualize thermal stress metrics, bleaching conditions, and historical trends across 363 reef monitoring stations worldwide.

## Features

### Interactive Dashboard
- **Home Page** with real-time database overview:
  - Total records, station count, date range of data
  - Quick access to recent measurements
  - Four exploratory tabs for different data views

- **By Station Tab**: Deep dive into individual station data
  - Select station, year, and month
  - Multi-metric time-series graphs with synchronized zooming
  - Displays: SST min/max, bleaching stress (SSTA@90th), hotspot anomalies (DHW), degree heating weeks
  - Drag to zoom horizontally across all graphs, double-click to reset
  - Station metadata (ocean, region, subregion) displayed in info panel

- **By Region Tab**: Compare data across regions
  - Aggregate view of all stations in a selected geographic region
  - Option to filter by subregion (e.g., Puerto Rico, Flower Garden Banks)
  - Shows metrics range across all region stations on most recent complete date

- **By Ocean Tab**: Global-scale perspective
  - View aggregated metrics for entire oceans (Atlantic, Pacific, Indian)
  - Metrics range across all ocean stations
  - Identify geographic thermal stress patterns

- **Query Database Page**: Custom data queries and export
  - Advanced filtering by station, date range, metrics
  - Export results to CSV

### Data Management
- **MongoDB Backend**: ~5.4M records across 363 stations (As of May 3rd, 2026)
- **Automatic Daily Updates**: Scheduled data ingestion from NOAA
- **Station Mappings**: Automatic geographic classification (Ocean/Region/Subregion)
- **Historical Data**: Complete historical archive from NOAA Coral Reef Watch

## Technologies

- **Frontend**: [Streamlit](https://streamlit.io/)
- **Visualization**: Plotly (time-series, interactive graphs)
- **Database**: MongoDB (document storage, aggregation queries)
- **Data Processing**: Pandas, NumPy
- **Web Scraping**: Selenium
- **Containerization**: Docker, Docker Compose

## Project Structure

```
reef-streamlit/
├── streamlit_app/                        # Streamlit dashboard
│   ├── app.py                            # Main dashboard (home + tabs)
│   ├── visualization_utils.py            # Shared viz components
│   └── requirements.txt
├── data_scraper/                         # Web scraping & data loading
│   ├── scraper.py                        # Daily/weekly NOAA scraper
│   ├── historical_loader.py              # Bulk historical data loader
│   ├── station_region_mapping.py         # Auto station → region mapper
│   ├── station_assignments.py            # Manual region assignments
│   ├── station_mappings.csv              # Structured station-region lookup
│   └── utils.py                          # Helper functions
├── mongo/                                # MongoDB utilities
│   ├── db_utils.py                       # Database queries & helpers
│   ├── midnight_scheduler.py             # Scheduled data updates
│   ├── load_historical_data.py           # Historical data loader
│   └── __init__.py
├── historical_data/                      # NOAA CSV data files
│   ├── _station_location.csv             # Station name/lat/lon
│   └── *.csv                             # 363 station data files
├── docker-compose.yml                    # MongoDB container
├── pyproject.toml                        # Project metadata
├── README.md                             # This file
└── CRON_SETUP.md                         # Automated scheduling guide
```

## Getting Started

### Prerequisites
- Python 3.8+
- Docker & Docker Compose
- MongoDB (or use the provided Docker container)

### Option 1: Full Docker Setup (Recommended)

Run both Streamlit and MongoDB in Docker containers:

1. **Start both containers**:
   ```bash
   docker-compose up -d --build
   ```

2. **Scrape historical data from NOAA** (one-time, ~5-10 minutes):
   ```bash
   docker-compose exec streamlit_app python data_scraper/historical_loader.py
   ```
   
   This scrapes CSV files from NOAA for all 363 coral reef stations.

on3. **Load data into MongoDB** (one-time, ~25-40 minutes):
   ```bash
   docker-compose exec streamlit_app python -m mongo.load_historical_data
   ```
   
   This processes and loads ~5.4M records into the database. ⚠️ Takes significant time but only needs to be run once.

4. **Open the dashboard**:
   - Navigate to `http://localhost:8501`

4. **View container logs** (if needed):
   ```bash
   docker-compose logs -f streamlit_app
   ```

5. **Stop containers** (keeps data):
   ```bash
   docker-compose down
   ```

### Option 2: Docker DB + Terminal Streamlit

Run MongoDB in Docker but Streamlit locally in your terminal (better for development):

1. **Start only MongoDB**:
   ```bash
   docker-compose up -d mongodb
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv reef-env
   source reef-env/bin/activate  # On Windows: reef-env\Scripts\activate
   pip install -r streamlit_app/requirements.txt
   ```

3. **Scrape historical data from NOAA** (one-time, ~5-10 minutes):
   ```bash
   python data_scraper/historical_loader.py
   ```
   
   This scrapes CSV files from NOAA for all 363 coral reef stations.

4. **Load data into MongoDB** (one-time, ~25-40 minutes):
   ```bash
   python -m mongo.load_historical_data
   ```
   
   This processes and loads ~5.4M records into the database. ⚠️ Takes significant time but only needs to be run once.

5. **Run Streamlit locally**:
   ```bash
   streamlit run streamlit_app/app.py
   ```

   The app will open at `http://localhost:8501`

6. **Stop MongoDB** (when done):
   ```bash
   docker-compose down
   ```

### Quick Reference

**Full Docker**:
```bash
docker-compose up -d --build          # Start both
docker-compose down                   # Stop both
```

**Docker DB + Terminal Streamlit**:
```bash
docker-compose up -d mongodb          # Start DB only
streamlit run streamlit_app/app.py    # Start Streamlit locally
```

### First-Time Data Loading

The first time you run the app, you must scrape and load historical data from NOAA in two steps:

**Step 1: Scrape data from NOAA** (~5-10 minutes):
```bash
# Full Docker:
docker-compose exec streamlit_app python data_scraper/historical_loader.py

# Local Streamlit (Docker DB):
python data_scraper/historical_loader.py
```

**Step 2: Load data into MongoDB** (~25-40 minutes):
```bash
# Full Docker:
docker-compose exec streamlit_app python -m mongo.load_historical_data

# Local Streamlit (Docker DB):
python -m mongo.load_historical_data
```

**Total Duration**: 30-50 minutes
**Data Volume**: ~5.4 million records across 363 stations

Once complete, the dashboard will be fully populated with historical data. Subsequent runs (for daily updates) are much faster.

## Data Sources & Collection

### NOAA Coral Reef Watch Program
Data is sourced from [NOAA's Coral Reef Watch](https://coralreefwatch.noaa.gov/), which provides:
- **Virtual Station Pages**: Aggregated data from satellite monitoring
- **Metrics**:
  - **SST_MIN/MAX**: Sea surface temperature min/max
  - **SST@90th_HS**: Sea surface temperature at 90th percentile of hottest season
  - **SSTA@90th_HS**: Sea surface temperature anomaly at 90th percentile
  - **90th_HS>0**: Days exceeding 90th percentile threshold
  - **DHW_from_90th_HS>1**: Degree heating weeks above 1°C threshold
  - **BAA_7day_max**: Bleaching alert area (7-day max)

### Data Collection Methods

#### Regular Data Scraping (`data_scraper/scraper.py`)
Daily/weekly collection of new NOAA data:
```bash
# Scrape all available data
python data_scraper/scraper.py

# Scrape only after a specific date (incremental)
python data_scraper/scraper.py 2026-04-14
```

#### Historical Bulk Load (`data_scraper/historical_loader.py`)
One-time import of all historical data:
```bash
python data_scraper/historical_loader.py
```

Creates `historical_data/_station_location.csv` with:
- Station Name
- Latitude / Longitude
- Source Filename (for data lineage)

## Database Management

### MongoDB Setup
Start the containerized MongoDB instance:
```bash
docker-compose up -d mongodb
```

Access the database at `mongodb://localhost:27017/reef_data`

### Loading Data

**Historical data (one-time)**:
```bash
python -m mongo.load_historical_data
```

**Incremental daily updates**:
```bash
python -m mongo.load_daily_data
```

**Recommended cron job** (runs at 2 AM daily):
```bash
0 2 * * * cd /path/to/reef-streamlit && source reef-env/bin/activate && python -m mongo.load_daily_data
```

See [CRON_SETUP.md](CRON_SETUP.md) for detailed scheduling instructions.

### Querying Data Programmatically

The `mongo.db_utils` module provides Python utilities:
```python
from mongo.db_utils import (
    get_all_stations,
    get_station_data,
    get_station_data_for_month,
    get_data_summary,
    get_unique_oceans,
    get_unique_regions,
)

# Database summary
summary = get_data_summary()
# Returns: {total_records, unique_stations, oldest_record, newest_record}

# All stations with metadata
stations = get_all_stations()
# Returns: [{'station_name': ..., 'ocean': ..., 'region': ...}, ...]

# Specific station data
data = get_station_data("Puerto Rico")

# Data for a month
data = get_station_data_for_month("Puerto Rico", 2026, 5)

# Available geographic filters
oceans = get_unique_oceans()
regions = get_unique_regions()
```

## Station Region & Ocean Mapping

Stations are automatically classified into oceans, regions, and subregions for easy geographic filtering.

### Mapping Strategy

1. **Structured Filenames**: Parse filename pattern `OceanName_Region_SubRegion_Station.txt`
   - Example: `AtlanticOcean_Caribbean_FlowerGardenBanks_28FathomBank.txt`
   - Automatically extracts ocean, region, subregion

2. **Manual Assignments**: Additional stations mapped via `station_assignments.py`

3. **Subregion Normalization**: Human-readable names
   - `GuamandCNMI` → `Guam and CNMI`
   - `FlowerGardenBanks` → `Flower Garden Banks`
   - `PuertoRico` → `Puerto Rico`
   - `SamoanIslands` → `Samoan Islands`
   - `SoutheastFlorida` → `Southeast Florida`
   - `FloridaKeys` → `Florida Keys`
   - `VirginIslands` → `Virgin Islands`

### Regenerating Mappings

After updating `station_assignments.py` or adding new data:
```bash
python data_scraper/station_region_mapping.py
```

This script:
- Parses all structured filenames
- Applies subregion normalization
- Merges manual assignments
- Exports to `station_mappings.csv`
- Drops and recreates MongoDB `station_mappings` collection
- Creates unique index on `station_name`

Result: `station_mappings` collection with 363 mapped stations

## Visualization Features

### Multi-Graph Dashboard (By Station Tab)
- **Synchronized Zooming**: Drag across one graph to zoom all metrics simultaneously
- **Fixed Y-Axes**: Each metric scales independently; y-axis always shows full data range
- **Double-Click Reset**: Double-click any graph to reset zoom to original view
- **Clean Drag Box**: Corner-to-corner drag selection (no axis guide lines)
- **Unified Hover**: Hover information shows across all graphs for selected date

### Data Aggregation Views
- **By Region**: Metrics range across all stations in region on most recent complete date
- **By Ocean**: Metrics range across entire ocean on most recent complete date
- Shows which date all selected stations have data for

## Architecture Notes

### Data Flow
1. **NOAA Coral Reef Watch** → Web scraper
2. **Scraper** → CSV files in `historical_data/`
3. **MongoDB loader** → `reef_data` database
4. **Streamlit queries** → Dashboard & visualizations

### Real-Time Updates
- Scheduled daily loader runs at 2 AM
- Incremental updates fetch only new data
- MongoDB aggregation queries handle geographic filtering

### Performance Optimizations
- Station metadata cached in `station_mappings` collection
- Indexed queries on `station_name`, `year`, `month`, `day`
- Aggregation pipeline for region/ocean-level metrics

## Troubleshooting

### MongoDB Connection Failed
Ensure MongoDB is running:
```bash
docker-compose up -d mongodb
```

### No Data Appearing in Dashboard
Check if data was loaded:
```bash
python -m mongo.load_historical_data --clear
```

### Graphs Not Rendering
Clear Streamlit cache:
```bash
streamlit cache clear
```

Then refresh the browser.

## Contributing

To add a new station:
1. Ensure it's in the NOAA data files or manually add to `station_assignments.py`
2. Run `python data_scraper/station_region_mapping.py`
3. Run `python -m mongo.load_historical_data --clear` to reload

## License

[Add your license here]

## References

- [NOAA Coral Reef Watch](https://coralreefwatch.noaa.gov/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [MongoDB Documentation](https://docs.mongodb.com/)

