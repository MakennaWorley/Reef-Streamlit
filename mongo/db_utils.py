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
	Create indexes for faster queries.
	"""
	collection = get_collection()

	# Index on station name for quick lookups
	collection.create_index('station_name')
	print("✓ Created index on 'station_name' field")

	# Index on date for time-series queries
	collection.create_index([('year', 1), ('month', 1), ('day', 1)])
	print('✓ Created index on date fields')

	# Index on stations collection
	stations = get_collection(STATIONS_COLLECTION)
	stations.create_index('station_name', unique=True)
	print("✓ Created index on 'station_name' in stations collection")


def insert_records(records, collection_name=COLLECTION_NAME):
	"""
	Insert multiple records into the collection.

	Args:
	    records: List of dictionaries to insert
	    collection_name: Name of the collection

	Returns:
	    int: Number of inserted records
	"""
	if not records:
		return 0

	collection = get_collection(collection_name)
	result = collection.insert_many(records)
	return len(result.inserted_ids)


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
	Get list of all stations with their location data.

	Returns:
	    list: List of station documents with name, longitude, latitude
	"""
	stations = get_collection(STATIONS_COLLECTION)
	return list(stations.find().sort('station_name', 1))


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

	Returns:
	    dict: Summary including total records, stations, date range
	"""
	collection = get_collection()

	total_records = collection.count_documents({})

	stations_collection = get_collection(STATIONS_COLLECTION)
	unique_stations = stations_collection.count_documents({})

	# Get date range - look for records with all date fields
	oldest = collection.find_one(
		{'year': {'$exists': True}, 'month': {'$exists': True}, 'day': {'$exists': True}}, sort=[('year', 1), ('month', 1), ('day', 1)]
	)
	newest = collection.find_one(
		{'year': {'$exists': True}, 'month': {'$exists': True}, 'day': {'$exists': True}}, sort=[('year', -1), ('month', -1), ('day', -1)]
	)

	return {
		'total_records': total_records,
		'unique_stations': unique_stations,
		'oldest_record': f'{oldest["year"]}-{oldest["month"]:02d}-{oldest["day"]:02d}' if oldest else 'N/A',
		'newest_record': f'{newest["year"]}-{newest["month"]:02d}-{newest["day"]:02d}' if newest else 'N/A',
	}
