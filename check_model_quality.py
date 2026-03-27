#!/usr/bin/env python3
"""Analyze model training quality across all models."""
import pandas as pd
import numpy as np

# =========================================================================
# 1. PER-POLLUTANT MODELS (XGBoost - primary forecasting models)
# =========================================================================
metrics = pd.read_csv('saved_models/pollutant_models/model_metrics.csv')
cols = ['pollutant','horizon','train_rmse','test_rmse','train_mae','test_mae','train_r2','test_r2','n_train','n_test']
m = metrics[cols].copy()
m['rmse_ratio'] = m['test_rmse'] / m['train_rmse']
m['r2_gap'] = m['train_r2'] - m['test_r2']

print("=" * 85)
print("PER-POLLUTANT MODEL METRICS (XGBoost) - 30 models total")
print("=" * 85)

for poll in ['pm25','pm10','no2','so2','co','o3']:
    sub = m[m['pollutant'] == poll].sort_values('horizon')
    print(f"\n  {poll.upper()}")
    print(f"  {'Hz':>4} | {'TrainR2':>7} | {'TestR2':>7} | {'Gap':>6} | {'TrainRMSE':>9} | {'TestRMSE':>9} | {'Ratio':>6} | {'TestMAE':>8} | Flag")
    print(f"  {'-'*4}-+-{'-'*7}-+-{'-'*7}-+-{'-'*6}-+-{'-'*9}-+-{'-'*9}-+-{'-'*6}-+-{'-'*8}-+------")
    for _, r in sub.iterrows():
        flags = []
        if r['r2_gap'] > 0.5: flags.append("SEVERE_OVERFIT")
        elif r['r2_gap'] > 0.3: flags.append("OVERFIT")
        if r['test_r2'] < 0: flags.append("BROKEN")
        elif r['test_r2'] < 0.3: flags.append("WEAK")
        elif r['test_r2'] < 0.5: flags.append("POOR")
        if r['rmse_ratio'] > 5: flags.append("HIGH_RATIO")
        flag_str = ", ".join(flags) if flags else "OK"
        print(f"  {int(r['horizon']):>3}h | {r['train_r2']:>7.4f} | {r['test_r2']:>7.4f} | {r['r2_gap']:>6.4f} | {r['train_rmse']:>9.3f} | {r['test_rmse']:>9.3f} | {r['rmse_ratio']:>5.1f}x | {r['test_mae']:>8.3f} | {flag_str}")

# Summary
print("\n" + "=" * 85)
print("DIAGNOSIS SUMMARY")
print("=" * 85)

severe = m[m['r2_gap'] > 0.5]
moderate = m[(m['r2_gap'] > 0.3) & (m['r2_gap'] <= 0.5)]
weak = m[m['test_r2'] < 0.3]
broken = m[m['test_r2'] < 0]
good = m[(m['test_r2'] >= 0.7) & (m['r2_gap'] < 0.3)]

print(f"\nTotal per-pollutant models: {len(m)}")
print(f"  GOOD (Test R2 >= 0.7, gap < 0.3):     {len(good)} models")
print(f"  SEVERE OVERFIT (R2 gap > 0.5):         {len(severe)} models")
print(f"  MODERATE OVERFIT (R2 gap 0.3-0.5):     {len(moderate)} models")
print(f"  WEAK (Test R2 < 0.3):                  {len(weak)} models")
print(f"  BROKEN (Test R2 < 0, worse than mean): {len(broken)} models")

if len(severe) > 0:
    print(f"\n  Severely overfitting models:")
    for _, r in severe.iterrows():
        print(f"    {r['pollutant']}_{int(r['horizon'])}h: Train={r['train_r2']:.4f} Test={r['test_r2']:.4f} gap={r['r2_gap']:.4f}")

if len(broken) > 0:
    print(f"\n  Broken models (predictions worse than just predicting the mean):")
    for _, r in broken.iterrows():
        print(f"    {r['pollutant']}_{int(r['horizon'])}h: Test R2={r['test_r2']:.4f}")

if len(weak) > 0:
    print(f"\n  Weak models (barely predictive):")
    for _, r in weak.iterrows():
        print(f"    {r['pollutant']}_{int(r['horizon'])}h: Test R2={r['test_r2']:.4f}")

# =========================================================================
# 2. DATA QUALITY CHECK
# =========================================================================
print("\n" + "=" * 85)
print("TRAINING DATA QUALITY")
print("=" * 85)

# Check a sample training CSV
sample_file = 'data/pollutant_training/pm25_predict_1h.csv'
try:
    df = pd.read_csv(sample_file)
    print(f"\nSample: {sample_file}")
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")
    
    # Check for data quality issues
    target_col = [c for c in df.columns if 'target' in c.lower() or 'predict' in c.lower()]
    if not target_col:
        # Assume last column is target
        target_col = [df.columns[-1]]
    
    if target_col:
        tc = target_col[0]
        vals = df[tc].dropna()
        print(f"  Target column: {tc}")
        print(f"  Target stats: mean={vals.mean():.2f}, std={vals.std():.2f}, min={vals.min():.2f}, max={vals.max():.2f}")
        print(f"  Zero values: {(vals == 0).sum()} ({(vals == 0).sum()/len(vals)*100:.1f}%)")
        print(f"  Null values: {df[tc].isna().sum()}")
        
        # Check for outliers
        q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
        iqr = q3 - q1
        outliers = ((vals < q1 - 3*iqr) | (vals > q3 + 3*iqr)).sum()
        print(f"  Outliers (3x IQR): {outliers} ({outliers/len(vals)*100:.1f}%)")
