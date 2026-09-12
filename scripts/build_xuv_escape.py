"""Build Phase 8 stellar-environment and atmospheric-escape scenarios."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from earth2.constants import S_EARTH_W_M2  # noqa: E402
from earth2.environment.escape import (  # noqa: E402
    energy_limited_mass_loss_rate,
    integrated_energy_limited_loss,
    roche_tide_factor,
)
from earth2.environment.xuv import (  # noqa: E402
    XUV_SCENARIOS,
    integrate_sed_bands,
    xuv_history_summary,
)

TARGET_COUNT = 60
HEATING_EFFICIENCIES = (0.05, 0.15, 0.30)
XUV_RADIUS_FACTORS = (1.0, 1.1, 1.3)
INITIAL_ENVELOPE_FRACTIONS = (0.001, 0.01, 0.10)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def optional_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def load_muscles_products() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    manifest_path = ROOT / "data/manifests/muscles_xuv.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    products: dict[str, dict[str, Any]] = {}
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if (
            not path.exists()
            or path.stat().st_size != item["bytes"]
            or sha256(path) != item["sha256"]
        ):
            raise ValueError(
                f"MUSCLES source missing or changed for {item['host']}; "
                "run python.exe scripts/fetch_muscles_xuv.py"
            )
        with fits.open(path, memmap=True) as hdul:
            spectrum = hdul[1].data
            bolometric_flux = float(hdul[0].header["BOLOFLUX"])
            bands = integrate_sed_bands(
                spectrum["WAVELENGTH0"],
                spectrum["WAVELENGTH1"],
                spectrum["FLUX"],
                spectrum["ERROR"],
                bolometric_flux,
            )
            products[item["host"]] = {
                "label": "DERIVED",
                "evidence_basis": "MAST_MUSCLES_STITCHED_OBSERVED_RECONSTRUCTED_MODEL_SED",
                "target": item["target"],
                "release": item["release"],
                "source_path": item["path"],
                "source_sha256": item["sha256"],
                "source_url": item["url"],
                "sed_bolometric_flux_at_earth_erg_s_cm2": bolometric_flux,
                "sed_min_wavelength_angstrom": float(np.min(spectrum["WAVELENGTH0"])),
                "sed_max_wavelength_angstrom": float(np.max(spectrum["WAVELENGTH1"])),
                "bands": bands,
                "uncertainty_boundary": (
                    "Reported bin errors are propagated as independent. Correlated SED stitching, "
                    "EUV reconstruction and model-systematic uncertainties are not captured."
                ),
            }
    return products, manifest


def mass_evidence(row: pd.Series) -> tuple[float | None, str]:
    mass = optional_float(row.get("pl_bmasse"))
    mass_class = str(row.get("mass_class") or "unknown")
    if mass is None or mass <= 0:
        return None, "missing_planet_mass"
    if mass_class == "upper_limit":
        return None, "upper_limit_not_used"
    labels = {
        "measured": "measured_mass",
        "msini_lower_limit": "minimum_mass_scenario",
        "msini_deprojected": "deprojected_minimum_mass_scenario",
        "inferred_mass_radius": "mass_radius_prediction_scenario",
    }
    return mass, labels.get(mass_class, f"catalogue_{mass_class}_scenario")


def scenario_range(values: list[float]) -> dict[str, float] | None:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if not finite.size:
        return None
    return {
        "minimum": float(np.min(finite)),
        "median": float(np.median(finite)),
        "maximum": float(np.max(finite)),
    }


def build_record(row: pd.Series, muscles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    host = str(row["hostname"])
    age = optional_float(row.get("st_age"))
    stellar_mass = optional_float(row.get("st_mass"))
    insolation = optional_float(row.get("insol_used"))
    orbit = optional_float(row.get("pl_orbsmax"))
    radius = optional_float(row.get("pl_rade"))
    bolometric_flux = (
        insolation * S_EARTH_W_M2 if insolation is not None and insolation > 0 else None
    )

    xuv_scenarios: dict[str, dict[str, float]] = {}
    if (
        age is not None
        and age > 0.01
        and stellar_mass is not None
        and stellar_mass > 0
        and bolometric_flux is not None
    ):
        for name, scenario in XUV_SCENARIOS.items():
            xuv_scenarios[name] = xuv_history_summary(
                stellar_age_gyr=age,
                bolometric_flux_w_m2=bolometric_flux,
                stellar_mass_solar=stellar_mass,
                scenario=scenario,
            )
        xuv_status = "bounded_age_activity_scenarios"
    else:
        xuv_status = "undetermined_missing_age_mass_or_bolometric_flux"

    muscles_record = muscles.get(host)
    if muscles_record is not None and bolometric_flux is not None:
        bands = muscles_record["bands"]
        scaled_bands = {}
        for name, band in bands.items():
            ratio = float(band["fraction_bolometric"])
            statistical_fraction = (
                float(band["statistical_error_erg_s_cm2"])
                / muscles_record["sed_bolometric_flux_at_earth_erg_s_cm2"]
            )
            scaled_bands[name] = {
                **band,
                "flux_at_planet_w_m2": ratio * bolometric_flux,
                "statistical_error_at_planet_w_m2": statistical_fraction * bolometric_flux,
            }
        muscles_current = {**muscles_record, "bands": scaled_bands}
    else:
        muscles_current = None

    planet_mass, planet_mass_basis = mass_evidence(row)
    escape_scenarios: list[dict[str, Any]] = []
    if (
        xuv_scenarios
        and planet_mass is not None
        and radius is not None
        and radius > 0
        and stellar_mass is not None
        and orbit is not None
        and orbit > 0
    ):
        for history_name, history in xuv_scenarios.items():
            for efficiency in HEATING_EFFICIENCIES:
                for radius_factor in XUV_RADIUS_FACTORS:
                    tide = roche_tide_factor(
                        stellar_mass_solar=stellar_mass,
                        planet_mass_earth=planet_mass,
                        semimajor_axis_au=orbit,
                        xuv_radius_earth=radius * radius_factor,
                    )
                    if not np.isfinite(tide) or tide <= 0:
                        continue
                    current_rate = energy_limited_mass_loss_rate(
                        xuv_flux_w_m2=history["current_xuv_flux_w_m2"],
                        planet_mass_earth=planet_mass,
                        planet_radius_earth=radius,
                        xuv_radius_factor=radius_factor,
                        heating_efficiency=efficiency,
                        tide_factor=tide,
                    )
                    lost = integrated_energy_limited_loss(
                        xuv_dose_j_m2=history["integrated_xuv_dose_j_m2"],
                        planet_mass_earth=planet_mass,
                        planet_radius_earth=radius,
                        xuv_radius_factor=radius_factor,
                        heating_efficiency=efficiency,
                        tide_factor=tide,
                    )
                    escape_scenarios.append(
                        {
                            "label": "SCENARIO",
                            "xuv_history": history_name,
                            "heating_efficiency": efficiency,
                            "xuv_radius_factor": radius_factor,
                            "tide_factor": tide,
                            "current_mass_loss_kg_s": current_rate,
                            "integrated_lost_earth_masses": lost,
                            "initial_envelope_loss_ratios": {
                                f"fraction_{fraction:g}": lost / (fraction * planet_mass)
                                for fraction in INITIAL_ENVELOPE_FRACTIONS
                            },
                        }
                    )

    generic_current = [scenario["current_xuv_flux_w_m2"] for scenario in xuv_scenarios.values()]
    doses = [scenario["integrated_xuv_dose_j_m2"] for scenario in xuv_scenarios.values()]
    losses = [scenario["integrated_lost_earth_masses"] for scenario in escape_scenarios]
    rates = [scenario["current_mass_loss_kg_s"] for scenario in escape_scenarios]
    return {
        "label": "SCENARIO",
        "pl_name": str(row["pl_name"]),
        "hostname": host,
        "earth2_rank": int(row["earth2_rank"]),
        "planet_radius_earth": radius,
        "planet_mass_earth_used": planet_mass,
        "planet_mass_basis": planet_mass_basis,
        "stellar_mass_solar": stellar_mass,
        "stellar_age_gyr": age,
        "semimajor_axis_au": orbit,
        "bolometric_insolation_earth": insolation,
        "bolometric_flux_w_m2": bolometric_flux,
        "xuv_history_status": xuv_status,
        "xuv_scenarios": xuv_scenarios,
        "generic_current_xuv_flux_w_m2": scenario_range(generic_current),
        "generic_integrated_xuv_dose_j_m2": scenario_range(doses),
        "muscles_current_environment": muscles_current,
        "escape_status": (
            "energy_limited_scenario_ensemble"
            if escape_scenarios
            else "undetermined_missing_age_environment_or_usable_mass"
        ),
        "escape_scenarios": escape_scenarios,
        "current_mass_loss_kg_s": scenario_range(rates),
        "integrated_lost_earth_masses": scenario_range(losses),
        "claim_boundary": (
            "XUV histories and energy-limited losses are scenarios, not measurements of "
            "atmospheric mass or proof that an atmosphere exists or is absent."
        ),
    }


def flatten(record: dict[str, Any]) -> dict[str, Any]:
    muscles = record["muscles_current_environment"]
    muscles_xuv = None
    if muscles is not None:
        muscles_xuv = muscles["bands"]["xuv_5_912a"]["flux_at_planet_w_m2"]
    return {
        "label": record["label"],
        "pl_name": record["pl_name"],
        "hostname": record["hostname"],
        "earth2_rank": record["earth2_rank"],
        "planet_radius_earth": record["planet_radius_earth"],
        "planet_mass_earth_used": record["planet_mass_earth_used"],
        "planet_mass_basis": record["planet_mass_basis"],
        "stellar_mass_solar": record["stellar_mass_solar"],
        "stellar_age_gyr": record["stellar_age_gyr"],
        "semimajor_axis_au": record["semimajor_axis_au"],
        "bolometric_insolation_earth": record["bolometric_insolation_earth"],
        "bolometric_flux_w_m2": record["bolometric_flux_w_m2"],
        "xuv_history_status": record["xuv_history_status"],
        "muscles_current_xuv_flux_w_m2": muscles_xuv,
        "generic_current_xuv_flux_min_w_m2": (record["generic_current_xuv_flux_w_m2"] or {}).get(
            "minimum"
        ),
        "generic_current_xuv_flux_median_w_m2": (record["generic_current_xuv_flux_w_m2"] or {}).get(
            "median"
        ),
        "generic_current_xuv_flux_max_w_m2": (record["generic_current_xuv_flux_w_m2"] or {}).get(
            "maximum"
        ),
        "generic_xuv_dose_min_j_m2": (record["generic_integrated_xuv_dose_j_m2"] or {}).get(
            "minimum"
        ),
        "generic_xuv_dose_median_j_m2": (record["generic_integrated_xuv_dose_j_m2"] or {}).get(
            "median"
        ),
        "generic_xuv_dose_max_j_m2": (record["generic_integrated_xuv_dose_j_m2"] or {}).get(
            "maximum"
        ),
        "escape_status": record["escape_status"],
        "current_mass_loss_min_kg_s": (record["current_mass_loss_kg_s"] or {}).get("minimum"),
        "current_mass_loss_median_kg_s": (record["current_mass_loss_kg_s"] or {}).get("median"),
        "current_mass_loss_max_kg_s": (record["current_mass_loss_kg_s"] or {}).get("maximum"),
        "integrated_lost_min_earth_masses": (record["integrated_lost_earth_masses"] or {}).get(
            "minimum"
        ),
        "integrated_lost_median_earth_masses": (record["integrated_lost_earth_masses"] or {}).get(
            "median"
        ),
        "integrated_lost_max_earth_masses": (record["integrated_lost_earth_masses"] or {}).get(
            "maximum"
        ),
    }


def make_environment_figure(frame: pd.DataFrame, output: Path) -> None:
    usable = frame[frame["generic_current_xuv_flux_median_w_m2"].notna()].copy()
    y = usable["muscles_current_xuv_flux_w_m2"].fillna(
        usable["generic_current_xuv_flux_median_w_m2"]
    )
    measured = usable["muscles_current_xuv_flux_w_m2"].notna()
    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-xuv-environment-v1"
    figure, axis = plt.subplots(figsize=(10.5, 6.2), constrained_layout=True)
    figure.patch.set_facecolor("#080b14")
    axis.set_facecolor("#080b14")
    axis.scatter(
        usable.loc[~measured, "bolometric_insolation_earth"],
        y[~measured],
        c="#596377",
        alpha=0.72,
        label="age-activity scenario",
    )
    axis.scatter(
        usable.loc[measured, "bolometric_insolation_earth"],
        y[measured],
        c="#52d3e1",
        edgecolors="white",
        linewidths=0.6,
        s=75,
        label="MAST MUSCLES stitched SED",
    )
    for _, row in usable[measured].iterrows():
        axis.annotate(
            row["pl_name"],
            (row["bolometric_insolation_earth"], row["muscles_current_xuv_flux_w_m2"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("incident bolometric flux [Earth = 1]")
    axis.set_ylabel("current XUV flux at planet [W m$^{-2}$]")
    axis.set_title(
        "Bolometric HZ position does not specify the XUV environment | DERIVED / SCENARIO"
    )
    axis.grid(alpha=0.12, which="both")
    axis.legend()
    figure.savefig(output.with_suffix(".png"), dpi=220, facecolor="#080b14")
    figure.savefig(output.with_suffix(".svg"), facecolor="#080b14", metadata={"Date": None})
    plt.close(figure)
    svg = output.with_suffix(".svg")
    normalized = svg.read_text(encoding="utf-8").replace("\r\n", "\n")
    with svg.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(normalized)


def make_escape_figure(frame: pd.DataFrame, output: Path) -> None:
    usable = frame[frame["integrated_lost_median_earth_masses"].notna()].head(24).copy()
    usable = usable.sort_values("earth2_rank", ascending=False)
    y = np.arange(len(usable))
    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-escape-scenarios-v1"
    figure, axis = plt.subplots(figsize=(10.5, 7.2), constrained_layout=True)
    figure.patch.set_facecolor("#080b14")
    axis.set_facecolor("#080b14")
    axis.hlines(
        y,
        usable["integrated_lost_min_earth_masses"],
        usable["integrated_lost_max_earth_masses"],
        color="#596377",
        linewidth=4,
    )
    axis.scatter(
        usable["integrated_lost_median_earth_masses"],
        y,
        color="#ffd166",
        zorder=3,
    )
    axis.set_yticks(y, usable["pl_name"], fontsize=8)
    axis.set_xscale("log")
    axis.set_xlabel("integrated energy-limited loss [Earth masses]")
    axis.set_title("Atmospheric escape spans model assumptions | SCENARIO")
    axis.grid(alpha=0.12, axis="x", which="both")
    figure.savefig(output.with_suffix(".png"), dpi=220, facecolor="#080b14")
    figure.savefig(output.with_suffix(".svg"), facecolor="#080b14", metadata={"Date": None})
    plt.close(figure)
    svg = output.with_suffix(".svg")
    normalized = svg.read_text(encoding="utf-8").replace("\r\n", "\n")
    with svg.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(normalized)


def main() -> None:
    ranking_path = ROOT / "results/candidate_ranking.parquet"
    ranking = pd.read_parquet(ranking_path)
    selected = (
        ranking[(~ranking["is_control"]) & ranking["pl_rade"].le(2.5)]
        .sort_values("earth2_rank")
        .head(TARGET_COUNT)
    )
    muscles, muscles_manifest = load_muscles_products()
    records = [build_record(row, muscles) for _, row in selected.iterrows()]
    frame = pd.DataFrame([flatten(record) for record in records])
    output = ROOT / "results/environment"
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "xuv_escape_scenarios.csv"
    json_path = output / "xuv_escape_scenarios.json"
    environment_figure = output / "bolometric_vs_xuv"
    escape_figure = output / "escape_sensitivity"
    frame.to_csv(csv_path, index=False, lineterminator="\n", float_format="%.10g")
    make_environment_figure(frame, environment_figure)
    make_escape_figure(frame, escape_figure)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "labels": ["DERIVED", "SCENARIO"],
        "title": "High-value candidate XUV environments and atmospheric-escape scenarios",
        "selection": f"top {TARGET_COUNT} ranked non-control planets with radius <=2.5 Earth radii",
        "sources": {
            "candidate_ranking": {
                "path": ranking_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(ranking_path),
            },
            "muscles_manifest": {
                "path": "data/manifests/muscles_xuv.json",
                "sha256": sha256(ROOT / "data/manifests/muscles_xuv.json"),
            },
            "muscles_archive": muscles_manifest["archive"],
            "muscles_doi": muscles_manifest["doi"],
            "builder": {
                "path": Path(__file__).relative_to(ROOT).as_posix(),
                "sha256": sha256(Path(__file__)),
            },
            "xuv_model": {
                "path": "src/earth2/environment/xuv.py",
                "sha256": sha256(ROOT / "src/earth2/environment/xuv.py"),
            },
            "escape_model": {
                "path": "src/earth2/environment/escape.py",
                "sha256": sha256(ROOT / "src/earth2/environment/escape.py"),
            },
        },
        "xuv_scenario_contract": {
            "form": "saturated L_XUV/L_bol followed by a power-law age decline",
            "scenario_names": list(XUV_SCENARIOS),
            "integration_start_gyr": 0.01,
            "warning": "bounded hypotheses informed by population studies, not target-specific activity posteriors",
        },
        "escape_scenario_contract": {
            "equation": "epsilon*pi*R_p*R_XUV^2*F_XUV/(G*M_p*K_tide)",
            "heating_efficiencies": list(HEATING_EFFICIENCIES),
            "xuv_radius_factors": list(XUV_RADIUS_FACTORS),
            "initial_envelope_mass_fractions": list(INITIAL_ENVELOPE_FRACTIONS),
            "fixed_properties_warning": "planet mass and radius are held fixed through time",
        },
        "population": {
            "targets": len(records),
            "with_age_activity_histories": int(frame["generic_xuv_dose_median_j_m2"].notna().sum()),
            "with_muscles_current_sed": int(frame["muscles_current_xuv_flux_w_m2"].notna().sum()),
            "with_escape_ensemble": int(frame["integrated_lost_median_earth_masses"].notna().sum()),
        },
        "claim_boundary": (
            "MUSCLES current fluxes are derived from stitched observed, reconstructed and modeled SEDs. "
            "Generic XUV histories and energy-limited escape outputs are scenarios. No output determines "
            "whether a planet has, retained or lost an atmosphere, and none is a habitability penalty."
        ),
        "records": records,
    }
    write_json(json_path, payload)
    files = [
        csv_path,
        json_path,
        environment_figure.with_suffix(".png"),
        environment_figure.with_suffix(".svg"),
        escape_figure.with_suffix(".png"),
        escape_figure.with_suffix(".svg"),
    ]
    product_manifest = {
        "schema_version": "1.0",
        "product": "Phase 8 XUV environment and atmospheric-escape scenarios",
        "files": {
            path.relative_to(ROOT).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        },
    }
    write_json(output / "environment_products.json", product_manifest)
    print(
        f"Environment release built: {len(records)} targets; "
        f"{payload['population']['with_muscles_current_sed']} MUSCLES matches; "
        f"{payload['population']['with_escape_ensemble']} escape ensembles",
        flush=True,
    )


if __name__ == "__main__":
    main()
