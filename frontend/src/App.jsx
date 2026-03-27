import { useState, useEffect, useCallback } from 'react';
import { MapPin, RefreshCw } from 'lucide-react';
import LocationSelector from './components/LocationSelector';
import AQIDashboard from './components/AQIDashboard';
import PredictionChart from './components/PredictionChart';
import WeatherParameters from './components/WeatherParameters';
import PollutantCards from './components/PollutantCards';
import HealthVulnerability from './components/HealthVulnerability';
import PollutionAlerts from './components/PollutionAlerts';
import { fetchCurrentAQI, fetchPredictions } from './utils/api';

export default function App() {
  const [location, setLocation] = useState(null);
  const [currentData, setCurrentData] = useState(null);
  const [predictionData, setPredictionData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [aqiStandard, setAqiStandard] = useState('indian');
  const [lastUpdated, setLastUpdated] = useState(null);

  // Fetch all data when location changes
  const loadData = useCallback(async (loc, silent = false) => {
    if (!silent) setLoading(true);
    setError('');

    try {
      const [current, preds] = await Promise.all([
        fetchCurrentAQI(loc.lat, loc.lon),
        fetchPredictions(loc.lat, loc.lon, 48)
      ]);
      setCurrentData(current);
      setPredictionData(preds);
      setLastUpdated(new Date());
    } catch (err) {
      if (!silent) setError(err.message || 'Failed to load data. Is the backend running on port 5001?');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  // Load data when location is set
  useEffect(() => {
    if (location) {
      loadData(location);
    }
  }, [location, loadData]);

  // Auto-refresh every 10 minutes
  useEffect(() => {
    if (!location) return;
    const interval = setInterval(() => loadData(location, true), 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, [location, loadData]);

  // Handle location selection
  const handleLocationSelect = (loc) => {
    setLocation(loc);
  };

  // Change location
  const handleChangeLocation = () => {
    setLocation(null);
    setCurrentData(null);
    setPredictionData(null);
    setError('');
  };

  // Refresh data
  const handleRefresh = () => {
    if (location) loadData(location);
  };

  // Show location selector if no location set
  if (!location) {
    return <LocationSelector onLocationSelect={handleLocationSelect} />;
  }

  // Loading state
  if (loading) {
    return (
      <div className="loading-fullscreen">
        <div className="loading-wind-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#4f8fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9.59 4.59A2 2 0 1 1 11 8H2" />
            <path d="M12.59 19.41A2 2 0 1 0 14 16H2" />
            <path d="M17.73 7.73A2.5 2.5 0 1 1 19.5 12H2" />
          </svg>
        </div>
        <h2 className="loading-title">Analyzing Air Quality</h2>
        <p className="loading-subtitle">Fetching real-time data and running ML predictions...</p>
        <div className="loading-ring" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="app-container">
        <div className="error-container glass-card" style={{ padding: '48px 32px' }}>
          <div className="error-icon">⚠️</div>
          <h2>Something went wrong</h2>
          <p>{error}</p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <button className="btn btn-primary" onClick={handleRefresh}>
              <RefreshCw size={16} /> Try Again
            </button>
            <button className="btn btn-ghost" onClick={handleChangeLocation}>
              <MapPin size={16} /> Change Location
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1>Air Pulse</h1>
        <p className="subtitle">Real-time AQI monitoring & ML predictions</p>
        <div className="header-controls">
          <button className="location-badge" onClick={handleChangeLocation}>
            <MapPin size={14} />
            {location.name}
          </button>
          <button className="refresh-badge" onClick={handleRefresh} title="Refresh data">
            <RefreshCw size={14} />
          </button>
        </div>
      </header>

      {/* Dashboard grid */}
      <div className="dashboard-grid">

        {/* Row 1: AQI Hero Card — stands alone, full-width */}
        {currentData && (
          <AQIDashboard
            data={{ ...currentData, city: location?.name }}
            currentAQI={aqiStandard === 'indian' ? predictionData?.current_aqi_indian : predictionData?.current_aqi_us}
            predictions={predictionData?.predictions || []}
            standard={aqiStandard}
            setAqiStandard={setAqiStandard}
            loading={loading}
          />
        )}

        {/* Unified canvas — all data sections live on one connected surface */}
        <div className="dashboard-canvas">

          {/* Forecast Chart */}
          {predictionData?.predictions?.length > 0 && (
            <PredictionChart
              predictions={predictionData.predictions}
              currentAQI={predictionData.current_aqi_indian}
              currentAQI_US={predictionData.current_aqi_us}
              standard={aqiStandard}
            />
          )}

          {/* Pollution Alerts & Spatial Analysis */}
          {predictionData && (predictionData.episodes?.length > 0 || predictionData.spatial_model) && (
            <PollutionAlerts
              episodes={predictionData.episodes}
              spatialModel={predictionData.spatial_model}
            />
          )}

          {/* Weather Parameters */}
          {currentData && currentData.weather && (
            <WeatherParameters weather={currentData.weather} locationName={location.name} />
          )}

          {/* Pollutant Cards */}
          {currentData && (
            <PollutantCards
              pollutants={currentData.pollutants}
              dataSource={currentData.data_source}
              station={currentData.station}
              lastUpdated={lastUpdated}
            />
          )}

          {/* Health Vulnerability Index + Advisories */}
          {location && <HealthVulnerability location={location} />}

        </div>
      </div>
    </div>
  );
}
