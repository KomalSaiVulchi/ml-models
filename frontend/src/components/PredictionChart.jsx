import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, BarChart3 } from 'lucide-react';
import { getAQIInfo, getAQIColor } from '../utils/aqiUtils';

function CustomTooltip({ active, payload, label, standard }) {
    if (!active || !payload || !payload.length) return null;

    const aqi = payload.find(p => p.dataKey === 'primary')?.value;
    const info = getAQIInfo(aqi, standard);
    const dataPoint = payload[0]?.payload;

    return (
        <div className="custom-tooltip">
            <div className="tooltip-time">{label}</div>
            <div className="tooltip-value" style={{ color: info.color }}>
                AQI: {Math.round(aqi)}
            </div>
            <div className="tooltip-category" style={{ color: info.color }}>
                {info.emoji} {info.category}
            </div>
            {dataPoint?.uncertainty > 0 && (
                <div style={{ fontSize: '0.75rem', color: '#9da5b4', marginTop: '3px' }}>
                    Range: {dataPoint.lower} – {dataPoint.upper} (±{Math.round(dataPoint.uncertainty)})
                </div>
            )}
            {payload.find(p => p.dataKey === 'secondary') && (
                <div className="tooltip-value" style={{ color: '#88a4d4', fontSize: '0.78rem', marginTop: '2px' }}>
                    {standard === 'indian' ? 'US EPA' : 'Indian CPCB'}: {Math.round(payload.find(p => p.dataKey === 'secondary')?.value)}
                </div>
            )}
        </div>
    );
}

