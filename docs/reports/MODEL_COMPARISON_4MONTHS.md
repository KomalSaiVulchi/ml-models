# Model Comparison - 4 Month Training Results

## Overview
All models trained on **4 months** of AQI data (Oct 2025 - Feb 2026)
- **Total samples**: 2,784
- **Features**: 120 engineered features
- **Train/Test split**: 80/20

---

## Performance Comparison

| Model | Test RMSE | Test MAE | Test R² | Training Time |
|-------|-----------|----------|---------|---------------|
| **XGBoost** ✅ | **12.48** | **2.67** | **98.5%** | ~3 sec |
| **LightGBM** | 14.58 | 4.35 | 97.9% | ~20 sec |
| **Random Forest** | 22.55 | 11.36 | 95.0% | ~1 sec |

### Winner: **XGBoost** 🏆
- Best overall performance with 98.5% R² score
- Lowest RMSE (12.48) and MAE (2.67)
- Fast training time
- **Currently in production**

---

## Detailed Results

### 1. XGBoost (BEST MODEL ⭐)
```
Training Set:  RMSE: 5.50   MAE: 2.01   R²: 99.8%
Test Set:      RMSE: 12.48  MAE: 2.67   R²: 98.5%
```
**Top Features:**
- AQI_rolling_mean_6h: 40.3%
- AQI_lag_1: 18.5%
- PM2.5_current: 9.4%

**Hyperparameters:**
- n_estimators: 500
- max_depth: 6
- learning_rate: 0.02
- subsample: 0.8

---

### 2. LightGBM (Strong Alternative)
```
Training Set:  RMSE: 0.48   MAE: 0.14   R²: 100.0%
Test Set:      RMSE: 14.58  MAE: 4.35   R²: 97.9%
```
**Top Features:**
- AQI_rolling_mean_6h: 36.2%
- AQI_lag_1: 26.1%
- PM2.5_current: 14.4%

**Hyperparameters:**
- num_boost_round: 1000
- num_leaves: 63
- learning_rate: 0.05
- max_depth: 15

**Note:** Shows signs of overfitting (perfect training score)

---

### 3. Random Forest
```
Training Set:  RMSE: 7.59   MAE: 2.63   R²: 99.7%
Test Set:      RMSE: 22.55  MAE: 11.36  R²: 95.0%
```
**Top Features:**
- AQI_rolling_mean_6h: 8.6%
- PM2.5_current: 7.2%
- PM10_current: 7.1%

**Hyperparameters:**
- n_estimators: 300
- max_depth: 25
- min_samples_split: 4
- max_features: sqrt

**Note:** More distributed feature importance, but lower overall accuracy

---

## Key Insights

### Why XGBoost Wins:
1. **Best accuracy-speed tradeoff**: 98.5% R² in 3 seconds
2. **No overfitting**: Small gap between train/test performance
3. **Robust predictions**: Lowest error metrics
4. **Feature focus**: Heavily relies on proven important features


### Why Use Each Model:

**XGBoost** (Production):
- Real-time forecasting
- Best accuracy
- Fast inference

**LightGBM** (Backup):
- When XGBoost is unavailable
- Slightly faster training
- Very close performance (97.9% vs 98.5%)

**Random Forest** (Baseline):
- Interpretability needs
- Ensemble diversity
- Simpler deployment

---

## Recommendations

### Current Setup ✅
Keep **XGBoost** as primary production model (98.5% R²)

### Future Improvements:
1. **Ensemble**: Combine XGBoost + LightGBM predictions
2. **Feature Selection**: Reduce from 120 to top 50 features
3. **Hyperparameter Tuning**: Run Optuna/GridSearch on all models
4. **More Data**: Extend training to 6+ months for even better accuracy

---

## Files Generated

### Models:
- `saved_models/best_model.pkl` - XGBoost (production) ⭐
- `saved_models/lightgbm_4months.pkl` - LightGBM
- `saved_models/random_forest_4months.pkl` - Random Forest

### Metrics:
- `saved_models/model_metrics_4months.csv` - XGBoost metrics
- `saved_models/lightgbm_metrics_4months.json`
- `saved_models/random_forest_metrics_4months.json`

### Feature Importance:
- `saved_models/lightgbm_feature_importance.csv`
- `saved_models/random_forest_feature_importance.csv`

---

## Training Scripts

All models can be retrained with:
```bash
python3 train_xgboost_4months.py      # Best model
python3 train_lightgbm_4months.py     # Strong alternative
python3 train_random_forest_4months.py # Baseline
```

---

*Last updated: February 4, 2026*
*Dataset: 4 months (Oct 2025 - Feb 2026), 2,784 samples*
