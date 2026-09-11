"""Scientific contracts for the probabilistic bulk-composition ensemble."""

from __future__ import annotations

import numpy as np
import pytest

from earth2.composition import (
    CompositionConfig,
    infer_bulk_composition,
    otegi_mass,
    zeng_rocky_radius,
)


def test_zeng_relation_reproduces_earth_like_scale_and_refuses_extrapolation():
    assert zeng_rocky_radius(1.0, 0.33) == pytest.approx(1.0007, rel=1e-4)
    assert np.isnan(zeng_rocky_radius(0.9, 0.33))
    assert np.isnan(zeng_rocky_radius(9.0, 0.33))


def test_otegi_relations_match_published_coefficients():
    assert otegi_mass(2.0, "rocky") == pytest.approx(0.9 * 2**3.45)
    assert otegi_mass(2.0, "volatile_rich") == pytest.approx(1.74 * 2**1.58)


def test_earth_bulk_data_are_consistent_with_the_terrestrial_family():
    result = infer_bulk_composition(
        radius_earth=1.0,
        mass_earth=1.0,
        independent_mass=True,
        config=CompositionConfig(draws=1000, seed=4),
    )
    assert result["p_requires_volatiles_zeng"] == 0.0
    assert result["p_consistent_with_terrestrial_composition_zeng"] == 1.0
    assert result["n_rocky_models_supported"] == 3


def test_low_density_planet_requires_volatiles_under_zeng_envelope():
    result = infer_bulk_composition(
        radius_earth=2.0,
        mass_earth=4.0,
        radius_error_minus=0.03,
        radius_error_plus=0.03,
        mass_error_minus=0.1,
        mass_error_plus=0.1,
        independent_mass=True,
        config=CompositionConfig(draws=2000, seed=9),
    )
    assert float(result["p_requires_volatiles_zeng"]) > 0.99
    assert float(result["p_rocky_zeng_fe_si_envelope"]) < 0.01


def test_radius_predicted_mass_never_becomes_independent_composition_evidence():
    result = infer_bulk_composition(
        radius_earth=1.2,
        mass_earth=2.7 * 1.2**1.3,
        independent_mass=False,
        config=CompositionConfig(draws=500, seed=3),
    )
    assert result["composition_evidence_scope"] == "radius_only_baseline"
    assert result["p_rocky_zeng_fe_si_envelope"] is None
    assert result["p_rocky_otegi_equal_prior"] is None
    assert result["wolfgang_prediction_is_dynamical_mass"] is False


def test_reported_mass_radius_correlation_changes_joint_sampling_result():
    independent = infer_bulk_composition(
        radius_earth=1.55,
        radius_error_minus=0.15,
        radius_error_plus=0.15,
        mass_earth=4.0,
        mass_error_minus=1.0,
        mass_error_plus=1.0,
        independent_mass=True,
        config=CompositionConfig(draws=8000, seed=12),
    )
    correlated = infer_bulk_composition(
        radius_earth=1.55,
        radius_error_minus=0.15,
        radius_error_plus=0.15,
        mass_earth=4.0,
        mass_error_minus=1.0,
        mass_error_plus=1.0,
        independent_mass=True,
        mass_radius_correlation=0.8,
        config=CompositionConfig(draws=8000, seed=12),
    )
    assert correlated["covariance_status"] == "reported_correlation_propagated"
    assert abs(
        float(independent["p_consistent_with_terrestrial_composition_zeng"])
        - float(correlated["p_consistent_with_terrestrial_composition_zeng"])
    ) > 0.02
