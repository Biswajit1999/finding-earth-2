"""Physical contracts for HWO direct-imaging scenarios."""

from __future__ import annotations

import numpy as np
import pytest

from earth2.missions.hwo.imaging import (
    CoronagraphScenario,
    deproject_minimum_mass,
    lambert_phase,
    observable_draws,
    orbital_geometry,
    solve_eccentric_anomaly,
)


def test_lambert_phase_has_expected_limits_and_quadrature():
    values = lambert_phase(np.array([0.0, np.pi / 2, np.pi]))
    assert values == pytest.approx([1.0, 1 / np.pi, 0.0], abs=1e-14)


def test_kepler_solver_satisfies_equation_for_eccentric_orbits():
    mean = np.linspace(0, 2 * np.pi, 20, endpoint=False)
    eccentricity = np.linspace(0, 0.8, 20)
    eccentric_anomaly = solve_eccentric_anomaly(mean, eccentricity)
    assert eccentric_anomaly - eccentricity * np.sin(eccentric_anomaly) == pytest.approx(
        mean, abs=1e-11
    )


def test_face_on_circular_orbit_has_constant_separation_and_quadrature_phase():
    mean = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    _, projected, phase = orbital_geometry(1.0, 0.0, 0.0, 0.0, mean)
    assert projected == pytest.approx(np.ones(24), abs=1e-12)
    assert phase == pytest.approx(np.full(24, np.pi / 2), abs=1e-12)


def test_analytic_iwa_and_tabulated_contrast_curve():
    analytic = CoronagraphScenario("six_metre", 6.0, 500.0, 3.0, 1e-10)
    assert analytic.iwa_mas == pytest.approx(51.5662, rel=1e-5)
    curve = CoronagraphScenario(
        "curve",
        6.0,
        500.0,
        3.0,
        1e-10,
        curve_separation_mas=(50.0, 100.0, 200.0),
        curve_contrast_limit=(1e-8, 1e-10, 1e-11),
    )
    limits = curve.contrast_limit_at(np.array([50.0, 75.0, 200.0]))
    assert limits == pytest.approx([1e-8, 1e-9, 1e-11])


def test_observability_applies_both_iwa_and_contrast():
    scenario = CoronagraphScenario("test", 6.0, 500.0, 3.0, 1e-10)
    result = observable_draws(
        scenario=scenario,
        distance_pc=np.array([10.0, 30.0]),
        semi_major_axis_au=np.ones(2),
        eccentricity=np.zeros(2),
        inclination_rad=np.zeros(2),
        argument_periapsis_rad=np.zeros(2),
        mean_anomaly_rad=np.zeros(2),
        planet_radius_earth=np.ones(2),
        geometric_albedo=np.full(2, 0.3),
    )
    assert result["projected_separation_mas"] == pytest.approx([100.0, 33.333333])
    assert result["contrast"][0] == pytest.approx(0.3 * (6.371e6 / 1.495978707e11) ** 2 / np.pi)
    assert result["accessible"].tolist() == [True, False]


def test_minimum_mass_deprojection_retains_inclination_dependence():
    values = deproject_minimum_mass(2.0, np.deg2rad(np.array([90.0, 30.0])))
    assert values == pytest.approx([2.0, 4.0])
