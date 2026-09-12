"""Time-dependent habitable-zone inference on a pinned MIST grid.

The stellar history is interpolated from MIST v1.2 phase-0 isochrones and
anchored to the sampled present-day catalogue luminosity.  Kopparapu et al.
(2013, including its erratum) supplies three deliberately separate climate
boundary prescriptions.  These calculations describe incident-flux exposure;
they do not establish surface conditions or habitability.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from earth2.habitability.hz import HZ_TEFF_MAX, HZ_TEFF_MIN, seff_boundary

CLIMATE_PRESCRIPTIONS: dict[str, tuple[str, str]] = {
    "kopparapu_conservative": ("runaway_greenhouse", "maximum_greenhouse"),
    "kopparapu_moist_greenhouse": ("moist_greenhouse", "maximum_greenhouse"),
    "kopparapu_optimistic_empirical": ("recent_venus", "early_mars"),
}


@dataclass(frozen=True)
class EvolutionConfig:
    """Numerical and evidence-support contract for one planet."""

    draws: int = 256
    history_steps: int = 72
    minimum_age_gyr: float = 0.1
    maximum_relative_age_error: float = 0.75
    maximum_age_interval_gyr: float = 6.0
    minimum_supported_fraction: float = 0.5

    def __post_init__(self) -> None:
        if self.draws < 64:
            raise ValueError("draws must be at least 64")
        if self.history_steps < 16:
            raise ValueError("history_steps must be at least 16")
        if self.minimum_age_gyr <= 0:
            raise ValueError("minimum_age_gyr must be positive")
        if not 0 < self.minimum_supported_fraction <= 1:
            raise ValueError("minimum_supported_fraction must lie in (0, 1]")


class MISTMainSequenceGrid:
    """Trilinear interpolator over the committed MIST phase-0 grid."""

    def __init__(self, frame: pd.DataFrame):
        required = {
            "feh",
            "log10_age_years",
            "initial_mass_solar",
            "log10_luminosity_solar",
            "log10_teff_kelvin",
        }
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"MIST grid is missing columns: {sorted(missing)}")
        if frame.duplicated(["feh", "log10_age_years", "initial_mass_solar"]).any():
            raise ValueError("MIST grid contains duplicate interpolation cells")

        self.feh = np.sort(frame["feh"].unique().astype(float))
        self.log_age = np.sort(frame["log10_age_years"].unique().astype(float))
        self.mass = np.sort(frame["initial_mass_solar"].unique().astype(float))
        shape = (len(self.feh), len(self.log_age), len(self.mass))
        luminosity = np.full(shape, np.nan)
        temperature = np.full(shape, np.nan)
        feh_index = {value: index for index, value in enumerate(self.feh)}
        age_index = {value: index for index, value in enumerate(self.log_age)}
        mass_index = {value: index for index, value in enumerate(self.mass)}
        for row in frame.itertuples(index=False):
            key = (
                feh_index[float(row.feh)],
                age_index[float(row.log10_age_years)],
                mass_index[float(row.initial_mass_solar)],
            )
            luminosity[key] = float(row.log10_luminosity_solar)
            temperature[key] = float(row.log10_teff_kelvin)
        axes = (self.feh, self.log_age, self.mass)
        self._luminosity = RegularGridInterpolator(
            axes, luminosity, bounds_error=False, fill_value=np.nan
        )
        self._temperature = RegularGridInterpolator(
            axes, temperature, bounds_error=False, fill_value=np.nan
        )

    @classmethod
    def from_csv(cls, path: str | Path) -> MISTMainSequenceGrid:
        return cls(pd.read_csv(path))

    def interpolate(
        self,
        *,
        age_gyr: np.ndarray | float,
        mass_solar: np.ndarray | float,
        feh: np.ndarray | float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return log10 luminosity and log10 effective temperature."""

        age, mass, metallicity = np.broadcast_arrays(
            np.asarray(age_gyr, dtype=float),
            np.asarray(mass_solar, dtype=float),
            np.asarray(feh, dtype=float),
        )
        with np.errstate(divide="ignore", invalid="ignore"):
            log_age = np.log10(age * 1e9)
        points = np.column_stack([metallicity.ravel(), log_age.ravel(), mass.ravel()])
        log_luminosity = self._luminosity(points).reshape(age.shape)
        log_temperature = self._temperature(points).reshape(age.shape)
        valid = np.isfinite(age) & (age > 0) & np.isfinite(mass) & np.isfinite(metallicity)
        return (
            np.where(valid, log_luminosity, np.nan),
            np.where(valid, log_temperature, np.nan),
        )


def _draw_split_normal(
    rng: np.random.Generator,
    centre: float,
    error_minus: float,
    error_plus: float,
    draws: int,
) -> np.ndarray:
    z = rng.normal(size=draws)
    lower = abs(float(error_minus))
    upper = abs(float(error_plus))
    return float(centre) + np.where(z < 0, z * lower, z * upper)


