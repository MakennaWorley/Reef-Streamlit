"""
================================================================================
MIDNIGHT DATA LOADER SCHEDULER
================================================================================

Runs the daily data loader at midnight using APScheduler.
Designed to run in background while Streamlit app is active.

Usage (in Streamlit app):
    from mongo.midnight_scheduler import start_scheduler
    
    if 'scheduler_started' not in st.session_state:
        start_scheduler()
        st.session_state.scheduler_started = True
"""

import atexit
import sys
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler_running = False


def run_daily_load():
	"""Execute the daily data load."""
	print('\n' + '=' * 80)
	print(f'🕛 MIDNIGHT SCHEDULER - Running daily load at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
	print('=' * 80)
	
	try:
		# Import here to avoid circular imports
		from mongo.load_daily_data import load_daily_data
		load_daily_data()
	except Exception as e:
		print(f'✗ Scheduler error: {e}')
		import traceback
		traceback.print_exc()


def start_scheduler():
	"""Start the midnight scheduler."""
	global scheduler_running
	
	if scheduler_running:
		print('⚠ Scheduler already running')
		return
	
	try:
		# Schedule job to run daily at midnight
		scheduler.add_job(
			run_daily_load,
			'cron',
			hour=0,
			minute=0,
			second=0,
			id='daily_reef_data_load',
			replace_existing=True
		)
		
		scheduler.start()
		scheduler_running = True
		print('✓ Midnight scheduler started - will run daily at 00:00:00')
		
		# Ensure scheduler shuts down gracefully on exit
		atexit.register(stop_scheduler)
		
	except Exception as e:
		print(f'✗ Error starting scheduler: {e}')
		import traceback
		traceback.print_exc()


def stop_scheduler():
	"""Stop the scheduler gracefully."""
	global scheduler_running
	
	if scheduler.running:
		scheduler.shutdown()
		scheduler_running = False
		print('✓ Scheduler stopped')
