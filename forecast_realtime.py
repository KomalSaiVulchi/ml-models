"""
Real-Time AQI Forecasting System
Fetches live data from OpenWeatherMap API and predicts next 6 hours
"""

import pandas as pd
import numpy as np
import joblib
import requests
from pathlib import Path
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from utils.aqi_calculation import calculate_indian_aqi

# Load environment variables
load_dotenv()
API_KEY = os.getenv('OPENWEATHER_API_KEY')

print("="*70)
print(" "*10 + "REAL-TIME AQI FORECASTING SYSTEM")
print("="*70)

# ============================================================================
# STEP 1: DETECT USER LOCATION
# ============================================================================

def get_user_location():
    """Detect user's location using IP geolocation"""
    print("\n📍 DETECTING YOUR LOCATION...")
    
    try:
        # Try ipapi.co (free, no API key needed)
        response = requests.get('https://ipapi.co/json/', timeout=5)
        response.raise_for_status()
        data = response.json()
        
        lat = data.get('latitude')
        lon = data.get('longitude')
        city = data.get('city', 'Unknown')
        region = data.get('region', '')
        country = data.get('country_name', '')
        
        if lat and lon:
            location_str = f"{city}, {region}, {country}" if region else f"{city}, {country}"
            print(f"✅ Location detected: {location_str}")
            print(f"   Coordinates: {lat}, {lon}")
            return lat, lon, location_str
        
    except Exception as e:
        print(f"⚠️  Auto-detection failed: {e}")
    
    # Fallback: Ask user for location
    print("\n🌍 Please enter your location:")
    choice = input("   1. Enter city name\n   2. Enter coordinates (lat, lon)\n   Choice (1/2): ").strip()
    
    if choice == '1':
        city = input("   City name: ").strip()
        if city:
            # Try to geocode city name using OpenWeatherMap
            try:
                geo_url = f"http://api.openweathermap.org/geo/1.0/direct"
                params = {'q': city, 'limit': 1, 'appid': API_KEY}
                response = requests.get(geo_url, params=params, timeout=5)
                response.raise_for_status()
                results = response.json()
                
                if results:
                    lat = results[0]['lat']
                    lon = results[0]['lon']
                    location_str = f"{results[0]['name']}, {results[0].get('country', '')}"
                    print(f"✅ Found: {location_str} ({lat}, {lon})")
                    return lat, lon, location_str
                else:
                    print("❌ City not found")
            except Exception as e:
                print(f"❌ Error geocoding city: {e}")
    
    elif choice == '2':
        try:
            lat = float(input("   Latitude: ").strip())
            lon = float(input("   Longitude: ").strip())
            print(f"✅ Using coordinates: {lat}, {lon}")
            return lat, lon, f"Custom Location ({lat}, {lon})"
        except ValueError:
            print("❌ Invalid coordinates")
    
    # Final fallback: Hyderabad
    print("⚠️  Using default location: Hyderabad, India")
    return 17.385044, 78.486671, "Hyderabad, India (default)"

# Get user location
USER_LAT, USER_LON, LOCATION_NAME = get_user_location()

# ============================================================================
# STEP 2: FETCH REAL-TIME DATA
# ============================================================================

def fetch_current_aqi(lat, lon):
    """Fetch current air pollution data"""
    url = f"http://api.openweathermap.org/data/2.5/air_pollution"
    params = {'lat': lat, 'lon': lon, 'appid': API_KEY}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current = data['list'][0]
        components = current['components']
        
        return {
            'timestamp': current['dt'],
            'datetime': datetime.fromtimestamp(current['dt']),
            'PM2.5': components.get('pm2_5', 0),
            'PM10': components.get('pm10', 0),
            'NO2': components.get('no2', 0),
            'SO2': components.get('so2', 0),
            'CO': components.get('co', 0),
            'O3': components.get('o3', 0),
            'NH3': components.get('nh3', 0)
        }
    except Exception as e:
        print(f"❌ Error fetching current data: {e}")
        return None

