# AirPulse

AirPulse is an end-to-end air quality forecasting and health risk assessment platform built with Python, Flask, React, XGBoost, LightGBM, and scikit-learn. It combines real-time AQI monitoring, multi-horizon pollutant forecasting, weather context, and health guidance into a single dashboard.

The current production flow uses 30 independently trained pollutant models across 6 pollutants and 5 forecast horizons. Supporting data includes 2,784 hourly observations from AQICN ground stations, OpenWeatherMap history, engineered lag/rolling features, and pollutant-specific training datasets stored under `data/` and `saved_models/`.

## Highlights

- Real-time AQI dashboard with Indian and US AQI standards.
- Forecasts for PM2.5, PM10, NO2, SO2, CO, and O3 across 1h, 3h, 6h, 12h, and 24h horizons.
- Flask API that serves current AQI, predictions, geocoding, and health-related outputs.
- React frontend for live visualization, weather context, pollutant cards, and vulnerability guidance.
- Model training scripts for XGBoost, LightGBM, Random Forest, and comparison workflows.

## Visual Preview

<p align="center">
	<img src="frontend/public/cityscape.png" alt="AirPulse cityscape background" width="360" />
	<img src="frontend/public/cloud_sun.png" alt="AirPulse weather background" width="360" />
</p>

<p align="center">
	<img src="frontend/public/aqi_good_man.png" alt="AirPulse AQI good state" width="140" />
	<img src="frontend/public/aqi_moderate_man.png" alt="AirPulse AQI moderate state" width="140" />
	<img src="frontend/public/aqi_severe_man.png" alt="AirPulse AQI severe state" width="140" />
	<img src="frontend/public/aqi_hazardous_man.png" alt="AirPulse AQI hazardous state" width="140" />
</p>

## Project Summary

AirPulse was designed to forecast air quality from station and weather data, then translate those predictions into actionable health risk information. The workflow starts with data collection, moves through feature engineering and model training, and ends with a browser-based dashboard that can be refreshed in real time.

Reported model performance for the pollutant forecasting system includes R2 = 98.5%, RMSE = 12.48, and MAE = 8.31 on a held-out test set.

## Tech Stack

- Python
- Flask
- React
- XGBoost
- LightGBM
- scikit-learn
- pandas, NumPy, joblib, requests, python-dotenv

## Repository Structure

- `backend/` - Flask API that serves AQI data and predictions.
- `frontend/` - React + Vite dashboard.
- `data/` - Training and historical datasets.
- `saved_models/` - Model artifacts, metrics, and manifests.
- `utils/` - AQI calculation helpers and category logic.
- `train_*.py` - Model training and comparison scripts.
- `fetch_*.py`, `process_*.py`, `build_*.py` - Data collection and preparation scripts.

## Setup

### 1. Create a Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### 2. Install frontend dependencies

```bash
cd frontend
npm install
```

### 3. Add environment variables

Create a `.env` file in the repository root with the required API keys:

```env
OPENWEATHER_API_KEY=your_openweather_key
AQICN_TOKEN=your_aqicn_token
```

## Run the App

Start both backend and frontend from the repository root:

```bash
./run.sh
```

Or run them separately:

```bash
cd backend
python3 app.py
```

```bash
cd frontend
npm run dev
```

The backend runs on port `5001` and the Vite frontend runs on the default dev server port.

## API Endpoints

The Flask backend exposes the following endpoints:

- `GET /api/current-aqi` - Current AQI, pollutants, and weather context.
- `GET /api/predict` - Multi-horizon AQI predictions.
- `GET /api/geocode` - Location lookup support.
- `GET /api/health` - Health check.
- `GET /api/hvi` - Health vulnerability index and advisory output.

## Data and Models

AirPulse uses pollutant-specific models stored in `saved_models/pollutant_models/` with a manifest that maps each pollutant-horizon pair to its trained artifact and feature list. The current backend loads those models at startup and computes AQI from predicted pollutant concentrations rather than predicting AQI directly.

Key datasets include:

- `data/real_aqi_training_4months.csv`
- `data/openweather_4month_history.csv`
- `data/station_measurements.csv`
- `data/pollutant_training/*.csv`

## Training Workflow

Common training and evaluation scripts include:

- `train_pollutant_models_v2.py`
- `train_pollutant_models.py`
- `train_xgboost_4months.py`
- `train_lightgbm_4months.py`
- `train_random_forest_4months.py`
- `check_model_quality.py`

## Supporting Documentation

Additional project write-ups are available in:

- [Docs overview](docs/README.md)
- [Project Abstract](docs/reports/PROJECT_ABSTRACT.md)
- [Research Paper](docs/reports/RESEARCH_PAPER.md)
- [Project Report](docs/reports/AQI_PROJECT_REPORT.md)
- [4-Month Model Comparison](docs/reports/MODEL_COMPARISON_4MONTHS.md)
- [Models Readme](docs/reports/MODELS_README.md)
- [How The Model Predicts](docs/reports/HOW_MODEL_PREDICTS.md)

## Notes

- The live app entrypoint is `run.sh`.
- The backend currently loads per-pollutant XGBoost models via `saved_models/pollutant_models/model_manifest.json`.
- The frontend is a Vite app in `frontend/`.
