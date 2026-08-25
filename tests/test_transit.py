"""Transit light-curve analysis tests.

Targets the behaviours the module's own docstring calls out as easy to get
wrong silently: mission time-system conversion (folding on the wrong epoch
still returns *a* phase, just a meaningless one), the asymmetric outlier clip
(a symmetric clip would remove the transit signal itself), and depth/period
recovery on synthetic data with a known answer.
"""

from __future__ import annotations

import numpy as np
import pytest

from earth2.transit.lightcurve import (
    bjd_to_mission_time,
    bls_period_search,
    clip_upward_outliers,
    detrend,
    fit_trapezoid,
    fold_on_ephemeris,
)


def test_bjd_to_mission_time_converts_tess_epoch():
    bjd = 2457322.5  # a plausible full-BJD transit epoch
    out = bjd_to_mission_time(bjd, "TESS")
    assert out == pytest.approx(bjd - 2457000.0)


def test_bjd_to_mission_time_converts_kepler_epoch():
    bjd = 2455000.0
    out = bjd_to_mission_time(bjd, "Kepler")
    assert out == pytest.approx(bjd - 2454833.0)


def test_bjd_to_mission_time_passes_through_already_converted_epoch():
    """A value already small enough to be an offset time (below 100000) must
    not be shifted a second time."""
    assert bjd_to_mission_time(1234.5, "TESS") == pytest.approx(1234.5)


def test_bjd_to_mission_time_passes_through_unknown_mission():
    bjd = 2457322.5
    assert bjd_to_mission_time(bjd, "SomeOtherMission") == pytest.approx(bjd)


def test_bjd_to_mission_time_handles_missing_input():
    assert np.isnan(bjd_to_mission_time(float("nan"), "TESS"))
    assert np.isnan(bjd_to_mission_time(None, "TESS"))  # type: ignore[arg-type]


def test_clip_upward_outliers_keeps_transit_shaped_downward_excursions():
    """A symmetric sigma-clip would remove a transit -- this asymmetry is the
    entire point of the function, so it must be pinned down directly."""
    flux = np.ones(200)
    rng = np.random.default_rng(0)
    flux += rng.normal(0, 0.001, 200)
    flux[50] += 0.02   # upward: a flare / cosmic ray
    flux[100] -= 0.02  # downward: a transit-like dip

    keep = clip_upward_outliers(flux, sigma=4.0)
    assert keep[50] == False  # noqa: E712 -- flare must be clipped
    assert keep[100] == True  # noqa: E712 -- transit-like dip must survive


def test_detrend_returns_input_unchanged_for_too_few_points():
    time = np.linspace(0, 1, 5)
    flux = np.ones(5)
    out = detrend(time, flux)
    assert np.array_equal(out, flux)


def test_detrend_removes_slow_trend_but_preserves_short_dip():
    rng = np.random.default_rng(1)
    time = np.linspace(0, 10, 2000)
    slow_trend = 1.0 + 0.05 * np.sin(2 * np.pi * time / 10.0)  # much slower than the transit
    flux = slow_trend.copy()
    dip = (time > 5.0) & (time < 5.05)  # ~1.2 hour dip
    flux[dip] -= 0.01
    flux += rng.normal(0, 0.0005, len(time))

    out = detrend(time, flux, transit_duration_hours=1.2)
    # After detrending, in-dip flux should sit visibly below the surrounding
    # out-of-dip median -- i.e. the transit signal must still be there.
    out_of_dip_median = np.nanmedian(out[~dip])
    in_dip_median = np.nanmedian(out[dip])
    assert in_dip_median < out_of_dip_median - 0.005


def test_fold_on_ephemeris_returns_empty_for_invalid_period():
    time = np.linspace(0, 10, 50)
    flux = np.ones(50)
    phase, folded = fold_on_ephemeris(time, flux, period_days=0.0, t0=0.0)
    assert len(phase) == 0
    assert len(folded) == 0


def test_fold_on_ephemeris_wraps_phase_around_zero():
    period = 5.0
    time = np.array([0.0, 2.5, 5.0, 7.5, 10.0])
    flux = np.arange(5, dtype=float)
    phase, _ = fold_on_ephemeris(time, flux, period_days=period, t0=0.0)
    assert np.all(phase >= -period / 2.0 - 1e-9)
    assert np.all(phase <= period / 2.0 + 1e-9)


def _synthetic_transit(depth=0.01, duration_hours=3.0, n=400, noise=0.0003, seed=0):
    rng = np.random.default_rng(seed)
    window_days = 0.6
    phase = np.linspace(-window_days, window_days, n)
    dur_days = duration_hours / 24.0
    flux = np.ones(n)
    in_transit = np.abs(phase) < dur_days / 2.0
    flux[in_transit] -= depth
    flux += rng.normal(0, noise, n)
    return phase, flux


def test_fit_trapezoid_recovers_known_depth_and_duration():
    phase, flux = _synthetic_transit(depth=0.01, duration_hours=3.0, noise=0.0002)
    fit = fit_trapezoid(phase, flux, duration_guess_hours=3.0)
    assert fit is not None
    assert fit.depth_ppm == pytest.approx(10000.0, rel=0.15)
    assert fit.duration_hours == pytest.approx(3.0, rel=0.25)
    assert fit.significant is True


def test_fit_trapezoid_returns_none_for_too_few_points():
    phase = np.linspace(-0.1, 0.1, 10)
    flux = np.ones(10)
    assert fit_trapezoid(phase, flux) is None


def test_fit_trapezoid_marks_noise_only_data_as_not_significant():
    rng = np.random.default_rng(5)
    phase = np.linspace(-0.6, 0.6, 400)
    flux = 1.0 + rng.normal(0, 0.01, 400)  # no transit at all, just noise
    fit = fit_trapezoid(phase, flux, duration_guess_hours=3.0)
    if fit is not None:
        assert fit.significant is False or fit.depth_ppm < 3000.0


def test_bls_period_search_rejects_too_few_cadences():
    time = np.linspace(0, 5, 50)
    flux = np.ones(50)
    out = bls_period_search(time, flux)
    assert out["ok"] is False
    assert "fewer than 100" in out["reason"]


def test_bls_period_search_recovers_injected_period():
    rng = np.random.default_rng(20260824)
    true_period = 4.2
    time = np.sort(rng.uniform(0, 60, 3000))
    flux = np.ones_like(time)
    phase = np.mod(time, true_period)
    dur = 0.08  # days
    in_transit = phase < dur
    flux[in_transit] -= 0.012
    flux += rng.normal(0, 0.0008, len(time))

    out = bls_period_search(time, flux, min_period=1.0, max_period=10.0, n_periods=8000)
    assert out["ok"] is True
    assert out["best_period_days"] == pytest.approx(true_period, rel=0.02)
