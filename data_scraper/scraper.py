import os
import sys
from datetime import datetime

from utils import scrape_and_download_station_data, scrape_multiple_stations

if __name__ == '__main__':
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

	# Use absolute path for .temp_data directory
	temp_data_dir = os.path.join(os.path.dirname(__file__), '..', '.temp_data')

	# Scrape main page table
	url = 'https://coralreefwatch.noaa.gov/product/vs/data.php'
	csv_files, stations = scrape_and_download_station_data(url, output_dir=temp_data_dir, start_date=start_date)
	print(f'\nDownloaded {len(csv_files)} CSV files from main table')

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
	csv_files2, stations2 = scrape_multiple_stations(station_urls, output_dir=temp_data_dir, start_date=start_date)
	print(f'Downloaded {len(csv_files2)} CSV files from station pages')
	print(f'\n✓ Scraping complete. Files saved to: {temp_data_dir}')