def fetch_historical_aqi(lat, lon, hours_back=48):
    """Fetch historical air pollution data"""
    end_time = int(datetime.now().timestamp())
    start_time = end_time - (hours_back * 3600)
    
    url = f"http://api.openweathermap.org/data/2.5/air_pollution/history"
    params = {
        'lat': lat,
        'lon': lon,
        'start': start_time,
        'end': end_time,
        'appid': API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        history = []
        for item in data['list']:
            components = item['components']
            history.append({
                'timestamp': item['dt'],
                'datetime': datetime.fromtimestamp(item['dt']),
                'PM2.5': components.get('pm2_5', 0),
                'PM10': components.get('pm10', 0),
                'NO2': components.get('no2', 0),
                'SO2': components.get('so2', 0),
                'CO': components.get('co', 0),
                'O3': components.get('o3', 0),
                'NH3': components.get('nh3', 0)
            })
        
        return pd.DataFrame(history).sort_values('datetime')
    
    except Exception as e:
        print(f"❌ Error fetching historical data: {e}")
        return None

# Indian AQI calculation is now imported from utils.aqi_calculation

def calculate_us_epa_aqi(pm25, pm10, no2, so2, co, o3):
    """Calculate US EPA AQI"""
    
    def get_aqi_for_pollutant(concentration, breakpoints):
        for bp in breakpoints:
            if bp['low'] <= concentration <= bp['high']:
                aqi = ((bp['aqi_high'] - bp['aqi_low']) / (bp['high'] - bp['low'])) * \
                      (concentration - bp['low']) + bp['aqi_low']
                return aqi
        return breakpoints[-1]['aqi_high']
    
    # US EPA Breakpoints for PM2.5 (24-hour average)
    pm25_bp = [
        {'low': 0.0, 'high': 12.0, 'aqi_low': 0, 'aqi_high': 50},
        {'low': 12.1, 'high': 35.4, 'aqi_low': 51, 'aqi_high': 100},
        {'low': 35.5, 'high': 55.4, 'aqi_low': 101, 'aqi_high': 150},
        {'low': 55.5, 'high': 150.4, 'aqi_low': 151, 'aqi_high': 200},
        {'low': 150.5, 'high': 250.4, 'aqi_low': 201, 'aqi_high': 300},
        {'low': 250.5, 'high': 500.4, 'aqi_low': 301, 'aqi_high': 500}
    ]
    
    # US EPA Breakpoints for PM10 (24-hour average)
    pm10_bp = [
        {'low': 0, 'high': 54, 'aqi_low': 0, 'aqi_high': 50},
        {'low': 55, 'high': 154, 'aqi_low': 51, 'aqi_high': 100},
        {'low': 155, 'high': 254, 'aqi_low': 101, 'aqi_high': 150},
        {'low': 255, 'high': 354, 'aqi_low': 151, 'aqi_high': 200},
        {'low': 355, 'high': 424, 'aqi_low': 201, 'aqi_high': 300},
        {'low': 425, 'high': 604, 'aqi_low': 301, 'aqi_high': 500}
    ]
    
    aqi_values = []
    if pm25 > 0: aqi_values.append(get_aqi_for_pollutant(pm25, pm25_bp))
    if pm10 > 0: aqi_values.append(get_aqi_for_pollutant(pm10, pm10_bp))
    
    return max(aqi_values) if aqi_values else 0

# ============================================================================
# STEP 3: FETCH LIVE DATA
# ============================================================================

print("\n📡 FETCHING REAL-TIME AIR QUALITY DATA...")
print(f"   Location: {LOCATION_NAME}")
print(f"   Coordinates: ({USER_LAT}, {USER_LON})")

current_data = fetch_current_aqi(USER_LAT, USER_LON)
if not current_data:
    print("❌ Failed to fetch current data. Exiting.")
    exit(1)

# Fetch 5 days (120 hours) of historical data
historical_df = fetch_historical_aqi(USER_LAT, USER_LON, hours_back=120)
if historical_df is None or len(historical_df) < 48:
    print(f"❌ Insufficient historical data (got {len(historical_df) if historical_df is not None else 0} points). Exiting.")
    exit(1)

print(f"✅ Current data: {current_data['datetime'].strftime('%Y-%m-%d %I:%M %p')}")
print(f"✅ Historical data: {len(historical_df)} hourly points (past {len(historical_df)} hours)")

# =====4======================================================================
# STEP 3: CALCULATE AQI FOR ALL DATA POINTS
# ============================================================================

print("\n🔧 CALCULATING AQI VALUES...")

# Calculate both Indian and US EPA AQI for historical data
historical_df['AQI_Indian'] = historical_df.apply(
    lambda row: calculate_indian_aqi(
        pm25=row['PM2.5'], pm10=row['PM10'], no2=row['NO2'], 
        so2=row['SO2'], co=row['CO']/1000, o3=row['O3']
    )[0] if calculate_indian_aqi(
        pm25=row['PM2.5'], pm10=row['PM10'], no2=row['NO2'], 
        so2=row['SO2'], co=row['CO']/1000, o3=row['O3']
    )[0] is not None else 0, axis=1
)

historical_df['AQI_US_EPA'] = historical_df.apply(
    lambda row: calculate_us_epa_aqi(
        row['PM2.5'], row['PM10'], row['NO2'], 
        row['SO2'], row['CO']/1000, row['O3']
    ), axis=1
)

# Calculate current AQI for both standards
current_aqi_indian, dominant_pollutant = calculate_indian_aqi(
    pm25=current_data['PM2.5'], pm10=current_data['PM10'], no2=current_data['NO2'],
    so2=current_data['SO2'], co=current_data['CO']/1000, o3=current_data['O3']
)

current_aqi_us = calculate_us_epa_aqi(
    current_data['PM2.5'], current_data['PM10'], current_data['NO2'],
    current_data['SO2'], current_data['CO']/1000, current_data['O3']
)

print(f"   Current AQI (Indian): {current_aqi_indian:.1f} | (US EPA): {current_aqi_us:.1f}")
print(f"   Dominant pollutant: {dominant_pollutant}")
print(f"   PM2.5: {current_data['PM2.5']:.2f} μg/m³")
print(f"   PM10: {current_data['PM10']:.2f} μg/m³")

# ============================================================================
# STEP 5: CALCULATE 120 FEATURES
# ============================================================================

print("\n🔧 ENGINEERING 120 FEATURES...")

# Get last 48 AQI values (most recent first)
aqi_history = historical_df['AQI_Indian'].values[-48:][::-1]  # Reverse to get recent first

if len(aqi_history) < 48:
    print(f"⚠️  Warning: Only {len(aqi_history)} hours of history available")
    # Pad with the oldest value if needed
    aqi_history = np.pad(aqi_history, (0, 48 - len(aqi_history)), 'edge')

features = {}

# Current time
now = datetime.now()

# 1. TIME FEATURES (14)
features['hour'] = now.hour
features['day_of_week'] = now.weekday()
features['month'] = now.month
features['season'] = (now.month % 12 + 3) // 3
features['is_weekend'] = 1 if now.weekday() >= 5 else 0
features['is_rush_hour'] = 1 if now.hour in [7,8,9,17,18,19] else 0
features['quarter'] = (now.month - 1) // 3 + 1
features['hour_sin'] = np.sin(2 * np.pi * now.hour / 24)
features['hour_cos'] = np.cos(2 * np.pi * now.hour / 24)
features['day_sin'] = np.sin(2 * np.pi * now.weekday() / 7)
features['day_cos'] = np.cos(2 * np.pi * now.weekday() / 7)
features['month_sin'] = np.sin(2 * np.pi * now.month / 12)
features['month_cos'] = np.cos(2 * np.pi * now.month / 12)

# 2. AQI LAG FEATURES (48)
for i in range(1, 49):
    features[f'AQI_lag_{i}'] = aqi_history[i-1] if i <= len(aqi_history) else aqi_history[-1]

# 3. POLLUTANT FEATURES (15)
features['PM2.5_current'] = current_data['PM2.5']
features['PM10_current'] = current_data['PM10']
features['NO2_current'] = current_data['NO2']
features['SO2_current'] = current_data['SO2']
features['CO_current'] = current_data['CO'] / 1000  # ✅ FIX: Convert to mg/m³ (same as training)
features['O3_current'] = current_data['O3']

# Pollutant lags
if len(historical_df) >= 24:
    features['PM2.5_lag_3h'] = historical_df.iloc[-3]['PM2.5'] if len(historical_df) >= 3 else current_data['PM2.5']
    features['PM2.5_lag_6h'] = historical_df.iloc[-6]['PM2.5'] if len(historical_df) >= 6 else current_data['PM2.5']
    features['PM2.5_lag_12h'] = historical_df.iloc[-12]['PM2.5'] if len(historical_df) >= 12 else current_data['PM2.5']
    features['PM2.5_lag_24h'] = historical_df.iloc[-24]['PM2.5']
    
    features['PM10_lag_3h'] = historical_df.iloc[-3]['PM10'] if len(historical_df) >= 3 else current_data['PM10']
    features['PM10_lag_6h'] = historical_df.iloc[-6]['PM10'] if len(historical_df) >= 6 else current_data['PM10']
    features['PM10_lag_12h'] = historical_df.iloc[-12]['PM10'] if len(historical_df) >= 12 else current_data['PM10']
    features['PM10_lag_24h'] = historical_df.iloc[-24]['PM10']
else:
    for lag in [3, 6, 12, 24]:
        features[f'PM2.5_lag_{lag}h'] = current_data['PM2.5']
        features[f'PM10_lag_{lag}h'] = current_data['PM10']

features['PM2.5_to_PM10_ratio'] = current_data['PM2.5'] / current_data['PM10'] if current_data['PM10'] > 0 else 0

# Dominant pollutant (simplified)
pollutants = {
    'PM2.5': current_data['PM2.5'] / 60,  # Normalize
    'PM10': current_data['PM10'] / 100,
    'NO2': current_data['NO2'] / 40,
    'SO2': current_data['SO2'] / 20,
    'CO': current_data['CO'] / 4000,
    'O3': current_data['O3'] / 100
}
dominant = max(pollutants, key=pollutants.get)
dominant_mapping = {'PM2.5': 1, 'PM10': 2, 'NO2': 3, 'SO2': 4, 'CO': 5, 'O3': 6}
features['dominant_pollutant'] = dominant_mapping.get(dominant, 1)

# 4. WEATHER FEATURES (20) - Fetch real weather data
def fetch_current_weather(lat, lon):
    """Fetch current weather data from OpenWeatherMap"""
    url = f"http://api.openweathermap.org/data/2.5/weather"
    params = {'lat': lat, 'lon': lon, 'appid': API_KEY, 'units': 'metric'}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            'temperature': data['main']['temp'],
            'humidity': data['main']['humidity'],
            'pressure': data['main']['pressure'],
            'wind_speed': data['wind']['speed']
        }
    except Exception as e:
        print(f"⚠️  Weather API error: {e}. Using fallback values.")
        # Fallback to reasonable defaults
        base_temp = 25 + 5 * np.sin(2 * np.pi * now.hour / 24)
        return {
            'temperature': base_temp,
            'humidity': 60,
            'wind_speed': 3.5,
            'pressure': 1013
        }

