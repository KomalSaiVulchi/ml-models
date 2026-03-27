"""
Train XGBoost Model with 4-Month Dataset
"""

import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
from pathlib import Path

# Use 4-month dataset
data_file = Path("data/real_aqi_training_4months.csv")
output_file = Path("saved_models/best_model_4months.pkl")

print("="*70)
print("TRAINING XGBOOST MODEL WITH 4-MONTH DATASET")
print("="*70)

# Load data
print("\n[1/5] Loading 4-month training data...")
df = pd.read_csv(data_file)

# Remove datetime column if present
if 'datetime' in df.columns:
    df = df.drop('datetime', axis=1)

# Separate features and target
y = df['AQI_target']
X = df.drop('AQI_target', axis=1)

# Split into train/test (80/20)
split_idx = int(len(X) * 0.8)
X_train = X.iloc[:split_idx]
X_test = X.iloc[split_idx:]
y_train = y.iloc[:split_idx]
y_test = y.iloc[split_idx:]

print(f"   Total samples: {len(df)}")
print(f"   Training samples: {len(X_train)}")
print(f"   Testing samples: {len(X_test)}")
print(f"   Features: {X.shape[1]}")
print(f"   Date range: ~4 months (Oct 2025 - Feb 2026)")

# Display AQI distribution
print(f"\n   AQI Statistics:")
print(f"     Mean: {y.mean():.1f}")
print(f"     Std: {y.std():.1f}")
print(f"     Min: {y.min():.1f}")
print(f"     Max: {y.max():.1f}")

# Create and train model with optimized hyperparameters
print("\n[2/5] Training XGBoost model...")
print("   Hyperparameters optimized for 4-month dataset")

model = XGBRegressor(
    n_estimators=500,           # Increased for more data
    max_depth=6,                # Slightly deeper for more patterns
    learning_rate=0.02,         # Lower learning rate for better convergence
    subsample=0.8,              # Higher subsample with more data
    colsample_bytree=0.8,       # More features per tree
    min_child_weight=8,         # Adjusted for larger dataset
    gamma=0.2,                  # Regularization
    reg_alpha=0.1,              # L1 regularization
    reg_lambda=1.5,             # L2 regularization
    random_state=42,
    n_jobs=-1                   # Use all CPU cores
)

model.fit(X_train, y_train, verbose=False)
print("   ✅ Training complete!")

# Predictions
print("\n[3/5] Evaluating model performance...")
y_train_pred = model.predict(X_train)
y_test_pred = model.predict(X_test)

# Calculate metrics
train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
train_mae = mean_absolute_error(y_train, y_train_pred)
test_mae = mean_absolute_error(y_test, y_test_pred)
train_r2 = r2_score(y_train, y_train_pred)
test_r2 = r2_score(y_test, y_test_pred)

# Display results
print("\n" + "="*70)
print("MODEL PERFORMANCE")
print("="*70)

print("\n📊 TRAINING SET:")
print(f"   RMSE: {train_rmse:.2f}")
print(f"   MAE:  {train_mae:.2f}")
print(f"   R²:   {train_r2:.4f} ({train_r2*100:.2f}%)")

print("\n📊 TEST SET:")
print(f"   RMSE: {test_rmse:.2f}")
print(f"   MAE:  {test_mae:.2f}")
print(f"   R²:   {test_r2:.4f} ({test_r2*100:.2f}%)")

# Compare with previous model
print("\n📈 COMPARISON WITH PREVIOUS MODEL (28-day dataset):")
print(f"   Previous: RMSE 12.39, R² 92.2%")
print(f"   Current:  RMSE {test_rmse:.2f}, R² {test_r2*100:.1f}%")
improvement = ((test_r2 - 0.922) / 0.922) * 100
if improvement > 0:
    print(f"   ✅ Improvement: +{improvement:.1f}% in R²")
else:
    print(f"   ⚠️  Change: {improvement:.1f}% in R²")

# Feature importance
print("\n[4/5] Analyzing feature importance...")
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\n🔝 Top 10 Most Important Features:")
for idx, row in feature_importance.head(10).iterrows():
    print(f"   {row['feature']:<30} {row['importance']:.4f}")

# Save model
print("\n[5/5] Saving model...")
output_file.parent.mkdir(exist_ok=True, parents=True)
joblib.dump(model, output_file)
print(f"   ✅ Model saved to: {output_file}")

# Also save as best_model.pkl to use in forecast
best_model_path = Path("saved_models/best_model.pkl")
joblib.dump(model, best_model_path)
print(f"   ✅ Also saved as: {best_model_path} (for forecasting)")

# Save metrics
metrics = {
    'dataset': '4-month (2784 samples)',
    'training_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
    'train_rmse': train_rmse,
    'test_rmse': test_rmse,
    'train_mae': train_mae,
    'test_mae': test_mae,
    'train_r2': train_r2,
    'test_r2': test_r2,
    'n_features': X.shape[1],
    'n_samples': len(df)
}

metrics_df = pd.DataFrame([metrics])
metrics_df.to_csv('saved_models/model_metrics_4months.csv', index=False)
print(f"   ✅ Metrics saved to: saved_models/model_metrics_4months.csv")

print("\n" + "="*70)
print("✅ TRAINING COMPLETE")
print("="*70)
print("\nModel is ready for use in forecast_realtime.py!")
print(f"Updated accuracy: RMSE {test_rmse:.2f}, R² {test_r2*100:.1f}%")
