"""I/O module for loading and normalizing UAV flight logs (PX4, ArduPilot, CSV)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Canonical channels expected across the telemetry pipeline
CANONICAL_COLUMNS: List[str] = [
    "timestamp",
    "lat",
    "lon",
    "alt",
    "groundspeed",
    "roll",
    "pitch",
    "yaw",
    "voltage",
    "current",
    "throttle",
]

# Aliases mapped to canonical column names
COLUMN_ALIASES: Dict[str, List[str]] = {
    "timestamp": [
        "timestamp",
        "time_usec",
        "TimeUS",
        "time",
        "t",
        "Time",
        "GPS_Time",
        "DateTime",
        "timestamp_s",
        "Time_s",
        "time_s",
        "timestamp_ms",
    ],
    "lat": ["lat", "latitude", "Lat", "GPS_Lat", "PosLat", "latitude_deg", "GLOBAL_POSITION_INT.lat"],
    "lon": ["lon", "longitude", "Lng", "Lon", "GPS_Lon", "PosLon", "longitude_deg", "GLOBAL_POSITION_INT.lon"],
    "alt": ["alt", "altitude", "Alt", "GPS_Alt", "BaroAlt", "height", "z", "Alt_m", "altitude_m", "GLOBAL_POSITION_INT.alt"],
    "groundspeed": [
        "groundspeed",
        "speed",
        "vel_m_s",
        "Spd",
        "GPS_Spd",
        "v",
        "Speed_m_s",
        "groundspeed_m_s",
        "VGY",
        "vel",
        "V",
    ],
    "roll": ["roll", "Roll", "ATT_Roll", "AngRoll", "roll_deg", "ATTITUDE.roll"],
    "pitch": ["pitch", "Pitch", "ATT_Pitch", "AngPitch", "pitch_deg", "ATTITUDE.pitch"],
    "yaw": ["yaw", "Yaw", "ATT_Yaw", "AngYaw", "yaw_deg", "heading", "Heading", "ATTITUDE.yaw"],
    "voltage": [
        "voltage",
        "Volt",
        "battery_voltage",
        "V",
        "BAT_Volt",
        "bat_v",
        "voltage_v",
        "BATTERY_STATUS.voltages[0]",
        "Volt_V",
    ],
    "current": [
        "current",
        "Curr",
        "battery_current",
        "I",
        "BAT_Curr",
        "bat_a",
        "current_a",
        "BATTERY_STATUS.current_battery",
        "Curr_A",
    ],
    "throttle": [
        "throttle",
        "Throt",
        "RC_Throttle",
        "thr",
        "throttle_pct",
        "throttle_ratio",
        "VFR_HUD.throttle",
        "ThrOut",
    ],
}


def auto_map_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Automatically maps raw dataframe column names to canonical telemetry names.

    Parameters
    ----------
    df : pd.DataFrame
        Raw telemetry dataframe.

    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, str]]
        Dataframe with mapped columns and mapping dictionary {canonical: original}.
    """
    column_mapping: Dict[str, str] = {}
    lower_to_orig = {col.lower().strip(): col for col in df.columns}

    for canonical, aliases in COLUMN_ALIASES.items():
        matched_col: Optional[str] = None
        for alias in aliases:
            alias_lower = alias.lower().strip()
            if alias_lower in lower_to_orig:
                matched_col = lower_to_orig[alias_lower]
                break
        if matched_col is not None:
            column_mapping[canonical] = matched_col

    # Invert mapping for rename: {original: canonical}
    rename_dict = {orig: can for can, orig in column_mapping.items()}
    mapped_df = df.rename(columns=rename_dict).copy()

    # Retain non-canonical columns too, but prioritize canonical ones
    return mapped_df, column_mapping


def validate_schema(
    df: pd.DataFrame,
    required: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """Validates presence and numeric types of canonical columns.

    Parameters
    ----------
    df : pd.DataFrame
        Mapped telemetry dataframe.
    required : Optional[List[str]]
        List of required canonical channels. Defaults to CANONICAL_COLUMNS.

    Returns
    -------
    Tuple[bool, List[str]]
        True if all required columns are valid, and list of missing or invalid column messages.
    """
    if required is None:
        required = ["timestamp", "alt", "voltage", "current"]

    errors: List[str] = []
    for col in required:
        if col not in df.columns:
            errors.append(f"Missing required channel: '{col}'")
        else:
            # Check if column is numeric or can be coerced to numeric
            if not pd.api.types.is_numeric_dtype(df[col]):
                try:
                    pd.to_numeric(df[col], errors="raise")
                except Exception:
                    errors.append(f"Channel '{col}' contains non-numeric values that cannot be parsed.")

    is_valid = len(errors) == 0
    return is_valid, errors


def load_csv(
    filepath_or_buffer: Union[str, Path, io.StringIO, bytes],
    **kwargs: Any,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Loads a PX4 / ArduPilot / generic UAV CSV flight log.

    Parameters
    ----------
    filepath_or_buffer : Union[str, Path, io.StringIO, bytes]
        Path to file, StringIO or raw bytes.
    **kwargs : Any
        Additional arguments passed to pd.read_csv.

    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, Any]]
        Mapped telemetry dataframe and metadata dict with source info, detected columns, and schema validity.
    """
    if isinstance(filepath_or_buffer, bytes):
        buffer = io.BytesIO(filepath_or_buffer)
        raw_df = pd.read_csv(buffer, **kwargs)
    else:
        raw_df = pd.read_csv(filepath_or_buffer, **kwargs)

    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    mapped_df, mapping = auto_map_columns(raw_df)
    is_valid, validation_errors = validate_schema(mapped_df)

    # Ensure numeric conversion for mapped canonical columns
    for col in CANONICAL_COLUMNS:
        if col in mapped_df.columns:
            mapped_df[col] = pd.to_numeric(mapped_df[col], errors="coerce")

    metadata: Dict[str, Any] = {
        "raw_columns": list(raw_df.columns),
        "mapped_columns": mapping,
        "missing_canonical": [c for c in CANONICAL_COLUMNS if c not in mapped_df.columns],
        "is_valid": is_valid,
        "validation_errors": validation_errors,
        "raw_row_count": len(raw_df),
    }

    return mapped_df, metadata
