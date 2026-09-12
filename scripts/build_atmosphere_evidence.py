"""Build Phase 9 atmospheric observability and spectrum-evidence products."""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from earth2.spectroscopy.evidence import (  # noqa: E402
    reduction_disagreement_catalogue,
    spectrum_reduction_id,
)
from earth2.spectroscopy.spectra import (  # noqa: E402
    atmospheric_scale_height_km,
    harmonise_emission_depths,
    harmonise_transit_depths,
    transmission_signal_ppm,
)

MEAN_MOLECULAR_WEIGHTS = {
    "hydrogen_helium": 2.3,
    "water_vapour": 18.0,
    "earth_like_n2_o2": 28.97,
    "carbon_dioxide": 44.0,
}
REFERENCE_RE = re.compile(
    r"href=(?:\"(?P<quoted>[^\"]+)\"|(?P<plain>[^\s>]+))[^>]*>(?P<label>.*?)</a>",
    re.IGNORECASE,
)
BIBCODE_RE = re.compile(r"/abs/([^/]+)/abstract")


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


def reference_fields(raw: Any) -> tuple[str | None, str | None, str | None]:
    if raw is None or pd.isna(raw):
        return None, None, None
    value = str(raw)
    match = REFERENCE_RE.search(value)
    url = html.unescape(match.group("quoted") or match.group("plain") or "") if match else None
    label = html.unescape(re.sub(r"<[^>]+>", "", match.group("label"))).strip() if match else None
    bibcode_match = BIBCODE_RE.search(url or "")
    return label or None, bibcode_match.group(1) if bibcode_match else None, url or None


def mass_for_signal(row: pd.Series) -> tuple[float | None, str]:
    mass = optional_float(row.get("pl_bmasse"))
    mass_class = str(row.get("mass_class") or "unknown")
    if mass is None or mass <= 0:
        return None, "missing"
    if mass_class == "upper_limit":
        return None, "upper_limit_not_used"
    return mass, mass_class


def build_observability(ranking: pd.DataFrame) -> list[dict[str, Any]]:
    selected = (
        ranking[(~ranking["is_control"]) & ranking["pl_rade"].le(2.5)]
        .sort_values("earth2_rank")
        .head(60)
    )
    records: list[dict[str, Any]] = []
    for _, row in selected.iterrows():
        mass, mass_basis = mass_for_signal(row)
        radius = optional_float(row.get("pl_rade"))
        temperature = optional_float(row.get("teq_used"))
        stellar_radius = optional_float(row.get("st_rad"))
        scenarios: dict[str, dict[str, Any]] = {}
        if all(
            value is not None and value > 0 for value in [mass, radius, temperature, stellar_radius]
        ):
            assert mass is not None and radius is not None
            assert temperature is not None and stellar_radius is not None
            for name, molecular_weight in MEAN_MOLECULAR_WEIGHTS.items():
                height = atmospheric_scale_height_km(
                    temperature,
                    mass,
                    radius,
                    mean_molecular_weight_amu=molecular_weight,
                )
                signal = transmission_signal_ppm(radius, stellar_radius, height, 5.0)
                scenarios[name] = {
                    "label": "SCENARIO",
                    "mean_molecular_weight_amu": molecular_weight,
                    "temperature_k": temperature,
                    "n_scale_heights": 5.0,
                    "scale_height_km": height,
                    "transmission_signal_ppm": signal,
                }
            status = "scenario_ensemble"
        else:
            status = "undetermined_missing_usable_mass_radius_temperature_or_star_radius"
        ratio = None
        if scenarios:
            ratio = (
                scenarios["hydrogen_helium"]["transmission_signal_ppm"]
                / scenarios["earth_like_n2_o2"]["transmission_signal_ppm"]
            )
        records.append(
            {
                "label": "SCENARIO",
                "pl_name": str(row["pl_name"]),
                "hostname": str(row["hostname"]),
                "earth2_rank": int(row["earth2_rank"]),
                "planet_mass_earth_used": mass,
                "planet_mass_basis": mass_basis,
                "planet_radius_earth": radius,
                "equilibrium_temperature_k": temperature,
                "stellar_radius_solar": stellar_radius,
                "status": status,
                "scenarios": scenarios,
                "hydrogen_to_earth_air_signal_ratio": ratio,
                "claim_boundary": (
                    "Five-scale-height clear-atmosphere approximation; clouds, composition, "
                    "refraction and molecular opacity are not retrieved."
                ),
            }
        )
    return records


