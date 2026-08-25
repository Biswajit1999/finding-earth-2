"""Earth Similarity Index (ESI).

Reference
---------
Schulze-Makuch, D., Mendez, A., Fairen, A. G., von Paris, P., Turse, C.,
Boyer, G., Davila, A. F., Resendes de Sousa Antonio, M., Catling, D., &
Irwin, L. N. (2011). *A Two-Tiered Approach to Assessing the Habitability of
Exoplanets.* Astrobiology, 11(10), 1041-1052. doi:10.1089/ast.2010.0592
(bibcode 2011AsBio..11.1041S)

Definition
----------
For a planetary property :math:`x` with terrestrial reference :math:`x_0` and
weight exponent :math:`w`::

    ESI_x = ( 1 - | (x - x_0) / (x + x_0) | ) ** (w / n)

The paper groups four properties into two tiers:

======================  ============  ==================
Property                Weight        Tier
======================  ============  ==================
Mean radius             0.57          Interior
Bulk density            1.07          Interior
Escape velocity         0.70          Surface
Surface temperature     5.58          Surface
======================  ============  ==================

with ``ESI_interior`` and ``ESI_surface`` each the geometric mean of their two
terms (``n = 2``), and::

    ESI_global = sqrt( ESI_interior * ESI_surface )

What the ESI is not
-------------------
This must be stated wherever the number is displayed:

* The ESI is a **similarity** measure of bulk physical properties. It is not a
  probability of habitability and emphatically not a probability of life.
* It has no atmospheric term. A planet with Earth's radius, density, escape
  velocity and equilibrium temperature scores near 1.0 whether it has a
  nitrogen-oxygen atmosphere, a CO2 inferno, or no atmosphere at all.
* It is symmetric and unbounded in the wrong direction: a body can score highly
  on individual terms for reasons unrelated to habitability.
* A high ESI on poorly measured inputs is not evidence. This project therefore
  reports ESI alongside an explicit observational-confidence score and never
  ranks on ESI alone.

The temperature substitution -- important
-----------------------------------------
The paper's fourth parameter is *surface* temperature, referenced to Earth's
288 K. **Surface temperature is not measured for exoplanets.** The only
temperature the catalogues provide is equilibrium temperature, which excludes
greenhouse warming by construction.

Substituting exoplanet T_eq against Earth's T_surf = 288 K compares two
different physical quantities and systematically rewards planets that are too
hot: a world with T_eq = 288 K would score a perfect temperature term while
actually being far warmer than Earth once any atmosphere is added.

This module therefore references equilibrium temperature against **Earth's own
equilibrium temperature, 254 K**, and records which convention was used in the
returned frame. ``T_SURF_EARTH_K`` exists in :mod:`earth2.constants` only for
display contrast and is never used as a scoring target.

The Venus problem -- read this before quoting any ESI
-----------------------------------------------------
The substitution above is unavoidable, and it has a consequence that limits
every ESI-based result in this project and in the literature:

    Venus scores ESI_global = 0.92, and ESI_temperature = 0.88 on equilibrium
    temperature alone.

Venus's Bond albedo (~0.77) is so high that its equilibrium temperature, 232 K,
is *cooler* than Earth's 254 K. On bulk radius, density, escape velocity and
equilibrium temperature, Venus is nearly indistinguishable from Earth. Its
actual surface sits at 737 K under 92 bar of CO2.

The Planetary Habitability Laboratory quotes Venus at ESI ~= 0.44 by using the
surface temperature. That number is not available for any exoplanet.

Therefore: **an ESI computed from data that exists for real exoplanets cannot
separate an Earth from a Venus.** This is a property of the available
observations, not a defect of this implementation. It is why this project
reports the ESI as one component among several, never as a ranking on its own,
and why Venus is carried through the entire pipeline as a control so a reader
can see the degeneracy rather than be told about it.
"""

from __future__ import annotations

from typing import Union

import numpy as np
import pandas as pd

from earth2.constants import (
    BOND_ALBEDO_EARTH,
    RHO_EARTH_G_CM3,
    V_ESC_EARTH_KMS,
    earth_equilibrium_temperature,
)

__all__ = [
    "ESI_WEIGHTS",
    "bulk_density_earth_units",
    "escape_velocity_earth_units",
    "esi_component",
    "esi_frame",
    "esi_global",
]

ArrayLike = Union[float, np.ndarray, pd.Series]

#: Weight exponents from Schulze-Makuch et al. (2011), Table 1.
ESI_WEIGHTS: dict[str, float] = {
    "radius": 0.57,
    "density": 1.07,
    "escape_velocity": 0.70,
    "temperature": 5.58,
}

#: Earth's equilibrium temperature under the same uniform-albedo convention the
#: pipeline applies to every planet. Computed rather than written as a literal so
#: that Earth scores exactly 1.0 by construction: if the reference were the
#: rounded 254.0 K while the pipeline derived 254.19 K, Earth would score 0.9997
#: and every other score would inherit that small offset.
T_EQ_EARTH_REFERENCE_K = earth_equilibrium_temperature(BOND_ALBEDO_EARTH)

#: Terrestrial reference values. Temperature is Earth's EQUILIBRIUM temperature,
#: see the module docstring for why.
ESI_REFERENCES: dict[str, float] = {
    "radius": 1.0,                       # Earth radii
    "density": RHO_EARTH_G_CM3,          # g cm^-3
    "escape_velocity": V_ESC_EARTH_KMS,  # km s^-1
    "temperature": T_EQ_EARTH_REFERENCE_K,  # K, equilibrium not surface
}


