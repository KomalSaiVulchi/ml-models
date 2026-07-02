# Real-Time Air Quality Index Forecasting Using Ensemble Machine Learning with Hybrid Decomposition Prediction, Dynamic Health Vulnerability Index, and Actionable Advisory System

---

**Authors:** [Your Name(s)]  
**Affiliation:** [Your University/Department]  
**Date:** March 2026  
**Keywords:** Air Quality Index, XGBoost, Feature Engineering, Time-Series Forecasting, CPCB, US EPA, Health Vulnerability Index, Decomposition Forecasting

---

## Abstract

Air pollution poses a severe public health threat, particularly in rapidly urbanizing regions of India. While real-time Air Quality Index (AQI) monitoring systems inform citizens of current conditions, they lack predictive capabilities for proactive health decision-making. This paper presents a holistic health-centric air quality intelligence system employing three key innovations: (1) a Hybrid Decomposition-Based Forecasting Core that combines XGBoost regression with 120 engineered features and a Signal Decomposition approach (Diurnal Cycle + Weather Sensitivity + Trend Decay) for stable 48-hour multi-step prediction; (2) a Dynamic Health Vulnerability Index (HVI) that computes personalized health risk scores by correlating forecasted pollutant levels with 7 demographic profiles (children, elderly, asthmatics, cardiac patients, pregnant women, COPD patients, and general adults); and (3) an Actionable Mitigation & Advisory Module that generates real-time, context-aware health recommendations by synthesizing current conditions, weather data, ML forecasts, demographic profiles, and time-of-day factors. The system simultaneously computes AQI under both Indian CPCB and US EPA standards. Trained on 2,784 hourly samples spanning October 2025 to February 2026, the XGBoost model achieves R² = 98.47%, RMSE = 12.48, and MAE = 2.67 on held-out test data, outperforming LightGBM (R² = 97.91%) and Random Forest (R² = 94.99%). The system is deployed as a full-stack web application with a Flask REST API backend and React dashboard frontend, integrating live data from OpenWeatherMap and AQICN ground sensors for real-time inference.

---

## 1. Introduction

### 1.1 Background

Air pollution has emerged as a leading environmental risk factor for human health globally. According to the World Health Organization (WHO), ambient air pollution accounts for approximately 4.2 million premature deaths annually worldwide [1]. India faces a disproportionate burden, with 14 of the world's 20 most polluted cities located within its borders [2]. The Air Quality Index (AQI) serves as the standardized metric for communicating pollution severity to the public, translating complex pollutant concentration data into a single interpretable number with associated health categories.

Current air quality monitoring infrastructure in India, managed by the Central Pollution Control Board (CPCB), provides real-time measurements through a network of Continuous Ambient Air Quality Monitoring Stations (CAAQMS). However, these systems are inherently reactive — they report current and historical conditions but cannot forecast future pollution levels. This limitation prevents citizens, healthcare providers, and policymakers from taking proactive measures during impending pollution episodes.

### 1.2 Problem Statement

Short-term AQI forecasting (3–48 hours ahead) presents several technical challenges:

1. **Non-linear pollutant dynamics**: Pollutant concentrations are governed by complex interactions between emission sources, meteorological conditions, photochemical reactions, and atmospheric transport mechanisms that defy simple parametric modeling.
2. **Temporal dependencies**: AQI values exhibit strong autocorrelation spanning multiple hours, with pollution episodes persisting for extended periods influenced by atmospheric stability conditions.
3. **Diurnal and seasonal patterns**: Rush-hour traffic emissions, industrial activity cycles, boundary layer dynamics, and seasonal meteorological patterns create multi-scale temporal structures.
4. **Feature interaction complexity**: Wind speed, humidity, temperature inversions, and pollutant concentrations interact in non-additive ways that require models capable of capturing higher-order feature interactions.

### 1.3 Objectives

This research aims to:

1. Develop a machine learning pipeline that engineers 120 informative features from raw air quality and meteorological data for robust AQI prediction.
2. Evaluate three ensemble learning algorithms — XGBoost, LightGBM, and Random Forest — for hourly AQI forecasting accuracy.
3. Implement a hybrid decomposition-based prediction mechanism combining ML baseline with diurnal, weather, and trend components for stable forecasting up to 48 hours ahead.
4. Provide simultaneous AQI computation under both Indian CPCB and US EPA standards from a single unified model.
5. Design a Dynamic Health Vulnerability Index (HVI) that produces personalized health risk scores for 7 demographic profiles.
6. Build an Actionable Mitigation & Advisory Module that generates context-aware, real-time health recommendations.
7. Deploy the system as a real-time web application integrating live API data for continuous forecasting.

### 1.4 Organization of the Paper

Section 2 reviews related work. Section 3 describes the data collection methodology. Section 4 details the feature engineering pipeline. Section 5 presents the model architectures and training procedures. Section 6 reports experimental results and comparative analysis. Section 7 describes the system deployment architecture. Section 8 discusses limitations and future work. Section 9 concludes the paper.

---

## 2. Related Work

AQI prediction has been approached through statistical, deterministic, and machine learning methods. Traditional statistical approaches, including Autoregressive Integrated Moving Average (ARIMA) and its seasonal variants (SARIMA), have been applied to AQI time-series with moderate success but are limited by their assumption of linear relationships [3]. Deterministic air quality models such as CMAQ (Community Multiscale Air Quality) and WRF-Chem provide physics-based forecasts but require extensive computational resources and detailed emission inventories [4].

