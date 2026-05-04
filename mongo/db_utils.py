"""
MongoDB utilities for reef-streamlit application.
Handles connection, database initialization, and data operations.
"""

import os

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Get MongoDB connection string from environment or use default
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
MONGO_URI = f'mongodb://{MONGO_HOST}:{MONGO_PORT}'

DB_NAME = 'reef_data'
COLLECTION_NAME = 'measurements'
STATIONS_COLLECTION = 'stations'


def get_mongo_client():
	"""
	Create and return a MongoDB client.

	Returns:
	    MongoClient: Connected MongoDB client

	Raises:
	    ConnectionFailure: If unable to connect to MongoDB
	"""
	try:
		client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
		# Test connection
		client.admin.command('ping')
		print(f'✓ Connected to MongoDB at {MONGO_URI}')
		return client
	except (ConnectionFailure, ServerSelectionTimeoutError) as e:
		print(f'✗ Failed to connect to MongoDB at {MONGO_URI}: {e}')
		print(f'  Make sure MongoDB is running. If using Docker, run: docker-compose up')
		raise


def get_database():
	"""
	Get the reef database.

	Returns:
	    Database: MongoDB database object
	"""
	client = get_mongo_client()
	return client[DB_NAME]


def get_collection(collection_name=COLLECTION_NAME):
	"""
	Get a collection from the reef database.

	Args:
	    collection_name: Name of the collection

	Returns:
	    Collection: MongoDB collection object
	"""
	db = get_database()
	return db[collection_name]


def clear_collection(collection_name=COLLECTION_NAME):
	"""
	Delete all documents in a collection.

	Args:
	    collection_name: Name of the collection to clear
	"""
	collection = get_collection(collection_name)
	result = collection.delete_many({})
	print(f'✓ Cleared {result.deleted_count} documents from {collection_name}')


def create_indexes():
	"""
	Create indexes for faster queries and prevent duplicates.
	"""
	collection = get_collection()

	# Index on station name for quick lookups
	collection.create_index('station_name')
	print("✓ Created index on 'station_name' field")

	# Index on date for time-series queries
	collection.create_index([('year', 1), ('month', 1), ('day', 1)])
	print('✓ Created index on date fields')

	# Unique index on station_name + date to prevent duplicate measurements
	collection.create_index([('station_name', 1), ('year', 1), ('month', 1), ('day', 1)], unique=True, sparse=True, name='unique_station_date')
	print('✓ Created unique index on (station_name, year, month, day) to prevent duplicates')

	# Index on stations collection
	stations = get_collection(STATIONS_COLLECTION)
	stations.create_index('station_name', unique=True)
	print("✓ Created unique index on 'station_name' in stations collection")


def insert_records(records, collection_name=COLLECTION_NAME):
	"""
	Insert or update multiple records into the collection.
	Uses upsert logic to prevent duplicates - if a record with the same
	station_name + date already exists, it will be replaced with the new data.

	Args:
	    records: List of dictionaries to insert
	    collection_name: Name of the collection

	Returns:
	    int: Number of records processed (inserted or updated)
	"""
	if not records:
		return 0

	collection = get_collection(collection_name)
	count = 0

	for record in records:
		# Use station_name + date as the unique identifier
		filter_query = {
			'station_name': record.get('station_name'),
			'year': record.get('year'),
			'month': record.get('month'),
			'day': record.get('day'),
		}

		# Replace the entire document if it exists, insert if it doesn't
		collection.replace_one(filter_query, record, upsert=True)
		count += 1

	return count


def insert_stations(station_records):
	"""
	Insert station location data into the stations collection.

	Args:
	    station_records: List of dictionaries with station_name, longitude, latitude

	Returns:
	    int: Number of inserted station records
	"""
	if not station_records:
		return 0

	stations = get_collection(STATIONS_COLLECTION)
	# Use replace_one to update if exists, insert if not
	for record in station_records:
		stations.update_one({'station_name': record['station_name']}, {'$set': record}, upsert=True)
	return len(station_records)


def clear_stations():
	"""Delete all documents in the stations collection."""
	stations = get_collection(STATIONS_COLLECTION)
	result = stations.delete_many({})
	print(f'✓ Cleared {result.deleted_count} stations from {STATIONS_COLLECTION}')


