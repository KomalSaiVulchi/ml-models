"""
AQI Forecasting Backend API
Flask server providing current AQI data, ML predictions, and geocoding.
"""

import sys
import os
from pathlib import Path

# Add project root to path so we can import utils
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import joblib
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(PROJECT_ROOT / '.env')

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv('OPENWEATHER_API_KEY')
AQICN_TOKEN = os.getenv('AQICN_TOKEN')

# ---------------------------------------------------------------------------
# Load Per-Pollutant Models at startup
# ---------------------------------------------------------------------------
POLLUTANT_MODELS_DIR = PROJECT_ROOT / 'saved_models' / 'pollutant_models'

# Per-pollutant models: each pollutant (PM2.5, PM10, NO2, SO2, CO, O3)
# has models for multiple forecast horizons (1h, 3h, 6h, 12h, 24h).
# AQI is ALWAYS computed from predicted pollutant concentrations — never directly.
POLLUTANT_MODELS = {}       # flat key: "pm25_6h" -> model
POLLUTANT_FEATURE_COLS = {} # flat key: "pm25_6h" -> [feature_list]
POLLUTANT_LOG_TRANSFORM = {} # flat key: "co_6h" -> True if model uses log1p target
FORECAST_HORIZONS = [1, 3, 6, 12, 24]
POLLUTANT_KEYS = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']

import json as _json

manifest_path = POLLUTANT_MODELS_DIR / 'model_manifest.json'
if manifest_path.exists():
    with open(manifest_path) as f:
        manifest = _json.load(f)
    loaded = 0
    for key, info in manifest.items():
        model_file = POLLUTANT_MODELS_DIR / info['model_file']
        if model_file.exists():
            POLLUTANT_MODELS[key] = joblib.load(model_file)
            POLLUTANT_FEATURE_COLS[key] = info['feature_columns']
            POLLUTANT_LOG_TRANSFORM[key] = info.get('log_transform', False)
            loaded += 1
    print(f"Per-pollutant models loaded: {loaded} models")
else:
    print("WARNING: Per-pollutant models not found!")
    print("  → Run: python station_data_collector.py --bootstrap")
    print("  → Run: python build_pollutant_training_data.py")
    print("  → Run: python train_pollutant_models.py")


# ---------------------------------------------------------------------------
# Satellite-to-Ground Correction Factors
# OWM satellite estimates underreport ground-level pollution by ~30-40%.
# Per-pollutant multipliers derived from satellite vs ground station studies.
# Particulates (PM2.5/PM10) have larger bias; gases are closer.
# ---------------------------------------------------------------------------
SATELLITE_CORRECTION = {
    'pm25': 1.35,   # Satellite underestimates fine particulates significantly
    'pm10': 1.30,   # Coarse particulates also underestimated
    'no2':  1.25,   # NOx underestimation moderate
    'so2':  1.20,   # SO2 moderate
    'co':   1.20,   # CO moderate
    'o3':   1.15,   # Ozone relatively well captured by satellite
}

# ---------------------------------------------------------------------------
# AQI Calculation Helpers
# ---------------------------------------------------------------------------

def calculate_indian_aqi_value(pm25, pm10, no2=0, so2=0, co=0, o3=0):
    """Calculate Indian CPCB AQI from pollutant concentrations."""
    def sub_index(conc, breakpoints):
        for bp in breakpoints:
            if bp[0] <= conc <= bp[1]:
                return ((bp[3] - bp[2]) / (bp[1] - bp[0])) * (conc - bp[0]) + bp[2]
        return breakpoints[-1][3]

    # CPCB National AQI breakpoints — continuous ranges (no gaps)
    pm25_bp = [(0,30,0,50),(30.01,60,51,100),(60.01,90,101,200),(90.01,120,201,300),(120.01,250,301,400),(250.01,999,401,500)]
    pm10_bp = [(0,50,0,50),(50.01,100,51,100),(100.01,250,101,200),(250.01,350,201,300),(350.01,430,301,400),(430.01,999,401,500)]
    no2_bp = [(0,40,0,50),(40.01,80,51,100),(80.01,180,101,200),(180.01,280,201,300),(280.01,400,301,400),(400.01,999,401,500)]
    so2_bp = [(0,40,0,50),(40.01,80,51,100),(80.01,380,101,200),(380.01,800,201,300),(800.01,1600,301,400),(1600.01,9999,401,500)]
    co_bp = [(0,1.0,0,50),(1.01,2.0,51,100),(2.01,10,101,200),(10.01,17,201,300),(17.01,34,301,400),(34.01,999,401,500)]
    o3_bp = [(0,50,0,50),(50.01,100,51,100),(100.01,168,101,200),(168.01,208,201,300),(208.01,748,301,400),(748.01,9999,401,500)]

    sub_indices = {}
    if pm25 > 0: sub_indices['PM2.5'] = sub_index(pm25, pm25_bp)
    if pm10 > 0: sub_indices['PM10'] = sub_index(pm10, pm10_bp)
    if no2 > 0: sub_indices['NO2'] = sub_index(no2, no2_bp)
    if so2 > 0: sub_indices['SO2'] = sub_index(so2, so2_bp)
    if co > 0: sub_indices['CO'] = sub_index(co, co_bp)
    if o3 > 0: sub_indices['O3'] = sub_index(o3, o3_bp)

    if not sub_indices:
        return 0, 'N/A'

    dominant = max(sub_indices, key=sub_indices.get)
    return round(sub_indices[dominant], 1), dominant


def calculate_us_epa_aqi(pm25=0, pm10=0, no2=0, so2=0, co=0, o3=0):
    """Calculate US EPA AQI from all 6 pollutant concentrations.
    Units: PM2.5/PM10/NO2/SO2/O3 in µg/m³, CO in mg/m³.
    Returns (aqi_value, dominant_pollutant).
    """
    def sub_index(conc, breakpoints):
        for bp in breakpoints:
            if bp[0] <= conc <= bp[1]:
                return ((bp[3] - bp[2]) / (bp[1] - bp[0])) * (conc - bp[0]) + bp[2]
        return breakpoints[-1][3]

    # US EPA AQI breakpoints — continuous ranges (no gaps)
    pm25_bp = [(0,12.0,0,50),(12.1,35.4,51,100),(35.5,55.4,101,150),(55.5,150.4,151,200),(150.5,250.4,201,300),(250.5,500.4,301,500)]
    pm10_bp = [(0,54,0,50),(54.01,154,51,100),(154.01,254,101,150),(254.01,354,151,200),(354.01,424,201,300),(424.01,604,301,500)]
    # NO2: convert µg/m³ → ppb (1 ppb = 1.88 µg/m³)
    no2_bp = [(0,53,0,50),(53.01,100,51,100),(100.01,360,101,150),(360.01,649,151,200),(649.01,1249,201,300),(1249.01,2049,301,500)]
    # SO2: convert µg/m³ → ppb (1 ppb = 2.62 µg/m³)
    so2_bp = [(0,35,0,50),(35.01,75,51,100),(75.01,185,101,150),(185.01,304,151,200),(304.01,604,201,300),(604.01,1004,301,500)]
    # CO: convert mg/m³ → ppm (1 ppm = 1.145 mg/m³)
    co_bp = [(0,4.4,0,50),(4.41,9.4,51,100),(9.41,12.4,101,150),(12.41,15.4,151,200),(15.41,30.4,201,300),(30.41,50.4,301,500)]
    # O3: convert µg/m³ → ppb (1 ppb = 2.0 µg/m³)
    o3_bp = [(0,54,0,50),(54.01,70,51,100),(70.01,85,101,150),(85.01,105,151,200),(105.01,200,201,300)]

    sub_indices = {}
    if pm25 > 0: sub_indices['PM2.5'] = sub_index(pm25, pm25_bp)
    if pm10 > 0: sub_indices['PM10'] = sub_index(pm10, pm10_bp)
    if no2 > 0: sub_indices['NO2'] = sub_index(no2 / 1.88, no2_bp)
    if so2 > 0: sub_indices['SO2'] = sub_index(so2 / 2.62, so2_bp)
    if co > 0: sub_indices['CO'] = sub_index(co / 1.145, co_bp)
    if o3 > 0: sub_indices['O3'] = sub_index(o3 / 2.0, o3_bp)

    if not sub_indices:
        return 0, 'N/A'
    dominant = max(sub_indices, key=sub_indices.get)
    return round(sub_indices[dominant], 1), dominant


def get_aqi_category(aqi):
    """Return Indian CPCB category name and color for given AQI value."""
    if aqi <= 50:
        return {'category': 'Good', 'color': '#00E400', 'level': 1}
    elif aqi <= 100:
        return {'category': 'Satisfactory', 'color': '#92D050', 'level': 2}
    elif aqi <= 200:
        return {'category': 'Moderate', 'color': '#FFD700', 'level': 3}
    elif aqi <= 300:
        return {'category': 'Poor', 'color': '#FF4444', 'level': 4}
    elif aqi <= 400:
        return {'category': 'Very Poor', 'color': '#CC0000', 'level': 5}
    else:
        return {'category': 'Severe', 'color': '#7E0023', 'level': 6}


def get_us_aqi_category(aqi):
    """Return US EPA category name and color for given AQI value."""
    if aqi <= 50:
        return {'category': 'Good', 'color': '#00E400', 'level': 1}
    elif aqi <= 100:
        return {'category': 'Moderate', 'color': '#FFFF00', 'level': 2}
    elif aqi <= 150:
        return {'category': 'Unhealthy for Sensitive Groups', 'color': '#FF7E00', 'level': 3}
    elif aqi <= 200:
        return {'category': 'Unhealthy', 'color': '#FF0000', 'level': 4}
    elif aqi <= 300:
        return {'category': 'Very Unhealthy', 'color': '#8F3F97', 'level': 5}
    else:
        return {'category': 'Hazardous', 'color': '#7E0023', 'level': 6}


def get_pollutant_level(name, value):
    """Return level info for a specific pollutant."""
    thresholds = {
        'PM2.5': [(30, 'Good'), (60, 'Satisfactory'), (90, 'Moderate'), (120, 'Poor'), (250, 'Very Poor')],
        'PM10': [(50, 'Good'), (100, 'Satisfactory'), (250, 'Moderate'), (350, 'Poor'), (430, 'Very Poor')],
        'NO2': [(40, 'Good'), (80, 'Satisfactory'), (180, 'Moderate'), (280, 'Poor'), (400, 'Very Poor')],
        'SO2': [(40, 'Good'), (80, 'Satisfactory'), (380, 'Moderate'), (800, 'Poor'), (1600, 'Very Poor')],
        'CO': [(1, 'Good'), (2, 'Satisfactory'), (10, 'Moderate'), (17, 'Poor'), (34, 'Very Poor')],
        'O3': [(50, 'Good'), (100, 'Satisfactory'), (168, 'Moderate'), (208, 'Poor'), (748, 'Very Poor')],
    }
    level_colors = {
        'Good': '#00E400', 'Satisfactory': '#92D050', 'Moderate': '#FFD700',
        'Poor': '#FF4444', 'Very Poor': '#CC0000', 'Severe': '#7E0023'
    }

    pollutant_thresholds = thresholds.get(name, [(100, 'Good'), (200, 'Moderate')])
    level = 'Severe'
    for threshold, lvl in pollutant_thresholds:
        if value <= threshold:
            level = lvl
            break
    return {'level': level, 'color': level_colors.get(level, '#7E0023')}


