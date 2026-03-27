"""
AQI categorization and health advisory system.

Based on Central Pollution Control Board (CPCB) India standards.
"""


# AQI Categories with ranges
AQI_CATEGORIES = {
    "Good": (0, 50),
    "Satisfactory": (51, 100),
    "Moderate": (101, 200),
    "Poor": (201, 300),
    "Very Poor": (301, 400),
    "Severe": (401, 500)
}


# Color coding for visualization
AQI_COLORS = {
    "Good": "#00E400",           # Green
    "Satisfactory": "#FFFF00",   # Yellow
    "Moderate": "#FF7E00",       # Orange
    "Poor": "#FF0000",           # Red
    "Very Poor": "#8F3F97",      # Purple
    "Severe": "#7E0023"          # Maroon
}


# Health impacts for general population
HEALTH_IMPACTS = {
    "Good": "Air quality is satisfactory, and air pollution poses little or no risk.",
    "Satisfactory": "Air quality is acceptable. However, sensitive individuals may experience minor breathing discomfort.",
    "Moderate": "People with lung disease, asthma, and heart disease may experience health effects. General public is less likely to be affected.",
    "Poor": "Everyone may begin to experience health effects. Members of sensitive groups may experience more serious health effects.",
    "Very Poor": "Health alert: everyone may experience more serious health effects. Avoid outdoor activities.",
    "Severe": "Health warning: emergency conditions. Entire population is more likely to be affected. Stay indoors."
}


# Health-specific advisories
HEALTH_ADVISORIES = {
    "Asthma": {
        "Good": "Safe for outdoor activities.",
        "Satisfactory": "Minimal risk. Carry inhaler as precaution.",
        "Moderate": "Limit prolonged outdoor exertion. Keep rescue inhaler accessible.",
        "Poor": "Avoid outdoor activities. Stay indoors with air purification.",
        "Very Poor": "Severe risk. Stay indoors. Use air purifiers. Consult doctor if symptoms worsen.",
        "Severe": "Critical risk. Remain indoors. Avoid all physical activity. Seek medical attention if breathing difficulty occurs."
    },
    "Heart Disease": {
        "Good": "Safe for normal activities.",
        "Satisfactory": "Minimal risk. Light activities are safe.",
        "Moderate": "Reduce prolonged or heavy outdoor exertion.",
        "Poor": "Avoid outdoor exertion. Rest more frequently.",
        "Very Poor": "Stay indoors. Avoid all physical stress. Monitor symptoms closely.",
        "Severe": "Critical risk. Complete rest advised. Seek immediate medical care if chest pain or discomfort occurs."
    },
    "Elderly": {
        "Good": "Safe for all activities.",
        "Satisfactory": "Normal activities with minimal precaution.",
        "Moderate": "Reduce outdoor activities. Short walks only.",
        "Poor": "Stay indoors. Avoid outdoor exposure.",
        "Very Poor": "Remain indoors. Use air purifiers. Monitor health closely.",
        "Severe": "Complete indoor isolation. Seek assistance for any health concerns."
    },
    "Child": {
        "Good": "Safe for outdoor play and activities.",
        "Satisfactory": "Safe for outdoor activities with normal precautions.",
        "Moderate": "Reduce outdoor playtime. Prefer indoor activities.",
        "Poor": "Keep children indoors. No outdoor play.",
        "Very Poor": "Strict indoor stay. Close windows. Use air purifiers.",
        "Severe": "Critical: Keep children indoors. Monitor breathing. Seek medical help if coughing or breathing difficulty."
    },
    "Healthy": {
        "Good": "Enjoy outdoor activities freely.",
        "Satisfactory": "Enjoy outdoor activities with minimal precaution.",
        "Moderate": "Reduce prolonged outdoor exertion if you experience symptoms.",
        "Poor": "Reduce outdoor activities. Consider wearing mask outdoors.",
        "Very Poor": "Avoid outdoor activities. Wear N95 mask if you must go out.",
        "Severe": "Stay indoors. Avoid all outdoor exposure. Wear N95 mask if absolutely necessary to go out."
    }
}


def get_aqi_category(aqi_value):
    """
    Convert AQI numeric value to category name.
    
    Args:
        aqi_value: Numeric AQI value
    
    Returns:
        str: Category name (Good, Satisfactory, Moderate, Poor, Very Poor, Severe)
    """
    if aqi_value <= 50:
        return "Good"
    elif aqi_value <= 100:
        return "Satisfactory"
    elif aqi_value <= 200:
        return "Moderate"
    elif aqi_value <= 300:
        return "Poor"
    elif aqi_value <= 400:
        return "Very Poor"
    else:
        return "Severe"


def get_health_advisory(aqi_value, health_condition="Healthy"):
    """
    Get health-specific advisory based on AQI and user's health condition.
    
    Args:
        aqi_value: Numeric AQI value
        health_condition: One of ['Asthma', 'Heart Disease', 'Elderly', 'Child', 'Healthy']
    
    Returns:
        tuple: (category, color, health_impact, specific_advisory)
    """
    category = get_aqi_category(aqi_value)
    color = AQI_COLORS[category]
    health_impact = HEALTH_IMPACTS[category]
    
    if health_condition in HEALTH_ADVISORIES:
        specific_advisory = HEALTH_ADVISORIES[health_condition][category]
    else:
        specific_advisory = HEALTH_ADVISORIES["Healthy"][category]
    
    return category, color, health_impact, specific_advisory


if __name__ == "__main__":
    # Test the module
    test_aqis = [45, 85, 150, 250, 350, 450]
    
    print("AQI Category Testing:")
    print("=" * 80)
    
    for aqi in test_aqis:
        cat, col, impact, _ = get_health_advisory(aqi, "Healthy")
        print(f"AQI {aqi:3d} → {cat:15s} | {impact}")
    
    print("\n" + "=" * 80)
    print("Health-specific advisory for AQI=250 (Poor):")
    print("=" * 80)
    
    for condition in ["Healthy", "Asthma", "Heart Disease", "Elderly", "Child"]:
        _, _, _, advisory = get_health_advisory(250, condition)
        print(f"\n{condition:15s}: {advisory}")