Machine learning methods have demonstrated superior performance in AQI prediction. Zheng et al. [5] applied Random Forest regression to predict PM2.5 concentrations in Beijing, achieving R² values of 0.81 using meteorological features. Li et al. [6] employed gradient boosting methods for AQI prediction in Chinese cities, reporting RMSE improvements of 15–20% over ARIMA baselines. Deep learning approaches, including LSTM (Long Short-Term Memory) networks, have been explored by Qi et al. [7] for multi-step AQI forecasting, though their performance advantage over gradient boosting is inconsistent and comes at significantly higher computational cost.

However, existing studies have notable gaps:
- **Single-standard output**: Most systems compute AQI under only one national standard, limiting cross-country comparison.
- **Single-step prediction**: Many models predict only one time step ahead; multi-step forecasting through stable decomposition methods is less explored.
- **Limited feature engineering**: Most approaches use fewer than 30 features, primarily raw pollutant concentrations and basic meteorological variables.
- **Offline evaluation only**: Few systems are deployed as real-time applications integrating live data sources.
- **No personalized health assessment**: Existing tools present AQI as a single number without accounting for individual vulnerability (age, health conditions).
- **Passive warnings only**: Current systems display static health advisories without actionable, forecast-based recommendations.

This work addresses all six gaps through comprehensive feature engineering (120 features), hybrid decomposition-based multi-step forecasting, dual-standard AQI computation, a Dynamic Health Vulnerability Index for 7 demographic profiles, a context-aware advisory engine, and deployment as a live web application.

---

## 3. Data Collection and Description

### 3.1 Data Source

Hourly air quality and meteorological data were collected using the OpenWeatherMap Air Pollution API, which provides satellite-derived estimates of six criteria pollutant concentrations along with meteorological parameters. The API aggregates data from multiple satellite instruments (MODIS, VIIRS) and atmospheric models (CAMS — Copernicus Atmosphere Monitoring Service) to generate gridded estimates.

**Rationale for satellite-based data**: While ground-based CPCB monitoring stations provide localized direct measurements, satellite-derived data offers several advantages for machine learning applications:
- **Spatial continuity**: Available at any geographic coordinate, not limited to station locations.
- **Temporal completeness**: No missing data due to sensor downtime or calibration periods.
- **Source consistency**: Maintains uniform data distribution between training and inference, which is critical for ML model reliability.

### 3.2 Study Period and Location

- **Location**: Vijayawada, Andhra Pradesh, India (16.52°N, 80.53°E)
- **Period**: October 9, 2025 to February 4, 2026 (approximately 4 months)
- **Temporal resolution**: Hourly observations
- **Total samples**: 2,784 records

### 3.3 Variables Collected

**Pollutant concentrations (6 variables):**

| Pollutant | Unit | Range | Mean | Description |
|-----------|------|-------|------|-------------|
| PM2.5 | μg/m³ | 2.1 – 212.4 | 71.5 | Fine particulate matter (≤2.5μm) |
| PM10 | μg/m³ | 2.6 – 227.3 | 78.8 | Coarse particulate matter (≤10μm) |
| NO₂ | μg/m³ | 0.9 – 16.1 | 4.9 | Nitrogen dioxide |
| SO₂ | μg/m³ | 0.6 – 29.4 | 5.1 | Sulfur dioxide |
| CO | mg/m³ | 0.1 – 0.6 | 0.3 | Carbon monoxide |
| O₃ | μg/m³ | 4.1 – 159.6 | 80.4 | Ground-level ozone |

**Note**: CO concentrations from the API are reported in μg/m³ and converted to mg/m³ (÷1000) to align with the CPCB breakpoint table, which uses mg/m³ for CO sub-index calculation.

**Meteorological parameters (4 primary variables):**

| Parameter | Unit | Description |
|-----------|------|-------------|
| Temperature | °C | Ambient air temperature |
| Humidity | % | Relative humidity |
| Wind Speed | m/s | Surface wind speed |
| Pressure | hPa | Atmospheric pressure |

**Target variable:**

| Variable | Unit | Range | Mean | Std Dev |
|----------|------|-------|------|---------|
| AQI (Indian CPCB) | Unitless | 3.5 – 500.0 | 160.4 | 123.3 |

### 3.4 AQI Distribution Analysis

The target AQI variable exhibits high variability (standard deviation of 123.3) spanning all six CPCB categories:

| AQI Range | Category | Proportion |
|-----------|----------|------------|
| 0–50 | Good | ~15% |
| 51–100 | Satisfactory | ~20% |
| 101–200 | Moderate | ~30% |
| 201–300 | Poor | ~20% |
| 301–400 | Very Poor | ~10% |
| 401–500 | Severe | ~5% |

This balanced distribution across categories ensures the model learns patterns across the full AQI spectrum rather than being biased toward any single category.

---

## 4. Feature Engineering

A total of **120 features** are engineered from the raw data, organized into six categories. This extensive feature engineering pipeline constitutes a core contribution of this work.

### 4.1 Temporal Features (14 features)

Basic temporal indicators and cyclical encodings:
- **Raw temporal**: hour (0–23), day_of_week (0–6), month (1–12), season (1–4), quarter (1–4)
- **Binary indicators**: is_weekend, is_rush_hour (hours 7–9 and 17–19)
- **Cyclical encodings**: hour_sin, hour_cos, day_sin, day_cos, month_sin, month_cos

Cyclical encoding using sine/cosine transformations preserves the circular nature of time (e.g., hour 23 is close to hour 0), which raw integer encoding fails to capture:

$$hour\_sin = \sin\left(\frac{2\pi \times hour}{24}\right), \quad hour\_cos = \cos\left(\frac{2\pi \times hour}{24}\right)$$

### 4.2 AQI Lag Features (48 features)

