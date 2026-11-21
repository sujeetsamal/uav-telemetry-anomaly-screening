import React, { useState } from 'react';
import {
  Brush,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { TelemetryEvent, TelemetryPoint } from '../types/telemetry';

interface SynchronizedChartsProps {
  data: TelemetryPoint[];
  events: TelemetryEvent[];
  selectedEvent: TelemetryEvent | null;
  onSelectEvent: (event: TelemetryEvent | null) => void;
}

export const SynchronizedCharts: React.FC<SynchronizedChartsProps> = ({
  data,
  events,
  selectedEvent,
}) => {
  const [activeChannel, setActiveChannel] = useState<'all' | 'dynamics' | 'electrical' | 'attitude'>('all');

  // Custom Dark Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-900/95 border border-gray-700/80 p-2.5 rounded-lg shadow-2xl backdrop-blur-md text-xs font-mono">
          <div className="text-cyan-300 font-semibold mb-1 border-b border-gray-800 pb-1">
            Time: {Number(label).toFixed(1)}s
          </div>
          <div className="space-y-0.5">
            {payload.map((entry: any, index: number) => (
              <div key={index} className="flex items-center justify-between gap-4">
                <span className="text-gray-400 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                  {entry.name}:
                </span>
                <span className="font-bold text-gray-200">
                  {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return null;
  };

  // Helper to render shaded anomaly reference areas
  const renderAnomalyBands = () => {
    return events.map((evt, idx) => {
      const isSelected = selectedEvent?.event_id === evt.event_id;
      const color = evt.severity === 'critical' ? '#ef4444' : evt.severity === 'high' ? '#f97316' : '#eab308';
      return (
        <ReferenceArea
          key={idx}
          x1={evt.start_time}
          x2={evt.end_time}
          stroke={isSelected ? '#38bdf8' : color}
          strokeWidth={isSelected ? 2 : 1}
          strokeOpacity={isSelected ? 0.9 : 0.4}
          fill={color}
          fillOpacity={isSelected ? 0.35 : 0.15}
        />
      );
    });
  };

  return (
    <div className="space-y-3 bg-gray-900/60 border border-gray-800/80 rounded-2xl p-4">
      <div className="flex items-center justify-between border-b border-gray-800 pb-3">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
          <h3 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
            Synchronized Multi-Channel Flight Telemetry
          </h3>
        </div>
        <div className="flex items-center gap-1.5 bg-gray-950 p-1 rounded-lg border border-gray-800 text-xs">
          {(['all', 'dynamics', 'electrical', 'attitude'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setActiveChannel(mode)}
              className={`px-3 py-1 rounded-md transition-all font-medium capitalize ${
                activeChannel === mode
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Chart 1: Altitude & Vertical Speed */}
      {(activeChannel === 'all' || activeChannel === 'dynamics') && (
        <div className="bg-gray-950/60 p-3 rounded-xl border border-gray-800/60">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1 px-2 font-mono">
            <span className="font-semibold text-sky-400">ALTITUDE (m) & VERTICAL SPEED (m/s)</span>
            <span className="text-[11px] text-gray-400">Shaded areas indicate flagged anomaly windows</span>
          </div>
          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} syncId="uav_telemetry">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="timestamp" stroke="#4b5563" tick={{ fontSize: 10, fill: '#9ca3af' }} hide />
                <YAxis yAxisId="alt" stroke="#38bdf8" tick={{ fontSize: 10, fill: '#38bdf8' }} domain={['auto', 'auto']} />
                <YAxis
                  yAxisId="vz"
                  orientation="right"
                  stroke="#fbbf24"
                  tick={{ fontSize: 10, fill: '#fbbf24' }}
                  domain={['auto', 'auto']}
                />
                <Tooltip content={<CustomTooltip />} />
                {renderAnomalyBands()}
                <Line yAxisId="alt" type="monotone" dataKey="alt" stroke="#38bdf8" dot={false} strokeWidth={1.6} name="Altitude (m)" isAnimationActive={false} />
                <Line yAxisId="vz" type="monotone" dataKey="vertical_speed" stroke="#fbbf24" dot={false} strokeWidth={1.2} strokeOpacity={0.8} name="V-Speed (m/s)" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Chart 2: Battery Voltage, Current & Power */}
      {(activeChannel === 'all' || activeChannel === 'electrical') && (
        <div className="bg-gray-950/60 p-3 rounded-xl border border-gray-800/60">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1 px-2 font-mono">
            <span className="font-semibold text-emerald-400">BATTERY VOLTAGE (V), CURRENT (A) & POWER (W)</span>
          </div>
          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} syncId="uav_telemetry">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="timestamp" stroke="#4b5563" tick={{ fontSize: 10, fill: '#9ca3af' }} hide />
                <YAxis yAxisId="v" stroke="#4ade80" tick={{ fontSize: 10, fill: '#4ade80' }} domain={[11.5, 17.5]} />
                <YAxis yAxisId="i" orientation="right" stroke="#f87171" tick={{ fontSize: 10, fill: '#f87171' }} domain={[0, 55]} />
                <Tooltip content={<CustomTooltip />} />
                {renderAnomalyBands()}
                <Line yAxisId="v" type="monotone" dataKey="voltage" stroke="#4ade80" dot={false} strokeWidth={1.6} name="Voltage (V)" isAnimationActive={false} />
                <Line yAxisId="i" type="monotone" dataKey="current" stroke="#f87171" dot={false} strokeWidth={1.2} strokeOpacity={0.85} name="Current (A)" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Chart 3: Attitude Dynamics (Roll, Pitch) */}
      {(activeChannel === 'all' || activeChannel === 'attitude') && (
        <div className="bg-gray-950/60 p-3 rounded-xl border border-gray-800/60">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1 px-2 font-mono">
            <span className="font-semibold text-purple-400">ATTITUDE ANGLES: ROLL (°) & PITCH (°)</span>
          </div>
          <div className="h-40 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} syncId="uav_telemetry">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="timestamp" stroke="#4b5563" tick={{ fontSize: 10, fill: '#9ca3af' }} hide />
                <YAxis stroke="#a855f7" tick={{ fontSize: 10, fill: '#a855f7' }} domain={[-35, 35]} />
                <Tooltip content={<CustomTooltip />} />
                {renderAnomalyBands()}
                <Line type="monotone" dataKey="roll" stroke="#a855f7" dot={false} strokeWidth={1.3} name="Roll (°)" isAnimationActive={false} />
                <Line type="monotone" dataKey="pitch" stroke="#f472b6" dot={false} strokeWidth={1.3} name="Pitch (°)" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Chart 4: Groundspeed & Throttle + Time Axis & Interactive Zoom Brush */}
      {(activeChannel === 'all' || activeChannel === 'dynamics') && (
        <div className="bg-gray-950/60 p-3 rounded-xl border border-gray-800/60">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1 px-2 font-mono">
            <span className="font-semibold text-teal-400">GROUNDSPEED (m/s) & THROTTLE (%)</span>
            <span className="text-gray-400">Time Navigation Brush</span>
          </div>
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} syncId="uav_telemetry">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis
                  dataKey="timestamp"
                  stroke="#6b7280"
                  tick={{ fontSize: 10, fill: '#9ca3af' }}
                  tickFormatter={(val) => `${Number(val).toFixed(0)}s`}
                />
                <YAxis yAxisId="spd" stroke="#2dd4bf" tick={{ fontSize: 10, fill: '#2dd4bf' }} domain={[0, 25]} />
                <YAxis yAxisId="thr" orientation="right" stroke="#e879f9" tick={{ fontSize: 10, fill: '#e879f9' }} domain={[0, 100]} />
                <Tooltip content={<CustomTooltip />} />
                {renderAnomalyBands()}
                <Line yAxisId="spd" type="monotone" dataKey="groundspeed" stroke="#2dd4bf" dot={false} strokeWidth={1.6} name="Speed (m/s)" isAnimationActive={false} />
                <Line yAxisId="thr" type="monotone" dataKey="throttle" stroke="#e879f9" dot={false} strokeWidth={1.2} strokeDasharray="3 3" name="Throttle (%)" isAnimationActive={false} />
                <Brush
                  dataKey="timestamp"
                  height={22}
                  stroke="#38bdf8"
                  fill="#0f172a"
                  tickFormatter={(v) => `${Number(v).toFixed(0)}s`}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};
