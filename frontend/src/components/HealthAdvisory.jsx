import { Shield } from 'lucide-react';
import { Thermometer, Droplets, Wind, Gauge } from 'lucide-react';

export default function HealthAdvisory({ advisory, weather }) {
    return (
        <div className="health-advisory glass-card">
            <div className="section-title">
                <Shield size={14} />
                Health Advisory
            </div>
            <p className="advisory-text">{advisory}</p>

            {weather && (
                <div className="weather-row">
                    {weather.temperature != null && (
                        <span className="weather-item">
                            <Thermometer /> {weather.temperature.toFixed(1)}°C
                        </span>
                    )}
                    {weather.humidity != null && (
                        <span className="weather-item">
                            <Droplets /> {weather.humidity}% Humidity
                        </span>
                    )}
                    {weather.wind_speed != null && (
                        <span className="weather-item">
                            <Wind /> {weather.wind_speed.toFixed(1)} m/s Wind
                        </span>
                    )}
                    {weather.pressure != null && (
                        <span className="weather-item">
                            <Gauge /> {weather.pressure} hPa
                        </span>
                    )}
                    {weather.description && (
                        <span className="weather-item">
                            ☁️ {weather.description}
                        </span>
                    )}
                </div>
            )}
        </div>
    );
}