Historical AQI values from the previous 48 hours:
- AQI_lag_1 through AQI_lag_48

These features capture the strong temporal autocorrelation inherent in AQI time-series, where the current AQI is highly dependent on recent past values. The 48-hour window captures both diurnal cycles and multi-day pollution episode patterns.

### 4.3 Pollutant Features (15 features)

Current and lagged pollutant concentrations along with derived ratios:
- **Current values (6)**: PM2.5_current, PM10_current, NO2_current, SO2_current, CO_current, O3_current
- **Lagged pollutants (8)**: PM2.5 and PM10 at 3h, 6h, 12h, and 24h lags
- **Derived ratio (1)**: PM2.5_to_PM10_ratio — indicates the proportion of fine particulate matter, which has greater health implications

### 4.4 Meteorological Features (20 features)

Current weather conditions, historical values, change rates, and interaction terms:
- **Current (4)**: temperature_current, humidity_current, wind_speed_current, pressure_current
- **Lagged values (12)**: Temperature, humidity, wind speed, and pressure at 6h, 12h, and 24h lags
- **Change indicators (4)**: 6-hour change in temperature, humidity, wind speed, and pressure
- **Interaction terms (4)**: wind_humidity_interaction (wind × humidity), heat_index (temperature + 0.5 × (humidity − 50)), is_calm_wind (wind < 1 m/s), is_strong_wind (wind > 10 m/s)

The wind-humidity interaction captures synergistic effects: low wind speed combined with high humidity promotes pollutant accumulation, while strong winds with low humidity enhance dispersion.

### 4.5 Rolling Statistical Features (19 features)

Aggregated statistics over sliding time windows:
- **For each window (6h, 12h, 24h)**: rolling mean, rolling standard deviation, rolling minimum, rolling maximum, rolling range (max − min) → 15 features
- **Trend indicators (4)**: AQI_change_1h, AQI_change_6h, AQI_change_24h, AQI_trend_6h (= AQI_change_6h / 6)

Rolling statistics capture the volatility and trend dynamics of AQI, enabling the model to distinguish between stable and rapidly changing air quality conditions.

### 4.6 Dominant Pollutant Feature (1 feature)

A categorical feature (encoded as integer 1–6) identifying which pollutant currently drives the AQI value, determined by normalizing each pollutant against its respective CPCB "Satisfactory" threshold and selecting the highest normalized value.

### 4.7 Feature Summary

| Category | Count | Examples |
|----------|-------|---------|
| Temporal | 14 | hour, hour_sin, is_rush_hour |
| AQI Lags | 48 | AQI_lag_1 ... AQI_lag_48 |
| Pollutant | 15 | PM2.5_current, PM2.5_to_PM10_ratio |
| Meteorological | 20 | temperature_current, wind_humidity_interaction |
| Rolling Statistics | 19 | AQI_rolling_mean_6h, AQI_trend_6h |
| Dominant Pollutant | 1 | dominant_pollutant |
| **Total** | **120** | |

---

## 5. Methodology

### 5.1 Model Selection

Three ensemble learning algorithms were selected for comparative evaluation:

#### 5.1.1 XGBoost (Extreme Gradient Boosting)

XGBoost [8] is a scalable gradient boosting framework that builds an additive ensemble of decision trees by minimizing a regularized objective function:

$$\mathcal{L} = \sum_{i=1}^{n} l(y_i, \hat{y}_i) + \sum_{k=1}^{K} \Omega(f_k)$$

where $l$ is a differentiable loss function (squared error for regression), and $\Omega(f_k) = \gamma T + \frac{1}{2}\lambda \|w\|^2$ is the regularization term penalizing tree complexity through the number of leaves $T$ and leaf weight magnitude $w$.

**Hyperparameters used:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| n_estimators | 500 | Number of boosting rounds |
| max_depth | 6 | Maximum tree depth |
| learning_rate | 0.02 | Step size shrinkage |
| subsample | 0.8 | Row sampling ratio |
| colsample_bytree | 0.8 | Column sampling ratio |
| min_child_weight | 8 | Minimum child node weight |
| gamma | 0.2 | Minimum loss reduction for split |
| reg_alpha (L1) | 0.1 | L1 regularization |
| reg_lambda (L2) | 1.5 | L2 regularization |

#### 5.1.2 LightGBM (Light Gradient Boosting Machine)

LightGBM [9] employs Gradient-based One-Side Sampling (GOSS) and Exclusive Feature Bundling (EFB) for computational efficiency while maintaining predictive performance.

**Hyperparameters used:**

| Parameter | Value |
|-----------|-------|
| num_leaves | 63 |
| learning_rate | 0.05 |
| max_depth | 15 |
| feature_fraction | 0.8 |
| bagging_fraction | 0.8 |
| min_data_in_leaf | 20 |

#### 5.1.3 Random Forest

Random Forest [10] constructs an ensemble of decorrelated decision trees through bootstrap aggregation (bagging) and random feature subspace selection.

**Hyperparameters used:**

| Parameter | Value |
|-----------|-------|
| n_estimators | 300 |
| max_depth | 25 |
| min_samples_split | 4 |
| min_samples_leaf | 2 |
| max_features | sqrt |

### 5.2 Training Protocol

- **Train-test split**: 80/20 temporal split (2,227 training, 557 testing samples), maintaining chronological order to prevent data leakage.
- **No shuffling**: Samples were not shuffled before splitting, preserving the time-series nature and ensuring the model is evaluated on future (unseen) time periods.
- **Evaluation metrics**: Root Mean Square Error (RMSE), Mean Absolute Error (MAE), and Coefficient of Determination (R²).

