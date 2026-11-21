"""Unit tests for uavtel.sim module."""

import numpy as np
import pandas as pd
import pytest

from uavtel.sim import generate_synthetic_flight


def test_sim_flight_reproducibility():
    df1 = generate_synthetic_flight(duration_sec=60.0, freq_hz=10.0, seed=123)
    df2 = generate_synthetic_flight(duration_sec=60.0, freq_hz=10.0, seed=123)
    pd.testing.assert_frame_equal(df1, df2)


def test_sim_flight_duration_and_columns():
    df = generate_synthetic_flight(duration_sec=900.0, freq_hz=10.0, seed=42)
    assert len(df) == 9001  # (900 * 10) + 1 points
    assert "timestamp" in df.columns
    assert "lat" in df.columns
    assert "lon" in df.columns
    assert "alt" in df.columns
    assert "groundspeed" in df.columns
    assert "voltage" in df.columns
    assert "current" in df.columns
    assert "is_anomaly" in df.columns
    assert "anomaly_type" in df.columns


def test_sim_flight_anomalies_injected():
    df = generate_synthetic_flight(duration_sec=900.0, freq_hz=10.0, seed=42)
    anomaly_mask = df["is_anomaly"]
    assert anomaly_mask.sum() > 500  # At 10Hz, ~8 anomalies of 6-15s = ~80s = ~800 points

    types = set(df.loc[anomaly_mask, "anomaly_type"].unique())
    expected_types = {
        "voltage_sag",
        "altitude_spike",
        "current_spike",
        "gps_jump",
        "excessive_sink_rate",
        "attitude_oscillation",
        "sensor_flatline",
        "airspeed_loss",
    }
    assert expected_types.issubset(types)


def test_sim_battery_sag_physics():
    df = generate_synthetic_flight(duration_sec=900.0, freq_hz=10.0, seed=42)
    # Under steady cruise (constant SOC window 150-250s), current fluctuations cause instant IR voltage sag (dV/dI < 0)
    cruise_segment = df[(df["timestamp"] >= 150.0) & (df["timestamp"] <= 250.0) & (~df["is_anomaly"])]
    # Check that differential changes in voltage are negatively correlated with differential changes in current
    dv = np.diff(cruise_segment["voltage"].to_numpy())
    di = np.diff(cruise_segment["current"].to_numpy())
    corr = np.corrcoef(dv, di)[0, 1]
    assert corr < -0.3  # Dynamic IR drop: dV = -R * dI
