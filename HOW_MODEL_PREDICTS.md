# How Your Current Forecasting Model Predicts

## What The Live System Predicts

The current system does not directly predict a single AQI number.

It first predicts future pollutant concentrations for:

- PM2.5
- PM10
- NO2
- SO2
- CO
- O3

and it does that for 5 trained forecast horizons:

- 1 hour
- 3 hours
- 6 hours
- 12 hours
- 24 hours

That means the deployed forecasting stack uses 30 separate models:

$$
6 \text{ pollutants} \times 5 \text{ horizons} = 30 \text{ models}
$$

Only after those pollutant values are predicted does the backend compute AQI from the pollutant concentrations.

## What Happens In Production

The real production flow is:

```text
Current pollutant history + weather history + time context
        ↓
Per-pollutant ML models predict future concentrations
        ↓
Atmospheric correction rules adjust those concentrations
        ↓
Indian AQI and US AQI are calculated from the adjusted pollutants
        ↓
Category, dominant pollutant, confidence band, and advisories are returned
```

So the system is now a pollutant forecasting engine, not a direct AQI regressor.

## The 30 Models

Each model predicts one pollutant at one horizon.

Examples:

- `pm25_1h_model.pkl` predicts PM2.5 1 hour ahead
- `o3_24h_model.pkl` predicts O3 24 hours ahead
- `co_12h_model.pkl` predicts CO 12 hours ahead

When the backend needs a forecast for a given hour ahead, it chooses the nearest trained horizon from:

- 1
- 3
- 6
- 12
- 24

Example:

- Request for 2 hours ahead uses the nearest trained horizon
- Request for 10 hours ahead uses the nearest trained horizon

This keeps inference simple and stable while still supporting multiple forecast windows.

## Inputs Used For Prediction

Each pollutant model uses a feature vector built at request time from recent pollution history, recent weather, and time context.

Depending on pollutant and horizon, a model uses between 80 and 161 features.

### 1. Time Features

These encode when the forecast is being made:

- hour
- day of week
- month
- weekend flag
- rush-hour flag
- cyclic encodings using sine and cosine

Why they matter:

- pollution has daily cycles
- traffic patterns matter
- seasonal behavior matters

### 2. Pollutant History Features

For each pollutant, the backend can use:

- current value
- lag values at 1, 2, 3, 6, 12, 24, 48, 72, and 168 hours
- rolling means over 6, 12, 24, 48, and 168 hours
- rolling standard deviations over the same windows

Why they matter:

- pollutant behavior is strongly autocorrelated
- persistence matters
- daily and weekly cycles matter
- volatility matters

### 3. Weather Features

The backend also builds weather features from current or forecast weather plus recent history:

- temperature
- humidity
- wind speed
- pressure
- lagged weather values
- 6-hour and 24-hour changes

Why they matter:

- wind affects dispersion
- humidity affects particle growth
- pressure can indicate stagnant conditions
- changing weather can shift pollutant behavior quickly

### 4. Cross-Feature Terms

The live feature builder also includes engineered interaction features when the model expects them, such as:

- PM2.5 to PM10 ratio
- wind-humidity interaction
- heat index
- calm-wind flag

These help the models capture physically meaningful combinations instead of only single raw variables.

## How A Single Forecast Is Made

For each pollutant:

1. The backend selects the model for the nearest available horizon.
2. It loads the exact feature list stored in the model manifest.
3. It reconstructs those features in the same order used during training.
4. The trained XGBoost model predicts the future concentration.
5. Negative predictions are clamped to zero.

For CO only, there is one extra step:

- the model was trained on `log1p(CO)`
- at inference time the backend applies `expm1()` to convert the prediction back to normal CO concentration space

That log transform was added because CO had the worst long-horizon behavior before retraining, and it materially improved accuracy.

## Post-Model Atmospheric Adjustments

The backend does not stop at the raw model output.

After pollutant prediction, it applies lightweight atmospheric adjustment rules before AQI is calculated. These rules account for:

- strong-wind dispersion
- low-wind stagnation
- rain washout
- humidity-driven PM2.5 growth
- thermal inversion style conditions using low wind and high pressure

