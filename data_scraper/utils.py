"""
Utility functions for data scraping and processing.
"""

import os
from datetime import datetime
from urllib.parse import urljoin

import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Column name mapping: simple format -> standard detailed format
COLUMN_MAPPING = {
	'SST': 'SST_MIN',
	'SSTA': 'SSTA@90th_HS',
	'HS': '90th_HS>0',
	'DHW': 'DHW_from_90th_HS>1',
	'BAA': 'BAA_7day_max',
	'BAA_7Day_Max': 'BAA_7day_max',
}

# Standard column set (detailed format)
STANDARD_COLUMNS = ['YYYY', 'MM', 'DD', 'SST_MIN', 'SST_MAX', 'SST@90th_HS', 'SSTA@90th_HS', '90th_HS>0', 'DHW_from_90th_HS>1', 'BAA_7day_max']


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
	"""
	Normalize column names from different NOAA formats to standard format.
	Maps simple column names to detailed names, removes duplicates, and adds missing columns.

	Args:
	    df: DataFrame with potentially non-standard column names

	Returns:
	    DataFrame with all standard columns in correct order
	"""
	# Rename columns according to mapping
	df = df.rename(columns=COLUMN_MAPPING)

	# Drop duplicate columns (keep first occurrence)
	df = df.loc[:, ~df.columns.duplicated(keep='first')]

	# Add missing columns with NaN values
	for col in STANDARD_COLUMNS:
		if col not in df.columns:
			df[col] = None

	# Keep only standard columns in standard order
	df = df[STANDARD_COLUMNS]

	return df


def extract_station_metadata(txt_content: str) -> dict:
	"""
	Extract station name and coordinates from txt content.

	Args:
	    txt_content: Raw txt content as string

	Returns:
	    Dictionary with 'name', 'latitude', 'longitude' or None if not found
	"""
	try:
		lines = txt_content.split('\n')
		metadata = {}

		for i, line in enumerate(lines):
			if 'Name:' in line and i + 1 < len(lines):
				metadata['name'] = lines[i + 1].strip()
			# Try both formats for latitude/longitude
			elif 'Latitude:' in line and i + 1 < len(lines):
				try:
					metadata['latitude'] = float(lines[i + 1].strip())
				except ValueError:
					pass
			elif 'Polygon Middle Latitude:' in line and i + 1 < len(lines):
				try:
					metadata['latitude'] = float(lines[i + 1].strip())
				except ValueError:
					pass
			elif 'Longitude:' in line and i + 1 < len(lines):
				try:
					metadata['longitude'] = float(lines[i + 1].strip())
				except ValueError:
					pass
			elif 'Polygon Middle Longitude:' in line and i + 1 < len(lines):
				try:
					metadata['longitude'] = float(lines[i + 1].strip())
				except ValueError:
					pass

		if all(k in metadata for k in ['name', 'latitude', 'longitude']):
			return metadata
		return None
	except Exception as e:
		print(f'  ✗ Error extracting metadata: {e}')
		return None


def update_station_locations_csv(new_stations: list, csv_path: str = None):
	"""
	Update _station_location.csv with new station data.

	Args:
	    new_stations: List of dictionaries with 'name', 'latitude', 'longitude', and optionally 'filename'
	    csv_path: Path to _station_location.csv (defaults to data/ directory)
	"""
	if csv_path is None:
		csv_path = os.path.join(os.path.dirname(__file__), '..', 'historical_data', '_station_location.csv')

	try:
		# Read existing CSV
		if os.path.exists(csv_path):
			df = pd.read_csv(csv_path)
		else:
			df = pd.DataFrame(columns=['Station Name', 'Longitude', 'Latitude', 'Filename'])

		# Add or update new stations
		for station in new_stations:
			# Check if station already exists (by name)
			if station['name'] in df['Station Name'].values:
				# Update existing
				idx = df[df['Station Name'] == station['name']].index[0]
				df.at[idx, 'Longitude'] = station['longitude']
				df.at[idx, 'Latitude'] = station['latitude']
				if 'filename' in station:
					df.at[idx, 'Filename'] = station['filename']
				print(f'  ✓ Updated: {station["name"]}')
			else:
				# Add new
				new_row = pd.DataFrame(
					[
						{
							'Station Name': station['name'],
							'Longitude': station['longitude'],
							'Latitude': station['latitude'],
							'Filename': station.get('filename', ''),
						}
					]
				)
				df = pd.concat([df, new_row], ignore_index=True)
				print(f'  ✓ Added: {station["name"]}')

		# Save updated CSV
		df.to_csv(csv_path, index=False)
		print(f'\n✓ Updated _station_location.csv')

	except Exception as e:
		print(f'✗ Error updating station locations: {e}')