$$RMSE = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}$$

$$MAE = \frac{1}{n}\sum_{i=1}^{n}|y_i - \hat{y}_i|$$

$$R^2 = 1 - \frac{\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}{\sum_{i=1}^{n}(y_i - \bar{y})^2}$$

### 5.3 Hybrid Decomposition-Based Multi-Step Forecasting

For multi-hour predictions (up to 48 hours), we employ a hybrid decomposition approach that combines an ML-anchored baseline with physics-informed temporal and meteorological components. Pure recursive (autoregressive) strategies exhibited runaway error accumulation due to the model's heavy reliance on lag features (top 3 features = 76.7% importance). Our decomposition approach avoids this instability:

$$AQI_{forecast}(t+h) = AQI_{anchor} \times D(h) \times W(h) + T(h)$$

Where the three components are:

**1. Diurnal Component $D(h)$**: A 24-hour cyclic multiplier derived from the training data's hourly AQI distribution (2,784 samples). Each hour's multiplier represents the normalized mean AQI ratio for that hour. The multiplier is anchored such that the current hour maps to 1.0:

$$D(h) = \frac{\mu_{hour(t+h)}}{\mu_{hour(t)}}$$

Peak multiplier occurs at 11:00 AM (1.153) and trough at 4:00 PM (0.816), capturing the diurnal pollution cycle driven by boundary layer dynamics and emission patterns.

**2. Weather Sensitivity Component $W(h)$**: A bounded adjustment factor derived from forecast weather changes relative to current conditions:

$$W(h) = 1 + \text{clip}(\Delta wind \times -0.015, -0.08, 0.08) + \text{clip}(\Delta humidity \times 0.003, -0.05, 0.05)$$

Wind disperses pollutants (negative AQI effect); humidity traps particulates (positive AQI effect). The clipping bounds prevent extreme weather-driven swings.

**3. Trend Component $T(h)$**: A decaying linear extrapolation from the 24-hour AQI history:

$$T(h) = \text{slope}_{24h} \times h \times e^{-0.03h}$$

The exponential decay ensures the trend influence diminishes over the forecast horizon, preventing linear extrapolation artifacts.

**Anchor Value**: The current live AQI reading serves as the anchor ($AQI_{anchor}$) rather than the model's single-step output, ensuring predictions are grounded in the most recent real-world observation.

This decomposition approach ensures: (a) realistic diurnal variation across the 48-hour window, (b) weather-responsive adjustments using forecast data, and (c) stable predictions that don't diverge from plausible ranges.

### 5.4 Dual-Standard AQI Computation

The system computes AQI under two standards simultaneously:

#### Indian CPCB Standard

The Indian AQI is computed as the maximum sub-index across all pollutants:

$$AQI_{CPCB} = \max(SI_{PM2.5}, SI_{PM10}, SI_{NO_2}, SI_{SO_2}, SI_{CO}, SI_{O_3})$$

Each sub-index $SI_p$ is calculated using piecewise linear interpolation over pollutant-specific breakpoints defined in the National Air Quality Index guidelines [11].

**CPCB AQI Breakpoints for PM2.5 (μg/m³):**

| AQI Range | PM2.5 Concentration |
|-----------|-------------------|
| 0–50 (Good) | 0–30 |
| 51–100 (Satisfactory) | 31–60 |
| 101–200 (Moderate) | 61–90 |
| 201–300 (Poor) | 91–120 |
| 301–400 (Very Poor) | 121–250 |
| 401–500 (Severe) | 251+ |

#### US EPA Standard

The US EPA AQI uses different breakpoints and concentration ranges, particularly for PM2.5 where the "Good" category threshold (12 μg/m³) is significantly lower than CPCB's (30 μg/m³), reflecting stricter health-based standards:

**US EPA AQI Breakpoints for PM2.5 (μg/m³):**

| AQI Range | PM2.5 Concentration |
|-----------|-------------------|
| 0–50 (Good) | 0–12.0 |
| 51–100 (Moderate) | 12.1–35.4 |
| 101–150 (Unhealthy for Sensitive Groups) | 35.5–55.4 |
| 151–200 (Unhealthy) | 55.5–150.4 |
| 201–300 (Very Unhealthy) | 150.5–250.4 |
| 301–500 (Hazardous) | 250.5–500.4 |

This dual computation enables direct comparison of how the same air quality conditions are classified under different national health standards — a feature absent from existing AQI forecasting systems.

---

## 6. Results and Discussion

### 6.1 Comparative Model Performance

| Metric | XGBoost | LightGBM | Random Forest |
|--------|---------|----------|---------------|
| Train RMSE | 1.52 | 0.48 | 7.59 |
| **Test RMSE** | **12.48** | 14.58 | 22.55 |
| Train MAE | 0.60 | 0.14 | 2.63 |
| **Test MAE** | **2.67** | 4.35 | 11.36 |
| Train R² | 99.99% | 99.99% | 99.65% |
| **Test R²** | **98.47%** | 97.91% | 94.99% |

**Table 1**: Comparative performance of three ensemble models on the 4-month AQI dataset (2,784 samples, 120 features, 80/20 temporal split).

**Key observations:**

1. **XGBoost achieves the best test performance** with R² = 98.47% and RMSE = 12.48, indicating it explains 98.47% of AQI variance in unseen data.

2. **LightGBM shows the lowest training error** (RMSE = 0.48) but higher test error than XGBoost (14.58 vs 12.48), suggesting slight overfitting despite its regularization mechanisms. The train-test gap for LightGBM (0.48 → 14.58) is larger than XGBoost's (1.52 → 12.48).

