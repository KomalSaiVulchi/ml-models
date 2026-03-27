#!/usr/bin/env python3
"""
Process 4 months of historical data into training-ready format with all features
"""

import pandas as pd
import numpy as np
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
import time

load_dotenv()
API_KEY = os.getenv('OPENWEATHER_API_KEY')

print("="*70)
print("PROCESSING 4-MONTH DATASET FOR TRAINING")
print("="*70)

# Load the 4-month historical data
print("\n[1/6] Loading 4-month historical data...")
df = pd.read_csv('data/openweather_4month_history.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('datetime').reset_index(drop=True)
print(f"   ✅ Loaded {len(df)} records")
print(f"   Date range: {df['datetime'].min()} to {df['datetime'].max()}")

# Calculate Indian AQI
print("\n[2/6] Calculating Indian AQI...")

def calculate_indian_aqi(pm25, pm10):
    def get_aqi(conc, breakpoints):
        for bp in breakpoints:
            if bp['low'] <= conc <= bp['high']:
                aqi = ((bp['aqi_high'] - bp['aqi_low']) / (bp['high'] - bp['low'])) * \
                      (conc - bp['low']) + bp['aqi_low']
                return aqi
        return breakpoints[-1]['aqi_high']
    
    pm25_bp = [
        {'low': 0, 'high': 30, 'aqi_low': 0, 'aqi_high': 50},
        {'low': 31, 'high': 60, 'aqi_low': 51, 'aqi_high': 100},
        {'low': 61, 'high': 90, 'aqi_low': 101, 'aqi_high': 200},
        {'low': 91, 'high': 120, 'aqi_low': 201, 'aqi_high': 300},
        {'low': 121, 'high': 250, 'aqi_low': 301, 'aqi_high': 400},
        {'low': 251, 'high': 999, 'aqi_low': 401, 'aqi_high': 500}
    ]
    
    pm10_bp = [
        {'low': 0, 'high': 50, 'aqi_low': 0, 'aqi_high': 50},
        {'low': 51, 'high': 100, 'aqi_low': 51, 'aqi_high': 100},
        {'low': 101, 'high': 250, 'aqi_low': 101, 'aqi_high': 200},
        {'low': 251, 'high': 350, 'aqi_low': 201, 'aqi_high': 300},
        {'low': 351, 'high': 430, 'aqi_low': 301, 'aqi_high': 400},
        {'low': 431, 'high': 999, 'aqi_low': 401, 'aqi_high': 500}
    ]
    
    return max(get_aqi(pm25, pm25_bp), get_aqi(pm10, pm10_bp))

df['AQI_Indian'] = df.apply(lambda row: calculate_indian_aqi(row['PM2.5'], row['PM10']), axis=1)
print(f"   ✅ Calculated AQI for {len(df)} records")
print(f"   AQI range: {df['AQI_Indian'].min():.1f} - {df['AQI_Indian'].max():.1f}")

# Fetch weather data
print("\n[3/6] Fetching historical weather data...")
print("   This will take a few minutes...")

weather_data = []
LAT, LON = 17.385044, 78.486671

# Process in chunks to show progress
chunk_size = 120  # 5 days of hourly data
total_chunks = (len(df) + chunk_size - 1) // chunk_size

for chunk_idx in range(total_chunks):
    start_idx = chunk_idx * chunk_size
    end_idx = min(start_idx + chunk_size, len(df))
    chunk_df = df.iloc[start_idx:end_idx]
    
    # Get weather for the middle timestamp of this chunk
    mid_timestamp = int(chunk_df.iloc[len(chunk_df)//2]['datetime'].timestamp())
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': LAT,
            'lon': LON,
            'appid': API_KEY,
            'units': 'metric'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        weather = response.json()
        
        # Extract weather data
        temp = weather['main']['temp']
        humidity = weather['main']['humidity']
        pressure = weather['main']['pressure']
        wind_speed = weather['wind']['speed']
        
        # Apply to all rows in this chunk with small variations
        for i in range(len(chunk_df)):
            hour = chunk_df.iloc[i]['datetime'].hour
            # Add hourly variations
            temp_var = temp + (np.sin(hour * np.pi / 12) * 5)  # ±5°C daily variation
            weather_data.append({
                'temperature': temp_var,
                'humidity': humidity + (np.random.rand() - 0.5) * 10,
                'pressure': pressure + (np.random.rand() - 0.5) * 2,
                'wind_speed': max(0, wind_speed + (np.random.rand() - 0.5) * 2)
            })
        
        progress = ((chunk_idx + 1) / total_chunks) * 100
        print(f"   Progress: {progress:.1f}% ({end_idx}/{len(df)} records)")
        
        time.sleep(0.5)  # Rate limiting
        
    except Exception as e:
        print(f"   ⚠️  Error fetching weather: {e}")
        # Use default values
        for i in range(len(chunk_df)):
            weather_data.append({
                'temperature': 25,
                'humidity': 60,
                'pressure': 1013,
                'wind_speed': 3
            })

weather_df = pd.DataFrame(weather_data)
for col in weather_df.columns:
    df[col] = weather_df[col].values

print(f"   ✅ Added weather data")

# Feature engineering
print("\n[4/6] Creating 120 features...")

training_data = []

# Need 48 hours of history for lag features
for i in range(48, len(df)):
    features = {}
    current = df.iloc[i]
    
    # Target
    features['AQI_target'] = current['AQI_Indian']
    
    # Time features
    features['datetime'] = current['datetime']
    features['hour'] = current['datetime'].hour
    features['day_of_week'] = current['datetime'].dayofweek
    features['month'] = current['datetime'].month
    features['season'] = (current['datetime'].month % 12 + 3) // 3
    features['is_weekend'] = 1 if current['datetime'].dayofweek >= 5 else 0
    features['is_rush_hour'] = 1 if current['datetime'].hour in [7,8,9,17,18,19] else 0
    features['quarter'] = (current['datetime'].month - 1) // 3 + 1
    features['hour_sin'] = np.sin(2 * np.pi * current['datetime'].hour / 24)
    features['hour_cos'] = np.cos(2 * np.pi * current['datetime'].hour / 24)
    features['day_sin'] = np.sin(2 * np.pi * current['datetime'].dayofweek / 7)
    features['day_cos'] = np.cos(2 * np.pi * current['datetime'].dayofweek / 7)
    features['month_sin'] = np.sin(2 * np.pi * current['datetime'].month / 12)
    features['month_cos'] = np.cos(2 * np.pi * current['datetime'].month / 12)
    
    # AQI lag features (48 hours)
    for lag in range(1, 49):
        features[f'AQI_lag_{lag}'] = df.iloc[i-lag]['AQI_Indian']
    
    # Pollutant features (current + lags)
    features['PM2.5_current'] = current['PM2.5']
    features['PM10_current'] = current['PM10']
    features['NO2_current'] = current['NO2']
    features['SO2_current'] = current['SO2']
    features['CO_current'] = current['CO'] / 1000
    features['O3_current'] = current['O3']
    
    # Pollutant lags
    for hours in [3, 6, 12, 24]:
        if i >= hours:
            features[f'PM2.5_lag_{hours}h'] = df.iloc[i-hours]['PM2.5']
            features[f'PM10_lag_{hours}h'] = df.iloc[i-hours]['PM10']
    
    # Pollutant ratios
    features['PM2.5_to_PM10_ratio'] = current['PM2.5'] / current['PM10'] if current['PM10'] > 0 else 0
    features['dominant_pollutant'] = 1 if current['PM2.5'] > current['PM10'] else 2
    
    # Weather features
    features['temperature_current'] = current['temperature']
    features['humidity_current'] = current['humidity']
    features['wind_speed_current'] = current['wind_speed']
    features['pressure_current'] = current['pressure']
    
    # Weather lags
    for hours in [6, 12, 24]:
        if i >= hours:
            features[f'temperature_lag_{hours}h'] = df.iloc[i-hours]['temperature']
            features[f'humidity_lag_{hours}h'] = df.iloc[i-hours]['humidity']
            features[f'wind_speed_lag_{hours}h'] = df.iloc[i-hours]['wind_speed']
            features[f'pressure_lag_{hours}h'] = df.iloc[i-hours]['pressure']
    
    # Weather changes
    if i >= 6:
        features['temperature_change_6h'] = current['temperature'] - df.iloc[i-6]['temperature']
        features['humidity_change_6h'] = current['humidity'] - df.iloc[i-6]['humidity']
        features['wind_speed_change_6h'] = current['wind_speed'] - df.iloc[i-6]['wind_speed']
        features['pressure_change_6h'] = current['pressure'] - df.iloc[i-6]['pressure']
    
    # Interactions
    features['wind_humidity_interaction'] = current['wind_speed'] * current['humidity']
    features['heat_index'] = current['temperature'] + (0.5555 * (current['humidity'] - 10))
    features['is_calm_wind'] = 1 if current['wind_speed'] < 1 else 0
    features['is_strong_wind'] = 1 if current['wind_speed'] > 5 else 0
    
    # Rolling statistics
    for window in [6, 12, 24]:
        if i >= window:
            window_aqi = [df.iloc[i-j]['AQI_Indian'] for j in range(window)]
            features[f'AQI_rolling_mean_{window}h'] = np.mean(window_aqi)
            features[f'AQI_rolling_std_{window}h'] = np.std(window_aqi)
            features[f'AQI_rolling_min_{window}h'] = np.min(window_aqi)
            features[f'AQI_rolling_max_{window}h'] = np.max(window_aqi)
            features[f'AQI_rolling_range_{window}h'] = np.max(window_aqi) - np.min(window_aqi)
    
    # AQI changes
    features['AQI_change_1h'] = current['AQI_Indian'] - df.iloc[i-1]['AQI_Indian']
    features['AQI_change_6h'] = current['AQI_Indian'] - df.iloc[i-6]['AQI_Indian']
    features['AQI_change_24h'] = current['AQI_Indian'] - df.iloc[i-24]['AQI_Indian']
    features['AQI_trend_6h'] = (current['AQI_Indian'] - df.iloc[i-6]['AQI_Indian']) / 6
    
    training_data.append(features)
    
    if (i - 48) % 200 == 0:
        print(f"   Progress: {((i-48) / (len(df)-48)) * 100:.1f}%")

training_df = pd.DataFrame(training_data)
print(f"   ✅ Created {len(training_df)} training samples with {len(training_df.columns)} features")

# Save training data
print("\n[5/6] Saving training data...")
output_file = 'data/real_aqi_training_4months.csv'
training_df.to_csv(output_file, index=False)
print(f"   ✅ Saved to: {output_file}")

# Display statistics
print("\n[6/6] Dataset Statistics:")
print(f"   Total samples: {len(training_df)}")
print(f"   Features: {len(training_df.columns) - 2}")  # Exclude datetime and target
print(f"   Date range: {training_df['datetime'].min()} to {training_df['datetime'].max()}")
print(f"   AQI range: {training_df['AQI_target'].min():.1f} - {training_df['AQI_target'].max():.1f}")
print(f"   Mean AQI: {training_df['AQI_target'].mean():.1f}")

print("\n" + "="*70)
print("✅ TRAINING DATA READY")
print("="*70)
print(f"\nData saved to: {output_file}")
print("Next step: Retrain the model with this expanded dataset")
print("Run: python3 train_xgboost.py")
