"""Transparent reflected-light and coronagraph scenario physics.

The functions here produce scenario-labelled forecasts.  They do not describe
a final HWO flight architecture and they do not turn a simulated planet into an
observation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from earth2.constants import AU_M, R_EARTH_M

RAD_TO_MAS = 206_264_806.24709636
EARTH_RADIUS_AU = R_EARTH_M / AU_M


def lambert_phase(phase_angle_rad: np.ndarray | float) -> np.ndarray:
    """Lambert-sphere phase function, normalized to one at full phase."""

    alpha = np.asarray(phase_angle_rad, dtype=float)
    if np.any((alpha < 0) | (alpha > np.pi)):
        raise ValueError("phase angle must lie in [0, pi]")
    return (np.sin(alpha) + (np.pi - alpha) * np.cos(alpha)) / np.pi


def solve_eccentric_anomaly(
    mean_anomaly_rad: np.ndarray | float,
    eccentricity: np.ndarray | float,
    *,
    iterations: int = 12,
) -> np.ndarray:
    """Solve Kepler's equation with deterministic vectorized Newton steps."""

    mean = np.mod(np.asarray(mean_anomaly_rad, dtype=float), 2 * np.pi)
    ecc = np.asarray(eccentricity, dtype=float)
    if np.any((ecc < 0) | (ecc >= 1)):
        raise ValueError("eccentricity must lie in [0, 1)")
    estimate = np.where(ecc < 0.8, mean, np.pi)
    for _ in range(iterations):
        residual = estimate - ecc * np.sin(estimate) - mean
        estimate -= residual / (1 - ecc * np.cos(estimate))
    return estimate


