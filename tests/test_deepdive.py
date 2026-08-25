"""Deep-dive report assembly tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from earth2.reporting.deepdive import _hz_boundaries_au


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
