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


def plot_smooth_reliability(fit, candidates: pd.DataFrame, output: Path) -> None:
    """Plot the constrained smooth evidence surfaces and calibrated candidates."""
    from earth2.population.smooth_reliability import predict_components

    periods = np.geomspace(fit.domain.period_min_days, fit.domain.period_max_days, 140)
    mes = np.linspace(fit.domain.mes_min, fit.domain.mes_max, 120)
    period_grid, mes_grid = np.meshgrid(periods, mes)
    evaluation = pd.DataFrame(
        {
            "period": period_grid.ravel(),
            "MES": mes_grid.ravel(),
            "Rp": np.ones(period_grid.size),
        }
    )
    prediction = predict_components(fit, evaluation)
    panels = [
        prediction["observed_false_alarm_fraction"],
        prediction["false_alarm_effectiveness"],
        prediction["false_alarm_reliability"],
    ]
    titles = [
        "Observed false-alarm fraction · OBSERVED model",
        "False-alarm rejection effectiveness · SIMULATED model",
        "Constrained false-alarm reliability · MODEL-INFERRED",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    fig.suptitle(
        "Kepler DR25 constrained reliability surface\n"
        "Quadratic in log-period and MES; experiment-aware rejection model",
        fontsize=15,
    )
    for ax, values, title in zip(axes.flat[:3], panels, titles):
        data = values.reshape(period_grid.shape)
        mesh = ax.pcolormesh(periods, mes, data, cmap="viridis", vmin=0, vmax=1, rasterized=True)
        fig.colorbar(mesh, ax=ax, shrink=0.85)
        ax.set(xscale="log", title=title, xlabel="Orbital period [days]", ylabel="MES")
    ax = axes.flat[3]
    calibrated = candidates["false_alarm_reliability_p50"].notna()
    points = candidates.loc[calibrated]
    scatter = ax.scatter(
        points["koi_period"],
        points["observed_tce_mes"],
        c=points["total_candidate_reliability_p50"],
        cmap="viridis",
        vmin=0,
        vmax=1,
        s=np.where(points["published_comparison_box"], 54, 24),
        edgecolors=np.where(points["published_comparison_box"], "white", "none"),
        linewidths=0.8,
    )
    fig.colorbar(scatter, ax=ax, shrink=0.85, label="Total reliability (FPP fixed)")
    ax.set(
        xscale="log",
        xlim=(fit.domain.period_min_days, fit.domain.period_max_days),
        ylim=(fit.domain.mes_min, fit.domain.mes_max),
        title="Eligible candidates · white rim = published box",
        xlabel="KOI orbital period [days]",
        ylabel="Observed TCE MES",
    )
    fig.supxlabel(
        "Reliability is constrained algebraically, never clipped. Candidate intervals use a Laplace coefficient approximation.\n"
        "Two high-MES candidates outside the calibrated domain are withheld; no occurrence rate is shown.",
        fontsize=10,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix(".png"), dpi=170)
    with plt.rc_context({"svg.hashsalt": "earth2-dr25-smooth-reliability-v1"}):
        fig.savefig(output.with_suffix(".svg"), metadata={"Date": None})
    plt.close(fig)


def plot_selection_surface(surface: pd.DataFrame, output: Path) -> None:
    """Plot the separately identified factors in the survey-wide selection surface."""
    periods = np.sort(surface["period_days"].unique())
    radii = np.sort(surface["planet_radius_earth"].unique())
    expected_rows = len(periods) * len(radii)
    if (
        len(surface) != expected_rows
        or surface.duplicated(["planet_radius_earth", "period_days"]).any()
    ):
        raise ValueError("Selection surface must contain one complete rectangular grid")
    target_counts = surface["target_stars"].unique()
    if len(target_counts) != 1:
        raise ValueError("Selection surface has an inconsistent stellar denominator")

    panels = [
        ("mean_transit_geometry", "Centre-crossing transit geometry", "log"),
        ("mean_phase_window", "At least three observed transits", "probability"),
        ("mean_pipeline_including_window", "Pipeline recovery including window", "probability"),
        ("mean_vetting_given_recovered", "Robovetter PC given recovery", "probability"),
        ("mean_total_selection", "Total selection probability", "log"),
        ("effective_stars", "Effective searched stars", "log"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5), constrained_layout=True)
    fig.suptitle(
        "Kepler DR25 survey-wide selection surface\n"
        f"{int(target_counts[0]):,} selected stars; impact parameter marginalized",
        fontsize=15,
    )
    for ax, (column, title, scale) in zip(axes.flat, panels):
        grid = (
            surface.pivot(index="planet_radius_earth", columns="period_days", values=column)
            .loc[radii, periods]
            .to_numpy(float)
        )
        if scale == "log":
            positive = grid[grid > 0]
            if not positive.size:
                raise ValueError(f"Selection surface column {column} has no positive support")
            norm = LogNorm(vmin=float(positive.min()), vmax=float(positive.max()))
            mesh = ax.pcolormesh(
                periods,
                radii,
                grid,
                cmap="magma",
                norm=norm,
                shading="nearest",
                rasterized=True,
            )
        else:
            mesh = ax.pcolormesh(
                periods,
                radii,
                grid,
                cmap="viridis",
                vmin=0,
                vmax=1,
                shading="nearest",
                rasterized=True,
            )
        fig.colorbar(mesh, ax=ax, shrink=0.82)
        ax.set(
            xscale="log",
            yscale="log",
            title=title,
            xlabel="Orbital period [days]",
            ylabel="Planet radius [Earth radii]",
        )
        ax.set_xticks([50, 100, 200, 500], labels=["50", "100", "200", "500"])
        ax.set_yticks([0.5, 1, 1.5, 2], labels=["0.5", "1", "1.5", "2"])
    fig.supxlabel(
        "MODEL-INFERRED from DR25 INJ1 on-target injections. Pipeline already includes the "
        "observing window; candidate reliability is not multiplied into selection.",
        fontsize=10,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix(".png"), dpi=170)
    with plt.rc_context({"svg.hashsalt": "earth2-dr25-selection-surface-v1"}):
        fig.savefig(output.with_suffix(".svg"), metadata={"Date": None})
    plt.close(fig)
