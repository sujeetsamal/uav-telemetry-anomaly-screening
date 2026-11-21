"""Unit tests for uavtel.features module."""

import numpy as np
import pandas as pd
import pytest

from uavtel.features import (
    compute_rolling_stats,
    compute_rates_of_change,
    compute_electrical_features,
    tag_flight_phases,
    extract_features,
)


def test_compute_rolling_stats():
    df = pd.DataFrame(
        {
            "voltage": [16.8, 16.7, 16.6, 16.5, 16.4],
            "current": [10.0, 12.0, 14.0, 16.0, 18.0],
        }
    )
    feats = compute_rolling_stats(df, channels=["voltage"], window_seconds=0.3, freq_hz=10.0)

    assert "voltage_roll_mean" in feats.columns
    assert "voltage_roll_std" in feats.columns
    assert "voltage_roll_min" in feats.columns
    assert "voltage_roll_max" in feats.columns
    assert feats["voltage_roll_max"].iloc[-1] <= 16.8


def test_compute_rates_of_change():
    t = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    alt = np.array([10.0, 10.5, 11.0, 11.5, 12.0])  # d_alt/dt = 5.0 m/s
    df = pd.DataFrame({"timestamp": t, "alt": alt})

    rates = compute_rates_of_change(df, freq_hz=10.0)
    assert "vertical_speed" in rates.columns
    assert pytest.approx(rates["vertical_speed"].iloc[2], abs=0.2) == 5.0


def test_compute_electrical_features():
    df = pd.DataFrame(
        {
            "timestamp": [0.0, 1.0, 2.0, 3.0],
            "voltage": [16.0, 16.0, 16.0, 16.0],
            "current": [10.0, 10.0, 10.0, 10.0],
        }
    )
    # Power = 160 W. In 3 seconds, energy = 160 * 3 / 3600 = 0.1333 Wh
    elec = compute_electrical_features(df)
    assert np.all(elec["power_w"] == 160.0)
    assert pytest.approx(elec["energy_wh"].iloc[-1], abs=1e-3) == 0.1333


def test_tag_flight_phases():
    df = pd.DataFrame(
        {
            "alt": [0.0, 20.0, 100.0, 80.0, 0.5],
            "vertical_speed": [0.0, 3.0, 0.0, -2.5, 0.0],
            "groundspeed": [0.0, 12.0, 18.0, 14.0, 0.2],
            "throttle": [0.0, 75.0, 50.0, 25.0, 0.0],
        }
    )
    phases = tag_flight_phases(df)
    assert phases.iloc[0] == "ground"
    assert phases.iloc[1] == "climb"
    assert phases.iloc[2] == "cruise"
    assert phases.iloc[3] == "descent"
    assert phases.iloc[4] == "ground"


def test_extract_features_end_to_end(cleaned_flight_df: pd.DataFrame):
    featured = extract_features(cleaned_flight_df, freq_hz=10.0)
    assert "vertical_speed" in featured.columns
    assert "power_w" in featured.columns
    assert "energy_wh" in featured.columns
    assert "flight_phase" in featured.columns
    assert "voltage_roll_mean" in featured.columns
