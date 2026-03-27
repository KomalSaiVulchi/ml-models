#!/usr/bin/env python3
"""
Train LightGBM model on 4-month AQI dataset
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import pickle
import json
from datetime import datetime

def train_lightgbm():
    """Train LightGBM model on 4-month dataset"""
    
    print("=" * 60)
    print("LIGHTGBM MODEL TRAINING - 4 MONTHS DATA")
    print("=" * 60)
    
    # Load the processed training data
    print("\n1. Loading training data...")
    df = pd.read_csv('data/real_aqi_training_4months.csv')
    print(f"   ✓ Loaded {len(df)} samples")
    print(f"   ✓ Date range: {df['datetime'].min()} to {df['datetime'].max()}")
    
    # Prepare features and target
    print("\n2. Preparing features and target...")
    exclude_cols = ['datetime', 'AQI_target']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    X = df[feature_cols]
    y = df['AQI_target']
    
    print(f"   ✓ Features: {len(feature_cols)}")
    print(f"   ✓ Target: AQI")
    
    # Split data
    print("\n3. Splitting data (80% train, 20% test)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=False
    )
    print(f"   ✓ Train samples: {len(X_train)}")
    print(f"   ✓ Test samples: {len(X_test)}")
    
    # Create LightGBM datasets
    print("\n4. Creating LightGBM datasets...")
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
    
    # Set parameters
    print("\n5. Training LightGBM model...")
    print("   Hyperparameters:")
    print("   - objective: regression")
    print("   - metric: rmse")
    print("   - boosting_type: gbdt")
    print("   - num_leaves: 63")
    print("   - learning_rate: 0.05")
    print("   - feature_fraction: 0.8")
    print("   - bagging_fraction: 0.8")
    print("   - bagging_freq: 5")
    print("   - max_depth: 15")
    print("   - min_data_in_leaf: 20")
    
    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'num_leaves': 63,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'max_depth': 15,
        'min_data_in_leaf': 20,
        'verbose': 0
    }
    
    # Train model
    callbacks = [lgb.log_evaluation(period=100)]
    model = lgb.train(
        params,
        train_data,
        num_boost_round=1000,
        valid_sets=[train_data, test_data],
        valid_names=['train', 'test'],
        callbacks=callbacks
    )
    print("   ✓ Training completed!")
    
    # Make predictions
    print("\n6. Evaluating model performance...")
    y_train_pred = model.predict(X_train, num_iteration=model.best_iteration)
    y_test_pred = model.predict(X_test, num_iteration=model.best_iteration)
    
    # Calculate metrics
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    train_mae = mean_absolute_error(y_train, y_train_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    
    # Display results
    print("\n" + "=" * 60)
    print("PERFORMANCE METRICS")
    print("=" * 60)
    print(f"\nTraining Set:")
    print(f"  RMSE: {train_rmse:.2f}")
    print(f"  MAE:  {train_mae:.2f}")
    print(f"  R²:   {train_r2:.4f} ({train_r2*100:.2f}%)")
    
    print(f"\nTest Set:")
    print(f"  RMSE: {test_rmse:.2f}")
    print(f"  MAE:  {test_mae:.2f}")
    print(f"  R²:   {test_r2:.4f} ({test_r2*100:.2f}%)")
    
    print(f"\nBest iteration: {model.best_iteration}")
    
    # Feature importance
    print("\n" + "=" * 60)
    print("TOP 10 FEATURE IMPORTANCE")
    print("=" * 60)
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importance(importance_type='gain')
    }).sort_values('importance', ascending=False)
    
    # Normalize importance to percentages
    total_importance = feature_importance['importance'].sum()
    feature_importance['importance_pct'] = (feature_importance['importance'] / total_importance) * 100
    
    for idx, row in feature_importance.head(10).iterrows():
        print(f"{row['feature']:30s} {row['importance_pct']:6.2f}%")
    
    # Save model
    print("\n7. Saving model...")
    model_path = 'saved_models/lightgbm_4months.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"   ✓ Model saved to: {model_path}")
    
    # Save metrics
    metrics = {
        'model': 'LightGBM',
        'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'dataset': '4 months (Oct 2025 - Feb 2026)',
        'samples': len(df),
        'features': len(feature_cols),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'best_iteration': int(model.best_iteration),
        'train_rmse': float(train_rmse),
        'test_rmse': float(test_rmse),
        'train_mae': float(train_mae),
        'test_mae': float(test_mae),
        'train_r2': float(train_r2),
        'test_r2': float(test_r2),
        'hyperparameters': params
    }
    
    metrics_path = 'saved_models/lightgbm_metrics_4months.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"   ✓ Metrics saved to: {metrics_path}")
    
    # Save feature importance
    feature_importance_path = 'saved_models/lightgbm_feature_importance.csv'
    feature_importance.to_csv(feature_importance_path, index=False)
    print(f"   ✓ Feature importance saved to: {feature_importance_path}")
    
    print("\n" + "=" * 60)
    print("✅ LIGHTGBM TRAINING COMPLETED!")
    print("=" * 60)
    
    return model, metrics

if __name__ == "__main__":
    model, metrics = train_lightgbm()
