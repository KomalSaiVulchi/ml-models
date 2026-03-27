import { useState } from 'react';
import { MapPin, Search, Navigation, Loader } from 'lucide-react';
import { geocodeCity } from '../utils/api';


export default function LocationSelector({ onLocationSelect }) {
    const [mode, setMode] = useState(null); // null | 'manual' | 'detecting'
    const [cityQuery, setCityQuery] = useState('');
    const [results, setResults] = useState([]);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const getGeoErrorMessage = (err) => {
        // Browser geolocation works only in secure contexts (HTTPS or localhost).
        if (!window.isSecureContext) {
            return 'Location needs a secure context. Open this app on localhost or HTTPS, then try again.';
        }

        switch (err?.code) {
            case 1:
                return 'Location access denied. Enable location permission for this site in browser settings, then retry.';
            case 2:
                return 'Location unavailable. Your device could not provide coordinates. Check system location services and retry.';
            case 3:
                return 'Location request timed out. Check connection/GPS and retry, or enter your city below.';
            default:
                return `Could not detect location${err?.message ? `: ${err.message}` : '.'} Please enter your city below.`;
        }
    };

    const handleAutoDetect = () => {
        if (!window.isSecureContext) {
            setError('Location is blocked because this page is not in a secure context. Use localhost or HTTPS.');
            return;
        }

        if (!navigator.geolocation) {
            setError('Geolocation is not supported by your browser. Please enter your city below.');
            return;
        }

        setMode('detecting');
        setError('');

        navigator.geolocation.getCurrentPosition(
            (position) => {
                onLocationSelect({
                    lat: position.coords.latitude,
                    lon: position.coords.longitude,
                    name: 'Your Location'
                });
            },
            (err) => {
                setMode(null);
                setError(getGeoErrorMessage(err));
            },
            { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 }
        );
    };

    const handleCitySearch = async () => {
        if (!cityQuery.trim()) return;

        setLoading(true);
        setError('');
        setResults([]);

        try {
            const data = await geocodeCity(cityQuery.trim());
            if (data.results && data.results.length > 0) {
                setResults(data.results);
            } else {
                setError('No results found. Try a different city name.');
            }
        } catch (err) {
            setError(err.message || 'Failed to search. Is the backend running?');
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') handleCitySearch();
    };

    const handleResultClick = (result) => {
        onLocationSelect({
            lat: result.lat,
            lon: result.lon,
            name: result.display_name || result.name
        });
    };

    return (
        <div className="location-overlay">
            <div className="location-card glass-card">
                <div className="icon-circle">
                    {mode === 'detecting' ? (
                        <Loader size={24} color="#4f8fff" className="loading-spinner" />
                    ) : (
                        <MapPin size={24} color="#4f8fff" />
                    )}
                </div>

                <h2>Where are you?</h2>
                <p className="desc">
                    We need your location to show real-time air quality data
                </p>

                {mode === 'detecting' ? (
                    <p className="loading-text">Detecting your location...</p>
                ) : (
                    <div className="location-options">
                        <button className="btn btn-primary" onClick={handleAutoDetect}>
                            <Navigation size={18} />
                            Use My Location
                        </button>

                        <span className="divider-text">or</span>

                        <div className="city-input-group">
                            <span className="input-icon">
                                {loading
                                    ? <Loader size={15} className="loading-spinner" />
                                    : <Search size={15} />}
                            </span>
                            <input
                                type="text"
                                placeholder="Enter city name and press Enter…"
                                value={cityQuery}
                                onChange={(e) => { setCityQuery(e.target.value); setResults([]); setError(''); }}
                                onKeyDown={handleKeyDown}
                                autoFocus
                            />
                        </div>

                        {results.length > 0 && (
                            <div className="location-results">
                                {results.map((r, i) => (
                                    <button
                                        key={i}
                                        className="location-result-item"
                                        onClick={() => handleResultClick(r)}
                                    >
                                        <span className="result-pin">📍</span>
                                        <span className="result-text">
                                            <span className="result-city">{r.name}</span>
                                            {(r.state || r.country) && (
                                                <span className="result-meta">
                                                    {[r.state, r.country].filter(Boolean).join(', ')}
                                                </span>
                                            )}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        )}

                        {error && <p className="location-error">⚠️ {error}</p>}
                    </div>
                )}
            </div>
        </div>
    );
}
