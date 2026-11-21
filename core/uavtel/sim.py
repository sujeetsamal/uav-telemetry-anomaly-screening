"""Realistic synthetic UAV flight simulator with battery electrodynamics, flight phases, GPS drift, and injected anomalies."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def generate_synthetic_flight(
    duration_sec: float = 900.0,
    freq_hz: float = 10.0,
    seed: int = 42,
    base_lat: float = 37.6188,
    base_lon: float = -122.3750,
) -> pd.DataFrame:
    """Generates a reproducible UAV flight with realistic physics and 8 injected anomalies.

    Physics model:
    - Trajectory: Ground idle -> Takeoff & Climb -> Cruise 1 -> Loiter (Circle) -> Cruise 2 -> Descent -> Flare & Land -> Ground
    - Aerodynamics & Attitude: Banked turns produce coordinated roll, climb induces positive pitch.
    - Battery electrodynamics: 4S LiPo discharge with state-of-charge (SOC) dependent open-circuit
      voltage and internal resistance IR sag: V_terminal = V_oc(SOC) - I * R_int.
    - GPS: Projected coordinates from local North-East frame with Gaussian multi-path jitter.
    """
    rng = np.random.default_rng(seed)

    # 1. Uniform time vector
    t = np.arange(0.0, duration_sec + (1.0 / freq_hz) * 0.5, 1.0 / freq_hz)
    n = len(t)

    # 2. Base flight profiles
    alt = np.zeros(n)
    groundspeed = np.zeros(n)
    throttle = np.zeros(n)
    roll = np.zeros(n)
    pitch = np.zeros(n)
    yaw = np.zeros(n)

    for i, cur_t in enumerate(t):
        if cur_t < 30.0:
            alt[i] = 0.0 + rng.normal(0, 0.05)
            groundspeed[i] = 0.0
            throttle[i] = 0.0
            roll[i] = rng.normal(0, 0.2)
            pitch[i] = 1.5 + rng.normal(0, 0.2)
            yaw[i] = 90.0
        elif cur_t < 140.0:
            progress = (cur_t - 30.0) / 110.0
            alt[i] = 110.0 * progress + rng.normal(0, 0.2)
            groundspeed[i] = 5.0 + 10.0 * np.sin(progress * np.pi / 2.0) + rng.normal(0, 0.15)
            throttle[i] = 78.0 - 10.0 * progress + rng.normal(0, 0.5)
            pitch[i] = 8.5 * (1.0 - 0.4 * progress) + rng.normal(0, 0.3)
            roll[i] = rng.normal(0, 0.4)
            yaw[i] = 90.0 + rng.normal(0, 0.3)
        elif cur_t < 360.0:
            alt[i] = 110.0 + 2.0 * np.sin((cur_t - 140.0) / 25.0) + rng.normal(0, 0.2)
            groundspeed[i] = 17.5 + rng.normal(0, 0.25)
            throttle[i] = 52.0 + rng.normal(0, 0.6)
            pitch[i] = 1.0 + rng.normal(0, 0.3)
            roll[i] = rng.normal(0, 0.4)
            yaw[i] = 90.0 + rng.normal(0, 0.4)
        elif cur_t < 480.0:
            turn_progress = (cur_t - 360.0) / 120.0
            alt[i] = 110.0 + rng.normal(0, 0.25)
            groundspeed[i] = 15.0 + rng.normal(0, 0.2)
            throttle[i] = 56.0 + rng.normal(0, 0.5)
            roll[i] = 22.0 + rng.normal(0, 0.5)
            pitch[i] = 2.0 + rng.normal(0, 0.3)
            yaw[i] = (90.0 + turn_progress * 360.0 * 2.0) % 360.0
        elif cur_t < 660.0:
            alt[i] = 100.0 + 1.5 * np.cos((cur_t - 480.0) / 30.0) + rng.normal(0, 0.2)
            groundspeed[i] = 18.0 + rng.normal(0, 0.25)
            throttle[i] = 51.0 + rng.normal(0, 0.5)
            pitch[i] = 0.8 + rng.normal(0, 0.3)
            roll[i] = rng.normal(0, 0.4)
            yaw[i] = 270.0 + rng.normal(0, 0.4)
        elif cur_t < 810.0:
            desc_progress = (cur_t - 660.0) / 150.0
            alt[i] = 100.0 * (1.0 - desc_progress) + rng.normal(0, 0.2)
            groundspeed[i] = 14.0 - 4.0 * desc_progress + rng.normal(0, 0.2)
            throttle[i] = 26.0 + rng.normal(0, 0.4)
            pitch[i] = -3.5 + rng.normal(0, 0.3)
            roll[i] = rng.normal(0, 0.4)
            yaw[i] = 270.0 + rng.normal(0, 0.4)
        elif cur_t < 860.0:
            flare_progress = (cur_t - 810.0) / 50.0
            alt[i] = max(0.0, 5.0 * (1.0 - flare_progress) + rng.normal(0, 0.05))
            groundspeed[i] = max(0.0, 10.0 * (1.0 - flare_progress) + rng.normal(0, 0.1))
            throttle[i] = max(0.0, 15.0 * (1.0 - flare_progress))
            pitch[i] = 3.0 * (1.0 - flare_progress) + 1.5 * flare_progress + rng.normal(0, 0.2)
            roll[i] = rng.normal(0, 0.2)
            yaw[i] = 270.0
        else:
            alt[i] = 0.0 + rng.normal(0, 0.03)
            groundspeed[i] = 0.0
            throttle[i] = 0.0
            pitch[i] = 1.5 + rng.normal(0, 0.1)
            roll[i] = rng.normal(0, 0.1)
            yaw[i] = 270.0

    alt = np.maximum(0.0, alt)

    yaw_rad = np.radians(yaw)
    dt = 1.0 / freq_hz
    v_north = groundspeed * np.cos(yaw_rad)
    v_east = groundspeed * np.sin(yaw_rad)
    pos_north = np.cumsum(v_north * dt)
    pos_east = np.cumsum(v_east * dt)

    lat_deg = base_lat + (pos_north / 111139.0) + rng.normal(0, 3e-6, n)
    lon_deg = base_lon + (pos_east / (111139.0 * np.cos(np.radians(base_lat)))) + rng.normal(0, 3e-6, n)

    # 3. Electrical & Battery Simulation
    total_capacity_coulombs = 18000.0  # 5 Ah * 3600
    r_int = 0.032  # Internal resistance: 32 mOhm

    base_current = 1.2 + 0.35 * (throttle / 100.0) + 32.0 * ((throttle / 100.0) ** 2.2)
    current = base_current + rng.normal(0, 0.25, n)
    current = np.maximum(0.8, current)

    charge_consumed = np.cumsum(current * dt)
    soc = np.clip(1.0 - (charge_consumed / total_capacity_coulombs), 0.05, 1.0)

    v_oc = 13.2 + 3.4 * soc - 0.25 * ((1.0 - soc) ** 3)
    voltage = v_oc - (current * r_int) + rng.normal(0, 0.03, n)

    # 4. Ground Truth Anomaly Annotation Arrays
    is_anomaly = np.zeros(n, dtype=bool)
    anomaly_type = np.full(n, "nominal", dtype=object)
    anomaly_channel = np.full(n, "none", dtype=object)
    anomaly_severity = np.full(n, "nominal", dtype=object)

    def inject(
        t_start: float,
        t_end: float,
        a_type: str,
        channel: str,
        severity: str,
    ) -> np.ndarray:
        mask = (t >= t_start) & (t <= t_end)
        if np.any(mask):
            is_anomaly[mask] = True
            anomaly_type[mask] = a_type
            anomaly_channel[mask] = channel
            anomaly_severity[mask] = severity
        return mask

    # --- Anomaly 1: Voltage Cell Sag [180, 192]s ---
    m1 = inject(180.0, 192.0, "voltage_sag", "voltage", "critical")
    if np.any(m1):
        voltage[m1] -= 2.6

    # --- Anomaly 2: Barometric Altitude Sensor Glitch [300, 306]s ---
    m2 = inject(300.0, 306.0, "altitude_spike", "alt", "high")
    if np.any(m2):
        alt[m2] += 36.0 + 4.0 * np.sin(np.linspace(0, 4 * np.pi, np.sum(m2)))

    # --- Anomaly 3: Current Surge / Motor Friction [380, 388]s ---
    m3 = inject(380.0, 388.0, "current_spike", "current", "high")
    if np.any(m3):
        current[m3] += 26.0
        voltage[m3] -= 26.0 * r_int * 1.5

    # --- Anomaly 4: GPS Multipath Coordinate Jump [460, 468]s ---
    m4 = inject(460.0, 468.0, "gps_jump", "lat_lon", "high")
    if np.any(m4):
        lat_deg[m4] += 0.00065
        lon_deg[m4] += 0.00045

    # --- Anomaly 5: Microburst Downdraft [540, 552]s ---
    m5 = inject(540.0, 552.0, "excessive_sink_rate", "alt", "critical")
    if np.any(m5):
        indices_m5 = np.where(m5)[0]
        for idx_step, idx_val in enumerate(indices_m5):
            alt[idx_val] -= idx_step * (6.8 * dt)

    # --- Anomaly 6: Attitude PID Flutter Oscillation [620, 635]s ---
    m6 = inject(620.0, 635.0, "attitude_oscillation", "roll_pitch", "medium")
    if np.any(m6):
        t_m6 = t[m6] - 620.0
        roll[m6] += 18.0 * np.sin(2.0 * np.pi * 2.8 * t_m6)
        pitch[m6] += 9.0 * np.cos(2.0 * np.pi * 2.8 * t_m6)

    # --- Anomaly 7: Current Sensor ADC Flatline [705, 720]s ---
    m7 = inject(705.0, 720.0, "sensor_flatline", "current", "medium")
    if np.any(m7):
        flatline_val = float(current[np.where(m7)[0][0]])
        current[m7] = flatline_val

    # --- Anomaly 8: Pitot Tube Blockage [780, 792]s ---
    m8 = inject(780.0, 792.0, "airspeed_loss", "groundspeed", "high")
    if np.any(m8):
        groundspeed[m8] = 1.2 + rng.normal(0, 0.1, np.sum(m8))

    df = pd.DataFrame(
        {
            "timestamp": t,
            "lat": lat_deg,
            "lon": lon_deg,
            "alt": alt,
            "groundspeed": groundspeed,
            "roll": roll,
            "pitch": pitch,
            "yaw": yaw,
            "voltage": voltage,
            "current": current,
            "throttle": throttle,
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "anomaly_channel": anomaly_channel,
            "anomaly_severity": anomaly_severity,
        }
    )

    return df
