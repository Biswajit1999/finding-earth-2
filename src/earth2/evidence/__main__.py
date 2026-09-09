"""Rebuild the evidence index from the committed v1 products, without network."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from earth2.config import ROOT
from earth2.evidence.catalogue import entity_id, import_v1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--database", type=Path, help="New SQLite file; existing files are refused")
    parser.add_argument("--output", type=Path, default=ROOT / "results/evidence")
    args = parser.parse_args()
    graph = import_v1(args.root)
    if args.database:
        graph.save(args.database)
    args.output.mkdir(parents=True, exist_ok=True)
    summary = graph.summary()
    summary["scope"] = "v1 composite reference index; not all published measurement solutions"
    summary["baseline_commit"] = "82d5b127418e32d2cacc95c6ed12dc8dad140bac"
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    examples = {}
    for planet in ("Proxima Cen b", "GJ 1061 d", "Kepler-442 b", "TRAPPIST-1 e"):
        examples[planet] = [
            graph.trace(n.id) for n in graph.measurements(entity_id("planet", planet), "pl_bmasse")
        ]
    (args.output / "mass_evidence_examples.json").write_text(
        json.dumps(examples, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
