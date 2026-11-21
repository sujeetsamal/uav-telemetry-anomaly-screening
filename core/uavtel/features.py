"""Feature engineering for UAV flight telemetry: rolling stats, derivatives, electrical power, and flight phase tagging."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def compute_rolling_stats(
    df: pd.DataFrame,
    channels: Optional[List[str]] = None,
    window_seconds: float = 1.0,
    freq_hz: float = 10.0,
) -> pd.DataFrame:
    """Computes vectorized rolling mean, std, min, and max for specified telemetry channels.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned telemetry dataframe.
    channels : Optional[List[str]]
        Channels to calculate rolling metrics for. Defaults to core flight parameters.
    window_seconds : float
        Rolling window duration in seconds.
    freq_hz : float
        Sampling frequency in Hz.

    Returns
    -------
    pd.DataFrame
        Dataframe containing new rolling feature columns.
    """
    if channels is None:
        channels = ["voltage", "current", "alt", "groundspeed", "roll", "pitch", "yaw"]

    window_size = max(2, int(round(window_seconds * freq_hz)))
    features = pd.DataFrame(index=df.index)

    for ch in channels:
        if ch in df.columns:
            series = df[ch]
            rolling = series.rolling(window=window_size, min_periods=1)
            features[f"{ch}_roll_mean"] = rolling.mean()
            features[f"{ch}_roll_std"] = rolling.std().fillna(0.0)
            features[f"{ch}_roll_min"] = rolling.min()
            features[f"{ch}_roll_max"] = rolling.max()

    return features


def compute_rates_of_change(
    df: pd.DataFrame,
    time_col: str = "timestamp",
    channels: Optional[List[str]] = None,
    freq_hz: float = 10.0,
) -> pd.DataFrame:
    """Computes time derivatives (rates of change) for telemetry channels.

    Calculates vertical speed (d_alt/dt) and angular rates using np.gradient with time vector.
    """
    if channels is None:
        channels = ["alt", "groundspeed", "voltage", "roll", "pitch", "yaw"]

    features = pd.DataFrame(index=df.index)
    t = df[time_col].to_numpy(dtype=float)

    # Ensure strictly increasing time coordinates for gradient calculation
    if len(t) < 2:
        for ch in channels:
            features[f"{ch}_rate"] = 0.0
        features["vertical_speed"] = 0.0
        return features

    # If timestamps have duplicates or zero dt, fallback to uniform dt
    dt_vals = np.diff(t)
    if np.any(dt_vals <= 0.0):
        t_coord = np.arange(len(t)) * (1.0 / freq_hz)
    else:
        t_coord = t

    for ch in channels:
        if ch in df.columns:
            val = df[ch].to_numpy(dtype=float)
            grad = np.gradient(val, t_coord)
            # Smooth derivative with a small 3-sample window to reduce high frequency noise
            smoothed_grad = pd.Series(grad).rolling(window=3, min_periods=1, center=True).mean().to_numpy()
            features[f"{ch}_rate"] = smoothed_grad

    # Explicitly alias vertical_speed
    if "alt_rate" in features.columns:
        features["vertical_speed"] = features["alt_rate"]

    return features


def compute_electrical_features(
    df: pd.DataFrame, time_col: str = "timestamp"
) -> pd.DataFrame:
    """Computes instantaneous electrical power (Watts) and cumulative energy consumption (Watt-hours).

    Formulas:
    Power (W) = Voltage (V) * Current (A)
    Energy (Wh) = ∫ Power(t) dt / 3600
    """
    features = pd.DataFrame(index=df.index)

    if "voltage" in df.columns and "current" in df.columns:
        v = df["voltage"].to_numpy(dtype=float)
        i = df["current"].to_numpy(dtype=float)
        t = df[time_col].to_numpy(dtype=float)

        power_w = v * i
        features["power_w"] = power_w

        # Vectorized trapezoidal integration for cumulative energy (Wh)
        if len(t) > 1:
            dt = np.diff(t, prepend=t[0])
            p_prev = np.roll(power_w, 1)
            p_prev[0] = power_w[0]
            step_energy_joules = 0.5 * (power_w + p_prev) * dt
            cumulative_joules = np.cumsum(step_energy_joules)
            features["energy_wh"] = cumulative_joules / 3600.0
        else:
            features["energy_wh"] = 0.0
    else:
        features["power_w"] = 0.0
        features["energy_wh"] = 0.0

    return features


def tag_flight_phases(
    df: pd.DataFrame,
    vertical_speed_col: str = "vertical_speed",
    alt_col: str = "alt",
    speed_col: str = "groundspeed",
    throttle_col: str = "throttle",
) -> pd.Series:
    """Vectorized rule-based flight phase tagging.

    Phases:
    - 'ground': altitude near ground (< 3m) AND groundspeed < 2.0 m/s AND throttle low (< 20%)
    - 'climb': vertical_speed > 0.6 m/s AND altitude > 2.0m AND throttle > 25%
    - 'descent': vertical_speed < -0.6 m/s AND altitude > 2.0m
    - 'loiter': |vertical_speed| <= 0.6 m/s AND groundspeed < 6.0 m/s AND altitude >= 10.0m
    - 'cruise': |vertical_speed| <= 0.6 m/s AND groundspeed >= 6.0 m/s AND altitude >= 5.0m
    """
    n = len(df)
    phases = np.full(n, "cruise", dtype=object)

    alt = df[alt_col].to_numpy(dtype=float) if alt_col in df.columns else np.full(n, 50.0)
    vz = df[vertical_speed_col].to_numpy(dtype=float) if vertical_speed_col in df.columns else np.zeros(n)
    spd = df[speed_col].to_numpy(dtype=float) if speed_col in df.columns else np.full(n, 15.0)
    thr = df[throttle_col].to_numpy(dtype=float) if throttle_col in df.columns else np.full(n, 50.0)

    # Relative altitude above initial point
    alt_rel = alt - np.nanmin(alt)

    # Vectorized boolean conditions
    is_ground = (alt_rel < 3.0) & (spd < 3.0) & (thr < 25.0)
    is_climb = (vz > 0.6) & (alt_rel >= 2.0)
    is_descent = (vz < -0.6) & (alt_rel >= 2.0)
    is_loiter = (np.abs(vz) <= 0.6) & (spd < 6.0) & (alt_rel >= 8.0)
    is_cruise = (np.abs(vz) <= 0.6) & (spd >= 6.0) & (alt_rel >= 4.0)

    # Assign in priority order
    phases[is_cruise] = "cruise"
    phases[is_loiter] = "loiter"
    phases[is_descent] = "descent"
    phases[is_climb] = "climb"
    phases[is_ground] = "ground"

    return pd.Series(phases, index=df.index, name="flight_phase")


def extract_features(
    df: pd.DataFrame, freq_hz: float = 10.0, window_seconds: float = 1.0
) -> pd.DataFrame:
    """Orchestrates end-to-end feature extraction on cleaned telemetry data."""
    out = df.copy()

    # 1. Derivatives (including vertical_speed)
    rates_df = compute_rates_of_change(out, freq_hz=freq_hz)
    for col in rates_df.columns:
        out[col] = rates_df[col]

    # 2. Rolling stats
    rolling_df = compute_rolling_stats(
        out, window_seconds=window_seconds, freq_hz=freq_hz
    )
    for col in rolling_df.columns:
        out[col] = rolling_df[col]

    # 3. Electrical features
    elec_df = compute_electrical_features(out)
    for col in elec_df.columns:
        out[col] = elec_df[col]

    # 4. Flight phases
    out["flight_phase"] = tag_flight_phases(out)

    return out
