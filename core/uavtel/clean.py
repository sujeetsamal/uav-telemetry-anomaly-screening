"""Data cleaning, resampling, unit conversion, and gap filling for UAV flight telemetry."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from uavtel.io import CANONICAL_COLUMNS


def sort_by_time(df: pd.DataFrame, time_col: str = "timestamp") -> pd.DataFrame:
    """Sorts dataframe chronologically by time column and resets index."""
    if time_col not in df.columns:
        raise KeyError(f"Timestamp column '{time_col}' not found in DataFrame.")
    cleaned = df.sort_values(by=time_col).reset_index(drop=True)
    return cleaned


def drop_duplicates(
    df: pd.DataFrame, time_col: str = "timestamp", keep: str = "first"
) -> pd.DataFrame:
    """Removes duplicate timestamp records."""
    if time_col not in df.columns:
        return df
    # Drop rows with duplicate timestamps
    return df.drop_duplicates(subset=[time_col], keep=keep).reset_index(drop=True)


def convert_units(df: pd.DataFrame) -> pd.DataFrame:
    """Performs heuristic unit detection and standardization.

    Standardizations:
    - Timestamps: microseconds/milliseconds converted to elapsed seconds (starting at 0.0s).
    - Coordinates: 1e7 scaled integers (PX4/ArduPilot standard) converted to decimal degrees.
    - Attitude: radians converted to degrees if roll/pitch values fall within [-pi, pi].
    - Throttle: [0, 1] normalized ratios scaled to [0, 100] percentage.
    """
    out = df.copy()

    # 1. Normalize timestamp to seconds starting from 0.0
    if "timestamp" in out.columns and len(out) > 0:
        ts = out["timestamp"].to_numpy(dtype=float)
        # Check if timestamps are microseconds (e.g. > 1e11)
        if np.nanmedian(ts) > 1e11:
            ts = ts / 1e6
        # Check if milliseconds (e.g. > 1e8)
        elif np.nanmedian(ts) > 1e8:
            ts = ts / 1e3

        # Shift to start at t = 0.0
        t0 = np.nanmin(ts)
        out["timestamp"] = ts - t0

    # 2. GPS Lat/Lon 1e7 conversion
    for coord_col in ["lat", "lon"]:
        if coord_col in out.columns:
            vals = out[coord_col].to_numpy(dtype=float)
            # If coordinates are integers in 1e7 format (e.g. 377749000 for 37.7749)
            if np.nanmax(np.abs(vals)) > 1000.0:
                out[coord_col] = vals / 1e7

    # 3. Attitude angles: radians to degrees check
    for angle_col in ["roll", "pitch"]:
        if angle_col in out.columns:
            vals = out[angle_col].to_numpy(dtype=float)
            finite_vals = vals[np.isfinite(vals)]
            if len(finite_vals) > 0 and np.max(np.abs(finite_vals)) <= (np.pi + 0.05):
                # Likely radians, convert to degrees
                out[angle_col] = np.degrees(vals)

    if "yaw" in out.columns:
        vals = out["yaw"].to_numpy(dtype=float)
        finite_vals = vals[np.isfinite(vals)]
        if len(finite_vals) > 0 and np.max(np.abs(finite_vals)) <= (2 * np.pi + 0.1):
            out["yaw"] = np.degrees(vals) % 360.0

    # 4. Throttle: scale ratio [0, 1] to percentage [0, 100]
    if "throttle" in out.columns:
        thr = out["throttle"].to_numpy(dtype=float)
        finite_thr = thr[np.isfinite(thr)]
        if len(finite_thr) > 0 and np.nanmax(finite_thr) <= 1.05 and np.nanmin(finite_thr) >= -0.05:
            out["throttle"] = np.clip(thr * 100.0, 0.0, 100.0)

    return out


def resample_to_timebase(
    df: pd.DataFrame,
    freq_hz: float = 10.0,
    time_col: str = "timestamp",
    max_gap_seconds: float = 2.0,
) -> pd.DataFrame:
    """Resamples all numerical telemetry channels to a fixed frequency grid via linear interpolation.

    Vectorized implementation:
    - Interpolates values across uniform dt grid using np.interp.
    - Automatically masks gaps larger than max_gap_seconds with NaN to prevent false extrapolation.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned telemetry dataframe with monotonic timestamp.
    freq_hz : float
        Target sampling frequency in Hz (default: 10.0 Hz).
    time_col : str
        Timestamp column name.
    max_gap_seconds : float
        Maximum allowable gap for interpolation. Gaps wider than this are left as NaN.

    Returns
    -------
    pd.DataFrame
        Uniformly resampled telemetry dataframe at freq_hz.
    """
    if len(df) < 2:
        return df.copy()

    dt = 1.0 / freq_hz
    t_raw = df[time_col].to_numpy(dtype=float)
    t_min = t_raw[0]
    t_max = t_raw[-1]

    # Target uniform time grid
    t_grid = np.arange(t_min, t_max + (dt * 0.5), dt)
    resampled_data: Dict[str, np.ndarray] = {time_col: t_grid}

    # Identify large gaps in original data
    raw_diffs = np.diff(t_raw)
    gap_indices = np.where(raw_diffs > max_gap_seconds)[0]
    gap_ranges: List[Tuple[float, float]] = [
        (t_raw[idx], t_raw[idx + 1]) for idx in gap_indices
    ]

    # Vectorized interpolation for each numerical column
    for col in df.columns:
        if col == time_col:
            continue

        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            vals = series.to_numpy(dtype=float)
            valid_mask = np.isfinite(vals) & np.isfinite(t_raw)

            if np.sum(valid_mask) >= 2:
                interp_vals = np.interp(
                    t_grid, t_raw[valid_mask], vals[valid_mask], left=np.nan, right=np.nan
                )
                # Mask out segments spanning across large gaps
                for g_start, g_end in gap_ranges:
                    gap_mask = (t_grid > g_start) & (t_grid < g_end)
                    interp_vals[gap_mask] = np.nan

                resampled_data[col] = interp_vals
            else:
                resampled_data[col] = np.full_like(t_grid, np.nan)
        else:
            # For non-numeric columns, use forward-fill nearest index mapping
            indices = np.searchsorted(t_raw, t_grid, side="right") - 1
            indices = np.clip(indices, 0, len(series) - 1)
            resampled_data[col] = series.iloc[indices].to_numpy()

    return pd.DataFrame(resampled_data)


def fill_short_gaps(
    df: pd.DataFrame, max_gap_seconds: float = 1.0, freq_hz: float = 10.0
) -> pd.DataFrame:
    """Fills short missing gaps using forward/backward linear interpolation within a sample limit."""
    limit = max(1, int(round(max_gap_seconds * freq_hz)))
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    out = df.copy()
    out[numeric_cols] = out[numeric_cols].interpolate(
        method="linear", limit=limit, limit_direction="both"
    )
    return out


def missing_report(df: pd.DataFrame) -> pd.DataFrame:
    """Generates a per-channel missingness analysis report."""
    total_rows = len(df)
    records: List[Dict[str, Any]] = []

    for col in df.columns:
        null_count = int(df[col].isna().sum())
        missing_pct = (null_count / total_rows * 100.0) if total_rows > 0 else 0.0
        records.append(
            {
                "channel": col,
                "missing_count": null_count,
                "missing_percent": round(missing_pct, 2),
                "is_complete": null_count == 0,
            }
        )

    return pd.DataFrame(records)


def clean_telemetry(
    df: pd.DataFrame, freq_hz: float = 10.0, max_gap_seconds: float = 2.0
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Runs end-to-end cleaning and standardization pipeline on raw telemetry."""
    if len(df) == 0:
        return df.copy(), {"status": "empty", "rows": 0}

    # 1. Sort by time
    df_sorted = sort_by_time(df)

    # 2. Drop duplicates
    df_dedup = drop_duplicates(df_sorted)

    # 3. Unit conversions
    df_units = convert_units(df_dedup)

    # 4. Resample to standard timebase
    df_resampled = resample_to_timebase(
        df_units, freq_hz=freq_hz, max_gap_seconds=max_gap_seconds
    )

    # 5. Fill short gaps
    df_clean = fill_short_gaps(df_resampled, max_gap_seconds=1.0, freq_hz=freq_hz)

    # 6. Generate missingness report
    rep = missing_report(df_clean)

    meta = {
        "original_rows": len(df),
        "clean_rows": len(df_clean),
        "freq_hz": freq_hz,
        "duration_sec": float(df_clean["timestamp"].iloc[-1] - df_clean["timestamp"].iloc[0])
        if len(df_clean) > 0
        else 0.0,
        "missing_report": rep.to_dict(orient="records"),
    }

    return df_clean, meta
