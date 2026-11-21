export interface FlightSummary {
  duration_sec: number;
  total_samples: number;
  freq_hz: number;
  max_altitude_m: number;
  max_groundspeed_ms: number;
  min_voltage_v: number;
  max_current_a: number;
  total_energy_wh: number;
  anomaly_event_count: number;
  anomaly_severity_counts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  flight_phases: Record<string, number>;
  has_ground_truth: boolean;
}

export interface TelemetryPoint {
  timestamp: number;
  alt: number;
  vertical_speed?: number;
  groundspeed: number;
  throttle?: number;
  voltage: number;
  current?: number;
  power_w?: number;
  roll?: number;
  pitch?: number;
  yaw?: number;
  lat?: number;
  lon?: number;
  flight_phase?: string;
  anomaly_score?: number;
  is_anomaly?: boolean;
}

export interface TelemetryEvent {
  event_id: string;
  start_time: number;
  end_time: number;
  duration_sec: number;
  channel: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  method: string;
  peak_score: number;
  description: string;
}

export interface MethodEvaluation {
  method: string;
  precision: number;
  recall: number;
  f1_score: number;
  detection_delay_s: number;
  event_recall: number;
  tp: number;
  fp: number;
  fn: number;
}

export interface DetectorParameters {
  zscore_thresh: number;
  iqr_k: number;
  ewma_mult: number;
  iso_contamination: number;
  ensemble_thresh: number;
}