def reindex_station_locations(csv_path: str = None):
	"""
	Reindex and alphabetize station_location.csv by station name.

	Args:
	    csv_path: Path to station_location.csv (defaults to data/ directory)
	"""
	if csv_path is None:
		csv_path = os.path.join(os.path.dirname(__file__), '..', 'historical_data', '_station_location.csv')

	try:
		# Read CSV
		df = pd.read_csv(csv_path)

		# Remove any duplicate header rows
		df = df[df['Station Name'] != 'Station Name']

		# Ensure Filename column exists
		if 'Filename' not in df.columns:
			df['Filename'] = ''

		# Sort by station name
		df = df.sort_values('Station Name').reset_index(drop=True)

		# Save updated CSV
		df.to_csv(csv_path, index=False)
		print(f'✓ Reindexed station_location.csv ({len(df)} stations)')

	except Exception as e:
		print(f'✗ Error reindexing station locations: {e}')


def txt_content_to_csv(txt_content: str, filename: str, output_dir: str = None, start_date: datetime = None, update_locations: bool = False) -> tuple:
	"""
	Convert NOAA txt content to CSV, keeping only data columns.
	Handles both space-separated and comma-separated formats.
	Optionally filters rows to only include data after start_date.

	Args:
	    txt_content: Raw txt content as string
	    filename: Filename to use for the CSV (without extension)
	    output_dir: Directory to save CSV (defaults to data/)
	    start_date: Optional datetime to filter rows (only keep data after this date)
	    update_locations: Whether to extract and return station metadata

	Returns:
	    tuple: (csv_file_path, metadata_dict or None)
	"""
	if output_dir is None:
		output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

	os.makedirs(output_dir, exist_ok=True)

	try:
		lines = txt_content.split('\n')

		# Find the header line
		header_idx = None
		for i, line in enumerate(lines):
			if 'YYYY' in line and ('MM' in line or ',' in line):
				header_idx = i
				break

		if header_idx is None:
			print(f'✗ Could not find header in {filename}')
			return None, None

		# Detect delimiter (comma or space)
		header_line = lines[header_idx].strip()
		if ',' in header_line:
			delimiter = ','
		else:
			delimiter = None  # Use split() for whitespace

		# Parse header
		if delimiter:
			header = [h.strip() for h in header_line.split(delimiter)]
		else:
			header = header_line.split()  # Split on any whitespace

		data_lines = lines[header_idx + 1 :]

		# Parse data
		rows = []
		skipped_count = 0
		for i, line in enumerate(data_lines):
			if line.strip():  # Skip empty lines
				# Split using detected delimiter
				if delimiter:
					values = [v.strip() for v in line.strip().split(delimiter)]
				else:
					values = line.split()  # Split on any whitespace

				if len(values) >= len(header):
					# If filtering by date, check if row is after start_date
					if start_date:
						try:
							year = int(values[0])
							month = int(values[1])
							day = int(values[2])
							row_date = datetime(year, month, day)

							if row_date < start_date:
								skipped_count += 1
								continue  # Skip rows before start_date (but include start_date itself)
						except (ValueError, IndexError) as e:
							skipped_count += 1
							continue

					rows.append(values[: len(header)])

		# If no rows after filtering, return None
		if not rows:
			if start_date:
				print(f'✗ No data after {start_date.strftime("%Y-%m-%d")} in {filename} (skipped {skipped_count} rows)')
			else:
				print(f'✗ No data in {filename}')
			return None, None

		# Create DataFrame
		df = pd.DataFrame(rows, columns=header)

		# Convert numeric columns (all columns after date columns)
		numeric_cols = header[3:]  # All columns after YYYY/MM/DD
		for col in numeric_cols:
			df[col] = pd.to_numeric(df[col], errors='coerce')

		# Normalize column names to standard format
		df = normalize_column_names(df)

		# Extract station metadata if requested
		metadata = None
		if update_locations:
			metadata = extract_station_metadata(txt_content)
			if metadata:
				metadata['filename'] = filename

		# Save as CSV
		base_name = filename.replace('.txt', '')
		csv_file = os.path.join(output_dir, f'{base_name}.csv')
		df.to_csv(csv_file, index=False)

		print(f'✓ Converted: {base_name}.csv ({len(df)} rows)')
		return csv_file, metadata

	except Exception as e:
		print(f'✗ Error converting {filename}: {e}')
		return None, None


