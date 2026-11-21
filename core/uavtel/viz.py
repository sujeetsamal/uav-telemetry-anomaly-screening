"""Visualization module for UAV flight telemetry: Multi-channel time-series, battery trends, flight phases, and GPS track."""

from __future__ import annotations

import base64
import io
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Headless backend safe for headless servers and APIs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_multichannel_timeseries(
    df: pd.DataFrame,
    events: Optional[List[Dict[str, Any]]] = None,
    figsize: Tuple[int, int] = (14, 10),
) -> plt.Figure:
    """Creates a 4-subplot synchronized flight telemetry overview with anomaly overlays.

    Subplots:
    1. Altitude & Vertical Speed
    2. Battery Voltage, Current & Power
    3. Attitude (Roll, Pitch, Yaw)
    4. Groundspeed & Throttle
    """
    t = df["timestamp"]
    fig, axes = plt.subplots(4, 1, figsize=figsize, sharex=True)
    plt.subplots_adjust(hspace=0.25)

    # Style
    bg_color = "#111827"
    panel_color = "#1f2937"
    text_color = "#f3f4f6"
    grid_color = "#374151"

    fig.patch.set_facecolor(bg_color)
    for ax in axes:
        ax.set_facecolor(panel_color)
        ax.grid(True, linestyle="--", alpha=0.5, color=grid_color)
        ax.tick_params(colors=text_color, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(grid_color)

    # Subplot 1: Altitude & Vertical Speed
    ax1 = axes[0]
    ax1.plot(t, df["alt"], color="#38bdf8", label="Altitude (m)", lw=1.5)
    ax1.set_ylabel("Altitude (m)", color="#38bdf8", fontsize=10)
    if "vertical_speed" in df.columns:
        ax1_twin = ax1.twinx()
        ax1_twin.plot(t, df["vertical_speed"], color="#fbbf24", label="V-Speed (m/s)", lw=1.0, alpha=0.7)
        ax1_twin.set_ylabel("V-Speed (m/s)", color="#fbbf24", fontsize=10)
        ax1_twin.tick_params(colors="#fbbf24", labelsize=9)
    ax1.set_title("Altitude & Vertical Dynamics", color=text_color, fontsize=11, fontweight="bold", loc="left")

    # Subplot 2: Battery Voltage & Current
    ax2 = axes[1]
    ax2.plot(t, df["voltage"], color="#4ade80", label="Voltage (V)", lw=1.5)
    ax2.set_ylabel("Voltage (V)", color="#4ade80", fontsize=10)
    if "current" in df.columns:
        ax2_twin = ax2.twinx()
        ax2_twin.plot(t, df["current"], color="#f87171", label="Current (A)", lw=1.0, alpha=0.7)
        ax2_twin.set_ylabel("Current (A)", color="#f87171", fontsize=10)
        ax2_twin.tick_params(colors="#f87171", labelsize=9)
    ax2.set_title("Battery & Electrical Load", color=text_color, fontsize=11, fontweight="bold", loc="left")

    # Subplot 3: Attitude
    ax3 = axes[2]
    if "roll" in df.columns:
        ax3.plot(t, df["roll"], color="#a78bfa", label="Roll (°)", lw=1.2)
    if "pitch" in df.columns:
        ax3.plot(t, df["pitch"], color="#f472b6", label="Pitch (°)", lw=1.2)
    ax3.set_ylabel("Angle (°)", color=text_color, fontsize=10)
    ax3.legend(loc="upper right", facecolor=panel_color, edgecolor=grid_color, labelcolor=text_color, fontsize=8)
    ax3.set_title("Attitude Dynamics (Roll & Pitch)", color=text_color, fontsize=11, fontweight="bold", loc="left")

    # Subplot 4: Groundspeed & Throttle
    ax4 = axes[3]
    if "groundspeed" in df.columns:
        ax4.plot(t, df["groundspeed"], color="#2dd4bf", label="Speed (m/s)", lw=1.5)
        ax4.set_ylabel("Speed (m/s)", color="#2dd4bf", fontsize=10)
    if "throttle" in df.columns:
        ax4_twin = ax4.twinx()
        ax4_twin.plot(t, df["throttle"], color="#e879f9", label="Throttle (%)", lw=1.0, alpha=0.6, linestyle=":")
        ax4_twin.set_ylabel("Throttle (%)", color="#e879f9", fontsize=10)
        ax4_twin.tick_params(colors="#e879f9", labelsize=9)
    ax4.set_xlabel("Time (s)", color=text_color, fontsize=10)
    ax4.set_title("Propulsion & Ground Velocity", color=text_color, fontsize=11, fontweight="bold", loc="left")

    # Overlay anomaly event intervals
    if events is not None:
        for evt in events:
            s_t = evt["start_time"]
            e_t = evt["end_time"]
            sev = evt.get("severity", "medium")
            color_map = {
                "critical": "#ef4444",
                "high": "#f97316",
                "medium": "#eab308",
                "low": "#3b82f6",
            }
            c = color_map.get(sev, "#ef4444")
            for ax in axes:
                ax.axvspan(s_t, e_t, color=c, alpha=0.22, lw=0)

    return fig


def plot_battery_trend(df: pd.DataFrame, figsize: Tuple[int, int] = (12, 5)) -> plt.Figure:
    """Visualizes battery discharge voltage vs current sag and cumulative energy consumption."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    bg_color = "#111827"
    panel_color = "#1f2937"
    text_color = "#f3f4f6"
    grid_color = "#374151"

    fig.patch.set_facecolor(bg_color)
    for ax in (ax1, ax2):
        ax.set_facecolor(panel_color)
        ax.grid(True, linestyle="--", alpha=0.4, color=grid_color)
        ax.tick_params(colors=text_color, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(grid_color)

    # Plot 1: V vs I sag scatter
    if "current" in df.columns and "voltage" in df.columns:
        sc = ax1.scatter(
            df["current"],
            df["voltage"],
            c=df["timestamp"],
            cmap="viridis",
            s=8,
            alpha=0.6,
        )
        cbar = fig.colorbar(sc, ax=ax1)
        cbar.set_label("Time (s)", color=text_color, fontsize=9)
        cbar.ax.tick_params(colors=text_color, labelsize=8)
        ax1.set_xlabel("Current (A)", color=text_color, fontsize=10)
        ax1.set_ylabel("Voltage (V)", color=text_color, fontsize=10)
        ax1.set_title("V vs I Battery Sag Curve", color=text_color, fontsize=11, fontweight="bold")

    # Plot 2: Cumulative Energy
    if "energy_wh" in df.columns:
        ax2.plot(df["timestamp"], df["energy_wh"], color="#fbbf24", lw=2.0)
        ax2.set_xlabel("Time (s)", color=text_color, fontsize=10)
        ax2.set_ylabel("Energy Consumed (Wh)", color=text_color, fontsize=10)
        ax2.set_title("Cumulative Energy Consumption", color=text_color, fontsize=11, fontweight="bold")

    return fig


def plot_flight_phases(df: pd.DataFrame, figsize: Tuple[int, int] = (12, 4)) -> plt.Figure:
    """Plots altitude profile color-coded by tagged flight phases."""
    fig, ax = plt.subplots(figsize=figsize)
    bg_color = "#111827"
    panel_color = "#1f2937"
    text_color = "#f3f4f6"
    grid_color = "#374151"

    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(panel_color)
    ax.grid(True, linestyle="--", alpha=0.4, color=grid_color)
    ax.tick_params(colors=text_color, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(grid_color)

    t = df["timestamp"]
    alt = df["alt"]
    phase_colors = {
        "ground": "#6b7280",
        "climb": "#10b981",
        "cruise": "#3b82f6",
        "loiter": "#8b5cf6",
        "descent": "#f59e0b",
    }

    if "flight_phase" in df.columns:
        for phase, color in phase_colors.items():
            mask = df["flight_phase"] == phase
            if mask.any():
                ax.scatter(t[mask], alt[mask], color=color, s=4, label=phase.capitalize(), alpha=0.8)
    else:
        ax.plot(t, alt, color="#38bdf8", lw=1.5)

    ax.set_xlabel("Time (s)", color=text_color, fontsize=10)
    ax.set_ylabel("Altitude (m)", color=text_color, fontsize=10)
    ax.set_title("Flight Phase Classification Profile", color=text_color, fontsize=11, fontweight="bold")
    ax.legend(loc="upper right", facecolor=panel_color, edgecolor=grid_color, labelcolor=text_color, fontsize=9)

    return fig


def plot_gps_track(
    df: pd.DataFrame,
    events: Optional[List[Dict[str, Any]]] = None,
    figsize: Tuple[int, int] = (8, 8),
) -> plt.Figure:
    """Plots the 2D GPS horizontal path colored by altitude with anomaly event markers."""
    fig, ax = plt.subplots(figsize=figsize)
    bg_color = "#111827"
    panel_color = "#1f2937"
    text_color = "#f3f4f6"
    grid_color = "#374151"

    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(panel_color)
    ax.grid(True, linestyle="--", alpha=0.4, color=grid_color)
    ax.tick_params(colors=text_color, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(grid_color)

    if "lon" in df.columns and "lat" in df.columns:
        sc = ax.scatter(
            df["lon"],
            df["lat"],
            c=df["alt"] if "alt" in df.columns else df["timestamp"],
            cmap="plasma",
            s=10,
            alpha=0.7,
        )
        cbar = fig.colorbar(sc, ax=ax)
        cbar.set_label("Altitude (m)", color=text_color, fontsize=9)
        cbar.ax.tick_params(colors=text_color, labelsize=8)

        # Mark Takeoff & Landing
        ax.plot(df["lon"].iloc[0], df["lat"].iloc[0], marker="o", color="#22c55e", markersize=9, label="Takeoff")
        ax.plot(df["lon"].iloc[-1], df["lat"].iloc[-1], marker="X", color="#ef4444", markersize=9, label="Landing")

        # Mark Anomaly locations
        if events is not None:
            for evt in events:
                s_t = evt["start_time"]
                e_t = evt["end_time"]
                mask = (df["timestamp"] >= s_t) & (df["timestamp"] <= e_t)
                if mask.any():
                    ax.scatter(
                        df.loc[mask, "lon"],
                        df.loc[mask, "lat"],
                        color="#ef4444",
                        s=35,
                        edgecolor="#ffffff",
                        lw=0.5,
                        zorder=5,
                    )

    ax.set_xlabel("Longitude (°)", color=text_color, fontsize=10)
    ax.set_ylabel("Latitude (°)", color=text_color, fontsize=10)
    ax.set_title("2D GPS Spatial Trajectory & Anomaly Footprint", color=text_color, fontsize=11, fontweight="bold")
    ax.legend(loc="best", facecolor=panel_color, edgecolor=grid_color, labelcolor=text_color, fontsize=9)

    return fig


def export_plot_to_base64(fig: plt.Figure) -> str:
    """Exports a Matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