export default function PredictionChart({ predictions, currentAQI, currentAQI_US, standard = 'indian' }) {
    if (!predictions || predictions.length === 0) return null;

    const isIndian = standard === 'indian';

    // Build chart data — show every 3rd point label to avoid crowding
    const chartData = [
        {
            time: 'Now',
            primary: Math.round(isIndian ? currentAQI : currentAQI_US),
            secondary: Math.round(isIndian ? currentAQI_US : currentAQI),
            upper: Math.round(isIndian ? currentAQI : currentAQI_US),
            lower: Math.round(isIndian ? currentAQI : currentAQI_US),
            uncertainty: 0,
        },
        ...predictions.map((p, i) => ({
            time: p.time_label,
            primary: Math.round(isIndian ? p.aqi_indian : p.aqi_us),
            secondary: Math.round(isIndian ? p.aqi_us : p.aqi_indian),
            upper: Math.round(isIndian ? (p.aqi_indian_upper || p.aqi_indian) : (p.aqi_us_upper || p.aqi_us)),
            lower: Math.round(isIndian ? (p.aqi_indian_lower || p.aqi_indian) : (p.aqi_us_lower || p.aqi_us)),
            uncertainty: p.uncertainty || 0,
            showLabel: (i + 1) % 6 === 0,
        }))
    ];

    // Trend info based on selected standard
    const firstAQI = chartData[0].primary;
    const lastAQI = chartData[chartData.length - 1].primary;
    const change = lastAQI - firstAQI;
    const avgChange = change / predictions.length;

    let trendIcon, trendLabel, trendColor;
    if (avgChange > 3) {
        trendIcon = <TrendingUp size={16} />;
        trendLabel = 'Rising';
        trendColor = '#FF4444';
    } else if (avgChange < -3) {
        trendIcon = <TrendingDown size={16} />;
        trendLabel = 'Falling';
        trendColor = '#00E400';
    } else {
        trendIcon = <Minus size={16} />;
        trendLabel = 'Stable';
        trendColor = '#FFD700';
    }

    const allPrimary = chartData.map(d => d.primary);
    const allUpper = chartData.map(d => d.upper || d.primary);
    const allLower = chartData.map(d => d.lower || d.primary);
    const minAQI = Math.min(...allLower);
    const maxAQI = Math.max(...allUpper);

    // Gradient color based on average AQI
    const avgAQI = allPrimary.reduce((s, v) => s + v, 0) / allPrimary.length;
    const gradientColor = getAQIColor(avgAQI, standard);

    const standardLabel = isIndian ? 'Indian CPCB' : 'US EPA';
    const secondaryLabel = isIndian ? 'US EPA' : 'Indian CPCB';

    return (
        <div className="prediction-chart glass-card">
            <div className="section-title">
                <BarChart3 size={14} />
                {standardLabel} AQI Forecast — Next {predictions.length} Hours
            </div>

            <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                        <defs>
                            <linearGradient id="aqiGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={gradientColor} stopOpacity={0.3} />
                                <stop offset="100%" stopColor={gradientColor} stopOpacity={0.02} />
                            </linearGradient>
                            <linearGradient id="secGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#4f8fff" stopOpacity={0.15} />
                                <stop offset="100%" stopColor="#4f8fff" stopOpacity={0.01} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis
                            dataKey="time"
                            tick={{ fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                            interval="preserveStartEnd"
                        />
                        <YAxis
                            tick={{ fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                            domain={[
                                Math.max(0, Math.floor(minAQI * 0.8)),
                                Math.ceil(maxAQI * 1.15)
                            ]}
                        />
                        <Tooltip content={<CustomTooltip standard={standard} />} />

                        {/* AQI Zone reference lines */}
                        <ReferenceLine y={50} stroke="#00E40033" strokeDasharray="6 4" />
                        <ReferenceLine y={100} stroke="#FFD70033" strokeDasharray="6 4" />
                        <ReferenceLine y={200} stroke="#FF444433" strokeDasharray="6 4" />

                        {/* Confidence band boundaries (dashed lines) */}
                        <Area
                            type="monotone"
                            dataKey="upper"
                            stroke={`${gradientColor}35`}
                            strokeWidth={1}
                            strokeDasharray="4 3"
                            fill="none"
                            dot={false}
                            activeDot={false}
                            isAnimationActive={false}
                            name="Upper bound"
                        />
                        <Area
                            type="monotone"
                            dataKey="lower"
                            stroke={`${gradientColor}35`}
                            strokeWidth={1}
                            strokeDasharray="4 3"
                            fill="none"
                            dot={false}
                            activeDot={false}
                            isAnimationActive={false}
                            name="Lower bound"
                        />

                        <Area
                            type="monotone"
                            dataKey="secondary"
                            stroke="#4f8fff55"
                            fill="url(#secGradient)"
                            strokeWidth={1.5}
                            dot={false}
                            name={secondaryLabel}
                        />
                        <Area
                            type="monotone"
                            dataKey="primary"
                            stroke={gradientColor}
                            fill="url(#aqiGradient)"
                            strokeWidth={2.5}
                            dot={{ fill: gradientColor, r: 3, strokeWidth: 0 }}
                            activeDot={{ r: 5, stroke: gradientColor, strokeWidth: 2, fill: '#0a0a1a' }}
                            name={standardLabel}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            <div className="trend-summary">
                <div className="trend-item">
                    <span
                        className="trend-badge"
                        style={{
                            background: `${trendColor}18`,
                            color: trendColor,
                            border: `1px solid ${trendColor}30`
                        }}
                    >
                        {trendIcon} {trendLabel}
                    </span>
                </div>
                <div className="trend-item">
                    Avg change: <strong style={{ color: change > 0 ? '#FF4444' : '#00E400' }}>
                        {change > 0 ? '+' : ''}{change.toFixed(1)}
                    </strong> AQI over {predictions.length}h
                </div>
                <div className="trend-item">
                    Range: <strong>{Math.round(minAQI)}</strong> — <strong>{Math.round(maxAQI)}</strong>
                </div>
                {chartData.length > 1 && chartData[chartData.length - 1].uncertainty > 0 && (
                    <div className="trend-item">
                        Confidence: <strong>±{Math.round(chartData[chartData.length - 1].uncertainty)}</strong> at {predictions.length}h
                    </div>
                )}
            </div>
        </div>
    );
}
