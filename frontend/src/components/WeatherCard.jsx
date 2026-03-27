import { Thermometer, Droplets, Wind, Gauge, Eye, CloudRain } from 'lucide-react';

export default function WeatherCard({ weather }) {
    if (!weather) return null;

    const items = [
        {
            icon: <Thermometer size={20} />,
            label: 'Temperature',
            value: `${weather.temperature?.toFixed(1)}°C`,
            color: '#FF6B6B',
        },
        {
            icon: <Droplets size={20} />,
            label: 'Humidity',
            value: `${weather.humidity}%`,
            color: '#4FC3F7',
        },
        {
            icon: <Wind size={20} />,
            label: 'Wind Speed',
            value: `${weather.wind_speed?.toFixed(1)} m/s`,
            color: '#81C784',
        },
        {
            icon: <Gauge size={20} />,
            label: 'Pressure',
            value: `${weather.pressure} hPa`,
            color: '#CE93D8',
        },
    ];

    // Add description if available
    if (weather.description) {
        items.push({
            icon: <CloudRain size={20} />,
            label: 'Condition',
            value: weather.description,
            color: '#FFB74D',
        });
    }

    return (
        <div className="weather-card glass-card">
            <div className="section-title">
                <Eye size={14} />
                Weather Conditions
            </div>
            <div className="weather-grid">
                {items.map((item) => (
                    <div className="weather-stat" key={item.label}>
                        <div className="weather-stat-icon" style={{ color: item.color, background: `${item.color}15` }}>
                            {item.icon}
                        </div>
                        <div className="weather-stat-info">
                            <span className="weather-stat-value">{item.value}</span>
                            <span className="weather-stat-label">{item.label}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
