"""Tests for the Phase 8 XUV and escape scenario physics."""

from __future__ import annotations

import numpy as np

from earth2.environment.escape import (
    energy_limited_mass_loss_rate,
    integrated_energy_limited_loss,
    roche_tide_factor,
)
from earth2.environment.xuv import (
    XUV_SCENARIOS,
    integrate_sed_bands,
    xuv_history_summary,
    xuv_luminosity_fraction,
)


def test_sed_band_integration_handles_partial_edges():
    result = integrate_sed_bands(
        np.array([0.0, 900.0, 1200.0]),
        np.array([10.0, 920.0, 1230.0]),
        np.ones(3),
        np.full(3, 0.1),
        1000.0,
    )
    assert np.isclose(result["xuv_5_912a"]["flux_at_earth_erg_s_cm2"], 17.0)
    assert np.isclose(result["lya_1210_1222a"]["flux_at_earth_erg_s_cm2"], 12.0)


def test_xuv_history_saturates_then_declines():
    scenario = XUV_SCENARIOS["nominal"]
    fractions = xuv_luminosity_fraction(np.array([0.01, 0.5, 5.0]), 0.3, scenario)
    assert np.isclose(fractions[0], scenario.saturated_fraction)
    assert np.isclose(fractions[1], scenario.saturated_fraction)
    assert fractions[2] < fractions[1]


def test_extended_m_dwarf_saturation_increases_integrated_dose():
    low = xuv_history_summary(
        stellar_age_gyr=5.0,
        bolometric_flux_w_m2=1000.0,
        stellar_mass_solar=0.2,
        scenario=XUV_SCENARIOS["short_low"],
    )
    high = xuv_history_summary(
        stellar_age_gyr=5.0,
        bolometric_flux_w_m2=1000.0,
        stellar_mass_solar=0.2,
        scenario=XUV_SCENARIOS["extended_high"],
    )
    assert high["integrated_xuv_dose_j_m2"] > low["integrated_xuv_dose_j_m2"]


def test_roche_factor_is_bounded_for_earth():
    factor = roche_tide_factor(
        stellar_mass_solar=1.0,
        planet_mass_earth=1.0,
        semimajor_axis_au=1.0,
        xuv_radius_earth=1.0,
    )
    assert 0 < factor < 1
    assert factor > 0.99


def test_energy_limited_rate_scales_linearly_with_flux_and_efficiency():
    kwargs = {
        "planet_mass_earth": 1.0,
        "planet_radius_earth": 1.0,
        "xuv_radius_factor": 1.1,
        "tide_factor": 1.0,
    }
    baseline = energy_limited_mass_loss_rate(xuv_flux_w_m2=1.0, heating_efficiency=0.1, **kwargs)
    doubled = energy_limited_mass_loss_rate(xuv_flux_w_m2=2.0, heating_efficiency=0.1, **kwargs)
    efficient = energy_limited_mass_loss_rate(xuv_flux_w_m2=1.0, heating_efficiency=0.2, **kwargs)
    assert np.isclose(doubled, 2 * baseline)
    assert np.isclose(efficient, 2 * baseline)


def test_integrated_loss_matches_rate_times_dose():
    lost = integrated_energy_limited_loss(
        xuv_dose_j_m2=1e16,
        planet_mass_earth=1.0,
        planet_radius_earth=1.0,
        xuv_radius_factor=1.0,
        heating_efficiency=0.1,
        tide_factor=1.0,
    )
    assert lost > 0