def scrape_and_download_station_data(url: str, output_dir: str = None, start_date: datetime = None, update_locations: bool = False) -> tuple:
	"""
	Scrape ocean station data table and convert txt files directly to CSV.

	Args:
	    url: The URL to scrape
	    output_dir: Directory to save CSV files (defaults to data/)
	    start_date: Optional datetime to filter rows (only keep data after this date)
	    update_locations: Whether to extract and update station metadata

	Returns:
	    tuple: (list of CSV file paths, list of station metadata dicts)
	"""
	if output_dir is None:
		output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

	os.makedirs(output_dir, exist_ok=True)

	# Initialize driver
	driver = webdriver.Chrome()
	csv_files = []
	collected_stations = []

	try:
		# Navigate to URL
		driver.get(url)
		print(f'Loading: {url}')

		# Wait for table to load
		wait = WebDriverWait(driver, 10)
		table = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'table')))

		# Find all txt links in the table
		txt_links = driver.find_elements(By.XPATH, "//table//a[contains(@href, '.txt')]")

		print(f'Found {len(txt_links)} txt files')

		# Extract all hrefs first (to avoid stale element reference)
		hrefs = []
		for link in txt_links:
			href = link.get_attribute('href')
			if href:
				hrefs.append(href)

		# Process each file
		for href in hrefs:
			if href:
				# Construct full URL if relative
				full_url = urljoin(url, href)

				# Extract filename from href
				filename = href.split('/')[-1]

				# Download and convert to CSV
				try:
					response = requests.get(full_url)
					response.raise_for_status()

					csv_file, metadata = txt_content_to_csv(
						response.text, filename, output_dir, start_date=start_date, update_locations=update_locations
					)
					if csv_file:
						csv_files.append(csv_file)
						if metadata:
							collected_stations.append(metadata)
				except Exception as e:
					print(f'✗ Failed to process {filename}: {e}')

		return csv_files, collected_stations

	finally:
		driver.quit()


def scrape_multiple_stations(urls: list, output_dir: str = None, start_date: datetime = None, update_locations: bool = False) -> tuple:
	"""
	Scrape multiple station pages and convert all txt files directly to CSV.

	Args:
	    urls: List of URLs to scrape
	    output_dir: Directory to save CSV files (defaults to data/)
	    start_date: Optional datetime to filter rows (only keep data after this date)
	    update_locations: Whether to extract and update station metadata

	Returns:
	    tuple: (list of all CSV file paths, list of all station metadata dicts)
	"""
	if output_dir is None:
		output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

	os.makedirs(output_dir, exist_ok=True)

	all_csv_files = []
	collected_stations = []
	driver = webdriver.Chrome()
	base_url = 'https://coralreefwatch.noaa.gov'

	try:
		for url in urls:
			# Construct full URL if relative
			full_url = urljoin(base_url, url) if url.startswith('/') else url

			try:
				driver.get(full_url)
				print(f'\nLoading: {full_url}')

				# Wait for page to load
				wait = WebDriverWait(driver, 10)
				wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

				# Find all txt links on page
				txt_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.txt')]")

				print(f'Found {len(txt_links)} txt files')

				# Extract all hrefs first (to avoid stale element reference)
				hrefs = []
				for link in txt_links:
					href = link.get_attribute('href')
					if href:
						hrefs.append(href)

				# Process each file
				for href in hrefs:
					if href:
						# Construct full URL if relative
						file_url = urljoin(full_url, href)

						# Extract filename from href
						filename = href.split('/')[-1]

						try:
							response = requests.get(file_url)
							response.raise_for_status()

							csv_file, metadata = txt_content_to_csv(
								response.text, filename, output_dir, start_date=start_date, update_locations=update_locations
							)
							if csv_file:
								all_csv_files.append(csv_file)
								if metadata:
									collected_stations.append(metadata)
						except Exception as e:
							print(f'  ✗ Failed to process {filename}: {e}')

			except Exception as e:
				print(f'✗ Failed to load {full_url}: {e}')

		return all_csv_files, collected_stations

	finally:
		driver.quit()
