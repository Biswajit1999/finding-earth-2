"""Scientific figures for the measured response to artificial injections."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm


def plot_injection_grid(grid: pd.DataFrame, output: Path) -> None:
    """Plot binomial means, trial counts and finite-trial interval widths."""
    radii = np.unique(np.r_[grid.radius_lower_earth, grid.radius_upper_earth])
    periods = np.unique(np.r_[grid.period_lower_days, grid.period_upper_days])
    shape = len(radii) - 1, len(periods) - 1
    ordered = grid.sort_values(["radius_lower_earth", "period_lower_days"])
    values = [
        ordered.pipeline_mean,
        ordered.pipeline_and_vetting_mean,
        ordered.n_injected,
        ordered.pipeline_and_vetting_upper - ordered.pipeline_and_vetting_lower,
    ]
    titles = [
        "Pipeline recovery",
        "Pipeline + Robovetter PC",
        "Number of injected signals",
        "95% interval width: pipeline + vetting",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    fig.suptitle(
        "DR25 artificial-signal recovery — SIMULATED\n4800–6300 K diagnostic stellar selection",
        fontsize=15,
    )
    for i, (ax, column, title) in enumerate(zip(axes.flat, values, titles)):
        data = np.asarray(column, float).reshape(shape)
        cmap = plt.get_cmap("viridis").copy()
        cmap.set_bad("#dddddd")
        if i == 2:
            data = np.ma.masked_where(data <= 0, data)
            mesh = ax.pcolormesh(
                periods,
                radii,
                data,
                cmap=cmap,
                norm=LogNorm(vmin=1, vmax=max(2, ordered.n_injected.max())),
            )
        else:
            mesh = ax.pcolormesh(
                periods, radii, np.ma.masked_invalid(data), cmap=cmap, vmin=0, vmax=1
            )
        fig.colorbar(mesh, ax=ax, shrink=0.85)
        ax.set(
            xscale="log",
            yscale="log",
            title=title,
            xlabel="Injected period [days]",
            ylabel="Injected radius [Earth radii]",
        )
        ax.set_xticks([1, 10, 100, 500], labels=["1", "10", "100", "500"])
        ax.set_yticks([0.5, 1, 2, 4, 10], labels=["0.5", "1", "2", "4", "10"])
    fig.supxlabel(
        "Conditional on injection design; not an intrinsic population estimate. Grey = no trials.\nJeffreys-prior intervals capture finite trial counts, not target heterogeneity.",
        fontsize=10,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix(".png"), dpi=170)
    with plt.rc_context({"svg.hashsalt": "earth2-dr25-injection-diagnostics-v1"}):
        fig.savefig(output.with_suffix(".svg"), metadata={"Date": None})
    plt.close(fig)


def plot_reliability_grid(grid: pd.DataFrame, output: Path) -> None:
    """Plot the three evidence layers and observed support of the cell diagnostic."""
    periods = np.unique(np.r_[grid.period_lower_days, grid.period_upper_days])
    mes = np.unique(np.r_[grid.mes_lower, grid.mes_upper])
    shape = len(periods) - 1, len(mes) - 1
    ordered = grid.sort_values(["period_lower_days", "mes_lower"])
    reliability = ordered.false_alarm_reliability_point.to_numpy(float).copy()
    reliability[(reliability < 0) | (reliability > 1)] = np.nan
    values = [
        ordered.false_alarm_effectiveness,
        ordered.observed_false_alarm_fraction,
        reliability,
        ordered.observed_tces,
    ]
    titles = [
        "False-alarm rejection effectiveness · SIMULATED",
        "Instrumental false-alarm fraction · OBSERVED",
        "Equation 8 cell diagnostic · MODEL-INFERRED",
        "Observed TCE support",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    fig.suptitle(
        "Kepler DR25 false-alarm reliability foundation\n"
        "4800–6300 K stellar selection; unique INV + SCR1–3 trials",
        fontsize=15,
    )
    for index, (ax, column, title) in enumerate(zip(axes.flat, values, titles)):
        data = np.asarray(column, float).reshape(shape).T
        cmap = plt.get_cmap("magma" if index == 3 else "viridis").copy()
        cmap.set_bad("#d9dde3")
        if index == 3:
            positive = data[data > 0]
            vmax = max(2, float(positive.max())) if positive.size else 2
            shown = np.ma.masked_where(data <= 0, data)
            mesh = ax.pcolormesh(periods, mes, shown, cmap=cmap, norm=LogNorm(vmin=1, vmax=vmax))
        else:
            mesh = ax.pcolormesh(
                periods, mes, np.ma.masked_invalid(data), cmap=cmap, vmin=0, vmax=1
            )
        fig.colorbar(mesh, ax=ax, shrink=0.85)
        ax.set(
            title=title,
            xlabel="Orbital period [days]",
            ylabel="Multiple Event Statistic (MES)",
        )
    fig.supxlabel(
        "Descriptive cells only. Grey reliability cells are empty or outside [0,1]; values are never clipped.\n"
        "Candidate-level reliability requires a separately validated smooth model.",
        fontsize=10,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix(".png"), dpi=170)
    with plt.rc_context({"svg.hashsalt": "earth2-dr25-reliability-foundation-v1"}):
        fig.savefig(output.with_suffix(".svg"), metadata={"Date": None})
    plt.close(fig)
