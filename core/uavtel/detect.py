"""Baseline anomaly detectors for UAV flight telemetry: Statistical, Control Chart, Rule-based, and Machine Learning."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler


def detect_zscore(
    series: pd.Series,
    window: int = 40,
    threshold: float = 3.2,
) -> Tuple[pd.Series, pd.Series]:
    """Rolling Z-score anomaly detector.

    Calculates: z = |x - mu_rolling| / (sigma_rolling + eps).
    Flags observations where z exceeds threshold.
    """
    rolling = series.rolling(window=window, min_periods=5)
    mean = rolling.mean()
    std = rolling.std().replace(0.0, np.nan)

    fallback_std = series.std() if series.std() > 1e-6 else 1.0
    std = std.fillna(fallback_std)
    mean = mean.fillna(series)

    z = (np.abs(series - mean) / (std + 1e-6)).fillna(0.0)
    flags = z > threshold
    score = np.clip(z / (threshold * 2.0), 0.0, 1.0)

    return flags.astype(bool), pd.Series(score, index=series.index, name="zscore_score")


def detect_iqr(
    series: pd.Series,
    window: int = 50,
    k: float = 2.5,
) -> Tuple[pd.Series, pd.Series]:
    """IQR / Tukey residual detector on rolling median."""
    rolling = series.rolling(window=window, min_periods=10)
    median = rolling.median().fillna(series)
    residual = np.abs(series - median)

    r_rolling = residual.rolling(window=window, min_periods=10)
    q25 = r_rolling.quantile(0.25).fillna(0.0)
    q75 = r_rolling.quantile(0.75).fillna(residual.std() if residual.std() > 0 else 1.0)
    iqr = np.maximum(q75 - q25, 1e-5)

    cutoff = q75 + k * iqr
    flags = residual > cutoff
    score = np.clip(residual / (cutoff + 1e-6), 0.0, 1.0)

    return flags.astype(bool), pd.Series(score, index=series.index, name="iqr_score")


def detect_ewma(
    series: pd.Series,
    span: int = 30,
    multiplier: float = 3.0,
) -> Tuple[pd.Series, pd.Series]:
    """EWMA (Exponentially Weighted Moving Average) residual control chart detector."""
    ewma_mean = series.ewm(span=span, adjust=False).mean()
    residual = series - ewma_mean
    ewma_std = residual.ewm(span=span, adjust=False).std().fillna(series.std() if series.std() > 0 else 1.0)
    ewma_std = np.maximum(ewma_std, 1e-5)

    control_limit = multiplier * ewma_std
    abs_res = np.abs(residual)
    flags = abs_res > control_limit
    score = np.clip(abs_res / (control_limit + 1e-6), 0.0, 1.0)

    return flags.astype(bool), pd.Series(score, index=series.index, name="ewma_score")


def detect_rules(
    df: pd.DataFrame,
    freq_hz: float = 10.0,
    min_voltage_under_load: float = 13.5,
    critical_voltage: float = 13.0,
    load_current_threshold: float = 10.0,
    max_vertical_speed_climb: float = 8.0,
    max_vertical_speed_descent: float = -5.0,
    max_gps_step_m: float = 25.0,
    flatline_duration_sec: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Domain-specific aerospace rule-based anomaly detector."""
    n = len(df)
    flags = np.zeros(n, dtype=bool)
    scores = np.zeros(n, dtype=float)
    rule_tags = np.full(n, "none", dtype=object)

    # 1. Battery voltage sag under load
    if "voltage" in df.columns and "current" in df.columns:
        v = df["voltage"].to_numpy(dtype=float)
        i = df["current"].to_numpy(dtype=float)

        rule_crit_v = v < critical_voltage
        rule_sag = (v < min_voltage_under_load) & (i > load_current_threshold)
        v_mask = rule_crit_v | rule_sag

        flags |= v_mask
        scores[v_mask] = np.maximum(scores[v_mask], 0.95)
        rule_tags[v_mask] = "Low Voltage Sag Under Load"

    # 2. Vertical speed limits
    vz_col = "vertical_speed" if "vertical_speed" in df.columns else ("alt_rate" if "alt_rate" in df.columns else None)
    if vz_col is not None:
        vz = df[vz_col].to_numpy(dtype=float)
        rule_vz = (vz > max_vertical_speed_climb) | (vz < max_vertical_speed_descent)
        flags |= rule_vz
        scores[rule_vz] = np.maximum(scores[rule_vz], 0.90)
        rule_tags[rule_vz] = "Excessive Vertical Speed / Downdraft"

    # 3. GPS Position Jump
    if "lat" in df.columns and "lon" in df.columns:
        lat = df["lat"].to_numpy(dtype=float)
        lon = df["lon"].to_numpy(dtype=float)
        d_lat_m = np.diff(lat, prepend=lat[0]) * 111139.0
        d_lon_m = np.diff(lon, prepend=lon[0]) * (111139.0 * np.cos(np.radians(lat)))
        step_dist = np.sqrt(d_lat_m**2 + d_lon_m**2)

        rule_gps = step_dist > max_gps_step_m
        flags |= rule_gps
        scores[rule_gps] = np.maximum(scores[rule_gps], 0.88)
        rule_tags[rule_gps] = "GPS Coordinate Teleport Jump"

    # 4. Sensor Flatline (Zero variance across rolling window)
    flatline_samples = max(5, int(round(flatline_duration_sec * freq_hz)))
    if "current" in df.columns:
        i_series = df["current"]
        i_std = i_series.rolling(window=flatline_samples, min_periods=flatline_samples).std().fillna(1.0)
        alt = df["alt"].to_numpy() if "alt" in df.columns else np.full(n, 50.0)

        rule_flat = (i_std < 1e-4) & (alt > 10.0)
        flags |= rule_flat
        scores[rule_flat] = np.maximum(scores[rule_flat], 0.75)
        rule_tags[rule_flat] = "Sensor Reading Flatline"

    # 5. Speed-Throttle Mismatch (Pitot blockage)
    if "groundspeed" in df.columns and "throttle" in df.columns and "alt" in df.columns:
        spd = df["groundspeed"].to_numpy(dtype=float)
        thr = df["throttle"].to_numpy(dtype=float)
        alt = df["alt"].to_numpy(dtype=float)

        rule_stall = (thr > 40.0) & (spd < 3.0) & (alt > 15.0)
        flags |= rule_stall
        scores[rule_stall] = np.maximum(scores[rule_stall], 0.85)
        rule_tags[rule_stall] = "Airspeed / Groundspeed Loss Under Throttle"

    return (
        pd.Series(flags, index=df.index, name="rules_flag"),
        pd.Series(scores, index=df.index, name="rules_score"),
        pd.Series(rule_tags, index=df.index, name="rules_triggered"),
    )