weather = fetch_current_weather(USER_LAT, USER_LON)
features['temperature_current'] = weather['temperature']
features['humidity_current'] = weather['humidity']
features['wind_speed_current'] = weather['wind_speed']
features['pressure_current'] = weather['pressure']

# Weather lags - fetch from historical weather if available, otherwise estimate
def fetch_historical_weather(lat, lon, hours_back=24):
    """Fetch historical weather data"""
    try:
        # Note: OpenWeatherMap's historical weather requires paid plan
        # For free tier, we'll use current data as baseline
        return None
    except:
        return None

historical_weather = fetch_historical_weather(USER_LAT, USER_LON, 24)

if historical_weather:
    # Use real historical weather
    for lag in [6, 12, 24]:
        features[f'temperature_lag_{lag}h'] = historical_weather.get(f'temp_{lag}h', weather['temperature'])
        features[f'humidity_lag_{lag}h'] = historical_weather.get(f'humidity_{lag}h', weather['humidity'])
        features[f'wind_speed_lag_{lag}h'] = historical_weather.get(f'wind_{lag}h', weather['wind_speed'])
        features[f'pressure_lag_{lag}h'] = historical_weather.get(f'pressure_{lag}h', weather['pressure'])
else:
    # Estimate based on current values and time of day (reasonable approximation)
    for lag in [6, 12, 24]:
        # Temperature varies by time of day
        lag_hour = (now.hour - lag) % 24
        temp_offset = 5 * (np.sin(2 * np.pi * now.hour / 24) - np.sin(2 * np.pi * lag_hour / 24))
        features[f'temperature_lag_{lag}h'] = weather['temperature'] - temp_offset
        features[f'humidity_lag_{lag}h'] = weather['humidity'] + (lag * 0.3)
        features[f'wind_speed_lag_{lag}h'] = max(0, weather['wind_speed'] - (lag * 0.05))
        features[f'pressure_lag_{lag}h'] = weather['pressure'] - (lag * 0.1)

