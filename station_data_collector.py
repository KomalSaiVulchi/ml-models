#!/usr/bin/env python3
"""
Ground Station Data Collector
=============================
Fetches REAL pollutant measurements from AQICN/WAQI ground monitoring stations
and stores them in a local SQLite database for model training.

Data sources:
  - Primary: WAQI API (aqicn.org) — physical ground stations (CPCB, US Embassy, etc.)
  - Secondary: OpenAQ — aggregated ground station data for India

Usage:
  # One-time historical bootstrap from OpenAQ
  python station_data_collector.py --bootstrap

  # Continuous hourly collection (run via cron or scheduler)
  python station_data_collector.py --collect

  # Export collected data to CSV for training
  python station_data_collector.py --export
"""

import os
import sys
import json
import time
import sqlite3
import argparse
import math
from datetime import datetime, timedelta
from pathlib import Path

import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

AQICN_TOKEN = os.getenv('AQICN_TOKEN')
DB_PATH = Path(__file__).parent / 'data' / 'ground_station_data.db'
EXPORT_PATH = Path(__file__).parent / 'data' / 'station_measurements.csv'

# Major Indian cities for data collection
INDIAN_CITIES = {
    'delhi':     {'lat': 28.6139, 'lon': 77.2090},
    'mumbai':    {'lat': 19.0760, 'lon': 72.8777},
    'hyderabad': {'lat': 17.3850, 'lon': 78.4867},
    'bangalore': {'lat': 12.9716, 'lon': 77.5946},
    'chennai':   {'lat': 13.0827, 'lon': 80.2707},
    'kolkata':   {'lat': 22.5726, 'lon': 88.3639},
    'pune':      {'lat': 18.5204, 'lon': 73.8567},
    'ahmedabad': {'lat': 23.0225, 'lon': 72.5714},
    'lucknow':   {'lat': 26.8467, 'lon': 80.9462},
    'jaipur':    {'lat': 26.9124, 'lon': 75.7873},
}

# EPA AQI breakpoints for reverse-calculating concentrations from sub-indices
EPA_BREAKPOINTS = {
    'pm25': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 12.0, 35.4, 55.4, 150.4, 250.4, 350.4, 500.4],
        'ppb_to_ugm3': None
    },
    'pm10': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 54, 154, 254, 354, 424, 504, 604],
        'ppb_to_ugm3': None
    },
    'no2': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 53, 100, 360, 649, 1249, 1649, 2049],
        'ppb_to_ugm3': 1.88
    },
    'o3': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 54, 70, 85, 105, 200, 404, 504],
        'ppb_to_ugm3': 1.96
    },
    'co': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 4.4, 9.4, 12.4, 15.4, 30.4, 40.4, 50.4],
        'ppm_to_mgm3': 1.145
    },
    'so2': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 35, 75, 185, 304, 604, 804, 1004],
        'ppb_to_ugm3': 2.62
    }
}


def aqi_sub_to_concentration(pollutant, aqi_value):
    """Reverse-calculate concentration from US EPA AQI sub-index."""
    if pollutant not in EPA_BREAKPOINTS or aqi_value is None:
        return None

    bp = EPA_BREAKPOINTS[pollutant]
    aqi_bp = bp['aqi']
    conc_bp = bp['conc']

    if aqi_value <= 0:
        return 0.0
    if aqi_value >= 500:
        return conc_bp[-1]

    for i in range(len(aqi_bp) - 1):
        if aqi_bp[i] <= aqi_value <= aqi_bp[i + 1]:
            aqi_lo, aqi_hi = aqi_bp[i], aqi_bp[i + 1]
            c_lo, c_hi = conc_bp[i], conc_bp[i + 1]
            conc = (aqi_value - aqi_lo) / (aqi_hi - aqi_lo) * (c_hi - c_lo) + c_lo

            if bp.get('ppb_to_ugm3'):
                conc *= bp['ppb_to_ugm3']
            elif bp.get('ppm_to_mgm3'):
                conc *= bp['ppm_to_mgm3']

            return round(conc, 2)

    return None


