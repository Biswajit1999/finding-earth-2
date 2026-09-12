"""Stellar-evolution and climate-boundary inference.

Every result in this package is conditional on named stellar and climate
models.  A habitable-zone classification is not evidence for an atmosphere,
surface liquid water, biology, or life.
"""

from earth2.climate.evolution import (
    CLIMATE_PRESCRIPTIONS,
    EvolutionConfig,
    MISTMainSequenceGrid,
    infer_continuous_hz,
)

__all__ = [
    "CLIMATE_PRESCRIPTIONS",
    "EvolutionConfig",
    "MISTMainSequenceGrid",
    "infer_continuous_hz",
]
