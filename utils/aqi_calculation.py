"""
Proper Indian AQI Calculation using CPCB formulas
Calculates sub-indices for each pollutant and returns the maximum (dominant pollutant)
"""

def calculate_pm25_sub_index(pm25):
    """Calculate sub-index for PM2.5 (24-hour average)"""
    if pm25 <= 30:
        return pm25 * 50 / 30
    elif pm25 <= 60:
        return 50 + (pm25 - 30) * 50 / 30
    elif pm25 <= 90:
        return 100 + (pm25 - 60) * 100 / 30
    elif pm25 <= 120:
        return 200 + (pm25 - 90) * 100 / 30
    elif pm25 <= 250:
        return 300 + (pm25 - 120) * 100 / 130
    else:
        return 400 + (pm25 - 250) * 100 / 130


def calculate_pm10_sub_index(pm10):
    """Calculate sub-index for PM10 (24-hour average)"""
    if pm10 <= 50:
        return pm10
    elif pm10 <= 100:
        return 50 + (pm10 - 50)
    elif pm10 <= 250:
        return 100 + (pm10 - 100) * 100 / 150
    elif pm10 <= 350:
        return 200 + (pm10 - 250)
    elif pm10 <= 430:
        return 300 + (pm10 - 350) * 100 / 80
    else:
        return 400 + (pm10 - 430) * 100 / 80


def calculate_no2_sub_index(no2):
    """Calculate sub-index for NO2 (24-hour average)"""
    if no2 <= 40:
        return no2 * 50 / 40
    elif no2 <= 80:
        return 50 + (no2 - 40) * 50 / 40
    elif no2 <= 180:
        return 100 + (no2 - 80) * 100 / 100
    elif no2 <= 280:
        return 200 + (no2 - 180) * 100 / 100
    elif no2 <= 400:
        return 300 + (no2 - 280) * 100 / 120
    else:
        return 400 + (no2 - 400) * 100 / 120


def calculate_so2_sub_index(so2):
    """Calculate sub-index for SO2 (24-hour average)"""
    if so2 <= 40:
        return so2 * 50 / 40
    elif so2 <= 80:
        return 50 + (so2 - 40) * 50 / 40
    elif so2 <= 380:
        return 100 + (so2 - 80) * 100 / 300
    elif so2 <= 800:
        return 200 + (so2 - 380) * 100 / 420
    elif so2 <= 1600:
        return 300 + (so2 - 800) * 100 / 800
    else:
        return 400 + (so2 - 1600) * 100 / 800


def calculate_co_sub_index(co):
    """Calculate sub-index for CO (8-hour average, in mg/m3)"""
    if co <= 1.0:
        return co * 50 / 1.0
    elif co <= 2.0:
        return 50 + (co - 1.0) * 50 / 1.0
    elif co <= 10:
        return 100 + (co - 2.0) * 100 / 8
    elif co <= 17:
        return 200 + (co - 10) * 100 / 7
    elif co <= 34:
        return 300 + (co - 17) * 100 / 17
    else:
        return 400 + (co - 34) * 100 / 17


def calculate_o3_sub_index(o3):
    """Calculate sub-index for O3 (8-hour average)"""
    if o3 <= 50:
        return o3 * 50 / 50
    elif o3 <= 100:
        return 50 + (o3 - 50) * 50 / 50
    elif o3 <= 168:
        return 100 + (o3 - 100) * 100 / 68
    elif o3 <= 208:
        return 200 + (o3 - 168) * 100 / 40
    elif o3 <= 748:
        return 300 + (o3 - 208) * 100 / 540
    else:
        return 400 + (o3 - 748) * 100 / 540