def best_index_match(
    index: pd.DataFrame,
    *,
    planet: str,
    spectrum_type: str,
    bibcode: str | None,
    facility: str | None,
    instrument: str | None,
    wavelength: float | None,
) -> pd.Series | None:
    if bibcode is None:
        return None
    candidates = index[
        index["pl_name"].eq(planet)
        & index["spec_type"].eq(spectrum_type)
        & index["bibcode"].eq(bibcode)
    ].copy()
    if candidates.empty:
        return None
    candidates["match_score"] = 0.0
    if facility is not None:
        candidates.loc[candidates["facility"].eq(facility), "match_score"] += 4
    if instrument is not None:
        candidates.loc[candidates["instrument"].eq(instrument), "match_score"] += 4
    if wavelength is not None:
        inside = candidates["minwavelng"].le(wavelength) & candidates["maxwavelng"].ge(wavelength)
        candidates.loc[inside, "match_score"] += 2
        centre = (candidates["minwavelng"] + candidates["maxwavelng"]) / 2
        candidates["distance"] = (centre - wavelength).abs().fillna(np.inf)
    else:
        candidates["distance"] = np.inf
    candidates = candidates.sort_values(
        ["match_score", "distance", "spec_path"], ascending=[False, True, True]
    )
    return candidates.iloc[0]


