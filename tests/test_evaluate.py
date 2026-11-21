"""Unit tests for uavtel.evaluate module."""

import numpy as np
import pandas as pd
import pytest

from uavtel.evaluate import evaluate_method, evaluate_all_methods


def test_evaluate_method_perfect_match():
    y_true = pd.Series([False, False, True, True, True, False, False])
    y_pred = pd.Series([False, False, True, True, True, False, False])
    t = pd.Series([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6])

    metrics = evaluate_method(y_true, y_pred, t)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["detection_delay_s"] == 0.0
    assert metrics["true_positives"] == 3
    assert metrics["false_positives"] == 0


def test_evaluate_method_with_delay():
    # Ground truth starts at t = 0.2s, prediction alarms at t = 0.4s
    y_true = pd.Series([False, False, True, True, True, False])
    y_pred = pd.Series([False, False, False, False, True, False])
    t = pd.Series([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])

    metrics = evaluate_method(y_true, y_pred, t)
    assert metrics["true_positives"] == 1
    assert metrics["false_negatives"] == 2
    assert pytest.approx(metrics["detection_delay_s"], abs=0.01) == 0.20


def test_evaluate_all_methods(featured_flight_df: pd.DataFrame):
    t = featured_flight_df["timestamp"]
    n = len(t)

    # Create dummy detections
    d1_flags = featured_flight_df["is_anomaly"].copy()
    d1_scores = d1_flags.astype(float)

    d2_flags = pd.Series(False, index=featured_flight_df.index)
    d2_scores = pd.Series(0.0, index=featured_flight_df.index)

    detections = {
        "perfect": (d1_flags, d1_scores),
        "silent": (d2_flags, d2_scores),
    }

    df_eval = evaluate_all_methods(featured_flight_df, detections)
    assert len(df_eval) == 2
    assert "method" in df_eval.columns
    assert "f1_score" in df_eval.columns
    assert df_eval.iloc[0]["f1_score"] >= df_eval.iloc[1]["f1_score"]
