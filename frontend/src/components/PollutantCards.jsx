import { FlaskConical, Radio, Satellite } from 'lucide-react';

export default function PollutantCards({ pollutants, dataSource, station, lastUpdated }) {
    if (!pollutants || pollutants.length === 0) return null;

    const isGround = dataSource === 'aqicn' || dataSource === 'aqicn_ground_station';
    const timeStr = lastUpdated ? lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

    return (
        <div className="pollutants-section-new">
            <div className="ps-header">
                <FlaskConical size={16} />
                <span>POLLUTANT LEVELS</span>
                <span className="ps-source-badge">
                    {isGround ? <Radio size={12} /> : <Satellite size={12} />}
                    {isGround ? (station || 'Ground Sensor') : 'Satellite'}
                    {timeStr && <span className="ps-updated">· {timeStr}</span>}
                </span>
            </div>

            <div className="ps-grid">
                {pollutants.map((p, i) => (
                    <div
                        key={i}
                        className="ps-card"
                    >
                        {/* Left solid color accent bar */}
                        <div
                            className="ps-accent-bar"
                            style={{ background: p.color }}
                        />

                        <div className="ps-card-content">
                            <div className="ps-name">{p.name}</div>

                            <div className="ps-flex-baseline">
                                <div className="ps-value" style={{ color: p.color }}>
                                    {p.value}
                                </div>
                                <div className="ps-unit">{p.unit}</div>
                            </div>

                            <div
                                className="ps-pill"
                                style={{
                                    color: p.color,
                                    border: `1px solid ${p.color}60`
                                }}
                            >
                                {p.level.toUpperCase()}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
