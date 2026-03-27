import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { getAQIInfo, getAQIColor } from '../utils/aqiUtils';

export default function AQIDashboard({ data, currentAQI, predictions = [], standard = 'indian', setAqiStandard, loading }) {
    const [isAqiDropdownOpen, setIsAqiDropdownOpen] = useState(false);
    const isIndian = standard === 'indian';
    const aqiValue = isIndian ? data.aqi_indian : data.aqi_us;
    const info = getAQIInfo(aqiValue, standard);

    // Select correct character based on AQI severity
    // Select correct character based on AQI severity
    let characterImage = '/char_moderate.png';
    if (aqiValue <= 50) characterImage = '/char_good.png';
    else if (aqiValue <= 100) characterImage = '/char_moderate.png';
    else if (aqiValue <= 200) characterImage = '/char_poor.png';
    else if (aqiValue <= 300) characterImage = '/char_unhealthy.png';
    else characterImage = '/char_severe.png';

    // Parse weather data from standard /api/predict or fetch current
    const weather = {
        temp: data.weather?.temperature ?? 0,
        condition: data.weather?.description ?? 'N/A',
        humidity: data.weather?.humidity ?? 0,
        wind: data.weather?.wind_speed ? (data.weather.wind_speed * 3.6).toFixed(1) : 0,
        uv: data.weather?.uv_index ?? 0
    };

    return (
        <div className="aqi-hero-card" style={{
            '--theme-grad-top': info.theme.gradientTop,
            '--theme-grad-mid': info.theme.gradientMid,
            '--theme-grad-bot': info.theme.gradientBottom,
            '--theme-sun': info.theme.sunColor,
            '--theme-sun-glow': info.theme.sunGlow,
            '--theme-cloud': info.theme.cloudColor,
            '--theme-cloud-op': info.theme.cloudOpacity,
            '--theme-city': info.theme.cityscapeColor,
        }}>
            {/* Background elements (Pure CSS) */}
            <div className="bg-clouds-sun"></div>
            <div className="bg-cityscape"></div>


            <div className="aqi-hero-content">
                {/* Header */}
                <div className="aqi-hero-header">
                    <div className="aqi-hero-titles">
                        <h2>Real-time Air Quality Index (AQI)</h2>
                        <h3 className="location-title" style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                            <span style={{ color: '#ffffff', textDecoration: 'underline' }}>{data.city || 'Delhi, India'}</span>
                        </h3>
                        <div className="aqi-hero-meta">
                            <span>Last Updated: {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} (Local Time)</span>
                            <span className="meta-divider">|</span>
                            <span>{data.data_source === 'cpcb_ground_station' ? '🏛️ CPCB Station' : data.data_source === 'aqicn_ground_station' ? '📡 Ground Station' : '🛰️ Satellite Estimate'}: {data.station ? `${data.station}` : 'N/A'}{data.station_distance_km != null ? ` (${data.station_distance_km} km)` : ''}</span>
                        </div>
                    </div>
                    <div className="aqi-hero-actions" style={{ display: 'flex', alignItems: 'flex-start', gap: '20px' }}>

                        <div className="aqi-standard-selector" style={{ position: 'relative' }}>
                            <div style={{ fontSize: '0.75rem', marginBottom: '6px', color: 'rgba(255,255,255,0.7)', fontWeight: '500' }}>AQI Standard</div>
                            <button
                                className="action-btn"
                                onClick={() => setIsAqiDropdownOpen(!isAqiDropdownOpen)}
                                style={{ padding: '6px 12px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)' }}
                            >
                                <span style={{ fontSize: '1.2rem', lineHeight: 1 }}>{standard === 'indian' ? '🇮🇳' : '🇺🇸'}</span>
                                <span style={{ fontWeight: 600 }}>{standard === 'indian' ? 'AQI' : 'AQI-US'}</span>
                                {isAqiDropdownOpen ? <ChevronUp size={14} color="#4da6ff" /> : <ChevronDown size={14} color="#4da6ff" />}
                            </button>

                            {isAqiDropdownOpen && (
                                <div className="aqi-dropdown-menu" style={{
                                    position: 'absolute',
                                    top: '100%',
                                    marginTop: '8px',
                                    left: 0,
                                    background: '#1c1c1f',
                                    border: '1px solid rgba(255,255,255,0.1)',
                                    borderRadius: '12px',
                                    padding: '8px',
                                    minWidth: '140px',
                                    zIndex: 20,
                                    boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
                                }}>
                                    <div
                                        className="dropdown-item"
                                        onClick={() => { if (setAqiStandard) setAqiStandard('indian'); setIsAqiDropdownOpen(false); }}
                                        style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 12px', cursor: 'pointer', borderRadius: '8px', transition: 'background 0.2s', background: standard === 'indian' ? 'rgba(255,255,255,0.1)' : 'transparent' }}
                                    >
                                        <span style={{ fontSize: '1.2rem', lineHeight: 1 }}>🇮🇳</span>
                                        <span style={{ fontWeight: 500 }}>AQI</span>
                                    </div>
                                    <div style={{ height: '1px', background: 'rgba(255,255,255,0.05)', margin: '4px 0' }}></div>
                                    <div
                                        className="dropdown-item"
                                        onClick={() => { if (setAqiStandard) setAqiStandard('us'); setIsAqiDropdownOpen(false); }}
                                        style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 12px', cursor: 'pointer', borderRadius: '8px', transition: 'background 0.2s', background: standard === 'us' ? 'rgba(255,255,255,0.1)' : 'transparent' }}
                                    >
                                        <span style={{ fontSize: '1.2rem', lineHeight: 1 }}>🇺🇸</span>
                                        <span style={{ fontWeight: 500 }}>AQI-US</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Main 3-Column Layout */}
                <div className="aqi-hero-grid">

                    {/* Left: AQI Metrics */}
                    <div className="hero-col-left">
                        <div className="live-badge">
                            <span className="live-dot" style={{ backgroundColor: info.color }}></span> {data.data_source === 'aqicn_ground_station' ? 'Measured AQI' : 'Live AQI'}
                        </div>

                        <div className="aqi-main-display">
                            <div className="aqi-number" style={{ color: info.color }}>
                                {Math.round(aqiValue)}
                            </div>
                            <div className="aqi-category-block" style={{ backgroundColor: `${info.color}15`, borderColor: `${info.color}40` }}>
                                <span className="cat-label">Air Quality is</span>
                                <span className="cat-value" style={{ color: info.color }}>{info.category}</span>
                            </div>
                        </div>

                        <div className="hero-pollutants">
                            <div className="hp-item">
                                <span className="hp-name">PM2.5:</span> {Math.round(data.pollutants?.find(p => p.name === 'PM2.5')?.value ?? 0)} <span className="hp-unit">µg/m³</span>
                            </div>
                            <div className="hp-item">
                                <span className="hp-name">PM10:</span> {Math.round(data.pollutants?.find(p => p.name === 'PM10')?.value ?? 0)} <span className="hp-unit">µg/m³</span>
                            </div>
                        </div>

                        {/* AQI Scale Bar */}
                        <div className="aqi-scale-container">
                            <div className="aqi-scale-labels">
                                {isIndian ? (
                                    <>
                                        <span>Good</span>
                                        <span>Satisfactory</span>
                                        <span>Moderate</span>
                                        <span>Poor</span>
                                        <span>Very Poor</span>
                                        <span>Severe</span>
                                    </>
                                ) : (
                                    <>
                                        <span>Good</span>
                                        <span>Moderate</span>
                                        <span>USG</span>
                                        <span>Unhealthy</span>
                                        <span>V. Unhealthy</span>
                                        <span>Hazardous</span>
                                    </>
                                )}
                            </div>
                            <div className="aqi-scale-bar-track">
                                <div
                                    className="aqi-scale-indicator"
                                    style={{ left: `${Math.min(100, (aqiValue / 500) * 100)}%`, backgroundColor: info.color }}
                                />
                            </div>
                            <div className="aqi-scale-ticks">
                                {isIndian ? (
                                    <><span>0</span><span>50</span><span>100</span><span>200</span><span>300</span><span>400</span><span>500</span></>
                                ) : (
                                    <><span>0</span><span>50</span><span>100</span><span>150</span><span>200</span><span>300</span><span>500</span></>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Center: Character Illustration */}
                    <div className="hero-col-center" style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-end', height: '100%', marginRight: '60px' }}>
                        <img src={characterImage} alt="AQI Character" className="hero-character" />
                    </div>

                    {/* Right: AQI Forecast Sub-card replacing Weather */}
                    <div className="hero-col-right" style={{ display: 'flex', flexDirection: 'column', alignSelf: 'stretch', justifyContent: 'center' }}>
                        <div className="aqi-forecast-card glass-card" style={{ padding: '28px', minWidth: '420px', display: 'flex', flexDirection: 'column', background: 'rgba(255,255,255,0.06)', borderRadius: '24px', boxShadow: '0 8px 32px rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.12)' }}>

                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                                <div style={{ fontSize: '1rem', fontWeight: '600', color: 'rgba(255,255,255,0.95)', letterSpacing: '0.5px' }}>
                                    AQI Forecast
                                </div>
                                <button className="wgc-expand" style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', transition: '0.2s' }}>↗</button>
                            </div>

                            <div style={{ height: '1px', background: 'rgba(255,255,255,0.15)', margin: '0 0 24px 0' }}></div>

                            <div className="forecast-grid" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flex: 1 }}>

                                {/* If predictions array is empty, show loading or fallback */}
                                {predictions.length === 0 && (
                                    <div style={{ padding: '20px 0', opacity: 0.6, fontSize: '0.9rem' }}>Loading predictions...</div>
                                )}

                                {/* Filter strictly 3, 6, 12, 24, 48 hr jumps to map the 5 column layout */}
                                {predictions.filter(p => [3, 6, 12, 24, 48].includes(p.hour)).map((p) => {
                                    const val = isIndian ? p.aqi_indian : p.aqi_us;
                                    const pColor = getAQIColor(val, standard);

                                    return (
                                        <div key={p.hour} className="forecast-item" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                                            <div style={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.85)', fontWeight: 600 }}>
                                                +{p.hour}h
                                            </div>
                                            <div style={{
                                                width: '12px', height: '12px', borderRadius: '50%',
                                                backgroundColor: pColor,
                                                boxShadow: `0 0 10px ${pColor}99`
                                            }}></div>
                                            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#fff' }}>
                                                {Math.round(val)}
                                            </div>
                                        </div>
                                    )
                                })}

                            </div>

                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}