def init_db():
    """Initialize SQLite database with proper schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        station_name TEXT NOT NULL,
        city TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        timestamp TEXT NOT NULL,
        pm25 REAL,
        pm10 REAL,
        no2 REAL,
        so2 REAL,
        co REAL,
        o3 REAL,
        temperature REAL,
        humidity REAL,
        wind_speed REAL,
        pressure REAL,
        data_source TEXT DEFAULT 'aqicn',
        UNIQUE(station_name, timestamp)
    )''')

    c.execute('''CREATE INDEX IF NOT EXISTS idx_city_time
                 ON measurements(city, timestamp)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_station_time
                 ON measurements(station_name, timestamp)''')

    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_PATH}")


def fetch_aqicn_station_data(lat, lon, city_name):
    """Fetch current data from nearest AQICN ground station."""
    if not AQICN_TOKEN:
        print("  ⚠ No AQICN_TOKEN set in .env")
        return []

    results = []

    try:
        # Find nearby stations using bounding box
        delta = 0.3
        bounds_url = (
            f"https://api.waqi.info/v2/map/bounds/"
            f"?latlng={lat - delta},{lon - delta},{lat + delta},{lon + delta}"
            f"&networks=all&token={AQICN_TOKEN}"
        )
        resp = requests.get(bounds_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get('status') != 'ok' or not data.get('data'):
            return []

        # Get UIDs of stations in this area
        station_uids = []
        for s in data['data']:
            uid = s.get('uid')
            aqi_val = s.get('aqi')
            if uid and aqi_val not in (None, '-', ''):
                slat = s.get('lat', 0)
                slon = s.get('lon', 0)
                try:
                    dist = _haversine(lat, lon, float(slat), float(slon))
                except (ValueError, TypeError):
                    dist = 999
                station_uids.append((uid, dist, s.get('station', {}).get('name', f'Station-{uid}')))

        station_uids.sort(key=lambda x: x[1])
        station_uids = station_uids[:5]  # top 5 nearest

        now_str = datetime.utcnow().strftime('%Y-%m-%d %H:00:00')

        for uid, dist, name in station_uids:
            try:
                url = f"https://api.waqi.info/feed/@{uid}/?token={AQICN_TOKEN}"
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                feed_data = resp.json()

                if feed_data.get('status') != 'ok':
                    continue

                feed = feed_data['data']
                iaqi = feed.get('iaqi', {})
                city_info = feed.get('city', {})
                station_geo = city_info.get('geo', [None, None])

                # Reverse-calc concentrations from AQI sub-indices
                pm25 = aqi_sub_to_concentration('pm25', iaqi.get('pm25', {}).get('v'))
                pm10 = aqi_sub_to_concentration('pm10', iaqi.get('pm10', {}).get('v'))
                no2 = aqi_sub_to_concentration('no2', iaqi.get('no2', {}).get('v'))
                so2 = aqi_sub_to_concentration('so2', iaqi.get('so2', {}).get('v'))
                co = aqi_sub_to_concentration('co', iaqi.get('co', {}).get('v'))
                o3 = aqi_sub_to_concentration('o3', iaqi.get('o3', {}).get('v'))

                # Weather from iaqi if available
                temp = iaqi.get('t', {}).get('v')
                humidity = iaqi.get('h', {}).get('v')
                wind = iaqi.get('w', {}).get('v')
                pressure = iaqi.get('p', {}).get('v')

                station_lat = float(station_geo[0]) if station_geo and station_geo[0] else lat
                station_lon = float(station_geo[1]) if station_geo and station_geo[1] else lon

                results.append({
                    'station_name': city_info.get('name', name),
                    'city': city_name,
                    'lat': station_lat,
                    'lon': station_lon,
                    'timestamp': now_str,
                    'pm25': pm25,
                    'pm10': pm10,
                    'no2': no2,
                    'so2': so2,
                    'co': co,
                    'o3': o3,
                    'temperature': temp,
                    'humidity': humidity,
                    'wind_speed': wind,
                    'pressure': pressure,
                    'data_source': 'aqicn'
                })

                time.sleep(0.3)  # Rate limiting

            except Exception as e:
                print(f"    Failed to fetch station {uid}: {e}")
                continue

    except Exception as e:
        print(f"  Error fetching AQICN data for {city_name}: {e}")

    return results


def fetch_openaq_historical(city_name, lat, lon, days_back=90):
    """Fetch historical ground station data from OpenAQ for a city.
    OpenAQ aggregates data from CPCB and state pollution boards.
    """
    results = []
    base_url = "https://api.openaq.org/v2"

    try:
        # Step 1: Find stations near this city
        loc_resp = requests.get(f"{base_url}/locations", params={
            'coordinates': f'{lat},{lon}',
            'radius': 25000,  # 25 km radius
            'country': 'IN',
            'limit': 10,
            'order_by': 'distance'
        }, timeout=15, headers={'Accept': 'application/json'})

        if not loc_resp.ok:
            print(f"  OpenAQ locations query failed: {loc_resp.status_code}")
            return []

        locations = loc_resp.json().get('results', [])
        if not locations:
            print(f"  No OpenAQ stations found near {city_name}")
            return []

        print(f"  Found {len(locations)} OpenAQ stations near {city_name}")

        date_to = datetime.utcnow()
        date_from = date_to - timedelta(days=days_back)

        for loc in locations[:3]:  # Top 3 stations
            location_id = loc['id']
            station_name = loc.get('name', f'OpenAQ-{location_id}')
            slat = loc.get('coordinates', {}).get('latitude', lat)
            slon = loc.get('coordinates', {}).get('longitude', lon)

            print(f"    Fetching {station_name} (ID: {location_id})...")

            # Fetch measurements for each pollutant
            pollutant_data = {}  # timestamp -> {pollutant: value}
            for param in ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']:
                page = 1
                while page <= 20:  # Max 20 pages per pollutant
                    try:
                        meas_resp = requests.get(f"{base_url}/measurements", params={
                            'location_id': location_id,
                            'parameter': param,
                            'date_from': date_from.isoformat() + 'Z',
                            'date_to': date_to.isoformat() + 'Z',
                            'limit': 1000,
                            'page': page,
                            'order_by': 'datetime'
                        }, timeout=20, headers={'Accept': 'application/json'})

                        if not meas_resp.ok:
                            break

                        meas_data = meas_resp.json().get('results', [])
                        if not meas_data:
                            break

                        for m in meas_data:
                            ts = m.get('date', {}).get('utc', '')
                            if ts:
                                # Round to nearest hour
                                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                hour_key = dt.strftime('%Y-%m-%d %H:00:00')
                                if hour_key not in pollutant_data:
                                    pollutant_data[hour_key] = {}

                                value = m.get('value', 0)
                                unit = m.get('unit', '')
                                # Normalize units
                                if param == 'co' and unit == 'µg/m³':
                                    value = value / 1000.0  # to mg/m³
                                pollutant_data[hour_key][param] = value

                        page += 1
                        time.sleep(0.5)  # Rate limiting

                    except Exception as e:
                        print(f"      Error fetching {param}: {e}")
                        break

            # Convert to records
            for ts, pollutants in pollutant_data.items():
                if len(pollutants) >= 2:  # Need at least 2 pollutants for useful data
                    results.append({
                        'station_name': station_name,
                        'city': city_name,
                        'lat': slat,
                        'lon': slon,
                        'timestamp': ts,
                        'pm25': pollutants.get('pm25'),
                        'pm10': pollutants.get('pm10'),
                        'no2': pollutants.get('no2'),
                        'so2': pollutants.get('so2'),
                        'co': pollutants.get('co'),
                        'o3': pollutants.get('o3'),
                        'temperature': None,
                        'humidity': None,
                        'wind_speed': None,
                        'pressure': None,
                        'data_source': 'openaq'
                    })

            print(f"      Collected {len(pollutant_data)} hourly records")
            time.sleep(1)

    except Exception as e:
        print(f"  OpenAQ fetch error for {city_name}: {e}")

    return results


def store_measurements(records):
    """Store measurement records in SQLite, skipping duplicates."""
    if not records:
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    inserted = 0

    for r in records:
        try:
            c.execute('''INSERT OR IGNORE INTO measurements
                (station_name, city, lat, lon, timestamp,
                 pm25, pm10, no2, so2, co, o3,
                 temperature, humidity, wind_speed, pressure, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (r['station_name'], r['city'], r['lat'], r['lon'], r['timestamp'],
                 r.get('pm25'), r.get('pm10'), r.get('no2'),
                 r.get('so2'), r.get('co'), r.get('o3'),
                 r.get('temperature'), r.get('humidity'),
                 r.get('wind_speed'), r.get('pressure'),
                 r.get('data_source', 'unknown')))
            if c.rowcount > 0:
                inserted += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return inserted


def add_weather_data(df, city_coords):
    """Backfill weather data from OpenWeatherMap for records missing it."""
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        return df

    missing_weather = df[df['temperature'].isna()]
    if missing_weather.empty:
        return df

    print(f"  Backfilling weather for {len(missing_weather)} records...")
    unique_cities = missing_weather['city'].unique()

    for city in unique_cities:
        if city not in city_coords:
            continue
        lat, lon = city_coords[city]['lat'], city_coords[city]['lon']
        city_mask = df['city'] == city

        # Group by day to minimize API calls
        city_records = df[city_mask & df['temperature'].isna()]
        dates = city_records['timestamp'].apply(lambda x: x[:10]).unique()

        for date_str in dates[:30]:  # Limit to prevent excessive API calls
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                start_ts = int(dt.timestamp())
                end_ts = start_ts + 86400

                resp = requests.get(
                    "http://api.openweathermap.org/data/2.5/air_pollution/history",
                    params={'lat': lat, 'lon': lon, 'start': start_ts, 'end': end_ts, 'appid': api_key},
                    timeout=10
                )
                if not resp.ok:
                    continue

                # Get weather for this day
                w_resp = requests.get(
                    "http://api.openweathermap.org/data/2.5/weather",
                    params={'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'metric'},
                    timeout=10
                )
                if w_resp.ok:
                    w = w_resp.json()
                    temp = w['main']['temp']
                    hum = w['main']['humidity']
                    wind = w.get('wind', {}).get('speed', 0)
                    pres = w['main']['pressure']

                    day_mask = city_mask & df['timestamp'].str.startswith(date_str)
                    df.loc[day_mask & df['temperature'].isna(), 'temperature'] = temp
                    df.loc[day_mask & df['humidity'].isna(), 'humidity'] = hum
                    df.loc[day_mask & df['wind_speed'].isna(), 'wind_speed'] = wind
                    df.loc[day_mask & df['pressure'].isna(), 'pressure'] = pres

                time.sleep(0.5)
            except Exception:
                continue

    return df


def collect_current():
    """Collect current readings from all configured Indian cities."""
    init_db()
    total_inserted = 0

    print("\n" + "="*60)
    print("  COLLECTING CURRENT GROUND STATION DATA")
    print("="*60)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Cities: {len(INDIAN_CITIES)}")

    for city_name, coords in INDIAN_CITIES.items():
        print(f"\n  {city_name.title()}...")
        records = fetch_aqicn_station_data(coords['lat'], coords['lon'], city_name)
        inserted = store_measurements(records)
        total_inserted += inserted
        print(f"    Fetched {len(records)} stations, inserted {inserted} new records")
        time.sleep(1)

    print(f"\n  Total new records: {total_inserted}")
    print(f"  Database: {DB_PATH}")

    # Show database stats
    conn = sqlite3.connect(str(DB_PATH))
    total = conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    cities = conn.execute("SELECT COUNT(DISTINCT city) FROM measurements").fetchone()[0]
    stations = conn.execute("SELECT COUNT(DISTINCT station_name) FROM measurements").fetchone()[0]
    date_range = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM measurements").fetchone()
    conn.close()

    print(f"\n  Database stats:")
    print(f"    Total records: {total}")
    print(f"    Cities: {cities}")
    print(f"    Stations: {stations}")
    print(f"    Date range: {date_range[0]} to {date_range[1]}")


def bootstrap_historical():
    """Bootstrap historical data from OpenAQ for training."""
    init_db()

    print("\n" + "="*60)
    print("  BOOTSTRAPPING HISTORICAL GROUND STATION DATA")
    print("="*60)
    print("  Source: OpenAQ (CPCB/State Board stations)")
    print(f"  Cities: {len(INDIAN_CITIES)}")

    total_records = 0
    for city_name, coords in INDIAN_CITIES.items():
        print(f"\n  {city_name.title()} ({coords['lat']}, {coords['lon']}):")
        records = fetch_openaq_historical(city_name, coords['lat'], coords['lon'], days_back=90)
        inserted = store_measurements(records)
        total_records += inserted
        print(f"    → Stored {inserted} new records")
        time.sleep(2)

    print(f"\n  Total bootstrapped records: {total_records}")


def export_data():
    """Export collected data to CSV for training pipeline."""
    if not DB_PATH.exists():
        print("No database found. Run --collect or --bootstrap first.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT * FROM measurements ORDER BY city, station_name, timestamp", conn
    )
    conn.close()

    if df.empty:
        print("No data in database. Run --collect or --bootstrap first.")
        return

    # Add weather data where missing
    df = add_weather_data(df, INDIAN_CITIES)

    # Forward-fill missing weather within each station
    for col in ['temperature', 'humidity', 'wind_speed', 'pressure']:
        df[col] = df.groupby('station_name')[col].transform(
            lambda x: x.ffill().bfill()
        )

    df.to_csv(str(EXPORT_PATH), index=False)

    print(f"\n  Exported {len(df)} records to {EXPORT_PATH}")
    print(f"  Cities: {df['city'].nunique()}")
    print(f"  Stations: {df['station_name'].nunique()}")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"\n  Pollutant coverage:")
    for col in ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']:
        non_null = df[col].notna().sum()
        print(f"    {col:6s}: {non_null:6d} readings ({non_null/len(df)*100:.1f}%)")


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    la1, lo1 = math.radians(lat1), math.radians(lon1)
    la2, lo2 = math.radians(lat2), math.radians(lon2)
    dlat, dlon = la2 - la1, lo2 - lo1
    a = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ground Station Data Collector')
    parser.add_argument('--bootstrap', action='store_true',
                       help='Bootstrap historical data from OpenAQ (run once)')
    parser.add_argument('--collect', action='store_true',
                       help='Collect current readings from AQICN stations')
    parser.add_argument('--export', action='store_true',
                       help='Export all data to CSV for training')
    parser.add_argument('--all', action='store_true',
                       help='Run collect + export')

    args = parser.parse_args()

    if args.bootstrap:
        bootstrap_historical()
    elif args.collect or args.all:
        collect_current()
    if args.export or args.all:
        export_data()

    if not any([args.bootstrap, args.collect, args.export, args.all]):
        parser.print_help()
        print("\nQuick start:")
        print("  python station_data_collector.py --bootstrap  # Get historical data")
        print("  python station_data_collector.py --collect     # Get current readings")
        print("  python station_data_collector.py --export      # Export to CSV")
