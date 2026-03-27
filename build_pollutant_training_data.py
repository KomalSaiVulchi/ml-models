#!/usr/bin/env python3
"""
Build Per-Pollutant Training Data
==================================
Transforms raw ground station measurements into training-ready datasets
with proper lag features for each pollutant.

Architecture:
  Past Pollutants + Weather → Future Pollutant Prediction

Features per pollutant model:
  - Pollutant lag features (1h, 3h, 6h, 12h, 24h)
  - Rolling statistics (mean, std for 6h, 12h, 24h)
  - Cross-pollutant features (PM2.5/PM10 ratio, etc.)
  - Weather features (temp, humidity, wind, pressure + lags)
  - Temporal features (hour, day_of_week, month, cyclical encodings)

Targets:
  - PM2.5 at t+1, t+3, t+6, t+12, t+24
  - PM10 at t+1, t+3, t+6, t+12, t+24
  - NO2, SO2, CO, O3 similarly
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent / 'data'
INPUT_FILE = DATA_DIR / 'station_measurements.csv'
OUTPUT_DIR = DATA_DIR / 'pollutant_training'


def load_and_clean(filepath):
    """Load raw station data and prepare for feature engineering."""
    print("[1/5] Loading station measurement data...")
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(['station_name', 'timestamp']).reset_index(drop=True)

    print(f"  Raw records: {len(df)}")
    print(f"  Stations: {df['station_name'].nunique()}")
    print(f"  Cities: {df['city'].nunique()}")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Remove stations with very few records
    station_counts = df.groupby('station_name').size()
    valid_stations = station_counts[station_counts >= 48].index  # min 48 hours
    df = df[df['station_name'].isin(valid_stations)].reset_index(drop=True)
    print(f"  After filtering (≥48h per station): {len(df)} records, {df['station_name'].nunique()} stations")

    # Forward-fill small gaps within each station (max 3 hours)
    pollutants = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
    weather_cols = ['temperature', 'humidity', 'wind_speed', 'pressure']

    for col in pollutants + weather_cols:
        df[col] = df.groupby('station_name')[col].transform(
            lambda x: x.ffill(limit=3).bfill(limit=3)
        )

    return df


def build_lag_features(group, pollutant, lags=[1, 2, 3, 6, 12, 24]):
    """Build lag features for a single pollutant within a station group."""
    features = {}
    series = group[pollutant]

    for lag in lags:
        features[f'{pollutant}_lag_{lag}h'] = series.shift(lag)

    return pd.DataFrame(features, index=group.index)


def build_rolling_features(group, pollutant, windows=[6, 12, 24]):
    """Build rolling statistics for a single pollutant."""
    features = {}
    series = group[pollutant]

    for w in windows:
        rolling = series.rolling(window=w, min_periods=max(1, w // 2))
        features[f'{pollutant}_rolling_mean_{w}h'] = rolling.mean()
        features[f'{pollutant}_rolling_std_{w}h'] = rolling.std()

    return pd.DataFrame(features, index=group.index)


def build_temporal_features(df):
    """Add temporal/cyclical features from timestamp."""
    print("[2/5] Building temporal features...")

    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['month'] = df['timestamp'].dt.month
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['is_rush_hour'] = df['hour'].isin([7, 8, 9, 17, 18, 19]).astype(int)

    # Cyclical encodings
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

    return df


def build_weather_features(group):
    """Build weather features with lags."""
    features = {}
    for col in ['temperature', 'humidity', 'wind_speed', 'pressure']:
        if col in group.columns:
            features[f'{col}_current'] = group[col]
            for lag in [3, 6, 12, 24]:
                features[f'{col}_lag_{lag}h'] = group[col].shift(lag)
            # Change features
            features[f'{col}_change_6h'] = group[col] - group[col].shift(6)
            features[f'{col}_change_24h'] = group[col] - group[col].shift(24)

    # Interaction features
    if 'wind_speed' in group.columns and 'humidity' in group.columns:
        features['wind_humidity_interaction'] = group['wind_speed'] * group['humidity']
    if 'temperature' in group.columns and 'humidity' in group.columns:
        features['heat_index'] = group['temperature'] + 0.5 * (group['humidity'] - 50)
    if 'wind_speed' in group.columns:
        features['is_calm_wind'] = (group['wind_speed'] < 1).astype(int)

    return pd.DataFrame(features, index=group.index)


def build_cross_pollutant_features(group):
    """Build cross-pollutant ratio features."""
    features = {}
    if 'pm25' in group.columns and 'pm10' in group.columns:
        pm10_safe = group['pm10'].replace(0, np.nan)
        features['pm25_to_pm10_ratio'] = group['pm25'] / pm10_safe

    return pd.DataFrame(features, index=group.index)


def engineer_features(df):
    """Build all features for the training dataset."""
    pollutants = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
    # Match inference lags exactly (predict_pollutants_per_hour in app.py)
    lags = [1, 2, 3, 6, 12, 24, 48, 72, 168]
    windows = [6, 12, 24, 48, 168]

    df = build_temporal_features(df)

    print("[3/5] Building pollutant lag + rolling features...")
    all_features = []

    for station_name, group in df.groupby('station_name'):
        station_features = group.copy()

        # Lag features for each pollutant
        for poll in pollutants:
            if poll in group.columns and group[poll].notna().sum() > 0:
                lag_feats = build_lag_features(group, poll, lags)
                station_features = pd.concat([station_features, lag_feats], axis=1)

                roll_feats = build_rolling_features(group, poll, windows)
                station_features = pd.concat([station_features, roll_feats], axis=1)

        # Weather features
        wx_feats = build_weather_features(group)
        station_features = pd.concat([station_features, wx_feats], axis=1)

        # Cross-pollutant features
        cross_feats = build_cross_pollutant_features(group)
        station_features = pd.concat([station_features, cross_feats], axis=1)

        all_features.append(station_features)

    df = pd.concat(all_features, ignore_index=True)
    return df


def create_target_columns(df, pollutants, horizons=[1, 3, 6, 12, 24]):
    """Create future pollutant targets (what we want to predict)."""
    print("[4/5] Creating prediction targets...")

    for station_name, group in df.groupby('station_name'):
        for poll in pollutants:
            if poll in group.columns:
                for h in horizons:
                    col_name = f'{poll}_target_{h}h'
                    df.loc[group.index, col_name] = group[poll].shift(-h)

    return df


def save_training_data(df, pollutants):
    """Save per-pollutant training datasets."""
    print("[5/5] Saving per-pollutant training datasets...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Identify feature columns (everything that's not a target, metadata, or raw pollutant)
    metadata_cols = ['id', 'station_name', 'city', 'lat', 'lon', 'timestamp', 'data_source']
    target_pattern = '_target_'

    feature_cols = [c for c in df.columns
                    if c not in metadata_cols
                    and target_pattern not in c
                    and c not in pollutants]

    print(f"  Feature columns: {len(feature_cols)}")

    # Save combined dataset
    combined_path = OUTPUT_DIR / 'combined_training_data.csv'
    df.to_csv(combined_path, index=False)
    print(f"  Combined: {combined_path} ({len(df)} rows)")

    # Save per-pollutant datasets (each with matching targets)
    horizons = [1, 3, 6, 12, 24]
    for poll in pollutants:
        for h in horizons:
            target_col = f'{poll}_target_{h}h'
            if target_col not in df.columns:
                continue

            # Select features + target, drop rows where target is NaN
            cols = feature_cols + [target_col]
            subset = df[cols].dropna(subset=[target_col])

            # Also require key lag features to be non-null
            lag_col = f'{poll}_lag_1h'
            if lag_col in subset.columns:
                subset = subset.dropna(subset=[lag_col])

            if len(subset) < 100:
                print(f"  ⚠ Skipping {poll} +{h}h (only {len(subset)} valid rows)")
                continue

            out_path = OUTPUT_DIR / f'{poll}_predict_{h}h.csv'
            subset.to_csv(out_path, index=False)
            print(f"  {poll:5s} +{h:2d}h: {out_path.name} ({len(subset)} rows)")

    # Save feature list for inference
    feature_path = OUTPUT_DIR / 'feature_columns.json'
    import json
    with open(feature_path, 'w') as f:
        json.dump(feature_cols, f, indent=2)
    print(f"  Feature list: {feature_path}")


def main():
    print("="*70)
    print("  BUILD PER-POLLUTANT TRAINING DATA")
    print("  Architecture: Past Pollutants + Weather → Future Pollutants")
    print("="*70)

    if not INPUT_FILE.exists():
        print(f"\n  ❌ Input file not found: {INPUT_FILE}")
        print(f"  Run station_data_collector.py --export first to generate it.")
        return

    df = load_and_clean(str(INPUT_FILE))

    if len(df) < 100:
        print(f"\n  ❌ Insufficient data ({len(df)} records). Need at least 100.")
        print(f"  Run station_data_collector.py to collect more data.")
        return

    pollutants = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']

    df = engineer_features(df)
    df = create_target_columns(df, pollutants)

    # Drop rows with too many missing values
    min_features = len([c for c in df.columns if '_lag_' in c]) // 2
    df = df.dropna(thresh=len(df.columns) - min_features)

    save_training_data(df, pollutants)

    print(f"\n  ✅ Training data ready in {OUTPUT_DIR}")
    print(f"  Total usable rows: {len(df)}")


if __name__ == '__main__':
    main()
