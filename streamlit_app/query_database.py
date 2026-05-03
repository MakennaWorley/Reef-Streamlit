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
	query_type = st.radio('Select Query Type', ['View All Stations', 'Search by Name (LIKE)', 'Query by Station', 'Advanced Query'])

	if query_type == 'View All Stations':
		st.subheader('All Stations in Database')
		stations = get_all_stations()

		if stations:
			# Convert to DataFrame for better display
			stations_df = pd.DataFrame(stations)

			# Remove MongoDB internal ID for cleaner display
			if '_id' in stations_df.columns:
				stations_df = stations_df.drop('_id', axis=1)

			# Reorder columns for better readability
			if 'station_name' in stations_df.columns:
				cols = ['station_name', 'latitude', 'longitude', 'datapoint_count']
				stations_df = stations_df[[col for col in cols if col in stations_df.columns]]
				stations_df = stations_df.rename(
					columns={'station_name': 'Station Name', 'latitude': 'Latitude', 'longitude': 'Longitude', 'datapoint_count': 'Datapoints'}
				)

			st.dataframe(stations_df, use_container_width=True, hide_index=True)

			st.info(f'Total: {len(stations)} station(s)')
		else:
			st.warning('No stations found in database. Have you loaded the data yet?')

	elif query_type == 'Search by Name (LIKE)':
		st.subheader('Search Stations (Pattern Matching)')

		search_pattern = st.text_input(
			'Enter search term (e.g., "florida", "key*", or just part of name):',
			help='Search is case-insensitive. Use * as wildcard for partial matches.',
		)

		if st.button('Search', key='search_btn'):
			if search_pattern:
				with st.spinner(f'Searching for "{search_pattern}"...'):
					try:
						# Build regex pattern for LIKE search
						# Convert simple wildcards to regex
						import re

						# Escape special regex characters except *
						pattern = search_pattern.replace('.', r'\.')
						pattern = pattern.replace('?', '.')
						pattern = pattern.replace('*', '.*')

						collection = get_collection()
						query = {'station_name': {'$regex': pattern, '$options': 'i'}}  # i = case-insensitive
						results = list(collection.find(query).distinct('station_name'))

						if results:
							st.success(f'Found {len(results)} matching station(s)')

							# Show matching stations
							for station_name in sorted(results):
								station_data = get_station_data(station_name)
								if station_data:
									with st.expander(f'{station_name} ({len(station_data)} records)'):
										data_df = pd.DataFrame(station_data)
										if '_id' in data_df.columns:
											data_df = data_df.drop('_id', axis=1)
										st.dataframe(data_df, use_container_width=True, hide_index=True)

										# Download button
										csv = data_df.to_csv(index=False)
										st.download_button(
											label='Download as CSV',
											data=csv,
											file_name=f'{station_name}_data.csv',
											mime='text/csv',
											key=f'download_{station_name}',
										)
						else:
							st.warning(f'No stations found matching "{search_pattern}"')
					except Exception as e:
						st.error(f'Search error: {e}')
			else:
				st.info('Enter a search term to begin')

	elif query_type == 'Query by Station':
		st.subheader('Query Data by Station')

		# Get list of stations
		stations = get_all_stations()
		if stations:
			# Create station options with datapoint counts
			station_options = sorted([f'{s.get("station_name", "Unknown")} ({s.get("datapoint_count", 0):,} datapoints)' for s in stations])
			selected_station_display = st.selectbox('Select a Station', station_options)

			# Extract station name from display (remove datapoint count)
			selected_station = selected_station_display.split(' (')[0]

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
		st.subheader('Advanced Query - MongoDB JSON Format')

		# Get collection for direct queries
		collection = get_collection()

		with st.expander('📚 Query Help & Examples', expanded=False):
			st.markdown("""
            ### MongoDB Query Syntax
            
            **Basic Examples:**
            - `{}` - All documents
            - `{"station_name": "Florida Keys"}` - Exact match
            - `{"station_name": {"$regex": "florida", "$options": "i"}}` - Case-insensitive pattern match
            
            **Comparison Operators:**
            - `{"year": {"$gt": 2023}}` - Greater than
            - `{"year": {"$lt": 2024}}` - Less than  
            - `{"year": {"$gte": 2023}}` - Greater than or equal
            - `{"day": {"$eq": 15}}` - Equals
            
            **Array/Multiple Values:**
            - `{"month": {"$in": [1, 2, 3]}}` - Match multiple months
            - `{"year": {"$nin": [2020, 2021]}}` - Exclude years
            
            **Complex Queries:**
            - `{"year": 2023, "month": {"$gte": 6}}` - AND condition
            - `{"$or": [{"year": 2023}, {"year": 2024}]}` - OR condition
            
            **Date Filtering (by year/month/day):**
            - `{"year": 2023, "month": 6, "day": {"$gte": 15}}` - From June 15, 2023 onward
            """)

		# Query templates
		col1, col2 = st.columns(2)
		template = None
		with col1:
			template = st.selectbox(
				'📋 Load a template:', ['Custom Query', 'All Records', 'By Station Name', 'By Year', 'By Month Range', 'By Date Range']
			)

		default_query = '{}'
		if template == 'By Station Name':
			default_query = '{"station_name": "Florida Keys"}'
		elif template == 'By Year':
			default_query = '{"year": 2024}'
		elif template == 'By Month Range':
			default_query = '{"year": 2024, "month": {"$in": [1, 2, 3]}}'
		elif template == 'By Date Range':
			default_query = '{"year": 2024, "month": 6, "day": {"$gte": 1, "$lte": 15}}'
		elif template == 'All Records':
			default_query = '{}'

		# Query input
		query_str = st.text_area('Enter MongoDB Query (JSON format):', value=default_query, height=120, help='Enter a valid MongoDB query as JSON')

		col1, col2, col3 = st.columns(3)
		with col1:
			limit = st.number_input('Limit results to:', min_value=1, max_value=10000, value=100)
		with col2:
			sort_field = st.text_input('Sort by field (optional):', value='', placeholder='e.g., station_name')
		with col3:
			sort_order = st.radio('Sort order:', ['Ascending ↑', 'Descending ↓'])
			sort_direction = 1 if sort_order == 'Ascending ↑' else -1

		if st.button('Execute Query', type='primary'):
			try:
				# Parse the query
				import json

				query = json.loads(query_str)

				# Execute query
				with st.spinner('Executing query...'):
					if sort_field:
						results = list(collection.find(query).sort(sort_field, sort_direction).limit(limit))
					else:
						results = list(collection.find(query).limit(limit))

				if results:
					st.success(f'✓ Found {len(results)} document(s)')

					# Convert to DataFrame
					results_df = pd.DataFrame(results)

					# Remove MongoDB internal ID
					if '_id' in results_df.columns:
						results_df = results_df.drop('_id', axis=1)

					# Display results with options
					st.dataframe(results_df, use_container_width=True, hide_index=True)

					# Download and stats
					col1, col2 = st.columns(2)
					with col1:
						csv = results_df.to_csv(index=False)
						st.download_button(label='⬇️ Download as CSV', data=csv, file_name='query_results.csv', mime='text/csv')
					with col2:
						st.metric('Columns', len(results_df.columns))
				else:
					st.info('No documents matched the query.')

			except json.JSONDecodeError as e:
				st.error(f'❌ Invalid JSON: {e}')
				st.info('Make sure your query is valid JSON. Check the Help section for examples.')
			except Exception as e:
				st.error(f'❌ Query error: {e}')

except Exception as e:
	st.error(f'Database connection error: {e}')
	st.info('Make sure MongoDB is running: `docker-compose up -d mongodb`')
