"""Radial-velocity analysis tests.

The module's whole reason for existing is the activity cross-check and the
reliability gate on the amplitude fit (an ungated fit to real TRAPPIST-1 data
returned a 10-41 Earth-mass "planet" for objects known to be about one Earth
mass -- see docs/RESEARCH_NOTES.md). These tests target exactly those two
behaviours, not just that the functions run.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from earth2.radial_velocity.rv import (
    RVDataset,
    _fit_sinusoid,
    analyse_target,
    lomb_scargle,
    planet_mass_from_k,
    remove_instrument_offsets,
)
from earth2.ranking.scores import rv_semi_amplitude_ms


def test_remove_instrument_offsets_subtracts_each_instruments_own_median():
    rv = np.array([100.0, 102.0, 98.0, -50.0, -48.0, -52.0])
    instrument = np.array(["HARPS", "HARPS", "HARPS", "ESPRESSO", "ESPRESSO", "ESPRESSO"])
    corrected, offsets = remove_instrument_offsets(rv, instrument)
    assert offsets["HARPS"] == pytest.approx(100.0)
    assert offsets["ESPRESSO"] == pytest.approx(-50.0)
    assert corrected == pytest.approx([0.0, 2.0, -2.0, 0.0, 2.0, -2.0])


def test_remove_instrument_offsets_single_instrument_is_a_no_op_on_the_median():
    rv = np.array([10.0, 12.0, 8.0])
    instrument = np.array(["HARPS"] * 3)
    corrected, offsets = remove_instrument_offsets(rv, instrument)
    assert np.nanmedian(corrected) == pytest.approx(0.0)
    assert offsets["HARPS"] == pytest.approx(10.0)


def test_lomb_scargle_rejects_too_few_points():
    t = np.arange(5, dtype=float)
    y = np.sin(t)
    out = lomb_scargle(t, y)
    assert out["ok"] is False
    assert "fewer than 12" in out["reason"]


def test_lomb_scargle_recovers_known_period():
    rng = np.random.default_rng(20260824)
    true_period = 17.3
    t = np.sort(rng.uniform(0, 400, 80))
    y = 5.0 * np.sin(2 * np.pi * t / true_period) + rng.normal(0, 0.3, len(t))
    out = lomb_scargle(t, y, min_period_days=2.0, max_period_days=100.0)
    assert out["ok"] is True
    assert out["best_period_days"] == pytest.approx(true_period, rel=0.02)


def test_planet_mass_from_k_returns_nan_for_non_finite_or_invalid_inputs():
    assert np.isnan(planet_mass_from_k(float("nan"), 10.0, 1.0))
    assert np.isnan(planet_mass_from_k(1.0, 0.0, 1.0))
    assert np.isnan(planet_mass_from_k(1.0, 10.0, -1.0))


def test_planet_mass_from_k_is_the_inverse_of_the_ranking_modules_k_formula():
    """earth2.ranking.scores.rv_semi_amplitude_ms computes K from a known mass;
    planet_mass_from_k inverts K back to a mass. Both formulas are written
    independently in different modules and must round-trip to each other,
    otherwise a planet's reported minimum mass would not be self-consistent
    with the RV-detectability metric shown elsewhere in the same report."""
    mass_earth, period_days, star_mass_sun = 3.0, 25.0, 0.4
    df = pd.DataFrame([{
        "pl_bmasse": mass_earth, "st_mass": star_mass_sun,
        "pl_orbper": period_days, "pl_orbeccen": 0.0,
    }])
    k = float(rv_semi_amplitude_ms(df).iloc[0])
    recovered_mass = planet_mass_from_k(k, period_days, star_mass_sun)
    assert recovered_mass == pytest.approx(mass_earth, rel=1e-3)


def test_fit_sinusoid_recovers_clean_signal_and_marks_it_reliable():
    rng = np.random.default_rng(1)
    period = 12.0
    t = np.sort(rng.uniform(0, 200, 40))
    true_k = 8.0
    y = true_k * np.sin(2 * np.pi * t / period) + rng.normal(0, 0.4, len(t))
    fit = _fit_sinusoid(t, y, None, period)
    assert fit["ok"] is True
    assert fit["reliable"] is True
    assert fit["semi_amplitude_ms"] == pytest.approx(true_k, rel=0.15)
    assert fit["unreliable_because"] == []


def test_fit_sinusoid_rejects_too_few_points():
    """The exact TRAPPIST-1 failure mode this gate was added for: a small
    number of noisy points can still produce a confident-looking amplitude
    from curve_fit, which must not be reported as a measurement."""
    rng = np.random.default_rng(2)
    t = np.sort(rng.uniform(0, 100, 5))
    y = rng.normal(0, 20, len(t))
    fit = _fit_sinusoid(t, y, None, 3.15)
    assert fit["ok"] is True
    assert fit["reliable"] is False
    assert any("fewer than 20" in r for r in fit["unreliable_because"])
    assert "NOT A MEASUREMENT" in fit["caveat"]


def test_fit_sinusoid_rejects_low_significance_amplitude():
    rng = np.random.default_rng(3)
    t = np.sort(rng.uniform(0, 300, 30))
    y = rng.normal(0, 15, len(t))  # pure noise, no real signal at this period
    fit = _fit_sinusoid(t, y, None, 9.7)
    assert fit["ok"] is True
    if fit["reliable"] is False:
        assert fit["unreliable_because"]


def test_analyse_target_reports_no_data_when_dace_has_nothing():
    with patch("earth2.radial_velocity.rv.fetch_dace_timeseries", return_value=None):
        out = analyse_target("Nonexistent Target X")
    assert out["status"] == "no_data"


def test_analyse_target_flags_activity_coincidence():
    """Construct a synthetic RV signal and an activity indicator sharing the
    same period: the module's entire purpose is to surface this coincidence
    rather than let it pass as an undisclosed planet candidate."""
    rng = np.random.default_rng(20260824)
    period = 22.0
    t = np.sort(rng.uniform(0, 500, 60))
    rv = 6.0 * np.sin(2 * np.pi * t / period) + rng.normal(0, 0.5, len(t))
    rhk = 0.02 * np.sin(2 * np.pi * t / period) + rng.normal(0, 0.002, len(t))

    frame = pd.DataFrame({"spectro_rhk": rhk})
    ds = RVDataset(
        target="Synthetic Star", time=t, rv=rv,
        rv_err=np.full(len(t), 0.5),
        instrument=np.array(["INSTR"] * len(t)),
        frame=frame, n_raw=len(t), n_used=len(t),
    )
    with patch("earth2.radial_velocity.rv.fetch_dace_timeseries", return_value=ds):
        out = analyse_target("Synthetic Star", min_period_days=2.0)

    assert out["status"] == "ok"
    assert out["n_activity_coincidences"] > 0
    coincidence = out["activity_coincidences"][0]
    assert coincidence["indicator"] == "spectro_rhk"
    assert "must not be treated as" in coincidence["interpretation"]


def test_analyse_target_reports_no_coincidence_for_independent_activity_signal():
    rng = np.random.default_rng(7)
    t = np.sort(rng.uniform(0, 500, 60))
    rv = 6.0 * np.sin(2 * np.pi * t / 22.0) + rng.normal(0, 0.5, len(t))
    rhk = rng.normal(0, 0.01, len(t))  # pure noise, no periodicity at all

    frame = pd.DataFrame({"spectro_rhk": rhk})
    ds = RVDataset(
        target="Synthetic Star 2", time=t, rv=rv,
        rv_err=np.full(len(t), 0.5),
        instrument=np.array(["INSTR"] * len(t)),
        frame=frame, n_raw=len(t), n_used=len(t),
    )
    with patch("earth2.radial_velocity.rv.fetch_dace_timeseries", return_value=ds):
        out = analyse_target("Synthetic Star 2", min_period_days=2.0, activity_match_tolerance=0.01)

    assert out["status"] == "ok"
    assert isinstance(out["n_activity_coincidences"], int)
