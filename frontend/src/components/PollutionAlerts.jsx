import { AlertTriangle, Wind, Radio } from 'lucide-react';

export default function PollutionAlerts({ episodes, spatialModel }) {
    if ((!episodes || episodes.length === 0) && !spatialModel) return null;

    return (
        <div className="pollution-alerts glass-card">
            {/* Episode Alerts */}
            {episodes && episodes.length > 0 && (
                <div className="pa-section">
                    <div className="section-title">
                        <AlertTriangle size={14} />
                        Pollution Alerts
                    </div>
                    <div className="pa-alert-list">
                        {episodes.map((ep, i) => (
                            <div key={i} className={`pa-alert-item pa-severity-${ep.severity}`}>
                                <span className="pa-alert-icon">{ep.icon}</span>
                                <div className="pa-alert-content">
                                    <div className="pa-alert-title">{ep.title}</div>
                                    <div className="pa-alert-detail">{ep.detail}</div>
                                </div>
                                <span className={`pa-severity-badge pa-badge-${ep.severity}`}>
                                    {ep.severity}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Spatial Model Info */}
            {spatialModel && spatialModel.stations_used > 0 && (
                <div className="pa-section">
                    <div className="section-title">
                        <Radio size={14} />
                        Spatial Model — {spatialModel.stations_used} Nearby Stations
                    </div>

                    {spatialModel.blended_aqi && (
                        <div className="pa-spatial-summary">
                            <div className="pa-spatial-stat">
                                <span className="pa-stat-label">IDW Blended AQI</span>
                                <span className="pa-stat-value">{spatialModel.blended_aqi}</span>
                            </div>
                            <div className="pa-spatial-stat">
                                <span className="pa-stat-label">Neighbor Effect</span>
                                <span className="pa-stat-value">{spatialModel.neighbor_effect}</span>
                            </div>
                        </div>
                    )}

                    {spatialModel.contributions && spatialModel.contributions.length > 0 && (
                        <div className="pa-station-list">
                            {spatialModel.contributions.map((s, i) => (
                                <div key={i} className="pa-station-row">
                                    <div className="pa-station-info">
                                        <Wind size={12} />
                                        <span className="pa-station-name">{s.station}</span>
                                    </div>
                                    <span className="pa-station-dist">{s.distance_km} km</span>
                                    <span className="pa-station-aqi">AQI {Math.round(s.aqi)}</span>
                                    <div className="pa-station-weight-bar">
                                        <div
                                            className="pa-station-weight-fill"
                                            style={{ width: `${Math.round(s.weight * 100)}%` }}
                                        />
                                    </div>
                                    <span className="pa-station-weight">{Math.round(s.weight * 100)}%</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
