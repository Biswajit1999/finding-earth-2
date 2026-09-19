"""Build conservative Phase 12 action-specific information-gain scenarios."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from earth2.decision.information_gain import (  # noqa: E402
    correlated_gaussian_target_information_gain,
    gaussian_expected_information_gain,
    gaussian_posterior_sigma,
    gaussian_transfer_break_even_correlation,
)

CORRELATION_GRID = (0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0)
CORRELATION_CEILING = 0.9

ACTION_MODELS: tuple[dict[str, Any], ...] = (
    {
        "action_id": "mass_precision_requirement",
        "parameter": "planet mass or minimum mass",
        "value": "pl_bmasse",
        "errors": ("pl_bmasseerr1", "pl_bmasseerr2"),
        "unit": "Earth masses",
        "noise_rule": "max(0.10 * measured value, 0.10 Earth masses)",
        "relative_noise": 0.10,
        "noise_floor": 0.10,
        "gate": "measured_or_msini",
        "observation_model": "A future independent Gaussian mass-like measurement.",
    },
    {
        "action_id": "radius_precision_requirement",
        "parameter": "planet radius",
        "value": "pl_rade",
        "errors": ("pl_radeerr1", "pl_radeerr2"),
        "unit": "Earth radii",
        "noise_rule": "max(0.02 * measured value, 0.01 Earth radii)",
        "relative_noise": 0.02,
        "noise_floor": 0.01,
        "gate": "finite_measurement",
        "observation_model": "A future independent Gaussian radius measurement.",
    },
    {
        "action_id": "stellar_radius_precision_requirement",
        "parameter": "stellar radius",
        "value": "st_rad",
        "errors": ("st_raderr1", "st_raderr2"),
        "unit": "Solar radii",
        "noise_rule": "max(0.01 * measured value, 0.005 Solar radii)",
        "relative_noise": 0.01,
        "noise_floor": 0.005,
        "gate": "finite_measurement",
        "observation_model": "A future independent Gaussian stellar-radius measurement.",
    },
    {
        "action_id": "stellar_age_precision_requirement",
        "parameter": "stellar age",
        "value": "st_age",
        "errors": ("st_ageerr1", "st_ageerr2"),
        "unit": "Gyr",
        "noise_rule": "max(0.20 * measured value, 0.20 Gyr)",
        "relative_noise": 0.20,
        "noise_floor": 0.20,
        "gate": "finite_measurement",
        "observation_model": "A future independent Gaussian stellar-age constraint.",
    },
    {
        "action_id": "eccentricity_precision_requirement",
        "parameter": "orbital eccentricity",
        "value": "pl_orbeccen",
        "errors": ("pl_orbeccenerr1", "pl_orbeccenerr2"),
        "unit": "dimensionless",
        "noise_rule": "Gaussian sigma 0.03",
        "absolute_noise": 0.03,
        "noise_floor": 0.03,
        "gate": "finite_measurement",
        "observation_model": "A local Gaussian approximation to a bounded eccentricity posterior.",
    },
    {
        "action_id": "inclination_precision_requirement",
        "parameter": "orbital inclination",
        "value": "pl_orbincl",
        "errors": ("pl_orbinclerr1", "pl_orbinclerr2"),
        "unit": "degrees",
        "noise_rule": "Gaussian sigma 0.5 degrees",
        "absolute_noise": 0.5,
        "noise_floor": 0.5,
        "gate": "finite_measurement",
        "observation_model": "A future independent astrometric or transit-geometry constraint.",
    },
)

WITHHELD_ACTIONS = (
    {
        "action_id": "ephemeris_refinement",
        "status": "withheld_no_joint_epoch_period_posterior",
        "reason": "A future transit window needs the epoch-period covariance, which the catalogue does not provide.",
    },
    {
        "action_id": "xuv_observation",
        "status": "withheld_no_statistical_likelihood",
        "reason": "The current XUV ranges are physical scenarios, not calibrated posterior samples.",
    },
    {
        "action_id": "transmission_spectrum",
        "status": "withheld_no_target_instrument_likelihood",
        "reason": "Scale-height amplitudes do not specify throughput, wavelength covariance, clouds, or systematics.",
    },
    {
        "action_id": "direct_imaging_detection",
        "status": "withheld_no_final_instrument_likelihood",
        "reason": "HWO trade cases are not a final observatory architecture or validated noise model.",
    },
    {
        "action_id": "albedo_measurement",
        "status": "withheld_no_observational_prior",
        "reason": "The existing albedo range is a scenario assumption rather than a posterior.",
    },
    {
        "action_id": "atmospheric_presence_test",
        "status": "withheld_no_calibrated_prevalence_or_test_model",
        "reason": "No target-specific atmosphere prior, sensitivity, or false-positive rate is defensible yet.",
    },
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def split_normal_sigma(row: pd.Series, columns: tuple[str, str]) -> float | None:
    values = [abs(value) for column in columns if (value := finite_float(row.get(column))) is not None]
    if not values or any(value <= 0 for value in values):
        return None
    return float(np.mean(values))


def action_noise(action: dict[str, Any], value: float) -> float:
    if "absolute_noise" in action:
        return float(action["absolute_noise"])
    return max(float(action["relative_noise"]) * abs(value), float(action["noise_floor"]))


def build_rows(catalogue: pd.DataFrame) -> pd.DataFrame:
    candidates = catalogue[catalogue["earth2_rank"].notna()].sort_values("earth2_rank").head(25)
    records: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        candidate_records: list[dict[str, Any]] = []
        for action in ACTION_MODELS:
            value = finite_float(candidate.get(action["value"]))
            prior_sigma = split_normal_sigma(candidate, action["errors"])
            supported = value is not None and prior_sigma is not None
            if action["gate"] == "measured_or_msini":
                supported &= str(candidate.get("mass_class")) in {
                    "measured",
                    "msini_lower_limit",
                }
            if supported:
                assert value is not None and prior_sigma is not None
                noise = action_noise(action, value)
                posterior_sigma = float(gaussian_posterior_sigma(prior_sigma, noise))
                eig_nats = float(gaussian_expected_information_gain(prior_sigma, noise))
                status = "synthetic_linear_gaussian"
            else:
                noise = None
                posterior_sigma = None
                eig_nats = None
                status = "undetermined_missing_measured_value_or_uncertainty"
            candidate_records.append(
                {
                    "label": "SIMULATED",
                    "pl_name": str(candidate["pl_name"]),
                    "earth2_rank": int(candidate["earth2_rank"]),
                    "action_id": action["action_id"],
                    "parameter": action["parameter"],
                    "parameter_value": value,
                    "unit": action["unit"],
                    "prior_sigma": prior_sigma,
                    "observation_sigma": noise,
                    "expected_posterior_sigma": posterior_sigma,
                    "expected_information_gain_nats": eig_nats,
                    "expected_information_gain_bits": (
                        None if eig_nats is None else eig_nats / np.log(2)
                    ),
                    "status": status,
                    "noise_rule": action["noise_rule"],
                    "observation_model": action["observation_model"],
                    "cost_or_time": "not_modelled",
                }
            )
        supported_records = [
            record for record in candidate_records if record["expected_information_gain_nats"] is not None
        ]
        supported_records.sort(
            key=lambda record: (-float(record["expected_information_gain_nats"]), record["action_id"])
        )
        for rank, record in enumerate(supported_records, start=1):
            record["within_target_information_rank"] = rank
        records.extend(candidate_records)
    return pd.DataFrame(records)


def make_figure(frame: pd.DataFrame, output: Path) -> None:
    action_ids = [str(action["action_id"]) for action in ACTION_MODELS]
    labels = [identifier.replace("_precision_requirement", "").replace("_", " ") for identifier in action_ids]
    candidates = frame["pl_name"].drop_duplicates().head(20).tolist()
    matrix = (
        frame.pivot(index="pl_name", columns="action_id", values="expected_information_gain_bits")
        .reindex(index=candidates, columns=action_ids)
        .to_numpy(dtype=float)
    )
    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-information-gain-v1"
    figure, axis = plt.subplots(figsize=(12, 8), constrained_layout=True)
    figure.patch.set_facecolor("#080b14")
    axis.set_facecolor("#080b14")
    colour_map = plt.colormaps["viridis"].copy()
    colour_map.set_bad("#242b3a")
    image = axis.imshow(np.ma.masked_invalid(matrix), aspect="auto", cmap=colour_map)
    axis.set_xticks(np.arange(len(labels)), labels, rotation=30, ha="right")
    axis.set_yticks(np.arange(len(candidates)), candidates)
    axis.set_title("Expected information from explicit precision requirements | SIMULATED")
    axis.set_xlabel("blank cells lack a measured catalogue uncertainty")
    colorbar = figure.colorbar(image, ax=axis, pad=0.02)
    colorbar.set_label("expected information gain [bits]")
    figure.savefig(output.with_suffix(".png"), dpi=220, facecolor="#080b14")
    figure.savefig(output.with_suffix(".svg"), facecolor="#080b14", metadata={"Date": None})
    plt.close(figure)
    svg = output.with_suffix(".svg")
    payload = svg.read_text(encoding="utf-8")
    with svg.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload.replace("\r\n", "\n"))


def build_objective_audit(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Compare direct and correlation-mediated information about planet radius."""

    records: list[dict[str, Any]] = []
    for planet, group in frame.groupby("pl_name", sort=False):
        actions = group.set_index("action_id")
        direct = actions.loc["radius_precision_requirement"]
        stellar = actions.loc["stellar_radius_precision_requirement"]
        required = [
            direct["prior_sigma"],
            direct["observation_sigma"],
            direct["expected_information_gain_nats"],
            stellar["prior_sigma"],
            stellar["observation_sigma"],
            stellar["expected_information_gain_nats"],
        ]
        if any(pd.isna(value) for value in required):
            continue

        direct_nats = float(direct["expected_information_gain_nats"])
        transferred = {
            f"{correlation:.2f}": float(
                correlated_gaussian_target_information_gain(
                    float(direct["prior_sigma"]),
                    float(stellar["prior_sigma"]),
                    correlation,
                    float(stellar["observation_sigma"]),
                )
                / np.log(2)
            )
            for correlation in CORRELATION_GRID
        }
        break_even = float(
            gaussian_transfer_break_even_correlation(
                direct_nats,
                float(stellar["prior_sigma"]),
                float(stellar["observation_sigma"]),
            )
        )
        direct_bits = direct_nats / np.log(2)
        stellar_own_bits = float(stellar["expected_information_gain_bits"])
        ceiling_bits = transferred[f"{CORRELATION_CEILING:.2f}"]
        records.append(
            {
                "label": "SENSITIVITY",
                "pl_name": str(planet),
                "earth2_rank": int(direct["earth2_rank"]),
                "objective": "planet radius uncertainty",
                "direct_planet_radius_information_bits": direct_bits,
                "stellar_radius_own_parameter_information_bits": stellar_own_bits,
                "stellar_to_planet_radius_information_bits_at_abs_correlation_0p90": ceiling_bits,
                "break_even_absolute_correlation": break_even if break_even <= 1 else None,
                "break_even_status": "reachable_only_above_ceiling"
                if break_even <= 1 and break_even > CORRELATION_CEILING
                else ("reachable_at_or_below_ceiling" if break_even <= 1 else "not_reachable"),
                "transfer_bits_by_absolute_correlation": transferred,
            }
        )
    return records


