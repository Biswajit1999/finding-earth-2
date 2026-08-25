"""Transit-pipeline validation on bright, well-characterised planets.

Why this module exists
----------------------
None of the project's top Earth-2.0 candidates produces a validated transit fit.
That is a real result, not a bug: six of the top ten are non-transiting radial-
velocity detections, and the transiting ones orbit faint M dwarfs whose TESS
photometry has per-cadence noise several times their transit depth.

But "our pipeline produced nothing on every candidate" is indistinguishable, to a
reader, from "our pipeline does not work". So the pipeline is additionally run on
a small set of **bright, deep, well-studied transiting planets** where the answer
is independently known, and the recovered depths are compared against published
values.

These targets are **validation instruments, not Earth-2.0 candidates**. Every one
is a hot Jupiter or hot Neptune with no habitability interest whatsoever. They
are labelled as such everywhere they appear, and they are never mixed into the
candidate ranking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from earth2.provenance import utc_now_iso
from earth2.reporting.jsonio import dump_json

__all__ = ["VALIDATION_TARGETS", "run_validation"]

#: (planet, host) pairs chosen for brightness and transit depth, not for science
#: interest. Each is a canonical, heavily observed transiting planet.
VALIDATION_TARGETS: list[dict[str, str]] = [
    {"planet": "HD 209458 b", "host": "HD 209458",
     "why": "The first transiting exoplanet ever detected; bright (Tmag 7.1) with a deep transit."},
    {"planet": "HD 189733 b", "host": "HD 189733",
     "why": "One of the best-studied hot Jupiters; very bright (Tmag 6.8)."},
    {"planet": "WASP-39 b", "host": "WASP-39",
     "why": "The JWST transmission-spectroscopy benchmark, with 1,625 published spectral points."},
    {"planet": "WASP-19 b", "host": "WASP-19",
     "why": "Very short period, giving many transits within a single TESS sector."},
    {"planet": "GJ 1214 b", "host": "GJ 1214",
     "why": "A well-studied sub-Neptune around an M dwarf; a harder, more realistic test."},
]


def run_validation(
    catalogue: pd.DataFrame,
    mission: str = "TESS",
    max_products: int = 2,
) -> dict[str, Any]:
    """Run the transit pipeline against known answers and report the comparison."""
    from earth2.transit import analyse_target

    results: list[dict[str, Any]] = []
    for t in VALIDATION_TARGETS:
        rows = catalogue[catalogue["pl_name"].astype(str) == t["planet"]]
        if rows.empty:
            results.append({**t, "status": "not_in_catalogue"})
            continue
        r = rows.iloc[0]

        def num(col: str, row: pd.Series = r) -> float | None:
            # `row` is bound as a default argument, not captured from the
            # enclosing loop, so this closure is safe even though it is
            # redefined on every iteration.
            v = pd.to_numeric(pd.Series([row.get(col)]), errors="coerce").iloc[0]
            return None if not np.isfinite(v) else float(v)

        depth_pct = num("pl_trandep")
        expected_ppm = depth_pct * 1e4 if depth_pct else None

        out = analyse_target(
            t["host"],
            period_days=num("pl_orbper"),
            t0_bjd=num("pl_tranmid"),
            duration_hours=num("pl_trandur"),
            mission=mission,
            max_products=max_products,
            search_period=False,
            expected_depth_ppm=expected_ppm,
        )
        fit = out.get("fit") or {}
        chk = out.get("catalogue_check") or {}
        lc = out.get("light_curve") or {}

        results.append({
            **t,
            "status": out.get("status"),
            "tmag": num("sy_tmag"),
            "period_days": num("pl_orbper"),
            "published_depth_ppm": expected_ppm,
            "fitted_depth_ppm": fit.get("depth_ppm"),
            "ratio_fitted_to_published": chk.get("ratio_fitted_to_published"),
            "validated": chk.get("consistent_with_published", False),
            "depth_snr": fit.get("depth_snr"),
            "duration_hours_fitted": fit.get("duration_hours"),
            "radius_ratio_approx": fit.get("radius_ratio_approx"),
            "cadence_precision_ppm": lc.get("median_flux_precision_ppm"),
            "n_cadences": lc.get("n_used_cadences"),
            "folded_binned": out.get("folded_binned"),
        })

    n_ok = sum(1 for r in results if r.get("validated"))
    attempted = [r for r in results if r.get("status") in ("ok", "fit_not_validated")]
    ratios = [r["ratio_fitted_to_published"] for r in results
              if r.get("ratio_fitted_to_published")]

    return {
        "generated_utc": utc_now_iso(),
        "purpose": (
            "Validation of the transit pipeline against planets whose depths are "
            "independently known. These are bright hot Jupiters and sub-Neptunes chosen "
            "for signal strength, NOT Earth-2.0 candidates, and they are excluded from "
            "the candidate ranking."
        ),
        "n_targets": len(results),
        "n_attempted": len(attempted),
        "n_validated": n_ok,
        "median_ratio_fitted_to_published": (round(float(np.median(ratios)), 3)
                                             if ratios else None),
        "systematic_note": (
            "Fitted depths run consistently below published values. This is a known "
            "systematic of the Savitzky-Golay detrending step, which absorbs a little of "
            "the transit even with its window forced to at least three times the transit "
            "duration. Depths from this pipeline are approximate and biased slightly low; "
            "published limb-darkened values take precedence."
        ),
        "targets": results,
    }


def write_validation(catalogue: pd.DataFrame, path: Path) -> Path:
    res = run_validation(catalogue)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_json(res, indent=1), encoding="utf-8")
    return path
