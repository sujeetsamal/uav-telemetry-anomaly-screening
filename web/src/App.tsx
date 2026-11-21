import React, { useEffect, useRef, useState } from 'react';
import {
  Award,
  Download,
  FileSpreadsheet,
  Layers,
  Plane,
  RefreshCw,
  Sliders,
  Upload,
} from 'lucide-react';
import { DetectorSettings } from './components/DetectorSettings';
import { EvaluationTable } from './components/EvaluationTable';
import { EventsTable } from './components/EventsTable';
import { GpsTrack } from './components/GpsTrack';
import { SummaryCards } from './components/SummaryCards';
import { SynchronizedCharts } from './components/SynchronizedCharts';
import { api } from './services/api';
import { DetectorParameters, FlightSummary, MethodEvaluation, TelemetryEvent, TelemetryPoint } from './types/telemetry';

export const App: React.FC = () => {
  const [summary, setSummary] = useState<FlightSummary | null>(null);
  const [series, setSeries] = useState<TelemetryPoint[]>([]);
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [evaluations, setEvaluations] = useState<MethodEvaluation[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<TelemetryEvent | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'screening' | 'evaluation' | 'settings'>('screening');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load all telemetry data
  const loadData = async () => {
    try {
      setRefreshing(true);
      const [sumData, seriesData, eventsData] = await Promise.all([
        api.getSummary(),
        api.getSeries(1200),
        api.getEvents(),
      ]);

      setSummary(sumData);
      setSeries(seriesData);
      setEvents(eventsData);

      if (sumData.has_ground_truth) {
        try {
          const evalData = await api.getEvaluation();
          setEvaluations(evalData);
        } catch (e) {
          console.warn('Evaluation not available:', e);
        }
      } else {
        setEvaluations([]);
      }
    } catch (err) {
      console.error('Failed to load telemetry dataset:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Handlers
  const handleLoadDemo = async () => {
    try {
      setLoading(true);
      await api.loadDemo(900, 42);
      await loadData();
    } catch (err) {
      alert('Failed to load demo flight: ' + err);
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setLoading(true);
      await api.uploadCSV(file);
      await loadData();
    } catch (err) {
      alert('Failed to upload flight log: ' + err);
      setLoading(false);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleApplyParameters = async (params: DetectorParameters) => {
    setLoading(true);
    try {
      const updatedEvents = await api.reDetect(params);
      setEvents(updatedEvents);
      const [sumData, seriesData] = await Promise.all([api.getSummary(), api.getSeries(1200)]);
      setSummary(sumData);
      setSeries(seriesData);

      if (sumData.has_ground_truth) {
        const evalData = await api.getEvaluation();
        setEvaluations(evalData);
      }
    } catch (err) {
      alert('Failed to re-screen telemetry: ' + err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-gray-100 flex flex-col">
      {/* Top Navigation & Telemetry Console Bar */}
      <header className="border-b border-gray-800/80 bg-gray-950/80 backdrop-blur-md sticky top-0 z-50 px-4 py-3">
        <div className="max-w-[1700px] mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
          {/* Logo & Platform Info */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Plane className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold tracking-wider uppercase text-gray-100">
                  UAV Flight Telemetry Analytics
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-semibold">
                  PX4 / ArduPilot
                </span>
              </div>
              <div className="text-[11px] text-gray-400 font-mono flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span>10 Hz Fixed Timebase</span>
                <span className="text-gray-600">•</span>
                <span>Active: {summary?.has_ground_truth ? '15-min Simulated Benchmark' : 'Custom Flight Log'}</span>
              </div>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".csv,.txt"
              className="hidden"
            />

            <button
              onClick={handleLoadDemo}
              disabled={loading || refreshing}
              className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700/80 text-gray-200 hover:bg-gray-800 text-xs font-mono font-medium flex items-center gap-1.5 transition-all shadow-sm"
              title="Loads reproducible 15-min simulated flight with 8 injected anomalies"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${refreshing ? 'animate-spin' : ''}`} />
              Load 15-min Demo
            </button>

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700/80 text-gray-200 hover:bg-gray-800 text-xs font-mono font-medium flex items-center gap-1.5 transition-all shadow-sm"
            >
              <Upload className="w-3.5 h-3.5 text-blue-400" />
              Upload CSV
            </button>

            <div className="h-4 w-px bg-gray-800 mx-1"></div>

            <a
              href={api.getExportEventsUrl()}
              download="uav_telemetry_events.csv"
              className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700/80 text-gray-300 hover:text-white hover:bg-gray-800 text-xs font-mono flex items-center gap-1.5 transition-all"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-amber-400" />
              Events CSV
            </a>

            <a
              href={api.getExportCleanUrl()}
              download="uav_clean_telemetry.csv"
              className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700/80 text-gray-300 hover:text-white hover:bg-gray-800 text-xs font-mono flex items-center gap-1.5 transition-all"
            >
              <Download className="w-3.5 h-3.5 text-emerald-400" />
              Clean CSV
            </a>
          </div>
        </div>

        {/* Tab Strip */}
        <div className="max-w-[1700px] mx-auto mt-3 pt-2 border-t border-gray-900 flex items-center gap-2">
          <button
            onClick={() => setActiveTab('screening')}
            className={`px-3 py-1 rounded-md text-xs font-mono transition-all flex items-center gap-1.5 ${
              activeTab === 'screening'
                ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-semibold'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" /> Telemetry Screening & Spatial Track
          </button>
          <button
            onClick={() => setActiveTab('evaluation')}
            className={`px-3 py-1 rounded-md text-xs font-mono transition-all flex items-center gap-1.5 ${
              activeTab === 'evaluation'
                ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-semibold'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Award className="w-3.5 h-3.5" /> Benchmark Model Evaluation ({evaluations.length} Methods)
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`px-3 py-1 rounded-md text-xs font-mono transition-all flex items-center gap-1.5 ${
              activeTab === 'settings'
                ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-semibold'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" /> Screening Thresholds & Tuning
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-[1700px] mx-auto p-4 flex-1 w-full space-y-4">
        {/* KPI Cards */}
        <SummaryCards summary={summary} loading={loading} />

        {activeTab === 'screening' && (
          <div className="space-y-4">
            {/* Top row: Multi-channel charts (2/3) + GPS Track (1/3) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2">
                <SynchronizedCharts
                  data={series}
                  events={events}
                  selectedEvent={selectedEvent}
                  onSelectEvent={setSelectedEvent}
                />
              </div>
              <div className="lg:col-span-1">
                <GpsTrack
                  data={series}
                  events={events}
                  selectedEvent={selectedEvent}
                  onSelectEvent={setSelectedEvent}
                />
              </div>
            </div>

            {/* Bottom row: Screened anomaly events log */}
            <div className="w-full">
              <EventsTable
                events={events}
                selectedEvent={selectedEvent}
                onSelectEvent={setSelectedEvent}
              />
            </div>
          </div>
        )}

        {activeTab === 'evaluation' && (
          <div className="space-y-4">
            <EvaluationTable evaluations={evaluations} loading={loading} />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4 text-xs space-y-2">
                <h4 className="font-semibold text-cyan-300 font-mono uppercase">
                  Evaluation Methodology & Metrics
                </h4>
                <p className="text-gray-300 leading-relaxed">
                  Detector models are evaluated against seeded ground-truth failure modes injected into the 15-minute
                  flight simulation.
                </p>
                <ul className="list-disc list-inside space-y-1 text-gray-400 font-mono text-[11px]">
                  <li>
                    <strong className="text-gray-200">Precision:</strong> TP / (TP + FP) — fraction of alarms that are real anomalies.
                  </li>
                  <li>
                    <strong className="text-gray-200">Recall:</strong> TP / (TP + FN) — fraction of anomaly durations correctly detected.
                  </li>
                  <li>
                    <strong className="text-gray-200">F1-Score:</strong> Harmonic mean balancing precision and recall.
                  </li>
                  <li>
                    <strong className="text-gray-200">Detection Delay:</strong> Latency in seconds from anomaly onset to first alarm flag.
                  </li>
                  <li>
                    <strong className="text-gray-200">Event Recall:</strong> Percentage of distinct anomaly episodes caught by the detector.
                  </li>
                </ul>
              </div>

              <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4 text-xs space-y-2">
                <h4 className="font-semibold text-emerald-300 font-mono uppercase">
                  Injected Ground-Truth Anomaly Episodes
                </h4>
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-gray-300">
                  <div className="bg-gray-950 p-2 rounded-lg border border-gray-800">
                    <span className="text-rose-400 font-bold">1. Voltage Sag:</span> t=180-192s (cell collapse &lt;13.0V)
                  </div>
                  <div className="bg-gray-950 p-2 rounded-lg border border-gray-800">
                    <span className="text-blue-400 font-bold">2. Alt Spike:</span> t=300-306s (+36m baro step)
                  </div>
                  <div className="bg-gray-950 p-2 rounded-lg border border-gray-800">
                    <span className="text-amber-400 font-bold">3. Current Surge:</span> t=380-388s (motor stall 46A)
                  </div>
                  <div className="bg-gray-950 p-2 rounded-lg border border-gray-800">
                    <span className="text-cyan-400 font-bold">4. GPS Jump:</span> t=460-468s (+75m multipath teleport)
                  </div>
                  <div className="bg-gray-950 p-2 rounded-lg border border-gray-800">
                    <span className="text-red-400 font-bold">5. Downdraft:</span> t=540-552s (-6.8 m/s sink rate)
                  </div>
                  <div className="bg-gray-950 p-2 rounded-lg border border-gray-800">
                    <span className="text-purple-400 font-bold">6. PID Flutter:</span> t=620-635s (2.8 Hz resonance)
                  </div>
                  <div className="bg-gray-950 p-2 rounded-lg border border-gray-800">
                    <span className="text-teal-400 font-bold">7. Flatline:</span> t=705-720s (current ADC frozen)
                  </div>
                  <div className="bg-gray-950 p-2 rounded-lg border border-gray-800">
                    <span className="text-orange-400 font-bold">8. Pitot Loss:</span> t=780-792s (stall reading under power)
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="space-y-4">
            <DetectorSettings onApply={handleApplyParameters} loading={loading} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-900 bg-gray-950/90 text-gray-400 text-xs font-mono py-3 px-4">
        <div className="max-w-[1700px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            UAV Flight Telemetry Analytics & Anomaly Screening Platform • Monorepo Architecture
          </div>
          <div>
            FastAPI Backend • React 18 + TypeScript + Vite + Recharts
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
