"""Entity-resolution tests.

The governing rule this module encodes is "never join on string similarity" --
these tests check the actual match-quality branches (ambiguous vs. unique,
resolved vs. unresolved) rather than just that the functions run.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest

from earth2.crossmatch.resolve import (
    CatalogueIds,
    build_alias_table,
    coordinate_crossmatch,
    extract_catalogue_ids,
    resolve_system,
)


def test_extract_catalogue_ids_finds_each_pattern():
    aliases = [
        "Gaia DR3 2635476908753563008", "TIC 278892590", "TOI-6838",
        "EPIC 246199087", "KIC 12345678", "KOI-123", "HIP 1234", "HD 4567",
        "GJ 667", "2MASS J01234567+0123456", "WISE J01234567+0123456",
        "K2-112", "Kepler-442",
    ]
    ids = extract_catalogue_ids("TRAPPIST-1 e", aliases)
    assert ids.resolved_name == "TRAPPIST-1 e"
    assert ids.ids["gaia_dr3"] == "2635476908753563008"
    assert ids.ids["tic"] == "278892590"
    assert ids.ids["toi"] == "6838"
    assert ids.ids["epic"] == "246199087"
    assert ids.ids["kic"] == "12345678"
    assert ids.ids["koi"] == "123"
    assert ids.ids["hip"] == "1234"
    assert ids.ids["hd"] == "4567"
    assert ids.ids["gj"] == "667"
    assert ids.ids["k2"] == "112"
    assert ids.ids["kepler"] == "442"


def test_extract_catalogue_ids_first_match_wins_per_key():
    """Two aliases matching the same pattern must not overwrite each other --
    the first one found is kept, since these are meant to be a stable identity,
    not a "most recent wins" mutable field."""
    ids = extract_catalogue_ids("X", ["TIC 111", "TIC 222"])
    assert ids.ids["tic"] == "111"


def test_extract_catalogue_ids_ignores_unmatched_aliases():
    ids = extract_catalogue_ids("X", ["some free-text alias", "not an id"])
    assert ids.ids == {}
    assert ids.aliases == ["some free-text alias", "not an id"]


def test_catalogue_ids_to_dict_prefixes_ids():
    ids = extract_catalogue_ids("X", ["TIC 111"])
    d = ids.to_dict()
    assert d["id_tic"] == "111"
    assert d["resolved_name"] == "X"
    assert d["n_aliases"] == 1


def test_coordinate_crossmatch_exact_position_is_high_confidence():
    left = pd.DataFrame({"pl_name": ["Test b"], "ra": [10.0], "dec": [20.0]})
    right = pd.DataFrame({"pl_name": ["Test b (alt)"], "ra": [10.0], "dec": [20.0]})
    out = coordinate_crossmatch(left, right)
    assert len(out) == 1
    assert out.iloc[0]["confidence"] == "high"
    assert out.iloc[0]["right"] == "Test b (alt)"
    assert out.iloc[0]["separation_arcsec"] == pytest.approx(0.0, abs=1e-6)


def test_coordinate_crossmatch_beyond_radius_is_no_match():
    left = pd.DataFrame({"pl_name": ["Test b"], "ra": [10.0], "dec": [20.0]})
    right = pd.DataFrame({"pl_name": ["Far away"], "ra": [10.01], "dec": [20.0]})
    out = coordinate_crossmatch(left, right, radius_arcsec=3.0)
    assert out.iloc[0]["confidence"] == "none"
    assert out.iloc[0]["right"] is None
    assert out.iloc[0]["n_candidates"] == 0


def test_coordinate_crossmatch_flags_ambiguous_when_multiple_sources_in_radius():
    """Two right-hand sources both within the match radius of one left-hand
    source must be reported as ambiguous (low confidence), never silently
    resolved to "the nearest one" without saying so."""
    left = pd.DataFrame({"pl_name": ["Test b"], "ra": [10.0], "dec": [20.0]})
    right = pd.DataFrame({
        "pl_name": ["Candidate A", "Candidate B"],
        "ra": [10.0002, 10.0004],
        "dec": [20.0, 20.0],
    })
    out = coordinate_crossmatch(left, right, radius_arcsec=5.0)
    assert out.iloc[0]["n_candidates"] == 2
    assert out.iloc[0]["confidence"] == "low"
    assert "ambiguous" in out.iloc[0]["note"]


def test_coordinate_crossmatch_empty_inputs_return_empty_frame():
    empty = pd.DataFrame(columns=["pl_name", "ra", "dec"])
    out = coordinate_crossmatch(empty, empty)
    assert out.empty
    assert list(out.columns) == [
        "left", "right", "method", "confidence", "separation_arcsec",
        "n_candidates", "note",
    ]


def test_coordinate_crossmatch_drops_rows_missing_coordinates():
    left = pd.DataFrame({"pl_name": ["A", "B"], "ra": [10.0, None], "dec": [20.0, 20.0]})
    right = pd.DataFrame({"pl_name": ["A2"], "ra": [10.0], "dec": [20.0]})
    out = coordinate_crossmatch(left, right)
    assert len(out) == 1
    assert out.iloc[0]["left"] == "A"


def _fake_response(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(content=json.dumps(payload).encode("utf-8"))


def test_resolve_system_returns_none_on_lookup_failure():
    ok_payload = {"manifest": {"lookup_status": "FAILED"}}
    with patch("earth2.crossmatch.resolve.http_get", return_value=_fake_response(ok_payload)):
        assert resolve_system("Nonexistent Planet X") is None


def test_resolve_system_returns_none_on_network_error():
    with patch("earth2.crossmatch.resolve.http_get", side_effect=OSError("network down")):
        assert resolve_system("TRAPPIST-1 e") is None


def test_resolve_system_parses_stars_and_planets():
    payload = {
        "manifest": {
            "lookup_status": "OK", "requested_name": "TRAPPIST-1 e",
            "resolved_name": "TRAPPIST-1 e", "system_name": "TRAPPIST-1",
            "compilation_date": "2026-01-01",
        },
        "system": {"objects": {
            "stellar_set": {"stars": {
                "TRAPPIST-1": {"alias_set": {"aliases": ["2MASS J23062928-0502285"]}},
            }},
            "planet_set": {"planets": {
                "TRAPPIST-1 e": {"alias_set": {"aliases": ["K2-112 e", "TOI-6838"]}},
            }},
        }},
    }
    with patch("earth2.crossmatch.resolve.http_get", return_value=_fake_response(payload)):
        info = resolve_system("TRAPPIST-1 e")
    assert info is not None
    assert info["n_stars"] == 1
    assert info["n_planets"] == 1
    assert "TRAPPIST-1 e" in info["planets"]
    assert info["planets"]["TRAPPIST-1 e"].ids["toi"] == "6838"


def test_build_alias_table_marks_unresolved_planets_explicitly():
    with patch("earth2.crossmatch.resolve.resolve_system", return_value=None):
        out = build_alias_table(["Unresolvable b"], pause_s=0.0)
    assert len(out) == 1
    assert out.iloc[0]["match_confidence"] == "none"
    assert out.iloc[0]["resolved_name"] is None


def test_build_alias_table_never_attaches_a_different_planets_ids():
    """If the resolver returns a system but the query planet is not among its
    named planets, the row must record that explicitly (medium confidence,
    host-only identifiers) rather than silently attaching some other planet's
    aliases under the queried name."""
    info = {
        "resolved_name": "Some System", "system_name": "Some System",
        "n_stars": 1, "n_planets": 1,
        "stars": {"Host": CatalogueIds(resolved_name="Host", aliases=["HD 1"], ids={"hd": "1"})},
        "planets": {},  # query name "Queried b" is not among the resolved planets
    }
    with patch("earth2.crossmatch.resolve.resolve_system", return_value=info):
        out = build_alias_table(["Queried b"], pause_s=0.0)
    row = out.iloc[0]
    assert row["match_confidence"] == "medium"
    assert "planet name not in resolver planet set" in row["note"]
    assert row["host_id_hd"] == "1"
