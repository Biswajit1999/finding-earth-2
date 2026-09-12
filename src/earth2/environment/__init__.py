"""Stellar high-energy environment and atmospheric escape scenarios."""

from earth2.environment.escape import (
    energy_limited_mass_loss_rate,
    integrated_energy_limited_loss,
    roche_tide_factor,
)
from earth2.environment.xuv import (
    XUV_SCENARIOS,
    integrate_sed_bands,
    xuv_flux_history,
    xuv_history_summary,
)

__all__ = [
    "XUV_SCENARIOS",
    "energy_limited_mass_loss_rate",
    "integrate_sed_bands",
    "integrated_energy_limited_loss",
    "roche_tide_factor",
    "xuv_flux_history",
    "xuv_history_summary",
]
