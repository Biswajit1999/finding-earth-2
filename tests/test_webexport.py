from __future__ import annotations

import math

import astropy.units as u_
import numpy as np
import pandas as pd
import pytest
from astropy.coordinates import SkyCoord

from earth2.reporting.webexport import (
    GALACTIC_CENTRE_DEC_DEG,
    GALACTIC_CENTRE_RA_DEG,
    GALCEN_DISTANCE_KPC,
    SUN_HEIGHT_PC,
    export_discovery_timeline,
    export_galaxy,
    export_universe,
)


def _sample_catalogue() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pl_name": ["Test b", "Test c", "No Distance d", "Control"],
            "hostname": ["Test", "Test", "No Distance", "Sun"],
            "ra": [10.0, 200.0, 50.0, 0.0],
            "dec": [20.0, -30.0, 5.0, 0.0],
            "sy_dist": [12.5, 340.0, np.nan, 0.0],
            "earth2_index": [0.5, 0.2, 0.1, 1.0],
            "discoverymethod": ["Transit", "Radial Velocity", "Imaging", "Radial Velocity"],
            "disc_year": [2020, 2015, 2019, 1995],
            "is_control": [False, False, False, True],
        }
    )


def test_export_galaxy_excludes_rows_without_distance_and_controls():
    g = export_galaxy(_sample_catalogue())
    # Control row and the row with no sy_dist are both excluded: 4 rows in,
    # 1 control dropped up front, 1 more excluded for missing distance.
    assert g["n_points"] == 2
    assert g["n_excluded_no_distance"] == 1
    assert set(g["name"]) == {"Test b", "Test c"}


def test_export_galaxy_sun_position_matches_cited_constants():
    g = export_galaxy(_sample_catalogue())
    assert g["sun_x_kpc"] == pytest.approx(-GALCEN_DISTANCE_KPC)
    assert g["sun_y_kpc"] == pytest.approx(0.0)
    assert g["sun_z_kpc"] == pytest.approx(SUN_HEIGHT_PC / 1000.0)


def test_export_galaxy_positions_are_self_consistent_with_distance_from_sun():
    """The galactocentric x/y/z must reconstruct each system's real distance
    from the Sun (not from the Galactic Centre) to within rounding precision --
    this is what actually catches a sign or axis-order mistake in the
    transform, not just "did it run"."""
    g = export_galaxy(_sample_catalogue())
    for i, expected_pc in enumerate(g["dist_pc"]):
        dx = g["x_kpc"][i] - g["sun_x_kpc"]
        dy = g["y_kpc"][i] - g["sun_y_kpc"]
        dz = g["z_kpc"][i] - g["sun_z_kpc"]
        recomputed_pc = math.sqrt(dx * dx + dy * dy + dz * dz) * 1000.0
        assert recomputed_pc == pytest.approx(expected_pc, abs=0.5)


def test_export_galaxy_method_shells_are_real_catalogue_maxima():
    g = export_galaxy(_sample_catalogue())
    # Test b (Transit, 12.5 pc) and Test c (Radial Velocity, 340.0 pc) survive
    # the distance filter; Imaging's only row (No Distance d) does not, so it
    # must not appear as a shell at all -- a fabricated zero would be worse
    # than an absent key.
    assert g["method_shells_pc"] == {"Transit": 12.5, "Radial Velocity": 340.0}
    assert "Imaging" not in g["method_shells_pc"]


def test_export_galaxy_bulge_direction_uses_raw_ra_dec_not_the_xyz_transform():
    """A row placed exactly at the Galactic Centre's own sky position must
    read as 100% "toward the bulge"; a row on the opposite side of the sky
    must read as 0% -- this exercises the angular-separation formula itself,
    not just that the key exists with some plausible-looking value."""
    df = pd.DataFrame(
        {
            "pl_name": ["At GC", "Opposite GC"],
            "hostname": ["h1", "h2"],
            "ra": [GALACTIC_CENTRE_RA_DEG, (GALACTIC_CENTRE_RA_DEG + 180) % 360],
            "dec": [GALACTIC_CENTRE_DEC_DEG, -GALACTIC_CENTRE_DEC_DEG],
            "sy_dist": [1000.0, 1000.0],
            "earth2_index": [0.1, 0.1],
            "discoverymethod": ["Microlensing", "Microlensing"],
            "disc_year": [2020, 2020],
        }
    )
    g = export_galaxy(df)
    assert g["pct_within_10deg_of_galactic_centre_by_method"]["Microlensing"] == pytest.approx(50.0)


def test_export_universe_passes_through_real_gaia_ruwe_without_fabricating_missing_values():
    df = _sample_catalogue()
    df["gaia_ruwe"] = [1.02, 1.87, np.nan, 1.0]
    u = export_universe(df)
    # Test b and Test c survive the distance filter (Control and No Distance d
    # don't); their real RUWE values must come through untouched, in the same
    # row order as "name".
    assert u["name"] == ["Test b", "Test c"]
    assert u["gaia_ruwe"] == [1.02, 1.87]


