"""Build the Phase 11 mission observatory without cross-mission aggregation."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from earth2.missions.observatory import MISSION_PROFILES, RELEASE_ADAPTERS  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def source_lookup(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["source_id"]): item for item in manifest["sources"]}


def evidence_records() -> dict[str, list[dict[str, Any]]]:
    reductions_path = ROOT / "results/atmosphere/spectrum_reductions.csv"
    reductions = pd.read_csv(reductions_path)
    jwst = reductions[
        reductions["facility"].astype("string").str.contains("Webb|JWST", case=False, na=False)
    ]
    hwo = read_json(ROOT / "results/hwo/hwo_precursor_atlas.json")
    gaia = read_json(ROOT / "data/manifests/gaia_dr3_crossmatch.json")
    microlensing = read_json(ROOT / "data/manifests/nasa_microlensing.json")

    adapters = {adapter.mission_id: adapter for adapter in RELEASE_ADAPTERS}
    jwst_label = adapters["jwst"].evidence_label("nea_atmosphere_2026-08-28")
    hwo_label = adapters["hwo"].evidence_label("hpic_v1.1")
    gaia_label = adapters["gaia"].evidence_label("dr3")

    return {
        "jwst": [
            {
                "evidence_id": "published_atmosphere_reductions",
                "label": jwst_label,
                "value": int(len(jwst)),
                "unit": "separate spectrum reductions",
                "secondary_value": int(jwst["planet"].nunique()),
                "secondary_unit": "unique planets",
                "source": "results/atmosphere/spectrum_reductions.csv",
                "interpretation": (
                    "Published reductions whose archive facility names JWST; reductions are not merged."
                ),
            },
            {
                "evidence_id": "programme_status_coverage",
                "label": "DERIVED",
                "value": 0,
                "unit": "reductions with programme status",
                "source": "results/atmosphere/spectrum_reductions.csv",
                "interpretation": (
                    "The pinned NASA Archive spectrum table does not provide complete programme IDs or "
                    "planned/approved/scheduled states."
                ),
            },
        ],
        "hwo": [
            {
                "evidence_id": "hpic_v1p1_stars",
                "label": hwo_label,
                "value": int(hwo["catalogue"]["hpic_rows"]),
                "unit": "precursor catalogue stars",
                "source": "results/hwo/hpic_v1p1_atlas.csv.gz",
                "interpretation": "Potential inputs, not observed HWO targets or detections.",
            },
            {
                "evidence_id": "generic_exoearth_accessibility",
                "label": "FORECAST",
                "value": int(hwo["exoearth_forecast"]["rows"]),
                "unit": "star-scenario rows",
                "secondary_value": int(hwo["exoearth_forecast"]["supported_stars"]),
                "secondary_unit": "stars with supported geometry",
                "source": "results/hwo/exoearth_accessibility.csv.gz",
                "interpretation": "Three generic analytic trade cases; not a mission yield.",
            },
            {
                "evidence_id": "known_planet_accessibility",
                "label": "FORECAST",
                "value": int(hwo["known_planet_forecast"]["matched_planets"]),
                "unit": "matched known planets",
                "secondary_value": int(hwo["known_planet_forecast"]["supported_planets"]),
                "secondary_unit": "planets with supported forecast",
                "source": "results/hwo/known_planet_accessibility.csv",
                "interpretation": "Catalogue-conditioned accessibility, not HWO observations.",
            },
        ],
        "andes": [
            {
                "evidence_id": "instrument_design",
                "label": "FORECAST",
                "value": 100000,
                "unit": "baseline resolving power",
                "source": "official:andes_design",
                "interpretation": "Design requirement, not on-sky achieved performance.",
            },
            {
                "evidence_id": "science_observations",
                "label": "DERIVED",
                "value": 0,
                "unit": "ANDES science rows in project",
                "source": "mission release adapter",
                "interpretation": "The instrument is not commissioned; future ingestion remains disabled.",
            },
        ],
        "plato": [
            {
                "evidence_id": "mission_camera_design",
                "label": "FORECAST",
                "value": 26,
                "unit": "cameras",
                "source": "official:plato_overview",
                "interpretation": "Mission configuration before launch, not observing output.",
            },
            {
                "evidence_id": "science_observations",
                "label": "DERIVED",
                "value": 0,
                "unit": "PLATO science rows in project",
                "source": "mission release adapter",
                "interpretation": "Launch is planned for March 2027; future ingestion remains disabled.",
            },
        ],
        "gaia": [
            {
                "evidence_id": "dr3_exact_host_crossmatch",
                "label": gaia_label,
                "value": int(gaia["n_rows"]),
                "unit": "Gaia DR3 source rows",
                "source": "data/manifests/gaia_dr3_crossmatch.json",
                "interpretation": "Exact source identifiers from confirmed-planet hosts.",
            },
            {
                "evidence_id": "dr4_science_rows",
                "label": "FORECAST",
                "value": 0,
                "unit": "Gaia DR4 rows in project",
                "source": "official:gaia_dr4",
                "interpretation": "DR4 is not public in this dated snapshot and is not fabricated.",
            },
        ],
        "roman": [
            {
                "evidence_id": "launch_status",
                "label": "OBSERVED",
                "value": 1,
                "unit": "verified launch event",
                "source": "official:roman_launch",
                "interpretation": "Launched 2026-08-30; travelling to L2 before science operations.",
            },
            {
                "evidence_id": "gbtds_high_cadence",
                "label": "FORECAST",
                "value": 12.1,
                "unit": "minutes per planned high-cadence visit",
                "secondary_value": 6,
                "secondary_unit": "planned seasons",
                "source": "official:roman_gbtds",
                "interpretation": "Current survey design, not executed observations or measured yield.",
            },
            {
                "evidence_id": "historical_microlensing_context",
                "label": "OBSERVED",
                "value": int(microlensing["n_rows"]),
                "unit": "NASA Archive comparison rows",
                "source": "data/manifests/nasa_microlensing.json",
                "interpretation": "Historical microlensing context; zero rows are Roman observations.",
            },
        ],
    }


def render_page(
    profile: dict[str, Any],
    records: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
) -> str:
    def bullets(values: list[str] | tuple[str, ...]) -> str:
        return "\n".join(f"- {value}" for value in values)

    evidence_lines = []
    for record in records:
        second = ""
        if "secondary_value" in record:
            second = f"; {record['secondary_value']:,} {record['secondary_unit']}"
        value = record["value"]
        rendered_value = f"{value:,}" if isinstance(value, int) else str(value)
        evidence_lines.append(
            f"- **{record['label']} — {record['evidence_id']}**: {rendered_value} "
            f"{record['unit']}{second}. {record['interpretation']}"
        )
    source_lines = []
    for source_id in profile["official_source_ids"]:
        source = sources[source_id]
        source_lines.append(f"- [{source['title']}]({source['url']}) — {source['supports']}")
    return f"""# {profile['name']} mission view

