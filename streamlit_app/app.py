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
	st.header('Welcome!')
	st.write('Select a page from the sidebar to get started.')

elif page == 'Query Database':
	# Add parent directory to path for imports
	sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

	# Import and run the query database page
	import importlib.util

	spec = importlib.util.spec_from_file_location('query_database', os.path.join(os.path.dirname(__file__), 'query_database.py'))
	query_db_module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(query_db_module)