def reduction_inventory(index: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in index.sort_values(["pl_name", "spec_type", "bibcode", "spec_path"]).iterrows():
        reduction_id = spectrum_reduction_id(
            planet=str(row["pl_name"]),
            spectrum_type=str(row["spec_type"]).lower(),
            bibcode=None if pd.isna(row["bibcode"]) else str(row["bibcode"]),
            facility=None if pd.isna(row["facility"]) else str(row["facility"]),
            instrument=None if pd.isna(row["instrument"]) else str(row["instrument"]),
            archive_path=None if pd.isna(row["spec_path"]) else str(row["spec_path"]),
        )
        rows.append(
            {
                "label": "OBSERVED",
                "reduction_id": reduction_id,
                "planet": str(row["pl_name"]),
                "spectrum_type": str(row["spec_type"]).lower(),
                "authors": None if pd.isna(row["authors"]) else str(row["authors"]),
                "bibcode": None if pd.isna(row["bibcode"]) else str(row["bibcode"]),
                "doi": None,
                "facility": None if pd.isna(row["facility"]) else str(row["facility"]),
                "instrument": None if pd.isna(row["instrument"]) else str(row["instrument"]),
                "program": None,
                "program_status": "not_provided_by_archive_index",
                "reduction_note": None if pd.isna(row["note"]) else str(row["note"]),
                "archive_spec_path": None if pd.isna(row["spec_path"]) else str(row["spec_path"]),
                "declared_points": optional_float(row["num_datapoints"]),
                "wavelength_min_um": optional_float(row["minwavelng"]),
                "wavelength_max_um": optional_float(row["maxwavelng"]),
                "data_source": "NASA Exoplanet Archive spectra index",
            }
        )
    return pd.DataFrame(rows)


def build_points(
    raw: pd.DataFrame,
    index: pd.DataFrame,
    *,
    spectrum_type: str,
    source_dataset: str,
) -> pd.DataFrame:
    if spectrum_type == "transmission":
        harmonised = harmonise_transit_depths(raw)
        reference_column = "plntranreflink"
        index_type = "Transmission"
    else:
        harmonised = harmonise_emission_depths(raw)
        reference_column = "plntreflink"
        index_type = "Eclipse"
    records: list[dict[str, Any]] = []
    for source_row, row in harmonised.iterrows():
        planet = str(row["plntname"])
        paper_label, bibcode, paper_url = reference_fields(row.get(reference_column))
        wavelength = optional_float(row.get("wavelength_um"))
        facility = None if pd.isna(row.get("facility")) else str(row.get("facility"))
        instrument = None if pd.isna(row.get("instrument")) else str(row.get("instrument"))
        match = best_index_match(
            index,
            planet=planet,
            spectrum_type=index_type,
            bibcode=bibcode,
            facility=facility,
            instrument=instrument,
            wavelength=wavelength,
        )
        archive_path = (
            None if match is None or pd.isna(match.get("spec_path")) else str(match["spec_path"])
        )
        reduction_id = spectrum_reduction_id(
            planet=planet,
            spectrum_type=spectrum_type,
            bibcode=bibcode,
            facility=facility,
            instrument=instrument,
            archive_path=archive_path,
        )
        if spectrum_type == "transmission":
            source = str(row["depth_source"])
            limit_column = "plntransdeplim" if source == "plntransdep_percent" else "plnratrorlim"
        else:
            source = str(row["depth_source"])
            limit_column = "especlipdeplim"
        limit_flag = optional_float(row.get(limit_column))
        if limit_flag == 1:
            role = "upper_limit"
        elif limit_flag == -1:
            role = "lower_limit"
        else:
            role = "measurement"
        records.append(
            {
                "label": "DERIVED",
                "source_dataset": source_dataset,
                "source_row": int(source_row),
                "planet": planet,
                "spectrum_type": spectrum_type,
                "wavelength_um": wavelength,
                "bandwidth_um": optional_float(row.get("bandwidth_um")),
                "measurement_ppm": optional_float(row.get("depth_ppm")),
                "uncertainty_ppm": optional_float(row.get("depth_ppm_err")),
                "measurement_unit": "ppm",
                "measurement_source_column": source,
                "measurement_role": role,
                "limit_flag": limit_flag,
                "brightness_temperature_k": optional_float(row.get("brightness_temperature_k")),
                "facility": facility,
                "instrument": instrument,
                "program": None,
                "program_status": "not_provided_by_source_table",
                "paper_label": paper_label,
                "paper_bibcode": bibcode,
                "paper_doi": None,
                "paper_url": paper_url,
                "reduction_id": reduction_id,
                "reduction_note": (
                    None if match is None or pd.isna(match.get("note")) else str(match["note"])
                ),
                "archive_spec_path": archive_path,
                "data_source": "NASA Exoplanet Archive published atmosphere table",
            }
        )
    frame = pd.DataFrame(records)
    numeric_columns = (
        "wavelength_um",
        "bandwidth_um",
        "measurement_ppm",
        "uncertainty_ppm",
        "limit_flag",
        "brightness_temperature_k",
    )
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("float64")
    return frame


def flatten_observability(record: dict[str, Any]) -> dict[str, Any]:
    row = {key: value for key, value in record.items() if key != "scenarios"}
    for name in MEAN_MOLECULAR_WEIGHTS:
        scenario = record["scenarios"].get(name, {})
        row[f"{name}__scale_height_km"] = scenario.get("scale_height_km")
        row[f"{name}__transmission_signal_ppm"] = scenario.get("transmission_signal_ppm")
    return row


def make_observability_figure(frame: pd.DataFrame, output: Path) -> None:
    usable = frame[frame["status"].eq("scenario_ensemble")].head(30).copy()
    usable = usable.sort_values("earth2_rank", ascending=False)
    y = np.arange(len(usable))
    h2 = usable["hydrogen_helium__transmission_signal_ppm"]
    air = usable["earth_like_n2_o2__transmission_signal_ppm"]
    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-atmosphere-observability-v1"
    figure, axis = plt.subplots(figsize=(10.5, 8.0), constrained_layout=True)
    figure.patch.set_facecolor("#080b14")
    axis.set_facecolor("#080b14")
    axis.hlines(y, air, h2, color="#596377", linewidth=3)
    axis.scatter(h2, y, color="#52d3e1", label="H/He, μ=2.3")
    axis.scatter(air, y, color="#ffd166", label="Earth-like air, μ=28.97")
    axis.set_yticks(y, usable["pl_name"], fontsize=8)
    axis.set_xscale("log")
    axis.set_xlabel("five-scale-height transmission signal [ppm]")
    axis.set_title(
        "Atmospheric composition changes observability by an order of magnitude | SCENARIO"
    )
    axis.grid(alpha=0.12, axis="x", which="both")
    axis.legend()
    figure.savefig(output.with_suffix(".png"), dpi=220, facecolor="#080b14")
    figure.savefig(output.with_suffix(".svg"), facecolor="#080b14", metadata={"Date": None})
    plt.close(figure)
    svg = output.with_suffix(".svg")
    payload = svg.read_bytes().replace(b"\r\n", b"\n")
    normalized = b"\n".join(line.rstrip() for line in payload.split(b"\n"))
    svg.write_bytes(normalized)


def main() -> None:
    ranking_path = ROOT / "results/candidate_ranking.parquet"
    transit_path = ROOT / "data/processed/nasa_transitspec.parquet"
    emission_path = ROOT / "data/processed/nasa_emissionspec.parquet"
    index_path = ROOT / "data/processed/nasa_spectra_index.parquet"
    ranking = pd.read_parquet(ranking_path)
    transit = pd.read_parquet(transit_path)
    emission = pd.read_parquet(emission_path)
    index = pd.read_parquet(index_path)

    observability_records = build_observability(ranking)
    observability = pd.DataFrame([flatten_observability(row) for row in observability_records])
    reductions = reduction_inventory(index)
    transmission_points = build_points(
        transit, index, spectrum_type="transmission", source_dataset="nasa_transitspec"
    )
    emission_points = build_points(
        emission, index, spectrum_type="eclipse", source_dataset="nasa_emissionspec"
    )
    points = pd.concat([transmission_points, emission_points], ignore_index=True)
    comparisons = reduction_disagreement_catalogue(points)

    output = ROOT / "results/atmosphere"
    output.mkdir(parents=True, exist_ok=True)
    observability_csv = output / "observability_scenarios.csv"
    reductions_csv = output / "spectrum_reductions.csv"
    points_csv = output / "spectrum_measurements.csv.gz"
    evidence_json = output / "atmosphere_evidence.json"
    figure = output / "transmission_observability"
    observability.to_csv(observability_csv, index=False, lineterminator="\n", float_format="%.10g")
    reductions.to_csv(reductions_csv, index=False, lineterminator="\n", float_format="%.10g")
    points.to_csv(
        points_csv,
        index=False,
        lineterminator="\n",
        float_format="%.10g",
        compression={"method": "gzip", "compresslevel": 9, "mtime": 0},
    )
    make_observability_figure(observability, figure)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "labels": ["OBSERVED", "DERIVED", "SCENARIO"],
        "title": "Atmospheric observability scenarios and reduction-preserving evidence",
        "sources": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in [ranking_path, transit_path, emission_path, index_path]
        },
        "observability": {
            "targets": len(observability_records),
            "supported": int(observability["status"].eq("scenario_ensemble").sum()),
            "mean_molecular_weights_amu": MEAN_MOLECULAR_WEIGHTS,
            "n_scale_heights": 5,
            "records": observability_records,
            "claim_boundary": (
                "Clear isothermal scale-height scenarios only; no atmosphere or molecule is detected."
            ),
        },
        "spectrum_evidence": {
            "reduction_count": len(reductions),
            "measurement_count": len(points),
            "transmission_measurements": len(transmission_points),
            "eclipse_measurements": len(emission_points),
            "reductions_with_archive_path": int(reductions["archive_spec_path"].notna().sum()),
            "measurements_with_reduction_path_match": int(
                points["archive_spec_path"].notna().sum()
            ),
            "program_metadata_status": "not_provided_by_current_archive_tables",
            "doi_metadata_status": "not_provided_by_current_archive_tables; bibcodes retained",
            "reduction_comparisons": comparisons,
            "comparison_count": len(comparisons),
            "claim_boundary": (
                "Published reductions remain separate. Pairwise overlap diagnostics do not "
                "select, average or retrieve an atmospheric composition."
            ),
        },
        "files": {
            "observability": observability_csv.relative_to(ROOT).as_posix(),
            "reductions": reductions_csv.relative_to(ROOT).as_posix(),
            "measurements": points_csv.relative_to(ROOT).as_posix(),
        },
    }
    write_json(evidence_json, payload)
    files = [
        observability_csv,
        reductions_csv,
        points_csv,
        evidence_json,
        figure.with_suffix(".png"),
        figure.with_suffix(".svg"),
    ]
    manifest = {
        "schema_version": "1.0",
        "product": "Phase 9 atmospheric signal and spectrum evidence architecture",
        "files": {
            path.relative_to(ROOT).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        },
    }
    write_json(output / "atmosphere_products.json", manifest)
    print(
        f"Atmosphere evidence built: {len(observability_records)} candidates, "
        f"{len(reductions):,} reductions, {len(points):,} measurements, "
        f"{len(comparisons):,} overlap diagnostics",
        flush=True,
    )


if __name__ == "__main__":
    main()
