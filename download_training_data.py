#!/usr/bin/env python3
"""
Download Per-Pollutant Training Data via Open-Meteo
=====================================================
Fetches 90 days of free hourly air quality + weather history from Open-Meteo
for 15 major Indian cities.  Saves to data/station_measurements.csv —
the exact format expected by build_pollutant_training_data.py.

Why Open-Meteo instead of AQICN bootstrap / OpenAQ?
  - Open-Meteo is the SAME source used for inference lag features, so
    there is ZERO domain shift between training and prediction.
  - Free, no API key, 92 days of history, all pollutants + weather.
  - OpenAQ v2 is unreliable for India; AQICN offers only current snapshots.

Usage:
    python download_training_data.py
"""

import time
import requests
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / 'data'
OUTPUT_PATH = DATA_DIR / 'station_measurements.csv'

# 15 major Indian cities spanning different climate regions
CITIES = {
    'delhi':      {'lat': 28.6139, 'lon': 77.2090},
    'mumbai':     {'lat': 19.0760, 'lon': 72.8777},
    'hyderabad':  {'lat': 17.3850, 'lon': 78.4867},
    'bangalore':  {'lat': 12.9716, 'lon': 77.5946},
    'chennai':    {'lat': 13.0827, 'lon': 80.2707},
    'kolkata':    {'lat': 22.5726, 'lon': 88.3639},
    'pune':       {'lat': 18.5204, 'lon': 73.8567},
    'ahmedabad':  {'lat': 23.0225, 'lon': 72.5714},
    'lucknow':    {'lat': 26.8467, 'lon': 80.9462},
    'jaipur':     {'lat': 26.9124, 'lon': 75.7873},
    'surat':      {'lat': 21.1702, 'lon': 72.8311},
    'nagpur':     {'lat': 21.1458, 'lon': 79.0882},
    'bhopal':     {'lat': 23.2599, 'lon': 77.4126},
    'patna':      {'lat': 25.5941, 'lon': 85.1376},
    'chandigarh': {'lat': 30.7333, 'lon': 76.7794},
}

PAST_DAYS = 90  # 3 months — 2160 hourly records per city


def fetch_city_data(city_name: str, lat: float, lon: float) -> pd.DataFrame:
    """Download air quality + weather data for one city from Open-Meteo."""
    print(f"  {city_name.title():12s} ({lat:.4f}, {lon:.4f}) ... ", end='', flush=True)

    # --- Air Quality (CAMS reanalysis, same source as inference) ---
    aq_resp = requests.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={
            'latitude': lat,
            'longitude': lon,
            'hourly': 'pm10,pm2_5,nitrogen_dioxide,sulphur_dioxide,ozone,carbon_monoxide',
            'past_days': PAST_DAYS,
            'forecast_days': 0,
            'timezone': 'UTC',
        },
        timeout=30,
    )
    aq_resp.raise_for_status()
    aq = aq_resp.json()['hourly']

    time.sleep(0.3)  # polite rate-limit

    # --- Weather (ERA5 + GFS, same source as inference) ---
    wx_resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            'latitude': lat,
            'longitude': lon,
            'hourly': 'temperature_2m,relative_humidity_2m,wind_speed_10m,surface_pressure',
            'past_days': PAST_DAYS,
            'forecast_days': 0,
            'timezone': 'UTC',
        },
        timeout=30,
    )
    wx_resp.raise_for_status()
    wx = wx_resp.json()['hourly']

    time.sleep(0.3)

    # Align on shorter axis — both should be identical length
    n = min(len(aq['time']), len(wx['time']))

    records = []
    for i in range(n):
        co_raw = aq['carbon_monoxide'][i]
        records.append({
            'station_name': city_name,
            'city': city_name,
            'lat': lat,
            'lon': lon,
            # Open-Meteo returns ISO 8601 like "2025-12-15T14:00"; strip the T
            'timestamp': aq['time'][i].replace('T', ' ') + ':00',
            'pm25':     aq['pm2_5'][i],
            'pm10':     aq['pm10'][i],
            'no2':      aq['nitrogen_dioxide'][i],
            'so2':      aq['sulphur_dioxide'][i],
            # CO comes in µg/m³ from Open-Meteo; convert to mg/m³ to match CPCB standard
            'co':       (co_raw / 1000.0) if co_raw is not None else None,
            'o3':       aq['ozone'][i],
            'temperature': wx['temperature_2m'][i],
            'humidity':    wx['relative_humidity_2m'][i],
            'wind_speed':  wx['wind_speed_10m'][i],
            'pressure':    wx['surface_pressure'][i],
            'data_source': 'open_meteo',
        })

    df = pd.DataFrame(records)
    valid = df[['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']].notna().any(axis=1).sum()
    print(f"{len(df)} records  ({valid} with at least one pollutant)")
    return df


def main():
    print("=" * 70)
    print("  DOWNLOAD OPEN-METEO TRAINING DATA")
    print(f"  Source : Open-Meteo AQ + Weather (free, {PAST_DAYS}-day history)")
    print(f"  Cities : {len(CITIES)}")
    print(f"  Output : {OUTPUT_PATH}")
    print("=" * 70)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_dfs = []
    failed = []

    for city_name, coords in CITIES.items():
        try:
            df = fetch_city_data(city_name, coords['lat'], coords['lon'])
            all_dfs.append(df)
            time.sleep(0.5)
        except Exception as e:
            print(f"FAILED — {e}")
            failed.append(city_name)

    if not all_dfs:
        print("\n❌  No data downloaded. Check internet connection.")
        return

    combined = pd.concat(all_dfs, ignore_index=True)

    # Remove rows where ALL pollutants are missing
    pollutant_cols = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
    before = len(combined)
    combined = combined.dropna(subset=pollutant_cols, how='all').reset_index(drop=True)
    print(f"\n  Dropped {before - len(combined)} fully-empty rows")

    combined.to_csv(OUTPUT_PATH, index=False)

    print(f"\n  ✅ Saved {len(combined):,} hourly records for {len(all_dfs)} cities")
    print(f"     Date range  : {combined['timestamp'].min()} → {combined['timestamp'].max()}")
    print(f"     Cities OK   : {', '.join(all_dfs[i]['city'].iloc[0] for i in range(len(all_dfs)))}")
    if failed:
        print(f"     Cities FAIL : {', '.join(failed)}")

    print("\n  Next steps:")
    print("    python build_pollutant_training_data.py")
    print("    python train_pollutant_models.py")


if __name__ == '__main__':
    main()
