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
		print(f'⚠ Could not start scheduler: {e}')
		st.session_state.scheduler_started = False

st.title('🪸 Reef Streamlit App')

# Navigation
st.sidebar.title('Navigation')
page = st.sidebar.radio('Go to:', ['Home', 'Query Database'])

if page == 'Home':
	try:
		import pandas as pd
		import plotly.express as px

		from mongo.db_utils import get_all_stations, get_collection, get_data_summary

		# Display summary metrics
		st.subheader('Database Overview')
		summary = get_data_summary()

		col1, col2, col3, col4 = st.columns(4)
		with col1:
			st.metric('📊 Total Records', f'{summary["total_records"]:,}')
		with col2:
			st.metric('📍 Total Stations', summary.get('unique_stations', 'N/A'))
		with col3:
			if summary.get('oldest_record'):
				st.metric('📅 Oldest Record', summary['oldest_record'])
		with col4:
			if summary.get('newest_record'):
				st.metric('📅 Latest Record', summary['newest_record'])

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

			# Chart: Datapoints by Station
			if not stations_df.empty:
				fig = px.bar(
					stations_df.sort_values('Datapoints', ascending=True),
					y='Station',
					x='Datapoints',
					orientation='h',
					title='Data Distribution by Station',
					labels={'Datapoints': 'Number of Records'},
					color='Datapoints',
					color_continuous_scale='Blues',
				)
				fig.update_layout(height=400, showlegend=False)
				st.plotly_chart(fig, use_container_width=True)

				# Display station table
				with st.expander('📋 View All Stations', expanded=False):
					st.dataframe(stations_df, use_container_width=True, hide_index=True)
		else:
			st.warning('No stations found in database.')

		st.divider()

		# Quick Stats
		st.subheader('Quick Actions')
		col1, col2 = st.columns(2)
		with col1:
			if st.button('🔍 Go to Query Database', use_container_width=True):
				st.switch_page('pages/Query Database')
		with col2:
			if st.button('📊 View Recent Data', use_container_width=True):
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