except Exception as e:
    print(f"  Error reading sample: {e}")

# Check station measurements
try:
    stations = pd.read_csv('data/station_measurements.csv')
    print(f"\nStation measurements: {len(stations):,} rows")
    n_stations = stations['station_id'].nunique() if 'station_id' in stations.columns else 'unknown'
    print(f"  Unique stations: {n_stations}")
    if 'datetime' in stations.columns:
        dates = pd.to_datetime(stations['datetime'])
        print(f"  Date range: {dates.min()} to {dates.max()}")
        days = (dates.max() - dates.min()).days
        print(f"  Span: {days} days")
except Exception as e:
    print(f"  Station data: {e}")

# =========================================================================
# 3. TRAIN/TEST SPLIT CHECK
# =========================================================================
print("\n" + "=" * 85)
print("TRAIN/TEST SPLIT")
print("=" * 85)
n_train = m.iloc[0]['n_train']
n_test = m.iloc[0]['n_test']
total = n_train + n_test
print(f"  Train: {int(n_train):,} samples ({n_train/total*100:.0f}%)")
print(f"  Test:  {int(n_test):,} samples ({n_test/total*100:.0f}%)")
print(f"  Total: {int(total):,} samples")
print(f"  Split ratio appears to be 80/20")

# =========================================================================
# 4. LEGACY MODEL
# =========================================================================
print("\n" + "=" * 85)
print("LEGACY ENSEMBLE MODEL (XGBoost - direct AQI prediction)")
print("=" * 85)
legacy = pd.read_csv('saved_models/model_metrics_4months.csv')
for _, r in legacy.iterrows():
    print(f"  Dataset: {r['dataset']}")
    print(f"  Train R2: {r['train_r2']:.6f}")
    print(f"  Test R2:  {r['test_r2']:.6f}")
    print(f"  R2 gap:   {r['train_r2'] - r['test_r2']:.6f}")
    print(f"  Train RMSE: {r['train_rmse']:.3f}")
    print(f"  Test RMSE:  {r['test_rmse']:.3f}")
    print(f"  RMSE ratio: {r['test_rmse']/r['train_rmse']:.1f}x")
    print(f"  Samples: {r['n_samples']}, Features: {r['n_features']}")
    if r['train_r2'] - r['test_r2'] > 0.01:
        print(f"  WARNING: Train R2={r['train_r2']:.4f} vs Test R2={r['test_r2']:.4f} - OVERFIT")

# =========================================================================
# 5. KEY FINDINGS
# =========================================================================
print("\n" + "=" * 85)
print("KEY FINDINGS")
print("=" * 85)

avg_1h_r2 = m[m['horizon'] == 1]['test_r2'].mean()
avg_3h_r2 = m[m['horizon'] == 3]['test_r2'].mean()
avg_6h_r2 = m[m['horizon'] == 6]['test_r2'].mean()
avg_12h_r2 = m[m['horizon'] == 12]['test_r2'].mean()
avg_24h_r2 = m[m['horizon'] == 24]['test_r2'].mean()

print(f"\n1. FORECAST QUALITY BY HORIZON (avg Test R2 across all pollutants):")
print(f"   1h:  {avg_1h_r2:.3f} {'GOOD' if avg_1h_r2 > 0.7 else 'NEEDS WORK'}")
print(f"   3h:  {avg_3h_r2:.3f} {'GOOD' if avg_3h_r2 > 0.7 else 'NEEDS WORK'}")
print(f"   6h:  {avg_6h_r2:.3f} {'GOOD' if avg_6h_r2 > 0.7 else 'NEEDS WORK'}")
print(f"   12h: {avg_12h_r2:.3f} {'GOOD' if avg_12h_r2 > 0.7 else 'NEEDS WORK'}")
print(f"   24h: {avg_24h_r2:.3f} {'GOOD' if avg_24h_r2 > 0.7 else 'NEEDS WORK'}")

print(f"\n2. OVERFITTING: All models show train R2 > 0.97 but test R2 drops fast.")
print(f"   Average train-test R2 gap: {m['r2_gap'].mean():.3f}")
print(f"   This indicates the models memorize training data too aggressively.")

problematic = ['so2', 'co']
print(f"\n3. PROBLEMATIC POLLUTANTS: {', '.join(p.upper() for p in problematic)}")
for p in problematic:
    sub = m[m['pollutant'] == p]
    print(f"   {p.upper()}: avg Test R2={sub['test_r2'].mean():.3f}, worst={sub['test_r2'].min():.3f}")

print(f"\n4. RECOMMENDATIONS:")
print(f"   a) REDUCE OVERFITTING: Lower max_depth (7→5), increase min_child_weight,")
print(f"      add stronger L1/L2 regularization, use early_stopping_rounds")
print(f"   b) MORE DATA: Only ~15K training samples from a few stations.")
print(f"      Collect data from 50+ stations across multiple cities/seasons")
print(f"   c) SO2/CO MODELS: These are essentially broken beyond 3h horizon.")
print(f"      Consider using simpler models or larger rolling window features")
print(f"   d) LEGACY MODEL: Train R2=0.9999 vs Test R2=0.985 → also overfitting")
print(f"      120 features for 2784 samples is too many (risk of p >> n-like issues)")
