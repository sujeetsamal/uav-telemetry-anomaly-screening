"""Unit tests for uavtel.detect module."""

import numpy as np
import pandas as pd
import pytest

from uavtel.detect import (
    detect_zscore,
    detect_iqr,
    detect_ewma,
    detect_rules,
    detect_isolation_forest,
    detect_ensemble,
    merge_flags_to_events,
    run_all_detectors,
)


def test_detect_zscore():
    clean_series = pd.Series([10.0] * 100)
    # Inject spike
    clean_series[50] = 50.0

    flags, scores = detect_zscore(clean_series, threshold=3.0)
    assert flags.iloc[50] is True or flags.iloc[50] == np.bool_(True)
    assert scores.iloc[50] > 0.5


def test_detect_iqr():
    series = pd.Series(np.random.normal(15.0, 0.2, 100))
    series.iloc[60] = 30.0  # Massive outlier

    flags, scores = detect_iqr(series, k=2.5)
    assert flags.iloc[60] is True or flags.iloc[60] == np.bool_(True)
    assert scores.iloc[60] > 0.5


def test_detect_ewma():
    series = pd.Series(np.linspace(10.0, 15.0, 100))
    series.iloc[70] = 35.0

    flags, scores = detect_ewma(series, multiplier=3.0)
    assert flags.iloc[70] is True or flags.iloc[70] == np.bool_(True)


def test_detect_rules_voltage_sag():
    df = pd.DataFrame(
        {
            "timestamp": [0.0, 0.1, 0.2],
            "voltage": [16.0, 12.8, 16.0],  # Critical voltage drop
            "current": [15.0, 25.0, 15.0],
            "alt": [50.0, 50.0, 50.0],
            "vertical_speed": [0.0, 0.0, 0.0],
            "groundspeed": [15.0, 15.0, 15.0],
            "throttle": [50.0, 50.0, 50.0],
            "lat": [37.77, 37.77, 37.77],
            "lon": [-122.41, -122.41, -122.41],
        }
    )
    flags, scores, tags = detect_rules(df)
    assert flags.iloc[1] is True or flags.iloc[1] == np.bool_(True)
    assert "Voltage" in tags.iloc[1]


def test_detect_isolation_forest(featured_flight_df: pd.DataFrame):
    flags, scores = detect_isolation_forest(featured_flight_df, contamination=0.08)
    assert len(flags) == len(featured_flight_df)
    assert flags.sum() > 0
    assert 0.0 <= scores.min() and scores.max() <= 1.0


def test_detect_ensemble():
    n = 50
    f1 = pd.Series([False] * n)
    f2 = pd.Series([False] * n)
    f1.iloc[10:15] = True
    f2.iloc[12:17] = True

    s1 = pd.Series(0.1, index=range(n))
    s2 = pd.Series(0.1, index=range(n))
    s1.iloc[10:15] = 0.9
    s2.iloc[12:17] = 0.9

    flags, score = detect_ensemble(
        {"m1": f1, "m2": f2},
        {"m1": s1, "m2": s2},
        vote_threshold=0.4,
    )
    # Overlapping region should trigger
    assert flags.iloc[13] is True or flags.iloc[13] == np.bool_(True)


def test_merge_flags_to_events():
    df = pd.DataFrame(
        {
            "timestamp": np.arange(0.0, 10.0, 0.1),
            "voltage": [16.0] * 100,
            "current": [10.0] * 100,
        }
    )
    flags = pd.Series([False] * 100)
    scores = pd.Series([0.1] * 100)

    # Trigger alarm between t = 2.0s and t = 4.0s (indices 20 to 40)
    flags.iloc[20:41] = True
    scores.iloc[20:41] = 0.88

    events = merge_flags_to_events(flags, scores, df, method="test")
    assert len(events) == 1
    evt = events[0]
    assert evt["start_time"] == 2.0
    assert evt["end_time"] == 4.0
    assert evt["severity"] == "critical"
