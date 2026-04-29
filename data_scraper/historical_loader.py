import os

from utils import reindex_station_locations, scrape_and_download_station_data, scrape_multiple_stations, update_station_locations_csv

if __name__ == '__main__':
	# Use absolute path for historical_data directory
	historical_data_dir = os.path.join(os.path.dirname(__file__), '..', 'historical_data')

	# Step 1: Scrape and convert all station data from main page to CSV
	url = 'https://coralreefwatch.noaa.gov/product/vs/data.php'
	csv_files, stations = scrape_and_download_station_data(url, output_dir=historical_data_dir, update_locations=True)

	# Update station locations CSV if requested
	if stations:
		update_station_locations_csv(stations)

	# Step 2: Scrape from specific station pages and convert to CSV
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
	csv_files2, stations2 = scrape_multiple_stations(station_urls, output_dir=historical_data_dir, update_locations=True)

	# Update station locations with new stations
	if stations2:
		update_station_locations_csv(stations2)

	# Reindex stations alphabetically
	reindex_station_locations()

	print(f'\n✓ Historical load complete. Files saved to: {historical_data_dir}')
