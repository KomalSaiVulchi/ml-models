#!/usr/bin/env python3
"""
Train Per-Pollutant XGBoost Models — v2 (Higher Accuracy)
==========================================================
Key improvements over v1:
  1. Early stopping with time-based validation split to prevent overfitting
  2. Horizon-adaptive hyperparameters (deeper for short, shallower for long)
  3. Log1p target transform for skewed pollutants (SO2, CO)
  4. Two-stage feature selection: drop low-importance noise features
  5. Stronger regularization across the board
  6. Lower learning rate + more trees (with early stopping, no waste)

Models trained:  30 total (6 pollutants × 5 horizons)
"""

import json
import warnings
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

warnings.filterwarnings('ignore', category=UserWarning)

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

DATA_DIR = Path(__file__).parent / 'data' / 'pollutant_training'
MODELS_DIR = Path(__file__).parent / 'saved_models' / 'pollutant_models'

POLLUTANTS = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
HORIZONS = [1, 3, 6, 12, 24]

# Pollutants where feature selection should be skipped
# (gaseous pollutants benefit from full cross-pollutant feature sets)
SKIP_FEATURE_SELECTION = {'no2', 'so2'}

# Gaseous pollutants: enforce minimum iteration count to prevent early stopping
# from being too aggressive on the small validation set (8% ≈ 2071 rows).
# v1 used 800 fixed iterations; early stopping on noisy gaseous targets halts
# far too early at longer horizons (100-240 iters), losing valid signal.
GASEOUS_MIN_ITERATIONS = 800

# Gaseous pollutants: use v1-like capacity (deeper, higher LR) since they
# benefited from it; the two-pass early stopping still prevents overshoot
GASEOUS_HP_OVERRIDE = {
    1:  {'max_depth': 7, 'min_child_weight': 8,  'reg_alpha': 0.1, 'reg_lambda': 2.0, 'gamma': 0.2, 'subsample': 0.8, 'colsample_bytree': 0.8, 'learning_rate': 0.015},
    3:  {'max_depth': 7, 'min_child_weight': 8,  'reg_alpha': 0.1, 'reg_lambda': 2.0, 'gamma': 0.2, 'subsample': 0.8, 'colsample_bytree': 0.8, 'learning_rate': 0.015},
    6:  {'max_depth': 7, 'min_child_weight': 8,  'reg_alpha': 0.1, 'reg_lambda': 2.0, 'gamma': 0.2, 'subsample': 0.8, 'colsample_bytree': 0.8, 'learning_rate': 0.015},
    12: {'max_depth': 7, 'min_child_weight': 8,  'reg_alpha': 0.1, 'reg_lambda': 2.0, 'gamma': 0.2, 'subsample': 0.8, 'colsample_bytree': 0.8, 'learning_rate': 0.015},
    24: {'max_depth': 7, 'min_child_weight': 8,  'reg_alpha': 0.1, 'reg_lambda': 2.0, 'gamma': 0.2, 'subsample': 0.8, 'colsample_bytree': 0.8, 'learning_rate': 0.015},
}

# Pollutants with high skewness benefit from log1p transform
# Note: SO2 tested worse with log transform due to spike patterns
LOG_TRANSFORM_POLLUTANTS = {'co'}

# Horizon-adaptive hyperparameters: short horizons can be deeper,
# long horizons need stronger regularization to generalize
HORIZON_PARAMS = {
    1: {
        'max_depth': 7,
        'min_child_weight': 5,
        'reg_alpha': 0.05,
        'reg_lambda': 2.0,
        'subsample': 0.85,
        'colsample_bytree': 0.8,
        'gamma': 0.05,
    },
    3: {
        'max_depth': 6,
        'min_child_weight': 8,
        'reg_alpha': 0.1,
        'reg_lambda': 3.0,
        'subsample': 0.8,
        'colsample_bytree': 0.75,
        'gamma': 0.1,
    },
    6: {
        'max_depth': 6,
        'min_child_weight': 12,
        'reg_alpha': 0.2,
        'reg_lambda': 5.0,
        'subsample': 0.75,
        'colsample_bytree': 0.7,
        'gamma': 0.15,
    },
    12: {
        'max_depth': 5,
        'min_child_weight': 15,
        'reg_alpha': 0.5,
        'reg_lambda': 8.0,
        'subsample': 0.7,
        'colsample_bytree': 0.65,
        'gamma': 0.2,
    },
    24: {
        'max_depth': 5,
        'min_child_weight': 20,
        'reg_alpha': 0.8,
        'reg_lambda': 10.0,
        'subsample': 0.65,
        'colsample_bytree': 0.6,
        'gamma': 0.3,
    },
}


