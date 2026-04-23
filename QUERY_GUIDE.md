# 🔍 Database Query Guide

You now have two ways to query your reef database:

## Option 1: Interactive Streamlit Interface (Recommended)

This is the easiest way to browse and query your database with a nice GUI.

### Step 1: Start MongoDB
```bash
docker-compose up -d mongodb
```

### Step 2: Start the Streamlit App
```bash
cd streamlit_app
streamlit run app.py
```

### Step 3: Navigate to Query Database
In your browser, go to `http://localhost:8501` and click on the **"Query Database"** page in the sidebar.

### Features:
- **Database Summary**: See total records, stations, and date range at a glance
- **View All Stations**: Browse all stations in a nice table
- **Query by Station**: Select a station and see all its data, with CSV download
- **Advanced Query**: Write MongoDB queries for complex filters

---

## Option 2: Command-Line Script

For quick queries from the terminal, use the Python script.

### Step 1: Make Sure MongoDB is Running
```bash
docker-compose up -d mongodb
```

### Step 2: Install Dependencies
```bash
pip install tabulate pymongo
```

### Step 3: Run Queries

#### Show database summary:
```bash
python mongo/query_db.py --summary
```

#### List all stations:
```bash
python mongo/query_db.py --stations
```

#### Get data for a specific station:
```bash
python mongo/query_db.py --station "Station Name"
```

#### Advanced MongoDB query:
```bash
python mongo/query_db.py --query '{"temperature": {"$gt": 25}}'
python mongo/query_db.py --query '{"year": 2023, "month": 6}' --limit 50
python mongo/query_db.py --query '{"station_name": "your_station"}' --sort station_name
```

---

## MongoDB Query Examples

If using the Advanced Query option, here are common patterns:

### Basic Queries
```javascript
{}                                    // All documents
{"station_name": "Your Station"}      // Single station
{"year": 2023}                        // Specific year
```

### Comparison Operators
```javascript
{"temperature": {"$gt": 25}}          // Greater than
{"temperature": {"$lt": 20}}          // Less than
{"temperature": {"$gte": 20, "$lte": 30}}  // Range
```

### Multiple Conditions
```javascript
{"station_name": "Station", "year": 2023}
{"month": {"$in": [1, 2, 3]}}         // January, February, March
{"temperature": {"$exists": true}}    // Has temperature field
```

### Date Range Queries
```javascript
{"year": 2023, "month": 6}            // June 2023
{"year": {"$gte": 2020, "$lte": 2023}} // 2020-2023
```

---

## Troubleshooting

### "Failed to connect to MongoDB"
Make sure MongoDB container is running:
```bash
docker ps | grep mongodb
docker-compose up -d mongodb  # Start if not running
```

### "No data found"
You might not have loaded any data yet. Check the MongoDB loading guide.

### "Connection refused"
Check that MongoDB is listening on port 27017:
```bash
docker-compose ps
```

---

## Next Steps

1. **Load Your Data**: Use the MongoDB data loader to import CSV files
2. **Explore**: Use the query tools to understand what data you have
3. **Visualize**: Once you understand the data, create visualizations in the Streamlit app
4. **Analyze**: Use the data for analysis and modeling

---

For more advanced MongoDB operations, see the [MongoDB documentation](https://docs.mongodb.com/).
