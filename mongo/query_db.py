#!/usr/bin/env python3
"""
Simple command-line tool to query the reef database.
Usage: python query_db.py [options]
"""

import argparse
import json
import os
import sys

from tabulate import tabulate

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db_utils import get_all_stations, get_collection, get_data_summary, get_station_data


def print_stations():
	"""Print all stations in the database."""
	print('\n📍 All Stations in Database:')
	print('=' * 60)

	stations = get_all_stations()
	if not stations:
		print('No stations found. Have you loaded the data?')
		return

	# Prepare table data
	table_data = []
	for station in stations:
		table_data.append(
			[
				station.get('station_name', 'Unknown'),
				station.get('latitude', 'N/A'),
				station.get('longitude', 'N/A'),
				station.get('datapoint_count', 0),
			]
		)

	print(tabulate(table_data, headers=['Station Name', 'Latitude', 'Longitude', 'Datapoints'], tablefmt='grid'))
	print(f'\nTotal: {len(stations)} station(s)\n')


def print_summary():
	"""Print database summary statistics."""
	print('\n📊 Database Summary:')
	print('=' * 60)

	summary = get_data_summary()

	summary_data = [
		['Total Records', f'{summary["total_records"]:,}'],
		['Total Stations', summary['unique_stations']],
		['Oldest Record', summary['oldest_record']],
		['Newest Record', summary['newest_record']],
	]

	print(tabulate(summary_data, headers=['Metric', 'Value'], tablefmt='grid'))
	print()


def query_station(station_name):
	"""Query and display data for a specific station."""
	print(f'\n📍 Data for: {station_name}')
	print('=' * 60)

	data = get_station_data(station_name)
	if not data:
		print(f'No data found for station: {station_name}')
		return

	# Convert to list of lists for tabulate
	print(f'Found {len(data)} records\n')

	# Display first few records as sample
	if len(data) > 10:
		print('First 10 records:')
		sample_data = data[:10]
	else:
		sample_data = data

	# Prepare table
	if sample_data:
		keys = list(sample_data[0].keys())
		# Remove MongoDB _id field
		if '_id' in keys:
			keys.remove('_id')

		table_data = []
		for record in sample_data:
			row = [str(record.get(key, 'N/A')) for key in keys]
			table_data.append(row)

		print(tabulate(table_data, headers=keys, tablefmt='grid'))

	if len(data) > 10:
		print(f'\n... and {len(data) - 10} more records')
	print()


def advanced_query(query_json, limit=100, sort_by=None):
	"""Execute an advanced MongoDB query."""
	try:
		query = json.loads(query_json)
	except json.JSONDecodeError as e:
		print(f'❌ Invalid JSON query: {e}')
		return

	print(f'\n🔍 Query Results:')
	print('=' * 60)

	collection = get_collection()

	try:
		if sort_by:
			results = list(collection.find(query).sort(sort_by, 1).limit(limit))
		else:
			results = list(collection.find(query).limit(limit))

		if not results:
			print('No documents matched the query.')
			return

		print(f'Found {len(results)} document(s) (limited to {limit})\n')

		# Prepare table
		keys = list(results[0].keys())
		if '_id' in keys:
			keys.remove('_id')

		# Limit display to reasonable number of columns
		if len(keys) > 10:
			keys = keys[:10]
			print(f'(Showing first 10 fields, {len(list(results[0].keys())) - 1} total)\n')

		table_data = []
		for record in results:
			row = [str(record.get(key, 'N/A'))[:50] for key in keys]  # Truncate long values
			table_data.append(row)

		print(tabulate(table_data, headers=keys, tablefmt='grid'))
		print()

	except Exception as e:
		print(f'❌ Query error: {e}')


def main():
	parser = argparse.ArgumentParser(
		description='Query the reef database',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  python query_db.py --summary              # Show database summary
  python query_db.py --stations             # List all stations
  python query_db.py --station "Station Name"  # Get data for a station
  python query_db.py --query '{"temperature": {"$gt": 25}}'  # Advanced query
        """,
	)

	parser.add_argument('--summary', action='store_true', help='Show database summary statistics')
	parser.add_argument('--stations', action='store_true', help='List all stations in database')
	parser.add_argument('--station', type=str, help='Query data for a specific station')
	parser.add_argument('--query', type=str, help='Execute a MongoDB query (JSON format)')
	parser.add_argument('--limit', type=int, default=100, help='Limit number of results (default: 100)')
	parser.add_argument('--sort', type=str, help='Sort field name')

	args = parser.parse_args()

	# If no arguments, show summary
	if not any([args.summary, args.stations, args.station, args.query]):
		print_summary()
		print_stations()
		return

	if args.summary:
		print_summary()

	if args.stations:
		print_stations()

	if args.station:
		query_station(args.station)

	if args.query:
		advanced_query(args.query, limit=args.limit, sort_by=args.sort)


if __name__ == '__main__':
	main()
