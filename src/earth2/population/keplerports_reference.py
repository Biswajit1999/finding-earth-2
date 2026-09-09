"""Hash-gated reproduction of the official KeplerPORTs KIC 3429335 example.

The upstream implementation is executed only after every required file matches
the pinned NASA repository manifest. It remains external source code and is not
vendored or imported by the scientific pipeline.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType

import numpy as np


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_reference(reference_dir: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("repository") != "https://github.com/nasa/KeplerPORTs":
        raise ValueError("Unexpected reference repository")
    if not manifest.get("commit") or len(manifest["commit"]) != 40:
        raise ValueError("Reference manifest requires a full commit identifier")
    for name, expected in manifest.get("files", {}).items():
        path = reference_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing pinned KeplerPORTs input: {name}")
        if _sha256(path) != expected:
            raise ValueError(f"KeplerPORTs hash mismatch: {name}")
    if len(manifest.get("files", {})) != 6:
        raise ValueError("Incomplete KeplerPORTs reference manifest")
    return manifest


def _load_reference(reference_dir: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "earth2_pinned_keplerports", reference_dir / "KeplerPORTs.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load pinned KeplerPORTs implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reproduce_reference(reference_dir: Path, manifest_path: Path) -> dict:
    """Run the upstream documented star on a compact deterministic check grid."""
    manifest = validate_reference(reference_dir, manifest_path)
    periods = np.array([20.0, 50.0, 100.0, 200.0, 365.25, 500.0, 730.0])
    radii = np.array([0.5, 0.75, 1.0, 1.5, 2.0, 4.0, 8.0, 15.0])
    original_cwd = Path.cwd()
    seed = 21037
    try:
        os.chdir(reference_dir)
        module = _load_reference(Path("."))
        # Upstream draws 10,000 beta variates for MES smearing without setting a
        # seed. Pin the legacy RNG so this reference artifact is reproducible.
        np.random.seed(seed)  # noqa: NPY002 - upstream scipy.stats uses global legacy RNG
        star = module.kepler_single_comp_data()
        star.id = 3429335
        star.rstar = 0.798
        star.logg = 4.578
        star.teff = 5554.0
        star.dataspan = 1458.93
        star.dutycycle = 0.874
        star.limbcoeffs = np.array([0.4869, 0.05340, 0.5129, -0.3007])
        star.cdppSlopeLong = -0.4564
        star.cdppSlopeShort = -0.7051
        star.period_want = periods
        star.rp_want = radii
        star.ecc = 0.0
        star.planet_detection_metric_path = ""
        pipeline, geometry_and_pipeline, _ = module.kepler_single_comp_dr25(star)
        solar_duration = float(module.transit_duration(1.0, 4.437, 365.25, 0.0))
    finally:
        os.chdir(original_cwd)
    if pipeline.shape != (len(radii), len(periods)):
        raise ValueError("Unexpected KeplerPORTs result shape")
    if (
        not np.isfinite(pipeline).all()
        or not np.isfinite(geometry_and_pipeline).all()
        or np.any((pipeline < 0) | (pipeline > 1))
        or np.any((geometry_and_pipeline < 0) | (geometry_and_pipeline > pipeline))
    ):
        raise ValueError("Invalid KeplerPORTs probabilities")
    return {
        "label": "MODEL-INFERRED",
        "scope": "Pinned upstream KeplerPORTs DR25 example for KIC 3429335",
        "upstream_commit": manifest["commit"],
        "upstream_mes_smearing_seed": seed,
        "upstream_mes_smearing_draws": 10000,
        "period_days": periods.tolist(),
        "planet_radius_earth": radii.tolist(),
        "pipeline_including_window": pipeline.tolist(),
        "geometry_times_pipeline_including_window": geometry_and_pipeline.tolist(),
        "solar_circular_mean_duration_hours": solar_duration,
        "interpretation": "Reference-code regression grid, not a survey population estimate",
    }
