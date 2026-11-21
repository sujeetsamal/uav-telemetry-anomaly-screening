"""Unit tests for uavtel.clean module."""

import numpy as np
import pandas as pd
import pytest

from uavtel.clean import (
    sort_by_time,
    drop_duplicates,
    convert_units,
    resample_to_timebase,
    fill_short_gaps,
    missing_report,
    clean_telemetry,
)


def test_sort_by_time_and_drop_duplicates():
    df = pd.DataFrame(
        {
            "timestamp": [3.0, 1.0, 2.0, 2.0],
            "alt": [30.0, 10.0, 20.0, 20.0],
        }
    )
    sorted_df = sort_by_time(df)
    assert sorted_df["timestamp"].tolist() == [1.0, 2.0, 2.0, 3.0]

    dedup_df = drop_duplicates(sorted_df)
    assert dedup_df["timestamp"].tolist() == [1.0, 2.0, 3.0]
    assert len(dedup_df) == 3


def test_convert_units():
    df = pd.DataFrame(
        {
            "timestamp": [1000000000000, 1000000100000],  # microseconds
            "lat": [377749000, 377749100],  # 1e7 int degrees
            "lon": [-1224194000, -1224193900],
            "roll": [0.05, 0.08],  # radians
            "throttle": [0.55, 0.60],  # 0 to 1 ratio
        }
    )
    converted = convert_units(df)

    assert converted["timestamp"].iloc[0] == 0.0
    assert pytest.approx(converted["timestamp"].iloc[1], rel=1e-3) == 0.1
    assert pytest.approx(converted["lat"].iloc[0], rel=1e-5) == 37.7749
    assert pytest.approx(converted["lon"].iloc[0], rel=1e-5) == -122.4194
    assert converted["roll"].iloc[0] > 1.0  # converted to degrees
    assert pytest.approx(converted["throttle"].iloc[0], abs=1e-3) == 55.0  # percentage


def test_resample_to_timebase():
    # Irregular 10 Hz telemetry: timestamps at 0.0, 0.11, 0.19, 0.30
    df = pd.DataFrame(
        {
            "timestamp": [0.0, 0.11, 0.19, 0.30],
            "alt": [10.0, 11.1, 11.9, 13.0],
        }
    )
    resampled = resample_to_timebase(df, freq_hz=10.0)

    # Expected grid: 0.0, 0.1, 0.2, 0.3
    assert len(resampled) == 4
    assert np.allclose(resampled["timestamp"], [0.0, 0.1, 0.2, 0.3])
    assert pytest.approx(resampled["alt"].iloc[1], abs=0.1) == 11.0


def test_fill_short_gaps_and_missing_report():
    df = pd.DataFrame(
        {
            "timestamp": [0.0, 0.1, 0.2, 0.3],
            "alt": [10.0, np.nan, 12.0, 13.0],
            "voltage": [16.8, np.nan, np.nan, 16.5],
        }
    )

    filled = fill_short_gaps(df, max_gap_seconds=0.15, freq_hz=10.0)
    assert not np.isnan(filled["alt"].iloc[1])
    assert pytest.approx(filled["alt"].iloc[1]) == 11.0

    rep = missing_report(df)
    assert len(rep) == 3
    assert "missing_percent" in rep.columns


def test_clean_telemetry_end_to_end(sim_flight_df: pd.DataFrame):
    clean_df, meta = clean_telemetry(sim_flight_df, freq_hz=10.0)
    assert len(clean_df) > 8000
    assert meta["clean_rows"] == len(clean_df)
    assert meta["duration_sec"] >= 899.0
