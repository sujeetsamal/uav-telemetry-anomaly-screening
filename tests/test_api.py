"""Integration tests for FastAPI endpoints."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

import io
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"


def test_api_demo_and_summary():
    # 1. Trigger demo simulation
    demo_resp = client.post("/demo?duration_sec=300&seed=42")
    assert demo_resp.status_code == 200
    assert demo_resp.json()["status"] == "success"

    # 2. Get summary
    sum_resp = client.get("/summary")
    assert sum_resp.status_code == 200
    summary = sum_resp.json()
    assert summary["duration_sec"] >= 299.0
    assert summary["max_altitude_m"] > 0
    assert summary["min_voltage_v"] > 0
    assert summary["total_energy_wh"] > 0
    assert summary["has_ground_truth"] is True


def test_api_series():
    resp = client.get("/series?max_points=500")
    assert resp.status_code == 200
    series = resp.json()
    assert isinstance(series, list)
    assert len(series) > 100
    # Check fields
    pt = series[0]
    assert "timestamp" in pt
    assert "alt" in pt
    assert "voltage" in pt
    assert "groundspeed" in pt


def test_api_events_and_redetect():
    # 1. Get initial events
    resp = client.get("/events")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)

    # 2. Re-detect with custom parameters
    detect_resp = client.post(
        "/detect",
        json={
            "zscore_thresh": 2.8,
            "iqr_k": 2.0,
            "ewma_mult": 2.5,
            "iso_contamination": 0.05,
            "ensemble_thresh": 0.30,
        },
    )
    assert detect_resp.status_code == 200
    data = detect_resp.json()
    assert data["status"] == "success"
    assert "events" in data


def test_api_evaluate():
    resp = client.get("/evaluate")
    assert resp.status_code == 200
    eval_list = resp.json()
    assert isinstance(eval_list, list)
    assert len(eval_list) > 0
    first = eval_list[0]
    assert "method" in first
    assert "f1_score" in first
    assert "precision" in first
    assert "recall" in first


def test_api_export_csv():
    # Export events CSV
    evt_resp = client.get("/export/events.csv")
    assert evt_resp.status_code == 200
    assert "text/csv" in evt_resp.headers["content-type"]
    assert b"event_id" in evt_resp.content

    # Export clean CSV
    clean_resp = client.get("/export/clean.csv")
    assert clean_resp.status_code == 200
    assert "text/csv" in clean_resp.headers["content-type"]
    assert b"timestamp" in clean_resp.content


def test_api_upload_csv(messy_px4_csv_bytes: bytes):
    files = {"file": ("flight_log.csv", io.BytesIO(messy_px4_csv_bytes), "text/csv")}
    resp = client.post("/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["filename"] == "flight_log.csv"
