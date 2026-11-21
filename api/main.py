"""FastAPI backend service for UAV Flight Telemetry Analytics & Anomaly Screening."""

from __future__ import annotations

import io
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure core package is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

import uavtel

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-loads default demo flight into session on startup
    session.load_simulated(duration_sec=900.0, seed=42)
    yield


app = FastAPI(
    title="UAV Flight Telemetry Analytics & Anomaly Screening API",
    description="High-performance telemetry analytics, sensor alignment, and multi-detector screening API.",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for frontend dashboard (Vite default: http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory state store for active flight session
class FlightSessionState:
    def __init__(self) -> None:
        self.raw_df: Optional[pd.DataFrame] = None
        self.clean_df: Optional[pd.DataFrame] = None
        self.feat_df: Optional[pd.DataFrame] = None
        self.detections: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.has_ground_truth: bool = False

    def load_simulated(self, duration_sec: float = 900.0, seed: int = 42) -> Dict[str, Any]:
        """Generates and processes synthetic 15-min flight."""
        raw = uavtel.generate_synthetic_flight(duration_sec=duration_sec, freq_hz=10.0, seed=seed)
        self.raw_df = raw
        self.has_ground_truth = True

        cleaned, clean_meta = uavtel.clean_telemetry(raw, freq_hz=10.0)
        self.clean_df = cleaned

        featured = uavtel.extract_features(cleaned, freq_hz=10.0)
        self.feat_df = featured

        detections, events = uavtel.run_all_detectors(featured, freq_hz=10.0)
        self.detections = detections
        self.events = events

        self.metadata = {
            "source": "simulation_15min",
            "seed": seed,
            "duration_sec": clean_meta["duration_sec"],
            "total_samples": len(featured),
            "freq_hz": 10.0,
            "has_ground_truth": True,
        }
        return self.metadata


session = FlightSessionState()


# Pydantic models
class DetectParameters(BaseModel):
    zscore_thresh: float = 3.2
    iqr_k: float = 2.5
    ewma_mult: float = 3.0
    iso_contamination: float = 0.08
    ensemble_thresh: float = 0.35



@app.get("/")
def root() -> Dict[str, str]:
    return {
        "service": "UAV Flight Telemetry Analytics API",
        "status": "online",
        "active_dataset": session.metadata.get("source", "none"),
    }


@app.post("/demo")
def generate_demo(duration_sec: float = 900.0, seed: int = 42) -> Dict[str, Any]:
    """Generates synthetic 15-min flight log with 8 ground-truth anomalies."""
    meta = session.load_simulated(duration_sec=duration_sec, seed=seed)
    return {"status": "success", "message": "Demo flight generated and screened", "metadata": meta}


@app.post("/upload")
async def upload_log(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Uploads and ingests a raw PX4 / ArduPilot / generic CSV flight log."""
    try:
        contents = await file.read()
        raw_df, io_meta = uavtel.load_csv(contents)
        if len(raw_df) == 0:
            raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

        session.raw_df = raw_df
        session.has_ground_truth = "is_anomaly" in raw_df.columns

        clean_df, clean_meta = uavtel.clean_telemetry(raw_df, freq_hz=10.0)
        session.clean_df = clean_df

        feat_df = uavtel.extract_features(clean_df, freq_hz=10.0)
        session.feat_df = feat_df

        detections, events = uavtel.run_all_detectors(feat_df, freq_hz=10.0)
        session.detections = detections
        session.events = events

        session.metadata = {
            "filename": file.filename,
            "source": "upload",
            "duration_sec": clean_meta["duration_sec"],
            "total_samples": len(feat_df),
            "freq_hz": 10.0,
            "has_ground_truth": session.has_ground_truth,
            "mapped_columns": io_meta["mapped_columns"],
        }

        return {
            "status": "success",
            "filename": file.filename,
            "metadata": session.metadata,
            "events_count": len(events),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process telemetry file: {str(e)}")


@app.get("/summary")
def get_summary() -> Dict[str, Any]:
    """Returns high-level summary KPIs for the active flight."""
    if session.feat_df is None or len(session.feat_df) == 0:
        raise HTTPException(status_code=404, detail="No active flight data loaded.")

    df = session.feat_df
    t = df["timestamp"]
    duration_sec = float(t.iloc[-1] - t.iloc[0])

    max_alt = float(df["alt"].max()) if "alt" in df.columns else 0.0
    max_speed = float(df["groundspeed"].max()) if "groundspeed" in df.columns else 0.0
    min_voltage = float(df["voltage"].min()) if "voltage" in df.columns else 0.0
    max_current = float(df["current"].max()) if "current" in df.columns else 0.0
    total_energy_wh = float(df["energy_wh"].iloc[-1]) if "energy_wh" in df.columns else 0.0

    # Phase breakdown
    phase_counts = df["flight_phase"].value_counts(normalize=True).to_dict() if "flight_phase" in df.columns else {}
    phase_percentages = {k: round(v * 100.0, 1) for k, v in phase_counts.items()}

    # Severity counts
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for e in session.events:
        sev = e.get("severity", "medium")
        if sev in sev_counts:
            sev_counts[sev] += 1

    return {
        "duration_sec": round(duration_sec, 1),
        "total_samples": len(df),
        "freq_hz": session.metadata.get("freq_hz", 10.0),
        "max_altitude_m": round(max_alt, 1),
        "max_groundspeed_ms": round(max_speed, 1),
        "min_voltage_v": round(min_voltage, 2),
        "max_current_a": round(max_current, 1),
        "total_energy_wh": round(total_energy_wh, 2),
        "anomaly_event_count": len(session.events),
        "anomaly_severity_counts": sev_counts,
        "flight_phases": phase_percentages,
        "has_ground_truth": session.has_ground_truth,
    }


@app.get("/series")
def get_series(max_points: int = Query(default=1200, ge=100, le=5000)) -> List[Dict[str, Any]]:
    """Returns downsampled/decimated time-series data for fast rendering on frontend charts.

    Preserves anomaly spikes and peak events during decimation.
    """
    if session.feat_df is None or len(session.feat_df) == 0:
        raise HTTPException(status_code=404, detail="No active flight data loaded.")

    df = session.feat_df
    n = len(df)

    step = max(1, n // max_points)
    decimated_indices = set(range(0, n, step))

    # Also include indices where anomalies or flags occur so spikes aren't smoothed out
    if "ensemble" in session.detections:
        flags = session.detections["ensemble"][0]
        alarm_indices = np.where(flags.to_numpy())[0]
        # Sample alarm indices every 2
        decimated_indices.update(alarm_indices[::2])

    sorted_indices = sorted(decimated_indices)
    subset = df.iloc[sorted_indices].copy()

    # Extract score column if present
    if "ensemble" in session.detections:
        subset["anomaly_score"] = session.detections["ensemble"][1].iloc[sorted_indices].values
    else:
        subset["anomaly_score"] = 0.0

    # Retain core telemetry fields
    cols = [
        "timestamp",
        "alt",
        "vertical_speed",
        "groundspeed",
        "throttle",
        "voltage",
        "current",
        "power_w",
        "roll",
        "pitch",
        "yaw",
        "lat",
        "lon",
        "flight_phase",
        "anomaly_score",
    ]
    if "is_anomaly" in subset.columns:
        cols.append("is_anomaly")

    available_cols = [c for c in cols if c in subset.columns]
    records = subset[available_cols].to_dict(orient="records")

    # Round floating values for JSON payload efficiency
    for r in records:
        for k, v in r.items():
            if isinstance(v, (float, np.floating)):
                r[k] = round(float(v), 3)

    return records


@app.get("/events")
def get_events() -> List[Dict[str, Any]]:
    """Returns detected anomaly events for the active flight."""
    return session.events


@app.post("/detect")
def re_detect(params: DetectParameters) -> Dict[str, Any]:
    """Re-runs anomaly detection pipeline with custom user parameters."""
    if session.feat_df is None or len(session.feat_df) == 0:
        raise HTTPException(status_code=404, detail="No active flight data loaded.")

    detections, events = uavtel.run_all_detectors(
        df=session.feat_df,
        freq_hz=session.metadata.get("freq_hz", 10.0),
        zscore_thresh=params.zscore_thresh,
        iqr_k=params.iqr_k,
        ewma_mult=params.ewma_mult,
        iso_contamination=params.iso_contamination,
        ensemble_thresh=params.ensemble_thresh,
    )
    session.detections = detections
    session.events = events

    return {
        "status": "success",
        "events_count": len(events),
        "events": events,
    }


@app.get("/evaluate")
def get_evaluation() -> List[Dict[str, Any]]:
    """Evaluates detection methods against ground truth labels (if present)."""
    if session.feat_df is None or len(session.feat_df) == 0:
        raise HTTPException(status_code=404, detail="No active flight data loaded.")

    if not session.has_ground_truth or "is_anomaly" not in session.feat_df.columns:
        raise HTTPException(
            status_code=400,
            detail="Active dataset does not have ground-truth 'is_anomaly' labels. Evaluation requires labeled data.",
        )

    df_eval = uavtel.evaluate_all_methods(session.feat_df, session.detections)
    return df_eval.to_dict(orient="records")


@app.get("/export/events.csv")
def export_events_csv() -> Response:
    """Exports detected events as downloadable CSV."""
    if not session.events:
        df_empty = pd.DataFrame(
            columns=["event_id", "start_time", "end_time", "duration_sec", "channel", "severity", "method", "description"]
        )
        csv_str = df_empty.to_csv(index=False)
    else:
        df_events = pd.DataFrame(session.events)
        csv_str = df_events.to_csv(index=False)

    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=uav_telemetry_events.csv"},
    )


@app.get("/export/clean.csv")
def export_clean_csv() -> StreamingResponse:
    """Streams cleaned and feature-engineered telemetry as downloadable CSV."""
    if session.feat_df is None:
        raise HTTPException(status_code=404, detail="No active flight data.")

    stream = io.StringIO()
    session.feat_df.to_csv(stream, index=False)
    stream.seek(0)

    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=uav_clean_telemetry.csv"},
    )