def calculate_indian_aqi(pm25=None, pm10=None, no2=None, so2=None, co=None, o3=None):
    """
    Calculate Indian AQI based on CPCB guidelines.
    Returns AQI value and dominant pollutant name.
    
    Args:
        pm25: PM2.5 concentration (μg/m³)
        pm10: PM10 concentration (μg/m³)
        no2: NO2 concentration (μg/m³)
        so2: SO2 concentration (μg/m³)
        co: CO concentration (mg/m³)
        o3: O3 concentration (μg/m³)
    
    Returns:
        tuple: (aqi_value, dominant_pollutant_name)
    """
    sub_indices = {}
    
    if pm25 is not None:
        sub_indices['PM2.5'] = calculate_pm25_sub_index(pm25)
    if pm10 is not None:
        sub_indices['PM10'] = calculate_pm10_sub_index(pm10)
    if no2 is not None:
        sub_indices['NO2'] = calculate_no2_sub_index(no2)
    if so2 is not None:
        sub_indices['SO2'] = calculate_so2_sub_index(so2)
    if co is not None:
        sub_indices['CO'] = calculate_co_sub_index(co)
    if o3 is not None:
        sub_indices['O3'] = calculate_o3_sub_index(o3)
    
    if not sub_indices:
        return None, None
    
    # AQI is the maximum of all sub-indices
    dominant_pollutant = max(sub_indices, key=sub_indices.get)
    aqi = sub_indices[dominant_pollutant]
    
    return round(aqi, 1), dominant_pollutant


# ================================================================================
# US EPA AQI CALCULATION (US Standard)
# ================================================================================

def calculate_us_epa_aqi_subindex(concentration, breakpoints):
    """
    Generic function to calculate US EPA AQI sub-index using linear interpolation
    
    Args:
        concentration: Pollutant concentration
        breakpoints: List of tuples [(C_low, C_high, I_low, I_high), ...]
    
    Returns:
        AQI sub-index value
    """
    for C_low, C_high, I_low, I_high in breakpoints:
        if C_low <= concentration <= C_high:
            # Linear interpolation formula: I = [(I_high - I_low)/(C_high - C_low)] * (C - C_low) + I_low
            return ((I_high - I_low) / (C_high - C_low)) * (concentration - C_low) + I_low
    
    # If concentration exceeds all breakpoints, use the last range
    C_low, C_high, I_low, I_high = breakpoints[-1]
    return ((I_high - I_low) / (C_high - C_low)) * (concentration - C_low) + I_low


def calculate_us_pm25_sub_index(pm25):
    """Calculate US EPA sub-index for PM2.5 (24-hour average in μg/m³)"""
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 500.4, 301, 500)
    ]
    return calculate_us_epa_aqi_subindex(pm25, breakpoints)


def calculate_us_pm10_sub_index(pm10):
    """Calculate US EPA sub-index for PM10 (24-hour average in μg/m³)"""
    breakpoints = [
        (0, 54, 0, 50),
        (55, 154, 51, 100),
        (155, 254, 101, 150),
        (255, 354, 151, 200),
        (355, 424, 201, 300),
        (425, 604, 301, 500)
    ]
    return calculate_us_epa_aqi_subindex(pm10, breakpoints)


def calculate_us_no2_sub_index(no2):
    """Calculate US EPA sub-index for NO2 (1-hour average in μg/m³)"""
    # US EPA uses ppb, conversion: 1 ppb NO2 = 1.88 μg/m³ at 25°C
    no2_ppb = no2 / 1.88
    
    breakpoints = [
        (0, 53, 0, 50),
        (54, 100, 51, 100),
        (101, 360, 101, 150),
        (361, 649, 151, 200),
        (650, 1249, 201, 300),
        (1250, 2049, 301, 500)
    ]
    aqi = calculate_us_epa_aqi_subindex(no2_ppb, breakpoints)
    return aqi


def calculate_us_so2_sub_index(so2):
    """Calculate US EPA sub-index for SO2 (1-hour average in μg/m³)"""
    # US EPA uses ppb, conversion: 1 ppb SO2 = 2.62 μg/m³ at 25°C
    so2_ppb = so2 / 2.62
    
    breakpoints = [
        (0, 35, 0, 50),
        (36, 75, 51, 100),
        (76, 185, 101, 150),
        (186, 304, 151, 200),
        (305, 604, 201, 300),
        (605, 1004, 301, 500)
    ]
    aqi = calculate_us_epa_aqi_subindex(so2_ppb, breakpoints)
    return aqi


def calculate_us_co_sub_index(co):
    """Calculate US EPA sub-index for CO (8-hour average in mg/m³)"""
    # US EPA uses ppm, conversion: 1 ppm CO = 1.145 mg/m³ at 25°C
    co_ppm = co / 1.145
    
    breakpoints = [
        (0.0, 4.4, 0, 50),
        (4.5, 9.4, 51, 100),
        (9.5, 12.4, 101, 150),
        (12.5, 15.4, 151, 200),
        (15.5, 30.4, 201, 300),
        (30.5, 50.4, 301, 500)
    ]
    aqi = calculate_us_epa_aqi_subindex(co_ppm, breakpoints)
    return aqi