def select_features_by_importance(X_train, y_train, feature_cols, horizon, top_k=None):
    """Stage-1 quick model to rank features, then keep only the most relevant."""
    # For short horizons keep more features, for long horizons prune aggressively
    if top_k is None:
        top_k = {1: 140, 3: 120, 6: 100, 12: 90, 24: 80}.get(horizon, 100)

    if len(feature_cols) <= top_k:
        return feature_cols

    quick_model = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.7,
        colsample_bytree=0.7,
        random_state=42,
        n_jobs=-1,
    )
    quick_model.fit(X_train, y_train)

    importances = quick_model.feature_importances_
    importance_idx = np.argsort(importances)[::-1][:top_k]
    selected = [feature_cols[i] for i in importance_idx]
    return selected


def train_single_model(data_path, pollutant, horizon):
    """Train a single model using two-pass approach for maximum accuracy.

    Pass 1: Train on 72%, validate on 72-80% → find optimal iteration count.
    Pass 2: Retrain on full 80% for that many iterations → more data = better model.
    Evaluate on last 20% (matches v1 split exactly).
    """
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

    if len(df) < 100:
        print(f"  ⚠ Too few samples ({len(df)}), skipping")
        return None

    X = df[valid_features]
    y = df[target_col]

    # --- Log1p transform for skewed targets ---
    use_log = pollutant in LOG_TRANSFORM_POLLUTANTS
    if use_log:
        y = np.log1p(y)

    # --- Splits ---
    n = len(X)
    split_80 = int(n * 0.80)
    split_72 = int(n * 0.72)

    X_full_train = X.iloc[:split_80]       # full 80% for pass 2
    y_full_train = y.iloc[:split_80]
    X_test = X.iloc[split_80:]             # last 20% (same as v1)
    y_test = y.iloc[split_80:]
    X_train_p1 = X.iloc[:split_72]         # pass 1 train
    y_train_p1 = y.iloc[:split_72]
    X_val_p1 = X.iloc[split_72:split_80]   # pass 1 validation
    y_val_p1 = y.iloc[split_72:split_80]

    # --- Feature selection on 80% data (skip for gaseous pollutants) ---
    if pollutant in SKIP_FEATURE_SELECTION:
        selected_features = valid_features
    else:
        selected_features = select_features_by_importance(
            X_full_train, y_full_train, valid_features, horizon
        )
    X_full_train = X_full_train[selected_features]
    X_test = X_test[selected_features]
    X_train_p1 = X_train_p1[selected_features]
    X_val_p1 = X_val_p1[selected_features]

    # --- Get horizon-specific hyperparameters ---
    if pollutant in SKIP_FEATURE_SELECTION and horizon in GASEOUS_HP_OVERRIDE:
        hp = GASEOUS_HP_OVERRIDE[horizon]
    else:
        hp = HORIZON_PARAMS[horizon]

    if not HAS_XGBOOST and not HAS_LIGHTGBM:
        print("  ❌ Neither XGBoost nor LightGBM installed!")
        return None

    # === PASS 1: Find optimal iteration count via early stopping ===
    lr = hp.get('learning_rate', 0.01)
    if HAS_XGBOOST:
        probe_model = XGBRegressor(
            n_estimators=3000,
            learning_rate=lr,
            max_depth=hp['max_depth'],
            min_child_weight=hp['min_child_weight'],
            reg_alpha=hp['reg_alpha'],
            reg_lambda=hp['reg_lambda'],
            subsample=hp['subsample'],
            colsample_bytree=hp['colsample_bytree'],
            gamma=hp['gamma'],
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=80,
        )
        probe_model.fit(
            X_train_p1, y_train_p1,
            eval_set=[(X_val_p1, y_val_p1)],
            verbose=False,
        )
        best_iter = max(100, probe_model.best_iteration or 300)
    else:
        probe_model = lgb.LGBMRegressor(
            n_estimators=3000,
            learning_rate=lr,
            max_depth=hp['max_depth'],
            min_child_samples=hp['min_child_weight'],
            reg_alpha=hp['reg_alpha'],
            reg_lambda=hp['reg_lambda'],
            subsample=hp['subsample'],
            colsample_bytree=hp['colsample_bytree'],
            min_split_gain=hp['gamma'],
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
        probe_model.fit(
            X_train_p1, y_train_p1,
            eval_set=[(X_val_p1, y_val_p1)],
            callbacks=[lgb.early_stopping(80, verbose=False)],
        )
        best_iter = max(100, probe_model.best_iteration_ or 300)

    # === PASS 2: Retrain on full 80% with calibrated iterations ===
    # Add ~10% more iterations since we have more data
    calibrated_iter = int(best_iter * 1.10)

    # For gaseous pollutants, enforce minimum iterations — early stopping
    # on the small validation set is unreliable for noisy long-horizon targets
    if pollutant in SKIP_FEATURE_SELECTION:
        calibrated_iter = max(calibrated_iter, GASEOUS_MIN_ITERATIONS)

    if HAS_XGBOOST:
        model = XGBRegressor(
            n_estimators=calibrated_iter,
            learning_rate=lr,
            max_depth=hp['max_depth'],
            min_child_weight=hp['min_child_weight'],
            reg_alpha=hp['reg_alpha'],
            reg_lambda=hp['reg_lambda'],
            subsample=hp['subsample'],
            colsample_bytree=hp['colsample_bytree'],
            gamma=hp['gamma'],
            random_state=42,
            n_jobs=-1,
        )
    else:
        model = lgb.LGBMRegressor(
            n_estimators=calibrated_iter,
            learning_rate=lr,
            max_depth=hp['max_depth'],
            min_child_samples=hp['min_child_weight'],
            reg_alpha=hp['reg_alpha'],
            reg_lambda=hp['reg_lambda'],
            subsample=hp['subsample'],
            colsample_bytree=hp['colsample_bytree'],
            min_split_gain=hp['gamma'],
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )

    model.fit(X_full_train, y_full_train)

    # --- Predict ---
    y_train_pred = model.predict(X_full_train)
    y_test_pred = model.predict(X_test)

    # --- Inverse log transform for metrics ---
    if use_log:
        y_train_actual = np.expm1(y_full_train)
        y_test_actual = np.expm1(y_test)
        y_train_pred = np.expm1(y_train_pred)
        y_test_pred = np.expm1(y_test_pred)
    else:
        y_train_actual = y_full_train
        y_test_actual = y_test

    # Clamp predictions to non-negative
    y_train_pred = np.maximum(y_train_pred, 0)
    y_test_pred = np.maximum(y_test_pred, 0)

    metrics = {
        'pollutant': pollutant,
        'horizon': horizon,
        'train_rmse': round(float(np.sqrt(mean_squared_error(y_train_actual, y_train_pred))), 3),
        'test_rmse': round(float(np.sqrt(mean_squared_error(y_test_actual, y_test_pred))), 3),
        'train_mae': round(float(mean_absolute_error(y_train_actual, y_train_pred)), 3),
        'test_mae': round(float(mean_absolute_error(y_test_actual, y_test_pred)), 3),
        'train_r2': round(float(r2_score(y_train_actual, y_train_pred)), 4),
        'test_r2': round(float(r2_score(y_test_actual, y_test_pred)), 4),
        'n_train': len(X_full_train),
        'n_test': len(X_test),
        'n_features': len(selected_features),
        'best_iteration': best_iter,
        'calibrated_iteration': calibrated_iter,
        'log_transform': use_log,
        'feature_columns': selected_features,
    }

    # Save model
    model_path = MODELS_DIR / f'{pollutant}_{horizon}h_model.pkl'
    joblib.dump(model, model_path)

    # Save feature importance
    importances = model.feature_importances_
    importance_df = pd.DataFrame({
        'feature': selected_features,
        'importance': importances
    }).sort_values('importance', ascending=False)
    importance_df.to_csv(MODELS_DIR / f'{pollutant}_{horizon}h_importance.csv', index=False)

    return metrics


def main():
    print("=" * 70)
    print("  TRAINING PER-POLLUTANT MODELS — v2 (Enhanced Accuracy)")
    print("  Improvements: early stopping, adaptive params, feature selection,")
    print("                log-transform, stronger regularization")
    print("=" * 70)

    if not HAS_XGBOOST and not HAS_LIGHTGBM:
        print("\n  ❌ Install xgboost or lightgbm: pip install xgboost lightgbm")
        return

    engine = "XGBoost" if HAS_XGBOOST else "LightGBM"
    print(f"  ML Engine: {engine}")
    print(f"  Log-transform targets: {LOG_TRANSFORM_POLLUTANTS}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    all_metrics = []
    trained_count = 0
    skipped_count = 0

    for pollutant in POLLUTANTS:
        print(f"\n{'─' * 50}")
        print(f"  Pollutant: {pollutant.upper()}"
              f"{'  [log1p transform]' if pollutant in LOG_TRANSFORM_POLLUTANTS else ''}")
        print(f"{'─' * 50}")

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
                      f"[{metrics['n_features']}feat, "
                      f"{metrics['best_iteration']}→{metrics['calibrated_iteration']}iter]")
            else:
                skipped_count += 1
                print("skipped")

    # Save metrics summary
    if all_metrics:
        metrics_df = pd.DataFrame(all_metrics)
        metrics_df.to_csv(MODELS_DIR / 'model_metrics.csv', index=False)

        # Save manifest for inference
        model_manifest = {}
        for m in all_metrics:
            key = f"{m['pollutant']}_{m['horizon']}h"
            model_manifest[key] = {
                'model_file': f"{m['pollutant']}_{m['horizon']}h_model.pkl",
                'feature_columns': m['feature_columns'],
                'test_r2': m['test_r2'],
                'test_mae': m['test_mae'],
                'log_transform': m['log_transform'],
            }

        with open(MODELS_DIR / 'model_manifest.json', 'w') as f:
            json.dump(model_manifest, f, indent=2)

        print(f"\n{'=' * 70}")
        print(f"  TRAINING SUMMARY — v2")
        print(f"{'=' * 70}")
        print(f"  Models trained: {trained_count}")
        print(f"  Models skipped: {skipped_count}")
        print(f"  Output directory: {MODELS_DIR}")

        # Load old metrics for comparison if available
        old_metrics_path = MODELS_DIR / 'model_metrics_v1_backup.csv'
        old_metrics = None
        if old_metrics_path.exists():
            old_metrics = pd.read_csv(old_metrics_path)

        print(f"\n  Performance by pollutant:")
        for poll in POLLUTANTS:
            poll_metrics = [m for m in all_metrics if m['pollutant'] == poll]
            if poll_metrics:
                avg_r2 = np.mean([m['test_r2'] for m in poll_metrics])
                avg_mae = np.mean([m['test_mae'] for m in poll_metrics])
                line = f"    {poll:5s}: avg R²={avg_r2:.3f}, avg MAE={avg_mae:.2f}"

                if old_metrics is not None:
                    old_poll = old_metrics[old_metrics['pollutant'] == poll]
                    if len(old_poll) > 0:
                        old_avg_r2 = old_poll['test_r2'].mean()
                        diff = avg_r2 - old_avg_r2
                        arrow = "↑" if diff > 0 else "↓"
                        line += f"  ({arrow}{abs(diff):.3f} vs v1)"

                print(line)

        # Per-horizon breakdown
        print(f"\n  Performance by horizon:")
        for h in HORIZONS:
            h_metrics = [m for m in all_metrics if m['horizon'] == h]
            if h_metrics:
                avg_r2 = np.mean([m['test_r2'] for m in h_metrics])
                avg_mae = np.mean([m['test_mae'] for m in h_metrics])
                overfit = np.mean([m['train_r2'] - m['test_r2'] for m in h_metrics])
                print(f"    +{h:2d}h: avg R²={avg_r2:.3f}, avg MAE={avg_mae:.2f}, "
                      f"overfit gap={overfit:.3f}")

    else:
        print("\n  ⚠ No models were trained.")


if __name__ == '__main__':
    main()
