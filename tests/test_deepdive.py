"""Deep-dive report assembly tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from earth2.reporting.deepdive import _hz_boundaries_au, _preserved_analysis


def test_hz_boundaries_au_computes_all_five_boundaries():
    r = pd.Series({"st_teff": 5772.0, "st_lum": 0.0})  # a Sun-like host
    out = _hz_boundaries_au(r)
    assert set(out) == {
        "recent_venus", "runaway_greenhouse", "moist_greenhouse",
        "maximum_greenhouse", "early_mars",
    }
    # For a Sun-like host, the runaway-greenhouse (inner) boundary should sit
    # just inside 1 au, and the boundaries should be strictly ordered from
    # innermost (highest flux) to outermost.
    ordered = [out[b] for b in (
        "recent_venus", "runaway_greenhouse", "moist_greenhouse",
        "maximum_greenhouse", "early_mars",
    )]
    assert all(v is not None for v in ordered)
    assert ordered == sorted(ordered)
    assert 0.9 < out["runaway_greenhouse"] < 1.0


def test_hz_boundaries_au_returns_none_for_missing_host_parameters():
    r = pd.Series({"st_teff": np.nan, "st_lum": 0.0})
    out = _hz_boundaries_au(r)
    assert all(v is None for v in out.values())


def test_live_analysis_is_preserved_during_catalogue_only_rebuild():
    previous = {
        "generated_utc": "2026-08-24T22:50:11Z",
        "rv_analysis": {"attempted": True, "n_observations": 321},
    }

    preserved = _preserved_analysis(previous, "rv_analysis", requested=False)

    assert preserved is not None
    assert preserved["n_observations"] == 321
    assert preserved["archive_status"] == {
        "preserved": True,
        "reason": "Live-source refresh was not requested for this catalogue rebuild.",
        "from_deep_dive_generated_utc": "2026-08-24T22:50:11Z",
    }
    assert "archive_status" not in previous["rv_analysis"]


def test_live_analysis_is_not_preserved_when_refresh_is_requested():
    previous = {"rv_analysis": {"attempted": True, "n_observations": 321}}

    assert _preserved_analysis(previous, "rv_analysis", requested=True) is None


def test_legacy_status_based_live_analysis_is_preserved():
    previous = {
        "generated_utc": "2026-08-24T22:50:11Z",
        "transit_analysis": {"status": "fit_not_validated", "n_points": 778},
    }

    preserved = _preserved_analysis(
        previous, "transit_analysis", requested=False,
    )

    assert preserved is not None
    assert preserved["status"] == "fit_not_validated"
    assert preserved["n_points"] == 778
