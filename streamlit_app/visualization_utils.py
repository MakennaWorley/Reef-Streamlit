"""
Reusable visualization utilities for Streamlit app.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

# Standard metric columns to visualize
STANDARD_METRIC_COLUMNS = ['SST_MIN', 'SST_MAX', 'SST@90th_HS', 'SSTA@90th_HS', '90th_HS>0', 'DHW_from_90th_HS>1', 'BAA_7day_max']

# Explanations for each metric
METRIC_EXPLANATIONS = {
	'SST_MIN': """**SST_MIN (Sea Surface Temperature Minimum)**

These represent the minimum daily 5km satellite sea surface temperatures (SST) recorded within a specific region on a given day. They show the range of temperatures corals are currently experiencing.""",
	'SST_MAX': """**SST_MAX (Sea Surface Temperature Maximum)**

These represent the maximum daily 5km satellite sea surface temperatures (SST) recorded within a specific region on a given day. If the SST_MAX is consistently high, it indicates the peak heat stress the reef is facing.""",
	'SST@90th_HS': """**SST@90th_HS (SST at the 90th Percentile HotSpot)**

This is the Sea Surface Temperature value associated with the 90th percentile of all HotSpot pixels in a region.

**The "90th Percentile" Rule:** NOAA uses the 90th percentile (rather than a simple average) to ensure that the reported stress level reflects the more severe conditions occurring within a region, rather than being "watered down" by cooler pixels.""",
	'SSTA@90th_HS': """**SSTA@90th_HS (SST Anomaly at the 90th Percentile HotSpot)**

The SST Anomaly (SSTA) is the difference between the current temperature and the "normal" temperature (the long-term average for that time of year).

**What it means:** If this value is +2.0, it means the water is 2°C warmer than the historical average for this specific date.""",
	'90th_HS>0': """**90th_HS > 0 (The HotSpot Value)**

A HotSpot (HS) measures how much the current SST exceeds the Maximum Monthly Mean (MMM)—the temperature of the warmest month in a typical year.

**Interpretation:**
- **HS = 0:** No thermal stress
- **HS > 0:** The water is warmer than the peak of a "normal" summer
- **HS ≥ 1.0:** This is the critical threshold. When the water is 1°C or more above the MMM, corals begin to experience significant heat stress.""",
	'DHW_from_90th_HS>1': """**DHW_from_90th_HS > 1 (Degree Heating Weeks)**

Degree Heating Weeks (DHW) measure the accumulation of heat stress over a rolling 12-week (3-month) period.

**How it's calculated:** It sums up the HotSpot values (specifically those ≥ 1°C) over the last 12 weeks.

**Significance:**
- **DHW > 4:** Significant bleaching is likely
- **DHW > 8:** Severe, widespread bleaching and coral mortality are likely

**Note:** The "from 90th HS" indicates this accumulation is based on the 90th percentile HotSpot values.""",
	'BAA_7day_max': """**BAA_7day_max (Bleaching Alert Area 7-Day Maximum)**

This is a summary alert level that combines the HotSpot and DHW data. It tells you the highest (maximum) alert level reached in the last 7 days.

**The Alert Levels:**
- **No Stress:** HotSpot ≤ 0
- **Bleaching Watch:** 0 < HotSpot < 1
- **Bleaching Warning:** HotSpot ≥ 1 but DHW < 4
- **Alert Level 1:** HotSpot ≥ 1 and 4 ≤ DHW < 8 (Bleaching likely)
- **Alert Level 2+:** HotSpot ≥ 1 and DHW ≥ 8 (Widespread bleaching and mortality)""",
}


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

				# Create title with popover explanation
				title_col1, title_col2 = st.columns([0.9, 0.1])
				with title_col1:
					st.subheader(metric)
				with title_col2:
					if metric in METRIC_EXPLANATIONS:
						with st.popover('❓'):
							st.markdown(METRIC_EXPLANATIONS[metric])

				# Create a simple bar chart showing min/max/mean
				chart_data = pd.DataFrame({'Metric': ['Min', 'Max', 'Mean'], 'Value': [min_val, max_val, mean_val]})

				fig = px.bar(
					chart_data,
					x='Metric',
					y='Value',
					title=f'{title_suffix} ({len(valid_data)} values)',
					color='Metric',
					color_discrete_map={'Min': '#636EFA', 'Max': '#EF553B', 'Mean': '#00CC96'},
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
