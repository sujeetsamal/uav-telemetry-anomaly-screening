"""UAV Flight Telemetry Analytics & Anomaly Screening Core Package."""

__version__ = "0.1.0"

from uavtel.io import load_csv, auto_map_columns, validate_schema, CANONICAL_COLUMNS
from uavtel.clean import (
    sort_by_time,
    drop_duplicates,
    convert_units,
    resample_to_timebase,
    fill_short_gaps,
    missing_report,
    clean_telemetry,
)
from uavtel.features import (
    compute_rolling_stats,
    compute_rates_of_change,
    compute_electrical_features,
    tag_flight_phases,
    extract_features,
)
from uavtel.sim import generate_synthetic_flight
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
from uavtel.evaluate import evaluate_method, evaluate_all_methods
from uavtel.viz import (
    plot_multichannel_timeseries,
    plot_battery_trend,
    plot_flight_phases,
    plot_gps_track,
    export_plot_to_base64,
)

__all__ = [
    "load_csv",
    "auto_map_columns",
    "validate_schema",
    "CANONICAL_COLUMNS",
    "sort_by_time",
    "drop_duplicates",
    "convert_units",
    "resample_to_timebase",
    "fill_short_gaps",
    "missing_report",
    "clean_telemetry",
    "compute_rolling_stats",
    "compute_rates_of_change",
    "compute_electrical_features",
    "tag_flight_phases",
    "extract_features",
    "generate_synthetic_flight",
    "detect_zscore",
    "detect_iqr",
    "detect_ewma",
    "detect_rules",
    "detect_isolation_forest",
    "detect_ensemble",
    "merge_flags_to_events",
    "run_all_detectors",
    "evaluate_method",
    "evaluate_all_methods",
    "plot_multichannel_timeseries",
    "plot_battery_trend",
    "plot_flight_phases",
    "plot_gps_track",
    "export_plot_to_base64",
]
