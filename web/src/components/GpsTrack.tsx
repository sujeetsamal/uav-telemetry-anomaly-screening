import React, { useMemo } from 'react';
import { Navigation } from 'lucide-react';
import { TelemetryEvent, TelemetryPoint } from '../types/telemetry';

interface GpsTrackProps {
  data: TelemetryPoint[];
  events: TelemetryEvent[];
  selectedEvent: TelemetryEvent | null;
  onSelectEvent: (event: TelemetryEvent | null) => void;
}

export const GpsTrack: React.FC<GpsTrackProps> = ({
  data,
  events,
  selectedEvent,
  onSelectEvent,
}) => {
  // Filter points that have valid coordinates
  const validPoints = useMemo(() => {
    return data.filter((p) => p.lat != null && p.lon != null && !isNaN(p.lat) && !isNaN(p.lon));
  }, [data]);

  // Compute 2D bounding box
  const bounds = useMemo(() => {
    if (validPoints.length === 0) {
      return { minLat: 0, maxLat: 1, minLon: 0, maxLon: 1 };
    }
    let minLat = Infinity,
      maxLat = -Infinity,
      minLon = Infinity,
      maxLon = -Infinity;

    for (const p of validPoints) {
      if (p.lat! < minLat) minLat = p.lat!;
      if (p.lat! > maxLat) maxLat = p.lat!;
      if (p.lon! < minLon) minLon = p.lon!;
      if (p.lon! > maxLon) maxLon = p.lon!;
    }

    const padLat = Math.max((maxLat - minLat) * 0.1, 0.0001);
    const padLon = Math.max((maxLon - minLon) * 0.1, 0.0001);

    return {
      minLat: minLat - padLat,
      maxLat: maxLat + padLat,
      minLon: minLon - padLon,
      maxLon: maxLon + padLon,
    };
  }, [validPoints]);

  const width = 450;
  const height = 340;

  const project = (lat: number, lon: number): [number, number] => {
    const x = ((lon - bounds.minLon) / (bounds.maxLon - bounds.minLon || 1)) * (width - 40) + 20;
    // Invert y since SVG top is 0
    const y = (1.0 - (lat - bounds.minLat) / (bounds.maxLat - bounds.minLat || 1)) * (height - 40) + 20;
    return [x, y];
  };

  // Build SVG path string
  const pathD = useMemo(() => {
    if (validPoints.length === 0) return '';
    return validPoints
      .map((p, idx) => {
        const [x, y] = project(p.lat!, p.lon!);
        return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(' ');
  }, [validPoints, bounds]);

  // Project anomaly events to track locations
  const eventPoints = useMemo(() => {
    return events.map((evt) => {
      // Find point closest to evt.start_time
      const match = validPoints.find((p) => p.timestamp >= evt.start_time) || validPoints[0];
      const coords = match && match.lat != null && match.lon != null ? project(match.lat, match.lon) : [0, 0];
      return {
        ...evt,
        x: coords[0],
        y: coords[1],
      };
    });
  }, [events, validPoints, bounds]);

  return (
    <div className="bg-gray-900/60 border border-gray-800/80 rounded-2xl p-4 flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-2">
        <div className="flex items-center gap-2">
          <Navigation className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
            2D GPS Flight Path & Anomaly Footprint
          </h3>
        </div>
        <div className="text-[11px] font-mono text-gray-400">
          {validPoints.length.toLocaleString()} Track Waypoints
        </div>
      </div>

      <div className="relative flex-1 bg-gray-950/80 rounded-xl border border-gray-800 overflow-hidden flex items-center justify-center p-2">
        {validPoints.length === 0 ? (
          <div className="text-gray-400 text-xs">No GPS coordinates available</div>
        ) : (
          <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full max-h-[360px] drop-shadow-md">
            {/* Grid Lines */}
            <line x1="20" y1="85" x2={width - 20} y2="85" stroke="#1f2937" strokeDasharray="3 3" />
            <line x1="20" y1="170" x2={width - 20} y2="170" stroke="#1f2937" strokeDasharray="3 3" />
            <line x1="20" y1="255" x2={width - 20} y2="255" stroke="#1f2937" strokeDasharray="3 3" />
            <line x1="112" y1="20" x2="112" y2={height - 20} stroke="#1f2937" strokeDasharray="3 3" />
            <line x1="225" y1="20" x2="225" y2={height - 20} stroke="#1f2937" strokeDasharray="3 3" />
            <line x1="337" y1="20" x2="337" y2={height - 20} stroke="#1f2937" strokeDasharray="3 3" />

            {/* Flight Path Line */}
            <path d={pathD} fill="none" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.85" />

            {/* Takeoff point (Green) */}
            {validPoints[0] && (
              <g>
                {(() => {
                  const [sx, sy] = project(validPoints[0].lat!, validPoints[0].lon!);
                  return (
                    <>
                      <circle cx={sx} cy={sy} r="6" fill="#10b981" stroke="#ffffff" strokeWidth="1.5" />
                      <text x={sx + 8} y={sy + 4} fill="#10b981" fontSize="10" fontWeight="bold">
                        Takeoff
                      </text>
                    </>
                  );
                })()}
              </g>
            )}

            {/* Touchdown point (Red/Orange) */}
            {validPoints.length > 1 && (
              <g>
                {(() => {
                  const last = validPoints[validPoints.length - 1];
                  const [ex, ey] = project(last.lat!, last.lon!);
                  return (
                    <>
                      <circle cx={ex} cy={ey} r="6" fill="#f43f5e" stroke="#ffffff" strokeWidth="1.5" />
                      <text x={ex + 8} y={ey + 4} fill="#f43f5e" fontSize="10" fontWeight="bold">
                        Touchdown
                      </text>
                    </>
                  );
                })()}
              </g>
            )}

            {/* Anomaly Event Markers */}
            {eventPoints.map((evt, idx) => {
              const isSelected = selectedEvent?.event_id === evt.event_id;
              const color = evt.severity === 'critical' ? '#ef4444' : evt.severity === 'high' ? '#f97316' : '#eab308';
              return (
                <g
                  key={idx}
                  className="cursor-pointer transition-transform hover:scale-125"
                  onClick={() => onSelectEvent(isSelected ? null : evt)}
                >
                  <circle
                    cx={evt.x}
                    cy={evt.y}
                    r={isSelected ? 8 : 5}
                    fill={color}
                    stroke="#ffffff"
                    strokeWidth={isSelected ? 2 : 1}
                  />
                  {isSelected && (
                    <circle cx={evt.x} cy={evt.y} r="14" fill="none" stroke={color} strokeWidth="1.5" className="animate-ping" />
                  )}
                </g>
              );
            })}
          </svg>
        )}

        {/* Floating Legend */}
        <div className="absolute bottom-2 left-2 bg-gray-900/90 border border-gray-800 rounded-lg p-2 text-[10px] font-mono flex items-center gap-3 backdrop-blur-sm">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Takeoff
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-500"></span> Touchdown
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500"></span> Anomaly
          </div>
        </div>
      </div>
    </div>
  );
};
