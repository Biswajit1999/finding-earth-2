"""Build the deterministic Finding Earth 2.0 v2 publication bundle.

The bundle intentionally contains derived research products and retrieval
manifests, never the cached third-party source tables.  Its checksum manifest,
inventory, manuscript macros, and Zenodo-ready ZIP are reproducible from a
clean checkout at the recorded source commit.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "earth2-v2-data-release"
ZIP_PATH = ROOT / "earth2-v2-data-release.zip"
FIXED_ZIP_TIME = (2026, 9, 13, 0, 0, 0)

# Every entry is a derived product, compact metadata, configuration, or query
# manifest. Raw/cache/processed archive tables are deliberately absent.
RELEASE_FILES = (
    "results/analysis_summary.json",
    "results/provenance_manifest.json",
    "results/transformation_ledger.json",
    "results/data_coverage.csv",
    "results/candidate_identifiers.csv",
    "results/candidate_ranking.csv",
    "results/evidence/summary.json",
    "results/evidence/mass_evidence_examples.json",
    "results/population/dr25_summary.json",
    "results/population/dr25_selection_model.json",
    "results/population/dr25_selection_surface.csv",
    "results/population/dr25_selection_validation.json",
    "results/population/dr25_reliability_grid.csv",
    "results/population/dr25_smooth_reliability_model.json",
    "results/population/dr25_occurrence_posterior.json",
    "results/population/dr25_occurrence_posterior_samples.csv",
    "results/population/dr25_observed_vs_intrinsic.json",
    "results/composition/composition_products.json",
    "results/composition/bulk_composition_ensemble.csv",
    "results/climate/continuous_hz_products.json",
    "results/climate/continuous_hz.csv",
    "results/environment/environment_products.json",
    "results/environment/xuv_escape_scenarios.csv",
    "results/atmosphere/atmosphere_products.json",
    "results/atmosphere/atmosphere_evidence.json",
    "results/atmosphere/observability_scenarios.csv",
    "results/atmosphere/earth_analogue_spectrum_screen.json",
    "results/atmosphere/earth_analogue_spectrum_candidates.csv",
    "results/hwo/hwo_products.json",
    "results/hwo/hwo_precursor_atlas.json",
    "results/hwo/known_planet_accessibility.csv",
    "results/missions/mission_observatory.json",
    "results/missions/mission_products.json",
    "results/information_gain/information_gain_products.json",
    "results/information_gain/information_gain.json",
    "results/information_gain/action_information_gain.csv",
    "results/information_gain/objective_conditioned_information.svg",
    "results/falsification/falsification_products.json",
    "results/falsification/falsification_summary.json",
    "results/falsification/solar_system_controls.csv",
    "results/falsification/candidate_model_sensitivity.csv",
    "pyproject.toml",
    "requirements-lock.txt",
    "CITATION.cff",
    "DATA_LICENSES.md",
)

PAPER_FIGURES = (
    "results/population/dr25_observed_vs_intrinsic.png",
    "results/population/dr25_selection_surface.png",
    "results/population/dr25_occurrence_posterior.png",
    "results/composition/composition_model_disagreement.png",
    "results/climate/continuous_hz_sensitivity.png",
    "results/environment/escape_sensitivity.png",
    "results/atmosphere/transmission_observability.png",
    "results/atmosphere/earth_analogue_spectrum_screen.png",
    "results/hwo/hwo_precursor_atlas.png",
    "results/information_gain/expected_information_gain.png",
    "results/information_gain/objective_conditioned_information.png",
    "results/falsification/falsification_and_robustness.png",
)


def load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_lf_text(dst: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write repository text without platform-dependent newline translation."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    with dst.open("w", encoding=encoding, newline="\n") as handle:
        handle.write(normalized)


def copy_release_text(src: Path, dst: Path) -> None:
    """Copy UTF-8 release text with repository-canonical LF newlines."""
    text = src.read_text(encoding="utf-8")
    with dst.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.replace("\r\n", "\n").replace("\r", "\n"))


def source_commit() -> str:
    git = shutil.which("git")
    if git is None:
        windows_git = Path(r"C:\Program Files\Git\cmd\git.exe")
        git = str(windows_git) if windows_git.is_file() else "git"
    return subprocess.check_output(
        [git, "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def latex_macros() -> str:
    summary = load("results/analysis_summary.json")
    story = load("results/population/dr25_observed_vs_intrinsic.json")
    composition = load("results/composition/bulk_composition_ensemble.json")
    climate = load("results/climate/continuous_hz.json")
    environment = load("results/environment/xuv_escape_scenarios.json")
    atmosphere = load("results/atmosphere/atmosphere_evidence.json")
    hwo = load("results/hwo/hwo_precursor_atlas.json")
    info = load("results/information_gain/information_gain.json")
    falsification = load("results/falsification/falsification_summary.json")
    p = story["intrinsic_posterior"]["full_fixed_box"]
    values: dict[str, str] = {
        "AnalysisTimestamp": summary["generated_utc"],
        "TotalSourceRecords": f'{summary["scale"]["total_source_records"]:,}',
        "DatasetCount": str(summary["scale"]["n_datasets_retrieved"]),
        "ConfirmedPlanets": f'{summary["population"]["n_confirmed_planets"]:,}',
        "HostSystems": f'{summary["population"]["n_unique_host_systems"]:,}',
        "ConservativeHZ": str(summary["habitable_zone"]["n_in_conservative_hz_nominal"]),
        "SmallConservativeHZ": str(summary["habitable_zone"]["n_conservative_hz_and_below_1p6_re"]),
        "SmallHZMeasuredMass": str(summary["habitable_zone"]["n_conservative_hz_and_below_1p6_re_with_measured_mass"]),
        "MeasuredMasses": f'{summary["measurement_coverage"]["n_with_measured_mass"]:,}',
        "MeasurementLinks": f'{summary["measurement_provenance"]["n_links"]:,}',
        "SelectedStars": f'{story["funnel"][0]["value"]:,}',
        "ObservedCandidates": f'{story["funnel"][1]["value"]:,}',
        "LatentCandidates": f'{story["funnel"][2]["value"]:.0f}',
        "EffectiveStars": f'{story["funnel"][3]["value"]:.1f}',
        "OccurrenceMedian": f'{p["p50"]:.3f}',
        "OccurrenceLow": f'{p["p025"]:.3f}',
        "OccurrenceHigh": f'{p["p975"]:.3f}',
        "EarthPivotSelectionPercent": f'{story["earth_pivot_visibility"]["mean_total_selection"] * 100:.5f}',
        "EarthPivotOnePer": f'{story["earth_pivot_visibility"]["one_selected_signal_per_stars"]:,.0f}',
        "CompositionPlanets": f'{composition["population"]["planets_with_radius_in_domain"]:,}',
        "IndependentMasses": str(composition["population"]["independent_measured_masses"]),
        "CompositionMedianSpan": f'{composition["model_disagreement"]["median_probability_range_three_model_subset"]:.3f}',
        "ClimateInferred": str(climate["population"]["inferred"]),
        "ClimateRobustInside": str(climate["population"]["classification_robustness"]["robustly_inside_across_prescriptions"]),
        "ClimateSensitive": str(climate["population"]["classification_robustness"]["boundary_or_model_sensitive"]),
        "EnvironmentTargets": str(environment["population"]["targets"]),
        "EscapeSupported": str(environment["population"]["with_escape_ensemble"]),
        "AtmosphereMeasurements": f'{atmosphere["spectrum_evidence"]["measurement_count"]:,}',
        "AtmosphereScenarios": str(atmosphere["observability"]["supported"]),
        "HwoStars": f'{hwo["catalogue"]["hpic_rows"]:,}',
        "HwoSupportedPlanets": str(hwo["known_planet_forecast"]["supported_planets"]),
        "InformationActions": str(info["action_count"]),
        "InformationRows": str(info["supported_rows"]),
        "VenusESI": f'{falsification["venus_esi"]:.3f}',
    }
    lines = [
        "% Generated by scripts/build_publication_release.py; do not edit.",
        f"% Source commit: {source_commit()}",
    ]
    for name, value in values.items():
        escaped = str(value).replace("_", r"\_").replace("%", r"\%")
        lines.append(f"\\newcommand{{\\{name}}}{{{escaped}}}")
    return "\n".join(lines) + "\n"


def release_readme(commit: str) -> str:
    return f"""# Finding Earth 2.0 — v2 data release

