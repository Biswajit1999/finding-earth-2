"""Transparent XUV histories and MUSCLES SED band integration.

The generic histories are bounded scenarios, not calibrated posteriors for an
individual star.  Exact MUSCLES host matches remain a separate current-epoch
data product because those SEDs combine observations, reconstructions and
model-filled wavelength regions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SECONDS_PER_GYR = 365.25 * 86400 * 1e9


@dataclass(frozen=True)
class XUVScenario:
    """Broken-power-law fractional XUV luminosity scenario."""

    saturated_fraction: float
    decay_exponent: float
    saturation_gyr_fgk: float
    saturation_gyr_m: float


XUV_SCENARIOS: dict[str, XUVScenario] = {
    "short_low": XUVScenario(3e-4, 1.50, 0.03, 0.50),
    "nominal": XUVScenario(1e-3, 1.23, 0.10, 1.00),
    "extended_high": XUVScenario(3e-3, 1.00, 0.30, 3.00),
}


def integrate_sed_bands(
    wavelength_low_angstrom: np.ndarray,
    wavelength_high_angstrom: np.ndarray,
    flux_density_erg_s_cm2_angstrom: np.ndarray,
    error_density_erg_s_cm2_angstrom: np.ndarray,
    bolometric_flux_erg_s_cm2: float,
) -> dict[str, dict[str, float]]:
    """Integrate XUV, FUV, NUV and Ly-alpha bands from a binned SED.

    Bin overlap is handled exactly at band edges.  Error propagation treats
    bins as independent and therefore captures reported statistical errors,
    not correlated reconstruction or model uncertainty.
    """

    low, high, flux, error = np.broadcast_arrays(
        np.asarray(wavelength_low_angstrom, dtype=float),
        np.asarray(wavelength_high_angstrom, dtype=float),
        np.asarray(flux_density_erg_s_cm2_angstrom, dtype=float),
        np.asarray(error_density_erg_s_cm2_angstrom, dtype=float),
    )
    if not np.isfinite(bolometric_flux_erg_s_cm2) or bolometric_flux_erg_s_cm2 <= 0:
        raise ValueError("bolometric flux must be finite and positive")
    if np.any(high <= low):
        raise ValueError("SED wavelength bins must have positive width")
    bands = {
        "xuv_5_912a": (5.0, 912.0),
        "fuv_912_1700a": (912.0, 1700.0),
        "nuv_1700_3200a": (1700.0, 3200.0),
        "lya_1210_1222a": (1210.0, 1222.0),
    }
    result: dict[str, dict[str, float]] = {}
    for name, (band_low, band_high) in bands.items():
        overlap = np.maximum(0.0, np.minimum(high, band_high) - np.maximum(low, band_low))
        finite = np.isfinite(flux) & np.isfinite(error)
        integrated = float(np.sum(np.where(finite, flux * overlap, 0.0)))
        statistical_error = float(np.sqrt(np.sum(np.where(finite, (error * overlap) ** 2, 0.0))))
        result[name] = {
            "flux_at_earth_erg_s_cm2": integrated,
            "statistical_error_erg_s_cm2": statistical_error,
            "fraction_bolometric": integrated / bolometric_flux_erg_s_cm2,
        }
    return result


def saturation_time_gyr(stellar_mass_solar: float, scenario: XUVScenario) -> float:
    if not np.isfinite(stellar_mass_solar) or stellar_mass_solar <= 0:
        raise ValueError("stellar mass must be finite and positive")
    return scenario.saturation_gyr_m if stellar_mass_solar < 0.6 else scenario.saturation_gyr_fgk


def xuv_luminosity_fraction(
    age_gyr: np.ndarray | float,
    stellar_mass_solar: float,
    scenario: XUVScenario,
) -> np.ndarray:
    """Return L_XUV/L_bol for a saturated-then-decaying scenario."""

    age = np.asarray(age_gyr, dtype=float)
    t_sat = saturation_time_gyr(stellar_mass_solar, scenario)
    valid = np.isfinite(age) & (age > 0)
    ratio = scenario.saturated_fraction * np.maximum(age / t_sat, 1.0) ** (-scenario.decay_exponent)
    return np.where(valid, ratio, np.nan)


def xuv_flux_history(
    age_gyr: np.ndarray | float,
    bolometric_flux_w_m2: float,
    stellar_mass_solar: float,
    scenario: XUVScenario,
) -> np.ndarray:
    if not np.isfinite(bolometric_flux_w_m2) or bolometric_flux_w_m2 <= 0:
        raise ValueError("bolometric flux must be finite and positive")
    return bolometric_flux_w_m2 * xuv_luminosity_fraction(age_gyr, stellar_mass_solar, scenario)


def xuv_history_summary(
    *,
    stellar_age_gyr: float,
    bolometric_flux_w_m2: float,
    stellar_mass_solar: float,
    scenario: XUVScenario,
    start_age_gyr: float = 0.01,
    steps: int = 512,
) -> dict[str, float]:
    """Current XUV flux and integrated exposure for one scenario."""

    if not np.isfinite(stellar_age_gyr) or stellar_age_gyr <= start_age_gyr:
        raise ValueError("stellar age must exceed the integration start")
    ages = np.geomspace(start_age_gyr, stellar_age_gyr, steps)
    flux = xuv_flux_history(ages, bolometric_flux_w_m2, stellar_mass_solar, scenario)
    dose = float(np.sum(0.5 * (flux[:-1] + flux[1:]) * np.diff(ages)) * SECONDS_PER_GYR)
    return {
        "current_xuv_flux_w_m2": float(flux[-1]),
        "integrated_xuv_dose_j_m2": dose,
        "saturation_time_gyr": saturation_time_gyr(stellar_mass_solar, scenario),
        "integration_start_gyr": start_age_gyr,
    }
