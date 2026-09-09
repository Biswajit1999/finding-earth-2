"""Transit geometry: Kipping (2014), Eqs. 1--2; planet omega in radians."""

from __future__ import annotations

import numpy as np
from astropy import constants as c


def semimajor_axis_au(period_days, stellar_mass_solar, planet_mass_earth=0.0) -> np.ndarray:
    p, ms, mp = np.broadcast_arrays(
        np.asarray(period_days, float),
        np.asarray(stellar_mass_solar, float),
        np.asarray(planet_mass_earth, float),
    )
    if not np.all(np.isfinite(p + ms + mp)) or np.any(p <= 0) or np.any(ms <= 0) or np.any(mp < 0):
        raise ValueError("Periods and stellar masses must be finite positive; planet masses >= 0")
    return (
        np.cbrt(
            c.G.value
            * (ms * c.M_sun.value + mp * c.M_earth.value)
            * (p * 86400) ** 2
            / (4 * np.pi**2)
        )
        / c.au.value
    )


def transit_probability(
    stellar_radius_solar,
    planet_radius_earth,
    semimajor_au,
    eccentricity=0.0,
    omega_rad=0.0,
    *,
    criterion: str = "centre_crossing",
) -> np.ndarray:
    """Isotropic-orientation probability, conditional on e and planet omega.

    centre_crossing means b<1, matching DR25 INJ1's impact-parameter domain.
    any_overlap means b<1+Rp/Rstar (includes grazing transits). The conjunction
    approximation assumes Rstar/a is small. Colliding orbits are rejected.
    """
    rs, rp, a, e, w = np.broadcast_arrays(
        *[
            np.asarray(v, float)
            for v in (
                stellar_radius_solar,
                planet_radius_earth,
                semimajor_au,
                eccentricity,
                omega_rad,
            )
        ]
    )
    if (
        not all(np.all(np.isfinite(v)) for v in (rs, rp, a, e, w))
        or np.any(rs <= 0)
        or np.any(rp < 0)
        or np.any(a <= 0)
        or np.any((e < 0) | (e >= 1))
    ):
        raise ValueError("Finite positive radii/orbits and 0 <= eccentricity < 1 required")
    stellar_au = rs * c.R_sun.value / c.au.value
    planet_au = rp * c.R_earth.value / c.au.value
    if np.any(a * (1 - e) <= stellar_au + planet_au):
        raise ValueError("Orbit intersects the star at periastron")
    if criterion not in {"centre_crossing", "any_overlap"}:
        raise ValueError("Unknown transit criterion")
    radius = stellar_au + (planet_au if criterion == "any_overlap" else 0)
    return np.clip(radius / a * (1 + e * np.sin(w)) / (1 - e * e), 0, 1)