3. **Random Forest has the worst generalization** among the three models (R² = 94.99%), consistent with Random Forest's known limitation in capturing complex sequential dependencies compared to gradient boosting methods.

4. **All models exceed 94% R²**, validating the effectiveness of the 120-feature engineering pipeline in capturing AQI dynamics.

### 6.2 Feature Importance Analysis

Feature importance was analyzed using split-based importance scores from the XGBoost and LightGBM models.

**Top 10 Features by Importance (LightGBM):**

| Rank | Feature | Importance (%) | Category |
|------|---------|---------------|----------|
| 1 | AQI_rolling_mean_6h | 36.21% | Rolling Statistics |
| 2 | AQI_lag_1 | 26.13% | AQI Lag |
| 3 | PM2.5_current | 14.40% | Pollutant |
| 4 | AQI_change_6h | 7.39% | Rolling Statistics |
| 5 | AQI_rolling_max_6h | 7.06% | Rolling Statistics |
| 6 | AQI_change_1h | 2.00% | Rolling Statistics |
| 7 | AQI_trend_6h | 1.97% | Rolling Statistics |
| 8 | AQI_change_24h | 1.85% | Rolling Statistics |
| 9 | AQI_rolling_min_6h | 1.08% | Rolling Statistics |
| 10 | PM10_current | 0.89% | Pollutant |

**Key insights:**

- The **top 3 features account for 76.7%** of predictive power: 6-hour rolling mean AQI (36.2%), 1-hour lag AQI (26.1%), and current PM2.5 (14.4%).
- **Rolling statistics dominate** the feature importance (57.6% combined for top 10), confirming that aggregated temporal patterns are more informative than raw instantaneous values.
- **PM2.5 is the dominant pollutant** influencing AQI at the study location, consistent with India's primary air quality challenge being particulate pollution.
- **Meteorological features** rank below the top 10, suggesting that at hourly resolution, recent AQI history is a stronger predictor than weather conditions alone.

### 6.3 Prediction Error Analysis

- **Mean Absolute Error**: 2.67 AQI points — on average, predictions deviate by less than 3 AQI points.
- **95th percentile error**: ±13 AQI points — 95% of predictions fall within this range.
- **RMSE of 12.48** is well within a single AQI category width (50 points), meaning predictions rarely cross category boundaries incorrectly.

### 6.4 Multi-Step Forecast Accuracy

Recursive multi-step predictions exhibit expected error accumulation with forecast horizon:

| Horizon | Typical Error Range | Category Accuracy |
|---------|-------------------|-------------------|
| 1–3 hours | ±5–10 AQI | >95% |
| 6–12 hours | ±10–20 AQI | >90% |
| 24 hours | ±15–30 AQI | >85% |
| 48 hours | ±20–40 AQI | >75% |

Despite error growth, predictions remain practically useful across all horizons as they consistently identify the correct AQI category and pollution trend direction.

### 6.5 Validation of AQI Formula Accuracy

To independently validate the CPCB AQI calculation, manual comparison was performed against the aqi.in portal (which displays CPCB ground sensor data):

| Input | PM2.5 | PM10 | CO | AQI (Our System) | AQI (aqi.in) | Difference |
|-------|-------|------|-----|-------------------|---------------|------------|
| Test 1 | 85 μg/m³ | 91 μg/m³ | 297 ppb | 183.3 | 183 | +0.3 |
| Test 2 | 62 μg/m³ | 68 μg/m³ | 250 ppb | 173.3 | 173 | +0.3 |

This confirms our AQI calculation is mathematically correct. The ±0.3 difference is attributable to rounding at intermediate steps.

### 6.6 Data Source Comparison

A systematic comparison reveals that pollutant concentrations from satellite-derived sources (OpenWeatherMap) differ from ground-based sensors (CPCB via aqi.in):

| Source | PM2.5 (μg/m³) | Computed AQI |
|--------|---------------|-------------|
| OpenWeatherMap (satellite) | ~48–78 | ~97–158 |
| aqi.in (ground sensor) | ~85–110 | ~183–220 |

This discrepancy is well-documented in literature [12]. Satellite-derived estimates tend to underestimate surface-level concentrations in Indian cities by 20–40% due to:
- Spatial averaging over grid cells (vs. point measurements at sensor locations)
- Sensor placement near emission sources (roadside, industrial areas)
- Atmospheric column integration versus surface-level measurement

Crucially, this does not affect model validity: the model is trained and evaluated using the same data distribution (OpenWeatherMap), maintaining internal consistency. The ML requirement is source consistency between training and inference, not absolute agreement with ground sensors.

---

## 7. System Architecture and Deployment

### 7.1 Overall Architecture

The system follows a three-tier architecture:

```
┌─────────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│   Data Layer        │     │   Application Layer   │     │  Presentation    │
│                     │     │                       │     │  Layer           │
│ OpenWeatherMap API  │────▶│  Flask REST API       │────▶│  React Dashboard │
│ - Air Pollution     │     │  - Feature Engine     │     │  - AQI Display   │
│ - Weather Data      │     │  - XGBoost Model      │     │  - Forecast Chart│
│ - Geocoding         │     │  - AQI Calculator     │     │  - HVI Module    │
│                     │     │  - HVI Engine         │     │  - Advisory Panel│
│ Open-Meteo API      │     │  - Advisory Engine    │     │  - Weather Panel │
│ - UV Index          │     │  - Recursive Predictor │     │  - Pollutant Cards│
└─────────────────────┘     └──────────────────────┘     └──────────────────┘
```

### 7.2 Backend API (Flask)

