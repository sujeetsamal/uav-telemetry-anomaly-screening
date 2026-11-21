"""Unit tests for uavtel.io module."""

import io
import pandas as pd
import pytest

from uavtel.io import auto_map_columns, load_csv, validate_schema, CANONICAL_COLUMNS


def test_auto_map_columns_px4_ardupilot():
    raw_df = pd.DataFrame(
        {
            "TimeUS": [100, 200],
            "GPS_Lat": [37.77, 37.78],
            "GPS_Lon": [-122.41, -122.40],
            "BaroAlt": [50.0, 52.0],
            "Spd": [15.0, 15.5],
            "ATT_Roll": [1.2, 1.4],
            "ATT_Pitch": [0.5, 0.6],
            "Heading": [90.0, 92.0],
            "BAT_Volt": [16.2, 16.1],
            "BAT_Curr": [12.0, 12.5],
            "ThrOut": [0.5, 0.52],
        }
    )

    mapped_df, mapping = auto_map_columns(raw_df)

    for col in CANONICAL_COLUMNS:
        assert col in mapped_df.columns
        assert col in mapping


def test_validate_schema_success():
    valid_df = pd.DataFrame(
        {
            "timestamp": [0.0, 0.1, 0.2],
            "alt": [10.0, 11.0, 12.0],
            "voltage": [16.8, 16.7, 16.6],
            "current": [12.0, 13.0, 14.0],
        }
    )
    is_valid, errors = validate_schema(valid_df)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_schema_failure():
    invalid_df = pd.DataFrame(
        {
            "timestamp": ["not_a_time", "bad"],
            "alt": [10.0, 11.0],
        }
    )
    is_valid, errors = validate_schema(invalid_df)
    assert is_valid is False
    assert any("voltage" in e for e in errors)


def test_load_csv_from_bytes(messy_px4_csv_bytes: bytes):
    df, meta = load_csv(messy_px4_csv_bytes)
    assert meta["is_valid"] is True
    assert "timestamp" in df.columns
    assert "alt" in df.columns
    assert "voltage" in df.columns
    assert "current" in df.columns
    assert len(df) == 5
