'use client';

import { useEffect, useState } from 'react';
import { ComposableMap, Geographies, Geography, Graticule, Marker, Sphere } from 'react-simple-maps';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

const KNOWN_COORDS: Record<string, [number, number]> = {
  tokyo: [139.69, 35.69],
  osaka: [135.50, 34.69],
  kyoto: [135.77, 35.01],
  paris: [2.35, 48.86],
  london: [-0.13, 51.51],
  'new york': [-74.01, 40.71],
  nyc: [-74.01, 40.71],
  dubai: [55.27, 25.20],
  sydney: [151.21, -33.87],
  rome: [12.50, 41.90],
  barcelona: [2.17, 41.39],
  bangkok: [100.50, 13.76],
  singapore: [103.82, 1.35],
  bali: [115.22, -8.41],
  istanbul: [28.98, 41.01],
  amsterdam: [4.90, 52.37],
  berlin: [13.41, 52.52],
  madrid: [-3.70, 40.42],
  vienna: [16.37, 48.21],
  prague: [14.42, 50.09],
  lisbon: [-9.14, 38.72],
  athens: [23.73, 37.98],
  cairo: [31.24, 30.04],
  nairobi: [36.82, -1.29],
  'cape town': [18.42, -33.92],
  toronto: [-79.38, 43.65],
  'los angeles': [-118.24, 34.05],
  chicago: [-87.63, 41.88],
  miami: [-80.19, 25.76],
  'mexico city': [-99.13, 19.43],
  'buenos aires': [-58.38, -34.60],
  'rio de janeiro': [-43.17, -22.91],
  mumbai: [72.88, 19.08],
  delhi: [77.10, 28.70],
  'new delhi': [77.21, 28.61],
  beijing: [116.41, 39.90],
  shanghai: [121.47, 31.23],
  'hong kong': [114.17, 22.32],
  seoul: [126.98, 37.57],
  'kuala lumpur': [101.69, 3.14],
  jakarta: [106.85, -6.21],
  manila: [120.98, 14.60],
  moscow: [37.62, 55.76],
  zurich: [8.54, 47.38],
  brussels: [4.35, 50.85],
  stockholm: [18.07, 59.33],
  oslo: [10.75, 59.91],
  copenhagen: [12.57, 55.68],
  helsinki: [24.94, 60.17],
  vancouver: [-123.12, 49.28],
  montreal: [-73.57, 45.50],
  'san francisco': [-122.42, 37.77],
  'las vegas': [-115.14, 36.17],
  hawaii: [-157.82, 21.31],
  honolulu: [-157.82, 21.31],
  maldives: [73.22, 3.20],
  auckland: [174.77, -36.87],
  'new zealand': [174.77, -36.87],
  'st. petersburg': [30.32, 59.94],
  'saint petersburg': [30.32, 59.94],
  budapest: [19.04, 47.50],
  warsaw: [21.01, 52.23],
  edinburgh: [-3.19, 55.95],
  dublin: [-6.26, 53.34],
  milan: [9.19, 45.46],
  florence: [11.26, 43.77],
  venice: [12.34, 45.44],
  cancun: [-86.85, 21.16],
  phuket: [98.30, 7.89],
  'ho chi minh': [106.63, 10.82],
  hanoi: [105.83, 21.03],
  'siem reap': [103.86, 13.36],
  doha: [51.53, 25.29],
  riyadh: [46.72, 24.69],
  'abu dhabi': [54.37, 24.47],
  geneva: [6.14, 46.20],
  lagos: [3.39, 6.45],
  accra: [-0.19, 5.56],
  addis: [38.74, 9.02],
  casablanca: [-7.59, 33.57],
  marrakech: [-8.01, 31.63],
};

const _geocodeCache = new Map<string, [number, number]>();

