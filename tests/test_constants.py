"""Physical constants self-consistency."""

from __future__ import annotations

from earth2 import constants as c


def test_earth_equilibrium_temperature_matches_stated_constant():
    """T_eq(albedo=0.306) must equal the T_EQ_EARTH_K constant to <1 K."""
    assert abs(c.earth_equilibrium_temperature() - c.T_EQ_EARTH_K) < 1.0


def test_jupiter_radius_ratio():
    assert abs(c.R_JUP_IN_R_EARTH - 11.209) < 0.01


def test_jupiter_mass_ratio():
    assert abs(c.M_JUP_IN_M_EARTH - 317.8) < 0.5


def test_earth_mass_kg():
    assert abs(c.M_EARTH_KG - 5.9722e24) / 5.9722e24 < 1e-3


def test_solar_system_controls_have_all_required_fields():
    required = {"pl_rade", "pl_bmasse", "pl_dens", "pl_orbsmax", "pl_orbper",
                "pl_eqt", "pl_insol", "st_teff"}
    for name, body in c.SOLAR_SYSTEM_CONTROLS.items():
        missing = required - set(body)
        assert not missing, f"{name} missing fields: {missing}"


def test_solar_system_controls_physically_ordered_by_distance():
    """Insolation must decrease monotonically with semi-major axis (fixed L)."""
    order = ["Mercury", "Venus", "Earth", "Mars", "Jupiter"]
    smax = [c.SOLAR_SYSTEM_CONTROLS[n]["pl_orbsmax"] for n in order]
    insol = [c.SOLAR_SYSTEM_CONTROLS[n]["pl_insol"] for n in order]
    assert smax == sorted(smax)
    assert insol == sorted(insol, reverse=True)


def test_self_check_passes():
    c._self_check()
