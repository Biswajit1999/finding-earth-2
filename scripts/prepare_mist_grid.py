"""Prepare a compact main-sequence luminosity/temperature grid from MIST v1.2."""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import requests

SOURCE_URL = (
    "https://mist.science/data/tarballs_v1.2/"
    "MIST_v1.2_vvcrit0.4_basic_isos.txz"
)
SOURCE_SHA256 = "bb3f42743f75676fa8bf6ca63c4cb2723a0839b77204efebcae39fa4610a92c8"
SOURCE_BYTES = 221_507_784
RETRIEVED_UTC = "2026-09-11T23:44:05Z"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(SOURCE_URL, stream=True, timeout=120) as response:
        response.raise_for_status()
        with path.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                handle.write(chunk)


def metallicity_from_name(name: str) -> float:
    match = re.search(r"feh_([mp])(\d+\.\d+)", name)
    if not match:
        raise ValueError(f"Cannot parse metallicity from {name}")
    sign = -1 if match.group(1) == "m" else 1
    return sign * float(match.group(2))


def parse_isochrone(
    archive: tarfile.TarFile,
    member: tarfile.TarInfo,
) -> dict[float, list[tuple[float, float, float]]]:
    """Read only phase-0 rows in the released age and mass interpolation box."""

    grouped: dict[float, list[tuple[float, float, float]]] = defaultdict(list)
    handle = archive.extractfile(member)
    if handle is None:
        raise ValueError(f"Cannot read {member.name}")
    for raw in handle:
        if raw.startswith(b"#") or not raw.strip():
            continue
        fields = raw.split()
        if len(fields) != 25:
            continue
        log_age = round(float(fields[1]), 2)
        initial_mass = float(fields[2])
        phase = float(fields[24])
        if (
            phase == 0
            and 8.0 <= log_age <= 10.15
            and 0.45 <= initial_mass <= 1.55
        ):
            grouped[log_age].append(
                (initial_mass, float(fields[7]), float(fields[10]))
            )
    return grouped


def build_grid(raw_path: Path) -> pd.DataFrame:
    age_axis = np.round(np.arange(8.0, 10.151, 0.05), 2)
    mass_axis = np.round(np.arange(0.5, 1.501, 0.025), 3)
    records: list[dict[str, float | str]] = []
    with tarfile.open(raw_path, mode="r:xz") as archive:
        members = sorted(
            (member for member in archive.getmembers() if member.name.endswith(".iso")),
            key=lambda member: metallicity_from_name(member.name),
        )
        for member in members:
            feh = metallicity_from_name(member.name)
            grouped = parse_isochrone(archive, member)
            for log_age in age_axis:
                values = sorted(grouped.get(float(log_age), []))
                if len(values) < 2:
                    continue
                source_mass = np.asarray([value[0] for value in values])
                log_luminosity = np.asarray([value[1] for value in values])
                log_teff = np.asarray([value[2] for value in values])
                supported = mass_axis[
                    (mass_axis >= source_mass.min()) & (mass_axis <= source_mass.max())
                ]
                for mass in supported:
                    records.append(
                        {
                            "label": "MODEL-INFERRED",
                            "mist_version": "1.2",
                            "rotation_v_over_vcrit": 0.4,
                            "feh": feh,
                            "log10_age_years": float(log_age),
                            "initial_mass_solar": float(mass),
                            "log10_luminosity_solar": float(
                                np.interp(mass, source_mass, log_luminosity)
                            ),
                            "log10_teff_kelvin": float(
                                np.interp(mass, source_mass, log_teff)
                            ),
                        }
                    )
    frame = pd.DataFrame.from_records(records)
    return frame.sort_values(
        ["feh", "log10_age_years", "initial_mass_solar"]
    ).reset_index(drop=True)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")


def main() -> None:
    root = Path.cwd().resolve()
    raw_path = root / "data/raw/MIST_v1.2_vvcrit0.4_basic_isos.txz"
    if not raw_path.exists():
        download(raw_path)
    if raw_path.stat().st_size != SOURCE_BYTES or sha256(raw_path) != SOURCE_SHA256:
        raise ValueError("MIST source archive failed its byte/hash contract")

    output_dir = root / "results/climate"
    output_dir.mkdir(parents=True, exist_ok=True)
    grid_path = output_dir / "mist_v1p2_main_sequence_grid.csv"
    metadata_path = output_dir / "mist_v1p2_main_sequence_grid.json"
    grid = build_grid(raw_path)
    grid.to_csv(grid_path, index=False, lineterminator="\n", float_format="%.10g")

    source_manifest = {
        "dataset_id": "mist_v1p2_vvcrit0p4_basic_isochrones",
        "archive": "MESA Isochrones and Stellar Tracks (MIST)",
        "source_url": SOURCE_URL,
        "retrieved_utc": RETRIEVED_UTC,
        "version": "MIST v1.2; v/vcrit=0.4; basic theoretical isochrones",
        "bytes": SOURCE_BYTES,
        "sha256": SOURCE_SHA256,
        "licence_and_attribution": "MIST project terms and Choi et al. (2016); Dotter (2016)",
        "raw_payload_committed": False,
    }
    write_json(root / "data/manifests/mist_v1p2_basic_isochrones.json", source_manifest)
    metadata = {
        "schema_version": "1.0",
        "label": "MODEL-INFERRED",
        "model": source_manifest["version"],
        "source_sha256": SOURCE_SHA256,
        "builder_sha256": sha256(Path(__file__)),
        "rows": int(len(grid)),
        "axes": {
            "feh": sorted(grid["feh"].unique().tolist()),
            "log10_age_years": [
                float(grid["log10_age_years"].min()),
                float(grid["log10_age_years"].max()),
                0.05,
            ],
            "initial_mass_solar": [
                float(grid["initial_mass_solar"].min()),
                float(grid["initial_mass_solar"].max()),
                0.025,
            ],
        },
        "selection": "MIST phase=0 main sequence only",
        "columns": grid.columns.tolist(),
        "grid_sha256": sha256(grid_path),
        "claim_boundary": (
            "This is a stellar-evolution model grid, not an observed stellar history. "
            "Missing phase-0 cells are intentionally unsupported."
        ),
    }
    write_json(metadata_path, metadata)
    write_json(
        output_dir / "mist_grid_products.json",
        {
            "schema_version": "1.0",
            "product": "Compact MIST v1.2 main-sequence interpolation grid",
            "files": {
                path.relative_to(root).as_posix(): {
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
                for path in (grid_path, metadata_path)
            },
        },
    )
    print(f"Prepared {len(grid):,} MIST main-sequence grid rows", flush=True)


if __name__ == "__main__":
    main()
