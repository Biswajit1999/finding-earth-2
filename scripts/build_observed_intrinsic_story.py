"""Build the observed-versus-intrinsic DR25 narrative and website payload."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")


def normalize_text_lf(path: Path) -> None:
    payload = path.read_bytes().replace(b"\r\n", b"\n")
    normalized = b"\n".join(line.rstrip() for line in payload.split(b"\n"))
    if normalized != payload:
        path.write_bytes(normalized)


def interpolate_surface(surface: pd.DataFrame, column: str, period: float, radius: float) -> float:
    periods = np.sort(surface["period_days"].unique())
    radii = np.sort(surface["planet_radius_earth"].unique())
    matrix = (
        surface.pivot(index="planet_radius_earth", columns="period_days", values=column)
        .loc[radii, periods]
        .to_numpy(float)
    )
    interpolator = RegularGridInterpolator(
        (np.log(radii), np.log(periods)), np.log(np.maximum(matrix, 1e-300))
    )
    return float(np.exp(interpolator([[np.log(radius), np.log(period)]])[0]))


def plot_story(
    candidates: pd.DataFrame,
    surface: pd.DataFrame,
    posterior: dict,
    path: Path,
) -> None:
    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-observed-intrinsic"
    figure, axes = plt.subplots(1, 3, figsize=(15.5, 5.2), constrained_layout=True)
    figure.patch.set_facecolor("#080b14")

    supported = candidates["total_candidate_reliability_p50"].notna()
    scatter = axes[0].scatter(
        candidates.loc[supported, "koi_period"],
        candidates.loc[supported, "koi_prad"],
        c=candidates.loc[supported, "total_candidate_reliability_p50"],
        cmap="viridis",
        vmin=0,
        vmax=1,
        s=26,
        alpha=0.85,
        linewidths=0,
    )
    axes[0].scatter(
        candidates.loc[~supported, "koi_period"],
        candidates.loc[~supported, "koi_prad"],
        marker="x",
        s=54,
        color="#ffd166",
        label="reliability withheld",
    )
    axes[0].legend(loc="lower left", fontsize=8, framealpha=0.75)
    figure.colorbar(scatter, ax=axes[0], label="candidate reliability", fraction=0.05)
    axes[0].set_title("01  What entered the catalogue", loc="left")

    periods = np.sort(surface["period_days"].unique())
    radii = np.sort(surface["planet_radius_earth"].unique())
    selection = (
        surface.pivot(
            index="planet_radius_earth", columns="period_days", values="mean_total_selection"
        )
        .loc[radii, periods]
        .to_numpy(float)
    )
    selection_mesh = axes[1].pcolormesh(
        periods,
        radii,
        np.log10(selection),
        shading="nearest",
        cmap="magma",
    )
    figure.colorbar(selection_mesh, ax=axes[1], label="log10 selection probability", fraction=0.05)
    axes[1].scatter([365.25], [1], marker="*", color="white", s=80, edgecolor="#080b14")
    axes[1].set_title("02  What Kepler could select", loc="left")

    baseline = posterior["baseline_posteriors"]["full_fixed_box__unsupported_lower"]
    alpha = baseline["period_slope_alpha"]["p50"]
    beta = baseline["radius_slope_beta"]["p50"]
    period_grid = np.geomspace(50, 500, 160)
    radius_grid = np.geomspace(0.5, 2, 140)
    pp, rr = np.meshgrid(period_grid, radius_grid)
    intrinsic = (pp / 365.25) ** alpha * rr**beta
    intrinsic /= intrinsic.max()
    intrinsic_mesh = axes[2].pcolormesh(
        period_grid,
        radius_grid,
        intrinsic,
        shading="auto",
        cmap="cividis",
    )
    figure.colorbar(intrinsic_mesh, ax=axes[2], label="relative intrinsic density", fraction=0.05)
    axes[2].scatter([365.25], [1], marker="*", color="white", s=80, edgecolor="#080b14")
    axes[2].set_title("03  What the model infers", loc="left")

    for axis in axes:
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_xlim(50, 500)
        axis.set_ylim(0.5, 2)
        axis.set_xlabel("orbital period [days]")
        axis.set_ylabel("planet radius [Earth radii]")
        axis.grid(alpha=0.08, which="both")
    figure.suptitle(
        "Observed is not intrinsic | Kepler DR25 | OBSERVED + MODEL-INFERRED",
        fontsize=15,
    )
    figure.savefig(path.with_suffix(".png"), dpi=220, facecolor="#080b14")
    figure.savefig(path.with_suffix(".svg"), facecolor="#080b14", metadata={"Date": None})
    plt.close(figure)
    normalize_text_lf(path.with_suffix(".svg"))


def main() -> None:
    root = Path.cwd().resolve()
    output = root / "results/population"
    web_data = root / "web/public/data"
    web_figures = root / "web/public/figures"
    web_data.mkdir(parents=True, exist_ok=True)
    web_figures.mkdir(parents=True, exist_ok=True)
    posterior_path = output / "dr25_occurrence_posterior.json"
    surface_path = output / "dr25_selection_surface.csv"
    candidate_path = output / "dr25_candidate_reliability.csv"
    posterior = json.loads(posterior_path.read_text(encoding="utf-8"))
    surface = pd.read_csv(surface_path)
    candidates = pd.read_csv(candidate_path)
    baseline = posterior["baseline_posteriors"]["full_fixed_box__unsupported_lower"]
    rate = baseline["integrated_planets_per_star"]
    valid = baseline["imputed_valid_candidate_count"]
    exposure = baseline["shape_weighted_effective_stars"]
    selected_stars = posterior["stellar_population"]["selected_stars"]
    raw_rate = len(candidates) / selected_stars
    reliability_adjusted_observed_rate = valid["mean"] / selected_stars
    derived = posterior["full_fit_derived_densities_and_projected_subdomains"]["unsupported_lower"]
    earth_visibility = {
        name: interpolate_surface(surface, column, 365.25, 1.0)
        for name, column in {
            "mean_transit_geometry": "mean_transit_geometry",
            "mean_phase_window": "mean_phase_window",
            "mean_pipeline_including_window": "mean_pipeline_including_window",
            "mean_vetting_given_recovered": "mean_vetting_given_recovered",
            "mean_pipeline_and_vetting": "mean_pipeline_and_vetting",
            "mean_total_selection": "mean_total_selection",
            "effective_stars": "effective_stars",
        }.items()
    }
    story = {
        "schema_version": "1.0",
        "label": "OBSERVED + MODEL-INFERRED",
        "title": "The catalogue is the visible tip of a selected population",
        "domain": posterior["estimands"]["full_fixed_box"]["domain"],
        "funnel": [
            {
                "stage": "searched stars",
                "value": selected_stars,
                "unit": "selected GK dwarfs",
                "label": "OBSERVED",
            },
            {
                "stage": "catalogue candidates",
                "value": len(candidates),
                "unit": "KOIs in the fixed box",
                "label": "OBSERVED",
            },
            {
                "stage": "latent valid candidates",
                "value": valid["mean"],
                "interval": [valid["p025"], valid["p975"]],
                "unit": "mean imputed candidates",
                "label": "MODEL-INFERRED",
            },
            {
                "stage": "shape-weighted exposure",
                "value": exposure["p50"],
                "interval": [exposure["p025"], exposure["p975"]],
                "unit": "effective stars",
                "label": "MODEL-INFERRED",
            },
            {
                "stage": "intrinsic occurrence",
                "value": rate["p50"],
                "interval": [rate["p025"], rate["p975"]],
                "unit": "planets per selected star",
                "label": "MODEL-INFERRED",
            },
        ],
        "observed_rates_for_explanation_only": {
            "raw_candidate_entries_per_selected_star": raw_rate,
            "mean_imputed_valid_candidates_per_selected_star": reliability_adjusted_observed_rate,
            "intrinsic_to_raw_catalogue_ratio": rate["p50"] / raw_rate,
            "intrinsic_to_reliability_adjusted_observed_ratio": rate["p50"]
            / reliability_adjusted_observed_rate,
            "warning": (
                "These ratios explain scale; neither is the estimator. The posterior "
                "integrates target-specific selection over period-radius shape."
            ),
        },
        "earth_pivot_visibility": {
            "period_days": 365.25,
            "radius_earth": 1.0,
            **earth_visibility,
            "one_selected_signal_per_stars": 1 / earth_visibility["mean_total_selection"],
            "warning": (
                "Pipeline already includes the observing window. Averaged factors are "
                "diagnostics and must not be multiplied as independent means."
            ),
        },
        "intrinsic_posterior": {
            "full_fixed_box": rate,
            "period_slope_alpha": baseline["period_slope_alpha"],
            "radius_slope_beta": baseline["radius_slope_beta"],
            "gamma_earth_per_dlnp_dlnr": derived["gamma_earth_per_dlnp_dlnr"],
            "hsu_box_projection": derived["full_model_projected_hsu_box_rate"],
            "earth_20_percent_box_projection": derived[
                "full_model_projected_bryson_earth_box_rate"
            ],
        },
        "story_steps": [
            {
                "number": "01",
                "title": "Count what the survey recorded",
                "body": (
                    "Eighty-nine KOIs pass the fixed stellar and planet-domain contract. "
                    "That count describes the selected catalogue, not the intrinsic population."
                ),
            },
            {
                "number": "02",
                "title": "Ask which candidates are likely real",
                "body": (
                    "Shared reliability draws and astrophysical FPP reduce the mean latent "
                    "valid count to about 54, while keeping every uncertainty correlated."
                ),
            },
            {
                "number": "03",
                "title": "Model what the telescope could have selected",
                "body": (
                    "Geometry, window, pipeline recovery and vetting turn 114,105 targets "
                    "into about 78 shape-weighted effective stars for the fitted population."
                ),
            },
            {
                "number": "04",
                "title": "Infer the population that could produce the visible sample",
                "body": (
                    "The Poisson posterior gives 0.692 planets per selected star over the "
                    "whole fixed box, with a broad 0.267-1.918 95% interval."
                ),
            },
        ],
        "claim_boundary": (
            "This is a fixed period-radius occurrence result. It is not a probability of "
            "habitability, biology or a star-dependent habitable-zone eta Earth."
        ),
        "source_hashes": {
            "occurrence_posterior": sha256(posterior_path),
            "selection_surface": sha256(surface_path),
            "candidate_reliability": sha256(candidate_path),
            "builder": sha256(Path(__file__)),
        },
    }
    story_path = output / "dr25_observed_vs_intrinsic.json"
    figure_base = output / "dr25_observed_vs_intrinsic"
    write_json(story_path, story)
    plot_story(candidates, surface, posterior, figure_base)
    web_story_path = web_data / "occurrence.json"
    web_figure_path = web_figures / "observed_vs_intrinsic.png"
    shutil.copyfile(story_path, web_story_path)
    shutil.copyfile(figure_base.with_suffix(".png"), web_figure_path)
    manifest = {
        "schema_version": "1.0",
        "product": "DR25 observed-versus-intrinsic narrative",
        "files": {
            path.relative_to(root).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in (
                story_path,
                figure_base.with_suffix(".png"),
                figure_base.with_suffix(".svg"),
                web_story_path,
                web_figure_path,
            )
        },
    }
    write_json(output / "dr25_observed_intrinsic_products.json", manifest)
    print("Observed-versus-intrinsic story built for research outputs and web", flush=True)


if __name__ == "__main__":
    main()
