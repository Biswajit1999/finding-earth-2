"""Scientific contracts for time-dependent habitable-zone inference."""

from __future__ import annotations

import numpy as np
import pandas as pd

from earth2.climate.evolution import (
    CLIMATE_PRESCRIPTIONS,
    EvolutionConfig,
    MISTMainSequenceGrid,
    infer_continuous_hz,
)


def _grid() -> MISTMainSequenceGrid:
    rows = []
    for feh in (-0.5, 0.0, 0.5):
        for log_age in (8.0, 9.0, 10.0):
            for mass in (0.5, 1.0, 1.5):
                age_gyr = 10**log_age / 1e9
                rows.append(
                    {
                        "feh": feh,
                        "log10_age_years": log_age,
                        "initial_mass_solar": mass,
                        "log10_luminosity_solar": np.log10(mass**3.5 * (0.7 + 0.06 * age_gyr)),
                        "log10_teff_kelvin": np.log10(5780 * mass**0.4),
                    }
                )
    return MISTMainSequenceGrid(pd.DataFrame(rows))


def _earthlike(**overrides):
    values = {
        "age_gyr": 4.6,
        "age_error_minus": 0.2,
        "age_error_plus": 0.2,
        "mass_solar": 1.0,
        "mass_error_minus": 0.01,
        "mass_error_plus": 0.01,
        "feh": 0.0,
        "feh_error_minus": 0.02,
        "feh_error_plus": 0.02,
        "log_luminosity_solar": 0.0,
        "log_luminosity_error_minus": 0.01,
        "log_luminosity_error_plus": 0.01,
        "semimajor_axis_au": 1.0,
        "semimajor_axis_error_minus": 0.001,
        "semimajor_axis_error_plus": 0.001,
        "seed": 42,
        "config": EvolutionConfig(draws=96, history_steps=32),
    }
    values.update(overrides)
    return values


def test_grid_recovers_exact_node():
    grid = _grid()
    luminosity, temperature = grid.interpolate(age_gyr=1.0, mass_solar=1.0, feh=0.0)
    assert np.isclose(float(luminosity), np.log10(0.76))
    assert np.isclose(10 ** float(temperature), 5780)


def test_inference_is_deterministic_and_anchors_present_luminosity():
    grid = _grid()
    first = infer_continuous_hz(grid, **_earthlike())
    second = infer_continuous_hz(grid, **_earthlike())
    assert first == second
    assert first["status"] == "inferred"
    assert first["luminosity_anchor_max_abs_dex"] < 1e-12


def test_nested_climate_prescriptions_have_expected_probabilities():
    result = infer_continuous_hz(_grid(), **_earthlike())
    models = result["climate_prescriptions"]
    assert set(models) == set(CLIMATE_PRESCRIPTIONS)
    optimistic = models["kopparapu_optimistic_empirical"]["p_current_hz"]
    conservative = models["kopparapu_conservative"]["p_current_hz"]
    moist = models["kopparapu_moist_greenhouse"]["p_current_hz"]
    assert optimistic >= conservative >= moist
    assert 0 <= result["boundary_sensitivity"] <= 1


def test_broad_stellar_age_is_undetermined():
    result = infer_continuous_hz(
        _grid(),
        **_earthlike(age_error_minus=4.0, age_error_plus=4.0),
    )
    assert result["status"] == "undetermined"
    assert result["reason"] == "stellar_age_effectively_unconstrained"


def test_out_of_grid_stellar_mass_is_undetermined():
    result = infer_continuous_hz(
        _grid(),
        **_earthlike(mass_solar=0.2, mass_error_minus=0.01, mass_error_plus=0.01),
    )
    assert result["status"] == "undetermined"
    assert result["reason"] == "insufficient_mist_main_sequence_support"
