"""Build the compact, browser-ready v2 evidence observatory payload.

The scientific result files remain authoritative.  This exporter selects the
fields needed by the static Next.js interface, preserves evidence labels and
claim boundaries, and records a SHA-256 for every source it reads.  It does not
recalculate scientific results in the browser.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PUBLIC = ROOT / "web" / "public"
DATA = PUBLIC / "data"
FIGURES = PUBLIC / "figures" / "v2"


def read_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def read_csv(relative: str) -> list[dict[str, Any]]:
    with (ROOT / relative).open(encoding="utf-8", newline="") as handle:
        rows: list[dict[str, Any]] = []
        for row in csv.DictReader(handle):
            parsed: dict[str, Any] = {}
            for key, value in row.items():
                if value is None or value == "":
                    parsed[key] = None
                    continue
                try:
                    parsed[key] = float(value)
                except ValueError:
                    parsed[key] = value
            rows.append(parsed)
        return rows


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def take_fields(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: row.get(field) for field in fields}


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    source_files = [
        "results/analysis_summary.json",
        "results/population/dr25_observed_vs_intrinsic.json",
        "results/population/dr25_selection_model.json",
        "results/population/dr25_selection_surface.csv",
        "results/composition/bulk_composition_ensemble.json",
        "results/climate/continuous_hz.json",
        "results/environment/xuv_escape_scenarios.json",
        "results/atmosphere/atmosphere_evidence.json",
        "results/hwo/hwo_precursor_atlas.json",
        "results/hwo/known_planet_accessibility.csv",
        "results/missions/mission_observatory.json",
        "results/information_gain/information_gain.json",
        "results/information_gain/action_information_gain.csv",
        "results/falsification/falsification_summary.json",
        "results/falsification/solar_system_controls.csv",
        "results/falsification/candidate_model_sensitivity.csv",
        "results/evidence/summary.json",
        "results/evidence/mass_evidence_examples.json",
    ]

    summary = read_json(source_files[0])
    population = read_json(source_files[1])
    selection = read_json(source_files[2])
    selection_cells = read_csv(source_files[3])
    composition = read_json(source_files[4])
    climate = read_json(source_files[5])
    environment = read_json(source_files[6])
    atmosphere = read_json(source_files[7])
    hwo = read_json(source_files[8])
    hwo_rows = read_csv(source_files[9])
    missions = read_json(source_files[10])
    mission_details = {
        item["mission_id"]: read_json(f"results/missions/{item['mission_id']}.json")
        for item in missions["missions"]
    }
    information_gain = read_json(source_files[11])
    information_rows = read_csv(source_files[12])
    falsification = read_json(source_files[13])
    controls = read_csv(source_files[14])
    sensitivity = read_csv(source_files[15])
    evidence = read_json(source_files[16])
    evidence_examples = read_json(source_files[17])

    ranked_names = {
        item["pl_name"] for item in information_gain["best_supported_action_by_target"]
    }
    composition_records = [
        row for row in composition["records"] if row.get("pl_name") in ranked_names
    ]
    climate_records = [
        row
        for row in climate["records"]
        if row.get("pl_name") in ranked_names
        or row.get("classification_robustness") == "boundary_or_model_sensitive"
    ][:80]
    environment_records = [
        take_fields(
            row,
            (
                "pl_name",
                "hostname",
                "earth2_rank",
                "label",
                "bolometric_insolation_earth",
                "stellar_age_gyr",
                "xuv_history_status",
                "escape_status",
                "generic_current_xuv_flux_w_m2",
                "generic_integrated_xuv_dose_j_m2",
                "integrated_lost_earth_masses",
                "planet_mass_basis",
                "claim_boundary",
            ),
        )
        for row in environment["records"]
    ]
    atmosphere_records = [
        take_fields(
            row,
            (
                "pl_name",
                "hostname",
                "earth2_rank",
                "planet_mass_basis",
                "equilibrium_temperature_k",
                "stellar_radius_solar",
                "hydrogen_to_earth_air_signal_ratio",
                "scenarios",
                "status",
                "label",
                "claim_boundary",
            ),
        )
        for row in atmosphere["observability"]["records"]
    ]
    supported_hwo = [row for row in hwo_rows if row.get("p_observable") is not None]
    supported_hwo.sort(key=lambda row: float(row["p_observable"]), reverse=True)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "title": "Finding Earth 2.0 Exoearth Evidence Observatory",
        "generated_utc": summary["generated_utc"],
        "author": "Biswajit Jana",
        "source_hashes": {name: sha256(name) for name in source_files},
        "population": population,
        "selection": {
            "label": selection["label"],
            "scope": selection["scope"],
            "release_status": selection["release_status"],
            "stellar_selection": selection["stellar_selection"],
            "stellar_denominator": selection["stellar_denominator"],
            "calibration_sample": selection["calibration_sample"],
            "model": selection["model"],
            "surface_grid": selection["surface_grid"],
            "cells": selection_cells,
            "interpretation": selection["interpretation"],
        },
        "composition": {
            "label": composition["label"],
            "population": composition["population"],
            "models": composition["models"],
            "model_disagreement": composition["model_disagreement"],
            "claim_boundary": composition["claim_boundary"],
            "records": composition_records,
        },
        "climate": {
            "label": climate["label"],
            "population": climate["population"],
            "prescriptions": climate["climate_prescriptions"],
            "claim_boundary": climate["claim_boundary"],
            "records": climate_records,
        },
        "environment": {
            "labels": environment["labels"],
            "population": environment["population"],
            "xuv_contract": environment["xuv_scenario_contract"],
            "escape_contract": environment["escape_scenario_contract"],
            "claim_boundary": environment["claim_boundary"],
            "records": environment_records,
        },
        "atmosphere": {
            "labels": atmosphere["labels"],
            "spectrum_evidence": atmosphere["spectrum_evidence"],
            "observability": {
                key: value
                for key, value in atmosphere["observability"].items()
                if key != "records"
            },
            "records": atmosphere_records,
        },
        "hwo": {
            "labels": hwo["labels"],
            "catalogue": hwo["catalogue"],
            "instrument_scenarios": hwo["instrument_scenarios"],
            "exoearth_forecast": hwo["exoearth_forecast"],
            "known_planet_forecast": hwo["known_planet_forecast"],
            "claim_boundary": hwo["claim_boundary"],
            "top_accessible_known_planets": supported_hwo[:36],
        },
        "missions": {**missions, "details": mission_details},
        "information_gain": {**information_gain, "rows": information_rows},
        "falsification": {
            **falsification,
            "controls": controls,
            "candidate_sensitivity": sensitivity,
        },
        "evidence": {
            **evidence,
            "mass_examples": evidence_examples,
        },
    }

    output = DATA / "observatory.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    release = {
        "schema_version": "1.0",
        "title": payload["title"],
        "author": payload["author"],
        "generated_utc": payload["generated_utc"],
        "observatory_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "source_count": len(source_files),
        "update_policy": (
            "The browser checks GitHub main on open. New archive inputs are processed, "
            "validated and committed by the scheduled workflow before publication."
        ),
    }
    (DATA / "release.json").write_text(
        json.dumps(release, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    figure_sources = {
        "selection-surface.png": "results/population/dr25_selection_surface.png",
        "observed-intrinsic.png": "results/population/dr25_observed_vs_intrinsic.png",
        "composition-models.png": "results/composition/composition_model_disagreement.png",
        "climate-sensitivity.png": "results/climate/continuous_hz_sensitivity.png",
        "bolometric-xuv.png": "results/environment/bolometric_vs_xuv.png",
        "escape-sensitivity.png": "results/environment/escape_sensitivity.png",
        "atmosphere-observability.png": "results/atmosphere/transmission_observability.png",
        "hwo-atlas.png": "results/hwo/hwo_precursor_atlas.png",
        "information-gain.png": "results/information_gain/expected_information_gain.png",
        "falsification.png": "results/falsification/falsification_and_robustness.png",
    }
    for destination, source in figure_sources.items():
        shutil.copyfile(ROOT / source, FIGURES / destination)

    print(
        f"Web observatory built: {output.relative_to(ROOT)} "
        f"({len(selection_cells)} selection cells, {len(information_rows)} EIG actions)"
    )


if __name__ == "__main__":
    main()