def esi_component(
    value: ArrayLike,
    reference: float,
    weight: float,
    n: int = 1,
) -> np.ndarray:
    """One ESI term.

    Returns NaN where ``value`` is missing or non-positive. A non-positive
    radius, density or temperature is unphysical; treating it as zero would
    yield a spuriously defined similarity.
    """
    x = np.asarray(value, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.abs((x - reference) / (x + reference))
        term = (1.0 - frac) ** (weight / float(n))
    bad = ~np.isfinite(x) | (x <= 0)
    return np.where(bad, np.nan, term)


def bulk_density_earth_units(
    mass_earth: ArrayLike,
    radius_earth: ArrayLike,
) -> np.ndarray:
    """Bulk density in g cm^-3 from mass and radius in Earth units.

    rho = rho_Earth * (M/M_E) / (R/R_E)^3
    """
    m = np.asarray(mass_earth, dtype=float)
    r = np.asarray(radius_earth, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        rho = RHO_EARTH_G_CM3 * m / (r**3)
    return np.where(np.isfinite(rho) & (r > 0) & (m > 0), rho, np.nan)


def escape_velocity_earth_units(
    mass_earth: ArrayLike,
    radius_earth: ArrayLike,
) -> np.ndarray:
    """Escape velocity in km s^-1 from mass and radius in Earth units.

    v_esc = v_esc,Earth * sqrt( (M/M_E) / (R/R_E) )
    """
    m = np.asarray(mass_earth, dtype=float)
    r = np.asarray(radius_earth, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        v = V_ESC_EARTH_KMS * np.sqrt(m / r)
    return np.where(np.isfinite(v) & (r > 0) & (m > 0), v, np.nan)


def esi_global(
    radius_earth: ArrayLike,
    density_g_cm3: ArrayLike,
    escape_velocity_kms: ArrayLike,
    equilibrium_temp_k: ArrayLike,
) -> dict[str, np.ndarray]:
    """Interior, surface and global ESI.

    Every input must already be in the units named. Missing inputs propagate as
    NaN through the tier they belong to and then through the global value --
    deliberately. An ESI computed from two of four properties is not an ESI, and
    filling the gaps with Earth values would manufacture similarity from
    ignorance, which is exactly the failure mode this project exists to avoid.
    """
    n_tier = 2

    esi_r = esi_component(radius_earth, ESI_REFERENCES["radius"],
                          ESI_WEIGHTS["radius"], n_tier)
    esi_d = esi_component(density_g_cm3, ESI_REFERENCES["density"],
                          ESI_WEIGHTS["density"], n_tier)
    esi_v = esi_component(escape_velocity_kms, ESI_REFERENCES["escape_velocity"],
                          ESI_WEIGHTS["escape_velocity"], n_tier)
    esi_t = esi_component(equilibrium_temp_k, ESI_REFERENCES["temperature"],
                          ESI_WEIGHTS["temperature"], n_tier)

    with np.errstate(invalid="ignore"):
        # esi_r/d/v/t already carry the tier-level n=2 exponent (weight / 2), so
        # ESI_interior and ESI_surface are the plain products of their two terms
        # -- NOT a further sqrt of that product. An earlier version of this
        # function took that extra sqrt here, which silently compounded to
        # global exponents of weight/8 instead of the published weight/4 (each
        # of the two sqrt calls below halves the exponent once; adding a third
        # halving here is the bug). See docs/RESEARCH_NOTES.md, "ESI exponent
        # bug: an extra square root at the tier-combining step", for the fix.
        interior = esi_r * esi_d
        surface = esi_v * esi_t
        glob = np.sqrt(interior * surface)

    return {
        "esi_radius": esi_r,
        "esi_density": esi_d,
        "esi_escape_velocity": esi_v,
        "esi_temperature": esi_t,
        "esi_interior": interior,
        "esi_surface": surface,
        "esi_global": glob,
    }


def esi_frame(
    df: pd.DataFrame,
    radius_col: str = "pl_rade",
    mass_col: str = "pl_bmasse",
    density_col: str | None = "pl_dens",
    teq_col: str = "pl_eqt",
) -> pd.DataFrame:
    """Compute ESI for a catalogue frame.

    Density is taken from the catalogue where present and otherwise derived from
    mass and radius. Which of the two happened is recorded per row in
    ``esi_density_source`` so the provenance panel can show it, because a
    catalogue density and a derived density are not equally trustworthy: the
    derived one inherits the full uncertainty of both mass and radius.
    """
    out = pd.DataFrame(index=df.index)

    radius = df[radius_col] if radius_col in df else pd.Series(np.nan, index=df.index)
    mass = df[mass_col] if mass_col in df else pd.Series(np.nan, index=df.index)
    teq = df[teq_col] if teq_col in df else pd.Series(np.nan, index=df.index)

    derived_rho = bulk_density_earth_units(mass, radius)
    if density_col and density_col in df:
        cat_rho = pd.to_numeric(df[density_col], errors="coerce").to_numpy(dtype=float)
        use_cat = np.isfinite(cat_rho) & (cat_rho > 0)
        rho = np.where(use_cat, cat_rho, derived_rho)
        source = np.where(
            use_cat, "catalogue",
            np.where(np.isfinite(derived_rho), "derived_from_mass_radius", "missing"),
        )
    else:
        rho = derived_rho
        source = np.where(np.isfinite(derived_rho), "derived_from_mass_radius", "missing")

    vesc = escape_velocity_earth_units(mass, radius)

    comps = esi_global(radius, rho, vesc, teq)
    for k, v in comps.items():
        out[k] = v

    out["pl_dens_used"] = rho
    out["esi_density_source"] = source
    out["pl_vesc_kms"] = vesc
    out["esi_temperature_reference"] = "equilibrium_254K"
    return out