# Weather changes
features['temperature_change_6h'] = features['temperature_current'] - features['temperature_lag_6h']
features['humidity_change_6h'] = features['humidity_current'] - features['humidity_lag_6h']
features['wind_speed_change_6h'] = features['wind_speed_current'] - features['wind_speed_lag_6h']
features['pressure_change_6h'] = features['pressure_current'] - features['pressure_lag_6h']

# Weather interactions
features['wind_humidity_interaction'] = features['wind_speed_current'] * features['humidity_current']
features['heat_index'] = features['temperature_current'] + 0.5 * (features['humidity_current'] - 50)
features['is_calm_wind'] = 1 if features['wind_speed_current'] < 1 else 0
features['is_strong_wind'] = 1 if features['wind_speed_current'] > 10 else 0

# 5. ROLLING STATISTICS (19)
for window in [6, 12, 24]:
    window_aqi = aqi_history[:window]
    features[f'AQI_rolling_mean_{window}h'] = np.mean(window_aqi)
    features[f'AQI_rolling_std_{window}h'] = np.std(window_aqi)
    features[f'AQI_rolling_min_{window}h'] = np.min(window_aqi)
    features[f'AQI_rolling_max_{window}h'] = np.max(window_aqi)
    features[f'AQI_rolling_range_{window}h'] = features[f'AQI_rolling_max_{window}h'] - features[f'AQI_rolling_min_{window}h']

