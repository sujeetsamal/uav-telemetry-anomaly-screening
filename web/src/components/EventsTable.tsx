import React, { useState } from 'react';
import { AlertCircle, ChevronRight, Search } from 'lucide-react';
import { TelemetryEvent } from '../types/telemetry';

interface EventsTableProps {
  events: TelemetryEvent[];
  selectedEvent: TelemetryEvent | null;
  onSelectEvent: (event: TelemetryEvent | null) => void;
}

export const EventsTable: React.FC<EventsTableProps> = ({
  events,
  selectedEvent,
  onSelectEvent,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredEvents = events.filter((evt) => {
    if (filterSeverity !== 'all' && evt.severity !== filterSeverity) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        evt.event_id.toLowerCase().includes(q) ||
        evt.description.toLowerCase().includes(q) ||
        evt.channel.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'critical':
        return 'bg-rose-950/80 text-rose-300 border-rose-800/80';
      case 'high':
        return 'bg-orange-950/80 text-orange-300 border-orange-800/80';
      case 'medium':
        return 'bg-amber-950/80 text-amber-300 border-amber-800/80';
      case 'low':
      default:
        return 'bg-blue-950/80 text-blue-300 border-blue-800/80';
    }
  };

  return (
    <div className="bg-gray-900/60 border border-gray-800/80 rounded-2xl p-4 flex flex-col h-full">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-gray-800 pb-3 mb-3">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400" />
          <h3 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
            Screened Telemetry Events ({filteredEvents.length})
          </h3>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          {/* Search box */}
          <div className="relative flex-1 sm:w-44">
            <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Filter channel / desc..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg pl-8 pr-2.5 py-1 text-xs text-gray-200 focus:outline-none focus:border-cyan-500/60 font-mono"
            />
          </div>

          {/* Severity selector */}
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-gray-950 border border-gray-800 rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-cyan-500/60 font-mono"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto max-h-[380px] rounded-xl border border-gray-800/80 bg-gray-950/50">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-gray-900/90 text-gray-400 uppercase tracking-wider sticky top-0 border-b border-gray-800">
            <tr>
              <th className="py-2.5 px-3">Event ID</th>
              <th className="py-2.5 px-3">Time Window</th>
              <th className="py-2.5 px-3">Duration</th>
              <th className="py-2.5 px-3">Severity</th>
              <th className="py-2.5 px-3">Channel</th>
              <th className="py-2.5 px-3">Score</th>
              <th className="py-2.5 px-3">Engineering Description</th>
              <th className="py-2.5 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60">
            {filteredEvents.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-gray-400 text-xs">
                  No anomaly events match current criteria.
                </td>
              </tr>
            ) : (
              filteredEvents.map((evt) => {
                const isSelected = selectedEvent?.event_id === evt.event_id;
                return (
                  <tr
                    key={evt.event_id}
                    onClick={() => onSelectEvent(isSelected ? null : evt)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-cyan-950/40 border-l-4 border-l-cyan-400'
                        : 'hover:bg-gray-900/60'
                    }`}
                  >
                    <td className="py-2.5 px-3 font-bold text-gray-200">{evt.event_id}</td>
                    <td className="py-2.5 px-3 text-gray-400">
                      {evt.start_time.toFixed(1)}s - {evt.end_time.toFixed(1)}s
                    </td>
                    <td className="py-2.5 px-3 text-gray-300 font-semibold">{evt.duration_sec}s</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${getSeverityBadge(
                          evt.severity
                        )}`}
                      >
                        {evt.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-cyan-300 font-semibold">{evt.channel}</td>
                    <td className="py-2.5 px-3 text-gray-300">{evt.peak_score.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-gray-300 max-w-xs truncate" title={evt.description}>
                      {evt.description}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-0.5 ml-auto">
                        Seek <ChevronRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
