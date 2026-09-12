"""Energy-limited atmospheric-escape scenario calculations."""

from __future__ import annotations

import numpy as np

from earth2.constants import AU_M, G_SI, M_EARTH_KG, M_SUN_KG, R_EARTH_M


def roche_tide_factor(
    *,
    stellar_mass_solar: float,
    planet_mass_earth: float,
    semimajor_axis_au: float,
    xuv_radius_earth: float,
) -> float:
    """Erkaev-style Roche potential correction using a Hill-radius scale."""

    values = np.asarray(
        [stellar_mass_solar, planet_mass_earth, semimajor_axis_au, xuv_radius_earth]
    )
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("stellar, planet, orbit and XUV radius inputs must be positive")
    roche_radius = (
        semimajor_axis_au
        * AU_M
        * (planet_mass_earth * M_EARTH_KG / (3 * stellar_mass_solar * M_SUN_KG)) ** (1 / 3)
    )
    xi = roche_radius / (xuv_radius_earth * R_EARTH_M)
    if xi <= 1:
        return float("nan")
    return float(1 - 3 / (2 * xi) + 1 / (2 * xi**3))


def energy_limited_mass_loss_rate(
    *,
    xuv_flux_w_m2: float,
    planet_mass_earth: float,
    planet_radius_earth: float,
    xuv_radius_factor: float,
    heating_efficiency: float,
    tide_factor: float,
) -> float:
    """Energy-limited escape rate in kg/s.

    Uses pi*epsilon*R_p*R_XUV^2*F_XUV/(G*M_p*K_tide), with gravitational
    binding evaluated at the optical radius as requested by the project model.
    """

    values = np.asarray(
        [
            xuv_flux_w_m2,
            planet_mass_earth,
            planet_radius_earth,
            xuv_radius_factor,
            heating_efficiency,
            tide_factor,
        ]
    )
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("energy-limited escape inputs must be finite and positive")
    if heating_efficiency > 1:
        raise ValueError("heating efficiency cannot exceed one")
    planet_radius = planet_radius_earth * R_EARTH_M
    xuv_radius = xuv_radius_factor * planet_radius
    planet_mass = planet_mass_earth * M_EARTH_KG
    return float(
        np.pi
        * heating_efficiency
        * planet_radius
        * xuv_radius**2
        * xuv_flux_w_m2
        / (G_SI * planet_mass * tide_factor)
    )


def integrated_energy_limited_loss(
    *,
    xuv_dose_j_m2: float,
    planet_mass_earth: float,
    planet_radius_earth: float,
    xuv_radius_factor: float,
    heating_efficiency: float,
    tide_factor: float,
) -> float:
    """Integrated lost mass in Earth masses with planet properties held fixed."""

    rate_per_flux = energy_limited_mass_loss_rate(
        xuv_flux_w_m2=1.0,
        planet_mass_earth=planet_mass_earth,
        planet_radius_earth=planet_radius_earth,
        xuv_radius_factor=xuv_radius_factor,
        heating_efficiency=heating_efficiency,
        tide_factor=tide_factor,
    )
    return float(rate_per_flux * xuv_dose_j_m2 / M_EARTH_KG)