def get_all_stations():
	"""
	Get list of all stations with their location data and measurement count.

	Returns:
	    list: List of station documents with name, longitude, latitude, and datapoint_count
	"""
	stations_collection = get_collection(STATIONS_COLLECTION)
	measurements_collection = get_collection(COLLECTION_NAME)

	stations = list(stations_collection.find().sort('station_name', 1))

	# Add datapoint count for each station
	for station in stations:
		count = measurements_collection.count_documents({'station_name': station.get('station_name')})
		station['datapoint_count'] = count

	return stations


def get_station_data(station_name):
	"""
	Get all measurements for a specific station.

	Args:
	    station_name: Name of the station

	Returns:
	    list: List of measurement documents
	"""
	collection = get_collection()
	return list(collection.find({'station_name': station_name}).sort([('year', 1), ('month', 1), ('day', 1)]))


def get_data_summary():
	"""
	Get summary statistics about the data in the database.
	Uses aggregation with sorting to reliably find the absolute oldest and newest dates.

	Returns:
	    dict: Summary including total records, stations, date range
	"""
	collection = get_collection()

	total_records = collection.count_documents({})

	stations_collection = get_collection(STATIONS_COLLECTION)
	unique_stations = stations_collection.count_documents({})

	# Get oldest record by sorting
	pipeline_oldest = [
		{'$match': {'year': {'$exists': True}, 'month': {'$exists': True}, 'day': {'$exists': True}}},
		{'$sort': {'year': 1, 'month': 1, 'day': 1}},
		{'$limit': 1},
	]

	# Get newest record by sorting
	pipeline_newest = [
		{'$match': {'year': {'$exists': True}, 'month': {'$exists': True}, 'day': {'$exists': True}}},
		{'$sort': {'year': -1, 'month': -1, 'day': -1}},
		{'$limit': 1},
	]

	oldest_result = list(collection.aggregate(pipeline_oldest))
	newest_result = list(collection.aggregate(pipeline_newest))

	if oldest_result:
		oldest = oldest_result[0]
		oldest_str = f'{oldest["year"]}-{oldest["month"]:02d}-{oldest["day"]:02d}'
	else:
		oldest_str = 'N/A'

	if newest_result:
		newest = newest_result[0]
		newest_str = f'{newest["year"]}-{newest["month"]:02d}-{newest["day"]:02d}'
	else:
		newest_str = 'N/A'

	return {'total_records': total_records, 'unique_stations': unique_stations, 'oldest_record': oldest_str, 'newest_record': newest_str}


def get_most_recent_common_date():
	"""
	Find the most recent date where all stations have at least one measurement.
	Returns the most recent day that has complete coverage across all stations.

	Returns:
	    dict: Contains 'year', 'month', 'day', 'date_str' or None if not enough data
	"""
	collection = get_collection()
	stations_collection = get_collection(STATIONS_COLLECTION)

	# Get all unique stations
	unique_stations = stations_collection.count_documents({})
	if unique_stations == 0:
		return None

	# Get all unique dates with their station counts, sorted by date descending
	pipeline = [
		{'$match': {'year': {'$exists': True}, 'month': {'$exists': True}, 'day': {'$exists': True}}},
		{'$group': {'_id': {'year': '$year', 'month': '$month', 'day': '$day'}, 'station_count': {'$addToSet': '$station_name'}}},
		{'$addFields': {'num_stations': {'$size': '$station_count'}}},
		{
			'$match': {'num_stations': unique_stations}  # Only dates with all stations
		},
		{'$sort': {'_id.year': -1, '_id.month': -1, '_id.day': -1}},
		{'$limit': 1},
	]

	result = list(collection.aggregate(pipeline))

	if result:
		date_info = result[0]['_id']
		date_str = f'{date_info["year"]}-{date_info["month"]:02d}-{date_info["day"]:02d}'
		return {'year': date_info['year'], 'month': date_info['month'], 'day': date_info['day'], 'date_str': date_str}

	return None


def get_data_for_date(year, month, day):
	"""
	Get all measurements for a specific date across all stations.

	Args:
	    year: Year
	    month: Month (1-12)
	    day: Day (1-31)

	Returns:
	    list: List of measurement documents for that date
	"""
	collection = get_collection()
	return list(collection.find({'year': year, 'month': month, 'day': day}).sort('station_name', 1))


def get_most_recent_data_for_station(station_name):
	"""
	Get the most recent measurement for a specific station.

	Args:
	    station_name: Name of the station

	Returns:
	    dict or None: Most recent measurement document
	"""
	collection = get_collection()
	return collection.find_one({'station_name': station_name}, sort=[('year', -1), ('month', -1), ('day', -1)])


