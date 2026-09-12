"""Transparent distance, relativity, flux, and angular-resolution calculations."""

from __future__ import annotations

import math
from typing import Any

C_KM_S = 299_792.458
PC_KM = 3.085677581491367e13
LY_PER_PC = 3.261563777
SECONDS_PER_YEAR = 31_557_600.0
SOLAR_LUMINOSITY_W = 3.828e26
EARTH_RADIUS_M = 6.3781e6
AU_M = 149_597_870_700.0
PLANCK_J_S = 6.62607015e-34


def distance_summary(distance_pc: float, speed_fractions: tuple[float, ...] = ()) -> dict[str, Any]:
    """Return communication and travel times in Earth and traveller frames."""
    if not math.isfinite(distance_pc) or distance_pc <= 0:
        raise ValueError("distance_pc must be finite and positive")
    distance_ly = distance_pc * LY_PER_PC
    if not speed_fractions:
        speed_fractions = (17.0 / C_KM_S, 191.0 / C_KM_S, 0.01, 0.1, 0.2, 0.5, 0.9, 0.99)
    travel = []
    for beta in speed_fractions:
        if not 0 < beta < 1:
            raise ValueError("massive-object speed fractions must be between zero and one")
        gamma = 1.0 / math.sqrt(1.0 - beta * beta)
        earth_years = distance_ly / beta
        travel.append(
            {
                "fraction_c": beta,
                "speed_km_s": beta * C_KM_S,
                "gamma": gamma,
                "earth_frame_years": earth_years,
                "traveller_proper_years": earth_years / gamma,
            }
        )
    return {
        "distance_pc": distance_pc,
        "distance_ly": distance_ly,
        "distance_km": distance_pc * PC_KM,
        "signal_one_way_years": distance_ly,
        "signal_round_trip_years": 2 * distance_ly,
        "massive_spacecraft_at_c": "physically impossible; c is the signal-limit thought experiment",
        "travel": travel,
    }


def extragalactic_feasibility(
    distance_pc: float,
    *,
    wavelength_m: float = 550e-9,
    telescope_diameter_m: float = 6.0,
    throughput: float = 0.2,
) -> dict[str, float]:
    """Compute idealized Earth-Sun analogue flux and resolution diagnostics.

    Photon rate treats reflected bolometric power as if every collected photon
    arrived at the selected wavelength. It is therefore an explicit optimistic
    upper bound, before stellar leakage, backgrounds, bandwidth, or detector noise.
    """
    if min(distance_pc, wavelength_m, telescope_diameter_m, throughput) <= 0:
        raise ValueError("all inputs must be positive")
    distance_m = distance_pc * PC_KM * 1000.0
    stellar_flux = SOLAR_LUMINOSITY_W / (4.0 * math.pi * distance_m**2)
    lambert_quadrature = 1.0 / math.pi
    contrast = 0.3 * lambert_quadrature * (EARTH_RADIUS_M / AU_M) ** 2
    planet_flux = stellar_flux * contrast
    photon_energy = PLANCK_J_S * C_KM_S * 1000.0 / wavelength_m
    collecting_area = math.pi * (telescope_diameter_m / 2.0) ** 2
    optimistic_photons = planet_flux * collecting_area * throughput / photon_energy
    separation_rad = AU_M / distance_m
    diameter_rad = 2.0 * EARTH_RADIUS_M / distance_m
    return {
        "distance_pc": distance_pc,
        "stellar_bolometric_flux_w_m2": stellar_flux,
        "earth_quadrature_contrast": contrast,
        "earth_reflected_bolometric_flux_w_m2": planet_flux,
        "earth_sun_separation_microarcsec": separation_rad * 206265e6,
        "earth_diameter_microarcsec": diameter_rad * 206265e6,
        "diffraction_diameter_separate_1au_m": 1.22 * wavelength_m / separation_rad,
        "diffraction_diameter_resolve_earth_m": 1.22 * wavelength_m / diameter_rad,
        "optimistic_photon_upper_bound_s": optimistic_photons,
    }