def _quantiles(values: np.ndarray) -> dict[str, float | None]:
    finite = values[np.isfinite(values)]
    if not finite.size:
        return {"p16": None, "p50": None, "p84": None}
    p16, p50, p84 = np.quantile(finite, [0.16, 0.5, 0.84])
    return {"p16": float(p16), "p50": float(p50), "p84": float(p84)}


def _undetermined(reason: str, *, draws: int, age_precision_status: str) -> dict[str, Any]:
    return {
        "label": "MODEL-INFERRED",
        "status": "undetermined",
        "reason": reason,
        "draws_requested": draws,
        "draws_supported": 0,
        "supported_fraction": 0.0,
        "age_precision_status": age_precision_status,
        "climate_prescriptions": {},
        "model_agreement": None,
        "boundary_sensitivity": None,
        "classification_robustness": "undetermined",
    }


def infer_continuous_hz(
    grid: MISTMainSequenceGrid,
    *,
    age_gyr: float,
    age_error_minus: float,
    age_error_plus: float,
    mass_solar: float,
    mass_error_minus: float,
    mass_error_plus: float,
    feh: float,
    feh_error_minus: float,
    feh_error_plus: float,
    log_luminosity_solar: float,
    log_luminosity_error_minus: float,
    log_luminosity_error_plus: float,
    semimajor_axis_au: float,
    semimajor_axis_error_minus: float,
    semimajor_axis_error_plus: float,
    seed: int = 20260912,
    config: EvolutionConfig | None = None,
) -> dict[str, Any]:
    """Infer present and lifetime HZ exposure for one sufficiently constrained system.

    The MIST history starts at 0.1 Gyr.  ``tau_HZ`` integrates only supported
    phase-0 history, while ``f_CHZ`` divides by the sampled stellar age so the
    unavailable pre-0.1-Gyr interval is never silently counted as habitable.
    """

    cfg = config or EvolutionConfig()
    values = np.asarray(
        [
            age_gyr,
            age_error_minus,
            age_error_plus,
            mass_solar,
            mass_error_minus,
            mass_error_plus,
            feh,
            feh_error_minus,
            feh_error_plus,
            log_luminosity_solar,
            log_luminosity_error_minus,
            log_luminosity_error_plus,
            semimajor_axis_au,
            semimajor_axis_error_minus,
            semimajor_axis_error_plus,
        ],
        dtype=float,
    )
    if not np.isfinite(values).all():
        return _undetermined(
            "missing_required_measurement_or_uncertainty",
            draws=cfg.draws,
            age_precision_status="missing",
        )
    if age_gyr <= cfg.minimum_age_gyr or mass_solar <= 0 or semimajor_axis_au <= 0:
        return _undetermined(
            "nonpositive_or_premain_sequence_input",
            draws=cfg.draws,
            age_precision_status="invalid",
        )

    relative_age_error = max(abs(age_error_minus), abs(age_error_plus)) / age_gyr
    age_interval = abs(age_error_minus) + abs(age_error_plus)
    if (
        relative_age_error > cfg.maximum_relative_age_error
        or age_interval > cfg.maximum_age_interval_gyr
    ):
        return _undetermined(
            "stellar_age_effectively_unconstrained",
            draws=cfg.draws,
            age_precision_status="too_broad",
        )

    rng = np.random.default_rng(seed)
    age = _draw_split_normal(rng, age_gyr, age_error_minus, age_error_plus, cfg.draws)
    mass = _draw_split_normal(rng, mass_solar, mass_error_minus, mass_error_plus, cfg.draws)
    metallicity = _draw_split_normal(rng, feh, feh_error_minus, feh_error_plus, cfg.draws)
    current_log_luminosity = _draw_split_normal(
        rng,
        log_luminosity_solar,
        log_luminosity_error_minus,
        log_luminosity_error_plus,
        cfg.draws,
    )
    orbit = _draw_split_normal(
        rng,
        semimajor_axis_au,
        semimajor_axis_error_minus,
        semimajor_axis_error_plus,
        cfg.draws,
    )
    input_valid = (
        np.isfinite(age)
        & (age > cfg.minimum_age_gyr)
        & np.isfinite(mass)
        & (mass > 0)
        & np.isfinite(metallicity)
        & np.isfinite(current_log_luminosity)
        & np.isfinite(orbit)
        & (orbit > 0)
    )
    model_log_luminosity_now, model_log_temperature_now = grid.interpolate(
        age_gyr=age,
        mass_solar=mass,
        feh=metallicity,
    )
    supported = (
        input_valid & np.isfinite(model_log_luminosity_now) & np.isfinite(model_log_temperature_now)
    )
    supported_fraction = float(np.mean(supported))
    if supported_fraction < cfg.minimum_supported_fraction:
        result = _undetermined(
            "insufficient_mist_main_sequence_support",
            draws=cfg.draws,
            age_precision_status="supported",
        )
        result["draws_supported"] = int(supported.sum())
        result["supported_fraction"] = supported_fraction
        return result

    age = age[supported]
    mass = mass[supported]
    metallicity = metallicity[supported]
    current_log_luminosity = current_log_luminosity[supported]
    orbit = orbit[supported]
    model_log_luminosity_now = model_log_luminosity_now[supported]

    fraction = np.linspace(0, 1, cfg.history_steps)
    history_age = cfg.minimum_age_gyr + fraction[None, :] * (age[:, None] - cfg.minimum_age_gyr)
    history_mass = np.broadcast_to(mass[:, None], history_age.shape)
    history_feh = np.broadcast_to(metallicity[:, None], history_age.shape)
    model_log_luminosity, model_log_temperature = grid.interpolate(
        age_gyr=history_age,
        mass_solar=history_mass,
        feh=history_feh,
    )
    luminosity_offset = current_log_luminosity - model_log_luminosity_now
    anchored_luminosity = 10 ** (model_log_luminosity + luminosity_offset[:, None])
    temperature = 10**model_log_temperature
    insolation = anchored_luminosity / orbit[:, None] ** 2
    complete_history = (
        np.isfinite(insolation).all(axis=1)
        & np.isfinite(temperature).all(axis=1)
        & (temperature >= HZ_TEFF_MIN).all(axis=1)
        & (temperature <= HZ_TEFF_MAX).all(axis=1)
    )
    complete_fraction = float(complete_history.sum() / cfg.draws)
    if complete_fraction < cfg.minimum_supported_fraction:
        result = _undetermined(
            "insufficient_continuous_track_support",
            draws=cfg.draws,
            age_precision_status="supported",
        )
        result["draws_supported"] = int(complete_history.sum())
        result["supported_fraction"] = complete_fraction
        return result

    age = age[complete_history]
    current_log_luminosity = current_log_luminosity[complete_history]
    luminosity_offset = luminosity_offset[complete_history]
    model_log_luminosity = model_log_luminosity[complete_history]
    history_age = history_age[complete_history]
    temperature = temperature[complete_history]
    insolation = insolation[complete_history]

    prescriptions: dict[str, dict[str, Any]] = {}
    current_probabilities: list[float] = []
    for name, (inner_name, outer_name) in CLIMATE_PRESCRIPTIONS.items():
        inner = seff_boundary(temperature, inner_name)
        outer = seff_boundary(temperature, outer_name)
        finite_history = np.isfinite(insolation) & np.isfinite(inner) & np.isfinite(outer)
        in_hz = finite_history & (insolation <= inner) & (insolation >= outer)
        complete = finite_history.all(axis=1)
        tau = np.full(len(age), np.nan)
        if complete.any():
            indicator = in_hz[complete].astype(float)
            intervals = np.diff(history_age[complete], axis=1)
            tau[complete] = np.sum(
                0.5 * (indicator[:, :-1] + indicator[:, 1:]) * intervals,
                axis=1,
            )
        fraction_hz = tau / age
        current_supported = finite_history[:, -1]
        p_current = (
            float(np.mean(in_hz[current_supported, -1])) if current_supported.any() else np.nan
        )
        current_probabilities.append(p_current)
        prescriptions[name] = {
            "inner_boundary": inner_name,
            "outer_boundary": outer_name,
            "p_current_hz": None if not np.isfinite(p_current) else p_current,
            "tau_hz_gyr": _quantiles(tau),
            "f_chz": _quantiles(fraction_hz),
            "complete_history_draws": int(complete.sum()),
        }

    finite_probabilities = np.asarray(current_probabilities)
    finite_probabilities = finite_probabilities[np.isfinite(finite_probabilities)]
    if finite_probabilities.size:
        sensitivity = float(finite_probabilities.max() - finite_probabilities.min())
        agreement = float(1 - sensitivity)
        if np.all(finite_probabilities >= 0.84):
            robustness = "robustly_inside_across_prescriptions"
        elif np.all(finite_probabilities <= 0.16):
            robustness = "robustly_outside_across_prescriptions"
        else:
            robustness = "boundary_or_model_sensitive"
    else:
        sensitivity = np.nan
        agreement = np.nan
        robustness = "undetermined"

    anchored_present = model_log_luminosity[:, -1] + luminosity_offset
    anchoring_error = float(np.nanmax(np.abs(anchored_present - current_log_luminosity)))
    return {
        "label": "MODEL-INFERRED",
        "status": "inferred",
        "reason": None,
        "draws_requested": cfg.draws,
        "draws_supported": int(complete_history.sum()),
        "supported_fraction": complete_fraction,
        "age_precision_status": "supported",
        "history_start_gyr": cfg.minimum_age_gyr,
        "history_steps": cfg.history_steps,
        "luminosity_anchor_max_abs_dex": anchoring_error,
        "climate_prescriptions": prescriptions,
        "model_agreement": None if not np.isfinite(agreement) else agreement,
        "boundary_sensitivity": None if not np.isfinite(sensitivity) else sensitivity,
        "classification_robustness": robustness,
    }
