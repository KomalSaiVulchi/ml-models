# AQI Prediction - Holistic Health-Centric Air Quality Intelligence System

Full-stack AQI forecasting system with ML predictions, Health Vulnerability Index, and Actionable Advisory Module.

## 📁 Project Structure

```
ml models/
├── backend/
│   ├── app.py                             # Flask REST API (main backend)
│   └── requirements.txt                   # Backend dependencies
│
├── frontend/                              # React + Vite dashboard
│   ├── src/
│   │   ├── App.jsx                        # Main app component
│   │   ├── components/
│   │   │   ├── AQIDashboard.jsx           # AQI hero card with character
│   │   │   ├── PredictionChart.jsx        # 48h forecast chart
│   │   │   ├── HealthVulnerability.jsx    # HVI + Advisories panel
│   │   │   ├── WeatherParameters.jsx      # Detailed weather display
│   │   │   ├── PollutantCards.jsx         # Six pollutant cards
│   │   │   ├── LocationSelector.jsx       # City search + geolocation
│   │   │   ├── ForecastSummary.jsx        # Quick forecast badges
│   │   │   ├── ForecastSelector.jsx       # Hour selection
│   │   │   ├── WeatherCard.jsx            # Compact weather card
│   │   │   └── HealthAdvisory.jsx         # Basic health advisory
│   │   └── utils/
│   │       ├── api.js                     # API client functions
│   │       └── aqiUtils.js                # AQI scale/color definitions
│   └── vite.config.js                     # Vite config (proxy to :5001)
│
├── data/
│   ├── openweather_4month_history.csv     # Raw data (2,832 records)
│   └── real_aqi_training_4months.csv      # Training data (2,784 samples, 120 features)
│
├── saved_models/                           # Trained models
│   ├── best_model.pkl                     # XGBoost (Production) ⭐
│   ├── lightgbm_4months.pkl               # LightGBM
│   ├── random_forest_4months.pkl          # Random Forest
│   ├── model_metrics_4months.csv          # Performance metrics
│   └── *_feature_importance.csv           # Feature importance files
│
├── train_xgboost_4months.py              # Train XGBoost (best)
├── train_lightgbm_4months.py             # Train LightGBM
├── train_random_forest_4months.py        # Train Random Forest
├── fetch_4month_data.py                  # Collect historical data
├── process_4month_data.py                # Process & engineer features
├── forecast_realtime.py                  # CLI real-time forecasting
│
├── RESEARCH_PAPER.md                     # Full academic paper
├── PROJECT_ABSTRACT.md                   # Abstract with novelty
├── MODEL_COMPARISON_4MONTHS.md           # 3-model comparison
├── HOW_MODEL_PREDICTS.md                 # Prediction methodology
├── requirements.txt                      # Python dependencies
└── .env                                  # API keys (not committed)
```

## 🚀 Quick Start

### Train Models
```bash
# Best model (recommended)
python train_xgboost_4months.py

# Alternative models
python train_lightgbm_4months.py
python train_random_forest_4months.py
```

### Run Real-time Forecast
```bash
python forecast_realtime.py
```

This will:
1. Auto-detect your location
2. Fetch 120 hours of historical AQI data
3. Calculate 120 features
4. Predict next 3/6/12/24/48 hours (your choice)
5. Display both Indian CPCB and US EPA AQI standards

## 📊 Models Included

### 1. XGBoost ⭐ (Production)
- **File:** `train_xgboost_4months.py`
- **Algorithm:** Gradient boosting with 500 trees
- **Performance:** RMSE 12.48, MAE 2.67, R² 98.5%
- **Training:** 4 months of data (2,784 samples)
- **Status:** Best model, currently in production

### 2. LightGBM (Strong Backup)
- **File:** `train_lightgbm_4months.py`
- **Algorithm:** Fast gradient boosting
- **Performance:** RMSE 14.58, MAE 4.35, R² 97.9%
- **Advantages:** Faster training, very close performance