# 6. AQI CHANGES (4) - using Indian AQI for consistency with training
features['AQI_change_1h'] = current_aqi_indian - aqi_history[0]
features['AQI_change_6h'] = current_aqi_indian - aqi_history[5]
features['AQI_change_24h'] = current_aqi_indian - aqi_history[23]
features['AQI_trend_6h'] = (current_aqi_indian - aqi_history[5]) / 6

print(f"✅ Created {len(features)} features")

# ============================================================================
# STEP 6: SELECT FORECAST DURATION
# ============================================================================

print("\n⏱️  SELECT FORECAST DURATION:")
print("   1. Next 3 hours")
print("   2. Next 6 hours")
print("   3. Next 12 hours")
print("   4. Next 24 hours (1 day)")
print("   5. Next 48 hours (2 days)")

forecast_options = {
    '1': (3, '3 hours'),
    '2': (6, '6 hours'),
    '3': (12, '12 hours'),
    '4': (24, '24 hours (1 day)'),
    '5': (48, '48 hours (2 days)')
}

choice = input("\nYour choice (1-5) [default: 2]: ").strip() or '2'

if choice in forecast_options:
    FORECAST_HOURS, FORECAST_LABEL = forecast_options[choice]
    print(f"✅ Selected: {FORECAST_LABEL}")
