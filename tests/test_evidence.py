"""Evidence validity and failure tests; no network or fabricated covariance."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace

import pytest

from earth2.evidence import EvidenceGraph, EvidenceLabel, EvidenceNode


def base_graph():
    graph = EvidenceGraph()
    graph.add(EvidenceNode("star", "star", "Fixture star"))
    graph.add(EvidenceNode("planet", "planet", "Fixture planet"))
    graph.link("planet", "orbits", "star")
    graph.add(EvidenceNode("source", "source", "Fixture source"))
    graph.add(EvidenceNode("model", "model", "Fixture model", attributes={"version": "1"}))
    node = EvidenceNode(
        "radius",
        "measurement",
        "Radius",
        EvidenceLabel.OBSERVED,
        {
            "parameter": "radius",
            "unit": "R_earth",
            "value": 1.0,
            "measurement_type": "estimate",
            "uncertainty_plus": None,
        },
    )
    graph.add(node)
    graph.link("radius", "describes", "planet")
    graph.link("radius", "retrieved_from", "source")
    return graph, node


def test_roundtrip_trace_and_missing_uncertainty(tmp_path):
    graph, _ = base_graph()
    graph.save(tmp_path / "graph.sqlite")
    loaded = EvidenceGraph.load(tmp_path / "graph.sqlite")
    assert loaded.trace("radius") == graph.trace("radius")
    assert loaded.measurements("planet", "radius")[0].attributes["uncertainty_plus"] is None
    assert json.loads(json.dumps(loaded.trace("radius")))
    with pytest.raises(FileExistsError):
        graph.save(tmp_path / "graph.sqlite")


def test_conflict_and_dangling_link_rejected():
    graph, node = base_graph()
    with pytest.raises(ValueError, match="Conflicting"):
        graph.add(replace(node, name="Different estimate"))
    with pytest.raises(ValueError, match="Dangling"):
        graph.link("radius", "derived_from", "absent")
    with pytest.raises(ValueError, match="Invalid node kinds"):
        graph.link("star", "orbits", "planet")


@pytest.mark.parametrize(
    "change",
    [
        {"value": float("nan")},
        {"value": float("inf")},
        {"unit": ""},
        {"uncertainty_plus": -1},
        {"measurement_type": "made_up"},
    ],
)
def test_invalid_numeric_and_semantic_data_rejected(change):
    _, node = base_graph()
    with pytest.raises(ValueError):
        replace(node, attributes={**node.attributes, **change}).validate()


def test_scenario_requires_assumptions_and_unknown_requires_explanation():
    _, node = base_graph()
    with pytest.raises(ValueError, match="assumptions"):
        replace(node, label=EvidenceLabel.SCENARIO).validate()
    with pytest.raises(ValueError, match="explanation"):
        replace(node, label=None).validate()
    with pytest.raises(ValueError, match="EvidenceLabel"):
        replace(node, label="OBSERVED").validate()


def test_missing_and_cyclic_derivation_rejected():
    graph, node = base_graph()
    graph.nodes["radius"] = replace(node, label=EvidenceLabel.DERIVED)
    with pytest.raises(ValueError, match="inputs and a model"):
        graph.validate()
    graph.add(replace(node, id="radius2"))
    graph.link("radius2", "describes", "planet")
    graph.link("radius2", "retrieved_from", "source")
    graph.link("radius", "derived_from", "radius2")
    graph.link("radius", "uses_model", "model")
    graph.validate()
    graph.link("radius2", "derived_from", "radius")
    with pytest.raises(ValueError, match="Cyclic"):
        graph.validate()


def test_incomplete_archive_calculation_requires_missing_provenance():
    graph, node = base_graph()
    graph.nodes["radius"] = replace(
        node,
        label=EvidenceLabel.DERIVED,
        attributes={**node.attributes, "provenance_status": "incomplete_external"},
    )
    with pytest.raises(ValueError, match="what is unknown"):
        graph.validate()
    graph.nodes["radius"].attributes["missing_provenance"] = ["archive model version"]
    graph.validate()


def test_unknown_schema_refused(tmp_path):
    graph, _ = base_graph()
    path = tmp_path / "graph.sqlite"
    graph.save(path)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE metadata SET value='future'")
    with pytest.raises(ValueError, match="schema"):
        EvidenceGraph.load(path)


def test_composite_import_preserves_predictions_minimum_masses_and_unknowns(tmp_path):
    import pandas as pd

    from earth2.evidence.catalogue import entity_id, import_v1

    (tmp_path / "results").mkdir()
    (tmp_path / "data/manifests").mkdir(parents=True)
    masses = ["inferred_mass_radius", "msini_lower_limit", "measured", "upper_limit"]
    names = ["Fixture " + str(i) for i in range(4)]
    pd.DataFrame(
        {
            "pl_name": names,
            "hostname": ["Fixture star"] * 4,
            "is_control": [False] * 4,
            "mass_class": masses,
        }
    ).to_parquet(tmp_path / "results/candidate_ranking.parquet")
    pd.DataFrame(
        [
            {
                "pl_name": name,
                "parameter": "pl_bmasse",
                "value": 1.0,
                "source_kind": "archive_calculated" if i == 0 else "publication",
                "reference_key": "CALCULATED_VALUE" if i == 0 else "paper",
                "reference_label": "Fixture source",
                "reference_url": None,
                "bibcode": None,
            }
            for i, name in enumerate(names)
        ]
    ).to_csv(tmp_path / "results/measurement_provenance.csv.gz", index=False)
    (tmp_path / "data/manifests/nasa_pscomppars.json").write_text(
        json.dumps(
            {
                "sha256": "a" * 64,
                "retrieved_utc": "2026-01-01T00:00:00Z",
            }
        )
    )
    graph = import_v1(tmp_path)
    records = [graph.measurements(entity_id("planet", name), "pl_bmasse")[0] for name in names]
    assert records[0].label == EvidenceLabel.MODEL_INFERRED
    assert records[1].attributes["measurement_type"] == "minimum_mass"
    assert records[2].label is None
    assert records[3].attributes["measurement_type"] == "upper_limit"
    assert graph.summary()["nodes_by_kind"]["star"] == 1
    assert all(record.attributes["uncertainty_plus"] is None for record in records)
