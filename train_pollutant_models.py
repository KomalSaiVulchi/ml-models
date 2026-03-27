#!/usr/bin/env python3
"""
Train Per-Pollutant XGBoost Models
====================================
Trains separate XGBoost models for each pollutant at each forecast horizon.

Architecture:
  For each (pollutant, horizon) pair:
    Input:  pollutant lags + weather + temporal features
    Output: predicted pollutant concentration at t+horizon

Models trained:
  pm25_1h, pm25_3h, pm25_6h, pm25_12h, pm25_24h
  pm10_1h, pm10_3h, pm10_6h, pm10_12h, pm10_24h
  no2_1h, no2_3h, no2_6h, no2_12h, no2_24h
  so2_1h, so2_3h, so2_6h, so2_12h, so2_24h
  co_1h,  co_3h,  co_6h,  co_12h,  co_24h
  o3_1h,  o3_3h,  o3_6h,  o3_12h,  o3_24h

After prediction, AQI is computed from predicted pollutant concentrations.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

DATA_DIR = Path(__file__).parent / 'data' / 'pollutant_training'
MODELS_DIR = Path(__file__).parent / 'saved_models' / 'pollutant_models'

POLLUTANTS = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
HORIZONS = [1, 3, 6, 12, 24]


def train_single_model(data_path, pollutant, horizon):
    """Train a single model for one (pollutant, horizon) pair."""
    df = pd.read_csv(data_path)
    target_col = f'{pollutant}_target_{horizon}h'

    if target_col not in df.columns:
        print(f"  ⚠ Target column {target_col} not found, skipping")
        return None

    # Feature columns = everything except the target
    feature_cols = [c for c in df.columns if c != target_col]

    # Drop rows with NaN in target
    df = df.dropna(subset=[target_col])

    # Drop features that are mostly NaN
    null_frac = df[feature_cols].isnull().mean()
    valid_features = null_frac[null_frac < 0.5].index.tolist()
    df = df[valid_features + [target_col]].dropna()

    if len(df) < 50:
        print(f"  ⚠ Too few samples ({len(df)}), skipping")
        return None

    X = df[valid_features]
    y = df[target_col]

    # Time-based split (80/20) — don't shuffle time series!
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Train model — prefer XGBoost for accuracy, fallback to LightGBM
    if HAS_XGBOOST:
        model = XGBRegressor(
            n_estimators=800,
            max_depth=7,
            learning_rate=0.015,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=8,
            gamma=0.2,
            reg_alpha=0.1,
            reg_lambda=2.0,
            random_state=42,
            n_jobs=-1
        )
    elif HAS_LIGHTGBM:
        model = lgb.LGBMRegressor(
            n_estimators=800,
            max_depth=7,
            learning_rate=0.015,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_samples=10,
            reg_alpha=0.1,
            reg_lambda=2.0,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
    else:
        print("  ❌ Neither LightGBM nor XGBoost installed!")
        return None

    model.fit(X_train, y_train)

    # Evaluate
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    metrics = {
        'pollutant': pollutant,
        'horizon': horizon,
        'train_rmse': round(float(np.sqrt(mean_squared_error(y_train, y_train_pred))), 3),
        'test_rmse': round(float(np.sqrt(mean_squared_error(y_test, y_test_pred))), 3),
        'train_mae': round(float(mean_absolute_error(y_train, y_train_pred)), 3),
        'test_mae': round(float(mean_absolute_error(y_test, y_test_pred)), 3),
        'train_r2': round(float(r2_score(y_train, y_train_pred)), 4),
        'test_r2': round(float(r2_score(y_test, y_test_pred)), 4),
        'n_train': len(X_train),
        'n_test': len(X_test),
        'n_features': len(valid_features),
        'feature_columns': valid_features
    }

    # Save model
    model_path = MODELS_DIR / f'{pollutant}_{horizon}h_model.pkl'
    joblib.dump(model, model_path)

    # Save feature importance
    if HAS_LIGHTGBM:
        importances = model.feature_importances_
    else:
        importances = model.feature_importances_

    importance_df = pd.DataFrame({
        'feature': valid_features,
        'importance': importances
    }).sort_values('importance', ascending=False)
    importance_df.to_csv(MODELS_DIR / f'{pollutant}_{horizon}h_importance.csv', index=False)

    return metrics


def main():
    print("="*70)
    print("  TRAINING PER-POLLUTANT FORECASTING MODELS")
    print("  Architecture: Past Pollutants + Weather → Future Pollutants")
    print("="*70)

    if not HAS_XGBOOST and not HAS_LIGHTGBM:
        print("\n  ❌ Install xgboost or lightgbm: pip install xgboost lightgbm")
        return

    engine = "XGBoost" if HAS_XGBOOST else "LightGBM"
    print(f"  ML Engine: {engine}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    all_metrics = []
    trained_count = 0
    skipped_count = 0

    for pollutant in POLLUTANTS:
        print(f"\n{'─'*50}")
        print(f"  Pollutant: {pollutant.upper()}")
        print(f"{'─'*50}")

        for horizon in HORIZONS:
            data_path = DATA_DIR / f'{pollutant}_predict_{horizon}h.csv'

            if not data_path.exists():
                print(f"  +{horizon:2d}h: No training data found, skipping")
                skipped_count += 1
                continue

            print(f"  +{horizon:2d}h: Training...", end=' ', flush=True)

            metrics = train_single_model(data_path, pollutant, horizon)
            if metrics:
                all_metrics.append(metrics)
                trained_count += 1
                print(f"R²={metrics['test_r2']:.3f} "
                      f"MAE={metrics['test_mae']:.2f} "
                      f"RMSE={metrics['test_rmse']:.2f} "
                      f"({metrics['n_train']}+{metrics['n_test']} samples)")
            else:
                skipped_count += 1
                print("skipped")

    # Save metrics summary
    if all_metrics:
        metrics_df = pd.DataFrame(all_metrics)
        metrics_df.to_csv(MODELS_DIR / 'model_metrics.csv', index=False)

        # Save metadata for inference
        model_manifest = {}
        for m in all_metrics:
            key = f"{m['pollutant']}_{m['horizon']}h"
            model_manifest[key] = {
                'model_file': f"{m['pollutant']}_{m['horizon']}h_model.pkl",
                'feature_columns': m['feature_columns'],
                'test_r2': m['test_r2'],
                'test_mae': m['test_mae']
            }

        with open(MODELS_DIR / 'model_manifest.json', 'w') as f:
            json.dump(model_manifest, f, indent=2)

        print(f"\n{'='*70}")
        print(f"  TRAINING SUMMARY")
        print(f"{'='*70}")
        print(f"  Models trained: {trained_count}")
        print(f"  Models skipped: {skipped_count}")
        print(f"  Output directory: {MODELS_DIR}")
        print(f"\n  Performance by pollutant:")

        for poll in POLLUTANTS:
            poll_metrics = [m for m in all_metrics if m['pollutant'] == poll]
            if poll_metrics:
                avg_r2 = np.mean([m['test_r2'] for m in poll_metrics])
                avg_mae = np.mean([m['test_mae'] for m in poll_metrics])
                print(f"    {poll:5s}: avg R²={avg_r2:.3f}, avg MAE={avg_mae:.2f}")

    else:
        print("\n  ⚠ No models were trained. Check that training data exists.")
        print(f"  Expected location: {DATA_DIR}")
        print(f"  Run build_pollutant_training_data.py first.")


if __name__ == '__main__':
    main()
