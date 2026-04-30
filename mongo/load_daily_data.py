"""
================================================================================
DAILY DATA LOADER
================================================================================

Purpose: Load NEW daily data for all 363 stations (incremental updates)

Usage:
    python -m mongo.load_daily_data

This script:
  - Queries database to find the last updated date
  - Scrapes data from that date onwards
  - Adds just the NEW measurements to MongoDB
  - Does NOT clear existing data
  - Updates station locations if needed

Use this DAILY (via cron job or scheduler) to keep your database current.

Example cron job (runs daily at 2 AM):
    0 2 * * * cd /path/to/reef-streamlit && source reef-env/bin/activate && python -m mongo.load_daily_data
================================================================================
"""

import os
import sys
from datetime import datetime, timedelta

import pandas as pd

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data_scraper.utils import scrape_and_download_station_data, scrape_multiple_stations
from mongo.db_utils import get_collection, insert_records, insert_stations


def get_last_update_date():
	"""
	Query MongoDB to find the OLDEST (minimum) date across all stations.
	This ensures we catch up any station that's behind on updates.

	For example:
	- Station A last updated: 2026-04-21
	- Station B last updated: 2026-04-20
	- Returns: 2026-04-20 (so we scrape from 04-20 onwards)

	Returns:
	    datetime: The oldest date with data in the database, or None if empty
	"""
	try:
		collection = get_collection()

		# Find the most recent date for each station, then get the oldest of those
		pipeline = [
			{'$sort': {'year': -1, 'month': -1, 'day': -1}},
			{'$group': {'_id': '$station_name', 'year': {'$first': '$year'}, 'month': {'$first': '$month'}, 'day': {'$first': '$day'}}},
			{'$sort': {'year': 1, 'month': 1, 'day': 1}},
			{'$limit': 1},
		]

		result = list(collection.aggregate(pipeline))

		if result:
			year = result[0].get('year')
			month = result[0].get('month')
			day = result[0].get('day')
			if year and month and day:
				return datetime(year, month, day)
	except Exception as e:
		print(f'✗ Error querying oldest update date: {e}')

	return None


def csv_to_records(csv_file: str):
	"""
	Convert a CSV file to database records.

	Args:
	    csv_file: Path to the CSV file

	Returns:
	    list: List of record dicts ready for MongoDB (measurements only)
	"""
	try:
		df = pd.read_csv(csv_file)
		records = []

		# Extract station name from filename
		filename = os.path.basename(csv_file)
		station_name = filename.replace('.csv', '').replace('_', ' ')

		for _, row in df.iterrows():
			record = {'station_name': station_name, 'year': int(row.get('YYYY', 0)), 'month': int(row.get('MM', 0)), 'day': int(row.get('DD', 0))}

			# Add all other columns as measurements
			for col in df.columns:
				if col not in ['YYYY', 'MM', 'DD']:
					try:
						record[col] = float(row[col]) if pd.notna(row[col]) else None
					except (ValueError, TypeError):
						record[col] = row[col]

			records.append(record)

		return records
	except Exception as e:
		print(f'✗ Error converting {csv_file}: {e}')
		return []


def scrape_daily_data():
	"""
	Scrape missing data starting from the oldest date in the database.
	This ensures we catch up any station that's behind on updates.

	For example:
	- Station A last updated: 2026-04-21
	- Station B last updated: 2026-04-20
	- We scrape from 2026-04-20 onwards to catch all missing data

	Returns:
	    tuple: (records, stations)
	"""
	# Get the oldest date in database
	oldest_date = get_last_update_date()

	if oldest_date:
		print(f'Oldest data in database: {oldest_date.strftime("%Y-%m-%d")}')
		start_date = oldest_date  # Start from the oldest date
	else:
		print('No data in database yet. Starting from 2024-01-01')
		start_date = datetime(2024, 1, 1)

	print(f'Scraping data from: {start_date.strftime("%Y-%m-%d")} onwards\n')

	# Create temp directory for CSV files
	temp_dir = os.path.join(os.path.dirname(__file__), '..', '.temp_data')
	os.makedirs(temp_dir, exist_ok=True)

	try:
		# Scrape main station data
		print('Scraping main station data...')
		url = 'https://coralreefwatch.noaa.gov/product/vs/data.php'
		csv_files, stations = scrape_and_download_station_data(url, output_dir=temp_dir, start_date=start_date)

		# Scrape specific station pages
		station_urls = [
			'/product/vs_single_pixel_exp/florida_keys.php',
			'/product/vs_single_pixel_exp/fgb.php',
			'/product/vs_single_pixel_exp/usvi.php',
			'/product/vs_single_pixel_exp/puerto_rico.php',
			'/product/vs_single_pixel_exp/samoas.php',
			'/product/vs_single_pixel_exp/guam.php',
			'/product/vs_single_pixel_exp/rota.php',
			'/product/vs_single_pixel_exp/saipan_tinian_aguijan.php',
		]
		print('Scraping specific station pages...')
		station_csv_files, station_stations = scrape_multiple_stations(station_urls, output_dir=temp_dir, start_date=start_date)
		csv_files.extend(station_csv_files)
		stations.extend(station_stations)

		# Convert CSVs to records
		records = []

		for csv_file in csv_files:
			csv_records = csv_to_records(csv_file)
			records.extend(csv_records)

		# Add any new stations from the scraped data
		if stations:
			print(f'Found {len(stations)} station metadata updates')

		# Cleanup temp directory
		import shutil

		shutil.rmtree(temp_dir, ignore_errors=True)

		return records, stations

	except Exception as e:
		print(f'✗ Error during scraping: {e}')
		import traceback

		traceback.print_exc()
		return [], []


def load_daily_data():
	"""Load today's data for all stations into MongoDB."""
	print('=' * 80)
	print('DAILY DATA LOAD')
	print('=' * 80)
	print(f'\nTime: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

	# Scrape data from last update date onwards
	print('\nQuerying database and scraping new data...')
	try:
		records, stations = scrape_daily_data()
	except Exception as e:
		print(f'✗ Error scraping data: {e}')
		import traceback

		traceback.print_exc()
		return

	if not records:
		print('ℹ No new data found')
		return

	# Insert records into database
	print(f'\nInserting {len(records)} new measurements...')
	try:
		inserted_records = insert_records(records)
		print(f'✓ Inserted {inserted_records} measurement records')
	except Exception as e:
		print(f'✗ Error inserting records: {e}')
		return

	# Update station locations if provided
	if stations:
		print(f'\nUpdating {len(stations)} station locations...')
		try:
			inserted_stations = insert_stations(stations)
			print(f'✓ Updated {inserted_stations} station locations')
		except Exception as e:
			print(f'✗ Error updating stations: {e}')

	print('\n' + '=' * 80)
	print('DAILY LOAD COMPLETE ✓')
	print('=' * 80)
	print(f'\nTotal measurements added: {inserted_records}')


def main():
	try:
		load_daily_data()
	except Exception as e:
		print(f'\n✗ Fatal error: {e}')
		import traceback

		traceback.print_exc()


if __name__ == '__main__':
	main()
