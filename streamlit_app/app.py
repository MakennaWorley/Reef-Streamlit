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
		import plotly.graph_objects as go
		from plotly.subplots import make_subplots
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
			get_station_data_for_month,
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

				# --- Globe (click a dot to select that station) ---
				st.markdown('**Click a station dot on the globe to select it below, or use the dropdown directly.**')
				import plotly.colors as pc

				tab_stations_df = pd.DataFrame(
					[
						{
							'Station': s.get('station_name', 'Unknown'),
							'Latitude': s.get('latitude'),
							'Longitude': s.get('longitude'),
						}
						for s in stations
					]
				)
				mappings_path_tab = os.path.join(os.path.dirname(__file__), '..', 'data_scraper', 'station_mappings.csv')
				station_mappings_tab = pd.read_csv(mappings_path_tab)[['station_name', 'region']]
				globe_tab_df = tab_stations_df.dropna(subset=['Latitude', 'Longitude']).merge(
					station_mappings_tab, left_on='Station', right_on='station_name', how='left'
				)
				globe_tab_df['region'] = globe_tab_df['region'].fillna('Unknown')

				region_list_tab = sorted(globe_tab_df['region'].unique())
				color_seq_tab = pc.qualitative.Light24
				region_colors_tab = {r: color_seq_tab[i % len(color_seq_tab)] for i, r in enumerate(region_list_tab)}

				fig_globe_tab = go.Figure()
				for region_name in region_list_tab:
					rdf_tab = globe_tab_df[globe_tab_df['region'] == region_name]
					fig_globe_tab.add_trace(
						go.Scattergeo(
							lat=rdf_tab['Latitude'],
							lon=rdf_tab['Longitude'],
							text=rdf_tab['Station'],
						customdata=rdf_tab['Station'].tolist(),
						name=region_name,
						mode='markers',
						marker=dict(
							size=10,
							color=region_colors_tab[region_name],
							opacity=0.9,
							line=dict(width=1, color='white'),
						),
						hovertemplate='<b>%{text}</b><br>Region: ' + region_name + '<br>Lat: %{lat:.3f}<br>Lon: %{lon:.3f}<br><i>Click to select</i><extra></extra>',
						)
					)
				fig_globe_tab.update_layout(
					clickmode='event+select',
					uirevision='globe_tab',
					geo=dict(
						projection_type='orthographic',
						showland=True,
						landcolor='rgb(210, 230, 200)',
						showocean=True,
						oceancolor='rgb(50, 120, 200)',
						showlakes=True,
						lakecolor='rgb(80, 150, 220)',
						showrivers=False,
						showcountries=True,
						countrycolor='rgb(160, 160, 160)',
						countrywidth=0.5,
						showcoastlines=True,
						coastlinecolor='rgb(80, 80, 80)',
						coastlinewidth=0.8,
						bgcolor='rgba(0,0,0,0)',
						showframe=False,
						projection=dict(rotation=dict(lon=0, lat=20, roll=0)),
					),
					legend=dict(
						title='Region',
						bgcolor='rgba(0,0,0,0.85)',
						bordercolor='rgba(0,0,0,0.2)',
						borderwidth=1,
						itemsizing='constant',
					),
					height=900,
					margin=dict(t=10, b=10, l=10, r=10),
					paper_bgcolor='rgba(0,0,0,0)',
				)

				globe_event = st.plotly_chart(fig_globe_tab, use_container_width=True, on_select='rerun', selection_mode='points', key='globe_tab_chart')
				if globe_event and globe_event.selection and globe_event.selection.points:
					pt = globe_event.selection.points[0]
					# customdata is a list element when returned from Streamlit
					raw = pt.get('customdata')
					clicked_station = raw[0] if isinstance(raw, list) else (raw or pt.get('text'))
					if clicked_station and clicked_station in station_names:
						st.session_state['station_select'] = clicked_station

				st.divider()

				selected_station = st.selectbox('Select a station:', station_names, key='station_select')

				# Get available years and months for this station
				collection = get_collection()
				all_dates = list(collection.find({'station_name': selected_station}, {'year': 1, 'month': 1}).distinct('year'))
				available_years = sorted(
					set(doc.get('year') for doc in collection.find({'station_name': selected_station}, {'year': 1}) if doc.get('year')), reverse=True
				)

				if available_years:
					# Month name mapping
					month_names = {
						1: 'January',
						2: 'February',
						3: 'March',
						4: 'April',
						5: 'May',
						6: 'June',
						7: 'July',
						8: 'August',
						9: 'September',
						10: 'October',
						11: 'November',
						12: 'December',
					}

					# Year and month selectors
					col1, col2 = st.columns(2)
					with col1:
						# Default to 2026 if available, otherwise first year
						default_year_idx = 0
						if 2026 in available_years:
							default_year_idx = available_years.index(2026)
						selected_year = st.selectbox('Select year:', available_years, index=default_year_idx, key='station_year')

					# Get available months for selected year
					available_months = sorted(
						set(
							doc.get('month')
							for doc in collection.find({'station_name': selected_station, 'year': selected_year}, {'month': 1})
							if doc.get('month')
						)
					)

					with col2:
						# Create month display options
						month_options = [(m, month_names.get(m, str(m))) for m in available_months]

						# Default to May (5) if available, otherwise first month
						default_month_idx = 0
						if any(m[0] == 5 for m in month_options):
							default_month_idx = next(i for i, m in enumerate(month_options) if m[0] == 5)

						selected_month_name = st.selectbox(
							'Select month:', [m[1] for m in month_options], index=default_month_idx, key='station_month'
						)

						# Get the numeric month value
						selected_month = next(m[0] for m in month_options if m[1] == selected_month_name)

					# Get data for the selected month
					month_data = get_station_data_for_month(selected_station, selected_year, selected_month)

					if month_data:
						df_month = pd.DataFrame(month_data)

						# Get ocean and region info from station mappings
						mappings_path = os.path.join(os.path.dirname(__file__), '..', 'data_scraper', 'station_mappings.csv')
						station_mappings = pd.read_csv(mappings_path)
						station_row = station_mappings[station_mappings['station_name'] == selected_station]

						# Build info text with station metadata
						info_text = f'**{selected_station}** - {selected_year}-{selected_month:02d} ({len(month_data)} days of data)'
						if not station_row.empty:
							ocean = station_row.iloc[0]['ocean']
							region = station_row.iloc[0]['region']
							subregion = station_row.iloc[0]['subregion']

							info_text += f'\n**Ocean:** {ocean} | **Region:** {region}'
							if pd.notna(subregion) and subregion.strip():
								info_text += f' | **Subregion:** {subregion}'

						# Display info
						st.info(info_text)

						# Define metric columns to graph
						metric_columns = ['SST_MIN', 'SST_MAX', 'SST@90th_HS', 'SSTA@90th_HS', '90th_HS>0', 'DHW_from_90th_HS>1', 'BAA_7day_max']

						# Filter to available metrics (only show if column exists AND has data)
						available_metrics = []
						for col in metric_columns:
							if col in df_month.columns:
								# Check if column has any non-null values after numeric conversion
								numeric_col = pd.to_numeric(df_month[col], errors='coerce')
								if numeric_col.notna().any():
									available_metrics.append(col)

						if available_metrics:
							from visualization_utils import METRIC_EXPLANATIONS

							# Create a column for date string for x-axis
							df_month['date'] = pd.to_datetime(
								df_month[['year', 'month', 'day']].rename(columns={'year': 'Year', 'month': 'Month', 'day': 'Day'}), errors='coerce'
							)

							# Render each metric with its title and help button above its own chart
							num_metrics = len(available_metrics)
							num_rows = (num_metrics + 1) // 2

							metric_colors = {
								'SST_MIN': '#636EFA',
								'SST_MAX': '#EF553B',
								'SST@90th_HS': '#00CC96',
								'SSTA@90th_HS': '#AB63FA',
								'90th_HS>0': '#FFA15A',
								'DHW_from_90th_HS>1': '#19D3F3',
								'BAA_7day_max': '#FF6692',
							}

							# Note: bar chart colors (Min=#636EFA, Max=#EF553B, Mean=#00CC96) match
							# SST_MIN, SST_MAX, and SST@90th_HS line colors above

							for row_idx in range(num_rows):
								cols = st.columns(2)
								for col_idx in range(2):
									metric_idx = row_idx * 2 + col_idx
									if metric_idx < num_metrics:
										metric = available_metrics[metric_idx]
										color = metric_colors.get(metric, '#636EFA')
										with cols[col_idx]:
											# Title and help button above the chart
											title_col1, title_col2 = st.columns([0.9, 0.1])
											with title_col1:
												st.subheader(metric)
											with title_col2:
												if metric in METRIC_EXPLANATIONS:
													with st.popover('❓'):
														st.markdown(METRIC_EXPLANATIONS[metric])

											# Individual chart for this metric
											numeric_values = pd.to_numeric(df_month[metric], errors='coerce')
											fig = go.Figure()
											fig.add_trace(
												go.Scatter(
													x=df_month['date'],
													y=numeric_values,
													mode='lines+markers',
													name=metric,
													line=dict(width=2, color=color),
													marker=dict(color=color),
													hovertemplate='<b>' + metric + '</b><br>Date: %{x|%Y-%m-%d}<br>Value: %{y}<extra></extra>',
												)
											)
											fig.update_layout(
												height=300,
												showlegend=False,
												hovermode='x unified',
												xaxis_title='Date',
												yaxis_title='Value',
												margin=dict(t=10, b=40),
											)
											st.plotly_chart(fig, use_container_width=True)
						else:
							st.warning('No metric data available for this period.')
					else:
						st.warning(f'No data found for {selected_station} in {selected_year}-{selected_month:02d}.')
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
						selected_subregion = st.selectbox(
							'Select a subregion (optional):', ['All Subregions'] + subregions, key='region_tab_subregion'
						)
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