def detect_isolation_forest(
    df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    contamination: float = 0.08,
    random_state: int = 42,
) -> Tuple[pd.Series, pd.Series]:
    """Multivariate Isolation Forest baseline anomaly detector."""
    if feature_cols is None:
        candidate_cols = [
            "voltage",
            "current",
            "alt",
            "groundspeed",
            "roll",
            "pitch",
            "vertical_speed",
            "power_w",
        ]
        feature_cols = [c for c in candidate_cols if c in df.columns]

    if len(feature_cols) == 0:
        n = len(df)
        return (
            pd.Series(np.zeros(n, dtype=bool), index=df.index),
            pd.Series(np.zeros(n, dtype=float), index=df.index),
        )

    X = df[feature_cols].copy().ffill().bfill().fillna(0.0)
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=100,
        n_jobs=-1,
    )
    iso.fit(X_scaled)

    raw_scores = -iso.decision_function(X_scaled)
    preds = iso.predict(X_scaled)
    flags = preds == -1

    min_s, max_s = np.min(raw_scores), np.max(raw_scores)
    score_range = max_s - min_s if (max_s - min_s) > 1e-6 else 1.0
    norm_score = np.clip((raw_scores - min_s) / score_range, 0.0, 1.0)

    return (
        pd.Series(flags, index=df.index, name="iforest_flag"),
        pd.Series(norm_score, index=df.index, name="iforest_score"),
    )


