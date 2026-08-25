"""Habitable-zone model tests.

Regression values are the paper's own Table 3 outputs for the Sun
(Teff = 5780 K, L = 1 Lsun): Kopparapu et al. (2013), Section 3.1.
"""

from __future__ import annotations

import numpy as np
import pytest

from earth2.habitability import hz

SUN_TEFF = 5780.0


@pytest.mark.parametrize(
    "boundary,expected_au",
    [
        ("recent_venus", 0.75),
        ("runaway_greenhouse", 0.97),
        ("moist_greenhouse", 0.99),
        ("maximum_greenhouse", 1.70),
        ("early_mars", 1.77),
    ],
)
def test_sun_boundaries_match_paper(boundary, expected_au):
    d = hz.hz_distance_au(SUN_TEFF, 1.0, boundary, hz.COEFFS_ERRATUM_2013)
    assert abs(float(d) - expected_au) < 0.02


def test_erratum_differs_from_original_at_runaway_greenhouse():
    """The erratum must not silently equal the superseded original table."""
    s_orig = hz.seff_boundary(SUN_TEFF, "runaway_greenhouse", hz.COEFFS_ORIGINAL_2013)
    s_err = hz.seff_boundary(SUN_TEFF, "runaway_greenhouse", hz.COEFFS_ERRATUM_2013)
    assert abs(float(s_orig) - float(s_err)) > 1e-3


def test_earth_is_in_both_habitable_zones():
    assert float(hz.in_conservative_hz(1.0, SUN_TEFF)) == 1.0
    assert float(hz.in_optimistic_hz(1.0, SUN_TEFF)) == 1.0


def test_venus_is_outside_both_habitable_zones():
    # Venus insolation ~1.91 S_Earth
    assert float(hz.in_conservative_hz(1.911, SUN_TEFF)) == 0.0
    assert float(hz.in_optimistic_hz(1.911, SUN_TEFF)) == 0.0


def test_mars_is_inside_both_habitable_zones():
    assert float(hz.in_conservative_hz(0.431, SUN_TEFF)) == 1.0
    assert float(hz.in_optimistic_hz(0.431, SUN_TEFF)) == 1.0


def test_unknown_insolation_yields_nan_not_false():
    """Missing data must propagate as 'unknown', never as a silent 'no'."""
    result = hz.in_conservative_hz(np.nan, SUN_TEFF)
    assert np.isnan(float(result))


def test_validity_range_returns_nan_outside_bounds():
    assert np.isnan(float(hz.seff_boundary(2400.0, "runaway_greenhouse")))
    assert np.isnan(float(hz.seff_boundary(9000.0, "runaway_greenhouse")))


def test_validity_range_returns_finite_at_bounds():
    assert np.isfinite(float(hz.seff_boundary(hz.HZ_TEFF_MIN, "runaway_greenhouse")))
    assert np.isfinite(float(hz.seff_boundary(hz.HZ_TEFF_MAX, "runaway_greenhouse")))


def test_hz_membership_responds_to_stellar_luminosity():
    """A cooler/dimmer star must move the habitable zone inward in flux terms."""
    hot = hz.seff_boundary(6500.0, "runaway_greenhouse")
    cool = hz.seff_boundary(3200.0, "runaway_greenhouse")
    assert float(hot) != float(cool)


def test_hz_position_zero_at_inner_edge():
    inner = float(hz.seff_boundary(SUN_TEFF, "runaway_greenhouse"))
    pos = hz.hz_position(inner, SUN_TEFF)
    assert abs(float(pos)) < 1e-6


def test_hz_position_one_at_outer_edge():
    outer = float(hz.seff_boundary(SUN_TEFF, "maximum_greenhouse"))
    pos = hz.hz_position(outer, SUN_TEFF)
    assert abs(float(pos) - 1.0) < 1e-6


def test_array_input_vectorises():
    teff = np.array([5780.0, 5780.0, 5780.0])
    insol = np.array([1.0, 1.911, 0.1])
    result = hz.in_conservative_hz(insol, teff)
    np.testing.assert_array_equal(result, [1.0, 0.0, 0.0])