def orbital_geometry(
    semi_major_axis_au: np.ndarray | float,
    eccentricity: np.ndarray | float,
    inclination_rad: np.ndarray | float,
    argument_periapsis_rad: np.ndarray | float,
    mean_anomaly_rad: np.ndarray | float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return orbital radius, sky separation, and star-planet-observer angle.

    The longitude of ascending node is omitted because it rotates the sky plane
    without changing scalar separation.  The observer lies on the positive-z
    axis.  The phase angle is zero when the illuminated hemisphere faces the
    observer.
    """

    a = np.asarray(semi_major_axis_au, dtype=float)
    ecc = np.asarray(eccentricity, dtype=float)
    inc = np.asarray(inclination_rad, dtype=float)
    omega = np.asarray(argument_periapsis_rad, dtype=float)
    mean = np.asarray(mean_anomaly_rad, dtype=float)
    if np.any(a <= 0):
        raise ValueError("semi-major axis must be positive")
    eccentric_anomaly = solve_eccentric_anomaly(mean, ecc)
    radius = a * (1 - ecc * np.cos(eccentric_anomaly))
    true_anomaly = 2 * np.arctan2(
        np.sqrt(1 + ecc) * np.sin(eccentric_anomaly / 2),
        np.sqrt(1 - ecc) * np.cos(eccentric_anomaly / 2),
    )
    argument_latitude = true_anomaly + omega
    projected = radius * np.sqrt(
        np.cos(argument_latitude) ** 2 + np.sin(argument_latitude) ** 2 * np.cos(inc) ** 2
    )
    cos_phase = -np.sin(argument_latitude) * np.sin(inc)
    phase = np.arccos(np.clip(cos_phase, -1, 1))
    return radius, projected, phase


@dataclass(frozen=True)
class CoronagraphScenario:
    """One analytic or tabulated coronagraph trade-study scenario."""

    name: str
    diameter_m: float
    wavelength_nm: float
    iwa_lambda_over_d: float
    contrast_floor: float
    owa_mas: float | None = None
    curve_separation_mas: tuple[float, ...] | None = None
    curve_contrast_limit: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if self.diameter_m <= 0 or self.wavelength_nm <= 0:
            raise ValueError("diameter and wavelength must be positive")
        if self.iwa_lambda_over_d <= 0 or self.contrast_floor <= 0:
            raise ValueError("IWA coefficient and contrast floor must be positive")
        curve_x = self.curve_separation_mas
        curve_y = self.curve_contrast_limit
        if (curve_x is None) != (curve_y is None):
            raise ValueError("both contrast-curve arrays must be supplied")
        if curve_x is not None and curve_y is not None:
            if len(curve_x) < 2 or len(curve_x) != len(curve_y):
                raise ValueError("contrast curve needs equal arrays with at least two points")
            if any(right <= left for left, right in zip(curve_x, curve_x[1:])):
                raise ValueError("contrast-curve separation must be strictly increasing")
            if any(value <= 0 for value in curve_y):
                raise ValueError("contrast-curve limits must be positive")

    @property
    def iwa_mas(self) -> float:
        wavelength_m = self.wavelength_nm * 1e-9
        return self.iwa_lambda_over_d * wavelength_m / self.diameter_m * RAD_TO_MAS

    def contrast_limit_at(self, separation_mas: np.ndarray | float) -> np.ndarray:
        separation = np.asarray(separation_mas, dtype=float)
        if self.curve_separation_mas is None or self.curve_contrast_limit is None:
            return np.full_like(separation, self.contrast_floor, dtype=float)
        curve_x = np.asarray(self.curve_separation_mas, dtype=float)
        curve_y = np.asarray(self.curve_contrast_limit, dtype=float)
        return 10 ** np.interp(
            separation,
            curve_x,
            np.log10(curve_y),
            left=np.log10(curve_y[0]),
            right=np.log10(curve_y[-1]),
        )


def observable_draws(
    *,
    scenario: CoronagraphScenario,
    distance_pc: np.ndarray,
    semi_major_axis_au: np.ndarray,
    eccentricity: np.ndarray,
    inclination_rad: np.ndarray,
    argument_periapsis_rad: np.ndarray,
    mean_anomaly_rad: np.ndarray,
    planet_radius_earth: np.ndarray,
    geometric_albedo: np.ndarray,
) -> dict[str, np.ndarray]:
    """Evaluate sampled reflected-light accessibility for one scenario."""

    distance = np.asarray(distance_pc, dtype=float)
    radius, projected, phase = orbital_geometry(
        semi_major_axis_au,
        eccentricity,
        inclination_rad,
        argument_periapsis_rad,
        mean_anomaly_rad,
    )
    separation_mas = 1000 * projected / distance
    radius_au = np.asarray(planet_radius_earth, dtype=float) * EARTH_RADIUS_AU
    contrast = (
        np.asarray(geometric_albedo, dtype=float) * lambert_phase(phase) * (radius_au / radius) ** 2
    )
    contrast_limit = scenario.contrast_limit_at(separation_mas)
    accessible = (
        np.isfinite(separation_mas)
        & np.isfinite(contrast)
        & (distance > 0)
        & (separation_mas >= scenario.iwa_mas)
        & (contrast >= contrast_limit)
    )
    if scenario.owa_mas is not None:
        accessible &= separation_mas <= scenario.owa_mas
    return {
        "radius_au": radius,
        "projected_separation_mas": separation_mas,
        "phase_angle_rad": phase,
        "contrast": contrast,
        "contrast_limit": contrast_limit,
        "accessible": accessible,
    }


def deproject_minimum_mass(
    minimum_mass_earth: np.ndarray | float,
    inclination_rad: np.ndarray | float,
) -> np.ndarray:
    """Convert M sin(i) draws to true mass without relabelling the input."""

    minimum_mass = np.asarray(minimum_mass_earth, dtype=float)
    sine = np.sin(np.asarray(inclination_rad, dtype=float))
    if np.any(minimum_mass <= 0) or np.any(sine <= 0):
        raise ValueError("minimum mass and sin(inclination) must be positive")
    return minimum_mass / sine