Examples of the current logic:

- strong wind reduces PM2.5 and PM10
- rain reduces particulates
- very high humidity increases PM2.5
- low wind plus high pressure slightly increases PM2.5 and PM10

After that, each pollutant is clamped to a realistic range.

## How AQI Is Calculated

AQI is derived from the adjusted pollutant forecast, not predicted directly.

So the actual conceptual pipeline is:

$$
\\text{Predicted AQI} = g\left(\\text{Adjusted PM2.5}, \\text{PM10}, \\text{NO2}, \\text{SO2}, \\text{CO}, \\text{O3}\right)
$$

The backend then computes:

- Indian AQI
- US AQI
- dominant pollutant
- health category
- advisory text

This is more defensible than directly regressing AQI because AQI is fundamentally a function of pollutant concentrations.

## How The Models Were Trained

The current forecasting stack is trained by `train_pollutant_models_v2.py`.

### Training Data

For each pollutant-horizon pair, the training file is built from historical pollutant and weather data.

Typical scale:

- about 25,000 to 26,000 samples per model
- 80 to 161 final features depending on pollutant and horizon

### Time-Based Train Split

Training is time-aware, not randomly shuffled.

The split is:

- first 72% for pass-1 training
- next 8% for validation and early stopping search
- last 20% for final test evaluation

This is important because forecasting should be validated on future data, not random rows.

### Two-Pass Training Strategy

Each model is trained in two stages:

1. Pass 1 trains on 72% and uses early stopping on the next 8% to estimate the right tree count.
2. Pass 2 retrains on the full first 80% using that calibrated number of iterations.

This keeps the model from overfitting while still giving the final model more usable history.

### Pollutant-Specific Logic

The training is not identical for every pollutant.

#### PM2.5, PM10, and O3

These use horizon-adaptive regularization and feature selection.

- short horizons keep more features
- long horizons prune more aggressively

Feature counts typically shrink like this:

- 1h: 140 features
- 3h: 120 features
- 6h: 100 features
- 12h: 90 features
- 24h: 80 features

#### NO2 and SO2

These skip feature selection and keep the full cross-pollutant feature set.

They also use:

- v1-style capacity
- higher learning rate
- a minimum floor of 800 trees

This was necessary because early stopping alone became too aggressive for noisy gaseous targets at longer horizons.

#### CO

CO uses a `log1p` target transform during training and `expm1` during inference.

This was the most important targeted fix in the new training pipeline.

## Current Deployed Accuracy

Based on the latest retraining results, average test $R^2$ by pollutant is:

| Pollutant | Avg Test R² |
|---|---:|
| PM2.5 | 0.641 |
| PM10 | 0.630 |
| NO2 | 0.653 |
| SO2 | 0.378 |
| CO | 0.487 |
| O3 | 0.658 |

Key observations:

- PM2.5 and PM10 are strong at short horizons and remain usable at longer ones.
- NO2 now matches the old baseline while using the improved pipeline.
- SO2 remains the hardest pollutant because of noisy spike behavior.
- CO improved the most after the log-transform change.
- O3 is one of the strongest overall performers, especially at 1h and 24h.

By horizon, the average test $R^2$ is currently strongest at 1 hour and gradually declines as the forecast horizon increases, which is expected in real-world time-series forecasting.

## Example End-To-End Forecast

Suppose the backend needs a 12-hour forecast.

It will:

1. Pull recent pollutant history and current weather.
2. Build the exact features required for each pollutant's 12-hour model.
3. Run 6 separate models: PM2.5 12h, PM10 12h, NO2 12h, SO2 12h, CO 12h, and O3 12h.
4. Convert the CO prediction back from log-space.
5. Apply atmospheric adjustment rules.
6. Compute AQI from the adjusted pollutant set.
7. Return AQI, category, dominant pollutant, bounds, and advisory.

## In One Sentence

Your current system predicts future pollutant concentrations with 30 specialized XGBoost models, corrects those predictions with simple atmospheric physics rules, and then calculates AQI from the resulting pollutant forecast.
