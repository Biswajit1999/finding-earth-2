"""Generate deterministic Beyond Earth 2.0 feasibility products."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from earth2.futures.distance import distance_summary, extragalactic_feasibility

ROOT = Path(__file__).resolve().parents[1]

DISTANCES = (
    ("Proxima Centauri", 1.301),
    ("Nearby survey horizon", 10.0),
    ("Milky Way kiloparsec", 1_000.0),
    ("Andromeda / Local Group", 780_000.0),
    ("M51 candidate host galaxy", 8_600_000.0),
    ("Nearby cosmological volume", 100_000_000.0),
)


def build() -> dict[str, object]:
    rows = []
    for label, distance_pc in DISTANCES:
        row = {"label": label, **extragalactic_feasibility(distance_pc)}
        rows.append(row)
    output = ROOT / "results" / "futures"
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "extragalactic_earth_feasibility.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "schema_version": "1.0",
        "label": "PHYSICS-BASED CALCULATION",
        "title": "Beyond Earth 2.0 distance and extragalactic feasibility",
        "assumptions": {
            "planet": "Earth radius, geometric albedo 0.3, Lambert phase at quadrature",
            "star": "solar bolometric luminosity",
            "telescope": "6 m diameter, 20% throughput, 550 nm photon-energy conversion",
            "photon_warning": "optimistic upper bound: all reflected bolometric power is treated as 550 nm photons; backgrounds and stellar leakage omitted",
            "resolution": "Rayleigh 1.22 lambda/D; separate 1 AU and resolve one Earth diameter",
        },
        "case_study": {
            "name": "M51-ULS-1b",
            "status": "UNCONFIRMED EXTRAGALACTIC PLANET CANDIDATE; not an Earth analogue",
            "distance_pc": 8_600_000,
            "method": "single X-ray eclipse of a compact X-ray source",
            "source": "Di Stefano et al. 2021, Nature Astronomy, doi:10.1038/s41550-021-01495-w",
        },
        "feasibility": rows,
        "reference_journey": distance_summary(1.301),
    }
    (output / "beyond_frontier.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    web = ROOT / "web" / "public" / "data" / "beyond-frontier.json"
    web.parent.mkdir(parents=True, exist_ok=True)
    web.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    return {"rows": len(rows), "json": str(output / "beyond_frontier.json"), "csv": str(csv_path)}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
