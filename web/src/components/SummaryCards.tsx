import React from 'react';
import { Activity, AlertTriangle, BatteryCharging, Compass, Gauge, Zap } from 'lucide-react';
import { FlightSummary } from '../types/telemetry';

interface SummaryCardsProps {
  summary: FlightSummary | null;
  loading: boolean;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({ summary, loading }) => {
  if (loading || !summary) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 animate-pulse">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-800/60 rounded-xl border border-gray-700/50"></div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: 'Flight Duration',
      value: `${Math.floor(summary.duration_sec / 60)}m ${Math.round(summary.duration_sec % 60)}s`,
      sub: `${summary.total_samples.toLocaleString()} samples @ ${summary.freq_hz}Hz`,
      icon: Activity,
      color: 'text-cyan-400',
      bg: 'bg-cyan-500/10 border-cyan-500/20',
    },
    {
      label: 'Max Altitude',
      value: `${summary.max_altitude_m} m`,
      sub: `AGL ceiling`,
      icon: Compass,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10 border-blue-500/20',
    },
    {
      label: 'Max Groundspeed',
      value: `${summary.max_groundspeed_ms} m/s`,
      sub: `${(summary.max_groundspeed_ms * 3.6).toFixed(1)} km/h`,
      icon: Gauge,
      color: 'text-teal-400',
      bg: 'bg-teal-500/10 border-teal-500/20',
    },
    {
      label: 'Min Battery Voltage',
      value: `${summary.min_voltage_v} V`,
      sub: `Max load: ${summary.max_current_a} A`,
      icon: BatteryCharging,
      color: summary.min_voltage_v < 13.5 ? 'text-rose-400' : 'text-emerald-400',
      bg: summary.min_voltage_v < 13.5 ? 'bg-rose-500/10 border-rose-500/20' : 'bg-emerald-500/10 border-emerald-500/20',
    },
    {
      label: 'Cumulative Energy',
      value: `${summary.total_energy_wh} Wh`,
      sub: `4S LiPo consumption`,
      icon: Zap,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10 border-amber-500/20',
    },
    {
      label: 'Screened Anomalies',
      value: `${summary.anomaly_event_count}`,
      sub: `${summary.anomaly_severity_counts.critical} crit, ${summary.anomaly_severity_counts.high} high`,
      icon: AlertTriangle,
      color: summary.anomaly_event_count > 0 ? 'text-rose-400' : 'text-emerald-400',
      bg: summary.anomaly_event_count > 0 ? 'bg-rose-500/15 border-rose-500/30' : 'bg-emerald-500/10 border-emerald-500/20',
    },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {cards.map((c, i) => {
          const Icon = c.icon;
          return (
            <div
              key={i}
              className={`p-3.5 rounded-xl border ${c.bg} backdrop-blur-sm transition-all hover:border-gray-600/60`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">{c.label}</span>
                <Icon className={`w-4 h-4 ${c.color}`} />
              </div>
              <div className={`text-xl font-bold font-mono tracking-tight ${c.color}`}>{c.value}</div>
              <div className="text-[11px] text-gray-400 mt-1 truncate">{c.sub}</div>
            </div>
          );
        })}
      </div>

      {/* Flight Phase Distribution Bar */}
      {summary.flight_phases && Object.keys(summary.flight_phases).length > 0 && (
        <div className="bg-gray-900/70 border border-gray-800 rounded-xl p-3 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
          <span className="text-gray-400 font-medium whitespace-nowrap">Flight Phase Breakdown:</span>
          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            {Object.entries(summary.flight_phases).map(([phase, pct]) => {
              const phaseBadgeColors: Record<string, string> = {
                ground: 'bg-gray-800 text-gray-300 border-gray-700',
                climb: 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60',
                cruise: 'bg-blue-950/80 text-blue-300 border-blue-800/60',
                loiter: 'bg-purple-950/80 text-purple-300 border-purple-800/60',
                descent: 'bg-amber-950/80 text-amber-300 border-amber-800/60',
              };
              return (
                <span
                  key={phase}
                  className={`px-2.5 py-1 rounded-md border text-[11px] font-mono flex items-center gap-1.5 ${
                    phaseBadgeColors[phase] || 'bg-gray-800 text-gray-300 border-gray-700'
                  }`}
                >
                  <span className="capitalize font-semibold">{phase}:</span>
                  <span>{pct}%</span>
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
