"""Small relational evidence graph with explicit missing provenance.

Unknown fields remain null. A reference to a publication is not proof that a
quantity was independently measured. Derived results require input links unless
they are explicitly incomplete external archive calculations.
"""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class EvidenceLabel(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    MODEL_INFERRED = "MODEL-INFERRED"
    SCENARIO = "SCENARIO"
    FORECAST = "FORECAST"
    SIMULATED = "SIMULATED"


@dataclass(frozen=True)
class EvidenceNode:
    id: str
    kind: str
    name: str
    label: EvidenceLabel | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.id or not self.name:
            raise ValueError("Evidence nodes require an identifier and name")
        if self.kind not in {"star", "planet", "measurement", "quantity", "source", "model"}:
            raise ValueError(f"Unsupported node kind: {self.kind}")
        if self.label is not None and not isinstance(self.label, EvidenceLabel):
            raise ValueError("Use an EvidenceLabel, never an unvalidated evidence claim")
        # Also rejects non-finite numbers nested in assumptions or uncertainties.
        json.dumps(asdict(self), allow_nan=False)
        a = self.attributes
        if self.kind in {"measurement", "quantity"}:
            if not a.get("parameter") or not a.get("unit"):
                raise ValueError("Quantities require a parameter and explicit unit")
            v = a.get("value")
            if v is not None and (
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            ):
                raise ValueError("Scalar quantities require a finite numeric value or null")
            for k in ("uncertainty_plus", "uncertainty_minus"):
                if a.get(k) is not None and a[k] < 0:
                    raise ValueError("Uncertainties are nonnegative magnitudes")
            if a.get("measurement_type") not in {
                "estimate",
                "minimum_mass",
                "upper_limit",
                "lower_limit",
                "external_calculation",
                "prediction",
                "unknown",
            }:
                raise ValueError("Explicit measurement_type required")
            if self.label is None and not a.get("classification_unknown_reason"):
                raise ValueError("Unclassified evidence requires an explanation")
        if self.label in {
            EvidenceLabel.SCENARIO,
            EvidenceLabel.FORECAST,
            EvidenceLabel.SIMULATED,
        } and not a.get("assumptions"):
            raise ValueError("Scenarios, forecasts and simulations require assumptions")


class EvidenceGraph:
    """Typed nodes and directed subject-to-dependency edges; no fuzzy entity joins."""

    def __init__(self) -> None:
        self.nodes: dict[str, EvidenceNode] = {}
        self.edges: set[tuple[str, str, str]] = set()

    def add(self, node: EvidenceNode) -> str:
        node.validate()
        if node.id in self.nodes and self.nodes[node.id] != node:
            raise ValueError(f"Conflicting evidence for identifier {node.id}")
        self.nodes[node.id] = node
        return node.id

    def link(self, subject: str, relation: str, dependency: str) -> None:
        if relation not in {
            "orbits",
            "describes",
            "retrieved_from",
            "published_in",
            "uses_model",
            "derived_from",
        }:
            raise ValueError(f"Unsupported evidence relation: {relation}")
        if subject not in self.nodes or dependency not in self.nodes:
            raise ValueError("Dangling evidence link")
        kinds = (self.nodes[subject].kind, self.nodes[dependency].kind)
        allowed = {
            "orbits": ({"planet"}, {"star"}),
            "describes": ({"measurement", "quantity"}, {"star", "planet"}),
            "retrieved_from": ({"measurement", "quantity", "source"}, {"source"}),
            "published_in": ({"measurement", "quantity", "model"}, {"source"}),
            "uses_model": ({"measurement", "quantity"}, {"model"}),
            "derived_from": ({"quantity", "measurement"}, {"quantity", "measurement"}),
        }
        a, b = allowed[relation]
        if kinds[0] not in a or kinds[1] not in b:
            raise ValueError("Invalid node kinds for evidence relation")
        if subject == dependency:
            raise ValueError("Self-dependent evidence")
        self.edges.add((subject, relation, dependency))

    def validate(self) -> None:
        dependencies: dict[str, list[str]] = {}
        relations: dict[str, set[str]] = {}
        for subject, relation, dep in self.edges:
            if subject not in self.nodes or dep not in self.nodes:
                raise ValueError("Dangling evidence link")
            relations.setdefault(subject, set()).add(relation)
            if relation == "derived_from":
                dependencies.setdefault(subject, []).append(dep)
        state: dict[str, int] = {}

        def visit(key: str) -> None:
            if state.get(key) == 1:
                raise ValueError("Cyclic scientific derivation")
            if state.get(key) == 2:
                return
            state[key] = 1
            for dep in dependencies.get(key, []):
                visit(dep)
            state[key] = 2

        for key, node in self.nodes.items():
            node.validate()
            visit(key)
            if node.kind not in {"measurement", "quantity"}:
                continue
            r = relations.get(key, set())
            if "describes" not in r:
                raise ValueError("A quantity must describe a physical entity")
            if node.kind == "measurement" and "retrieved_from" not in r:
                raise ValueError("A measurement requires its retrieval source")
            if node.label in {EvidenceLabel.DERIVED, EvidenceLabel.MODEL_INFERRED}:
                if node.attributes.get("provenance_status") == "incomplete_external":
                    if not node.attributes.get("missing_provenance"):
                        raise ValueError("Incomplete provenance must list what is unknown")
                elif not {"derived_from", "uses_model"} <= r:
                    raise ValueError("Derived quantities require inputs and a model")

    def measurements(self, entity_id: str, parameter: str) -> list[EvidenceNode]:
        keys = {s for s, r, d in self.edges if r == "describes" and d == entity_id}
        return [
            self.nodes[k]
            for k in sorted(keys)
            if self.nodes[k].attributes.get("parameter") == parameter
        ]

    def trace(self, node_id: str) -> dict[str, Any]:
        if node_id not in self.nodes:
            raise KeyError(node_id)
        seen: set[str] = set()
        pending = [node_id]
        outgoing: dict[str, list[tuple[str, str, str]]] = {}
        for edge in self.edges:
            outgoing.setdefault(edge[0], []).append(edge)
        found = set()
        while pending:
            key = pending.pop()
            if key in seen:
                continue
            seen.add(key)
            for edge in outgoing.get(key, []):
                found.add(edge)
                pending.append(edge[2])
        return {
            "root": node_id,
            "nodes": [asdict(self.nodes[k]) for k in sorted(seen)],
            "edges": sorted(found),
        }

    def summary(self) -> dict[str, Any]:
        kinds: dict[str, int] = {}
        labels: dict[str, int] = {}
        missing = 0
        for n in self.nodes.values():
            kinds[n.kind] = kinds.get(n.kind, 0) + 1
            if n.kind in {"quantity", "measurement"}:
                label = n.label.value if n.label else "UNCLASSIFIED"
                labels[label] = labels.get(label, 0) + 1
                missing += bool(n.attributes.get("missing_provenance"))
        return {
            "schema_version": "1.0",
            "nodes_by_kind": kinds,
            "quantity_labels": labels,
            "edges": len(self.edges),
            "records_with_provenance_gaps": missing,
            "independent_measurement_count": None,
        }

    def save(self, path: Path) -> None:
        """Write a new database; never overwrite an existing scientific snapshot."""
        self.validate()
        path = Path(path)
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT INTO metadata VALUES ('schema_version','1.0')")
            db.execute(
                "CREATE TABLE nodes (id TEXT PRIMARY KEY, kind TEXT NOT NULL, "
                "name TEXT NOT NULL, label TEXT, attributes TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE edges (subject TEXT REFERENCES nodes(id), relation TEXT, "
                "dependency TEXT REFERENCES nodes(id), "
                "PRIMARY KEY(subject,relation,dependency))"
            )
            db.execute("CREATE INDEX edges_dependency ON edges(dependency,relation)")
            db.executemany(
                "INSERT INTO nodes VALUES (?,?,?,?,?)",
                [
                    (
                        n.id,
                        n.kind,
                        n.name,
                        n.label.value if n.label else None,
                        json.dumps(n.attributes, sort_keys=True, allow_nan=False),
                    )
                    for n in self.nodes.values()
                ],
            )
            db.executemany("INSERT INTO edges VALUES (?,?,?)", sorted(self.edges))

    @classmethod
    def load(cls, path: Path) -> EvidenceGraph:
        graph = cls()
        if not Path(path).is_file():
            raise FileNotFoundError(path)
        with sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) as db:
            version = db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if version != ("1.0",):
                raise ValueError("Unsupported evidence schema version")
            for key, kind, name, label, attributes in db.execute("SELECT * FROM nodes"):
                graph.add(
                    EvidenceNode(
                        key,
                        kind,
                        name,
                        EvidenceLabel(label) if label else None,
                        json.loads(attributes),
                    )
                )
            for subject, relation, dep in db.execute("SELECT * FROM edges"):
                graph.link(subject, relation, dep)
        graph.validate()
        return graph
