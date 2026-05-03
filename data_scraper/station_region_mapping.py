"""
Station-to-Region and Ocean mapping generator.
Extracts ocean and region from structured filenames (OceanName_Region_SubRegion_Station.txt).
Also includes manually assigned stations from station_assignments.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'mongo'))
from db_utils import get_mongo_client
from station_assignments import STATION_ASSIGNMENTS


def parse_structured_filename(filename):
	"""
	Parse a structured filename to extract ocean, region, and subregion.

	Expected format: OceanName_Region_SubRegion_Station.txt
	Example: AtlanticOcean_Caribbean_FlowerGardenBanks_28FathomBank.txt

	Returns:
	    dict: {'ocean': str, 'region': str, 'subregion': str, 'filename_station': str} or None
	"""
	# Remove .txt extension
	name = filename.replace('.txt', '')

	# Split by underscore
	parts = name.split('_')

	# Must have at least 3 parts: OceanName, Region, SubRegion (or station name)
	# and first part must contain "Ocean"
	if len(parts) >= 3 and 'Ocean' in parts[0]:
		ocean = parts[0].replace('Ocean', '')
		region = parts[1]

		# Handle cases with 3 or 4+ parts
		if len(parts) == 3:
			# OceanName_Region_Station (no subregion)
			subregion = None
			filename_station = parts[2]
		else:
			# OceanName_Region_SubRegion_Station (or more parts)
			subregion = '_'.join(parts[2:-1])  # All middle parts
			filename_station = parts[-1]  # Last part is station

		return {'ocean': ocean, 'region': region, 'subregion': subregion, 'filename_station': filename_station}

	return None


def extract_station_mapping_from_csv(csv_path):
	"""
	Read the station location CSV and extract mappings from:
	1. Structured filenames (OceanName_Region_SubRegion_Station.txt)
	2. Manually assigned stations from STATION_ASSIGNMENTS

	Args:
	    csv_path: Path to _station_location.csv

	Returns:
	    list: List of dicts with station_name, ocean, region, subregion, and filename
	    int: Number of unmapped stations
	    set: Set of unmapped station names
	"""
	# Build a lookup of station names to filenames
	station_to_filename = {}
	with open(csv_path, 'r') as f:
		reader = csv.DictReader(f)
		for row in reader:
			station_to_filename[row['Station Name']] = row['Filename']

	mappings = []
	unmapped_stations = set(station_to_filename.keys())

	# First pass: extract from structured filenames
	with open(csv_path, 'r') as f:
		reader = csv.DictReader(f)
		for row in reader:
			station_name = row['Station Name']
			filename = row['Filename']

			# Try to parse from filename
			parsed = parse_structured_filename(filename)

			if parsed:
				mapping = {'station_name': station_name, 'ocean': parsed['ocean'], 'region': parsed['region']}

				# Add subregion if it exists
				if parsed['subregion']:
					mapping['subregion'] = parsed['subregion']

				mapping['filename'] = filename
				mappings.append(mapping)
				unmapped_stations.discard(station_name)

	# Second pass: add assigned stations
	for (ocean, region), station_names in STATION_ASSIGNMENTS.items():
		for station_name in station_names:
			if station_name in station_to_filename:
				filename = station_to_filename[station_name]
				mapping = {'station_name': station_name, 'ocean': ocean, 'region': region, 'filename': filename}
				# Leave subregion blank for assigned stations
				mappings.append(mapping)
				unmapped_stations.discard(station_name)

	return mappings, len(unmapped_stations), sorted(unmapped_stations)


def print_mappings_summary(mappings, unmapped_count, unmapped_stations):
	"""Print a summary of the mappings for user review."""
	print('\n' + '=' * 80)
	print('STATION TO REGION AND OCEAN MAPPING')
	print('(Structured filenames + manually assigned stations)')
	print('=' * 80 + '\n')

	# Group by ocean
	by_ocean = {}

	for mapping in mappings:
		ocean = mapping['ocean']
		region = mapping['region']
		station = mapping['station_name']

		if ocean not in by_ocean:
			by_ocean[ocean] = {}

		if region not in by_ocean[ocean]:
			by_ocean[ocean][region] = []

		by_ocean[ocean][region].append({'station': station, 'subregion': mapping.get('subregion'), 'filename': mapping.get('filename')})

	# Print organized by ocean and region
	for ocean in sorted(by_ocean.keys()):
		print(f'\n{ocean.upper()} OCEAN')
		print('-' * 80)

		for region in sorted(by_ocean[ocean].keys()):
			stations = by_ocean[ocean][region]
			print(f'  {region}: {len(stations)} stations')
			for item in sorted(stations, key=lambda x: x['station']):
				station_line = f'    - {item["station"]}'
				if item.get('subregion'):
					station_line += f' ({item["subregion"]})'
				print(station_line)

	print('\n' + '=' * 80)
	print(f'TOTAL MAPPED: {len(mappings)} stations')
	print(f'UNMAPPED: {unmapped_count} stations')
	if unmapped_stations:
		print('\nStations still needing assignment:')
		for station in unmapped_stations[:20]:  # Show first 20
			print(f'  - {station}')
		if len(unmapped_stations) > 20:
			print(f'  ... and {len(unmapped_stations) - 20} more')
	print('=' * 80 + '\n')


def insert_mappings_to_database(mappings):
	"""Insert station mappings into MongoDB with unique constraint on station_name."""
	try:
		client = get_mongo_client()
		db = client['reef_data']
		collection = db['station_mappings']

		# Drop existing collection to avoid duplicates
		collection.drop()

		# Create unique index on station_name
		collection.create_index('station_name', unique=True)

		# Insert all mappings
		result = collection.insert_many(mappings)
		print(f'Successfully inserted {len(result.inserted_ids)} station mappings into MongoDB')
		print('Unique index created on station_name to prevent duplicates')
		return True
	except Exception as e:
		print(f'Error inserting mappings into database: {e}')
		return False


def export_mappings_to_csv(mappings, output_path):
	"""Export mappings to CSV for review."""
	# Determine all fieldnames needed
	fieldnames = ['station_name', 'ocean', 'region']

	# Check if any mapping has subregion
	has_subregion = any('subregion' in m for m in mappings)
	if has_subregion:
		fieldnames.append('subregion')

	fieldnames.append('filename')

	with open(output_path, 'w', newline='') as f:
		writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
		writer.writeheader()
		writer.writerows(mappings)
	print(f'Mappings exported to CSV: {output_path}')


if __name__ == '__main__':
	import sys

	# Use the CSV from historical_data directory
	csv_path = Path(__file__).parent.parent / 'historical_data' / '_station_location.csv'

	if not csv_path.exists():
		print(f'Error: CSV file not found at {csv_path}')
		sys.exit(1)

	print(f'Reading station data from: {csv_path}')
	print('Processing structured filenames and assigned stations...\n')

	# Extract mappings
	mappings, unmapped_count, unmapped_stations = extract_station_mapping_from_csv(csv_path)

	# Sort mappings alphabetically by station name
	mappings.sort(key=lambda x: x['station_name'])

	# Deduplicate by station_name (keep first occurrence after sorting)
	seen_stations = set()
	deduplicated_mappings = []
	for mapping in mappings:
		station = mapping['station_name']
		if station not in seen_stations:
			deduplicated_mappings.append(mapping)
			seen_stations.add(station)
		else:
			print(f'Warning: Duplicate station found: {station}')

	mappings = deduplicated_mappings

	# Print summary for user review
	print_mappings_summary(mappings, unmapped_count, unmapped_stations)

	# Export to CSV for review
	output_dir = Path(__file__).parent
	export_mappings_to_csv(mappings, output_dir / 'station_mappings.csv')

	print('\nTo review the mappings, check:')
	print(f'  - CSV: station_mappings.csv')

	# Insert into database
	print('\nInserting into MongoDB...')
	if insert_mappings_to_database(mappings):
		print('\nStation mappings successfully inserted into database.')
	else:
		print('\nFailed to insert mappings. Please check the error above.')