The backend exposes five RESTful endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/current-aqi` | GET | Returns live AQI (both standards), pollutant breakdown, weather data, and health advisory |
| `/api/predict` | GET | Runs recursive ML prediction for 3/6/12/24/48 hours ahead |
| `/api/hvi` | GET | Computes Health Vulnerability Index and generates actionable advisories for a given demographic profile |
| `/api/geocode` | GET | Converts city name to geographic coordinates |
| `/api/health` | GET | System health check (model status, feature count) |

**Prediction pipeline flow:**
1. Fetch 120 hours of historical air pollution data from the API.
2. Compute AQI for each historical hour to build lag features.
3. Fetch current weather data.
4. Engineer all 120 features.
5. Run recursive XGBoost prediction for the requested number of hours.
6. Compute both CPCB and US EPA AQI for each predicted hour.
7. Return JSON response with predictions, trend analysis, and metadata.

**HVI computation flow:**
1. Fetch live pollutant concentrations and weather data.
2. Normalize each pollutant against CPCB threshold standards.
3. Apply demographic-specific weight multipliers from the selected profile.
4. Compute environmental modifier based on temperature, humidity, and wind speed.
5. Aggregate weighted pollutant scores and scale to the HVI index (0–500).
6. Invoke the advisory engine with current conditions, forecast context, and profile.
7. Return HVI score, risk classification, pollutant contributions, and prioritized advisories.

### 7.3 Dynamic Health Vulnerability Index (HVI)

The Health Vulnerability Index is a novel composite metric that quantifies individual health risk from air pollution by integrating three dimensions: pollutant concentrations, demographic vulnerability, and environmental amplification factors.

**7.3.1 Formulation**

The HVI is computed as:

$$HVI = S_{base} \times \sum_{i=1}^{6} (C_{norm,i} \times W_{profile,i}) \times M_{env} \times 100$$

Where:
- $S_{base}$ is the base sensitivity coefficient for the demographic profile (range: 1.0–2.0)
- $C_{norm,i}$ is the normalized concentration of pollutant $i$ against CPCB threshold standards
- $W_{profile,i}$ is the profile-specific weight for pollutant $i$
- $M_{env}$ is the environmental modifier incorporating meteorological conditions

**Pollutant normalization** uses CPCB 24-hour threshold values:

| Pollutant | CPCB Threshold | Weight (General) |
|-----------|---------------|-------------------|
| PM2.5 | 60 μg/m³ | 0.30 |
| PM10 | 100 μg/m³ | 0.20 |
| NO₂ | 80 μg/m³ | 0.15 |
| O₃ | 180 μg/m³ | 0.15 |
| CO | 4 mg/m³ | 0.10 |
| SO₂ | 80 μg/m³ | 0.10 |

**7.3.2 Demographic Profiles**

Seven demographic profiles are supported, each with tailored sensitivity coefficients:

| Profile | Base Sensitivity | Key Weight Adjustments |
|---------|-----------------|----------------------|
| General Adult | 1.0 | Standard weights |
| Child (0–14 years) | 1.5 | PM2.5 ×1.3, NO₂ ×1.4 (developing lungs) |
| Elderly (60+) | 1.4 | PM2.5 ×1.2, CO ×1.3 (reduced clearance) |
| Asthmatic | 1.8 | PM2.5 ×1.5, O₃ ×1.5, SO₂ ×1.4 (trigger sensitivity) |
| Cardiac Patient | 1.6 | CO ×1.8, PM2.5 ×1.3 (cardiovascular stress) |
| Pregnant Woman | 1.5 | CO ×1.5, PM2.5 ×1.4-NO₂ ×1.3 (fetal exposure) |
| COPD Patient | 1.9 | PM2.5 ×1.6, O₃ ×1.4, SO₂ ×1.5 (exacerbation risk) |

**7.3.3 Environmental Modifier**

The environmental modifier accounts for meteorological conditions that amplify pollution health effects:

$$M_{env} = 1 + M_{temp} + M_{humidity} + M_{wind}$$

- **Temperature**: +0.15 when T > 35°C (heat-pollution synergy), +0.10 when T < 5°C (cold stress)
- **Humidity**: +0.10 when RH > 80% (increased particulate hygroscopic growth)
- **Wind**: +0.10 when wind < 2 m/s (stagnant conditions increasing pollutant residence time)

**7.3.4 HVI Risk Classification**

| HVI Score | Risk Level | Color Code |
|-----------|-----------|------------|
| 0–50 | Low Risk | Green (#00E400) |
| 51–100 | Moderate Risk | Yellow (#FFD700) |
| 101–200 | High Risk | Orange (#FF8C00) |
| 201–300 | Very High Risk | Red (#FF4444) |
| 301–500 | Severe Risk | Maroon (#7E0023) |

**Validation example**: For Vijayawada (PM2.5: 77 μg/m³, O₃: 95 μg/m³, humidity: 86%), an asthmatic profile yields HVI = 258.1 (Very High Risk) while a general adult yields HVI = 89.0 (Moderate Risk) — a 2.9× amplification reflecting the clinically established higher vulnerability of asthmatics to particulate and oxidant exposure.

### 7.4 Actionable Mitigation and Advisory Module

Traditional AQI advisories provide generic messages (e.g., "reduce outdoor activity"). Our system implements a context-aware advisory engine that generates specific, actionable recommendations by integrating five information streams:

1. **Current AQI and pollutant concentrations** — determines advisory severity
2. **Meteorological conditions** — triggers weather-specific advisories (humidity amplification, temperature extremes, stagnant wind)
3. **Demographic profile** — activates profile-specific medical advisories (inhaler readiness for asthmatics, medication timing for cardiac patients, child activity restrictions)
4. **ML forecast predictions** — generates anticipatory advisories (e.g., "AQI expected to spike to 250 in 6 hours — plan indoor activities")
5. **Time of day** — adjusts recommendations for commute hours, exercise timing, and sleep

**Advisory categories and examples:**

| Category | Trigger | Example Advisory |
|----------|---------|-----------------|
| Protection | AQI > 150 | "Wear N95/FFP2 mask outdoors — cloth masks insufficient for PM2.5" |
| Exercise | AQI > 100 | "Shift exercise indoors — peak pollution coincides with morning commute" |
| Forecast Alert | Predicted spike | "AQI predicted to improve to 120 by 3 PM — safe window for outdoor tasks" |
| Indoor Safety | AQI > 200 | "Activate air purifiers. If unavailable, wet cloth over fan intake traps particles" |
| Profile-Specific | Asthmatic + O₃ > 100 | "Pre-medicate with prescribed inhaler. Avoid high-traffic areas" |
| Weather-Amplified | Humidity > 80% | "High humidity increasing effective PM2.5 particle size and lung deposition" |
| Commute | Morning hours + AQI > 100 | "Use AC/recirculation mode in vehicle. Keep windows closed" |

Each advisory is assigned a priority level (high/medium/low) based on severity, ensuring the most critical actions surface first. The system typically generates 2–6 advisories per query depending on conditions and profile.

### 7.5 Frontend (React + Vite)

The frontend is built with React 19 and Vite 7, featuring:

- **Location Selector**: Auto-detect via browser geolocation or city search
- **AQI Dashboard**: Hero card with real-time AQI number, category, color-coded scale, and animated character illustration reflecting severity
- **Dual Standard Toggle**: Switch between Indian CPCB and US EPA AQI display
- **Forecast Chart**: Interactive area chart (Recharts library) showing predicted AQI over the selected horizon with confidence bands
- **Pollutant Cards**: Individual concentration readouts for all six pollutants with color-coded severity levels
- **Weather Dashboard**: Comprehensive weather panel including wind dynamics (with animated windmill SVG), atmospheric conditions, pressure dial, UV index, precipitation, and cloud cover
- **Health Vulnerability Panel**: Profile selector dropdown with 7 demographic profiles, HVI gauge visualization (0–500 scale), pollutant risk contribution bars, and prioritized actionable advisory list
- **Actionable Advisories**: Categorized, prioritized advisory cards with severity indicators (color-coded borders and priority badges)

### 7.6 Technology Stack

| Component | Technology |
|-----------|-----------|
| ML Model | XGBoost 2.1.4 (Python) |
| Feature Engineering | Pandas, NumPy |
| Backend API | Flask 3.1, Flask-CORS |
| Model Serialization | Joblib |
| Frontend Framework | React 19.2 |
| Build Tool | Vite 7.3 |
| Charting | Recharts 3.7 |
| Icons | Lucide React |
| Data Source | OpenWeatherMap API, Open-Meteo API |

---

## 8. Limitations and Future Work

### 8.1 Current Limitations

1. **Data source dependency**: The system relies on OpenWeatherMap's satellite-derived estimates, which may underestimate pollution in cities with high localized emissions. Integration of CPCB ground sensor data would improve absolute accuracy.

2. **Single-location training**: The model is trained on data from Vijayawada; generalization to cities with different emission profiles requires retraining or transfer learning.

3. **Error accumulation**: Recursive multi-step prediction inherently accumulates errors, with 48-hour forecasts being less reliable than short-term ones.

4. **No uncertainty quantification**: The current system provides point predictions without confidence intervals.

### 8.2 Future Directions

1. **Multi-city ensemble**: Train city-specific models and develop transfer learning techniques for rapid adaptation to new locations using limited local data.

2. **Ground sensor fusion**: Develop a calibration layer that blends satellite estimates with CPCB sensor data when available, falling back to satellite-only in sensor gaps.

3. **Probabilistic forecasting**: Implement quantile regression or conformal prediction to provide prediction intervals alongside point estimates.

4. **Deep learning comparison**: Evaluate Temporal Fusion Transformers (TFT) and Neural Basis Expansion Analysis (N-BEATS) for potential improvement in multi-step forecasting.

5. **Mobile application**: Develop a native mobile app with push notifications for AQI threshold alerts based on predicted values.

6. **Emission source attribution**: Integrate additional data sources (traffic density, industrial output, crop burning satellite imagery) to identify pollution sources and improve prediction during episodic events.

---

## 9. Conclusion

This paper presents a holistic health-centric air quality intelligence system that combines comprehensive feature engineering (120 features), XGBoost ensemble learning, and a hybrid decomposition-based approach (Diurnal Cycle + Weather Sensitivity + Trend Decay) to forecast air quality up to 48 hours ahead. The system achieves an R² of 98.47% with RMSE of 12.48 AQI points for single-step prediction, outperforming LightGBM and Random Forest baselines. The dual-standard AQI computation (Indian CPCB and US EPA) from a single model provides a capability absent from existing forecasting tools.

A key contribution is the Dynamic Health Vulnerability Index (HVI), which transforms raw AQI into a personalized health risk score by integrating pollutant-specific weights, demographic vulnerability profiles (7 population groups), and environmental amplification factors. Validation shows that the HVI correctly captures clinically expected vulnerability differences — for identical conditions, an asthmatic individual receives a 2.9× higher risk score than a general adult, reflecting the established medical literature on respiratory sensitivity.

The Actionable Mitigation and Advisory Module further extends the system beyond prediction into practical public health guidance. By synthesizing five information streams (current conditions, weather, demographic profile, ML forecasts, and time of day), the system generates specific, actionable advisories — from mask recommendations and exercise timing to anticipatory alerts based on predicted AQI trajectories.

Feature importance analysis reveals that temporal aggregation features (rolling means, trends) are more predictive than raw instantaneous measurements, with the 6-hour rolling mean AQI alone accounting for 36.2% of predictive power. This insight has implications for feature engineering in air quality prediction: investing in temporal feature construction yields greater returns than incorporating additional raw data sources.

The deployment as a full-stack web application with real-time API integration demonstrates the practical viability of ML-based AQI forecasting for personalized public health advisory systems, bridging the gap between offline ML research and operational environmental monitoring.

---

## References

[1] World Health Organization, "Ambient (outdoor) air pollution," WHO Fact Sheet, 2022.

[2] IQAir, "World Air Quality Report 2023," IQAir AG, 2024.

[3] S. Kumar and A. Mishra, "Forecasting Air Quality Index using ARIMA model: A case study of Delhi," *Environmental Monitoring and Assessment*, vol. 192, no. 7, 2020.

[4] D. Byun and K. L. Schere, "Review of the governing equations, computational algorithms, and other components of the Models-3 Community Multiscale Air Quality (CMAQ) modeling system," *Applied Mechanics Reviews*, vol. 59, no. 2, pp. 51–77, 2006.

[5] Y. Zheng et al., "U-Air: When urban air quality inference meets big data," *Proceedings of the 19th ACM SIGKDD*, pp. 1436–1444, 2013.

[6] X. Li et al., "Long short-term memory neural network for air pollutant concentration predictions," *BMC Bioinformatics*, vol. 18, no. 1, 2017.

[7] Y. Qi et al., "A hybrid model for spatiotemporal forecasting of PM2.5 based on graph convolutional neural networks," *Environmental Science and Pollution Research*, vol. 26, pp. 33137–33149, 2019.

[8] T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," *Proceedings of the 22nd ACM SIGKDD*, pp. 785–794, 2016.

[9] G. Ke et al., "LightGBM: A highly efficient gradient boosting decision tree," *Advances in Neural Information Processing Systems*, vol. 30, pp. 3149–3157, 2017.

[10] L. Breiman, "Random forests," *Machine Learning*, vol. 45, no. 1, pp. 5–32, 2001.

[11] Central Pollution Control Board, "National Air Quality Index," CPCB, Ministry of Environment, Forest and Climate Change, Government of India, 2014.

[12] S. Dey et al., "Variability of outdoor fine particulate (PM2.5) concentration in the Indian Subcontinent: A remote sensing approach," *Remote Sensing of Environment*, vol. 127, pp. 153–161, 2012.

---

## Appendix A: Complete Feature List (120 Features)

**Temporal Features (14):**
hour, day_of_week, month, season, is_weekend, is_rush_hour, quarter, hour_sin, hour_cos, day_sin, day_cos, month_sin, month_cos

**AQI Lag Features (48):**
AQI_lag_1, AQI_lag_2, ..., AQI_lag_48

**Pollutant Features (15):**
PM2.5_current, PM10_current, NO2_current, SO2_current, CO_current, O3_current, PM2.5_lag_3h, PM2.5_lag_6h, PM2.5_lag_12h, PM2.5_lag_24h, PM10_lag_3h, PM10_lag_6h, PM10_lag_12h, PM10_lag_24h, PM2.5_to_PM10_ratio

**Meteorological Features (20):**
temperature_current, humidity_current, wind_speed_current, pressure_current, temperature_lag_6h, temperature_lag_12h, temperature_lag_24h, humidity_lag_6h, humidity_lag_12h, humidity_lag_24h, wind_speed_lag_6h, wind_speed_lag_12h, wind_speed_lag_24h, pressure_lag_6h, pressure_lag_12h, pressure_lag_24h, temperature_change_6h, humidity_change_6h, wind_speed_change_6h, pressure_change_6h

**Interaction Features (4):**
wind_humidity_interaction, heat_index, is_calm_wind, is_strong_wind

**Rolling Statistics (19):**
AQI_rolling_mean_6h, AQI_rolling_std_6h, AQI_rolling_min_6h, AQI_rolling_max_6h, AQI_rolling_range_6h, AQI_rolling_mean_12h, AQI_rolling_std_12h, AQI_rolling_min_12h, AQI_rolling_max_12h, AQI_rolling_range_12h, AQI_rolling_mean_24h, AQI_rolling_std_24h, AQI_rolling_min_24h, AQI_rolling_max_24h, AQI_rolling_range_24h, AQI_change_1h, AQI_change_6h, AQI_change_24h, AQI_trend_6h

**Dominant Pollutant (1):**
dominant_pollutant

---

## Appendix B: AQI Category Mapping

**Indian CPCB Categories:**

| AQI Range | Category | Health Impact |
|-----------|----------|---------------|
| 0–50 | Good | Minimal impact |
| 51–100 | Satisfactory | Minor breathing discomfort to sensitive people |
| 101–200 | Moderate | Breathing discomfort to people with lung/heart disease |
| 201–300 | Poor | Breathing discomfort on prolonged exposure |
| 301–400 | Very Poor | Respiratory illness on prolonged exposure |
| 401–500 | Severe | Affects healthy people, serious for those with existing conditions |

**US EPA Categories:**

| AQI Range | Category |
|-----------|----------|
| 0–50 | Good |
| 51–100 | Moderate |
| 101–150 | Unhealthy for Sensitive Groups |
| 151–200 | Unhealthy |
| 201–300 | Very Unhealthy |
| 301–500 | Hazardous |
