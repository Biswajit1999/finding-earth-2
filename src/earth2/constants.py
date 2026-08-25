"""Physical constants and Earth reference values.

Every value here carries its source. Where the IAU has adopted a nominal value
(IAU 2015 Resolution B3) that nominal value is used, because the whole point of
the resolution is that derived quantities stay comparable between papers.

Nothing in this module is fitted, tuned, or chosen to make a result come out a
particular way.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Fundamental / astronomical constants
# --------------------------------------------------------------------------
# IAU 2015 Resolution B3 nominal conversion constants.
# https://www.iau.org/static/resolutions/IAU2015_English.pdf
L_SUN_W = 3.828e26          # nominal solar luminosity, W
R_SUN_M = 6.957e8           # nominal solar radius, m
GM_SUN = 1.3271244e20       # nominal solar mass parameter, m^3 s^-2
R_EARTH_EQ_M = 6.3781e6     # nominal Earth equatorial radius, m
R_EARTH_M = 6.371e6         # Earth volumetric mean radius, m (IAU/NASA fact sheet)
GM_EARTH = 3.986004e14      # nominal terrestrial mass parameter, m^3 s^-2
R_JUP_EQ_M = 7.1492e7       # nominal Jupiter equatorial radius, m

G_SI = 6.67430e-11          # CODATA 2018 gravitational constant, m^3 kg^-1 s^-2
SIGMA_SB = 5.670374419e-8   # CODATA 2018 Stefan-Boltzmann, W m^-2 K^-4
AU_M = 1.495978707e11       # IAU 2012 Resolution B2 astronomical unit, m
PC_M = 3.0856775814913673e16  # parsec, m

M_SUN_KG = GM_SUN / G_SI    # ~1.98841e30 kg
M_EARTH_KG = GM_EARTH / G_SI  # ~5.97217e24 kg
M_JUP_KG = 1.89812e27       # IAU nominal Jovian mass parameter / G

#: Earth radii per Jupiter radius (equatorial, nominal).
R_JUP_IN_R_EARTH = R_JUP_EQ_M / R_EARTH_EQ_M   # ~11.209
#: Earth masses per Jupiter mass.
M_JUP_IN_M_EARTH = M_JUP_KG / M_EARTH_KG       # ~317.8

# --------------------------------------------------------------------------
# Earth reference values -- the yardstick for every "Earth-like" statement
# --------------------------------------------------------------------------
#: Total solar irradiance at 1 au, W m^-2. Kopp & Lean (2011), Geophys. Res.
#: Lett. 38, L01706, doi:10.1029/2010GL045777. The archive's `pl_insol` column
#: is already normalised to Earth = 1, so this is used for unit conversion and
#: for display only.
S_EARTH_W_M2 = 1360.8

#: Earth bulk density, g cm^-3 (NASA Earth Fact Sheet).
RHO_EARTH_G_CM3 = 5.514

#: Earth surface gravity, m s^-2.
G_EARTH_MS2 = 9.80665

#: Earth escape velocity, km s^-1.
V_ESC_EARTH_KMS = 11.186

#: Earth Bond albedo. Stephens et al. (2015), Nature Geoscience 8, 261,
#: doi:10.1038/ngeo2398 give 0.29; the classical Kopparapu/Kasting HZ work
#: uses 0.306 (NASA Earth Fact Sheet). We adopt 0.306 for continuity with the
#: habitable-zone literature and expose the choice as a parameter.
BOND_ALBEDO_EARTH = 0.306

#: Earth equilibrium temperature, K, for A_B = 0.306 and zero greenhouse.
#: T_eq = 278.5 * (1 - A)^(1/4) * S^(1/4) with S in Earth units.
#: NOTE: this is ~254 K, NOT Earth's ~288 K mean surface temperature. The 34 K
#: difference is the greenhouse effect, which equilibrium temperature excludes
#: by construction. Every comparison in this project is equilibrium-to-
#: equilibrium; we never compare an exoplanet T_eq against Earth's surface T.
T_EQ_EARTH_K = 254.0

#: Earth mean surface temperature, K -- carried ONLY so the interface can show
#: the contrast above. It is never used as a scoring target.
T_SURF_EARTH_K = 288.0

#: Earth orbital period, days.
P_EARTH_DAYS = 365.256363

# --------------------------------------------------------------------------
# Solar System comparison controls
# --------------------------------------------------------------------------
#: Solar System bodies injected into the analysis as *controls*, never as
#: exoplanet observations. They exist so a reader can see where the yardstick
#: itself lands in every ranking. `is_control=True` follows them everywhere.
#:
#: Sources: NASA planetary fact sheets (radius, mass, density, semi-major axis,
#: equilibrium temperature). Insolation is computed as 1/a^2 with a in au.
SOLAR_SYSTEM_CONTROLS: dict[str, dict] = {
    "Earth": {
        "pl_rade": 1.0, "pl_bmasse": 1.0, "pl_dens": 5.514, "pl_orbsmax": 1.0000,
        "pl_orbper": 365.256, "pl_orbeccen": 0.0167, "pl_eqt": 254.0, "pl_insol": 1.0,
        "st_teff": 5772.0, "st_rad": 1.0, "st_mass": 1.0, "st_lum": 0.0, "st_met": 0.0,
        "st_age": 4.60, "sy_dist": 0.0,
    },
    "Venus": {
        "pl_rade": 0.9499, "pl_bmasse": 0.8150, "pl_dens": 5.243, "pl_orbsmax": 0.7233,
        "pl_orbper": 224.701, "pl_orbeccen": 0.0068, "pl_eqt": 231.7, "pl_insol": 1.911,
        "st_teff": 5772.0, "st_rad": 1.0, "st_mass": 1.0, "st_lum": 0.0, "st_met": 0.0,
        "st_age": 4.60, "sy_dist": 0.0,
    },
    "Mars": {
        "pl_rade": 0.5320, "pl_bmasse": 0.1074, "pl_dens": 3.934, "pl_orbsmax": 1.5237,
        "pl_orbper": 686.980, "pl_orbeccen": 0.0934, "pl_eqt": 209.8, "pl_insol": 0.431,
        "st_teff": 5772.0, "st_rad": 1.0, "st_mass": 1.0, "st_lum": 0.0, "st_met": 0.0,
        "st_age": 4.60, "sy_dist": 0.0,
    },
    "Mercury": {
        "pl_rade": 0.3829, "pl_bmasse": 0.0553, "pl_dens": 5.427, "pl_orbsmax": 0.3871,
        "pl_orbper": 87.969, "pl_orbeccen": 0.2056, "pl_eqt": 439.6, "pl_insol": 6.674,
        "st_teff": 5772.0, "st_rad": 1.0, "st_mass": 1.0, "st_lum": 0.0, "st_met": 0.0,
        "st_age": 4.60, "sy_dist": 0.0,
    },
    "Jupiter": {
        "pl_rade": 11.209, "pl_bmasse": 317.83, "pl_dens": 1.326, "pl_orbsmax": 5.2044,
        "pl_orbper": 4332.589, "pl_orbeccen": 0.0489, "pl_eqt": 110.0, "pl_insol": 0.0369,
        "st_teff": 5772.0, "st_rad": 1.0, "st_mass": 1.0, "st_lum": 0.0, "st_met": 0.0,
        "st_age": 4.60, "sy_dist": 0.0,
    },
}

#: Effective temperature of the Sun used as the HZ polynomial pivot by
#: Kopparapu et al. (2013). NOTE: this is the paper's pivot (5780 K), which
#: differs slightly from the IAU nominal solar T_eff (5772 K). The pivot must
#: match the paper or the polynomial is evaluated at the wrong offset.
T_EFF_SUN_HZ_PIVOT_K = 5780.0

#: IAU 2015 nominal solar effective temperature, K.
T_EFF_SUN_K = 5772.0


def earth_equilibrium_temperature(albedo: float = BOND_ALBEDO_EARTH) -> float:
    """Equilibrium temperature of Earth for a given Bond albedo, K.

    Provided so tests can assert the constant above is self-consistent rather
    than a copied literal.
    """
    return 278.5 * (1.0 - albedo) ** 0.25


def _self_check() -> None:  # pragma: no cover - exercised by tests
    assert abs(earth_equilibrium_temperature() - T_EQ_EARTH_K) < 1.0
    assert abs(R_JUP_IN_R_EARTH - 11.209) < 0.01
    assert abs(M_JUP_IN_M_EARTH - 317.8) < 0.5
    assert abs(M_EARTH_KG - 5.9722e24) / 5.9722e24 < 1e-3
