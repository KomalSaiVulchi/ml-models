export const AQI_SCALE = [
    {
        min: 0, max: 50, category: 'Good', color: '#00E400',
        bgGlow: 'rgba(0, 228, 0, 0.15)', emoji: '😊',
        theme: {
            gradientTop: '#1a3a1a',
            gradientMid: '#2d5a1e',
            gradientBottom: '#4a8c28',
            sunColor: '#ffcc33',
            sunGlow: 'rgba(255,204,51,0.3)',
            cloudColor: 'rgba(255,255,255,0.7)',
            cloudOpacity: 0.6,
            cityscapeColor: 'rgba(30,80,20,0.5)',
        }
    },
    {
        min: 51, max: 100, category: 'Satisfactory', color: '#92D050',
        bgGlow: 'rgba(146, 208, 80, 0.15)', emoji: '🙂',
        theme: {
            gradientTop: '#1c1f26',
            gradientMid: '#3d3520',
            gradientBottom: '#8a7530',
            sunColor: '#ffa500',
            sunGlow: 'rgba(255,165,0,0.35)',
            cloudColor: 'rgba(180,170,140,0.8)',
            cloudOpacity: 0.7,
            cityscapeColor: 'rgba(100,80,30,0.4)',
        }
    },
    {
        min: 101, max: 200, category: 'Moderate', color: '#FFD700',
        bgGlow: 'rgba(255, 215, 0, 0.15)', emoji: '😐',
        theme: {
            gradientTop: '#1c1f26',
            gradientMid: '#302621',
            gradientBottom: '#854015',
            sunColor: '#e8a020',
            sunGlow: 'rgba(232,160,32,0.3)',
            cloudColor: 'rgba(160,140,110,0.7)',
            cloudOpacity: 0.6,
            cityscapeColor: 'rgba(80,40,10,0.4)',
        }
    },
    {
        min: 201, max: 300, category: 'Poor', color: '#FF4444',
        bgGlow: 'rgba(255, 68, 68, 0.15)', emoji: '😷',
        theme: {
            gradientTop: '#2a1020',
            gradientMid: '#6b2040',
            gradientBottom: '#c04070',
            sunColor: '#cc6688',
            sunGlow: 'rgba(204,102,136,0.3)',
            cloudColor: 'rgba(150,100,120,0.7)',
            cloudOpacity: 0.7,
            cityscapeColor: 'rgba(80,20,40,0.4)',
        }
    },
    {
        min: 301, max: 400, category: 'Very Poor', color: '#CC0000',
        bgGlow: 'rgba(204, 0, 0, 0.15)', emoji: '🤢',
        theme: {
            gradientTop: '#1a0a0a',
            gradientMid: '#3a1515',
            gradientBottom: '#602020',
            sunColor: '#aa4444',
            sunGlow: 'rgba(170,68,68,0.25)',
            cloudColor: 'rgba(120,80,80,0.6)',
            cloudOpacity: 0.5,
            cityscapeColor: 'rgba(60,15,15,0.5)',
        }
    },
    {
        min: 401, max: 500, category: 'Severe', color: '#7E0023',
        bgGlow: 'rgba(126, 0, 35, 0.15)', emoji: '💀',
        theme: {
            gradientTop: '#0a0505',
            gradientMid: '#200a10',
            gradientBottom: '#3a1520',
            sunColor: '#663333',
            sunGlow: 'rgba(102,51,51,0.2)',
            cloudColor: 'rgba(80,50,50,0.5)',
            cloudOpacity: 0.4,
            cityscapeColor: 'rgba(40,10,10,0.5)',
        }
    },
];

