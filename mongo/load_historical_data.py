"""
================================================================================
HISTORICAL DATA LOADER
================================================================================

Purpose: Load ALL historical data from CSV files into MongoDB (one-time setup)

Usage:
    python -m mongo.load_historical_data                 # Load all CSV files
    python -m mongo.load_historical_data --clear         # Clear database and reload all data

This script:
  - Reads ALL CSV files from historical_data/
  - Loads station metadata from _station_location.csv
  - Inserts every row into the measurements collection
  - Creates the stations collection with location data
  - Creates database indexes

Use this ONCE when setting up your database for the first time.
================================================================================
"""

import argparse
import glob
import os
import sys

import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mongo.db_utils import clear_collection, clear_stations, create_indexes, get_data_summary, insert_records, insert_stations


def get_csv_files(directory=None):
	"""
	Get all CSV files from historical_data directory.

	Args:
	    directory: Path to historical_data directory (defaults to ./historical_data)

	Returns:
	    list: Sorted list of CSV file paths

	WARNING: This function only READS from the directory, it never deletes it.
	"""
	if directory is None:
		directory = os.path.join(os.path.dirname(__file__), '..', 'historical_data')

	# Exclude the station location file
	csv_files = [f for f in glob.glob(os.path.join(directory, '*.csv')) if not f.endswith('_station_location.csv')]

	return sorted(csv_files)


def load_station_metadata(directory=None):
	"""
	Load station metadata from _station_location.csv.

	Supports two CSV formats:
	1. With Filename column: Filename -> {station_name, longitude, latitude}
	2. Without Filename: Uses station_name as key (for direct lookups)

	Args:
	    directory: Path to historical_data directory

	Returns:
	    dict: Mapping of filename/station_name -> {station_name, longitude, latitude}
	"""
	if directory is None:
		directory = os.path.join(os.path.dirname(__file__), '..', 'historical_data')

	station_file = os.path.join(directory, '_station_location.csv')

	if not os.path.exists(station_file):
		print(f'✗ Station location file not found: {station_file}')
		return {}

	try:
		df = pd.read_csv(station_file)

		# Detect column names (support multiple naming conventions)
		station_col = None
		lon_col = None
		lat_col = None
		filename_col = None

		# Try different column name variations
		for col in df.columns:
			col_lower = col.lower()
			if 'station' in col_lower and 'name' in col_lower:
				station_col = col
			elif 'longitude' in col_lower or 'lon' in col_lower:
				lon_col = col
			elif 'latitude' in col_lower or 'lat' in col_lower:
				lat_col = col
			elif 'filename' in col_lower:
				filename_col = col

		if not station_col or not lon_col or not lat_col:
			print(f'✗ Could not find required columns (Station Name, Longitude, Latitude)')
			print(f'  Available columns: {list(df.columns)}')
			return {}

		# Create mapping: filename or station_name -> station metadata
		metadata = {}
		for _, row in df.iterrows():
			station_name = str(row.get(station_col, '')).strip()

			if not station_name:
				continue

			station_data = {'station_name': station_name, 'longitude': float(row.get(lon_col, 0)), 'latitude': float(row.get(lat_col, 0))}

			# Use filename if available, otherwise use station name as key
			if filename_col:
				filename = str(row.get(filename_col, '')).replace('.txt', '').replace('.csv', '').strip()
				if filename:
					metadata[filename] = station_data
			else:
				# Use station name as key (will match during CSV processing)
				metadata[station_name] = station_data

		print(f'✓ Loaded metadata for {len(metadata)} stations')
		return metadata

	except Exception as e:
		print(f'✗ Error loading station metadata: {e}')
		return {}


