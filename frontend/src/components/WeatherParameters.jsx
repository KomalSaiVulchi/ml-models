import React, { useState, useRef } from 'react';
import { createPortal } from 'react-dom';

// Descriptions for each info button
const INFO_TEXT = {
    temperature: 'Air temperature measured in °C at ground level. Affects pollutant dispersion — hot air rises, lifting pollutants, while cold air traps them near the surface.',
    humidity: 'Percentage of water vapour in the air. High humidity (>70%) can trap fine particles like PM2.5 near the surface and worsen air quality.',
    wind_speed: 'Speed of horizontal air movement in km/h. Higher wind speeds disperse pollutants faster; calm winds (< 10 km/h) allow pollution build-up.',
    wind_gust: 'Sudden short bursts of high-speed wind (m/s). Gusts can temporarily spike or clear local pollutant concentrations.',
    wind_direction: 'The compass direction the wind is blowing from, in degrees. Wind direction determines which areas receive transported pollutants.',
    cloud_cover: 'Percentage of sky covered by clouds (0–100%). Heavy cloud cover can trap ozone and particulate matter under an inversion layer.',
    visibility: 'Maximum distance (km) at which objects can be clearly seen. Low visibility (<5 km) often indicates high PM2.5 or fog.',
    precipitation: 'Amount of rainfall or snowfall in the past hour (mm). Rain washes out particles and SO₂ from the air, temporarily improving AQI.',
    pressure: 'Atmospheric pressure in millibars (mb). Low pressure (< 1005 mb) often causes poor air quality by trapping pollutants near ground level.',
    uv_index: 'Ultraviolet radiation intensity (0–11+). High UV drives the formation of ground-level ozone (O₃), a key AQI pollutant.',
};

// Tooltip rendered into document.body via portal — escapes all overflow/stacking contexts
function InfoIcon({ id }) {
    const [pos, setPos] = useState(null);
    const iconRef = useRef(null);

    const handleMouseEnter = () => {
        if (iconRef.current) {
            const r = iconRef.current.getBoundingClientRect();
            setPos({ top: r.bottom + window.scrollY + 10, left: r.left + window.scrollX + r.width / 2 });
        }
    };

    const tooltip = pos && createPortal(
        <div style={{
            position: 'absolute',
            top: pos.top,
            left: pos.left,
            transform: 'translateX(-50%)',
            zIndex: 99999,
            width: '240px',
            background: '#1a2035',
            border: '1px solid rgba(79,143,255,0.4)',
            borderRadius: '10px',
            padding: '12px 14px',
            boxShadow: '0 12px 40px rgba(0,0,0,0.7)',
            fontSize: '0.78rem',
            color: '#c8d0e8',
            lineHeight: '1.6',
            fontWeight: 400,
            pointerEvents: 'none',
        }}>
            {/* Arrow */}
            <div style={{
                position: 'absolute', top: '-6px', left: '50%', transform: 'translateX(-50%)',
                width: 0, height: 0,
                borderLeft: '6px solid transparent', borderRight: '6px solid transparent',
                borderBottom: '6px solid rgba(79,143,255,0.4)',
            }} />
            <div style={{
                position: 'absolute', top: '-5px', left: '50%', transform: 'translateX(-50%)',
                width: 0, height: 0,
                borderLeft: '5px solid transparent', borderRight: '5px solid transparent',
                borderBottom: '5px solid #1a2035',
            }} />
            {INFO_TEXT[id] || 'No information available.'}
        </div>,
        document.body
    );

    return (
        <span
            ref={iconRef}
            className="wg-info-icon-wrap"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={() => setPos(null)}
        >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                stroke={pos ? '#4f8fff' : 'rgba(255,255,255,0.4)'}
                strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                className="wg-info-svg"
                style={{ transition: 'stroke 0.2s' }}>
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            {tooltip}
        </span>
    );
}

// Wind vector icon
const WindGustIcon = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2" />
        <circle cx="18" cy="16" r="3" fill="#d97706" stroke="#b45309" strokeWidth="1" />
        <path d="M17 19l2-2" stroke="#b45309" />
    </svg>
);

// Needle Direction Arrow
const DirArrow = ({ deg }) => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="#3b82f6" style={{ transform: `rotate(${deg}deg)` }}>
        <path d="M12 2L4 20l8-4 8 4Z" />
    </svg>
);

