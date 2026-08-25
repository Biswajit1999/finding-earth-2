"""Turn retrieved archive tables into quantities the scoring engine may use."""

from __future__ import annotations

from earth2.preprocessing.catalogue import (
    MASS_CLASSES,
    add_derived_quantities,
    attach_atmosphere_availability,
    attach_gaia_crossmatch,
    attach_reference_evidence,
    build_catalogue,
    classify_mass_provenance,
    derive_equilibrium_temperature,
    derive_insolation,
    solar_system_control_frame,
)

__all__ = [
    "MASS_CLASSES", "add_derived_quantities", "attach_atmosphere_availability",
    "attach_gaia_crossmatch", "attach_reference_evidence", "build_catalogue",
    "classify_mass_provenance", "derive_equilibrium_temperature", "derive_insolation",
    "solar_system_control_frame",
]