### 3. Random Forest (Baseline)
- **File:** `train_random_forest_4months.py`
- **Algorithm:** Ensemble of 300 decision trees
- **Performance:** RMSE 22.55, MAE 11.36, R² 95.0%
- **Advantages:** Simpler, more interpretable
real_aqi_training_4months.csv`
- **Rows:** 2,784 samples
- **Period:** Oct 7, 2025 - Feb 4, 2026 (4 months)
- **Features:** 120 engineered features
  - 48 AQI lags (past 48 hours)
  - 15 Pollutant features (PM2.5, PM10, NO2, SO2, CO, O3)
  - 20 Weather features (temp, humidity, wind, pressure + lags)
  - 19 Rolling statistics (6h, 12h, 24h windows)
  - 14 Temporal features (hour, day, month, season, etc.)
  - 4 Change metrics (1h, 6h, 24h trends)

**Split:** 80% training (2,227 samples), 20% testing (557
  - Temporal (hour, day, month, weekend, rush hour)

**Split:** 80% training (537 samples), 20% testing (135 samples)

## 🎯 Output Files

Aftbest_model.pkl` - XGBoost (production model) ⭐
- `lightgbm_4months.pkl` - LightGBM model
- `random_forest_4months.pkl` - Random Forest model

**Metrics Files:**
- `model_metrics_4months.csv` - XGBoost performance
- `lightgbm_metrics_4months.json` - LightGBM performance
- `random_forest_metrics_4months.json` - Random Forest performance

**Feature Importance:**
- `lightgbm_feature_importance.csv`
- `random_forest_feature_importance.csv`
- `xgboost_metrics.json` - Performance metrics
- `lightgbm_metrics.json` - Performance metrics
- `model_comparison.json` - Comparison of all models

## 📝 Using Trained Models

### Load Best Model
```python
import joblib
# NOTE (deployment): The live backend launched by [run.sh](run.sh)
# loads the per-pollutant model manifest from
# `saved_models/pollutant_models/model_manifest.json` and uses the
# 30 per-pollutant models (6 pollutants × 5 horizons) for forecasting.
# The single-file `saved_models/best_model.pkl` is retained for the
# legacy 4-month AQI benchmark scripts but is not used by the live API.

# Example (legacy): load the single-AQI benchmark model (not used by the
# deployed backend) and run predictions
model = joblib.load('saved_models/best_model.pkl')
predictions = model.predict(X_test)
```

### Load Specific Model
```python
import joblib
Model Performance
```python
import pandas as pd

# Load XGBoost metrics
metrics = pd.read_csv('saved_models/model_metrics_4months.csv')
print(metrics)

# Output:
# Test RMSE: 12.48
# Test MAE: 2.67
# Test R²: 0.985
with open('saved_models/model_comparison.json', 'r') as f:
    comparison = json.load(f)
    
print(f"Best model: {comparison['best_model']}")
print(f"Best RMSE: {comparison['best_rmse']:.2f}")
```date range in `fetch_4month_data.py`
2. Run `python fetch_4month_data.py` (collects 4 months of data)
3. Run `python process_4month_data.py` (processes & engineers features)
4. Run `python train_xgboost_4months.py` (trains best model)

## 📦 Dependencies

```bash
pip install pandas numpy scikit-learn xgboost lightgbm requests python-dotenv
```

## ✅ Current Results (4-Month Training)

| Model | Test RMSE | Test MAE | Test R² | Status |
|-------|-----------|----------|---------|--------|
| **XGBoost** | **12.48** | **2.67** | **98.5%** | ⭐ Production |
| LightGBM | 14.58 | 4.35 | 97.9% | Backup |
| Random Forest | 22.55 | 11.36 | 95.0% | Baseline |

**Winner:** XGBoost with 98.5% R² (best accuracy)

### Top 3 Most Important Features:
1. `AQI_rolling_mean_6h` - 40.3%
2. `AQI_lag_1` - 18.5%
3. `PM2.5_current` - 9.4, OpenWeatherMap API
**Training Period:** October 2025 - February 2026 (4 months)
**Production Model:** XGBoost with 98.5% R² accuracy
| Random Forest | ~11.14 | ~0.85 | Good |
| XGBoost | ~6.65 | ~0.95 | ⭐ Best |
| LightGBM | ~7.73 | ~0.93 | Very Good |

**Winner:** Usually XGBoost with RMSE around 6.65 and R² of 94.6%

---

**Built with:** Python, scikit-learn, XGBoost, LightGBM
