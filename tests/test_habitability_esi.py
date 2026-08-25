"""Earth Similarity Index tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from earth2.constants import SOLAR_SYSTEM_CONTROLS
from earth2.habitability import esi


def test_earth_scores_exactly_one():
    df = pd.DataFrame([{
        "pl_rade": 1.0, "pl_bmasse": 1.0, "pl_dens": 5.514,
        "pl_eqt": esi.T_EQ_EARTH_REFERENCE_K,
    }])
    out = esi.esi_frame(df)
    assert abs(float(out["esi_global"].iloc[0]) - 1.0) < 1e-9


def test_venus_scores_above_point_nine():
    """Documented consequence of using equilibrium temperature: Venus reads
    as near-Earth-similar. This is the whole point of the module's warning."""
    v = SOLAR_SYSTEM_CONTROLS["Venus"]
    df = pd.DataFrame([{
        "pl_rade": v["pl_rade"], "pl_bmasse": v["pl_bmasse"],
        "pl_dens": v["pl_dens"], "pl_eqt": v["pl_eqt"],
    }])
    out = esi.esi_frame(df)
    assert float(out["esi_global"].iloc[0]) > 0.9


def test_jupiter_scores_far_below_earth():
    j = SOLAR_SYSTEM_CONTROLS["Jupiter"]
    df = pd.DataFrame([{
        "pl_rade": j["pl_rade"], "pl_bmasse": j["pl_bmasse"],
        "pl_dens": j["pl_dens"], "pl_eqt": j["pl_eqt"],
    }])
    out = esi.esi_frame(df)
    assert float(out["esi_global"].iloc[0]) < 0.6


def test_missing_mass_yields_nan_not_earth_default():
    """A missing mass must never silently become Earth's mass."""
    df = pd.DataFrame([{"pl_rade": 1.0, "pl_bmasse": np.nan, "pl_dens": np.nan, "pl_eqt": 255.0}])
    out = esi.esi_frame(df)
    assert np.isnan(float(out["esi_global"].iloc[0]))


def test_missing_radius_yields_nan():
    df = pd.DataFrame([{"pl_rade": np.nan, "pl_bmasse": 1.0, "pl_dens": np.nan, "pl_eqt": 255.0}])
    out = esi.esi_frame(df)
    assert np.isnan(float(out["esi_global"].iloc[0]))


def test_non_positive_inputs_are_rejected():
    assert np.isnan(float(esi.esi_component(-1.0, 1.0, 0.5, 1)))
    assert np.isnan(float(esi.esi_component(0.0, 1.0, 0.5, 1)))


def test_bulk_density_earth_formula():
    # Same mass and radius as Earth -> Earth's density.
    rho = esi.bulk_density_earth_units(1.0, 1.0)
    assert abs(float(rho) - 5.514) < 1e-6


def test_escape_velocity_earth_formula():
    v = esi.escape_velocity_earth_units(1.0, 1.0)
    assert abs(float(v) - 11.186) < 1e-6


def test_esi_bounded_zero_to_one_for_extreme_inputs():
    df = pd.DataFrame([{"pl_rade": 20.0, "pl_bmasse": 5000.0, "pl_dens": 20.0, "pl_eqt": 3000.0}])
    out = esi.esi_frame(df)
    v = float(out["esi_global"].iloc[0])
    assert 0.0 <= v <= 1.0


def _independent_reference_esi(radius, density, vesc, teq) -> float:
    """Flat four-variable ESI, coded independently of esi_global's tier
    structure, as a numerical cross-check that the hierarchical two-tier
    computation reduces to the published formula.

    Schulze-Makuch et al. (2011): ESI = prod_i (1 - |(x_i - x0_i)/(x_i + x0_i)|)^(w_i / 4),
    with n = 4 because there are four properties total -- NOT because there
    happen to be two tiers of two. The two-tier computation in esi_global is a
    reporting convenience (it exposes ESI_interior/ESI_surface separately) and
    must collapse to exactly this when multiplied out. A regression here would
    have caught the exponent bug fixed in this module (w_i/8 instead of w_i/4,
    from an extra sqrt taken when combining each tier) that the two coarser
    bound-only tests above (Venus > 0.9, Jupiter < 0.6) were too loose to catch.
    """
    refs = esi.ESI_REFERENCES
    weights = esi.ESI_WEIGHTS
    total = 1.0
    for value, key in (
        (radius, "radius"), (density, "density"),
        (vesc, "escape_velocity"), (teq, "temperature"),
    ):
        frac = abs((value - refs[key]) / (value + refs[key]))
        total *= (1.0 - frac) ** (weights[key] / 4.0)
    return total


def test_esi_global_matches_independent_flat_formula_for_venus():
    v = SOLAR_SYSTEM_CONTROLS["Venus"]
    vesc = float(esi.escape_velocity_earth_units(v["pl_bmasse"], v["pl_rade"]))
    expected = _independent_reference_esi(v["pl_rade"], v["pl_dens"], vesc, v["pl_eqt"])
    actual = float(esi.esi_frame(pd.DataFrame([{
        "pl_rade": v["pl_rade"], "pl_bmasse": v["pl_bmasse"],
        "pl_dens": v["pl_dens"], "pl_eqt": v["pl_eqt"],
    }]))["esi_global"].iloc[0])
    assert abs(actual - expected) < 1e-9
    # Pinned value so a silent regression in either implementation is caught
    # even if both happened to agree with each other but not with the paper.
    assert abs(actual - 0.9199035164025666) < 1e-9


def test_esi_global_matches_independent_flat_formula_for_random_planets():
    rng = np.random.default_rng(20260824)
    for _ in range(200):
        radius = rng.uniform(0.3, 4.0)
        mass = rng.uniform(0.05, 20.0)
        teq = rng.uniform(150.0, 500.0)
        density = float(esi.bulk_density_earth_units(mass, radius))
        vesc = float(esi.escape_velocity_earth_units(mass, radius))
        expected = _independent_reference_esi(radius, density, vesc, teq)
        actual = float(esi.esi_global(radius, density, vesc, teq)["esi_global"])
        assert abs(actual - expected) < 1e-9
