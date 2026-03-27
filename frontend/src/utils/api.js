const API_BASE = '/api';

export async function fetchCurrentAQI(lat, lon) {
    const resp = await fetch(`${API_BASE}/current-aqi?lat=${lat}&lon=${lon}`);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || 'Failed to fetch current AQI');
    }
    return resp.json();
}

export async function fetchPredictions(lat, lon, hours = 6) {
    const resp = await fetch(`${API_BASE}/predict?lat=${lat}&lon=${lon}&hours=${hours}`);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || 'Failed to fetch predictions');
    }
    return resp.json();
}

export async function geocodeCity(city) {
    const resp = await fetch(`${API_BASE}/geocode?city=${encodeURIComponent(city)}`);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || 'Geocoding failed');
    }
    return resp.json();
}

export async function fetchHVI(lat, lon, profile = 'general') {
    const resp = await fetch(`${API_BASE}/hvi?lat=${lat}&lon=${lon}&profile=${encodeURIComponent(profile)}`);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || 'Failed to fetch health vulnerability data');
    }
    return resp.json();
}
