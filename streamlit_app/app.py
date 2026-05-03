import os
import sys

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Reef Data', layout='wide')

# Initialize midnight data loader scheduler
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

if 'scheduler_started' not in st.session_state:
	try:
		from mongo.midnight_scheduler import start_scheduler

		start_scheduler()
		st.session_state.scheduler_started = True
	except Exception as e:
		print(f'WARNING: Could not start scheduler: {e}')
		st.session_state.scheduler_started = False

st.title('🪸 Reef Streamlit App')

# Navigation
st.sidebar.title('Navigation')
page = st.sidebar.radio('Go to:', ['Home', 'Query Database'])

if page == 'Home':
	try:
		import pandas as pd
		import plotly.express as px
		from visualization_utils import display_metric_ranges_stats

		from mongo.db_utils import (
			get_all_stations,
			get_collection,
			get_data_for_date,
			get_data_summary,
			get_most_recent_common_date,
			get_most_recent_data_for_station,
			get_ocean_for_region,
			get_station_data,
			get_stations_by_ocean_region,
			get_stations_by_region,
			get_unique_oceans,
			get_unique_regions,
			get_unique_subregions,
		)

		# Display summary metrics
		st.subheader('Database Overview')
		summary = get_data_summary()

		col1, col2, col3, col4 = st.columns(4)
		with col1:
			st.metric('Total Records', f'{summary["total_records"]:,}')
		with col2:
			st.metric('Total Stations', summary.get('unique_stations', 'N/A'))
		with col3:
			if summary.get('oldest_record'):
				st.metric('Oldest Record', summary['oldest_record'])
		with col4:
			if summary.get('newest_record'):
				st.metric('Latest Record', summary['newest_record'])
		st.divider()

		# Quick Actions
		st.subheader('Quick Actions')
		col1, col2 = st.columns(2)
		with col1:
			if st.button('Go to Query Database', use_container_width=True):
				st.switch_page('pages/Query Database')
		with col2:
			if st.button('View Recent Data', use_container_width=True):
				with st.spinner('Loading recent measurements...'):
					collection = get_collection()
					recent = list(collection.find().sort('_id', -1).limit(10))
					if recent:
						recent_df = pd.DataFrame(recent)
						if '_id' in recent_df.columns:
							recent_df = recent_df.drop('_id', axis=1)
						st.dataframe(recent_df, use_container_width=True, hide_index=True)
					else:
						st.info('No data available yet.')

		st.divider()

		# Create tabs for different views
		tab_all, tab_station, tab_region, tab_ocean = st.tabs(['📊 All Data', '🏝️ By Station', '🗺️ By Region', '🌊 By Ocean'])

		# TAB 1: All Data
		with tab_all:
			st.subheader('Most Recent Complete Data Day')
			common_date = get_most_recent_common_date()

			if common_date:
				date_str = common_date['date_str']
				st.info(f'Showing data from **{date_str}** (most recent day with all stations)')

				# Get data for this date
				data_records = get_data_for_date(common_date['year'], common_date['month'], common_date['day'])

				if data_records:
					df_date = pd.DataFrame(data_records)

					# Display metric ranges and stats
					display_metric_ranges_stats(df_date, title_suffix=f'Range across stations on {date_str}')
				else:
					st.warning('No data found for the most recent complete date.')
			else:
				st.warning('No common date found where all stations have data. Check data coverage.')

			st.divider()

			# Display stations and their data counts
			st.subheader('Stations & Data Distribution')
			stations = get_all_stations()

			if stations:
				# Create DataFrame for visualization
				stations_df = pd.DataFrame(
					[
						{
							'Station': s.get('station_name', 'Unknown'),
							'Datapoints': s.get('datapoint_count', 0),
							'Latitude': s.get('latitude'),
							'Longitude': s.get('longitude'),
						}
						for s in stations
					]
				)

				# Display station table
				if not stations_df.empty:
					st.dataframe(stations_df, use_container_width=True, hide_index=True)
			else:
				st.warning('No stations found in database.')

		# TAB 2: By Station
		with tab_station:
			st.subheader('View Data by Individual Station')
			stations = get_all_stations()

			if stations:
				station_names = sorted([s.get('station_name', 'Unknown') for s in stations])
				selected_station = st.selectbox('Select a station:', station_names)

				# Get the most recent data for this station
				latest_data = get_most_recent_data_for_station(selected_station)

				if latest_data:
					# Display when this data was recorded
					date_str = f'{latest_data.get("year", "N/A")}-{latest_data.get("month", 0):02d}-{latest_data.get("day", 0):02d}'
					st.info(f'Most recent data for **{selected_station}**: {date_str}')

					# Convert to DataFrame and display metrics
					df_station = pd.DataFrame([latest_data])
					display_metric_ranges_stats(df_station, title_suffix=f'Latest for {selected_station}')
				else:
					st.warning(f'No data found for station: {selected_station}')
			else:
				st.warning('No stations found in database.')

		# TAB 3: By Region
		with tab_region:
			st.subheader('View Data by Region')

			# Get all unique regions across all oceans
			all_regions = get_unique_regions()
			if not all_regions:
				st.warning('No regions found in station mappings.')
			else:
				# Region dropdown
				selected_region = st.selectbox('Select a region:', all_regions, key='region_tab_region')

				# Get ocean for this region
				ocean_for_region = get_ocean_for_region(selected_region)

				if ocean_for_region:
					# Get subregions for this region
					subregions = get_unique_subregions(ocean_for_region, selected_region)

					# If there are subregions, show dropdown; otherwise proceed with region
					if subregions:
						selected_subregion = st.selectbox('Select a subregion (optional):', ['All Subregions'] + subregions, key='region_tab_subregion')
						if selected_subregion == 'All Subregions':
							# Get all stations for this region
							region_stations = get_stations_by_ocean_region(ocean_for_region, selected_region)
						else:
							# Get stations for region and subregion
							region_stations = get_stations_by_ocean_region(ocean_for_region, selected_region, selected_subregion)
					else:
						# No subregions, just use region
						region_stations = get_stations_by_ocean_region(ocean_for_region, selected_region)

					if region_stations:
						st.info(f'**{ocean_for_region} - {selected_region}** - {len(region_stations)} station(s)')

						# Find the most recent date with data from all region stations
						collection = get_collection()

						# Find the most recent date with data from all region stations
						pipeline = [
							{
								'$match': {
									'station_name': {'$in': region_stations},
									'year': {'$exists': True},
									'month': {'$exists': True},
									'day': {'$exists': True},
								}
							},
							{'$group': {'_id': {'year': '$year', 'month': '$month', 'day': '$day'}, 'station_count': {'$addToSet': '$station_name'}}},
							{'$addFields': {'num_stations': {'$size': '$station_count'}}},
							{'$match': {'num_stations': len(region_stations)}},
							{'$sort': {'_id.year': -1, '_id.month': -1, '_id.day': -1}},
							{'$limit': 1},
						]

						result = list(collection.aggregate(pipeline))

						if result:
							date_info = result[0]['_id']
							region_date_str = f'{date_info["year"]}-{date_info["month"]:02d}-{date_info["day"]:02d}'

							# Get data for all region stations on this date
							region_data = list(
								collection.find(
									{
										'station_name': {'$in': region_stations},
										'year': date_info['year'],
										'month': date_info['month'],
										'day': date_info['day'],
									}
								).sort('station_name', 1)
							)

							if region_data:
								df_region = pd.DataFrame(region_data)
								st.info(f'Showing data from **{region_date_str}** (most recent complete date for this selection)')
								display_metric_ranges_stats(df_region, title_suffix=f'Range across {len(region_data)} stations')
							else:
								st.warning(f'No data found on {region_date_str}.')
						else:
							st.warning(f'No common date found where all selected stations have data.')
					else:
						st.warning('No stations found for the selected region.')
				else:
					st.warning('Could not determine ocean for this region.')

		# TAB 4: By Ocean
		with tab_ocean:
			st.subheader('View Data by Ocean')

			# Get all unique oceans
			oceans = get_unique_oceans()
			if not oceans:
				st.warning('No ocean data available in station mappings.')
			else:
				# Ocean dropdown
				selected_ocean = st.selectbox('Select an ocean:', oceans, key='ocean_tab_ocean')

				# Get stations for the selected ocean
				ocean_stations = get_stations_by_ocean_region(selected_ocean)

				if ocean_stations:
					st.info(f'**{selected_ocean}** - {len(ocean_stations)} station(s)')

					# Find the most recent date with data from all ocean stations
					collection = get_collection()

					# Find the most recent date with data from all ocean stations
					pipeline = [
						{
							'$match': {
								'station_name': {'$in': ocean_stations},
								'year': {'$exists': True},
								'month': {'$exists': True},
								'day': {'$exists': True},
							}
						},
						{'$group': {'_id': {'year': '$year', 'month': '$month', 'day': '$day'}, 'station_count': {'$addToSet': '$station_name'}}},
						{'$addFields': {'num_stations': {'$size': '$station_count'}}},
						{'$match': {'num_stations': len(ocean_stations)}},
						{'$sort': {'_id.year': -1, '_id.month': -1, '_id.day': -1}},
						{'$limit': 1},
					]

					result = list(collection.aggregate(pipeline))

					if result:
						date_info = result[0]['_id']
						ocean_date_str = f'{date_info["year"]}-{date_info["month"]:02d}-{date_info["day"]:02d}'

						# Get data for all ocean stations on this date
						ocean_data = list(
							collection.find(
								{
									'station_name': {'$in': ocean_stations},
									'year': date_info['year'],
									'month': date_info['month'],
									'day': date_info['day'],
								}
							).sort('station_name', 1)
						)

						if ocean_data:
							df_ocean = pd.DataFrame(ocean_data)
							st.info(f'Showing data from **{ocean_date_str}** (most recent complete date for this selection)')
							display_metric_ranges_stats(df_ocean, title_suffix=f'Range across {len(ocean_data)} stations')
						else:
							st.warning(f'No data found on {ocean_date_str}.')
					else:
						st.warning(f'No common date found where all selected stations have data.')
				else:
					st.warning('No stations found for the selected ocean.')

	except Exception as e:
		st.error(f'Dashboard error: {e}')
		st.info('Make sure MongoDB is running: `docker-compose up -d mongodb`')

elif page == 'Query Database':
	# Add parent directory to path for imports
	sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

	# Import and run the query database page
	import importlib.util

	spec = importlib.util.spec_from_file_location('query_database', os.path.join(os.path.dirname(__file__), 'query_database.py'))
	query_db_module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(query_db_module)
