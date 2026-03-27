#!/usr/bin/env python3
"""
Fetch 4 months of historical AQI data from OpenWeatherMap
This will create a comprehensive training dataset
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('OPENWEATHER_API_KEY')

# Hyderabad coordinates
LAT = 17.385044
LON = 78.486671

print("="*70)
print("FETCHING 4 MONTHS OF HISTORICAL AQI DATA")
print("="*70)

# Calculate date range: 4 months back from today
end_date = datetime.now()
start_date = end_date - timedelta(days=120)  # ~4 months

print(f"\nDate Range:")
print(f"  Start: {start_date.strftime('%Y-%m-%d')}")
print(f"  End: {end_date.strftime('%Y-%m-%d')}")
print(f"  Total days: 120")
print(f"\nLocation: Hyderabad, India ({LAT}, {LON})")

# OpenWeatherMap historical data endpoint
# Note: Free tier has limits, we'll fetch day by day
all_data = []
total_hours = 120 * 24  # 4 months * 24 hours

print(f"\n🔄 Fetching historical data...")
print(f"   Expected records: ~{total_hours} hourly data points")

# Fetch data in chunks (5-day periods to avoid rate limits)
chunk_size = 5  # days per request
total_chunks = 120 // chunk_size

for chunk in range(total_chunks):
    chunk_start = start_date + timedelta(days=chunk * chunk_size)
    chunk_end = chunk_start + timedelta(days=chunk_size)
    
    # Convert to Unix timestamp
    start_timestamp = int(chunk_start.timestamp())
    end_timestamp = int(chunk_end.timestamp())
    
    try:
        # Fetch air pollution history
        url = f"http://api.openweathermap.org/data/2.5/air_pollution/history"
        params = {
            'lat': LAT,
            'lon': LON,
            'start': start_timestamp,
            'end': end_timestamp,
            'appid': API_KEY
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Process the data
        for record in data.get('list', []):
            dt = datetime.fromtimestamp(record['dt'])
            components = record['components']
            
            all_data.append({
                'datetime': dt,
                'PM2.5': components.get('pm2_5', 0),
                'PM10': components.get('pm10', 0),
                'NO2': components.get('no2', 0),
                'SO2': components.get('so2', 0),
                'CO': components.get('co', 0),
                'O3': components.get('o3', 0),
                'NH3': components.get('nh3', 0)
            })
        
        progress = ((chunk + 1) / total_chunks) * 100
        print(f"   Progress: {progress:.1f}% - Fetched up to {chunk_end.strftime('%Y-%m-%d')} ({len(all_data)} records)")
        
        # Rate limiting: wait 1 second between requests
        time.sleep(1)
        
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  Error fetching data for {chunk_start.strftime('%Y-%m-%d')}: {e}")
        continue

print(f"\n✅ Data collection complete!")
print(f"   Total records collected: {len(all_data)}")

# Create DataFrame
df = pd.DataFrame(all_data)
df = df.sort_values('datetime').reset_index(drop=True)

# Remove duplicates (if any)
df = df.drop_duplicates(subset=['datetime'], keep='first')

print(f"\n📊 Dataset Summary:")
print(f"   Records: {len(df)}")
print(f"   Start: {df['datetime'].min()}")
print(f"   End: {df['datetime'].max()}")
print(f"   Duration: {(df['datetime'].max() - df['datetime'].min()).days} days")
print(f"   Avg records per day: {len(df) / ((df['datetime'].max() - df['datetime'].min()).days + 1):.1f}")

# Save raw data
output_file = 'data/openweather_4month_history.csv'
df.to_csv(output_file, index=False)
print(f"\n💾 Saved to: {output_file}")

print("\n" + "="*70)
print("✅ DATA COLLECTION COMPLETE")
print("="*70)
print("\nNext steps:")
print("1. Run the feature engineering script to process this data")
print("2. Retrain the model with 4 months of data")
print("3. Compare accuracy improvements")
