"""Run and export the expanded hierarchical occurrence recovery suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from earth2.population.hierarchical_validation import run_hierarchical_recovery


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--replicates", type=int, default=60)
    parser.add_argument("--posterior-draws", type=int, default=256)
    args = parser.parse_args()
    result = run_hierarchical_recovery(
        seed=args.seed,
        replicates=args.replicates,
        posterior_draws=args.posterior_draws,
    )
    if not result["passed"]:
        failed = [row["scenario"] for row in result["scenarios"] if not row["passed"]]
        raise RuntimeError(f"Hierarchical recovery gate failed: {failed}")
    output = args.root.resolve() / "results/population/validation"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "hierarchical_recovery.json"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(
        f"Hierarchical recovery passed {len(result['scenarios'])} scenarios: {path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
