"""
Utility modules for AQI prediction system.
"""

from .aqi_categories import (
    AQI_CATEGORIES,
    AQI_COLORS,
    HEALTH_IMPACTS,
    HEALTH_ADVISORIES,
    get_aqi_category,
    get_health_advisory
)

from .helpers import (
    fetch_past_48_hours_aqi,
    generate_synthetic_aqi_sequence,
    prepare_input_for_model,
    load_model_and_predict,
    calculate_metrics,
    format_datetime
)

from .llm_integration import (
    generate_health_advisory_with_llm,
    generate_fallback_advisory
)

__all__ = [
    'AQI_CATEGORIES',
    'AQI_COLORS',
    'HEALTH_IMPACTS',
    'HEALTH_ADVISORIES',
    'get_aqi_category',
    'get_health_advisory',
    'fetch_past_48_hours_aqi',
    'generate_synthetic_aqi_sequence',
    'prepare_input_for_model',
    'load_model_and_predict',
    'calculate_metrics',
    'format_datetime',
    'generate_health_advisory_with_llm',
    'generate_fallback_advisory'
]
