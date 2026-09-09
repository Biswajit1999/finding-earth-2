"""Fetch/verify DR25 products and export injection-conditioned diagnostics."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from earth2.population.archive import fetch_product
from earth2.population.kepler import StellarSelection, empirical_grid, join_injections


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    frames, manifests = {}, {}
    for kind in ("stars", "injections", "vetting"):
        print(f"Verifying/retrieving {kind} ...", flush=True)
        frames[kind], manifests[kind] = fetch_product(root, kind)
        print(f"  {len(frames[kind]):,} validated rows", flush=True)
    joined = join_injections(frames["injections"], frames["vetting"], frames["stars"])
    selection = StellarSelection()
    selected_stars = frames["stars"].loc[selection.select(frames["stars"])]
    selected = joined.loc[joined["kepid"].isin(selected_stars["kepid"])]
    radius_edges = np.array([0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 10, 16])
    period_edges = np.array([0.5, 2, 5, 10, 20, 50, 100, 200, 300, 400, 500])
    grid = empirical_grid(selected, radius_edges, period_edges)
    output = root / "results" / "population"
    output.mkdir(parents=True, exist_ok=True)
    grid.to_csv(output / "dr25_injection_grid.csv", index=False, float_format="%.10g")
    summary = {
        "label": "SIMULATED",
        "scope": "Official DR25 artificial-signal experiment; selected stellar subset",
        "interpretation": "Recovery conditional on the injection proposal, not a population selection surface or occurrence rate.",
        "selection": asdict(selection),
        "selection_additional_requirements": "Finite positive mass, radius, dataspan, six-hour CDPP and MES threshold; 0 < dutycycle <= 1",
        "archive_stellar_rows": len(frames["stars"]),
        "selected_stars": len(selected_stars),
        "injections_all": len(joined),
        "injections_without_stellar_match": int(joined["kepid"].isna().sum()),
        "recovered_all": int(joined["pipeline_recovered"].sum()),
        "recovery_code_2_all": int(joined["recovery_code_2"].sum()),
        "recovery_definition": "Codes 1 and 2 with a matching official INJ1 TCE; code 2 audited separately, not asserted to have a correct recovered period",
        "vetted_pc_all": int(joined["vetted_pc"].sum()),
        "injections_selected": len(selected),
        "recovered_selected": int(selected["pipeline_recovered"].sum()),
        "recovery_code_2_selected": int(selected["recovery_code_2"].sum()),
        "vetted_pc_selected": int(selected["vetted_pc"].sum()),
        "selected_stars_without_injection": int(
            (~selected_stars["kepid"].isin(selected["KIC_ID"])).sum()
        ),
        "grid_injections": int(grid["n_injected"].sum()),
        "grid_empty_cells": int(grid["n_injected"].eq(0).sum()),
        "interval": "95% equal-tail Beta posterior, Jeffreys Beta(0.5,0.5) prior; empty cells undefined",
        "radius_convention": "Original DR25 radius times injected Rp/Rstar; IAU nominal solar and equatorial Earth radii from astropy.constants",
        "transit_criterion": "centre_crossing, b in [0,1]; circular injected orbits",
        "source_hashes": {key: value["sha256"] for key, value in manifests.items()},
        "scientific_gates_open": [
            "Verified searched-target denominator and per-target calibration",
            "Injection-proposal correction or validated per-target detection model",
            "False-alarm reliability and astrophysical false-positive treatment",
            "Measurement uncertainties and prior-consistent hierarchical likelihood",
            "Synthetic recovery and literature-matched occurrence comparison",
        ],
    }
    (output / "dr25_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