async function geocode(destination: string): Promise<[number, number]> {
  const key = destination.toLowerCase().trim();
  for (const [city, coords] of Object.entries(KNOWN_COORDS)) {
    if (key === city || key.startsWith(city) || city.startsWith(key)) return coords;
  }
  if (_geocodeCache.has(key)) return _geocodeCache.get(key)!;
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(destination)}&format=json&limit=1`,
      { headers: { 'User-Agent': 'TravelPlannerApp/1.0' } }
    );
    const data = await res.json();
    if (data?.[0]) {
      const coords: [number, number] = [parseFloat(data[0].lon), parseFloat(data[0].lat)];
      _geocodeCache.set(key, coords);
      return coords;
    }
  } catch {}
  return [0, 20];
}

const SIZE = 300;
const SCALE = 142;

export default function DestinationGlobe({ destination }: { destination: string }) {
  const [coords, setCoords] = useState<[number, number]>([0, 20]);
  const [rotation, setRotation] = useState<[number, number, number]>([0, -20, 0]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(false);
    let currentAngle = 0;
    let active = true;

    const spinId = setInterval(() => {
      if (!active) return;
      currentAngle = (currentAngle + 3) % 360;
      setRotation([currentAngle, -20, 0]);
    }, 40);

    geocode(destination).then((c) => {
      if (!active) return;
      clearInterval(spinId);
      setCoords(c);

      const startAngle = currentAngle;
      const targetRot: [number, number, number] = [
        -c[0],
        Math.max(-70, Math.min(70, -c[1] * 0.8)),
        0,
      ];

      let step = 0;
      const totalSteps = 35;
      const animId = setInterval(() => {
        if (!active) { clearInterval(animId); return; }
        step++;
        const t = step / totalSteps;
        const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
        if (step >= totalSteps) {
          clearInterval(animId);
          setRotation(targetRot);
          setReady(true);
        } else {
          setRotation([
            startAngle + (targetRot[0] - startAngle) * ease,
            -20 + (targetRot[1] + 20) * ease,
            0,
          ]);
        }
      }, 28);
    });

    return () => { active = false; };
  }, [destination]);

  return (
    <div className="flex flex-col items-center gap-5">
      <div className="relative" style={{ width: SIZE, height: SIZE }}>
        {/* Outer glow rings */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            boxShadow:
              '0 0 0 1px rgba(96,165,250,0.15), 0 0 40px rgba(59,130,246,0.5), 0 0 90px rgba(59,130,246,0.25), 0 0 160px rgba(59,130,246,0.1)',
          }}
        />

        {/* Globe body */}
        <div className="rounded-full overflow-hidden" style={{ width: SIZE, height: SIZE }}>
          <ComposableMap
            projection="geoOrthographic"
            projectionConfig={{ rotate: rotation, scale: SCALE }}
            width={SIZE}
            height={SIZE}
            style={{ width: '100%', height: '100%' }}
          >
            {/* Ocean */}
            <Sphere id="rsm-sphere" fill="#0c2d6b" stroke="#1a4a9e" strokeWidth={0.6} />
            {/* Grid lines */}
            <Graticule stroke="#1a4a9e" strokeWidth={0.45} opacity={0.7} />
            {/* Land */}
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map((geo) => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#2d9e5f"
                    stroke="#1a6b3f"
                    strokeWidth={0.35}
                    style={{
                      default: { outline: 'none' },
                      hover: { outline: 'none' },
                      pressed: { outline: 'none' },
                    }}
                  />
                ))
              }
            </Geographies>

            {/* Destination marker */}
            {ready && (
              <Marker coordinates={coords}>
                {/* Outer pulse rings */}
                <circle r={6} fill="#ef4444" opacity={0.25}>
                  <animate attributeName="r" values="6;22;6" dur="2.2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.4;0;0.4" dur="2.2s" repeatCount="indefinite" />
                </circle>
                <circle r={6} fill="#ef4444" opacity={0.35}>
                  <animate attributeName="r" values="6;14;6" dur="2.2s" begin="0.4s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.5;0;0.5" dur="2.2s" begin="0.4s" repeatCount="indefinite" />
                </circle>
                {/* Pin dot */}
                <circle r={5.5} fill="#ef4444" stroke="white" strokeWidth={2} />
                <circle r={2.5} fill="white" opacity={0.9} />
              </Marker>
            )}
          </ComposableMap>
        </div>

        {/* Shine highlight */}
        <div
          className="absolute inset-0 rounded-full pointer-events-none"
          style={{
            background:
              'radial-gradient(circle at 30% 26%, rgba(255,255,255,0.22) 0%, rgba(255,255,255,0.06) 38%, transparent 65%)',
          }}
        />
        {/* Edge vignette */}
        <div
          className="absolute inset-0 rounded-full pointer-events-none"
          style={{
            background:
              'radial-gradient(circle at 50% 50%, transparent 52%, rgba(0,4,18,0.75) 100%)',
          }}
        />
      </div>

      {/* Destination label */}
      <div className="text-center">
        <div className="flex items-center gap-2 justify-center mb-1">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
          </span>
          <span className="text-white font-semibold text-base tracking-wide">{destination}</span>
        </div>
        {!ready && (
          <p className="text-white/35 text-xs">Locating on globe…</p>
        )}
      </div>
    </div>
  );
}