def load_csv_to_records(csv_file, station_metadata):
	"""
	Convert CSV file to list of MongoDB documents.

	Args:
	    csv_file: Path to CSV file
	    station_metadata: Dictionary mapping filename -> station info

	Returns:
	    tuple: (filename, list of record dictionaries)
	"""
	filename = os.path.basename(csv_file)
	filename_key = filename.replace('.csv', '')

	try:
		df = pd.read_csv(csv_file)

		# Get station info - try both filename and derived station name as keys
		station_info = station_metadata.get(filename_key, {})

		# If not found by filename, try to derive station name from filename and look it up
		if not station_info:
			# Convert filename (e.g., "Florida_Keys") to station name (e.g., "Florida Keys")
			derived_name = filename_key.replace('_', ' ')
			station_info = station_metadata.get(derived_name, {})

		station_name = station_info.get('station_name', filename_key)

		# Convert each row to a dictionary and add station info
		records = []
		for _, row in df.iterrows():
			record = row.to_dict()

			# Add station name only (longitude/latitude stored separately in stations collection)
			record['station_name'] = station_name

			# Convert date columns to integers
			if 'YYYY' in record:
				record['year'] = int(record['YYYY'])
				del record['YYYY']
			if 'MM' in record:
				record['month'] = int(record['MM'])
				del record['MM']
			if 'DD' in record:
				record['day'] = int(record['DD'])
				del record['DD']

			# Convert numeric columns (skip non-numeric)
			for key, value in record.items():
				if key not in ['station_name', 'year', 'month', 'day']:
					try:
						# Try to convert to float
						if pd.notna(value) and value != '':
							record[key] = float(value)
						else:
							record[key] = None
					except (ValueError, TypeError):
						pass  # Keep as string if not numeric

			records.append(record)

		return (station_name, records)

	except Exception as e:
		print(f'✗ Error loading {filename}: {e}')
		return (filename_key, [])


def load_all_data(clear_existing=False, directory=None):
	"""
	Load all CSV files into MongoDB.

	Args:
	    clear_existing: Whether to clear existing data first
	    directory: Path to historical_data directory
	"""
	print('=' * 80)
	print('LOADING HISTORICAL DATA - ONE TIME SETUP')
	print('=' * 80)

	# Get CSV files first
	csv_files = get_csv_files(directory)

	if not csv_files:
		print('\n✗ No CSV files found in historical_data/')
		print('\nTo set up your database:')
		print('  1. Run: python data_scraper/scraper.py')
		print('  2. This will download CSV files to .temp_data/')
		print('  3. Create historical_data/ directory: mkdir -p historical_data')
		print('  4. Move/copy files: mv .temp_data/*.csv historical_data/')
		print('  5. Run this script again: python mongo/load_historical_data.py --clear')
		return

	print(f'Found {len(csv_files)} CSV files')

	# Load station metadata if available
	print('\nLoading station metadata...')
	station_metadata = load_station_metadata(directory)

	if not station_metadata:
		print(f'⚠ No station metadata file found. Using filename-based station names.')
		print(f'  (This is OK for the first load - station names will be based on filenames)')

	# Clear existing data if requested
	if clear_existing:
		print('\nClearing existing data...')
		clear_collection()
		clear_stations()

	# Prepare station data for the stations collection (only if we have metadata)
	station_records = list(station_metadata.values()) if station_metadata else []

	# Load each CSV file
	print('\nLoading data...')
	total_records = 0
	failed_files = []

	for i, csv_file in enumerate(csv_files, 1):
		station_name, records = load_csv_to_records(csv_file, station_metadata)

		if records:
			inserted = insert_records(records)
			total_records += inserted
			print(f'  [{i:3d}/{len(csv_files)}] {station_name}: {inserted:6d} records')
		else:
			failed_files.append(station_name)
			print(f'  [{i:3d}/{len(csv_files)}] {station_name}: FAILED')

	# Insert station data if available
	if station_records:
		print('\nLoading station locations...')
		inserted_stations = insert_stations(station_records)
		print(f'✓ Loaded {inserted_stations} station locations')
	else:
		print('\n⚠ No station location data loaded (metadata file not found)')
		print('  Stations will be created when first referenced in measurement records')

	# Create indexes for faster queries
	print('\nCreating indexes...')
	create_indexes()

	# Print summary
	print('\n' + '=' * 80)
	print('HISTORICAL LOAD COMPLETE ✓')
	print('=' * 80)
	print(f'\nTotal records loaded: {total_records:,}')

	if failed_files:
		print(f'Failed files: {len(failed_files)}')
		for f in failed_files:
			print(f'  - {f}')

	# Get database summary
	summary = get_data_summary()
	print(f'\nDatabase Summary:')
	print(f'  Unique stations: {summary["unique_stations"]}')
	print(f'  Total records: {summary["total_records"]:,}')
	print(f'  Date range: {summary["oldest_record"]} to {summary["newest_record"]}')


def main():
	parser = argparse.ArgumentParser(description='Load historical reef data from CSV files into MongoDB')
	parser.add_argument('--clear', action='store_true', help='Clear existing data before loading')
	parser.add_argument('--directory', default=None, help='Path to historical_data directory (default: ../historical_data/)')

	args = parser.parse_args()

	try:
		load_all_data(clear_existing=args.clear, directory=args.directory)
	except Exception as e:
		print(f'\n✗ Fatal error: {e}')
		import traceback

		traceback.print_exc()


if __name__ == '__main__':
	main()