def calculate_us_o3_sub_index(o3):
    """Calculate US EPA sub-index for O3 (8-hour average in μg/m³)"""
    # US EPA uses ppb, conversion: 1 ppb O3 = 2.00 μg/m³ at 25°C
    o3_ppb = o3 / 2.00
    
    breakpoints = [
        (0, 54, 0, 50),
        (55, 70, 51, 100),
        (71, 85, 101, 150),
        (86, 105, 151, 200),
        (106, 200, 201, 300)
    ]
    aqi = calculate_us_epa_aqi_subindex(o3_ppb, breakpoints)
    return aqi


def calculate_us_epa_aqi(pm25=None, pm10=None, no2=None, so2=None, co=None, o3=None):
    """
    Calculate US EPA AQI.
    Returns AQI value and dominant pollutant name.
    
    Args:
        pm25: PM2.5 concentration (μg/m³)
        pm10: PM10 concentration (μg/m³)
        no2: NO2 concentration (μg/m³)
        so2: SO2 concentration (μg/m³)
        co: CO concentration (mg/m³)
        o3: O3 concentration (μg/m³)
    
    Returns:
        tuple: (aqi_value, dominant_pollutant_name)
    """
    sub_indices = {}
    
    if pm25 is not None and pm25 > 0:
        sub_indices['PM2.5'] = calculate_us_pm25_sub_index(pm25)
    if pm10 is not None and pm10 > 0:
        sub_indices['PM10'] = calculate_us_pm10_sub_index(pm10)
    if no2 is not None and no2 > 0:
        sub_indices['NO2'] = calculate_us_no2_sub_index(no2)
    if so2 is not None and so2 > 0:
        sub_indices['SO2'] = calculate_us_so2_sub_index(so2)
    if co is not None and co > 0:
        sub_indices['CO'] = calculate_us_co_sub_index(co)
    if o3 is not None and o3 > 0:
        sub_indices['O3'] = calculate_us_o3_sub_index(o3)
    
    if not sub_indices:
        return None, None
    
    # AQI is the maximum of all sub-indices
    dominant_pollutant = max(sub_indices, key=sub_indices.get)
    aqi = sub_indices[dominant_pollutant]
    
    return round(aqi, 1), dominant_pollutant


if __name__ == "__main__":
    # Test the AQI calculations
    print("Testing AQI Calculations")
    print("=" * 70)
    
    # Test data
    test_pollutants = {
        'pm25': 57.4,
        'pm10': 147.9,
        'no2': 7.4,
        'so2': 2.8,
        'co': 0.013,  # 13 μg/m³ = 0.013 mg/m³
        'o3': 15.9
    }
    
    print("\nTest Pollutant Concentrations:")
    print(f"  PM2.5: {test_pollutants['pm25']:.1f} μg/m³")
    print(f"  PM10:  {test_pollutants['pm10']:.1f} μg/m³")
    print(f"  NO2:   {test_pollutants['no2']:.1f} μg/m³")
    print(f"  SO2:   {test_pollutants['so2']:.1f} μg/m³")
    print(f"  CO:    {test_pollutants['co']:.3f} mg/m³")
    print(f"  O3:    {test_pollutants['o3']:.1f} μg/m³")
    
    # Indian CPCB AQI
    indian_aqi, indian_pollutant = calculate_indian_aqi(
        pm25=test_pollutants['pm25'],
        pm10=test_pollutants['pm10'],
        no2=test_pollutants['no2'],
        so2=test_pollutants['so2'],
        co=test_pollutants['co'],
        o3=test_pollutants['o3']
    )
    print(f"\n🇮🇳 Indian CPCB AQI:")
    print(f"  AQI: {indian_aqi}")
    print(f"  Dominant Pollutant: {indian_pollutant}")
    
    # US EPA AQI
    us_aqi, us_pollutant = calculate_us_epa_aqi(
        pm25=test_pollutants['pm25'],
        pm10=test_pollutants['pm10'],
        no2=test_pollutants['no2'],
        so2=test_pollutants['so2'],
        co=test_pollutants['co'],
        o3=test_pollutants['o3']
    )
    print(f"\n🇺🇸 US EPA AQI:")
    print(f"  AQI: {us_aqi}")
    print(f"  Dominant Pollutant: {us_pollutant}")