export const US_AQI_SCALE = [
    {
        min: 0, max: 50, category: 'Good', color: '#00E400',
        bgGlow: 'rgba(0, 228, 0, 0.15)', emoji: '😊',
        theme: {
            gradientTop: '#1a3a1a', gradientMid: '#2d5a1e', gradientBottom: '#4a8c28',
            sunColor: '#ffcc33', sunGlow: 'rgba(255,204,51,0.3)',
            cloudColor: 'rgba(255,255,255,0.7)', cloudOpacity: 0.6,
            cityscapeColor: 'rgba(30,80,20,0.5)',
        }
    },
    {
        min: 51, max: 100, category: 'Moderate', color: '#FFFF00',
        bgGlow: 'rgba(255, 255, 0, 0.15)', emoji: '🙂',
        theme: {
            gradientTop: '#1c1f26', gradientMid: '#3d3520', gradientBottom: '#8a7530',
            sunColor: '#ffa500', sunGlow: 'rgba(255,165,0,0.35)',
            cloudColor: 'rgba(180,170,140,0.8)', cloudOpacity: 0.7,
            cityscapeColor: 'rgba(100,80,30,0.4)',
        }
    },
    {
        min: 101, max: 150, category: 'Unhealthy for Sensitive Groups', color: '#FF7E00',
        bgGlow: 'rgba(255, 126, 0, 0.15)', emoji: '😐',
        theme: {
            gradientTop: '#1c1f26', gradientMid: '#302621', gradientBottom: '#854015',
            sunColor: '#e8a020', sunGlow: 'rgba(232,160,32,0.3)',
            cloudColor: 'rgba(160,140,110,0.7)', cloudOpacity: 0.6,
            cityscapeColor: 'rgba(80,40,10,0.4)',
        }
    },
    {
        min: 151, max: 200, category: 'Unhealthy', color: '#FF0000',
        bgGlow: 'rgba(255, 0, 0, 0.15)', emoji: '😷',
        theme: {
            gradientTop: '#2a1020', gradientMid: '#6b2040', gradientBottom: '#c04070',
            sunColor: '#cc6688', sunGlow: 'rgba(204,102,136,0.3)',
            cloudColor: 'rgba(150,100,120,0.7)', cloudOpacity: 0.7,
            cityscapeColor: 'rgba(80,20,40,0.4)',
        }
    },
    {
        min: 201, max: 300, category: 'Very Unhealthy', color: '#8F3F97',
        bgGlow: 'rgba(143, 63, 151, 0.15)', emoji: '🤢',
        theme: {
            gradientTop: '#1a0a0a', gradientMid: '#3a1535', gradientBottom: '#602060',
            sunColor: '#aa44aa', sunGlow: 'rgba(170,68,170,0.25)',
            cloudColor: 'rgba(120,80,120,0.6)', cloudOpacity: 0.5,
            cityscapeColor: 'rgba(60,15,45,0.5)',
        }
    },
    {
        min: 301, max: 500, category: 'Hazardous', color: '#7E0023',
        bgGlow: 'rgba(126, 0, 35, 0.15)', emoji: '💀',
        theme: {
            gradientTop: '#0a0505', gradientMid: '#200a10', gradientBottom: '#3a1520',
            sunColor: '#663333', sunGlow: 'rgba(102,51,51,0.2)',
            cloudColor: 'rgba(80,50,50,0.5)', cloudOpacity: 0.4,
            cityscapeColor: 'rgba(40,10,10,0.5)',
        }
    },
];

export function getAQIInfo(aqi, standard = 'indian') {
    const scale = standard === 'us' ? US_AQI_SCALE : AQI_SCALE;
    for (const level of scale) {
        if (aqi <= level.max) return level;
    }
    return scale[scale.length - 1];
}

export function getAQIColor(aqi, standard = 'indian') {
    return getAQIInfo(aqi, standard).color;
}

export function getAQICategory(aqi, standard = 'indian') {
    return getAQIInfo(aqi, standard).category;
}

export function getAQIGradient(aqi) {
    const info = getAQIInfo(aqi);
    return `linear-gradient(135deg, ${info.color}22, ${info.color}08)`;
}

export function getPollutantColor(level) {
    const colors = {
        'Good': '#00E400',
        'Satisfactory': '#92D050',
        'Moderate': '#FFD700',
        'Poor': '#FF4444',
        'Very Poor': '#CC0000',
        'Severe': '#7E0023'
    };
    return colors[level] || '#FFD700';
}
