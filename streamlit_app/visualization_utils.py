"""
Reusable visualization utilities for Streamlit app.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

# Standard metric columns to visualize
STANDARD_METRIC_COLUMNS = ['SST_MIN', 'SST_MAX', 'SST@90th_HS', 'SSTA@90th_HS', '90th_HS>0', 'DHW_from_90th_HS>1', 'BAA_7day_max']


def display_metric_ranges_stats(df: pd.DataFrame, metric_columns: list = None, title_suffix: str = 'Range'):
	"""
	Display metrics with bar charts showing min/max/mean and detailed stats.
	Uses a 2-column layout for better space utilization.

	Args:
	    df: DataFrame containing the metric data
	    metric_columns: List of column names to visualize. If None, uses STANDARD_METRIC_COLUMNS
	    title_suffix: Text to append to the chart title (e.g., "Range across X stations")
	"""
	if metric_columns is None:
		metric_columns = STANDARD_METRIC_COLUMNS

	# Filter to only columns that exist in the dataframe
	available_metrics = [col for col in metric_columns if col in df.columns]

	if not available_metrics:
		st.warning('No metric data available.')
		return

	# Create two columns for better layout
	col1, col2 = st.columns(2)

	# Display range visualization for each metric
	for idx, metric in enumerate(available_metrics):
		with col1 if idx % 2 == 0 else col2:
			# Convert to numeric, handling NaN values
			metric_data = pd.to_numeric(df[metric], errors='coerce')
			valid_data = metric_data.dropna()

			if len(valid_data) > 0:
				min_val = valid_data.min()
				max_val = valid_data.max()
				mean_val = valid_data.mean()

				# Create a simple bar chart showing min/max/mean
				chart_data = pd.DataFrame({'Metric': ['Min', 'Max', 'Mean'], 'Value': [min_val, max_val, mean_val]})

				fig = px.bar(
					chart_data,
					x='Metric',
					y='Value',
					title=f'{metric} - {title_suffix} ({len(valid_data)} values)',
					color='Metric',
					color_discrete_map={'Min': '#3498db', 'Max': '#e74c3c', 'Mean': '#2ecc71'},
				)
				fig.update_layout(height=300, showlegend=False)
				st.plotly_chart(fig, use_container_width=True)

				# Show detailed stats
				stats_col1, stats_col2, stats_col3 = st.columns(3)
				with stats_col1:
					st.metric('Minimum', f'{min_val:.2f}')
				with stats_col2:
					st.metric('Maximum', f'{max_val:.2f}')
				with stats_col3:
					st.metric('Mean', f'{mean_val:.2f}')