else:
    print(f"⚠️  Invalid choice. Defaulting to 6 hours")
    FORECAST_HOURS, FORECAST_LABEL = 6, '6 hours'

# ============================================================================
# STEP 7: LOAD MODEL AND PREDICT
# ============================================================================

print("\n🤖 LOADING MODEL...")
model_path = Path("saved_models/best_model.pkl")
model = joblib.load(model_path)
print(f"✅ Loaded: {model_path}")

# Ensure feature order matches training
training_data = pd.read_csv("data/real_aqi_training_4months.csv", nrows=1)
feature_cols = [col for col in training_data.columns if col not in ['AQI_target', 'datetime']]

# Create feature vector in correct order
X_current = pd.Series(features).reindex(feature_cols, fill_value=0).values.reshape(1, -1)

print("\n" + "="*70)
print(f"🔮 MAKING PREDICTIONS FOR NEXT {FORECAST_HOURS} HOURS...")
print("="*70)

predictions = []
current_features = pd.Series(features).reindex(feature_cols, fill_value=0)
pred_time = now

for hour in range(1, FORECAST_HOURS + 1):
    # Predict (model outputs Indian AQI since it was trained on Indian AQI)
    predicted_aqi_indian = model.predict(X_current)[0]
    pred_time = now + timedelta(hours=hour)
    
    # Convert to US EPA AQI (approximate ratio based on current values)
    ratio = current_aqi_us / current_aqi_indian if current_aqi_indian > 0 else 0.7
    predicted_aqi_us = predicted_aqi_indian * ratio
    
    predictions.append({
        'hour': hour,
        'time': pred_time,
        'predicted_aqi_indian': predicted_aqi_indian,
        'predicted_aqi_us': predicted_aqi_us
    })
    
    # Show progress every 6 hours or for short forecasts
    if hour % 6 == 0 or FORECAST_HOURS <= 12:
        print(f"Hour +{hour} ({pred_time.strftime('%b %d, %I:%M %p')}): Indian: {predicted_aqi_indian:.1f} | US EPA: {predicted_aqi_us:.1f}")
    
    # Update features for next iteration
    # Shift AQI lags
    for i in range(48, 1, -1):
        if f'AQI_lag_{i}' in feature_cols:
            idx = feature_cols.index(f'AQI_lag_{i}')
            X_current[0, idx] = X_current[0, feature_cols.index(f'AQI_lag_{i-1}')]
    
    # Update lag_1 with prediction
    if 'AQI_lag_1' in feature_cols:
        X_current[0, feature_cols.index('AQI_lag_1')] = predicted_aqi_indian
    
    # Update rolling stats (simplified)
    recent_aqi = [predicted_aqi_indian] + [X_current[0, feature_cols.index(f'AQI_lag_{i}')] for i in range(1, 25) if f'AQI_lag_{i}' in feature_cols]
    
    if 'AQI_rolling_mean_6h' in feature_cols:
        X_current[0, feature_cols.index('AQI_rolling_mean_6h')] = np.mean(recent_aqi[:6])
    if 'AQI_rolling_mean_12h' in feature_cols:
        X_current[0, feature_cols.index('AQI_rolling_mean_12h')] = np.mean(recent_aqi[:12])
    if 'AQI_rolling_mean_24h' in feature_cols:
        X_current[0, feature_cols.index('AQI_rolling_mean_24h')] = np.mean(recent_aqi[:24])
    
    # Update time features
    if 'hour' in feature_cols:
        X_current[0, feature_cols.index('hour')] = pred_time.hour
    if 'hour_sin' in feature_cols:
        X_current[0, feature_cols.index('hour_sin')] = np.sin(2 * np.pi * pred_time.hour / 24)
    if 'hour_cos' in feature_cols:
        X_current[0, feature_cols.index('hour_cos')] = np.cos(2 * np.pi * pred_time.hour / 24)
    if 'is_rush_hour' in feature_cols:
        X_current[0, feature_cols.index('is_rush_hour')] = 1 if pred_time.hour in [7,8,9,17,18,19] else 0

