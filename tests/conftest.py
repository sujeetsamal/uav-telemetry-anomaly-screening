"""Shared fixtures for pytest test suite."""

import sys
from pathlib import Path

# Ensure core package is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

import io
import pytest
import numpy as np
import pandas as pd

import uavtel


@pytest.fixture(scope="session")
def sim_flight_df() -> pd.DataFrame:
    """Fixture providing a 15-minute 10 Hz simulated UAV flight."""
    return uavtel.generate_synthetic_flight(duration_sec=900.0, freq_hz=10.0, seed=42)


@pytest.fixture(scope="session")
def short_sim_df() -> pd.DataFrame:
    """Fixture providing a short 2-minute 10 Hz simulated UAV flight for quick tests."""
    return uavtel.generate_synthetic_flight(duration_sec=120.0, freq_hz=10.0, seed=42)


@pytest.fixture(scope="session")
def cleaned_flight_df(sim_flight_df: pd.DataFrame) -> pd.DataFrame:
    """Fixture providing cleaned flight telemetry."""
    cleaned, _ = uavtel.clean_telemetry(sim_flight_df, freq_hz=10.0)
    return cleaned


@pytest.fixture(scope="session")
def featured_flight_df(cleaned_flight_df: pd.DataFrame) -> pd.DataFrame:
    """Fixture providing feature-engineered telemetry."""
    return uavtel.extract_features(cleaned_flight_df, freq_hz=10.0)


@pytest.fixture
def messy_px4_csv_bytes() -> bytes:
    """Creates a raw CSV string simulating PX4/ArduPilot logging format."""
    csv_text = """TimeUS,GLOBAL_POSITION_INT.lat,GLOBAL_POSITION_INT.lon,Alt_m,GPS_Spd,ATTITUDE.roll,ATTITUDE.pitch,ATTITUDE.yaw,BAT_Volt,BAT_Curr,ThrOut
1000000000000,377749000,-1224194000,10.5,12.4,0.05,0.02,1.57,16.2,14.5,0.55
1000000100000,377749100,-1224193900,11.2,12.6,0.04,0.03,1.57,16.1,14.8,0.56
1000000100000,377749100,-1224193900,11.2,12.6,0.04,0.03,1.57,16.1,14.8,0.56
1000000200000,377749200,-1224193800,12.0,12.8,0.03,0.02,1.58,16.0,15.0,0.57
1000000300000,377749300,-1224193700,12.7,13.0,0.02,0.01,1.58,15.9,15.2,0.58
"""
    return csv_text.encode("utf-8")
