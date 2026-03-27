export default function ForecastSelector({ hours, onChange }) {
    const options = [3, 6, 12, 24, 48];

    return (
        <div className="forecast-selector glass-card">
            <span className="section-title">Forecast Duration</span>
            <div className="forecast-pills">
                {options.map((h) => (
                    <button
                        key={h}
                        className={`forecast-pill ${hours === h ? 'active' : ''}`}
                        onClick={() => onChange(h)}
                    >
                        {h}h
                    </button>
                ))}
            </div>
        </div>
    );
}
