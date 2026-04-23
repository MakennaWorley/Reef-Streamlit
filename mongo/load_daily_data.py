"""
================================================================================
DAILY DATA LOADER
================================================================================

Purpose: Load NEW daily data for all 363 stations (incremental updates)

Usage:
    python -m mongo.load_daily_data

This script:
  - Scrapes TODAY's data for all stations
  - Adds just the NEW measurements to MongoDB
  - Does NOT clear existing data
  - Updates station locations if needed

Use this DAILY (via cron job or scheduler) to keep your database current.

Example cron job (runs daily at 2 AM):
    0 2 * * * cd /path/to/reef-streamlit && source reef-env/bin/activate && python -m mongo.load_daily_data
================================================================================
"""

import os
from datetime import datetime

from .db_utils import insert_records, insert_stations


def scrape_daily_data():
    """
    Scrape today's data for all 363 stations.
    
    This function should call your scraper and return:
    - records: List of measurement documents
    - stations: List of station location documents
    
    Each record must have:
      - station_name: Name of station
      - longitude: Station longitude
      - latitude: Station latitude
      - year, month, day: Date of measurement
      - measurement columns (temperature, salinity, etc.)
    
    Returns:
        tuple: (records, stations)
    """
    # TODO: Implement your daily scraper here
    # For now, this is a placeholder showing the expected format
    
    records = [
        # Example: {
        #     "station_name": "Aruba, Curacao, and Bonaire",
        #     "longitude": -69.125,
        #     "latitude": 12.3,
        #     "year": 2024,
        #     "month": 4,
        #     "day": 21,
        #     "temperature": 25.5,
        #     "salinity": 35.2,
        #     "depth": 12.5,
        # }
    ]
    
    stations = [
        # Example: {
        #     "station_name": "Aruba, Curacao, and Bonaire",
        #     "longitude": -69.125,
        #     "latitude": 12.3,
        # }
    ]
    
    return records, stations


def load_daily_data():
    """Load today's data for all stations into MongoDB."""
    print("=" * 80)
    print("DAILY DATA LOAD")
    print("=" * 80)
    print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Scrape today's data
    print("\nScraping data for all 363 stations...")
    try:
        records, stations = scrape_daily_data()
    except Exception as e:
        print(f"✗ Error scraping data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    if not records:
        print("ℹ No new data scraped today")
        return
    
    # Insert records into database
    print(f"\nInserting {len(records)} new measurements...")
    try:
        inserted_records = insert_records(records)
        print(f"✓ Inserted {inserted_records} measurement records")
    except Exception as e:
        print(f"✗ Error inserting records: {e}")
        return
    
    # Update station locations if provided
    if stations:
        print(f"\nUpdating {len(stations)} station locations...")
        try:
            inserted_stations = insert_stations(stations)
            print(f"✓ Updated {inserted_stations} station locations")
        except Exception as e:
            print(f"✗ Error updating stations: {e}")
    
    print("\n" + "=" * 80)
    print("DAILY LOAD COMPLETE ✓")
    print("=" * 80)
    print(f"\nTotal measurements added today: {inserted_records}")


def main():
    try:
        load_daily_data()
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