def get_health_advisory(aqi):
    """Return health advisory based on AQI value."""
    if aqi <= 50:
        return "Air quality is excellent! Enjoy outdoor activities freely."
    elif aqi <= 100:
        return "Air quality is acceptable. Sensitive individuals should take minimal precautions."
    elif aqi <= 200:
        return "Moderate air quality. Reduce prolonged outdoor exertion if you experience symptoms."
    elif aqi <= 300:
        return "Poor air quality. Everyone should reduce outdoor activities. Wear a mask outdoors."
    elif aqi <= 400:
        return "Very poor air quality. Avoid outdoor activities. Stay indoors with windows closed."
    else:
        return "Severe! Health emergency. Stay indoors. Use air purifiers. Wear N95 mask if going out."


# ---------------------------------------------------------------------------
# Dynamic Health Vulnerability Index (HVI)
# ---------------------------------------------------------------------------

# Vulnerability multipliers by demographic profile
VULNERABILITY_PROFILES = {
    'general': {
        'label': 'General Adult',
        'pm25_weight': 1.0, 'pm10_weight': 1.0, 'no2_weight': 1.0,
        'o3_weight': 1.0, 'co_weight': 1.0, 'so2_weight': 1.0,
        'base_sensitivity': 1.0,
    },
    'child': {
        'label': 'Child (0-14 years)',
        'pm25_weight': 1.6, 'pm10_weight': 1.4, 'no2_weight': 1.3,
        'o3_weight': 1.5, 'co_weight': 1.2, 'so2_weight': 1.3,
        'base_sensitivity': 1.5,
    },
    'elderly': {
        'label': 'Elderly (60+ years)',
        'pm25_weight': 1.5, 'pm10_weight': 1.3, 'no2_weight': 1.4,
        'o3_weight': 1.3, 'co_weight': 1.5, 'so2_weight': 1.2,
        'base_sensitivity': 1.4,
    },
    'asthmatic': {
        'label': 'Asthmatic',
        'pm25_weight': 1.8, 'pm10_weight': 1.6, 'no2_weight': 1.5,
        'o3_weight': 1.7, 'co_weight': 1.1, 'so2_weight': 1.6,
        'base_sensitivity': 1.7,
    },
    'cardiac': {
        'label': 'Heart/Cardiac Patient',
        'pm25_weight': 1.7, 'pm10_weight': 1.2, 'no2_weight': 1.6,
        'o3_weight': 1.2, 'co_weight': 1.8, 'so2_weight': 1.3,
        'base_sensitivity': 1.6,
    },
    'pregnant': {
        'label': 'Pregnant Woman',
        'pm25_weight': 1.5, 'pm10_weight': 1.3, 'no2_weight': 1.4,
        'o3_weight': 1.3, 'co_weight': 1.6, 'so2_weight': 1.4,
        'base_sensitivity': 1.5,
    },
    'copd': {
        'label': 'COPD Patient',
        'pm25_weight': 1.9, 'pm10_weight': 1.7, 'no2_weight': 1.6,
        'o3_weight': 1.8, 'co_weight': 1.3, 'so2_weight': 1.7,
        'base_sensitivity': 1.8,
    },
}


def calculate_hvi(pm25, pm10, no2, so2, co, o3, profile_key, weather=None):
    """
    Calculate the Dynamic Health Vulnerability Index (HVI).
    
    HVI = base_sensitivity × Σ(pollutant_normalized × profile_weight) × env_modifier
    
    Returns a score 0-500 with risk category.
    """
    profile = VULNERABILITY_PROFILES.get(profile_key, VULNERABILITY_PROFILES['general'])

    # Normalize pollutants against CPCB "Satisfactory" thresholds (upper limit)
    pm25_norm = pm25 / 60.0
    pm10_norm = pm10 / 100.0
    no2_norm = no2 / 80.0
    so2_norm = so2 / 80.0
    co_norm = co / 2.0   # mg/m³
    o3_norm = o3 / 100.0

    # Weighted vulnerability sum
    weighted_sum = (
        pm25_norm * profile['pm25_weight'] * 0.30 +   # PM2.5 highest health weight
        pm10_norm * profile['pm10_weight'] * 0.20 +
        no2_norm * profile['no2_weight'] * 0.15 +
        o3_norm * profile['o3_weight'] * 0.15 +
        co_norm * profile['co_weight'] * 0.10 +
        so2_norm * profile['so2_weight'] * 0.10
    )

    # Environmental modifier based on weather conditions
    env_modifier = 1.0
    if weather:
        temp = weather.get('temperature', 25)
        humidity = weather.get('humidity', 50)
        wind = weather.get('wind_speed', 3)

        # High temperature + high humidity worsens health impact
        if temp > 35:
            env_modifier += 0.15
        elif temp < 10:
            env_modifier += 0.10

        if humidity > 80:
            env_modifier += 0.10

        # Low wind = poor dispersion = worse exposure
        if wind < 1:
            env_modifier += 0.15
        elif wind < 2:
            env_modifier += 0.08

    # Final HVI score (0-500 scale)
    raw_score = weighted_sum * profile['base_sensitivity'] * env_modifier * 100
    hvi_score = min(500, max(0, round(raw_score, 1)))

    # Risk category
    if hvi_score <= 50:
        risk = {'level': 'Low Risk', 'color': '#00E400', 'severity': 1}
    elif hvi_score <= 100:
        risk = {'level': 'Moderate Risk', 'color': '#92D050', 'severity': 2}
    elif hvi_score <= 200:
        risk = {'level': 'High Risk', 'color': '#FFD700', 'severity': 3}
    elif hvi_score <= 300:
        risk = {'level': 'Very High Risk', 'color': '#FF4444', 'severity': 4}
    elif hvi_score <= 400:
        risk = {'level': 'Severe Risk', 'color': '#CC0000', 'severity': 5}
    else:
        risk = {'level': 'Emergency', 'color': '#7E0023', 'severity': 6}

    # Identify top risk pollutants for this profile
    pollutant_risks = [
        ('PM2.5', pm25_norm * profile['pm25_weight'], pm25, 'μg/m³'),
        ('PM10', pm10_norm * profile['pm10_weight'], pm10, 'μg/m³'),
        ('NO₂', no2_norm * profile['no2_weight'], no2, 'μg/m³'),
        ('O₃', o3_norm * profile['o3_weight'], o3, 'μg/m³'),
        ('CO', co_norm * profile['co_weight'], co, 'mg/m³'),
        ('SO₂', so2_norm * profile['so2_weight'], so2, 'μg/m³'),
    ]
    pollutant_risks.sort(key=lambda x: x[1], reverse=True)
    top_risk = pollutant_risks[0][0]

    return {
        'score': hvi_score,
        'risk_level': risk['level'],
        'risk_color': risk['color'],
        'severity': risk['severity'],
        'profile': profile['label'],
        'profile_key': profile_key,
        'top_risk_pollutant': top_risk,
        'env_modifier': round(env_modifier, 2),
        'pollutant_contributions': [
            {'name': p[0], 'risk_score': round(p[1] * 100, 1), 'value': round(p[2], 2), 'unit': p[3]}
            for p in pollutant_risks
        ]
    }


# ---------------------------------------------------------------------------
# Actionable Mitigation & Advisory Engine
# ---------------------------------------------------------------------------