**Status as of {profile['status_as_of']}:** {profile['status']}.

**Scientific role:** {profile['scientific_role']}.

This page is one independent observatory view. Its rows are not converted into a shared mission ranking.

## What it measures

{bullets(profile['measures'])}

## What it cannot establish

{bullets(profile['cannot_measure'])}

## Wavelength domain

{bullets(profile['wavelength'])}

## Resolution concept

{bullets(profile['resolution'])}

## Data available to this project

{bullets(profile['data_available'])}

## Evidence snapshot

{chr(10).join(evidence_lines)}

## Observation / forecast boundary

{profile['forecast_boundary']}

## Official sources

{chr(10).join(source_lines)}
"""


def main() -> None:
    source_manifest_path = ROOT / "data/manifests/mission_observatory_sources.json"
    source_manifest = read_json(source_manifest_path)
    sources = source_lookup(source_manifest)
    records_by_mission = evidence_records()
    output = ROOT / "results/missions"
    docs = ROOT / "docs/missions"
    output.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)

    input_paths = [
        source_manifest_path,
        ROOT / "results/atmosphere/spectrum_reductions.csv",
        ROOT / "results/hwo/hwo_precursor_atlas.json",
        ROOT / "data/manifests/gaia_dr3_crossmatch.json",
        ROOT / "data/manifests/nasa_microlensing.json",
    ]
    index_entries: list[dict[str, Any]] = []
    product_paths: list[Path] = []
    for profile_model in MISSION_PROFILES:
        profile = profile_model.to_dict()
        mission_id = profile_model.mission_id
        missing_sources = set(profile_model.official_source_ids) - set(sources)
        if missing_sources:
            raise ValueError(f"{mission_id} has unknown official sources: {sorted(missing_sources)}")
        records = records_by_mission[mission_id]
        payload = {
            "schema_version": "1.0",
            "mission": profile,
            "evidence_records": records,
            "official_sources": [sources[item] for item in profile_model.official_source_ids],
            "source_snapshot": source_manifest["accessed_utc"],
            "source_manifest": source_manifest_path.relative_to(ROOT).as_posix(),
            "source_manifest_sha256": sha256(source_manifest_path),
            "input_hashes": {
                path.relative_to(ROOT).as_posix(): sha256(path) for path in input_paths[1:]
            },
        }
        json_path = output / f"{mission_id}.json"
        doc_path = docs / f"{mission_id.upper()}.md"
        write_json(json_path, payload)
        with doc_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(render_page(profile, records, sources))
        product_paths.extend([json_path, doc_path])
        index_entries.append(
            {
                "mission_id": mission_id,
                "name": profile["name"],
                "status_as_of": profile["status_as_of"],
                "status": profile["status"],
                "scientific_role": profile["scientific_role"],
                "evidence_file": json_path.relative_to(ROOT).as_posix(),
                "page": doc_path.relative_to(ROOT).as_posix(),
                "labels_present": sorted({record["label"] for record in records}),
            }
        )

    index_path = output / "mission_observatory.json"
    write_json(
        index_path,
        {
            "schema_version": "1.0",
            "title": "Finding Earth 2.0 mission observatory",
            "status_as_of": "2026-09-12",
            "separation_policy": (
                "Each mission answers a different measurement question. No cross-mission aggregate, "
                "ranking, or scientific merit number is defined."
            ),
            "missions": index_entries,
        },
    )
    product_paths.append(index_path)

    overview_path = ROOT / "docs/MISSION_OBSERVATORY.md"
    table_rows = "\n".join(
        f"| [{entry['name']}](missions/{entry['mission_id'].upper()}.md) | "
        f"{entry['status']} | {entry['scientific_role']} |"
        for entry in index_entries
    )
    with overview_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            f"""# Mission observatory

The observatory keeps six measurement programmes scientifically separate. A published JWST spectrum,
a Gaia astrometric source, an HWO accessibility scenario, an ANDES design capability, a future PLATO
light curve, and a Roman microlensing forecast are not interchangeable evidence.

| Mission | Status on 2026-09-12 | Question addressed |
|---|---|---|
{table_rows}

Every page states what the mission measures, what it cannot establish, its wavelength and resolution
concepts, the data currently available, and the boundary between observation and forecast. Future-release
adapters reject Gaia DR4, PLATO, ANDES, HWO, and Roman science rows as observations until a verified public
release exists.
"""
        )
    product_paths.append(overview_path)

    manifest_path = output / "mission_products.json"
    write_json(
        manifest_path,
        {
            "schema_version": "1.0",
            "product": "Phase 11 scientifically separate mission observatory",
            "files": {
                path.relative_to(ROOT).as_posix(): {
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
                for path in product_paths
            },
        },
    )
    print(
        "Mission observatory built: six separate views, "
        f"{sum(len(rows) for rows in records_by_mission.values())} evidence records",
        flush=True,
    )


if __name__ == "__main__":
    main()