This is the deterministic, machine-readable companion to the v2 manuscript.
It was built from source commit `{commit}`.

The release contains derived catalogues, posterior summaries and samples,
selection/reliability surfaces, model-sensitivity tables, mission scenarios,
source query manifests, environment metadata, and exact software requirements.
It does **not** contain raw or processed third-party archive tables.

Evidence labels retain their strict meanings: `OBSERVED`, `MODEL-INFERRED`,
`SIMULATED`, and `SCENARIO-ASSUMPTION`. No score is a probability of life.

Verify every byte with `sha256sum -c MANIFEST.sha256` or an equivalent SHA-256
tool. See `release_inventory.json` for file roles and `DATA_LICENSES.md` for
source attribution and reuse boundaries.

Suggested Zenodo upload: `earth2-v2-data-release.zip`. Reserve or mint a DOI in
Zenodo, then replace the `doi: pending` field in the inventory and citation files
in a DOI-only patch release.
"""


def build() -> dict[str, Any]:
    commit = source_commit()
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir()

    for rel in RELEASE_FILES:
        src = ROOT / rel
        if not src.is_file():
            raise FileNotFoundError(rel)
        dst = RELEASE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        copy_release_text(src, dst)

    manifest_dir = RELEASE / "data" / "manifests"
    manifest_dir.mkdir(parents=True)
    for src in sorted((ROOT / "data" / "manifests").glob("*.json")):
        copy_release_text(src, manifest_dir / src.name)

    write_lf_text(RELEASE / "README.md", release_readme(commit))
    write_lf_text(RELEASE / "VERSION", "2.1.0\n", encoding="ascii")
    write_lf_text(RELEASE / "SOURCE_COMMIT", commit + "\n", encoding="ascii")

    paper_figures = ROOT / "paper" / "figures" / "v2"
    paper_figures.mkdir(parents=True, exist_ok=True)
    for rel in PAPER_FIGURES:
        shutil.copy2(ROOT / rel, paper_figures / Path(rel).name)
    shutil.copy2(ROOT / "references" / "references.bib", ROOT / "paper" / "references.bib")
    write_lf_text(ROOT / "paper" / "generated_results.tex", latex_macros())

    inventory_files = []
    for path in sorted(p for p in RELEASE.rglob("*") if p.is_file()):
        rel = path.relative_to(RELEASE).as_posix()
        inventory_files.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})
    inventory: dict[str, Any] = {
        "schema_version": "1.0",
        "release": "2.1.0",
        "title": "Finding Earth 2.0 v2 data release",
        "doi": "pending",
        "source_commit": commit,
        "analysis_timestamp": load("results/analysis_summary.json")["generated_utc"],
        "licensing_boundary": "Derived products only; no cached third-party source tables.",
        "file_count_before_inventory": len(inventory_files),
        "files": inventory_files,
    }
    inv_path = RELEASE / "release_inventory.json"
    write_lf_text(inv_path, json.dumps(inventory, indent=2, sort_keys=True) + "\n")

    manifest_paths = sorted(
        p for p in RELEASE.rglob("*") if p.is_file() and p.name != "MANIFEST.sha256"
    )
    manifest = "".join(
        f"{sha256(path)}  {path.relative_to(RELEASE).as_posix()}\n" for path in manifest_paths
    )
    write_lf_text(RELEASE / "MANIFEST.sha256", manifest, encoding="ascii")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in RELEASE.rglob("*") if p.is_file()):
            rel = Path(RELEASE.name) / path.relative_to(RELEASE)
            info = zipfile.ZipInfo(rel.as_posix(), FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    return {
        "release_files": len([p for p in RELEASE.rglob("*") if p.is_file()]),
        "zip_bytes": ZIP_PATH.stat().st_size,
        "zip_sha256": sha256(ZIP_PATH),
        "source_commit": commit,
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
