"""Habitable-zone boundaries after Kopparapu et al. (2013).

Reference
---------
Kopparapu, R. K., Ramirez, R., Kasting, J. F., Eymet, V., Robinson, T. D.,
Mahadevan, S., Terrien, R. C., Domagal-Goldman, S., Meadows, V., & Deshpande, R.
(2013). *Habitable Zones Around Main-Sequence Stars: New Estimates.*
The Astrophysical Journal, 765(2), 131. doi:10.1088/0004-637X/765/2/131

Erratum: 2013, ApJ, 770, 82. doi:10.1088/0004-637X/770/1/82

.. important::
   The erratum supersedes Table 3 of the original paper with a corrected set of
   coefficients. Both sets are implemented here and the **erratum is the
   default**, because the original values are the ones reproduced in the arXiv
   v1 preprint and are therefore the ones most often propagated by mistake.

   The difference is not cosmetic: the runaway-greenhouse (inner conservative)
   flux boundary moves from 1.0512 to 1.0385 S_Earth for a Sun-like star, which
   shifts the inner edge of the conservative habitable zone outward and changes
   which planets qualify.

The model
---------
The effective stellar flux at a habitable-zone boundary is a quartic in the
stellar effective temperature offset from the Sun::

    S_eff = S_eff_sun + a*T + b*T^2 + c*T^3 + d*T^4        (Equation 2)

    T = T_eff - 5780 K

and the corresponding orbital distance for a star of luminosity L (in solar
units) is::

    d = sqrt(L / S_eff)   [au]                              (Equation 3)

Note the pivot is the paper's 5780 K, which differs slightly from the IAU
nominal solar effective temperature of 5772 K. The paper's pivot must be used
or the polynomial is evaluated at the wrong offset.

Validity
--------
The fit is stated for ``2600 K <= T_eff <= 7200 K``. Outside that range this
module returns NaN rather than extrapolating. Silent extrapolation onto A-type
hosts or ultracool dwarfs is a real and common error: the underlying climate
model was never run there.

Boundaries
----------
Two habitable zones are exposed separately, never merged into one "the"
habitable zone, because the disagreement between them is a genuine
methodological uncertainty:

**Conservative** -- runaway greenhouse (inner) to maximum greenhouse (outer).
Derived from climate modelling of when a water-rich planet loses its oceans and
when CO2 can no longer keep a surface above freezing.

**Optimistic** -- recent Venus (inner) to early Mars (outer). Empirical, based
on the argument that Venus had no liquid water for the last ~1 Gyr and Mars had
some ~3.8 Gyr ago, so the true boundaries lie at least that far out.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Union

import numpy as np

__all__ = [
    "BOUNDARIES",
    "COEFFS_ERRATUM_2013",
    "COEFFS_ORIGINAL_2013",
    "HZ_TEFF_MAX",
    "HZ_TEFF_MIN",
    "TEFF_SUN_PIVOT",
    "hz_distance_au",
    "hz_flux_boundaries",
    "hz_membership",
    "in_conservative_hz",
    "in_optimistic_hz",
    "seff_boundary",
]

ArrayLike = Union[float, np.ndarray]

#: Polynomial pivot used by Kopparapu et al. (2013), Equation (2).
TEFF_SUN_PIVOT = 5780.0

#: Stated validity range of the fit, K.
HZ_TEFF_MIN = 2600.0
HZ_TEFF_MAX = 7200.0

#: Boundary names, ordered from the innermost (highest flux) outward.
BOUNDARIES: tuple[str, ...] = (
    "recent_venus",
    "runaway_greenhouse",
    "moist_greenhouse",
    "maximum_greenhouse",
    "early_mars",
)

#: Kopparapu et al. (2013) ApJ 765, 131 -- Table 3 as originally published.
#: Retained so the effect of the erratum can be measured, not because it should
#: be used. Order per boundary: (S_eff_sun, a, b, c, d).
COEFFS_ORIGINAL_2013: dict[str, tuple[float, float, float, float, float]] = {
    "recent_venus":       (1.7753, 1.4316e-4, 2.9875e-9, -7.5702e-12, -1.1635e-15),
    "runaway_greenhouse": (1.0512, 1.3242e-4, 1.5418e-8, -7.9895e-12, -1.8328e-15),
    "moist_greenhouse":   (1.0140, 8.1774e-5, 1.7063e-9, -4.3241e-12, -6.6462e-16),
    "maximum_greenhouse": (0.3438, 5.8942e-5, 1.6558e-9, -3.0045e-12, -5.2983e-16),
    "early_mars":         (0.3179, 5.4513e-5, 1.5313e-9, -2.7786e-12, -4.8997e-16),
}

#: Kopparapu et al. (2013) Erratum, ApJ 770, 82 -- "Updated Coefficients".
#: THIS IS THE DEFAULT and the set that should be used.
COEFFS_ERRATUM_2013: dict[str, tuple[float, float, float, float, float]] = {
    "recent_venus":       (1.7763, 1.4335e-4, 3.3954e-9, -7.6364e-12, -1.1950e-15),
    "runaway_greenhouse": (1.0385, 1.2456e-4, 1.4612e-8, -7.6345e-12, -1.7511e-15),
    "moist_greenhouse":   (1.0146, 8.1884e-5, 1.9394e-9, -4.3618e-12, -6.8260e-16),
    "maximum_greenhouse": (0.3507, 5.9578e-5, 1.6707e-9, -3.0058e-12, -5.1925e-16),
    "early_mars":         (0.3207, 5.4471e-5, 1.5275e-9, -2.1709e-12, -3.8282e-16),
}

_DEFAULT_COEFFS = COEFFS_ERRATUM_2013


def seff_boundary(
    teff: ArrayLike,
    boundary: str,
    coefficients: Mapping[str, tuple[float, float, float, float, float]] = _DEFAULT_COEFFS,
    clip_to_validity: bool = False,
) -> np.ndarray:
    """Effective stellar flux at a habitable-zone boundary, in Earth units.

    Parameters
    ----------
    teff
        Stellar effective temperature, K.
    boundary
        One of :data:`BOUNDARIES`.
    coefficients
        Coefficient table. Defaults to the 2013 erratum.
    clip_to_validity
        If ``False`` (default) temperatures outside 2600-7200 K yield NaN. If
        ``True`` they are clipped to the range first -- only appropriate for
        visualisation, never for scoring, and the caller must say which.

    Returns
    -------
    numpy.ndarray
        S_eff in units of the flux Earth receives. Higher means closer in.
    """
    if boundary not in coefficients:
        raise KeyError("Unknown HZ boundary " + repr(boundary) + "; expected one of " + str(BOUNDARIES))

    t = np.asarray(teff, dtype=float)
    valid = np.isfinite(t) & (t >= HZ_TEFF_MIN) & (t <= HZ_TEFF_MAX)

    t_used = np.clip(t, HZ_TEFF_MIN, HZ_TEFF_MAX) if clip_to_validity else t

    s0, a, b, c, d = coefficients[boundary]
    dt = t_used - TEFF_SUN_PIVOT
    seff = s0 + a * dt + b * dt**2 + c * dt**3 + d * dt**4

    if not clip_to_validity:
        seff = np.where(valid, seff, np.nan)
    else:
        seff = np.where(np.isfinite(t), seff, np.nan)
    return seff


def hz_flux_boundaries(
    teff: ArrayLike,
    coefficients: Mapping[str, tuple[float, float, float, float, float]] = _DEFAULT_COEFFS,
    clip_to_validity: bool = False,
) -> dict[str, np.ndarray]:
    """All five boundary fluxes for the given effective temperature(s)."""
    return {
        b: seff_boundary(teff, b, coefficients, clip_to_validity) for b in BOUNDARIES
    }


def hz_distance_au(
    teff: ArrayLike,
    luminosity_lsun: ArrayLike,
    boundary: str,
    coefficients: Mapping[str, tuple[float, float, float, float, float]] = _DEFAULT_COEFFS,
    clip_to_validity: bool = False,
) -> np.ndarray:
    """Orbital distance of a habitable-zone boundary, au.

    Equation (3) of Kopparapu et al. (2013): ``d = sqrt(L / S_eff)`` with L in
    solar luminosities.
    """
    seff = seff_boundary(teff, boundary, coefficients, clip_to_validity)
    lum = np.asarray(luminosity_lsun, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        d = np.sqrt(lum / seff)
    return np.where(np.isfinite(d), d, np.nan)


def in_conservative_hz(
    insolation_earth: ArrayLike,
    teff: ArrayLike,
    coefficients: Mapping[str, tuple[float, float, float, float, float]] = _DEFAULT_COEFFS,
) -> np.ndarray:
    """Boolean-valued membership of the conservative habitable zone.

    Conservative HZ = runaway greenhouse (inner) to maximum greenhouse (outer).

    Returns a float array of 1.0 / 0.0 / NaN, not a bool array, because "we do
    not know" is a distinct and common answer that a bool cannot carry. NaN
    propagates when insolation is unknown or the host is outside the fit range.
    """
    s = np.asarray(insolation_earth, dtype=float)
    inner = seff_boundary(teff, "runaway_greenhouse", coefficients)
    outer = seff_boundary(teff, "maximum_greenhouse", coefficients)
    ok = np.isfinite(s) & np.isfinite(inner) & np.isfinite(outer)
    with np.errstate(invalid="ignore"):
        member = (s <= inner) & (s >= outer)
    return np.where(ok, member.astype(float), np.nan)


def in_optimistic_hz(
    insolation_earth: ArrayLike,
    teff: ArrayLike,
    coefficients: Mapping[str, tuple[float, float, float, float, float]] = _DEFAULT_COEFFS,
) -> np.ndarray:
    """Boolean-valued membership of the optimistic habitable zone.

    Optimistic HZ = recent Venus (inner) to early Mars (outer).
    """
    s = np.asarray(insolation_earth, dtype=float)
    inner = seff_boundary(teff, "recent_venus", coefficients)
    outer = seff_boundary(teff, "early_mars", coefficients)
    ok = np.isfinite(s) & np.isfinite(inner) & np.isfinite(outer)
    with np.errstate(invalid="ignore"):
        member = (s <= inner) & (s >= outer)
    return np.where(ok, member.astype(float), np.nan)


def hz_membership(
    insolation_earth: ArrayLike,
    teff: ArrayLike,
    coefficients: Mapping[str, tuple[float, float, float, float, float]] = _DEFAULT_COEFFS,
) -> dict[str, np.ndarray]:
    """Both habitable-zone memberships plus the boundary fluxes used.

    Returned together so the interface can show *why* a planet did or did not
    qualify, rather than only the verdict.
    """
    out: dict[str, np.ndarray] = {
        "hz_conservative": in_conservative_hz(insolation_earth, teff, coefficients),
        "hz_optimistic": in_optimistic_hz(insolation_earth, teff, coefficients),
    }
    for b in BOUNDARIES:
        out["seff_" + b] = seff_boundary(teff, b, coefficients)
    return out


def hz_position(
    insolation_earth: ArrayLike,
    teff: ArrayLike,
    coefficients: Mapping[str, tuple[float, float, float, float, float]] = _DEFAULT_COEFFS,
) -> np.ndarray:
    """Fractional position across the conservative habitable zone.

    0.0 at the inner (runaway greenhouse) edge, 1.0 at the outer (maximum
    greenhouse) edge; <0 is interior to the HZ, >1 is exterior. Useful for
    plotting a planet's location within the zone on a common axis regardless of
    host star.
    """
    s = np.asarray(insolation_earth, dtype=float)
    inner = seff_boundary(teff, "runaway_greenhouse", coefficients)
    outer = seff_boundary(teff, "maximum_greenhouse", coefficients)
    with np.errstate(invalid="ignore", divide="ignore"):
        pos = (inner - s) / (inner - outer)
    return np.where(np.isfinite(pos), pos, np.nan)
