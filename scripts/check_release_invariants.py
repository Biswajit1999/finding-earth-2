"""Cross-check the generated result artefacts against each other before a release.

Unit tests validate individual functions against hand-picked inputs; this
script instead validates that the *committed output files* are mutually
consistent -- that the headline scale claim actually sums from the
provenance manifest, that the ranking has no impossible values, and that
Solar System controls never leak into the numbered ranking. None of this
duplicates ``tests/``: it runs against whatever is currently in ``results/``,
which is exactly the thing a reader downloads and a reviewer checks.

Usage::

    python -m earth2 analyse && python -m earth2 export   # regenerate first
    python scripts/check_release_invariants.py

Exits non-zero on the first failed invariant.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402

from earth2.config import RESULTS_DIR  # noqa: E402

FAILURES: list[str] = []


def check(label: str, condition: bool) -> None:
    status = "OK  " if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def main() -> int:
    summary = json.loads((RESULTS_DIR / "analysis_summary.json").read_text())
    prov = json.loads((RESULTS_DIR / "provenance_manifest.json").read_text())
    ranking = pd.read_parquet(RESULTS_DIR / "candidate_ranking.parquet")

    retrieved = sum(int(r["n_rows"]) for r in prov.get("retrievals", []))
    check(
        "total_source_records matches the sum of provenance retrievals",
        retrieved == summary["scale"]["total_source_records"],
    )

    idx = pd.to_numeric(ranking["earth2_index"], errors="coerce").dropna()
    check("earth2_index is within [0, 1] for every scored row", idx.between(0.0, 1.0).all())

    is_control = ranking.get("is_control")
    if is_control is not None:
        is_control = is_control.fillna(False).astype(bool)
        exoplanets = ranking.loc[~is_control]
        check("pl_name is unique among non-control rows", exoplanets["pl_name"].is_unique)

        earth_rows = ranking.loc[is_control & (ranking["pl_name"] == "Earth")]
        check("exactly one Earth control row is present", len(earth_rows) == 1)

        ranked_controls = ranking.loc[is_control, "earth2_rank"].notna()
        check(
            "no Solar System control has a numbered rank",
            not ranked_controls.any() if "earth2_rank" in ranking.columns else True,
        )
    else:
        check("is_control column is present", False)

    if "hz_teff_valid_fraction" in ranking.columns and "score_conservative_habitability" in ranking.columns:
        low_valid = pd.to_numeric(ranking["hz_teff_valid_fraction"], errors="coerce") < 0.2
        high_habitability = pd.to_numeric(ranking["score_conservative_habitability"], errors="coerce") > 0.7
        check(
            "no candidate with <20% HZ-model-valid draws scores >0.7 conservative habitability",
            not (low_valid & high_habitability).any(),
        )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} invariant(s) failed:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("All release invariants passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