def detect_ensemble(
    flags_dict: Dict[str, pd.Series],
    scores_dict: Dict[str, pd.Series],
    weights: Optional[Dict[str, float]] = None,
    vote_threshold: float = 0.35,
) -> Tuple[pd.Series, pd.Series]:
    """Weighted ensemble voting combining statistical, control-chart, rule-based, and ML detectors."""
    if weights is None:
        # Default to equal weighting across provided score channels if custom, or balanced defaults
        weights = {k: 1.0 / len(scores_dict) for k in scores_dict}

    active_keys = [k for k in weights.keys() if k in scores_dict]
    if len(active_keys) == 0:
        active_keys = list(scores_dict.keys())
        weights = {k: 1.0 / len(active_keys) for k in active_keys}

    total_w = sum(weights[k] for k in active_keys)
    norm_w = {k: weights[k] / total_w for k in active_keys}

    first_series = next(iter(scores_dict.values()))
    combined_scores = pd.Series(0.0, index=first_series.index)

    for k in active_keys:
        s = scores_dict[k].fillna(0.0)
        combined_scores += norm_w[k] * s

    flags = combined_scores >= vote_threshold
    return flags.astype(bool), combined_scores.rename("ensemble_score")


def merge_flags_to_events(
    flags: pd.Series,
    scores: pd.Series,
    df: pd.DataFrame,
    method: str = "ensemble",
    min_duration_sec: float = 0.3,
    max_merge_gap_sec: float = 1.0,
    freq_hz: float = 10.0,
) -> List[Dict[str, Any]]:
    """Groups contiguous and near-adjacent alarm flags into discrete structured events."""
    if not flags.any():
        return []

    t = df["timestamp"].to_numpy(dtype=float)
    flag_arr = flags.to_numpy(dtype=bool)
    score_arr = scores.to_numpy(dtype=float)

    diff = np.diff(flag_arr.astype(int))
    starts = np.where(diff == 1)[0] + 1
    if flag_arr[0]:
        starts = np.insert(starts, 0, 0)

    ends = np.where(diff == -1)[0]
    if flag_arr[-1]:
        ends = np.append(ends, len(flag_arr) - 1)

    if len(starts) == 0:
        return []

    merged_segments: List[Tuple[int, int]] = []
    curr_start, curr_end = starts[0], ends[0]

    for next_start, next_end in zip(starts[1:], ends[1:]):
        gap_sec = t[next_start] - t[curr_end]
        if gap_sec <= max_merge_gap_sec:
            curr_end = next_end
        else:
            merged_segments.append((curr_start, curr_end))
            curr_start, curr_end = next_start, next_end
    merged_segments.append((curr_start, curr_end))

    events: List[Dict[str, Any]] = []
    evt_counter = 1

    for s_idx, e_idx in merged_segments:
        start_t = float(t[s_idx])
        end_t = float(t[e_idx])
        duration = round(end_t - start_t, 2)

        if duration < min_duration_sec:
            continue

        seg_scores = score_arr[s_idx : e_idx + 1]
        peak_score = float(np.max(seg_scores)) if len(seg_scores) > 0 else 0.5

        if peak_score >= 0.85:
            severity = "critical"
        elif peak_score >= 0.65:
            severity = "high"
        elif peak_score >= 0.45:
            severity = "medium"
        else:
            severity = "low"

        candidate_channels = ["voltage", "current", "alt", "groundspeed", "roll", "pitch"]
        best_ch = "multi"
        best_dev = -1.0

        for ch in candidate_channels:
            if ch in df.columns:
                ch_vals = df[ch].iloc[s_idx : e_idx + 1].to_numpy()
                global_std = df[ch].std()
                if global_std > 1e-4:
                    ch_dev = np.max(np.abs(ch_vals - df[ch].mean())) / global_std
                    if ch_dev > best_dev:
                        best_dev = ch_dev
                        best_ch = ch

        desc = f"{method.upper()}: Suspected {best_ch} anomaly lasting {duration}s (peak score {peak_score:.2f})."
        if "rules_triggered" in df.columns and method in ["rules", "ensemble"]:
            trig_rules = df["rules_triggered"].iloc[s_idx : e_idx + 1]
            non_none = trig_rules[trig_rules != "none"]
            if len(non_none) > 0:
                desc = f"{non_none.iloc[0]} ({duration}s, score {peak_score:.2f})"

        events.append(
            {
                "event_id": f"EVT-{evt_counter:03d}",
                "start_time": round(start_t, 2),
                "end_time": round(end_t, 2),
                "duration_sec": duration,
                "channel": best_ch,
                "severity": severity,
                "method": method,
                "peak_score": round(peak_score, 3),
                "description": desc,
            }
        )
        evt_counter += 1

    return events


