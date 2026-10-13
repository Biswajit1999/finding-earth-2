"""Check that displayed exoplanet points are not confused with unique host stars.

These checks operate on the published, versioned snapshot rather than claiming
live NASA Exoplanet Archive or Gaia data. Both browser views plot one record
per confirmed planet at the corresponding host-star position.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_universe_and_galaxy_use_one_record_per_plotted_planet() -> None:
    universe = _json("web/public/data/universe.json")
    galaxy = _json("web/public/data/galaxy.json")
    summary = _json("results/analysis_summary.json")
    history = _json("web/public/data/discovery_timeline.json")

    n_planets = summary["population"]["n_confirmed_planets"]
    n_points = universe["n_points"]
    n_excluded = universe["n_excluded_no_distance"]

    assert n_points + n_excluded == n_planets
    assert n_points == len(universe["name"]) == len(universe["host"])
    assert len(set(universe["name"])) == n_points
    assert len(set(universe["host"])) < n_points

    # The two projections and the discovery history use the same row filter.
    assert galaxy["n_points"] == n_points
    assert galaxy["n_excluded_no_distance"] == n_excluded
    assert galaxy["name"] == universe["name"]
    assert galaxy["host"] == universe["host"]
    assert history["total_count_by_year"][-1] == n_points
    assert sum(v[-1] for v in history["method_share_counts_by_year"].values()) == n_points

    # The full-catalogue host count is NOT the same as the plotted host count.
    assert len(set(universe["host"])) <= summary["population"]["n_unique_host_systems"]


def test_map_labels_disambiguate_planets_and_hosts() -> None:
    universe = (ROOT / "web/components/universe/UniverseExplorer.tsx").read_text(encoding="utf-8")
    galaxy = (ROOT / "web/components/galaxy/GalaxyExplorer.tsx").read_text(encoding="utf-8")
    page = (ROOT / "web/app/universe/page.tsx").read_text(encoding="utf-8")

    assert 'countMode === "hosts" ? uniqueHostCount : data.n_points' in universe
    assert 'countMode === "hosts" ? "host stars" : "planets"' in universe
    assert "planet records" in universe
    assert "host-star positions" in galaxy
    assert "Multiple planets orbiting one star" in page
