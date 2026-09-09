"""Reproduce a compact, hash-gated grid from the official KeplerPORTs example."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from earth2.population.keplerports_reference import reproduce_reference


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--reference-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = root / "data/manifests/population/keplerports_reference.json"
    result = reproduce_reference(args.reference_dir.resolve(), manifest)
    output = root / "results/population/keplerports_reference.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {output} from upstream {result['upstream_commit']}")


if __name__ == "__main__":
    main()
