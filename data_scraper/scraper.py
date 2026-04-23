import os
from datetime import datetime
from urllib.parse import urljoin

import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ============================================================================
# SIMPLE TABLE SCRAPER - Converts txt to CSV (filtered by date)
# ============================================================================


def txt_content_to_csv(txt_content: str, filename: str, output_dir: str = None, start_date: datetime = None) -> str:
	"""
	Convert NOAA txt content to CSV, keeping only data columns.
	Handles both space-separated and comma-separated formats.
	Optionally filters rows to only include data after start_date.

	Args:
	    txt_content: Raw txt content as string
	    filename: Filename to use for the CSV (without extension)
	    output_dir: Directory to save CSV (defaults to data/)
	    start_date: Optional datetime to filter rows (only keep data after this date)

	Returns:
	    Path to the converted CSV file, or None if no data after start_date
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
			return None

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
			return None

		# Create DataFrame
		df = pd.DataFrame(rows, columns=header)

		# Convert numeric columns (all columns after date columns)
		numeric_cols = header[3:]  # All columns after YYYY/MM/DD
		for col in numeric_cols:
			df[col] = pd.to_numeric(df[col], errors='coerce')

		# Save as CSV
		base_name = filename.replace('.txt', '')
		csv_file = os.path.join(output_dir, f'{base_name}.csv')
		df.to_csv(csv_file, index=False)

		print(f'✓ Converted: {base_name}.csv ({len(df)} rows)')
		return csv_file

	except Exception as e:
		print(f'✗ Error converting {filename}: {e}')
		return None


def scrape_and_download_station_data(url: str, output_dir: str = None, start_date: datetime = None) -> list:
	"""
	Scrape ocean station data table and convert txt files directly to CSV.

	Args:
	    url: The URL to scrape
	    output_dir: Directory to save CSV files (defaults to data/)
	    start_date: Optional datetime to filter rows (only keep data after this date)

	Returns:
	    List of converted CSV file paths
	"""
	if output_dir is None:
		output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

	os.makedirs(output_dir, exist_ok=True)

	# Initialize driver
	driver = webdriver.Chrome()
	csv_files = []

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

					csv_file = txt_content_to_csv(response.text, filename, output_dir, start_date=start_date)
					if csv_file:
						csv_files.append(csv_file)
				except Exception as e:
					print(f'✗ Failed to process {filename}: {e}')

		return csv_files

	finally:
		driver.quit()


def scrape_multiple_stations(urls: list, output_dir: str = None, start_date: datetime = None) -> list:
	"""
	Scrape multiple station pages and convert all txt files directly to CSV.

	Args:
	    urls: List of URLs to scrape
	    output_dir: Directory to save CSV files (defaults to data/)
	    start_date: Optional datetime to filter rows (only keep data after this date)

	Returns:
	    List of all converted CSV file paths
	"""
	if output_dir is None:
		output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

	os.makedirs(output_dir, exist_ok=True)

	all_csv_files = []
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

							csv_file = txt_content_to_csv(response.text, filename, output_dir, start_date=start_date)
							if csv_file:
								all_csv_files.append(csv_file)
						except Exception as e:
							print(f'  ✗ Failed to process {filename}: {e}')

			except Exception as e:
				print(f'✗ Failed to load {full_url}: {e}')

		return all_csv_files

	finally:
		driver.quit()


if __name__ == '__main__':
	import sys

	# Parse optional start_date argument
	# Usage: python scraper.py [YYYY-MM-DD]
	# Example: python scraper.py 2024-04-14
	start_date = None
	if len(sys.argv) > 1:
		try:
			start_date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
			print(f'Filtering data to only include updates after {start_date.strftime("%Y-%m-%d")}\n')
		except ValueError:
			print(f'Invalid date format: {sys.argv[1]}')
			print('Usage: python scraper.py [YYYY-MM-DD]')
			sys.exit(1)

	# Scrape main page table
	url = 'https://coralreefwatch.noaa.gov/product/vs/data.php'
	scrape_and_download_station_data(url, start_date=start_date)

	# Scrape specific station pages
	station_urls = [
		'/product/vs_single_pixel_exp/florida_keys.php',
		'/product/vs_single_pixel_exp/fgb.php',
		'/product/vs_single_pixel_exp/usvi.php',
		'/product/vs_single_pixel_exp/puerto_rico.php',
		'/product/vs_single_pixel_exp/samoas.php',
		'/product/vs_single_pixel_exp/guam.php',
		'/product/vs_single_pixel_exp/rota.php',
		'/product/vs_single_pixel_exp/saipan_tinian_aguijan.php',
	]
	scrape_multiple_stations(station_urls, start_date=start_date)