def _run_multichannel_detector(
    df: pd.DataFrame,
    detector_func: Any,
    channels: List[str],
    **kwargs: Any,
) -> Tuple[pd.Series, pd.Series]:
    """Helper to run a univariate detector across multiple channels and combine via maximum severity."""
    combined_flags = pd.Series(False, index=df.index)
    combined_scores = pd.Series(0.0, index=df.index)

    for ch in channels:
        if ch in df.columns:
            f, s = detector_func(df[ch], **kwargs)
            combined_flags |= f
            combined_scores = np.maximum(combined_scores, s)

    return combined_flags, combined_scores


def run_all_detectors(
    df: pd.DataFrame,
    freq_hz: float = 10.0,
    zscore_thresh: float = 3.2,
    iqr_k: float = 2.5,
    ewma_mult: float = 3.0,
    iso_contamination: float = 0.08,
    ensemble_thresh: float = 0.35,
) -> Tuple[Dict[str, Tuple[pd.Series, pd.Series]], List[Dict[str, Any]]]:
    """Runs the complete suite of statistical, rule-based, ML, and ensemble detectors."""
    results: Dict[str, Tuple[pd.Series, pd.Series]] = {}

    key_channels = [c for c in ["voltage", "current", "alt", "groundspeed", "roll", "pitch"] if c in df.columns]

    # 1. Rolling Z-Score across key channels
    flags_z, score_z = _run_multichannel_detector(
        df, detect_zscore, key_channels, threshold=zscore_thresh
    )
    results["zscore"] = (flags_z, score_z)

    # 2. IQR / Tukey across key channels
    flags_iqr, score_iqr = _run_multichannel_detector(
        df, detect_iqr, key_channels, k=iqr_k
    )
    results["iqr"] = (flags_iqr, score_iqr)

    # 3. EWMA Control Chart across key channels
    flags_ewma, score_ewma = _run_multichannel_detector(
        df, detect_ewma, key_channels, multiplier=ewma_mult
    )
    results["ewma"] = (flags_ewma, score_ewma)

    # 4. Rules
    flags_rules, score_rules, rule_tags = detect_rules(df, freq_hz=freq_hz)
    results["rules"] = (flags_rules, score_rules)
    df["rules_triggered"] = rule_tags

    # 5. Isolation Forest
    flags_iso, score_iso = detect_isolation_forest(df, contamination=iso_contamination)
    results["iforest"] = (flags_iso, score_iso)

    # 6. Ensemble
    flags_dict = {k: v[0] for k, v in results.items()}
    scores_dict = {k: v[1] for k, v in results.items()}
    flags_ens, score_ens = detect_ensemble(
        flags_dict, scores_dict, vote_threshold=ensemble_thresh
    )
    results["ensemble"] = (flags_ens, score_ens)

    # Group ensemble flags into structured events
    events = merge_flags_to_events(
        flags=flags_ens,
        scores=score_ens,
        df=df,
        method="ensemble",
        freq_hz=freq_hz,
    )

    return results, events
