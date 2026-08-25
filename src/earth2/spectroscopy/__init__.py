"""Atmospheric spectroscopy and biosignature context.

Planetary-atmosphere measurements only. Stellar spectra measure the star and are
counted, stored and displayed separately -- they are never added to an
atmospheric total.
"""

from __future__ import annotations

from earth2.spectroscopy.biosignature import (
    BIOSIGNATURE_CONTEXT,
    EVIDENCE_STATES,
    FALSE_POSITIVE_MECHANISMS,
    INTERPRETATION_REQUIREMENTS,
    biosignature_context_for,
)
from earth2.spectroscopy.spectra import (
    MOLECULAR_BANDS,
    atmospheric_scale_height_km,
    bands_in_range,
    harmonise_transit_depths,
    planet_spectrum,
    spectrum_inventory,
    transmission_signal_ppm,
)

__all__ = [
    "BIOSIGNATURE_CONTEXT", "EVIDENCE_STATES", "FALSE_POSITIVE_MECHANISMS",
    "INTERPRETATION_REQUIREMENTS", "biosignature_context_for",
    "MOLECULAR_BANDS", "atmospheric_scale_height_km", "bands_in_range",
    "harmonise_transit_depths", "planet_spectrum", "spectrum_inventory",
    "transmission_signal_ppm",
]