def test_export_universe_reports_missing_ruwe_as_null_not_a_fabricated_default():
    """A system this project never cross-matched against Gaia (or that Gaia
    doesn't have a RUWE for) must read as null, not as 1.0 or any other
    value that would silently read as 'astrometry looks fine'."""
    df = _sample_catalogue()
    df["gaia_ruwe"] = [np.nan, 1.1, np.nan, 1.0]
    u = export_universe(df)
    assert u["gaia_ruwe"][0] is None


def test_export_universe_still_matches_export_galaxy_distance_filter():
    """Both exports apply the identical ok-mask (ra, dec, dist all present,
    dist > 0, controls dropped); they must agree on how many systems survive."""
    df = _sample_catalogue()
    assert export_universe(df)["n_points"] == export_galaxy(df)["n_points"]
    assert export_universe(df)["n_excluded_no_distance"] == export_galaxy(df)["n_excluded_no_distance"]


def test_export_universe_galactic_lb_matches_direct_astropy_transform():
    """gal_l_deg/gal_b_deg must match a from-scratch astropy transform of the
    same raw ra/dec -- this is an independent recomputation, not a re-check of
    webexport's own internal call, so it would catch a wrong frame or a
    swapped l/b."""
    df = _sample_catalogue()
    result = export_universe(df)
    expected = SkyCoord(
        ra=[10.0, 200.0] * u_.deg, dec=[20.0, -30.0] * u_.deg, frame="icrs"
    ).galactic
    assert result["name"] == ["Test b", "Test c"]
    for got_l, got_b, exp_l, exp_b in zip(
        result["gal_l_deg"], result["gal_b_deg"], expected.l.deg, expected.b.deg
    ):
        assert got_l == pytest.approx(exp_l, abs=1e-2)
        assert got_b == pytest.approx(exp_b, abs=1e-2)


def test_export_universe_galactic_centre_reads_as_zero_zero():
    """A row placed exactly at Sagittarius A*'s own sky position must read as
    (l, b) approx (0, 0) by definition of the Galactic coordinate system --
    a real sanity check on the transform, not just "some number came out"."""
    df = pd.DataFrame(
        {
            "pl_name": ["At GC"],
            "hostname": ["h1"],
            "ra": [GALACTIC_CENTRE_RA_DEG],
            "dec": [GALACTIC_CENTRE_DEC_DEG],
            "sy_dist": [1000.0],
            "earth2_index": [0.1],
            "discoverymethod": ["Microlensing"],
            "disc_year": [2020],
        }
    )
    result = export_universe(df)
    l_wrapped = (result["gal_l_deg"][0] + 180) % 360 - 180
    assert l_wrapped == pytest.approx(0.0, abs=0.1)
    assert result["gal_b_deg"][0] == pytest.approx(0.0, abs=0.1)


def test_export_discovery_timeline_years_span_min_to_max_surviving_discovery_year():
    """Test b (Transit, 2020) and Test c (Radial Velocity, 2015) survive the
    shared distance filter; the timeline must span exactly 2015-2020, not the
    excluded rows' years (1995 control, 2019 no-distance)."""
    t = export_discovery_timeline(_sample_catalogue())
    assert t["years"] == list(range(2015, 2021))


def test_export_discovery_timeline_counts_are_cumulative_not_per_year():
    """Radial Velocity's one surviving system (Test c) was discovered in
    2015, so its cumulative count must already be 1 at 2015 and stay 1 at
    2020 -- a per-year-only (non-cumulative) implementation would instead
    show 1 at 2015 and 0 at 2020."""
    t = export_discovery_timeline(_sample_catalogue())
    rv_counts = t["method_share_counts_by_year"]["Radial Velocity"]
    assert rv_counts[t["years"].index(2015)] == 1
    assert rv_counts[t["years"].index(2020)] == 1
    transit_counts = t["method_share_counts_by_year"]["Transit"]
    assert transit_counts[t["years"].index(2019)] == 0
    assert transit_counts[t["years"].index(2020)] == 1
    assert t["total_count_by_year"] == [1, 1, 1, 1, 1, 2]


def test_export_discovery_timeline_method_with_no_detections_yet_is_null_not_zero():
    """Transit's only surviving system is discovered in 2020, so its distance
    quantiles at 2015-2019 must be null (nothing detected yet by that method),
    never a fabricated 0 pc."""
    t = export_discovery_timeline(_sample_catalogue())
    transit_median = t["distance_quantiles_pc_by_year"]["Transit"]["median_pc"]
    assert transit_median[t["years"].index(2019)] is None
    assert transit_median[t["years"].index(2020)] == pytest.approx(12.5)


def test_export_discovery_timeline_final_year_matches_export_universe_total():
    """At the last year, the cumulative total must equal export_universe's
    full n_points -- both derive from the identical row filter."""
    df = _sample_catalogue()
    t = export_discovery_timeline(df)
    u = export_universe(df)
    assert t["total_count_by_year"][-1] == u["n_points"]