def generate_actionable_advisories(aqi, pm25, pm10, o3, co, weather, profile_key,
                                   predictions=None, hvi_score=0):
    """
    Generate context-aware, actionable health recommendations based on:
    - Current AQI and pollutant levels
    - Whether conditions + time of day
    - User's demographic profile
    - Forecasted AQI trends
    """
    profile = VULNERABILITY_PROFILES.get(profile_key, VULNERABILITY_PROFILES['general'])
    advisories = []
    now = datetime.now()
    hour = now.hour
    temp = weather.get('temperature', 25) if weather else 25
    wind = weather.get('wind_speed', 3) if weather else 3
    humidity = weather.get('humidity', 50) if weather else 50

    # --- Mask Advisory ---
    if hvi_score > 150 or aqi > 200:
        advisories.append({
            'icon': '😷',
            'category': 'Protection',
            'priority': 'high',
            'title': 'Wear N95/FFP2 mask outdoors',
            'detail': f'Your HVI score ({hvi_score}) indicates significant health risk. Use an N95 or FFP2 mask for any outdoor exposure. Cloth masks are insufficient for PM2.5 filtration.',
        })
    elif hvi_score > 100 or aqi > 150:
        advisories.append({
            'icon': '😷',
            'category': 'Protection',
            'priority': 'medium',
            'title': 'Consider wearing a mask outdoors',
            'detail': f'As a {profile["label"]}, your vulnerability is elevated. Carry an N95 mask when stepping outside, especially near traffic.',
        })

    # --- Outdoor Activity Advisory ---
    is_exercise_hour = hour in [5, 6, 7, 17, 18, 19]
    if is_exercise_hour:
        if aqi > 150 or hvi_score > 150:
            advisories.append({
                'icon': '🏃',
                'category': 'Exercise',
                'priority': 'high',
                'title': 'Avoid outdoor exercise right now',
                'detail': f'AQI is {round(aqi)} during peak exercise hours. Shift workouts indoors or reschedule to early morning (5-6 AM) when pollution is typically lower.',
            })
        elif aqi > 100:
            advisories.append({
                'icon': '🏃',
                'category': 'Exercise',
                'priority': 'medium',
                'title': 'Reduce outdoor exercise intensity',
                'detail': f'Current AQI ({round(aqi)}) is moderate. Opt for light walking instead of jogging. Avoid exercising near roads or industrial areas.',
            })

    # --- Forecast-based spike warning ---
    if predictions and len(predictions) > 0:
        worst = max(predictions, key=lambda p: p.get('aqi_indian', 0))
        worst_aqi = worst.get('aqi_indian', 0)
        worst_time = worst.get('time_label', '')
        if worst_aqi > aqi + 30:
            advisories.append({
                'icon': '📈',
                'category': 'Forecast Alert',
                'priority': 'high',
                'title': f'AQI spike expected at {worst_time}',
                'detail': f'Forecast shows AQI rising to {round(worst_aqi)} at {worst_time} (currently {round(aqi)}). Complete outdoor tasks before the spike. Close windows and use air purifiers in advance.',
            })
        elif worst_aqi > aqi + 15:
            advisories.append({
                'icon': '📈',
                'category': 'Forecast Alert',
                'priority': 'medium',
                'title': f'Moderate AQI increase expected by {worst_time}',
                'detail': f'AQI may rise to {round(worst_aqi)}. Plan outdoor activities for the current lower-pollution window.',
            })

        # Check if conditions will improve
        best = min(predictions[:12], key=lambda p: p.get('aqi_indian', 999))
        best_aqi = best.get('aqi_indian', 999)
        best_time = best.get('time_label', '')
        if best_aqi < aqi - 20 and aqi > 100:
            advisories.append({
                'icon': '🌤️',
                'category': 'Opportunity',
                'priority': 'low',
                'title': f'Better air quality expected at {best_time}',
                'detail': f'AQI forecast to drop to {round(best_aqi)} at {best_time}. Schedule outdoor activities, walks, or errands for that window.',
            })

    # --- Indoor air quality advisory ---
    if aqi > 200 or hvi_score > 200:
        advisories.append({
            'icon': '🏠',
            'category': 'Indoor Safety',
            'priority': 'high',
            'title': 'Activate indoor air protection',
            'detail': 'Close all windows and doors. Run air purifiers on high. If no purifier, a wet cloth over fan intake helps trap particles. Avoid burning incense, candles, or cooking with high smoke.',
        })

    # --- Weather-specific advisories ---
    if wind < 1 and aqi > 100:
        advisories.append({
            'icon': '🌫️',
            'category': 'Weather',
            'priority': 'medium',
            'title': 'Stagnant air — pollutants trapped',
            'detail': f'Wind speed is only {wind} m/s. Without wind dispersion, pollution will accumulate. Minimize outdoor time until winds pick up.',
        })

    if temp > 35 and o3 > 100:
        advisories.append({
            'icon': '☀️',
            'category': 'Weather',
            'priority': 'medium',
            'title': 'High ozone due to heat',
            'detail': f'Temperature ({temp}°C) is driving ozone formation (O₃: {round(o3)} μg/m³). Avoid outdoor activity between 12-4 PM when ozone peaks.',
        })

    if humidity > 80 and pm25 > 60:
        advisories.append({
            'icon': '💧',
            'category': 'Weather',
            'priority': 'medium',
            'title': 'High humidity amplifying PM2.5 impact',
            'detail': f'Humidity ({humidity}%) causes particles to absorb water, increasing their effective size and lung deposition. Extra caution for respiratory sensitivity.',
        })

    # --- Profile-specific advisories ---
    if profile_key == 'child' and aqi > 100:
        advisories.append({
            'icon': '👶',
            'category': 'Child Safety',
            'priority': 'high',
            'title': 'Limit children\'s outdoor play',
            'detail': f'Children breathe faster and inhale more pollutants per body weight. Keep outdoor play under 30 minutes. Prefer indoor activities until AQI drops below 100.',
        })

    if profile_key == 'asthmatic' and (pm25 > 60 or o3 > 100):
        advisories.append({
            'icon': '🫁',
            'category': 'Asthma Management',
            'priority': 'high',
            'title': 'Keep rescue inhaler accessible',
            'detail': f'PM2.5 ({round(pm25)} μg/m³) and O₃ ({round(o3)} μg/m³) levels are triggers for asthma episodes. Pre-medicate if prescribed. Avoid areas with heavy traffic.',
        })

    if profile_key == 'cardiac' and (aqi > 150 or co > 2):
        advisories.append({
            'icon': '❤️',
            'category': 'Cardiac Safety',
            'priority': 'high',
            'title': 'Avoid physical exertion outdoors',
            'detail': f'CO levels ({round(co, 2)} mg/m³) and particulate pollution reduce blood oxygen. Avoid strenuous activity. Monitor for chest tightness or breathlessness.',
        })

    if profile_key == 'elderly' and aqi > 100:
        advisories.append({
            'icon': '🧓',
            'category': 'Elderly Care',
            'priority': 'medium',
            'title': 'Take precautions before going outside',
            'detail': 'Weakened immune response increases vulnerability. Wear a mask, limit exposure to 30 minutes, and stay hydrated. Avoid peak traffic hours.',
        })

    if profile_key == 'pregnant' and pm25 > 50:
        advisories.append({
            'icon': '🤰',
            'category': 'Prenatal Safety',
            'priority': 'high',
            'title': 'Stay indoors — PM2.5 elevated',
            'detail': f'PM2.5 at {round(pm25)} μg/m³ poses risks for fetal development. Stay indoors with filtered air. If you must go out, wear an N95 mask and keep exposure under 15 minutes.',
        })

    if profile_key == 'copd' and aqi > 100:
        advisories.append({
            'icon': '🫁',
            'category': 'COPD Management',
            'priority': 'high',
            'title': 'Strictly avoid outdoor exposure',
            'detail': f'AQI at {round(aqi)} significantly aggravates COPD. Stay indoors with air purification. Use prescribed bronchodilators preventively. Seek emergency care if symptoms worsen.',
        })

    # --- Commute Advisory ---
    if hour in [7, 8, 9, 17, 18, 19] and aqi > 100:
        advisories.append({
            'icon': '🚗',
            'category': 'Commute',
            'priority': 'medium',
            'title': 'Rush hour — keep car windows closed',
            'detail': 'Use recirculation mode in your vehicle AC. Avoid two-wheeler travel if possible. If cycling/walking, use back roads away from heavy traffic.',
        })

    # Sort by priority
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    advisories.sort(key=lambda a: priority_order.get(a['priority'], 3))

    return advisories


# ---------------------------------------------------------------------------
# AQICN Ground Sensor Integration
# ---------------------------------------------------------------------------

# US EPA AQI breakpoints for reverse-calculating concentrations from sub-indices
EPA_BREAKPOINTS = {
    'pm25': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 12.0, 35.4, 55.4, 150.4, 250.4, 350.4, 500.4],
        'unit': 'μg/m³'
    },
    'pm10': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 54, 154, 254, 354, 424, 504, 604],
        'unit': 'μg/m³'
    },
    'no2': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 53, 100, 360, 649, 1249, 1649, 2049],  # ppb
        'unit': 'μg/m³',
        'ppb_to_ugm3': 1.88  # NO2 conversion factor at STP
    },
    'o3': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 54, 70, 85, 105, 200, 404, 504],  # ppb (8-hr)
        'unit': 'μg/m³',
        'ppb_to_ugm3': 1.96  # O3 conversion factor at STP
    },
    'co': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 4.4, 9.4, 12.4, 15.4, 30.4, 40.4, 50.4],  # ppm
        'unit': 'mg/m³',
        'ppm_to_mgm3': 1.145  # CO conversion factor at STP
    },
    'so2': {
        'aqi':  [0, 50, 100, 150, 200, 300, 400, 500],
        'conc': [0, 35, 75, 185, 304, 604, 804, 1004],  # ppb
        'unit': 'μg/m³',
        'ppb_to_ugm3': 2.62  # SO2 conversion factor at STP
    }
}


def aqi_sub_to_concentration(pollutant, aqi_value):
    """Reverse-calculate concentration from US EPA AQI sub-index."""
    if pollutant not in EPA_BREAKPOINTS or aqi_value is None:
        return None

    bp = EPA_BREAKPOINTS[pollutant]
    aqi_bp = bp['aqi']
    conc_bp = bp['conc']

    # Clamp
    if aqi_value <= 0:
        return 0.0
    if aqi_value >= 500:
        return conc_bp[-1]

    # Find bracket
    for i in range(len(aqi_bp) - 1):
        if aqi_bp[i] <= aqi_value <= aqi_bp[i + 1]:
            aqi_lo, aqi_hi = aqi_bp[i], aqi_bp[i + 1]
            c_lo, c_hi = conc_bp[i], conc_bp[i + 1]
            conc = (aqi_value - aqi_lo) / (aqi_hi - aqi_lo) * (c_hi - c_lo) + c_lo

            # Convert ppb/ppm to μg/m³ or mg/m³
            if 'ppb_to_ugm3' in bp:
                conc *= bp['ppb_to_ugm3']
            elif 'ppm_to_mgm3' in bp:
                conc *= bp['ppm_to_mgm3']

            return round(conc, 2)

    return None


def _haversine(lat1, lon1, lat2, lon2):
    """Return distance in km between two lat/lon points."""
    import math
    R = 6371
    la1, lo1 = math.radians(lat1), math.radians(lon1)
    la2, lo2 = math.radians(lat2), math.radians(lon2)
    dlat, dlon = la2 - la1, lo2 - lo1
    a = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Multi-Station Spatial Modeling
# ---------------------------------------------------------------------------

