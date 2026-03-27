import { Clock, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { getAQIInfo } from '../utils/aqiUtils';

export default function ForecastSummary({ predictions, currentAQI, standard = 'indian', loading }) {
    const isIndian = standard === 'indian';
    const targetHours = [3, 6, 12, 24];
    const picks = [];

    if (predictions && predictions.length > 0) {
        for (const h of targetHours) {
            const pred = predictions.find((p) => p.hour === h);
            if (pred) picks.push(pred);
        }
    }

    // Get the AQI value for a prediction based on selected standard
    const getAqi = (pred) => isIndian ? pred.aqi_indian : pred.aqi_us;

    let trendIcon, trendLabel, trendColor;
    if (picks.length > 0 && currentAQI) {
        const lastAQI = getAqi(picks[picks.length - 1]);
        const change = lastAQI - currentAQI;
        if (change > 15) {
            trendIcon = <TrendingUp size={14} />;
            trendLabel = 'Worsening';
            trendColor = '#FF4444';
        } else if (change < -15) {
            trendIcon = <TrendingDown size={14} />;
            trendLabel = 'Improving';
            trendColor = '#00E400';
        } else {
            trendIcon = <Minus size={14} />;
            trendLabel = 'Stable';
            trendColor = '#FFD700';
        }
    }

    return (
        <div className="forecast-summary glass-card">
            <div className="section-title">
                <Clock size={14} />
                AQI Forecast
            </div>

            {loading ? (
                <div className="fs-loading">
                    <div className="loading-spinner" style={{ width: 28, height: 28 }} />
                </div>
            ) : picks.length > 0 ? (
                <>
                    <div className="fs-grid">
                        {picks.map((p) => {
                            const aqi = getAqi(p);
                            const info = getAQIInfo(aqi);
                            const uncertainty = p.uncertainty || 0;
                            return (
                                <div className="fs-item" key={p.hour}>
                                    <div
                                        className="fs-circle"
                                        style={{
                                            borderColor: info.color,
                                            boxShadow: `0 0 20px ${info.color}20, inset 0 0 20px ${info.color}08`,
                                        }}
                                    >
                                        <span className="fs-aqi" style={{ color: info.color }}>
                                            {Math.round(aqi)}
                                        </span>
                                        <span className="fs-cat" style={{ color: info.color }}>
                                            {info.emoji} {info.category}
                                        </span>
                                        {uncertainty > 0 && (
                                            <span className="fs-confidence" style={{ color: `${info.color}99` }}>
                                                ±{Math.round(uncertainty)}
                                            </span>
                                        )}
                                    </div>
                                    <span className="fs-time">+{p.hour}h</span>
                                    <span className="fs-time-label">{p.time_label}</span>
                                </div>
                            );
                        })}
                    </div>

                    {trendLabel && (
                        <div className="fs-trend">
                            <span
                                className="trend-badge"
                                style={{
                                    background: `${trendColor}18`,
                                    color: trendColor,
                                    border: `1px solid ${trendColor}30`,
                                }}
                            >
                                {trendIcon} {trendLabel} over 24h
                            </span>
                        </div>
                    )}
                </>
            ) : (
                <div className="fs-loading" style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                    No forecast data available
                </div>
            )}
        </div>
    );
}
