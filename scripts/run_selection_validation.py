"""Generate the deterministic Phase 3 synthetic selection validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from earth2.population.synthetic_validation import run_validation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = run_validation()
    if not result["passed"]:
        raise RuntimeError("Synthetic selection validation failed")
    output = args.root.resolve() / "results/population/synthetic_selection_validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