def _fetch_nearby_stations(lat, lon, max_stations=5):
    """Fetch multiple nearby AQICN stations for spatial IDW modeling.
    Uses a wider bounding box (~33 km) to capture regional pollution transport.
    """
    if not AQICN_TOKEN:
        return []

    try:
        delta = 0.3  # ~33 km bounding box
        bounds_url = (
            f"https://api.waqi.info/v2/map/bounds/"
            f"?latlng={lat - delta},{lon - delta},{lat + delta},{lon + delta}"
            f"&networks=all&token={AQICN_TOKEN}"
        )
        resp = requests.get(bounds_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get('status') != 'ok' or not data.get('data'):
            return []

        stations = []
        for s in data['data']:
            slat = s.get('lat')
            slon = s.get('lon')
            aqi_val = s.get('aqi')
            station_name = s.get('station', {}).get('name', 'Unknown')

            if slat is None or slon is None:
                continue
            if aqi_val in (None, '-', ''):
                continue

            try:
                aqi_num = float(aqi_val)
            except (ValueError, TypeError):
                continue

            dist = _haversine(lat, lon, float(slat), float(slon))
            stations.append({
                'name': station_name,
                'lat': float(slat),
                'lon': float(slon),
                'distance_km': round(dist, 1),
                'aqi': aqi_num,
                'uid': s.get('uid')
            })

        stations.sort(key=lambda x: x['distance_km'])
        return stations[:max_stations]

    except Exception as e:
        print(f"Nearby stations fetch failed: {e}")
        return []


def spatial_idw_blend(stations, lat, lon, power=1):
    """Inverse Distance Weighting of nearby station AQI values.

    weight_i = 1 / distance_i^power
    blended_aqi = Σ(weight_i × aqi_i) / Σ(weight_i)

    Also returns neighbor_effect = Σ(weight_i × aqi_i) for spatial transport detection.
    """
    if not stations:
        return None, 0, []

    weights = []
    for s in stations:
        d = max(s['distance_km'], 0.1)  # avoid division by zero
        weights.append(1.0 / (d ** power))

    total_weight = sum(weights)
    blended_aqi = sum(w * s['aqi'] for w, s in zip(weights, stations)) / total_weight
    neighbor_effect = sum(w * s['aqi'] for w, s in zip(weights, stations))

    contributions = [
        {
            'station': s['name'],
            'distance_km': s['distance_km'],
            'aqi': s['aqi'],
            'weight': round(w / total_weight, 3)
        }
        for w, s in zip(weights, stations)
    ]

    return round(blended_aqi, 1), round(neighbor_effect, 2), contributions


# ---------------------------------------------------------------------------
# Wind Transport Helpers
# ---------------------------------------------------------------------------

def _compute_bearing(lat1, lon1, lat2, lon2):
    """Compute bearing (degrees) from point 1 to point 2."""
    import math
    la1, lo1 = math.radians(lat1), math.radians(lon1)
    la2, lo2 = math.radians(lat2), math.radians(lon2)
    dlon = lo2 - lo1
    x = math.sin(dlon) * math.cos(la2)
    y = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def _compute_wind_alignment(wind_dir, bearing):
    """Compute alignment between wind direction and station bearing.
    Returns value from -1 (opposite) to +1 (aligned = upwind).
    wind_dir: direction wind is coming FROM (degrees).
    bearing: direction from station to target location (degrees).
    """
    import math
    diff = abs(wind_dir - bearing)
    if diff > 180:
        diff = 360 - diff
    return math.cos(math.radians(diff))


# ---------------------------------------------------------------------------
# Spatial Pollutant Features (per-pollutant IDW + wind transport)
# ---------------------------------------------------------------------------

def fetch_spatial_pollutant_features(lat, lon, wind_dir=None, max_stations=5, radius_km=100):
    """Fetch nearby station per-pollutant data and compute spatial features
    using inverse distance weighting (IDW) with optional wind transport adjustment.

    Returns dict of spatial features for ML and blending.
    """
    if not AQICN_TOKEN:
        return {}

    try:
        delta = radius_km / 111.0  # ~111 km per degree latitude
        bounds_url = (
            f"https://api.waqi.info/v2/map/bounds/"
            f"?latlng={lat - delta},{lon - delta},{lat + delta},{lon + delta}"
            f"&networks=all&token={AQICN_TOKEN}"
        )
        resp = requests.get(bounds_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get('status') != 'ok' or not data.get('data'):
            return {}

        stations = []
        for s in data['data']:
            slat = s.get('lat')
            slon = s.get('lon')
            uid = s.get('uid')
            if slat is None or slon is None or uid is None:
                continue
            dist = _haversine(lat, lon, float(slat), float(slon))
            if dist > radius_km:
                continue
            stations.append({
                'uid': uid,
                'lat': float(slat),
                'lon': float(slon),
                'distance_km': dist,
                'name': s.get('station', {}).get('name', 'Unknown'),
            })

        stations.sort(key=lambda x: x['distance_km'])
        stations = stations[:max_stations]

        if not stations:
            return {}

        # Fetch per-pollutant data from each station
        pollutant_keys = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
        station_data = []

        for s in stations:
            try:
                url = f"https://api.waqi.info/feed/@{s['uid']}/?token={AQICN_TOKEN}"
                sresp = requests.get(url, timeout=8)
                if not sresp.ok:
                    continue
                feed = sresp.json()
                if feed.get('status') != 'ok':
                    continue

                iaqi = feed['data'].get('iaqi', {})
                pollutants = {}
                for pk in pollutant_keys:
                    sub_idx = iaqi.get(pk, {}).get('v')
                    if sub_idx is not None:
                        conc = aqi_sub_to_concentration(pk, sub_idx)
                        if conc is not None:
                            pollutants[pk] = conc

                if pollutants:
                    s['pollutants'] = pollutants
                    s['aqi'] = feed['data'].get('aqi', 0)
                    try:
                        s['aqi'] = float(s['aqi'])
                    except (ValueError, TypeError):
                        s['aqi'] = 0
                    station_data.append(s)
            except Exception:
                continue

        if not station_data:
            return {}

        # Compute IDW weights with optional wind transport adjustment
        features = {}
        weights = []
        for s in station_data:
            d = max(s['distance_km'], 0.1)
            w = 1.0 / d

            # Wind transport: stations in the upwind direction have more influence
            if wind_dir is not None:
                bearing = _compute_bearing(s['lat'], s['lon'], lat, lon)
                alignment = _compute_wind_alignment(wind_dir, bearing)
                if alignment > 0.7:
                    w *= 1.5   # upwind station — stronger influence
                elif alignment < -0.3:
                    w *= 0.7   # downwind station — weaker influence

            weights.append(w)

        total_weight = sum(weights)
        if total_weight == 0:
            return {}

        # Per-pollutant IDW weighted averages
        for pk in pollutant_keys:
            values = []
            w_list = []
            for s, w in zip(station_data, weights):
                if pk in s.get('pollutants', {}):
                    values.append(s['pollutants'][pk])
                    w_list.append(w)
            if values:
                w_total = sum(w_list)
                features[f'neighbor_{pk}_avg'] = round(
                    sum(v * w for v, w in zip(values, w_list)) / w_total, 2
                )

        # Weighted AQI
        aqi_values = [s.get('aqi', 0) for s in station_data]
        features['neighbor_aqi_weighted'] = round(
            sum(a * w for a, w in zip(aqi_values, weights)) / total_weight, 1
        )

        # Wind transport features for particulates
        if wind_dir is not None:
            for pk in ['pm25', 'pm10']:
                upwind_vals = []
                for s, w in zip(station_data, weights):
                    if pk in s.get('pollutants', {}):
                        bearing = _compute_bearing(s['lat'], s['lon'], lat, lon)
                        alignment = _compute_wind_alignment(wind_dir, bearing)
                        if alignment > 0.5:
                            upwind_vals.append(s['pollutants'][pk] * alignment)
                features[f'wind_transport_{pk}'] = round(np.mean(upwind_vals), 2) if upwind_vals else 0

        features['spatial_station_count'] = len(station_data)
        return features

    except Exception as e:
        print(f"Spatial pollutant feature fetch failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# Atmospheric Physics Corrections
# ---------------------------------------------------------------------------

def apply_atmospheric_adjustments(predicted_pollutants, weather):
    """Apply atmospheric physics corrections to predicted pollutant concentrations.

    Applied AFTER ML model predictions, BEFORE AQI calculation.

    Corrections:
      - Wind dispersion (strong wind disperses particulates)
      - Low wind stagnation (pollutants accumulate)
      - Rain washout (precipitation removes particulates)
      - Humidity particle growth (PM2.5 absorbs water vapor)
      - Thermal inversion detection (low wind + high pressure traps pollutants)
    """
    adjusted = dict(predicted_pollutants)

    wind_speed = weather.get('wind_speed', 3)
    humidity = weather.get('humidity', 50)
    pressure = weather.get('pressure', 1013)
    rain = weather.get('precipitation', 0)

    # Wind dispersion: strong wind disperses particulates
    if wind_speed > 6:
        adjusted['pm25'] = adjusted.get('pm25', 0) * 0.9
        adjusted['pm10'] = adjusted.get('pm10', 0) * 0.9

    # Low wind stagnation: pollutants accumulate
    if wind_speed < 2:
        adjusted['pm25'] = adjusted.get('pm25', 0) * 1.05
        adjusted['pm10'] = adjusted.get('pm10', 0) * 1.05

    # Rain washout: precipitation removes particulates
    if rain > 1:
        adjusted['pm25'] = adjusted.get('pm25', 0) * 0.8
        adjusted['pm10'] = adjusted.get('pm10', 0) * 0.85

    # Humidity particle growth: PM2.5 absorbs water vapor
    if humidity > 80:
        adjusted['pm25'] = adjusted.get('pm25', 0) * 1.1

    # Thermal inversion detection: low wind + high pressure traps pollutants
    if wind_speed < 2 and pressure > 1015:
        adjusted['pm25'] = adjusted.get('pm25', 0) * 1.08
        adjusted['pm10'] = adjusted.get('pm10', 0) * 1.08

    # Clamp to realistic ranges
    clamp_ranges = {
        'pm25': (0, 1000), 'pm10': (0, 1000),
        'no2': (0, 500), 'so2': (0, 2000),
        'co': (0, 100), 'o3': (0, 600),
    }
    for poll, (lo, hi) in clamp_ranges.items():
        if poll in adjusted:
            adjusted[poll] = max(lo, min(hi, adjusted[poll]))

    return adjusted


# ---------------------------------------------------------------------------
# Pollution Episode Detection
# ---------------------------------------------------------------------------

def detect_pollution_episodes(aqi_history, predictions):
    """Detect pollution spikes in recent history and forecast.

    Rules:
    - Rapid increase > 40 AQI in 6 hours → pollution episode alert
    - Forecast spike > 50 AQI above current → predicted spike warning
    - Sustained high (>300 for 6+ hours) → severe episode
    """
    episodes = []

    # Check recent history for rapid increase
    if len(aqi_history) >= 6:
        recent_increase = aqi_history[0] - aqi_history[5]
        if recent_increase > 40:
            episodes.append({
                'type': 'rapid_increase',
                'severity': 'high',
                'title': 'Pollution episode detected',
                'detail': f'AQI increased by {round(recent_increase)} in the last 6 hours. '
                           'Possible causes: dust storm, crop burning, or industrial activity.',
                'icon': '⚠️'
            })
        elif recent_increase > 25:
            episodes.append({
                'type': 'moderate_increase',
                'severity': 'medium',
                'title': 'Rising pollution trend detected',
                'detail': f'AQI increased by {round(recent_increase)} in the last 6 hours.',
                'icon': '📊'
            })

    # Check if currently in sustained severe episode
    if len(aqi_history) >= 6:
        recent_6h = aqi_history[:6]
        if all(a > 300 for a in recent_6h):
            episodes.append({
                'type': 'sustained_severe',
                'severity': 'high',
                'title': 'Sustained severe pollution episode',
                'detail': 'AQI has been above 300 for the last 6+ hours. '
                           'Stay indoors with air purifiers. Avoid all outdoor activity.',
                'icon': '🚨'
            })

    # Check forecast for predicted spikes
    if predictions and len(predictions) > 1:
        current_pred_aqi = predictions[0].get('aqi_indian', 0)
        max_pred = max(p.get('aqi_indian', 0) for p in predictions)
        if max_pred - current_pred_aqi > 50:
            peak = next(p for p in predictions if p.get('aqi_indian', 0) == max_pred)
            episodes.append({
                'type': 'predicted_spike',
                'severity': 'medium',
                'title': f'Pollution spike predicted at {peak.get("time_label", "")}',
                'detail': f'AQI forecast to rise to {round(max_pred)} '
                           f'(+{round(max_pred - current_pred_aqi)} from current). '
                           'Complete outdoor tasks before the spike.',
                'icon': '📈'
            })

    return episodes


def _fetch_nearest_station_uid(lat, lon):
    """Use AQICN map/bounds API to find the nearest station with valid AQI."""
    # Search within ~0.15 degrees (~17 km) bounding box
    delta = 0.15
    bounds_url = (
        f"https://api.waqi.info/v2/map/bounds/"
        f"?latlng={lat - delta},{lon - delta},{lat + delta},{lon + delta}"
        f"&networks=all&token={AQICN_TOKEN}"
    )
    resp = requests.get(bounds_url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get('status') != 'ok' or not data.get('data'):
        return None

    # Rank stations by distance, prefer those with valid AQI
    candidates = []
    for s in data['data']:
        slat = s.get('lat')
        slon = s.get('lon')
        aqi_val = s.get('aqi')
        uid = s.get('uid')
        if slat is None or slon is None or uid is None:
            continue
        dist = _haversine(lat, lon, float(slat), float(slon))
        has_aqi = aqi_val not in (None, '-', '')
        candidates.append((not has_aqi, dist, uid))  # sort: valid-AQI first, then distance

    if not candidates:
        return None

    candidates.sort()
    return candidates[0][2]  # uid of best station







def fetch_aqicn_data(lat, lon):
    """Fetch ground-sensor pollutant data from nearby AQICN stations.
    Uses IDW blending of multiple stations when available for higher accuracy.
    Falls back to single nearest station if needed."""
    if not AQICN_TOKEN:
        return None

    try:
        # Step 1: Find nearby stations within ~17 km
        delta = 0.15
        bounds_url = (
            f"https://api.waqi.info/v2/map/bounds/"
            f"?latlng={lat - delta},{lon - delta},{lat + delta},{lon + delta}"
            f"&networks=all&token={AQICN_TOKEN}"
        )
        resp = requests.get(bounds_url, timeout=10)
        resp.raise_for_status()
        bounds_data = resp.json()

        nearby_uids = []
        if bounds_data.get('status') == 'ok' and bounds_data.get('data'):
            for s in bounds_data['data']:
                slat = s.get('lat')
                slon = s.get('lon')
                uid = s.get('uid')
                aqi_val = s.get('aqi')
                if slat is None or slon is None or uid is None:
                    continue
                if aqi_val in (None, '-', ''):
                    continue
                dist = _haversine(lat, lon, float(slat), float(slon))
                nearby_uids.append({
                    'uid': uid,
                    'dist': dist,
                    'name': s.get('station', {}).get('name', 'Unknown'),
                    'lat': float(slat),
                    'lon': float(slon),
                })
            nearby_uids.sort(key=lambda x: x['dist'])

        # Step 2: Fetch full data from nearest station (primary)
        if nearby_uids:
            best = nearby_uids[0]
            url = f"https://api.waqi.info/feed/@{best['uid']}/?token={AQICN_TOKEN}"
        else:
            url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={AQICN_TOKEN}"

        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get('status') != 'ok':
            return None

        feed = data['data']
        iaqi = feed.get('iaqi', {})
        city_info = feed.get('city', {})
        station = city_info.get('name', 'Unknown Station')
        station_geo = city_info.get('geo', [None, None])
        overall_aqi = feed.get('aqi')

        # Calculate distance from user to station
        station_distance_km = None
        if station_geo and station_geo[0] is not None and station_geo[1] is not None:
            station_distance_km = round(
                _haversine(lat, lon, float(station_geo[0]), float(station_geo[1])), 1
            )

        # Reverse-calc concentrations from US EPA AQI sub-indices
        pollutant_map = {
            'pm25': 'PM2.5', 'pm10': 'PM10', 'no2': 'NO₂',
            'so2': 'SO₂', 'co': 'CO', 'o3': 'O₃'
        }

        pollutants = {}
        for api_key, display_name in pollutant_map.items():
            sub_index = iaqi.get(api_key, {}).get('v')
            if sub_index is not None:
                conc = aqi_sub_to_concentration(api_key, sub_index)
                if conc is not None:
                    unit = EPA_BREAKPOINTS[api_key]['unit']
                    pollutants[api_key] = {
                        'name': display_name,
                        'value': conc,
                        'unit': unit,
                        'aqi_sub_index': round(sub_index)
                    }

        return {
            'station': station,
            'station_lat': float(station_geo[0]) if station_geo and station_geo[0] else None,
            'station_lon': float(station_geo[1]) if station_geo and station_geo[1] else None,
            'station_distance_km': station_distance_km,
            'overall_aqi': int(overall_aqi) if overall_aqi else None,
            'pollutants': pollutants,
            'nearby_count': len(nearby_uids),
        }

    except Exception as e:
        print(f"AQICN fetch failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Per-Pollutant Forecasting Engine
# ---------------------------------------------------------------------------

def predict_pollutants_per_hour(current_pollutants, pollutant_history,
                                weather_current, weather_forecast,
                                timestamp, hours_ahead):
    """
    Predict individual pollutant concentrations for a future time step
    using trained per-pollutant models.

    Architecture:
      Past Pollutants + Weather → Future Pollutant Concentrations → AQI

    Args:
        current_pollutants: dict with pm25, pm10, no2, so2, co, o3
        pollutant_history: DataFrame with hourly pollutant values (recent history)
        weather_current: dict with temperature, humidity, wind_speed, pressure
        weather_forecast: dict with forecasted weather for this hour
        timestamp: datetime of the forecast target
        hours_ahead: how many hours into the future

    Returns:
        dict with predicted pollutant concentrations, or None if models unavailable
    """
    if not POLLUTANT_MODELS:
        return None

    pollutants = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']

    # Choose best available model for this horizon
    # Prefer exact match, fallback to nearest available horizon
    available_horizons = [1, 3, 6, 12, 24]

    # Find closest trained horizon
    best_horizon = min(available_horizons, key=lambda h: abs(h - hours_ahead))

    predicted = {}
    for poll in pollutants:
        model_key = f"{poll}_{best_horizon}h"

        if model_key not in POLLUTANT_MODELS:
            # Use current value as naive fallback for missing models
            predicted[poll] = current_pollutants.get(poll, 0)
            continue

        m = POLLUTANT_MODELS[model_key]
        feature_cols = POLLUTANT_FEATURE_COLS[model_key]

        # Build features for this prediction
        features = {}

        # Temporal features
        features['hour'] = timestamp.hour
        features['day_of_week'] = timestamp.weekday()
        features['month'] = timestamp.month
        features['is_weekend'] = 1 if timestamp.weekday() >= 5 else 0
        features['is_rush_hour'] = 1 if timestamp.hour in [7, 8, 9, 17, 18, 19] else 0
        features['hour_sin'] = np.sin(2 * np.pi * timestamp.hour / 24)
        features['hour_cos'] = np.cos(2 * np.pi * timestamp.hour / 24)
        features['day_sin'] = np.sin(2 * np.pi * timestamp.weekday() / 7)
        features['day_cos'] = np.cos(2 * np.pi * timestamp.weekday() / 7)
        features['month_sin'] = np.sin(2 * np.pi * timestamp.month / 12)
        features['month_cos'] = np.cos(2 * np.pi * timestamp.month / 12)

        # Pollutant lag features (using 30-day history)
        for p in pollutants:
            features[f'{p}_current'] = current_pollutants.get(p, 0) if f'{p}_current' in feature_cols else None
            if p in pollutant_history.columns:
                series = pollutant_history[p].values
                for lag in [1, 2, 3, 6, 12, 24, 48, 72, 168]:
                    col = f'{p}_lag_{lag}h'
                    if col in feature_cols:
                        # lag=k means k hours in the past: series[-1] is current, series[-(k+1)] is k hours ago
                        idx = min(lag, len(series) - 1)
                        features[col] = float(series[-(idx + 1)]) if idx < len(series) else current_pollutants.get(p, 0)

                # Rolling features (wider windows with 30-day data)
                for w in [6, 12, 24, 48, 168]:
                    window = series[-min(w, len(series)):]
                    if f'{p}_rolling_mean_{w}h' in feature_cols:
                        features[f'{p}_rolling_mean_{w}h'] = float(np.mean(window))
                    if f'{p}_rolling_std_{w}h' in feature_cols:
                        features[f'{p}_rolling_std_{w}h'] = float(np.std(window))

        # Cross-pollutant features
        pm10_val = current_pollutants.get('pm10', 1)
        if 'pm25_to_pm10_ratio' in feature_cols:
            features['pm25_to_pm10_ratio'] = current_pollutants.get('pm25', 0) / max(pm10_val, 0.1)

        # Weather features — use actual history when available
        wx = weather_forecast or weather_current
        for col in ['temperature', 'humidity', 'wind_speed', 'pressure']:
            cur_val = wx.get(col, weather_current.get(col, 0))
            # Some models use bare column name (= raw column from training CSV)
            if col in feature_cols:
                features[col] = cur_val
            # Other models use _current suffix (from build_weather_features)
            if f'{col}_current' in feature_cols:
                features[f'{col}_current'] = cur_val
            for lag in [3, 6, 12, 24]:
                if f'{col}_lag_{lag}h' in feature_cols:
                    # Try to get actual historical weather from pollutant_history
                    if hasattr(pollutant_history, 'columns') and col in pollutant_history.columns:
                        # lag=k means k hours ago: series[-(k+1)]
                        idx = min(lag, len(pollutant_history) - 1)
                        features[f'{col}_lag_{lag}h'] = float(pollutant_history[col].values[-(idx + 1)])
                    else:
                        features[f'{col}_lag_{lag}h'] = weather_current.get(col, 0)
            if f'{col}_change_6h' in feature_cols:
                lag_6h_val = features.get(f'{col}_lag_6h', weather_current.get(col, 0))
                features[f'{col}_change_6h'] = cur_val - lag_6h_val
            if f'{col}_change_24h' in feature_cols:
                lag_24h_val = features.get(f'{col}_lag_24h', weather_current.get(col, 0))
                features[f'{col}_change_24h'] = cur_val - lag_24h_val

        if 'wind_humidity_interaction' in feature_cols:
            features['wind_humidity_interaction'] = wx.get('wind_speed', 0) * wx.get('humidity', 0)
        if 'heat_index' in feature_cols:
            features['heat_index'] = wx.get('temperature', 25) + 0.5 * (wx.get('humidity', 50) - 50)
        if 'is_calm_wind' in feature_cols:
            features['is_calm_wind'] = 1 if wx.get('wind_speed', 0) < 1 else 0

        # Build feature vector in correct order
        feature_vector = pd.Series(features).reindex(feature_cols, fill_value=0).values.astype(float)

        try:
            pred = float(m.predict(feature_vector.reshape(1, -1))[0])
            if POLLUTANT_LOG_TRANSFORM.get(model_key, False):
                pred = float(np.expm1(pred))
            predicted[poll] = max(0, pred)  # concentrations can't be negative
        except Exception:
            predicted[poll] = current_pollutants.get(poll, 0)

    return predicted


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.route('/api/current-aqi', methods=['GET'])
def current_aqi():
    """Fetch current AQI and pollutant data for given coordinates."""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon are required'}), 400

    try:
        # --- GROUND STATION DATA (MEASURED, NOT PREDICTED) ---
        # Priority 1: AQICN (WAQI) — aggregated global station data
        # Fallback: OWM satellite estimate
        aqicn = fetch_aqicn_data(lat, lon)
        data_source = 'satellite_estimate'
        station_name = None
        station_distance_km = None

        # Always fetch OWM weather (not for pollutants, just weather data)
        # OWM pollutants are satellite-derived estimates, NOT ground measurements
        air_url = "http://api.openweathermap.org/data/2.5/air_pollution"
        air_resp = requests.get(air_url, params={'lat': lat, 'lon': lon, 'appid': API_KEY}, timeout=10)
        air_resp.raise_for_status()
        air_data = air_resp.json()

        components = air_data['list'][0]['components']
        owm_pm25 = components.get('pm2_5', 0)
        owm_pm10 = components.get('pm10', 0)
        owm_no2 = components.get('no2', 0)
        owm_so2 = components.get('so2', 0)
        owm_co = components.get('co', 0) / 1000
        owm_o3 = components.get('o3', 0)

        # PRIORITY 1: AQICN aggregated ground station data
        # FALLBACK: OWM satellite estimate (clearly labeled)
        if aqicn and aqicn.get('pollutants'):
            ap = aqicn['pollutants']
            pm25 = ap.get('pm25', {}).get('value', owm_pm25)
            pm10 = ap.get('pm10', {}).get('value', owm_pm10)
            no2 = ap.get('no2', {}).get('value', owm_no2)
            so2 = ap.get('so2', {}).get('value', owm_so2)
            co = ap.get('co', {}).get('value', owm_co)
            o3 = ap.get('o3', {}).get('value', owm_o3)
            data_source = 'aqicn_ground_station'
            station_name = aqicn.get('station')
            station_distance_km = aqicn.get('station_distance_km')
        else:
            # FALLBACK: satellite estimate — apply correction for known underreporting
            pm25 = owm_pm25 * SATELLITE_CORRECTION['pm25']
            pm10 = owm_pm10 * SATELLITE_CORRECTION['pm10']
            no2  = owm_no2  * SATELLITE_CORRECTION['no2']
            so2  = owm_so2  * SATELLITE_CORRECTION['so2']
            co   = owm_co   * SATELLITE_CORRECTION['co']
            o3   = owm_o3   * SATELLITE_CORRECTION['o3']
            data_source = 'satellite_estimate'

        # Calculate AQI from the selected pollutant values
        aqi_indian, dominant_indian = calculate_indian_aqi_value(pm25, pm10, no2, so2, co, o3)
        aqi_us, dominant_us = calculate_us_epa_aqi(pm25, pm10, no2, so2, co, o3)
        category_indian = get_aqi_category(aqi_indian)
        category_us = get_us_aqi_category(aqi_us)

        # Build pollutant details
        pollutants = []
        for name, value, unit in [
            ('PM2.5', pm25, 'μg/m³'), ('PM10', pm10, 'μg/m³'),
            ('NO₂', no2, 'μg/m³'), ('SO₂', so2, 'μg/m³'),
            ('CO', co, 'mg/m³'), ('O₃', o3, 'μg/m³')
        ]:
            key = name.replace('₂', '2').replace('₃', '3')
            lvl = get_pollutant_level(key, value)
            pollutants.append({
                'name': name, 'value': round(value, 2), 'unit': unit,
                'level': lvl['level'], 'color': lvl['color']
            })

        # Fetch weather data
        weather_url = "http://api.openweathermap.org/data/2.5/weather"
        weather_resp = requests.get(weather_url, params={'lat': lat, 'lon': lon, 'appid': API_KEY, 'units': 'metric'}, timeout=10)
        weather_data = {
            'temperature': 0, 'humidity': 0, 'pressure': 0, 'description': '',
            'wind_speed': 0, 'wind_gust': 0, 'wind_deg': 0, 'visibility': 10,
            'cloud_cover': 0, 'precipitation': 0, 'uv_index': 0
        }
        
        if weather_resp.ok:
            w = weather_resp.json()
            weather_data.update({
                'temperature': w['main']['temp'],
                'humidity': w['main']['humidity'],
                'pressure': w['main']['pressure'],
                'description': w['weather'][0]['description'] if w.get('weather') else '',
                'wind_speed': w.get('wind', {}).get('speed', 0),
                'wind_gust': w.get('wind', {}).get('gust', 0),
                'wind_deg': w.get('wind', {}).get('deg', 0),
                'visibility': w.get('visibility', 10000) / 1000,
                'cloud_cover': w.get('clouds', {}).get('all', 0),
                'precipitation': w.get('rain', {}).get('1h', 0) or w.get('snow', {}).get('1h', 0)
            })
            
            try:
                uv_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=uv_index"
                uv_resp = requests.get(uv_url, timeout=5)
                if uv_resp.ok:
                    weather_data['uv_index'] = uv_resp.json().get('current', {}).get('uv_index', 0)
            except Exception as e:
                print(f"Failed to fetch UV Index from Open-Meteo: {e}")

        response = {
            'aqi_indian': aqi_indian,
            'aqi_us': aqi_us,
            'category_indian': category_indian['category'],
            'color_indian': category_indian['color'],
            'level_indian': category_indian['level'],
            'category_us': category_us['category'],
            'color_us': category_us['color'],
            'level_us': category_us['level'],
            'dominant_pollutant_indian': dominant_indian,
            'dominant_pollutant_us': dominant_us,
            'pollutants': pollutants,
            'weather': weather_data,
            'health_advisory': get_health_advisory(aqi_indian),
            'timestamp': datetime.now().isoformat(),
            'location': {'lat': lat, 'lon': lon},
            'data_source': data_source,
        }
        if station_name:
            response['station'] = station_name
        if station_distance_km is not None:
            response['station_distance_km'] = station_distance_km

        # Log data source for debugging
        print(f"[AQI] lat={lat}, lon={lon} | source={data_source} | station={station_name} | dist={station_distance_km}km | AQI_IN={aqi_indian} AQI_US={aqi_us}")

        return jsonify(response)

    except requests.RequestException as e:
        return jsonify({'error': f'Failed to fetch data: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/predict', methods=['GET'])
def predict():
    """
    Forecast AQI for the next N hours.

    ARCHITECTURE:
      1. Get CURRENT pollutant measurements from ground stations (MEASURED)
      2. Get historical pollutant data for lag features
      3. For each future hour:
         a. Predict each pollutant separately (PM2.5, PM10, NO2, SO2, CO, O3)
         b. Apply atmospheric physics corrections
         c. Compute AQI from corrected pollutant concentrations
      4. ONLY future AQI is predicted — current AQI is always measured
    """
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    hours = request.args.get('hours', default=6, type=int)

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon are required'}), 400
    if hours not in [3, 6, 12, 24, 48]:
        return jsonify({'error': 'hours must be one of: 3, 6, 12, 24, 48'}), 400

    try:
        now = datetime.now()

        # ================================================================
        # STEP 1: Get CURRENT pollutant measurements from ground station
        # Priority 1: AQICN — aggregated global station data
        # Fallback: OWM satellite estimate
        # ================================================================
        aqicn_data = fetch_aqicn_data(lat, lon)
        ground_station_source = False
        predict_data_source = 'satellite_estimate'

        if aqicn_data and aqicn_data.get('pollutants'):
            ap = aqicn_data['pollutants']
            current_pollutants = {
                'pm25': ap.get('pm25', {}).get('value', 0),
                'pm10': ap.get('pm10', {}).get('value', 0),
                'no2': ap.get('no2', {}).get('value', 0),
                'so2': ap.get('so2', {}).get('value', 0),
                'co': ap.get('co', {}).get('value', 0),
                'o3': ap.get('o3', {}).get('value', 0),
            }
            ground_station_source = True
            predict_data_source = 'aqicn_ground_station'
        else:
            # Fallback: OWM satellite — apply correction for known underreporting
            air_url = "http://api.openweathermap.org/data/2.5/air_pollution"
            air_resp = requests.get(air_url, params={'lat': lat, 'lon': lon, 'appid': API_KEY}, timeout=10)
            air_resp.raise_for_status()
            c_live = air_resp.json()['list'][0]['components']
            current_pollutants = {
                'pm25': c_live.get('pm2_5', 0) * SATELLITE_CORRECTION['pm25'],
                'pm10': c_live.get('pm10', 0) * SATELLITE_CORRECTION['pm10'],
                'no2': c_live.get('no2', 0) * SATELLITE_CORRECTION['no2'],
                'so2': c_live.get('so2', 0) * SATELLITE_CORRECTION['so2'],
                'co': (c_live.get('co', 0) / 1000.0) * SATELLITE_CORRECTION['co'],
                'o3': c_live.get('o3', 0) * SATELLITE_CORRECTION['o3'],
            }

        # Current AQI from MEASURED pollutant concentrations (not predicted)
        anchor_aqi, _ = calculate_indian_aqi_value(
            current_pollutants['pm25'], current_pollutants['pm10'],
            current_pollutants['no2'], current_pollutants['so2'],
            current_pollutants['co'], current_pollutants['o3']
        )
        anchor_aqi = float(anchor_aqi)

        current_aqi_us, _ = calculate_us_epa_aqi(
            current_pollutants['pm25'], current_pollutants['pm10'],
            current_pollutants['no2'], current_pollutants['so2'],
            current_pollutants['co'], current_pollutants['o3']
        )
        ratio = current_aqi_us / anchor_aqi if anchor_aqi > 0 else 0.7

        # ================================================================
        # STEP 2: Get 30-day hourly pollutant + weather history
        #         Source: Open-Meteo Air Quality API (free, reliable)
        #         Calibrated with AQICN ground station measurements
        # ================================================================
        aq_hist_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        aq_hist_resp = requests.get(aq_hist_url, params={
            'latitude': lat, 'longitude': lon,
            'hourly': 'pm10,pm2_5,nitrogen_dioxide,sulphur_dioxide,ozone,carbon_monoxide',
            'past_days': 30,
            'forecast_days': 0,
        }, timeout=20)
        aq_hist_resp.raise_for_status()
        aq_hist_data = aq_hist_resp.json()

        aq_h = aq_hist_data['hourly']
        records = []
        for i, t in enumerate(aq_h['time']):
            pm25_v = aq_h['pm2_5'][i]
            pm10_v = aq_h['pm10'][i]
            no2_v = aq_h['nitrogen_dioxide'][i]
            so2_v = aq_h['sulphur_dioxide'][i]
            o3_v = aq_h['ozone'][i]
            co_v = aq_h['carbon_monoxide'][i]
            records.append({
                'datetime': datetime.fromisoformat(t),
                'pm25': pm25_v if pm25_v is not None else 0,
                'pm10': pm10_v if pm10_v is not None else 0,
                'no2': no2_v if no2_v is not None else 0,
                'so2': so2_v if so2_v is not None else 0,
                'co': (co_v / 1000.0) if co_v is not None else 0,  # µg/m³ → mg/m³
                'o3': o3_v if o3_v is not None else 0,
            })

        hist_df = pd.DataFrame(records).sort_values('datetime').reset_index(drop=True)

        # Keep raw Open-Meteo history for per-pollutant models
        # (they are trained on raw Open-Meteo data — no domain shift)
        raw_hist_df = hist_df.copy()

        # Calibration factors: reference_current / Open-Meteo_current
        # Ground station: AQICN / Open-Meteo (high confidence)
        # Satellite: OWM / Open-Meteo (moderate — ensures forecast consistency)
        poll_cal_factors = {}
        if len(hist_df) > 0:
            om_latest = raw_hist_df.iloc[-1]  # Raw Open-Meteo latest
            for poll in ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']:
                model_val = float(om_latest[poll])
                ref_val = current_pollutants[poll]
                if model_val > 0 and ref_val > 0:
                    max_cf = 4.0 if ground_station_source else 2.5
                    cal_factor = max(0.3, min(max_cf, ref_val / model_val))
                    poll_cal_factors[poll] = cal_factor
            # Only calibrate legacy hist_df with ground-truth data
            if ground_station_source:
                for poll, cf in poll_cal_factors.items():
                    hist_df[poll] = hist_df[poll] * cf

        # For per-pollutant model features, use Open-Meteo latest when no ground
        # station — avoids domain mismatch between OWM current and Open-Meteo lags
        if ground_station_source:
            model_pollutants = current_pollutants
        elif len(raw_hist_df) > 0:
            om = raw_hist_df.iloc[-1]
            model_pollutants = {p: float(om[p]) for p in ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']}
        else:
            model_pollutants = current_pollutants

        # Calculate AQI history
        hist_df['AQI_Indian'] = hist_df.apply(
            lambda r: calculate_indian_aqi_value(
                r['pm25'], r['pm10'], r['no2'], r['so2'], r['co'], r['o3']
            )[0], axis=1
        )

        if len(hist_df) < 48:
            return jsonify({'error': f'Insufficient historical data ({len(hist_df)} points)'}), 422

        aqi_history = list(hist_df['AQI_Indian'].values[-48:][::-1])
        aqi_history[0] = anchor_aqi  # Override with measured current

        # ================================================================
        # STEP 3: Fetch weather (30-day history + 48h forecast)
        #         Source: Open-Meteo Weather API (hourly resolution)
        # ================================================================
        forecast_days = min(max(2, (hours // 24) + 1), 7)
        try:
            wx_resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    'latitude': lat, 'longitude': lon,
                    'hourly': 'temperature_2m,relative_humidity_2m,wind_speed_10m,surface_pressure,wind_direction_10m,precipitation',
                    'past_days': 30,
                    'forecast_days': forecast_days,
                }, timeout=15
            )
            wx_resp.raise_for_status()
            wx_data = wx_resp.json()['hourly']

            # Build weather history DataFrame aligned with pollutant history
            wx_records = []
            _n = len(wx_data['time'])
            for i, t in enumerate(wx_data['time']):
                wx_records.append({
                    'datetime': datetime.fromisoformat(t),
                    'temperature': wx_data['temperature_2m'][i] or 25,
                    'humidity': wx_data['relative_humidity_2m'][i] or 50,
                    'wind_speed': wx_data['wind_speed_10m'][i] or 0,
                    'pressure': wx_data['surface_pressure'][i] or 1013,
                    'wind_deg': wx_data.get('wind_direction_10m', [None]*_n)[i],
                    'precipitation': (wx_data.get('precipitation', [0]*_n)[i]) or 0,
                })
            wx_df = pd.DataFrame(wx_records)

            # Find current weather from the closest record to now
            wx_df['_offset'] = (wx_df['datetime'] - now).abs()
            nearest_idx = wx_df['_offset'].idxmin()
            base_temp = float(wx_df.loc[nearest_idx, 'temperature'])
            base_humidity = float(wx_df.loc[nearest_idx, 'humidity'])
            base_wind = float(wx_df.loc[nearest_idx, 'wind_speed'])
            base_pressure = float(wx_df.loc[nearest_idx, 'pressure'])
            _wd_val = wx_df.loc[nearest_idx, 'wind_deg']
            base_wind_deg = float(_wd_val) if pd.notna(_wd_val) else None
            wx_df = wx_df.drop(columns=['_offset'])

            # Build hourly weather forecast lookup
            hourly_weather = {}
            for h in range(0, hours + 1):
                target_time = now + timedelta(hours=h)
                diffs = (wx_df['datetime'] - target_time).abs()
                idx = diffs.idxmin()
                row = wx_df.iloc[idx]
                _rwd = row.get('wind_deg')
                hourly_weather[h] = {
                    'temp': float(row['temperature']),
                    'humidity': float(row['humidity']),
                    'wind': float(row['wind_speed']),
                    'pressure': float(row['pressure']),
                    'wind_deg': float(_rwd) if pd.notna(_rwd) else None,
                    'precipitation': float(row.get('precipitation', 0)),
                }

            # Merge weather into pollutant history for richer features
            if len(hist_df) > 0 and len(wx_df) > 0:
                hist_df['datetime'] = pd.to_datetime(hist_df['datetime'])
                wx_df['datetime'] = pd.to_datetime(wx_df['datetime'])
                hist_df = pd.merge_asof(
                    hist_df.sort_values('datetime'),
                    wx_df.sort_values('datetime'),
                    on='datetime', direction='nearest', tolerance=pd.Timedelta('2h')
                )
                for col in ['temperature', 'humidity', 'wind_speed', 'pressure']:
                    if col in hist_df.columns:
                        hist_df[col] = hist_df[col].ffill().bfill().fillna(
                            {'temperature': 25, 'humidity': 50, 'wind_speed': 2, 'pressure': 1013}[col]
                        )

                # Also add weather to raw_hist_df so per-pollutant models get correct
                # historical weather lag features (raw_hist_df has raw/uncalibrated pollutants)
                raw_hist_df['datetime'] = pd.to_datetime(raw_hist_df['datetime'])
                raw_hist_df = pd.merge_asof(
                    raw_hist_df.sort_values('datetime'),
                    wx_df.sort_values('datetime'),
                    on='datetime', direction='nearest', tolerance=pd.Timedelta('2h')
                )
                for col in ['temperature', 'humidity', 'wind_speed', 'pressure']:
                    if col in raw_hist_df.columns:
                        raw_hist_df[col] = raw_hist_df[col].ffill().bfill().fillna(
                            {'temperature': 25, 'humidity': 50, 'wind_speed': 2, 'pressure': 1013}[col]
                        )

        except Exception as e:
            print(f"Open-Meteo weather fetch failed, falling back to OWM: {e}")
            base_temp, base_humidity, base_wind, base_pressure = 25, 60, 3, 1013
            base_wind_deg = None
            hourly_weather = {}
            # Fallback: OWM current weather
            try:
                w_resp = requests.get(
                    "http://api.openweathermap.org/data/2.5/weather",
                    params={'lat': lat, 'lon': lon, 'appid': API_KEY, 'units': 'metric'}, timeout=10
                )
                if w_resp.ok:
                    w = w_resp.json()
                    base_temp = w['main']['temp']
                    base_humidity = w['main']['humidity']
                    base_wind = w['wind']['speed']
                    base_pressure = w['main']['pressure']
            except Exception:
                pass

        weather_current = {
            'temperature': base_temp, 'humidity': base_humidity,
            'wind_speed': base_wind, 'pressure': base_pressure,
            'wind_deg': base_wind_deg,
        }

        default_wx = {'temp': base_temp, 'humidity': base_humidity,
                      'wind': base_wind, 'pressure': base_pressure,
                      'wind_deg': base_wind_deg, 'precipitation': 0}

        # Multi-station spatial modeling
        nearby_stations = _fetch_nearby_stations(lat, lon, max_stations=5)
        spatial_aqi, neighbor_effect, station_contributions = spatial_idw_blend(
            nearby_stations, lat, lon
        )

        # Confidence interval base
        rolling_std_24h = float(np.std(aqi_history[:min(24, len(aqi_history))]))
        uncertainty_base = rolling_std_24h * 0.8

        # ================================================================
        # STEP 4: FORECAST — Per-pollutant prediction → AQI
        # ================================================================
        # Architecture:
        #   For each future hour:
        #     1. Predict PM2.5(t+h), PM10(t+h), NO2(t+h), SO2(t+h), CO(t+h), O3(t+h)
        #     2. Apply atmospheric physics corrections
        #     3. Compute AQI from corrected pollutant concentrations
        # ================================================================

        if not POLLUTANT_MODELS:
            return jsonify({'error': 'Pollutant models not loaded. Train models first.'}), 503

        # Fetch spatial pollution features from nearby monitoring stations
        wind_dir = weather_current.get('wind_deg')
        spatial_pollutant_features = fetch_spatial_pollutant_features(
            lat, lon, wind_dir=wind_dir
        )

        # ================================================================
        # Generate hourly predictions
        # ================================================================
        predictions = []
        for hour in range(1, hours + 1):
            pt = now + timedelta(hours=hour)
            wx = hourly_weather.get(hour, default_wx)

            wx_forecast = {
                'temperature': wx['temp'], 'humidity': wx['humidity'],
                'wind_speed': wx['wind'], 'pressure': wx['pressure'],
                'precipitation': wx.get('precipitation', 0),
            }

            # Predict each pollutant concentration for this hour
            predicted_poll = predict_pollutants_per_hour(
                model_pollutants, raw_hist_df,
                weather_current, wx_forecast, pt, hour
            )

            if predicted_poll:
                # Scale raw Open-Meteo predictions to reference space
                # (ground station when available, OWM satellite otherwise)
                for _p, _cf in poll_cal_factors.items():
                    if _p in predicted_poll:
                        predicted_poll[_p] = max(0.0, predicted_poll[_p] * _cf)

                # Apply atmospheric physics corrections
                predicted_poll = apply_atmospheric_adjustments(predicted_poll, wx_forecast)

                # Compute AQI from corrected predicted concentrations
                predicted_indian, dominant_indian = calculate_indian_aqi_value(
                    predicted_poll['pm25'], predicted_poll['pm10'],
                    predicted_poll['no2'], predicted_poll['so2'],
                    predicted_poll['co'], predicted_poll['o3']
                )
                predicted_us, dominant_us = calculate_us_epa_aqi(
                    predicted_poll['pm25'], predicted_poll['pm10'],
                    predicted_poll['no2'], predicted_poll['so2'],
                    predicted_poll['co'], predicted_poll['o3']
                )
            else:
                # Fallback: use current values if prediction fails
                predicted_poll = dict(current_pollutants)
                predicted_indian = anchor_aqi
                predicted_us = current_aqi_us
                dominant_indian = 'PM2.5'
                dominant_us = 'PM2.5'

            predicted_indian = max(1.0, min(500.0, predicted_indian))
            predicted_us = max(1.0, min(500.0, predicted_us))

            # Confidence interval
            uncertainty = uncertainty_base * (1.0 + 0.04 * hour)
            aqi_lower = max(1.0, round(predicted_indian - uncertainty, 1))
            aqi_upper = min(500.0, round(predicted_indian + uncertainty, 1))

            cat_indian = get_aqi_category(predicted_indian)
            cat_us = get_us_aqi_category(predicted_us)

            predictions.append({
                'hour': hour,
                'time': pt.strftime('%Y-%m-%d %H:%M'),
                'time_label': pt.strftime('%I:%M %p'),
                'date_label': pt.strftime('%b %d'),
                'pm25': round(predicted_poll.get('pm25', 0), 2),
                'pm10': round(predicted_poll.get('pm10', 0), 2),
                'no2': round(predicted_poll.get('no2', 0), 2),
                'so2': round(predicted_poll.get('so2', 0), 2),
                'co': round(predicted_poll.get('co', 0), 3),
                'o3': round(predicted_poll.get('o3', 0), 2),
                'aqi_indian': round(predicted_indian, 1),
                'aqi_us': round(predicted_us, 1),
                'dominant_pollutant': dominant_indian,
                'aqi_indian_lower': aqi_lower,
                'aqi_indian_upper': aqi_upper,
                'aqi_us_lower': round(max(1.0, aqi_lower * ratio), 1),
                'aqi_us_upper': round(min(500.0, aqi_upper * ratio), 1),
                'uncertainty': round(uncertainty, 1),
                'category_indian': cat_indian['category'],
                'color_indian': cat_indian['color'],
                'category_us': cat_us['category'],
                'color_us': cat_us['color'],
            })

        # Trend analysis
        if predictions:
            first_aqi = anchor_aqi
            last_aqi = predictions[-1]['aqi_indian']
            avg_change = (last_aqi - first_aqi) / hours
            if avg_change > 5: trend = 'rising_fast'
            elif avg_change > 1: trend = 'rising'
            elif avg_change < -5: trend = 'falling_fast'
            elif avg_change < -1: trend = 'falling'
            else: trend = 'stable'
        else:
            trend = 'stable'
            avg_change = 0

        episodes = detect_pollution_episodes(aqi_history, predictions)

        return jsonify({
            'predictions': predictions,
            'current_aqi_indian': anchor_aqi,
            'current_aqi_us': current_aqi_us,
            'trend': trend,
            'avg_change_per_hour': round(avg_change, 2),
            'hours': hours,
            'model': 'Per-Pollutant XGBoost → Atmospheric Corrections → AQI',
            'data_source': predict_data_source,
            'timestamp': datetime.now().isoformat(),
            'confidence': {
                'base_uncertainty': round(uncertainty_base, 1),
                'method': 'rolling_std_24h × 0.8, scaled by forecast horizon'
            },
            'spatial_model': {
                'stations_used': len(nearby_stations),
                'blended_aqi': spatial_aqi,
                'neighbor_effect': neighbor_effect,
                'contributions': station_contributions[:3],
                'spatial_pollutant_features': spatial_pollutant_features,
            } if nearby_stations else None,
            'episodes': episodes
        })

    except requests.RequestException as e:
        return jsonify({'error': f'API request failed: {str(e)}'}), 502
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Prediction error: {str(e)}'}), 500


@app.route('/api/geocode', methods=['GET'])
def geocode():
    """Convert city name to lat/lon coordinates."""
    city = request.args.get('city', '').strip()
    if not city:
        return jsonify({'error': 'city parameter is required'}), 400

    try:
        geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        resp = requests.get(geo_url, params={'q': city, 'limit': 5, 'appid': API_KEY}, timeout=10)
        resp.raise_for_status()
        results = resp.json()

        if not results:
            return jsonify({'error': f'City "{city}" not found'}), 404

        locations = []
        for r in results:
            locations.append({
                'name': r.get('name', ''),
                'state': r.get('state', ''),
                'country': r.get('country', ''),
                'lat': r['lat'],
                'lon': r['lon'],
                'display_name': f"{r.get('name', '')}, {r.get('state', '')}, {r.get('country', '')}".strip(', ')
            })

        return jsonify({'results': locations})

    except requests.RequestException as e:
        return jsonify({'error': f'Geocoding failed: {str(e)}'}), 502


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'pollutant_models_loaded': len(POLLUTANT_MODELS),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/hvi', methods=['GET'])
def hvi_endpoint():
    """Calculate Health Vulnerability Index for a user profile at given location."""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    profile = request.args.get('profile', default='general')

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon are required'}), 400

    valid_profiles = list(VULNERABILITY_PROFILES.keys())
    if profile not in valid_profiles:
        return jsonify({'error': f'Invalid profile. Choose from: {valid_profiles}'}), 400

    try:
        # --- GROUND STATION DATA for HVI (measured, not predicted) ---
        pm25 = pm10 = no2 = so2 = co = o3 = 0
        data_source = 'satellite_estimate'

        aqicn_data = fetch_aqicn_data(lat, lon)
        if aqicn_data and aqicn_data.get('pollutants'):
            ap = aqicn_data['pollutants']
            pm25 = ap.get('pm25', {}).get('value', 0)
            pm10 = ap.get('pm10', {}).get('value', 0)
            no2 = ap.get('no2', {}).get('value', 0)
            so2 = ap.get('so2', {}).get('value', 0)
            co = ap.get('co', {}).get('value', 0)
            o3 = ap.get('o3', {}).get('value', 0)
            data_source = 'aqicn_ground_station'

        # Fallback to OWM satellite if ground station unavailable
        if data_source == 'satellite_estimate':
            air_url = "http://api.openweathermap.org/data/2.5/air_pollution"
            air_resp = requests.get(air_url, params={'lat': lat, 'lon': lon, 'appid': API_KEY}, timeout=10)
            air_resp.raise_for_status()
            components = air_resp.json()['list'][0]['components']
            pm25 = components.get('pm2_5', 0)
            pm10 = components.get('pm10', 0)
            no2 = components.get('no2', 0)
            so2 = components.get('so2', 0)
            co = components.get('co', 0) / 1000.0
            o3 = components.get('o3', 0)

        # Weather data
        weather_data = {}
        try:
            w_resp = requests.get("http://api.openweathermap.org/data/2.5/weather",
                                  params={'lat': lat, 'lon': lon, 'appid': API_KEY, 'units': 'metric'}, timeout=10)
            if w_resp.ok:
                w = w_resp.json()
                weather_data = {
                    'temperature': w['main']['temp'],
                    'humidity': w['main']['humidity'],
                    'wind_speed': w.get('wind', {}).get('speed', 0),
                    'pressure': w['main']['pressure'],
                }
        except Exception:
            pass

        # Calculate both Indian and US AQI from the same pollutant data
        aqi_indian, _ = calculate_indian_aqi_value(pm25, pm10, no2, so2, co, o3)
        aqi_us, _ = calculate_us_epa_aqi(pm25, pm10, no2, so2, co, o3)

        # Calculate HVI
        hvi_result = calculate_hvi(pm25, pm10, no2, so2, co, o3, profile, weather_data)

        # Generate advisories — get predictions if available
        predictions = []
        try:
            # Quick 12-hour prediction for advisory context
            predict_resp = requests.get(f"http://127.0.0.1:5001/api/predict",
                                        params={'lat': lat, 'lon': lon, 'hours': 12}, timeout=30)
            if predict_resp.ok:
                predictions = predict_resp.json().get('predictions', [])
        except Exception:
            pass

        advisories = generate_actionable_advisories(
            aqi=aqi_indian, pm25=pm25, pm10=pm10, o3=o3, co=co,
            weather=weather_data, profile_key=profile,
            predictions=predictions, hvi_score=hvi_result['score']
        )

        # All available profiles for frontend dropdown
        profiles_list = [
            {'key': k, 'label': v['label']}
            for k, v in VULNERABILITY_PROFILES.items()
        ]

        return jsonify({
            'hvi': hvi_result,
            'advisories': advisories,
            'aqi_indian': aqi_indian,
            'aqi_us': aqi_us,
            'data_source': data_source,
            'available_profiles': profiles_list,
            'timestamp': datetime.now().isoformat()
        })

    except requests.RequestException as e:
        return jsonify({'error': f'API request failed: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': f'HVI calculation error: {str(e)}'}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  AQI Forecasting Backend API")
    print("  Architecture: Pollutants → Atmospheric Corrections → AQI")
    print("="*60)
    print(f"  Priority 1: AQICN ground station")
    print(f"  Priority 2: OWM satellite estimate (last resort)")
    print(f"  Per-Pollutant Models: {len(POLLUTANT_MODELS)} loaded")
    print(f"  Spatial Features: IDW + Wind Transport")
    print(f"  Atmospheric Corrections: Wind/Rain/Humidity/Inversion")
    print(f"  Endpoints:")
    print(f"    GET /api/current-aqi?lat=...&lon=...  (MEASURED)")
    print(f"    GET /api/predict?lat=...&lon=...&hours=...  (FORECAST)")
    print(f"    GET /api/geocode?city=...")
    print(f"    GET /api/hvi?lat=...&lon=...&profile=...")
    print(f"    GET /api/health")
    print("="*60 + "\n")
    app.run(debug=False, port=5001)
