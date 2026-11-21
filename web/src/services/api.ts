import { DetectorParameters, FlightSummary, MethodEvaluation, TelemetryEvent, TelemetryPoint } from '../types/telemetry';

const API_BASE = '/api';

export const api = {
  async getSummary(): Promise<FlightSummary> {
    const res = await fetch(`${API_BASE}/summary`);
    if (!res.ok) throw new Error('Failed to fetch summary');
    return res.json();
  },

  async getSeries(maxPoints = 1200): Promise<TelemetryPoint[]> {
    const res = await fetch(`${API_BASE}/series?max_points=${maxPoints}`);
    if (!res.ok) throw new Error('Failed to fetch series data');
    return res.json();
  },

  async getEvents(): Promise<TelemetryEvent[]> {
    const res = await fetch(`${API_BASE}/events`);
    if (!res.ok) throw new Error('Failed to fetch events');
    return res.json();
  },

  async getEvaluation(): Promise<MethodEvaluation[]> {
    const res = await fetch(`${API_BASE}/evaluate`);
    if (!res.ok) throw new Error('Failed to fetch evaluation metrics');
    return res.json();
  },

  async loadDemo(durationSec = 900, seed = 42): Promise<void> {
    const res = await fetch(`${API_BASE}/demo?duration_sec=${durationSec}&seed=${seed}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to generate demo flight');
  },

  async uploadCSV(file: File): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload flight log');
  },

  async reDetect(params: DetectorParameters): Promise<TelemetryEvent[]> {
    const res = await fetch(`${API_BASE}/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok) throw new Error('Failed to run detector screening');
    const data = await res.json();
    return data.events;
  },

  getExportEventsUrl(): string {
    return `${API_BASE}/export/events.csv`;
  },

  getExportCleanUrl(): string {
    return `${API_BASE}/export/clean.csv`;
  },
};
