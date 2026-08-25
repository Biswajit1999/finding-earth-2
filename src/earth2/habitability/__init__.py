"""Physically motivated habitability metrics.

Two independent things live here and must not be conflated:

``hz``   habitable-zone membership -- does the planet receive a stellar flux
         compatible with surface liquid water, per Kopparapu et al. (2013)?
``esi``  Earth Similarity Index -- how close are the bulk physical properties
         to Earth's, per Schulze-Makuch et al. (2011)?

A planet can score highly on one and poorly on the other. Neither is a
probability of habitability, and neither is evidence of life.
"""

from __future__ import annotations

from earth2.habitability.esi import (
    ESI_REFERENCES,
    ESI_WEIGHTS,
    bulk_density_earth_units,
    escape_velocity_earth_units,
    esi_frame,
    esi_global,
)
from earth2.habitability.hz import (
    BOUNDARIES,
    COEFFS_ERRATUM_2013,
    COEFFS_ORIGINAL_2013,
    hz_distance_au,
    hz_flux_boundaries,
    hz_membership,
    hz_position,
    in_conservative_hz,
    in_optimistic_hz,
    seff_boundary,
)

__all__ = [
    "BOUNDARIES", "COEFFS_ERRATUM_2013", "COEFFS_ORIGINAL_2013",
    "ESI_REFERENCES", "ESI_WEIGHTS",
    "bulk_density_earth_units", "escape_velocity_earth_units",
    "esi_frame", "esi_global",
    "hz_distance_au", "hz_flux_boundaries", "hz_membership", "hz_position",
    "in_conservative_hz", "in_optimistic_hz", "seff_boundary",
]
