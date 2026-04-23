"""
Database Query Page - Browse and query reef data from MongoDB
"""

import os
import sys

import pandas as pd
import streamlit as st

# Add parent directory to path so we can import db_utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mongo.db_utils import get_all_stations, get_collection, get_data_summary, get_station_data

st.header('📊 Query Reef Database')

try:
	# Display database summary
	st.subheader('Database Summary')

	summary = get_data_summary()

	col1, col2, col3 = st.columns(3)
	with col1:
		st.metric('Total Records', f'{summary["total_records"]:,}')
	with col2:
		st.metric('Total Stations', summary.get('unique_stations', 'N/A'))
	with col3:
		if summary.get('oldest_record') and summary.get('newest_record'):
			st.metric('Date Range', f'{summary["oldest_record"]} to {summary["newest_record"]}')

	st.divider()

	# Query options
	query_type = st.radio('Select Query Type', ['View All Stations', 'Query by Station', 'Advanced Query'])

	if query_type == 'View All Stations':
		st.subheader('All Stations in Database')
		stations = get_all_stations()

		if stations:
			# Convert to DataFrame for better display
			stations_df = pd.DataFrame(stations)

			# Remove MongoDB internal ID for cleaner display
			if '_id' in stations_df.columns:
				stations_df = stations_df.drop('_id', axis=1)

			st.dataframe(stations_df, use_container_width=True, hide_index=True)

			st.info(f'Total: {len(stations)} station(s)')
		else:
			st.warning('No stations found in database. Have you loaded the data yet?')

	elif query_type == 'Query by Station':
		st.subheader('Query Data by Station')

		# Get list of stations
		stations = get_all_stations()
		if stations:
			station_names = sorted([s.get('station_name', 'Unknown') for s in stations])
			selected_station = st.selectbox('Select a Station', station_names)

			if st.button('Load Station Data'):
				with st.spinner(f'Loading data for {selected_station}...'):
					station_data = get_station_data(selected_station)

				if station_data:
					st.success(f'Found {len(station_data)} records')

					# Convert to DataFrame
					data_df = pd.DataFrame(station_data)

					# Remove MongoDB internal ID
					if '_id' in data_df.columns:
						data_df = data_df.drop('_id', axis=1)

					# Display the data
					st.dataframe(data_df, use_container_width=True, hide_index=True)

					# Option to download as CSV
					csv = data_df.to_csv(index=False)
					st.download_button(label='Download as CSV', data=csv, file_name=f'{selected_station}_data.csv', mime='text/csv')
				else:
					st.warning(f'No data found for {selected_station}')
		else:
			st.warning('No stations found in database.')

	elif query_type == 'Advanced Query':
		st.subheader('Advanced Query')

		# Get collection for direct queries
		collection = get_collection()

		with st.expander('Query Help', expanded=False):
			st.markdown("""
            Use MongoDB query syntax. Examples:
            - `{}` - All documents
            - `{"station_name": "Station Name"}` - Filter by station
            - `{"temperature": {"$gt": 25}}` - Temperature greater than 25
            - `{"year": 2023}` - Filter by year
            - `{"month": {"$in": [1, 2, 3]}}` - Filter by specific months
            """)

		# Query input
		query_str = st.text_area('Enter MongoDB Query (JSON format):', value='{}', height=100, help='Enter a valid MongoDB query as JSON')

		col1, col2 = st.columns(2)
		with col1:
			limit = st.number_input('Limit results to:', min_value=1, max_value=10000, value=100)
		with col2:
			sort_field = st.text_input('Sort by field (optional):', value='')

		if st.button('Execute Query'):
			try:
				# Parse the query
				import json

				query = json.loads(query_str)

				# Execute query
				if sort_field:
					results = list(collection.find(query).sort(sort_field, 1).limit(limit))
				else:
					results = list(collection.find(query).limit(limit))

				if results:
					st.success(f'Found {len(results)} document(s)')

					# Convert to DataFrame
					results_df = pd.DataFrame(results)

					# Remove MongoDB internal ID
					if '_id' in results_df.columns:
						results_df = results_df.drop('_id', axis=1)

					# Display results
					st.dataframe(results_df, use_container_width=True, hide_index=True)

					# Option to download
					csv = results_df.to_csv(index=False)
					st.download_button(label='Download Results as CSV', data=csv, file_name='query_results.csv', mime='text/csv')
				else:
					st.info('No documents matched the query.')

			except json.JSONDecodeError as e:
				st.error(f'Invalid JSON: {e}')
			except Exception as e:
				st.error(f'Query error: {e}')

except Exception as e:
	st.error(f'Database connection error: {e}')
	st.info('Make sure MongoDB is running: `docker-compose up -d mongodb`')
