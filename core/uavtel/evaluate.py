"""Evaluation metrics for UAV telemetry anomaly detection algorithms against ground truth."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def extract_event_windows(
    flags: pd.Series, timestamps: pd.Series, min_duration_sec: float = 0.2
) -> List[Tuple[float, float]]:
    """Extracts contiguous time intervals (start_time, end_time) from a boolean flag series."""
    flag_arr = flags.to_numpy(dtype=bool)
    t = timestamps.to_numpy(dtype=float)

    if not flag_arr.any():
        return []

    diff = np.diff(flag_arr.astype(int))
    starts = np.where(diff == 1)[0] + 1
    if flag_arr[0]:
        starts = np.insert(starts, 0, 0)

    ends = np.where(diff == -1)[0]
    if flag_arr[-1]:
        ends = np.append(ends, len(flag_arr) - 1)

    windows: List[Tuple[float, float]] = []
    for s_idx, e_idx in zip(starts, ends):
        t_s = float(t[s_idx])
        t_e = float(t[e_idx])
        if (t_e - t_s) >= min_duration_sec:
            windows.append((t_s, t_e))

    return windows


def evaluate_method(
    y_true: pd.Series,
    y_pred: pd.Series,
    timestamps: pd.Series,
    tolerance_sec: float = 2.0,
) -> Dict[str, Any]:
    """Computes point-wise and event-wise evaluation metrics.

    Parameters
    ----------
    y_true : pd.Series
        Ground-truth boolean anomaly mask.
    y_pred : pd.Series
        Predicted boolean anomaly mask.
    timestamps : pd.Series
        Time in seconds.
    tolerance_sec : float
        Tolerance window in seconds for event detection delay matching.

    Returns
    -------
    Dict[str, Any]
        Metrics dictionary containing precision, recall, f1, detection delay, and confusion matrix.
    """
    yt = y_true.to_numpy(dtype=bool)
    yp = y_pred.to_numpy(dtype=bool)

    # Point-wise confusion matrix
    tp = int(np.sum(yt & yp))
    fp = int(np.sum(~yt & yp))
    fn = int(np.sum(yt & ~yp))
    tn = int(np.sum(~yt & ~yp))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(yt) if len(yt) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    # Event-wise evaluation & detection delay
    true_events = extract_event_windows(y_true, timestamps)
    pred_events = extract_event_windows(y_pred, timestamps)

    delays: List[float] = []
    matched_true_events = 0

    for t_start, t_end in true_events:
        # Search for first prediction flag within [t_start - tolerance, t_end + tolerance]
        pred_in_window = timestamps[(timestamps >= (t_start - 0.5)) & (timestamps <= (t_end + tolerance_sec)) & y_pred]
        if len(pred_in_window) > 0:
            first_pred_t = float(pred_in_window.iloc[0])
            delay = max(0.0, first_pred_t - t_start)
            delays.append(delay)
            matched_true_events += 1

    event_recall = (matched_true_events / len(true_events)) if len(true_events) > 0 else 1.0
    mean_delay = float(np.mean(delays)) if len(delays) > 0 else 0.0

    return {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "accuracy": round(float(accuracy), 4),
        "false_positive_rate": round(float(fpr), 4),
        "detection_delay_s": round(mean_delay, 2),
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "true_event_count": len(true_events),
        "detected_event_count": matched_true_events,
        "event_recall": round(float(event_recall), 4),
    }


def evaluate_all_methods(
    df: pd.DataFrame,
    detections: Dict[str, Tuple[pd.Series, pd.Series]],
    ground_truth_col: str = "is_anomaly",
    time_col: str = "timestamp",
) -> pd.DataFrame:
    """Evaluates all baseline methods and outputs a benchmark comparison DataFrame."""
    if ground_truth_col not in df.columns:
        raise KeyError(f"Ground truth column '{ground_truth_col}' not found in dataframe.")

    y_true = df[ground_truth_col]
    t = df[time_col]
    rows: List[Dict[str, Any]] = []

    for method_name, (flags, _) in detections.items():
        metrics = evaluate_method(y_true, flags, t)
        rows.append(
            {
                "method": method_name.upper(),
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1_score": metrics["f1_score"],
                "detection_delay_s": metrics["detection_delay_s"],
                "event_recall": metrics["event_recall"],
                "tp": metrics["true_positives"],
                "fp": metrics["false_positives"],
                "fn": metrics["false_negatives"],
            }
        )

    return pd.DataFrame(rows).sort_values(by="f1_score", ascending=False).reset_index(drop=True)
