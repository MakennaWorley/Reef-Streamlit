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
│   ├── historical_load.py
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
