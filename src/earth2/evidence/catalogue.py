"""Import archived composite parameter references without inventing provenance.

This adapter reads the committed v1 provenance and ranking, so it works on a
clean clone. It does not pretend their absent uncertainty/reduction fields exist.
Individual published solutions can be added separately; they are not reconstructed
from the archive's composite selection.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd

from earth2.evidence.graph import EvidenceGraph, EvidenceLabel, EvidenceNode

UNITS = {
    "pl_rade": "R_earth",
    "pl_bmasse": "M_earth",
    "pl_orbper": "day",
    "pl_orbsmax": "au",
    "pl_insol": "S_earth",
    "pl_eqt": "K",
    "pl_dens": "g cm-3",
    "pl_orbeccen": "dimensionless",
    "st_teff": "K",
    "st_rad": "R_sun",
    "st_mass": "M_sun",
    "st_lum": "dex(L_sun)",
    "st_met": "dex",
    "st_age": "Gyr",
    "sy_dist": "pc",
}


def entity_id(kind: str, name: str) -> str:
    return kind + ":" + quote(name, safe="")


def _optional(value: Any) -> Any:
    return None if pd.isna(value) else value


def import_v1(root: Path) -> EvidenceGraph:
    root = Path(root)
    graph = EvidenceGraph()
    ranking = pd.read_parquet(root / "results/candidate_ranking.parquet")
    ranking = ranking[~ranking["is_control"].astype(bool)].set_index("pl_name")
    provenance_path = root / "results/measurement_provenance.csv.gz"
    provenance = pd.read_csv(provenance_path)
    manifest = json.loads((root / "data/manifests/nasa_pscomppars.json").read_text())
    source_id = "source:nasa_pscomppars:" + manifest["sha256"]
    graph.add(
        EvidenceNode(
            source_id,
            "source",
            "NASA pscomppars v1 retrieval",
            attributes={
                **manifest,
                "local_provenance_file_sha256": hashlib.sha256(
                    provenance_path.read_bytes()
                ).hexdigest(),
                "software_commit": None,
                "missing_provenance": ["v1 retrieval software commit not recorded"],
            },
        )
    )
    for planet, row in ranking.iterrows():
        star = entity_id("star", str(row["hostname"]))
        graph.add(EvidenceNode(star, "star", str(row["hostname"])))
        pid = graph.add(EvidenceNode(entity_id("planet", str(planet)), "planet", str(planet)))
        graph.link(pid, "orbits", star)

    for row in provenance.to_dict(orient="records"):
        planet, param = str(row["pl_name"]), str(row["parameter"])
        if planet not in ranking.index or param not in UNITS or pd.isna(row["value"]):
            continue
        source_kind = row["source_kind"]
        missing = [
            "instrument",
            "facility",
            "observation_program",
            "reduction",
            "observation_timestamp",
            "covariance",
            "parameter_uncertainties",
        ]
        mass_class = str(ranking.loc[planet, "mass_class"]) if param == "pl_bmasse" else None
        label: EvidenceLabel | None = EvidenceLabel.OBSERVED
        measurement_type = "estimate"
        unknown_reason = None
        if source_kind == "archive_calculated":
            label = EvidenceLabel.DERIVED
            measurement_type = "external_calculation"
            missing += ["exact_input_records", "archive_equation_version", "assumptions"]
        if param == "pl_bmasse":
            if mass_class == "inferred_mass_radius":
                label = EvidenceLabel.MODEL_INFERRED
                measurement_type = "prediction"
                missing += ["exact_mass_radius_model", "model_version", "input_records"]
            elif mass_class == "msini_lower_limit":
                measurement_type = "minimum_mass"
            elif mass_class == "upper_limit":
                measurement_type = "upper_limit"
            else:
                # The committed v1 mass class is insufficient to certify true mass.
                label = None
                measurement_type = "unknown"
                unknown_reason = "v1 mass class requires publication-level verification"
        identity = json.dumps([source_id, planet, param, _optional(row["reference_key"])])
        key = "measurement:" + hashlib.sha256(identity.encode()).hexdigest()[:24]
        attrs = {
            "parameter": param,
            "value": float(row["value"]),
            "unit": UNITS[param],
            "measurement_type": measurement_type,
            "uncertainty_plus": None,
            "uncertainty_minus": None,
            "covariance": None,
            "instrument": None,
            "facility": None,
            "observation_program": None,
            "reduction": None,
            "observation_timestamp": None,
            "retrieval_utc": manifest["retrieved_utc"],
            "source_kind": source_kind,
            "archive_reference_key": _optional(row["reference_key"]),
            "bibcode": _optional(row["bibcode"]),
            "doi": None,
            "missing_provenance": sorted(set(missing)),
            "classification_unknown_reason": unknown_reason,
            "provenance_status": "incomplete_external",
            "v1_mass_class": mass_class,
            "interpretation": "Archive-reported parameter estimate; independence not established",
        }
        graph.add(EvidenceNode(key, "measurement", planet + " / " + param, label, attrs))
        target = (
            entity_id("star", str(ranking.loc[planet, "hostname"]))
            if param.startswith(("st_", "sy_"))
            else entity_id("planet", planet)
        )
        graph.link(key, "describes", target)
        graph.link(key, "retrieved_from", source_id)
        ref = _optional(row["reference_key"])
        if ref and source_kind == "publication":
            ref_id = entity_id("source", str(ref))
            node = EvidenceNode(
                ref_id,
                "source",
                str(_optional(row["reference_label"]) or ref),
                attributes={
                    "url": _optional(row["reference_url"]),
                    "bibcode": _optional(row["bibcode"]),
                    "doi": None,
                },
            )
            # Identical reference keys can have differently formatted labels/URLs.
            # Retain the exact per-measurement record rather than silently coalescing.
            ref_id += (
                ":"
                + hashlib.sha256(
                    json.dumps(node.attributes, sort_keys=True).encode() + node.name.encode()
                ).hexdigest()[:16]
            )
            graph.add(EvidenceNode(ref_id, node.kind, node.name, attributes=node.attributes))
            graph.link(key, "published_in", ref_id)
    graph.validate()
    return graph
