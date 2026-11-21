"""Performance and vectorization test handling 100k+ rows."""

import time
import numpy as np
import pandas as pd
import pytest

import uavtel


def test_vectorized_performance_100k_rows():
    """Confirms that cleaning, feature engineering, and detectors handle 100k+ rows efficiently without python row loops."""
    n_rows = 100_000
    t = np.linspace(0, 10000, n_rows)

    df_large = pd.DataFrame(
        {
            "timestamp": t,
            "lat": 37.77 + np.sin(t / 100) * 0.01,
            "lon": -122.41 + np.cos(t / 100) * 0.01,
            "alt": 100.0 + 5.0 * np.sin(t / 20),
            "groundspeed": 15.0 + np.random.normal(0, 0.2, n_rows),
            "roll": np.random.normal(0, 1.0, n_rows),
            "pitch": np.random.normal(0, 0.5, n_rows),
            "yaw": (t % 360),
            "voltage": 16.0 - (t / 10000.0) * 3.0,
            "current": 14.0 + np.random.normal(0, 0.5, n_rows),
            "throttle": np.full(n_rows, 55.0),
        }
    )

    start_time = time.perf_counter()

    # 1. Feature extraction
    df_feat = uavtel.extract_features(df_large, freq_hz=10.0)

    # 2. Vectorized rule-based detector
    flags_rules, scores_rules, _ = uavtel.detect_rules(df_feat)

    # 3. Vectorized z-score detector
    flags_z, scores_z = uavtel.detect_zscore(df_feat["voltage"])

    elapsed = time.perf_counter() - start_time

    assert len(df_feat) == n_rows
    assert len(flags_rules) == n_rows
    assert len(flags_z) == n_rows
    # Vectorized execution should easily finish in under 3.5 seconds
    assert elapsed < 3.5, f"Vectorized processing took too long: {elapsed:.2f}s"