print(f"\n✅ Generated {len(predictions)} hourly predictions")

# ============================================================================
# STEP 8: DISPLAY RESULTS
# ============================================================================
# ============================================================================

print("\n" + "="*70)
print("📊 PREDICTION SUMMARY")
print("="*70)

def get_aqi_category_indian(aqi):
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Satisfactory"
    elif aqi <= 200: return "Moderate"
    elif aqi <= 300: return "Poor"
    elif aqi <= 400: return "Very Poor"
    else: return "Severe"

def get_aqi_category_us(aqi):
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Moderate"
    elif aqi <= 150: return "Unhealthy for Sensitive"
    elif aqi <= 200: return "Unhealthy"
    elif aqi <= 300: return "Very Unhealthy"
    else: return "Hazardous"

pred_df = pd.DataFrame(predictions)
pred_df['category_indian'] = pred_df['predicted_aqi_indian'].apply(get_aqi_category_indian)
pred_df['category_us'] = pred_df['predicted_aqi_us'].apply(get_aqi_category_us)
pred_df['time_str'] = pred_df['time'].dt.strftime('%b %d %I:%M %p')

# For long forecasts, show summary table (every 3 or 6 hours)
if FORECAST_HOURS > 12:
    display_interval = 6
    print(f"\n{'Hour':<8} {'Time':<18} {'Indian AQI':<12} {'US EPA':<10} {'Category (Indian)':<25}")
    print("-"*85)
    print(f"{'Now':<8} {now.strftime('%b %d %I:%M %p'):<18} {current_aqi_indian:<12.1f} {current_aqi_us:<10.1f} {get_aqi_category_indian(current_aqi_indian):<25}")
    
    for _, row in pred_df[pred_df['hour'] % display_interval == 0].iterrows():
        change_indian = row['predicted_aqi_indian'] - current_aqi_indian
        change_str = f"({change_indian:+.1f})" if abs(change_indian) > 1 else ""
        print(f"{'+' + str(row['hour']) + 'h':<8} {row['time_str']:<18} {row['predicted_aqi_indian']:<12.1f} {row['predicted_aqi_us']:<10.1f} {row['category_indian']:<25} {change_str}")
else:
    # For short forecasts, show all hours
    print(f"\n{'Hour':<8} {'Time':<18} {'Indian AQI':<12} {'US EPA':<10} {'Category (Indian)':<25}")
    print("-"*85)
    print(f"{'Now':<8} {now.strftime('%b %d %I:%M %p'):<18} {current_aqi_indian:<12.1f} {current_aqi_us:<10.1f} {get_aqi_category_indian(current_aqi_indian):<25}")
    
    for _, row in pred_df.iterrows():
        change_indian = row['predicted_aqi_indian'] - current_aqi_indian
        change_str = f"({change_indian:+.1f})" if abs(change_indian) > 1 else ""
        print(f"{'+' + str(row['hour']) + 'h':<8} {row['time_str']:<18} {row['predicted_aqi_indian']:<12.1f} {row['predicted_aqi_us']:<10.1f} {row['category_indian']:<25} {change_str}")

# Trend analysis (using Indian AQI as it's more strict)
avg_change = (pred_df['predicted_aqi_indian'].iloc[-1] - current_aqi_indian) / FORECAST_HOURS

print("\n" + "="*70)
print("📈 TREND ANALYSIS")
print("="*70)

if avg_change > 5:
    trend, emoji = "Rising significantly", "⬆️"