def get_station_data_for_month(station_name, year, month):
	"""
	Get all measurements for a specific station in a given month.

	Args:
	    station_name: Name of the station
	    year: Year
	    month: Month (1-12)

	Returns:
	    list: List of measurement documents sorted by day
	"""
	collection = get_collection()
	return list(
		collection.find({'station_name': station_name, 'year': year, 'month': month}).sort([('day', 1)])
	)


def extract_region_from_station_name(station_name):
	"""
	Extract region from station name using common patterns.
	Handles formats like: "AtlanticOcean_Caribbean_FlowerGardenBanks_*"

	Args:
	    station_name: Station name from the database

	Returns:
	    str: Region name or the original station name if region cannot be extracted
	"""
	# Handle common patterns
	if 'AtlanticOcean_Caribbean' in station_name:
		if 'FlowerGardenBanks' in station_name:
			return 'Atlantic - Flower Garden Banks'
		elif 'PuertoRico' in station_name:
			return 'Atlantic - Puerto Rico'
	elif 'florida' in station_name.lower():
		return 'Florida Keys'
	elif 'USVI' in station_name or 'usvi' in station_name.lower():
		return 'US Virgin Islands'
	elif 'samoa' in station_name.lower():
		return 'Samoa'
	elif 'guam' in station_name.lower():
		return 'Guam'
	elif 'rota' in station_name.lower():
		return 'Rota'
	elif 'saipan' in station_name.lower() or 'tinian' in station_name.lower():
		return 'Saipan/Tinian'

	# Extract from underscore-separated names
	parts = station_name.split('_')
	if len(parts) > 1:
		return parts[0].replace('_', ' ')

	return station_name


def get_stations_by_region():
	"""
	Get all stations grouped by region.

	Returns:
	    dict: Dictionary with region names as keys and list of stations as values
	"""
	stations = get_all_stations()
	regions = {}

	for station in stations:
		region = extract_region_from_station_name(station.get('station_name', 'Unknown'))
		if region not in regions:
			regions[region] = []
		regions[region].append(station)

	return regions


def get_unique_oceans():
	"""
	Get all unique oceans from the station_mappings collection.

	Returns:
	    list: Sorted list of ocean names
	"""
	try:
		collection = get_collection('station_mappings')
		oceans = collection.distinct('ocean')
		return sorted([o for o in oceans if o])
	except Exception:
		return []


def get_unique_regions(ocean=None):
	"""
	Get all unique regions, optionally filtered by ocean.

	Args:
	    ocean: Optional ocean name to filter by

	Returns:
	    list: Sorted list of region names
	"""
	try:
		collection = get_collection('station_mappings')
		query = {}
		if ocean:
			query['ocean'] = ocean
		regions = collection.distinct('region', query)
		return sorted([r for r in regions if r])
	except Exception:
		return []


def get_ocean_for_region(region):
	"""
	Get the ocean for a given region.

	Args:
	    region: Region name

	Returns:
	    str: Ocean name or None if not found
	"""
	try:
		collection = get_collection('station_mappings')
		result = collection.find_one({'region': region}, {'ocean': 1})
		return result['ocean'] if result else None
	except Exception:
		return None


def get_unique_subregions(ocean, region):
	"""
	Get all unique subregions for a given ocean and region.

	Args:
	    ocean: Ocean name
	    region: Region name

	Returns:
	    list: Sorted list of subregion names (empty string if no subregion)
	"""
	try:
		collection = get_collection('station_mappings')
		subregions = collection.distinct('subregion', {'ocean': ocean, 'region': region})
		# Filter out None and empty strings, keep them sorted
		return sorted([s for s in subregions if s])
	except Exception:
		return []


def get_stations_by_ocean_region(ocean, region=None, subregion=None):
	"""
	Get all station names for a given ocean, optionally filtered by region and subregion.

	Args:
	    ocean: Ocean name
	    region: Optional region name
	    subregion: Optional subregion name

	Returns:
	    list: List of station names
	"""
	try:
		collection = get_collection('station_mappings')
		query = {'ocean': ocean}
		if region:
			query['region'] = region
		if subregion:
			query['subregion'] = subregion

		mappings = list(collection.find(query).sort('station_name', 1))
		return [m['station_name'] for m in mappings]
	except Exception:
		return []