export default function WeatherParameters({ weather, locationName }) {
    if (!weather) return null;

    const {
        temperature = 0, humidity = 0, pressure = 0, description = '',
        wind_speed = 0, wind_gust = 0, wind_deg = 0,
        visibility = 0, cloud_cover = 0, precipitation = 0, uv_index = 0
    } = weather;

    const windSpeedKm = Math.round(wind_speed * 3.6);

    const getWindDirection = (deg) => {
        const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
        return directions[Math.round(deg / 45) % 8];
    };

    const getUVRisk = (uvi) => {
        if (uvi <= 2) return { text: 'Low', color: '#facc15', bg: 'rgba(250, 204, 21, 0.2)' }; // Yellow
        if (uvi <= 5) return { text: 'Moderate', color: '#fb923c', bg: 'rgba(251, 146, 60, 0.2)' }; // Orange
        if (uvi <= 7) return { text: 'High', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.2)' }; // Red
        if (uvi <= 10) return { text: 'Very High', color: '#db2777', bg: 'rgba(219, 39, 119, 0.2)' }; // Pink
        return { text: 'Extreme', color: '#9333ea', bg: 'rgba(147, 51, 234, 0.2)' }; // Purple
    };

    const uvInfo = getUVRisk(uv_index);

    // Hardcode layout scale ticks for the pressure dial to match the visual
    const tickMarks = [];
    for (let i = -6; i <= 6; i++) {
        const angle = i * 15; // -90 to +90 sweep
        const isMajor = i % 2 === 0;
        const val = 1010 + i; // Assuming 1010 is center scale
        tickMarks.push({ angle, isMajor, val });
    }

    return (
        <div className="weather-grid-wrapper">
            <h2 className="wg-title">
                <span style={{ color: '#4da6ff' }}>{locationName?.split(',')[0]}</span> Weather Parameters
            </h2>

            <div className="wg-grid">

                {/* 0. TEMPERATURE & HUMIDITY */}
                <div className="wg-col-vertical">
                    <div className="wg-card">
                        <div className="wg-card-content">
                            <div className="wg-label">Temperature <InfoIcon id="temperature" /></div>
                            <div className="wg-flex-row" style={{ marginTop: '16px', alignItems: 'center' }}>
                                <div style={{ flex: 1, position: 'relative', height: '90px' }}>
                                    <svg viewBox="0 0 80 100" style={{ width: '70px', height: '90px' }}>
                                        {/* Thermometer body */}
                                        <rect x="30" y="8" width="20" height="62" rx="10" fill="none" stroke="#94a3b8" strokeWidth="2" />
                                        {/* Mercury fill */}
                                        <rect x="33" y={70 - Math.min(55, Math.max(5, temperature * 1.2))} width="14" rx="7"
                                            height={Math.min(55, Math.max(5, temperature * 1.2))}
                                            fill={temperature > 35 ? '#ef4444' : temperature > 25 ? '#f97316' : temperature > 15 ? '#facc15' : '#3b82f6'} />
                                        {/* Bulb */}
                                        <circle cx="40" cy="80" r="14"
                                            fill={temperature > 35 ? '#ef4444' : temperature > 25 ? '#f97316' : temperature > 15 ? '#facc15' : '#3b82f6'} />
                                    </svg>
                                </div>
                                <div style={{ flex: 1, textAlign: 'right' }}>
                                    <span className="wg-val-xl">{Math.round(temperature * 10) / 10}</span>
                                    <span className="wg-unit" style={{ display: 'block', fontSize: '1rem' }}>°C</span>
                                </div>
                            </div>
                        </div>
                        <div className="wg-footer">
                            {temperature > 35 ? 'Hot conditions — stay hydrated' :
                             temperature > 25 ? 'Warm & comfortable' :
                             temperature > 15 ? 'Pleasant temperature' :
                             'Cool conditions — dress warmly'}
                        </div>
                    </div>

                    <div className="wg-card">
                        <div className="wg-card-content">
                            <div className="wg-label">Humidity <InfoIcon id="humidity" /></div>
                            <div className="wg-flex-row" style={{ marginTop: '16px', alignItems: 'center' }}>
                                <div style={{ position: 'relative', width: '80px', height: '80px', flexShrink: 0 }}>
                                    <svg viewBox="0 0 100 100" width="80" height="80">
                                        <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" />
                                        <circle cx="50" cy="50" r="42" fill="none"
                                            stroke={humidity > 80 ? '#3b82f6' : humidity > 50 ? '#22d3ee' : '#facc15'}
                                            strokeWidth="10" strokeLinecap="round"
                                            strokeDasharray={`${humidity * 2.64} 264`}
                                            transform="rotate(-90 50 50)" />
                                    </svg>
                                </div>
                                <div style={{ flex: 1, textAlign: 'right' }}>
                                    <span className="wg-val-xl">{humidity}</span>
                                    <span className="wg-unit" style={{ display: 'block', fontSize: '1rem' }}>%</span>
                                    <div className="wg-pill-blue" style={{ marginTop: '6px', display: 'inline-block' }}>
                                        {humidity > 80 ? 'Very Humid' : humidity > 60 ? 'Humid' : humidity > 40 ? 'Comfortable' : 'Dry'}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="wg-footer">
                            Current humidity is {humidity}%{humidity > 70 ? ' — may feel muggy' : ''}
                        </div>
                    </div>
                </div>

                {/* 1. WIND DYNAMICS */}
                <div className="wg-card wg-tall">
                    <div className="wg-card-content" style={{ padding: '0px' }}>

                        <div style={{ height: '200px', position: 'relative', overflow: 'hidden' }}>
                            {/* Inline SVG Windmills targeting the screenshot look */}
                            <svg viewBox="0 0 300 200" width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0 }}>
                                {/* Base/Pole lines */}
                                <g stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round">
                                    {/* Left */}
                                    <line x1="90" y1="80" x2="90" y2="150" />
                                    <path d="M80 150 Q90 145 100 150" fill="none" />
                                    {/* Center */}
                                    <line x1="150" y1="90" x2="150" y2="150" />
                                    <path d="M140 150 Q150 145 160 150" fill="none" />
                                    {/* Right */}
                                    <line x1="200" y1="100" x2="200" y2="150" />
                                    <path d="M192 150 Q200 145 208 150" fill="none" />
                                </g>

                                {/* Rotors */}
                                <g className="wg-spin" style={{ transformOrigin: '90px 80px', animationDuration: '4s' }}>
                                    <path d="M90 80 L80 50 A5 5 0 0 1 100 50 Z" fill="#f8fafc" />
                                    <path d="M90 80 L60 95 A5 5 0 0 0 65 105 Z" fill="#f8fafc" />
                                    <path d="M90 80 L115 105 A5 5 0 0 0 120 95 Z" fill="#f8fafc" />
                                    <circle cx="90" cy="80" r="3" fill="#84cc16" />
                                </g>

                                <g className="wg-spin" style={{ transformOrigin: '150px 90px', animationDuration: '3s' }}>
                                    <path d="M150 90 L140 60 A5 5 0 0 1 160 60 Z" fill="#f8fafc" opacity="0.9" />
                                    <path d="M150 90 L120 105 A5 5 0 0 0 125 115 Z" fill="#f8fafc" opacity="0.9" />
                                    <path d="M150 90 L175 115 A5 5 0 0 0 180 105 Z" fill="#f8fafc" opacity="0.9" />
                                    <circle cx="150" cy="90" r="2.5" fill="#84cc16" />
                                </g>

                                <g className="wg-spin" style={{ transformOrigin: '200px 100px', animationDuration: '2.5s' }}>
                                    <path d="M200 100 L192 75 A4 4 0 0 1 208 75 Z" fill="#f8fafc" opacity="0.8" />
                                    <path d="M200 100 L175 112 A4 4 0 0 0 180 120 Z" fill="#f8fafc" opacity="0.8" />
                                    <path d="M200 100 L220 120 A4 4 0 0 0 225 112 Z" fill="#f8fafc" opacity="0.8" />
                                    <circle cx="200" cy="100" r="2" fill="#84cc16" />
                                </g>
                            </svg>
                        </div>

                        <div style={{ padding: '0 24px' }}>
                            <div className="wg-label">Wind Speed <InfoIcon id="wind_speed" /></div>
                            <div className="wg-flex-row" style={{ marginTop: '8px', marginBottom: '40px' }}>
                                <div>
                                    <span className="wg-val-lg">{windSpeedKm}</span>
                                    <span className="wg-unit">km/h</span>
                                </div>
                                <div className="wg-pill-blue">
                                    {windSpeedKm < 10 ? 'Light breeze' : windSpeedKm < 30 ? 'Moderate breeze' : 'Strong wind'}
                                </div>
                            </div>

                            <div className="wg-divider"></div>

                            <div className="wg-flex-row" style={{ marginTop: '20px', alignItems: 'flex-start' }}>
                                <div style={{ flex: 1 }}>
                                    <div className="wg-label">Gust Speed <InfoIcon id="wind_gust" /></div>
                                    <div className="wg-flex-row" style={{ marginTop: '8px', alignItems: 'center', gap: '8px' }}>
                                        <WindGustIcon />
                                    </div>
                                    <div style={{ marginTop: '12px' }}>
                                        <span className="wg-val-md">{wind_gust}</span>
                                        <span className="wg-unit">m/s</span>
                                    </div>
                                </div>
                                <div style={{ flex: 1, paddingLeft: '20px' }}>
                                    <div className="wg-label">Direction <InfoIcon id="wind_direction" /></div>
                                    <div style={{ marginTop: '12px', marginBottom: '12px' }}>
                                        <DirArrow deg={wind_deg} />
                                    </div>
                                    <div>
                                        <span className="wg-val-md">{wind_deg}° {getWindDirection(wind_deg)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="wg-footer">
                        Current wind speed is a {windSpeedKm} km/h, with gusts at {wind_gust}
                    </div>
                </div>

                <div className="wg-col-vertical">

                    {/* 2. ATMOSPHERIC / CLOUDS */}
                    <div className="wg-card">
                        <div className="wg-card-content" style={{ padding: 0 }}>
                                <div className="wg-cloud-header-box">
                                    {/* Row of fluffy moving clouds */}
                                    <div className="wg-moving-cloud wg-mc-1">
                                        <svg viewBox="0 0 100 60" fill="none"><path d="M90 45H15c-5 0-9-3.6-9-8s3-7.2 7-7.8c.5-6.5 6-11.7 13-11.7 3.5 0 6.7 1.3 9 3.4C37.5 15.5 43 12 50 12c10 0 18 7 19.5 16.2C72 29 74 31.5 74 34.5c0 .5 0 1-.1 1.5H90c4 0 7 3 7 4.5S94 45 90 45z" fill="#fff"/><path d="M85 42H12c-4 0-7-3-7-6.5s2.5-6 5.8-6.5c.4-5.5 5-10 11-10 3 0 5.6 1.1 7.5 2.8C31 18 36 15 42 15c8.5 0 15.5 6 16.8 13.8C61 29.5 63 31.8 63 35c0 .4 0 .8-.1 1.2H85c3.5 0 6.5 2.5 6.5 3.8S88.5 42 85 42z" fill="rgba(255,255,255,0.6)"/></svg>
                                    </div>
                                    <div className="wg-moving-cloud wg-mc-2">
                                        <svg viewBox="0 0 100 60" fill="none"><path d="M90 45H15c-5 0-9-3.6-9-8s3-7.2 7-7.8c.5-6.5 6-11.7 13-11.7 3.5 0 6.7 1.3 9 3.4C37.5 15.5 43 12 50 12c10 0 18 7 19.5 16.2C72 29 74 31.5 74 34.5c0 .5 0 1-.1 1.5H90c4 0 7 3 7 4.5S94 45 90 45z" fill="#fff"/></svg>
                                    </div>
                                    <div className="wg-moving-cloud wg-mc-3">
                                        <svg viewBox="0 0 100 60" fill="none"><path d="M85 42H12c-4 0-7-3-7-6.5s2.5-6 5.8-6.5c.4-5.5 5-10 11-10 3 0 5.6 1.1 7.5 2.8C31 18 36 15 42 15c8.5 0 15.5 6 16.8 13.8C61 29.5 63 31.8 63 35c0 .4 0 .8-.1 1.2H85c3.5 0 6.5 2.5 6.5 3.8S88.5 42 85 42z" fill="#fff"/></svg>
                                    </div>
                                    <div className="wg-moving-cloud wg-mc-4">
                                        <svg viewBox="0 0 100 60" fill="none"><path d="M90 45H15c-5 0-9-3.6-9-8s3-7.2 7-7.8c.5-6.5 6-11.7 13-11.7 3.5 0 6.7 1.3 9 3.4C37.5 15.5 43 12 50 12c10 0 18 7 19.5 16.2C72 29 74 31.5 74 34.5c0 .5 0 1-.1 1.5H90c4 0 7 3 7 4.5S94 45 90 45z" fill="rgba(255,255,255,0.85)"/></svg>
                                    </div>
                                    <div className="wg-moving-cloud wg-mc-5">
                                        <svg viewBox="0 0 100 60" fill="none"><path d="M85 42H12c-4 0-7-3-7-6.5s2.5-6 5.8-6.5c.4-5.5 5-10 11-10 3 0 5.6 1.1 7.5 2.8C31 18 36 15 42 15c8.5 0 15.5 6 16.8 13.8C61 29.5 63 31.8 63 35c0 .4 0 .8-.1 1.2H85c3.5 0 6.5 2.5 6.5 3.8S88.5 42 85 42z" fill="#fff"/></svg>
                                    </div>
                                    <div className="wg-moving-cloud wg-mc-6">
                                        <svg viewBox="0 0 100 60" fill="none"><path d="M90 45H15c-5 0-9-3.6-9-8s3-7.2 7-7.8c.5-6.5 6-11.7 13-11.7 3.5 0 6.7 1.3 9 3.4C37.5 15.5 43 12 50 12c10 0 18 7 19.5 16.2C72 29 74 31.5 74 34.5c0 .5 0 1-.1 1.5H90c4 0 7 3 7 4.5S94 45 90 45z" fill="rgba(255,255,255,0.7)"/></svg>
                                    </div>
                                </div>

                            <div className="wg-flex-row" style={{ padding: '0 24px', marginTop: '16px', marginBottom: '16px' }}>
                                <div style={{ flex: 1 }}>
                                    <div className="wg-label">Cloud Cover <InfoIcon id="cloud_cover" /></div>
                                    <div style={{ marginTop: '8px' }}>
                                        <span className="wg-val-lg">{cloud_cover}</span><span className="wg-unit">%</span>
                                    </div>
                                </div>
                                <div style={{ flex: 1 }}>
                                    <div className="wg-label">Visibility <InfoIcon id="visibility" /></div>
                                    <div style={{ marginTop: '8px' }}>
                                        <span className="wg-val-lg">{visibility}</span><span className="wg-unit">km</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="wg-footer">
                            Recent visibility is {visibility}km with {cloud_cover}% cloud coverage, so plan accordingly!
                        </div>
                    </div>

                    {/* 3. PRECIPITATION */}
                    <div className="wg-card">
                        <div className="wg-card-content">
                            <div className="wg-label">Precipitation <InfoIcon id="precipitation" /></div>
                            <div className="wg-flex-row" style={{ marginTop: '20px', alignItems: 'center' }}>
                                <div style={{ flex: 1, position: 'relative', height: '80px' }}>
                                    {/* Detailed sun/cloud/rain layout */}
                                    <svg viewBox="0 0 100 80" style={{ width: '100%', height: '100%' }}>
                                        {/* Orange Sun */}
                                        <circle cx="65" cy="35" r="15" fill="#f97316" />
                                        {/* Fluffy Cloud */}
                                        <path d="M25 50 a12 12 0 0 1 12 -12 a18 18 0 0 1 32 4 a14 14 0 0 1 2 26 H25 a14 14 0 0 1 0 -18 z" fill="#fff" />
                                        {/* Rain drops */}
                                        <path d="M40 65 l-3 8 M55 65 l-3 8 M70 65 l-3 8" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" />
                                    </svg>
                                </div>
                                <div style={{ flex: 1, textAlign: 'right' }}>
                                    <span className="wg-val-xl">{precipitation}</span>
                                    <span className="wg-unit" style={{ display: 'block', fontSize: '1rem' }}>mm</span>
                                </div>
                            </div>
                        </div>
                        <div className="wg-footer">
                            Current precipitation chances sit at {precipitation}mm
                        </div>
                    </div>

                </div>

                <div className="wg-col-vertical">

                    {/* 4. PRESSURE DIAL */}
                    <div className="wg-card">
                        <div className="wg-card-content">
                            <div className="wg-flex-row">
                                <span className="wg-label">Pressure</span> <InfoIcon id="pressure" />
                            </div>

                            <div style={{ display: 'flex', marginTop: '16px' }}>
                                <div style={{ width: '160px', height: '140px', position: 'relative' }}>
                                    <svg viewBox="0 0 200 200" width="100%" height="100%" style={{ overflow: 'visible' }}>
                                        <g transform="translate(100, 100)">
                                            {/* Tick Marks */}
                                            {tickMarks.map((tick, i) => {
                                                const rad = (tick.angle - 90) * Math.PI / 180;
                                                const r1 = 80;
                                                const r2 = tick.isMajor ? 65 : 72;
                                                const x1 = r1 * Math.cos(rad);
                                                const y1 = r1 * Math.sin(rad);
                                                const x2 = r2 * Math.cos(rad);
                                                const y2 = r2 * Math.sin(rad);

                                                // Text placement
                                                const rText = 48;
                                                const tx = rText * Math.cos(rad);
                                                const ty = rText * Math.sin(rad) + 4; // center text slightly

                                                return (
                                                    <g key={i}>
                                                        <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#cbd5e1" strokeWidth={tick.isMajor ? "3" : "2"} opacity={tick.isMajor ? "1" : "0.5"} strokeLinecap="round" />
                                                        {tick.isMajor && (
                                                            <text x={tx} y={ty} fill="#f8fafc" fontSize="10" fontWeight="600" textAnchor="middle">{tick.val}</text>
                                                        )}
                                                    </g>
                                                )
                                            })}
                                            {/* Needle */}
                                            <g style={{ transform: `rotate(${(pressure - 1010) * 15}deg)`, transition: 'transform 1s ease' }}>
                                                <polygon points="-3,-5 3,-5 0,-65" fill="#f43f5e" />
                                                <circle cx="0" cy="0" r="5" fill="#fff" />
                                            </g>
                                        </g>
                                    </svg>
                                </div>
                                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                                    <div>
                                        <span className="wg-val-xl">{pressure}</span>
                                        <span className="wg-unit" style={{ fontSize: '1rem', marginLeft: '4px' }}>mb</span>
                                    </div>
                                    <div className="wg-pill-pink" style={{ marginTop: '8px' }}>
                                        {pressure > 1015 ? 'High' : pressure < 1005 ? 'Low' : 'Moderate'}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="wg-footer">
                            Current pressure level is a {pressure} mb.
                        </div>
                    </div>

                    {/* 5. UV INDEX */}
                    <div className="wg-card">
                        <div className="wg-card-content">
                            <div className="wg-label" style={{ marginBottom: '16px' }}>UV Index <InfoIcon id="uv_index" /></div>

                            <div className="wg-flex-row" style={{ height: '80px', position: 'relative' }}>
                                {/* Top-left glowing arc */}
                                <div style={{ width: '80px', height: '80px', position: 'relative', overflow: 'hidden' }}>
                                    <div style={{ position: 'absolute', top: 0, left: 0, width: '160px', height: '160px', borderRadius: '50%', border: '16px solid rgba(234, 179, 8, 0.4)', boxSizing: 'border-box' }}></div>
                                    <div style={{ position: 'absolute', top: '12px', left: '12px', width: '136px', height: '136px', borderRadius: '50%', border: '24px solid rgba(250, 204, 21, 0.9)', boxSizing: 'border-box', boxShadow: '0 0 20px rgba(250, 204, 21, 0.5)' }}></div>
                                </div>

                                <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
                                    <span className="wg-label" style={{ color: '#fff' }}>UV Index</span>
                                    <span className="wg-val-xl" style={{ lineHeight: '1' }}>{Math.round(uv_index)}</span>
                                </div>
                            </div>

                            <div style={{ marginTop: '24px', position: 'relative' }}>
                                <div className="wg-uv-track"></div>
                                {/* Value indicator sliding across the track */}
                                <div className="wg-uv-thumb" style={{ left: `${Math.max(2, Math.min(98, (uv_index / 11) * 100))}%` }}>
                                    <div className="wg-uv-thumb-line"></div>
                                </div>
                                {/* "Low" generic floating pill aligned to center of text */}
                                <div className="wg-uv-floating-pill" style={{ left: `${Math.max(10, Math.min(90, (uv_index / 11) * 100))}%`, color: uvInfo.color, background: 'transparent' }}>
                                    <div style={{ background: '#f8fafc', padding: '2px 12px', borderRadius: '12px', color: '#1e293b', fontWeight: 600, fontSize: '0.8rem', marginTop: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.5)' }}>
                                        {uvInfo.text}
                                    </div>
                                </div>
                            </div>

                        </div>
                        <div className="wg-footer">
                            The present UV index is {Math.round(uv_index)}, consider suggestions for the same!
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}
