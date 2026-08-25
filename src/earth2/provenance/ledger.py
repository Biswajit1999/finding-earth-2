"""Transformation ledger.

Manifests record what came *in*. The ledger records what the pipeline *did* to
it. Together they close the chain the project promises on every candidate page::

    archive table -> source publication -> retrieval -> input measurement
                  -> transformation -> derived quantity -> ranking contribution

Each :class:`Transformation` is one deterministic step. The ledger is appended
to as the pipeline runs and serialised next to the results, so a reader can walk
backwards from any published number to the archive row it came from.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from earth2.provenance.manifest import utc_now_iso


@dataclass
class Transformation:
    """One deterministic pipeline step.

    Parameters
    ----------
    step
        Short stable identifier, e.g. ``compute_insolation``.
    description
        One sentence a scientist can read without opening the code.
    inputs
        Column or dataset names consumed.
    outputs
        Column or dataset names produced.
    equation
        The equation applied, in plain text or LaTeX. Empty for pure I/O steps.
    citation
        Bibliography key(s) backing the method, e.g. ``kopparapu2013``.
    parameters
        Any constants/choices that affect the result (albedo, seed, n_samples).
    n_rows_in, n_rows_out
        Row counts, so silent row loss is visible in the ledger itself.
    """

    step: str
    description: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    equation: str = ""
    citation: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    n_rows_in: int = 0
    n_rows_out: int = 0
    timestamp_utc: str = field(default_factory=utc_now_iso)
    software: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TransformLedger:
    """Ordered, serialisable list of transformations."""

    def __init__(self, name: str = "pipeline") -> None:
        self.name = name
        self.steps: list[Transformation] = []

    def record(self, transformation: Transformation) -> Transformation:
        self.steps.append(transformation)
        return transformation

    def add(self, step: str, description: str, **kw: Any) -> Transformation:
        """Convenience constructor + record in one call."""
        return self.record(Transformation(step=step, description=description, **kw))

    def __len__(self) -> int:
        return len(self.steps)

    def __iter__(self):
        return iter(self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger": self.name,
            "generated_utc": utc_now_iso(),
            "n_steps": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
        }

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> TransformLedger:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        led = cls(data.get("ledger", "pipeline"))
        known = set(Transformation.__dataclass_fields__)  # type: ignore[attr-defined]
        for s in data.get("steps", []):
            led.steps.append(Transformation(**{k: v for k, v in s.items() if k in known}))
        return led

    def find(self, step: str) -> Transformation | None:
        for s in self.steps:
            if s.step == step:
                return s
        return None