def make_objective_audit_figure(rows: list[dict[str, Any]], output: Path) -> None:
    ordered = sorted(rows, key=lambda row: int(row["earth2_rank"]), reverse=True)
    labels = [str(row["pl_name"]) for row in ordered]
    y = np.arange(len(ordered))
    direct = [float(row["direct_planet_radius_information_bits"]) for row in ordered]
    transfer = [
        float(row["stellar_to_planet_radius_information_bits_at_abs_correlation_0p90"])
        for row in ordered
    ]
    own = [float(row["stellar_radius_own_parameter_information_bits"]) for row in ordered]

    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-objective-audit-v1"
    figure, axis = plt.subplots(figsize=(12, max(7, len(ordered) * 0.48)), constrained_layout=True)
    figure.patch.set_facecolor("#080b14")
    axis.set_facecolor("#080b14")
    width = 0.24
    axis.barh(y - width, direct, height=width, color="#62d6d0", label="direct planet radius")
    axis.barh(
        y,
        transfer,
        height=width,
        color="#e9b44c",
        label="stellar → planet at |ρ| = 0.90",
    )
    axis.barh(
        y + width,
        own,
        height=width,
        color="#e97a8d",
        alpha=0.75,
        label="stellar own-parameter (different objective)",
    )
    axis.set_yticks(y, labels)
    axis.set_xlabel("expected information gain [bits]")
    axis.set_title("Objective-conditioned information audit | SENSITIVITY")
    axis.grid(axis="x", color="#ffffff", alpha=0.12, linewidth=0.8)
    axis.legend(loc="lower right", frameon=False, fontsize=9)
    figure.savefig(output.with_suffix(".png"), dpi=220, facecolor="#080b14")
    figure.savefig(output.with_suffix(".svg"), facecolor="#080b14", metadata={"Date": None})
    plt.close(figure)
    svg = output.with_suffix(".svg")
    payload = svg.read_text(encoding="utf-8")
    with svg.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload.replace("\r\n", "\n"))