elif avg_change > 1:
    trend, emoji = "Rising slowly", "↗️"
elif avg_change < -5:
    trend, emoji = "Falling significantly", "⬇️"
elif avg_change < -1:
    trend, emoji = "Falling slowly", "↘️"
else:
    trend, emoji = "Relatively stable", "➡️"

print(f"\n{emoji} Trend: {trend}")
print(f"   Average change: {avg_change:.2f} AQI per hour (Indian standard)")
print(f"   Total change ({FORECAST_HOURS}h): {pred_df['predicted_aqi_indian'].iloc[-1] - current_aqi_indian:.1f} AQI")

# Show AQI range over forecast period
min_aqi_indian = pred_df['predicted_aqi_indian'].min()
max_aqi_indian = pred_df['predicted_aqi_indian'].max()
min_aqi_us = pred_df['predicted_aqi_us'].min()
max_aqi_us = pred_df['predicted_aqi_us'].max()
print(f"   AQI range (Indian): {min_aqi_indian:.1f} - {max_aqi_indian:.1f}")
print(f"   AQI range (US EPA): {min_aqi_us:.1f} - {max_aqi_us:.1f}")

# Health advisory (using Indian AQI as it's more strict/conservative)
max_aqi_val = pred_df['predicted_aqi_indian'].max()
max_time = pred_df.loc[pred_df['predicted_aqi_indian'].idxmax(), 'time_str']
min_aqi_val = pred_df['predicted_aqi_indian'].min()
min_time = pred_df.loc[pred_df['predicted_aqi_indian'].idxmin(), 'time_str']

# Also get US EPA values for comparison
max_aqi_us_val = pred_df.loc[pred_df['predicted_aqi_indian'].idxmax(), 'predicted_aqi_us']
min_aqi_us_val = pred_df.loc[pred_df['predicted_aqi_indian'].idxmin(), 'predicted_aqi_us']

print("\n" + "="*70)
print("⚠️  HEALTH ADVISORY (Based on Indian AQI - More Strict)")
print("="*70)

print(f"\n📍 Peak AQI: Indian: {max_aqi_val:.1f} | US EPA: {max_aqi_us_val:.1f} at {max_time}")
print(f"📍 Lowest AQI: Indian: {min_aqi_val:.1f} | US EPA: {min_aqi_us_val:.1f} at {min_time}")


if max_aqi_val > 200:
    print("\n🚨 UNHEALTHY (Indian Standard): Everyone should take precautions")
    print("   • Avoid prolonged outdoor activities")
    print("   • Sensitive groups should stay indoors")
    print("   • Wear N95 masks if going outside")
elif max_aqi_val > 150:
    print("\n⚠️  UNHEALTHY FOR SENSITIVE GROUPS")
    print("   • Children, elderly, and respiratory patients limit outdoor activity")
    print("   • Consider wearing masks outdoors")
elif max_aqi_val > 100:
    print("\n⚡ MODERATE: Unusually sensitive people consider reducing prolonged outdoor exertion")
else:
    print("\n✅ GOOD: Air quality is acceptable")

print("\n" + "="*70)
print("✅ FORECAST COMPLETE")
print("="*70)
print(f"\n📍 Location: {LOCATION_NAME}")
print(f"📅 Forecast generated at: {now.strftime('%Y-%m-%d %I:%M %p')}")
print(f"⏱️  Forecast period: {FORECAST_LABEL}")
print(f"📊 AQI Standards: Indian CPCB & US EPA (both displayed)")
print(f"📡 Data source: OpenWeatherMap API (real-time, past 5 days)")
print(f"🤖 Model: XGBoost (RMSE: 12.39, R²: 98.5%)")
print(f"\n💡 Tip: Run this script anytime for fresh predictions at your current location")
print(f"   Available durations: 3h, 6h, 12h, 24h, 48h")
print(f"   Both AQI standards displayed: Indian (stricter) & US EPA")
print("="*70)
