"""Build Phase 7 time-dependent HZ and climate-sensitivity products."""

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

from earth2.climate.evolution import (  # noqa: E402
    CLIMATE_PRESCRIPTIONS,
    EvolutionConfig,
    MISTMainSequenceGrid,
    infer_continuous_hz,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_seed(name: str, base_seed: int) -> int:
    digest = hashlib.sha256(f"{base_seed}:{name}".encode()).digest()
    return int.from_bytes(digest[:4], "big")


def optional_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def build_record(
    row: pd.Series,
    grid: MISTMainSequenceGrid,
    config: EvolutionConfig,
    base_seed: int,
) -> dict[str, Any]:
    kwargs = {
        "age_gyr": optional_float(row.get("st_age")),
        "age_error_minus": optional_float(row.get("st_ageerr2")),
        "age_error_plus": optional_float(row.get("st_ageerr1")),
        "mass_solar": optional_float(row.get("st_mass")),
        "mass_error_minus": optional_float(row.get("st_masserr2")),
        "mass_error_plus": optional_float(row.get("st_masserr1")),
        "feh": optional_float(row.get("st_met")),
        "feh_error_minus": optional_float(row.get("st_meterr2")),
        "feh_error_plus": optional_float(row.get("st_meterr1")),
        "log_luminosity_solar": optional_float(row.get("st_lum")),
        "log_luminosity_error_minus": optional_float(row.get("st_lumerr2")),
        "log_luminosity_error_plus": optional_float(row.get("st_lumerr1")),
        "semimajor_axis_au": optional_float(row.get("pl_orbsmax")),
        "semimajor_axis_error_minus": optional_float(row.get("pl_orbsmaxerr2")),
        "semimajor_axis_error_plus": optional_float(row.get("pl_orbsmaxerr1")),
    }
    if any(value is None for value in kwargs.values()):
        result = {
            "label": "MODEL-INFERRED",
            "status": "undetermined",
            "reason": "missing_required_measurement_or_uncertainty",
            "draws_requested": config.draws,
            "draws_supported": 0,
            "supported_fraction": 0.0,
            "age_precision_status": "missing",
            "climate_prescriptions": {},
            "model_agreement": None,
            "boundary_sensitivity": None,
            "classification_robustness": "undetermined",
        }
    else:
        numeric_kwargs: dict[str, float] = {
            key: value for key, value in kwargs.items() if value is not None
        }
        result = infer_continuous_hz(
            grid,
            **numeric_kwargs,
            seed=stable_seed(str(row["pl_name"]), base_seed),
            config=config,
        )
    return {
        "pl_name": str(row["pl_name"]),
        "hostname": str(row["hostname"]),
        "is_control": False,
        "st_age_gyr": optional_float(row.get("st_age")),
        "st_mass_solar": optional_float(row.get("st_mass")),
        "st_feh": optional_float(row.get("st_met")),
        "st_log_luminosity_solar": optional_float(row.get("st_lum")),
        "pl_orbsmax_au": optional_float(row.get("pl_orbsmax")),
        **result,
    }


def flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    flat = {key: value for key, value in record.items() if key != "climate_prescriptions"}
    for name in CLIMATE_PRESCRIPTIONS:
        model = record["climate_prescriptions"].get(name, {})
        flat[f"{name}__p_current_hz"] = model.get("p_current_hz")
        for metric in ("tau_hz_gyr", "f_chz"):
            values = model.get(metric, {})
            for quantile in ("p16", "p50", "p84"):
                flat[f"{name}__{metric}_{quantile}"] = values.get(quantile)
    return flat


def make_figure(records: pd.DataFrame, output_base: Path) -> None:
    inferred = records[records["status"].eq("inferred")].copy()
    model = "kopparapu_conservative"
    p_hz = f"{model}__p_current_hz"
    f_chz = f"{model}__f_chz_p50"
    inferred = inferred[inferred[p_hz].notna() & inferred[f_chz].notna()]

    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-continuous-hz-v1"
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.2), constrained_layout=True)
    figure.patch.set_facecolor("#080b14")
    for axis in axes:
        axis.set_facecolor("#080b14")
        axis.grid(alpha=0.1)
    scatter = axes[0].scatter(
        inferred[p_hz],
        inferred[f_chz],
        c=inferred["boundary_sensitivity"],
        cmap="magma",
        s=18,
        alpha=0.75,
    )
    axes[0].set_xlabel("P(currently in conservative HZ)")
    axes[0].set_ylabel("median lifetime fraction in conservative HZ")
    axes[0].set_title("01  Snapshot versus history", loc="left")
    figure.colorbar(scatter, ax=axes[0], label="climate-boundary sensitivity")

    reason_labels = {
        "missing_required_measurement_or_uncertainty": "missing required evidence",
        "stellar_age_effectively_unconstrained": "stellar age too broad",
        "insufficient_mist_main_sequence_support": "outside present MIST support",
        "insufficient_continuous_track_support": "incomplete MIST history",
        "nonpositive_or_premain_sequence_input": "invalid or younger than 0.1 Gyr",
        "inferred": "continuous history inferred",
    }
    counts = records["reason"].fillna("inferred").value_counts().sort_values()
    labels = [reason_labels.get(str(reason), str(reason)) for reason in counts.index]
    axes[1].barh(labels, counts.values, color="#52d3e1")
    axes[1].set_xlabel("confirmed planets")
    axes[1].set_title("02  Evidence support is part of the result", loc="left")
    axes[1].tick_params(axis="y", labelsize=8)
    figure.suptitle(
        "Time-dependent habitable-zone inference | MODEL-INFERRED",
        fontsize=15,
    )
    figure.savefig(output_base.with_suffix(".png"), dpi=220, facecolor="#080b14")
    figure.savefig(
        output_base.with_suffix(".svg"),
        facecolor="#080b14",
        metadata={"Date": None},
    )
    plt.close(figure)
    svg = output_base.with_suffix(".svg")
    normalized_svg = svg.read_text(encoding="utf-8").replace("\r\n", "\n")
    with svg.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(normalized_svg)


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main() -> None:
    source = ROOT / "data/processed/nasa_pscomppars.parquet"
    grid_path = ROOT / "results/climate/mist_v1p2_main_sequence_grid.csv"
    output = ROOT / "results/climate"
    config = EvolutionConfig()
    base_seed = 20260912
    catalogue = pd.read_parquet(source)
    grid = MISTMainSequenceGrid.from_csv(grid_path)
    records = [build_record(row, grid, config, base_seed) for _, row in catalogue.iterrows()]
    flat = pd.DataFrame([flatten_record(record) for record in records])
    csv_path = output / "continuous_hz.csv"
    json_path = output / "continuous_hz.json"
    figure_base = output / "continuous_hz_sensitivity"
    flat.to_csv(csv_path, index=False, lineterminator="\n", float_format="%.10g")
    make_figure(flat, figure_base)

    inferred = flat[flat["status"].eq("inferred")]
    reason_counts = flat["reason"].fillna("inferred").value_counts().to_dict()
    robustness_counts = flat["classification_robustness"].value_counts().to_dict()
    payload = {
        "schema_version": "1.0",
        "label": "MODEL-INFERRED",
        "title": "MIST-anchored time-dependent habitable-zone inference",
        "sources": {
            "catalogue": {"path": source.relative_to(ROOT).as_posix(), "sha256": sha256(source)},
            "mist_grid": {
                "path": grid_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(grid_path),
            },
            "builder": {
                "path": Path(__file__).relative_to(ROOT).as_posix(),
                "sha256": sha256(Path(__file__)),
            },
            "model": {
                "path": "src/earth2/climate/evolution.py",
                "sha256": sha256(ROOT / "src/earth2/climate/evolution.py"),
            },
        },
        "sampling": {
            "draws_per_planet": config.draws,
            "history_steps": config.history_steps,
            "base_seed": base_seed,
            "minimum_supported_fraction": config.minimum_supported_fraction,
        },
        "support_contract": {
            "required": "finite central values and asymmetric uncertainties for age, mass, metallicity, log luminosity and semimajor axis",
            "age_precision": f"max relative side <= {config.maximum_relative_age_error} and 68% interval <= {config.maximum_age_interval_gyr} Gyr",
            "stellar_model": "at least half of posterior draws must remain inside the MIST phase-0 interpolation grid",
            "history_start_gyr": config.minimum_age_gyr,
        },
        "climate_prescriptions": {
            "kopparapu_conservative": "runaway greenhouse to maximum greenhouse",
            "kopparapu_moist_greenhouse": "moist greenhouse to maximum greenhouse",
            "kopparapu_optimistic_empirical": "recent Venus to early Mars",
        },
        "population": {
            "confirmed_planets_evaluated": int(len(flat)),
            "inferred": int(len(inferred)),
            "outcomes": {str(key): int(value) for key, value in reason_counts.items()},
            "classification_robustness": {
                str(key): int(value) for key, value in robustness_counts.items()
            },
        },
        "claim_boundary": (
            "These are stellar-model and climate-boundary conditional incident-flux histories. "
            "They are not observations of past climate, probabilities of surface liquid water, "
            "habitability, atmospheres, biology or life. The three prescriptions share the "
            "Kopparapu 1D framework and do not substitute for an independent 3D GCM ensemble."
        ),
        "records": records,
    }
    write_json(json_path, payload)
    files = [csv_path, json_path, figure_base.with_suffix(".png"), figure_base.with_suffix(".svg")]
    manifest = {
        "schema_version": "1.0",
        "product": "Phase 7 continuous-HZ and climate-boundary sensitivity",
        "files": {
            path.relative_to(ROOT).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        },
    }
    write_json(output / "continuous_hz_products.json", manifest)
    print(
        f"Continuous HZ built: {len(inferred):,}/{len(flat):,} planets inferred; "
        f"{len(flat) - len(inferred):,} undetermined",
        flush=True,
    )


if __name__ == "__main__":
    main()