def main() -> None:
    source = ROOT / "results/analysis_catalogue.parquet"
    output = ROOT / "results/information_gain"
    output.mkdir(parents=True, exist_ok=True)
    table_path = output / "action_information_gain.csv"
    summary_path = output / "information_gain.json"
    figure_path = output / "expected_information_gain"
    objective_figure_path = output / "objective_conditioned_information"
    if source.exists():
        catalogue = pd.read_parquet(source)
        frame = build_rows(catalogue)
        source_hash = sha256(source)
        rebuild_mode = "full_analysis_catalogue"
    else:
        try:
            prior_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            observatory = json.loads(
                (ROOT / "web/public/data/observatory.json").read_text(encoding="utf-8")
            )
            prior_summary = observatory["information_gain"]
        frame = pd.read_csv(table_path)
        source_hash = str(prior_summary["source_sha256"])
        rebuild_mode = "committed_target_action_grid"
    frame.to_csv(table_path, index=False, lineterminator="\n", float_format="%.10g")
    make_figure(frame, figure_path)
    objective_rows = build_objective_audit(frame)
    make_objective_audit_figure(objective_rows, objective_figure_path)

    supported = frame[frame["expected_information_gain_nats"].notna()]
    best = (
        supported.sort_values(
            ["pl_name", "within_target_information_rank", "action_id"]
        )
        .groupby("pl_name", sort=False)
        .first()
        .reset_index()
    )
    payload = {
        "schema_version": "1.0",
        "label": "SIMULATED",
        "title": "Action-specific expected information gain under declared synthetic likelihoods",
        "equation": "E_y[KL(p(theta|D,y,a) || p(theta|D))]",
        "linear_gaussian_solution_nats": "0.5 * ln(1 + prior_variance / observation_noise_variance)",
        "source": source.relative_to(ROOT).as_posix(),
        "source_sha256": source_hash,
        "rebuild_mode": rebuild_mode,
        "candidate_count": int(frame["pl_name"].nunique()),
        "action_count": len(ACTION_MODELS),
        "row_count": len(frame),
        "supported_rows": len(supported),
        "actions": list(ACTION_MODELS),
        "withheld_actions": list(WITHHELD_ACTIONS),
        "best_supported_action_by_target": [
            {
                "pl_name": str(row["pl_name"]),
                "action_id": str(row["action_id"]),
                "expected_information_gain_bits": float(row["expected_information_gain_bits"]),
            }
            for _, row in best.iterrows()
        ],
        "objective_conditioned_audit": {
            "label": "SENSITIVITY",
            "objective": "planet radius uncertainty",
            "method": (
                "Bivariate Gaussian transfer from a stellar-radius measurement to planet-radius "
                "uncertainty across an explicit absolute-correlation grid."
            ),
            "correlation_grid": list(CORRELATION_GRID),
            "assumed_absolute_correlation_ceiling": CORRELATION_CEILING,
            "eligible_target_count": len(objective_rows),
            "scalar_stellar_action_wins": int(
                sum(
                    row["stellar_radius_own_parameter_information_bits"]
                    > row["direct_planet_radius_information_bits"]
                    for row in objective_rows
                )
            ),
            "indirect_wins_at_or_below_ceiling": int(
                sum(
                    row["break_even_status"] == "reachable_at_or_below_ceiling"
                    for row in objective_rows
                )
            ),
            "claim_boundary": (
                "The archive publishes marginal uncertainties, not the joint radius posterior. "
                "Correlation values are sensitivity coordinates, not measured correlations. "
                "Own-parameter information and objective-conditioned information answer different questions."
            ),
            "rows": objective_rows,
        },
        "claim_boundary": (
            "These are synthetic precision-requirement experiments, not proposals, exposure-time "
            "estimates, instrument forecasts, or guarantees of achievable information. Comparisons are "
            "conditional on the listed Gaussian priors and likelihoods. Cost and time are not modelled."
        ),
        "references": [
            {
                "citation": "Lindley (1956), On a Measure of the Information Provided by an Experiment",
                "doi": "10.1214/aoms/1177728069",
            },
            {
                "citation": "Batalha & Line (2017), Information Content Analysis for Selection of Optimal JWST Observing Modes for Transiting Exoplanet Atmospheres",
                "arxiv": "1612.02085",
            },
        ],
    }
    write_json(summary_path, payload)
    files = [
        table_path,
        summary_path,
        figure_path.with_suffix(".png"),
        figure_path.with_suffix(".svg"),
        objective_figure_path.with_suffix(".png"),
        objective_figure_path.with_suffix(".svg"),
    ]
    write_json(
        output / "information_gain_products.json",
        {
            "schema_version": "1.0",
            "product": "Phase 12 action-specific expected information gain",
            "files": {
                path.relative_to(ROOT).as_posix(): {
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
                for path in files
            },
        },
    )
    print(
        f"Information-gain lab built: {len(frame)} target-action rows, "
        f"{len(supported)} supported synthetic likelihoods",
        flush=True,
    )


if __name__ == "__main__":
    main()
