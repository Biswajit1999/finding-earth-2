"""Uncertainty bridges for the DR25 selection, reliability and candidate data.

The validated selection and reliability releases are immutable inputs.  This
module reconstructs their published parameter objects, preserves shared
coefficient correlations, and supplies the multiple-imputation inputs used by
the occurrence likelihood.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from astropy import constants as c
from numpy.typing import NDArray

from earth2.population.geometry import semimajor_axis_au, transit_probability
from earth2.population.occurrence import LogQuadrature, OccurrenceDomain
from earth2.population.reliability import ReliabilityDomain
from earth2.population.selection_surface import (
    DETECTION_FEATURE_NAMES,
    MES_FEATURE_NAMES,
    DetectionFit,
    MesCalibration,
    SelectionDomain,
    SelectionModel,
    _detection_features,
    _mes_features,
    phase_averaged_window_probability,
    raw_expected_mes,
    transit_duration_hours,
)
from earth2.population.smooth_reliability import (
    BASE_FEATURE_NAMES,
    DEFAULT_EXPERIMENT_WEIGHTS,
    EXPERIMENTS,
    JointReliabilityFit,
    _q_features,
    _sigmoid,
    _surface_features,
    _validate_weights,
)


@dataclass(frozen=True)
class SelectionExposure:
    """Effective stars and local coefficient derivatives at quadrature nodes."""

    effective_stars: np.ndarray
    gradient: np.ndarray
    coefficient_names: tuple[str, ...]
    covariance: np.ndarray
    fixed_at_boundary: np.ndarray

    def log_sensitivity(self) -> np.ndarray:
        if np.any(self.effective_stars <= 0):
            raise ValueError("Selection exposure must be positive before log linearization")
        return self.gradient / self.effective_stars[:, None]


@dataclass(frozen=True)
class ReliabilityDraws:
    """Correlated candidate probabilities under shared reliability coefficients."""

    false_alarm: np.ndarray
    total: np.ndarray
    supported: np.ndarray


@dataclass(frozen=True)
class CandidateImputations:
    """Multiple imputations of candidate validity and measured coordinates."""

    periods_days: np.ndarray
    radii_earth: np.ndarray
    included: np.ndarray
    reliability_probability: np.ndarray


def load_selection_model(path: str | Path) -> SelectionModel:
    """Reconstruct the validated selection model without changing its release file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    model = payload.get("model", payload)
    mes = model["mes_calibration"]
    pipeline = model["pipeline_including_window"]
    vetting = model["vetting_given_recovered"]
    if tuple(mes["feature_names"]) != MES_FEATURE_NAMES:
        raise ValueError("Released MES feature schema does not match this code")
    if any(
        tuple(component["feature_names"]) != DETECTION_FEATURE_NAMES
        for component in (pipeline, vetting)
    ):
        raise ValueError("Released detection feature schema does not match this code")
    node_match = re.match(r"^(\d+)-node", model["impact_parameter_marginalization"])
    if node_match is None:
        raise ValueError("Released impact-parameter quadrature contract is malformed")

    def detection(component: dict) -> DetectionFit:
        constraints = component["constraints"]
        return DetectionFit(
            coefficients=np.asarray(component["coefficients"], float),
            covariance=np.asarray(component["covariance"], float),
            l2_penalty=float(component["l2_penalty"]),
            training_rows=int(component["training_rows"]),
            metrics={key: float(value) for key, value in component["training_metrics"].items()},
            monotonic_mes=bool(constraints["nondecreasing_with_expected_mes"]),
            monotonic_window=bool(constraints["nondecreasing_with_window_probability"]),
        )

    return SelectionModel(
        domain=SelectionDomain(**model["domain"]),
        mes_calibration=MesCalibration(
            coefficients=np.asarray(mes["coefficients"], float),
            covariance=np.asarray(mes["covariance"], float),
            ridge_penalty=float(mes["ridge_penalty"]),
            training_rows=int(mes["training_rows"]),
            log_residual_rmse=float(mes["training_log_residual_rmse"]),
            log_residual_bias=float(mes["training_log_residual_bias"]),
            expected_mes_min=float(mes["training_expected_mes_range"][0]),
            expected_mes_max=float(mes["training_expected_mes_range"][1]),
        ),
        pipeline_including_window=detection(pipeline),
        vetting_given_recovered=detection(vetting),
        impact_quadrature_nodes=int(node_match.group(1)),
    )


def load_reliability_model(path: str | Path) -> JointReliabilityFit:
    """Reconstruct the validated smooth reliability fit from its JSON product."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    fit = payload.get("fit", payload)
    domain = ReliabilityDomain(**fit["domain"])
    theta = np.asarray(fit["coefficients"], float)
    covariance = np.asarray(fit["covariance"], float)
    expected_names = tuple(f"f_{name}" for name in BASE_FEATURE_NAMES) + tuple(
        f"q_{name}" for name in BASE_FEATURE_NAMES
    )
    if fit["experiment_aware"]:
        expected_names += tuple(f"q_offset_{name.lower()}" for name in EXPERIMENTS[1:])
    if tuple(fit["coefficient_names"]) != expected_names:
        raise ValueError("Released reliability feature schema does not match this code")
    return JointReliabilityFit(
        theta=theta,
        covariance=covariance,
        domain=domain,
        experiment_aware=bool(fit["experiment_aware"]),
        l2_penalty=float(fit["l2_penalty"]),
        converged=bool(fit["converged"]),
        iterations=int(fit["iterations"]),
        gradient_norm=float(fit["gradient_norm"]),
        objective=float(fit["objective"]),
        synthetic_rows=int(fit["synthetic_rows"]),
        observed_rows=int(fit["observed_rows"]),
        synthetic_metrics={
            key: float(value)
            for key, value in fit["training_metrics"]["false_alarm_experiment"].items()
        },
        observed_metrics={
            key: float(value) for key, value in fit["training_metrics"]["observed_tce"].items()
        },
    )


def selection_parameter_contract(
    model: SelectionModel,
) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
    names = (
        tuple(f"mes::{name}" for name in MES_FEATURE_NAMES)
        + tuple(f"pipeline::{name}" for name in DETECTION_FEATURE_NAMES)
        + tuple(f"vetting::{name}" for name in DETECTION_FEATURE_NAMES)
    )
    blocks = (
        model.mes_calibration.covariance,
        model.pipeline_including_window.covariance,
        model.vetting_given_recovered.covariance,
    )
    covariance = np.zeros((len(names), len(names)))
    cursor = 0
    for block in blocks:
        width = len(block)
        covariance[cursor : cursor + width, cursor : cursor + width] = block
        cursor += width
    fixed = np.zeros(len(names), bool)
    pipeline_offset = len(MES_FEATURE_NAMES)
    vetting_offset = pipeline_offset + len(DETECTION_FEATURE_NAMES)
    if model.pipeline_including_window.monotonic_mes:
        fixed[pipeline_offset + 1] = model.pipeline_including_window.coefficients[1] <= 1e-10
    if model.pipeline_including_window.monotonic_window:
        fixed[pipeline_offset + 3] = model.pipeline_including_window.coefficients[3] <= 1e-10
    if model.vetting_given_recovered.monotonic_mes:
        fixed[vetting_offset + 1] = model.vetting_given_recovered.coefficients[1] <= 1e-10
    covariance[fixed, :] = 0
    covariance[:, fixed] = 0
    return names, covariance, fixed


def evaluate_selection_exposure(
    model: SelectionModel,
    selected_stars: pd.DataFrame,
    quadrature: LogQuadrature,
    occurrence_domain: OccurrenceDomain,
    *,
    chunk_size: int = 4000,
) -> SelectionExposure:
    """Evaluate all targets and differentiate effective stars at each node.

    Derivatives are analytic first derivatives at the fitted coefficients.  The
    three released covariance blocks are treated as independent because the
    sequential calibration does not publish their cross-covariance.
    """
    quadrature.validate(occurrence_domain)
    required = {
        "kepid",
        "mass",
        "radius",
        "logg",
        "teff",
        "dataspan",
        "dutycycle",
        "rrmscdpp06p0",
        "cdppslplong",
        "cdppslpshrt",
    }
    missing = required - set(selected_stars.columns)
    if missing:
        raise ValueError(f"Selected stars are missing {sorted(missing)}")
    if selected_stars["kepid"].duplicated().any() or len(selected_stars) == 0:
        raise ValueError("Selected stellar denominator must be non-empty and unique")
    numeric = selected_stars[sorted(required - {"kepid"})].to_numpy(float)
    if (
        not np.isfinite(numeric).all()
        or selected_stars[["mass", "radius", "dataspan", "rrmscdpp06p0"]].le(0).any().any()
        or not selected_stars["dutycycle"].between(0, 1, inclusive="right").all()
        or chunk_size <= 0
    ):
        raise ValueError("Selected stellar denominator contains invalid physical inputs")
    periods = quadrature.periods_days[: quadrature.period_nodes]
    radii = quadrature.radii_earth[:: quadrature.period_nodes]
    if len(periods) != quadrature.period_nodes or len(radii) != quadrature.radius_nodes:
        raise ValueError("Quadrature tensor ordering is inconsistent")
    if (
        periods[0] < model.domain.period_min_days
        or periods[-1] > model.domain.period_max_days
        or radii[0] < model.domain.radius_min_earth
        or radii[-1] > model.domain.radius_max_earth
    ):
        raise ValueError("Occurrence quadrature exceeds the selection calibration domain")

    names, covariance, fixed = selection_parameter_contract(model)
    shape = (len(radii), len(periods))
    exposure = np.zeros(shape)
    gradient = np.zeros((*shape, len(names)))
    impact_nodes: NDArray[np.float64]
    impact_weights: NDArray[np.float64]
    impact_nodes, impact_weights = np.polynomial.legendre.leggauss(model.impact_quadrature_nodes)
    impact_nodes = (impact_nodes + 1) / 2
    impact_weights /= 2
    period_grid = periods[None, None, :]
    radius_grid = radii[None, :, None]
    mes_width = len(MES_FEATURE_NAMES)
    detection_width = len(DETECTION_FEATURE_NAMES)
    pipeline_slice = slice(mes_width, mes_width + detection_width)
    vetting_slice = slice(mes_width + detection_width, len(names))

    for start in range(0, len(selected_stars), chunk_size):
        stars = selected_stars.iloc[start : start + chunk_size]
        values = {
            name: stars[name].to_numpy(float)[:, None, None] for name in required if name != "kepid"
        }
        stellar_radius = values["radius"]
        semimajor = semimajor_axis_au(period_grid, values["mass"])
        stellar_radius_au = stellar_radius * c.R_sun.value / c.au.value
        scaled_axis = semimajor / stellar_radius_au
        radius_ratio = radius_grid * c.R_earth.value / (stellar_radius * c.R_sun.value)
        geometry = transit_probability(stellar_radius, radius_grid, semimajor)
        window = phase_averaged_window_probability(
            values["dataspan"], values["dutycycle"], period_grid
        )
        for impact, weight in zip(impact_nodes, impact_weights):
            duration = transit_duration_hours(period_grid, radius_ratio, impact, scaled_axis)
            raw_mes = raw_expected_mes(
                period_grid,
                radius_ratio,
                duration,
                values["dataspan"],
                values["dutycycle"],
                values["rrmscdpp06p0"],
                values["cdppslplong"],
                values["cdppslpshrt"],
            )
            mes_features = _mes_features(
                raw_mes,
                period_grid,
                duration,
                values["dutycycle"],
                values["dataspan"],
                values["cdppslplong"],
                values["cdppslpshrt"],
                stellar_radius,
                values["logg"],
                values["teff"],
            )
            expected_mes = np.exp(mes_features @ model.mes_calibration.coefficients).reshape(
                geometry.shape
            )
            detection_features = _detection_features(
                expected_mes,
                period_grid + np.zeros_like(geometry),
                window + np.zeros_like(geometry),
                model.domain,
            ).reshape((*geometry.shape, detection_width))
            pipeline = model.pipeline_including_window.predict(
                detection_features.reshape(-1, detection_width)
            ).reshape(geometry.shape)
            vetting = model.vetting_given_recovered.predict(
                detection_features.reshape(-1, detection_width)
            ).reshape(geometry.shape)
            weighted_geometry = weight * geometry
            exposure += (weighted_geometry * pipeline * vetting).sum(axis=0)
            pipeline_factor = weighted_geometry * vetting * pipeline * (1 - pipeline)
            vetting_factor = weighted_geometry * pipeline * vetting * (1 - vetting)
            gradient[:, :, pipeline_slice] += np.einsum(
                "srp,srpf->rpf", pipeline_factor, detection_features, optimize=True
            )
            gradient[:, :, vetting_slice] += np.einsum(
                "srp,srpf->rpf", vetting_factor, detection_features, optimize=True
            )
            log_mes_factor = (
                weighted_geometry
                * pipeline
                * vetting
                * (
                    (1 - pipeline) * model.pipeline_including_window.coefficients[1]
                    + (1 - vetting) * model.vetting_given_recovered.coefficients[1]
                )
            )
            gradient[:, :, :mes_width] += np.einsum(
                "srp,srpf->rpf",
                log_mes_factor,
                mes_features.reshape((*geometry.shape, mes_width)),
                optimize=True,
            )

    result = SelectionExposure(
        effective_stars=exposure.ravel(),
        gradient=gradient.reshape(-1, len(names)),
        coefficient_names=names,
        covariance=covariance,
        fixed_at_boundary=fixed,
    )
    if (
        not np.isfinite(result.effective_stars).all()
        or not np.isfinite(result.gradient).all()
        or np.any(result.effective_stars <= 0)
    ):
        raise RuntimeError("Selection exposure or derivative is non-finite/non-positive")
    return result


def draw_selection_deltas(
    model: SelectionModel,
    draws: int,
    *,
    seed: int = 271828,
) -> np.ndarray:
    """Draw local coefficient perturbations with released monotonic bounds."""
    if draws <= 0:
        raise ValueError("Selection draw count must be positive")
    _, covariance, fixed = selection_parameter_contract(model)
    mean = np.r_[
        model.mes_calibration.coefficients,
        model.pipeline_including_window.coefficients,
        model.vetting_given_recovered.coefficients,
    ]
    constrained = np.zeros(len(mean), bool)
    pipeline_offset = len(MES_FEATURE_NAMES)
    vetting_offset = pipeline_offset + len(DETECTION_FEATURE_NAMES)
    constrained[pipeline_offset + 1] = model.pipeline_including_window.monotonic_mes
    constrained[pipeline_offset + 3] = model.pipeline_including_window.monotonic_window
    constrained[vetting_offset + 1] = model.vetting_given_recovered.monotonic_mes
    constrained &= ~fixed
    rng = np.random.default_rng(seed)
    accepted: list[np.ndarray] = []
    remaining = draws
    attempts = 0
    while remaining and attempts < 100:
        batch = rng.multivariate_normal(
            np.zeros(len(mean)), covariance, size=max(remaining * 2, 64)
        )
        valid = np.all(mean[None, constrained] + batch[:, constrained] >= 0, axis=1)
        accepted.append(batch[valid][:remaining])
        remaining -= min(remaining, int(valid.sum()))
        attempts += 1
    if remaining:
        raise RuntimeError("Could not draw enough bound-respecting selection coefficients")
    result = np.vstack(accepted)[:draws]
    result[:, fixed] = 0
    return result


def perturb_selection_exposure(
    exposure: SelectionExposure,
    coefficient_deltas,
) -> np.ndarray:
    """Apply a positive local log-linear map to shared selection perturbations."""
    deltas = np.asarray(coefficient_deltas, float)
    if deltas.ndim != 2 or deltas.shape[1] != len(exposure.coefficient_names):
        raise ValueError("Selection coefficient draws do not match the derivative schema")
    log_change = deltas @ exposure.log_sensitivity().T
    return exposure.effective_stars[None, :] * np.exp(np.clip(log_change, -20, 20))


def draw_candidate_reliability(
    fit: JointReliabilityFit,
    candidates: pd.DataFrame,
    draws: int,
    *,
    seed: int = 8675309,
) -> ReliabilityDraws:
    """Draw all candidate reliabilities from each shared coefficient draw."""
    if fit.covariance is None:
        raise ValueError("Candidate reliability draws require coefficient covariance")
    if draws <= 0:
        raise ValueError("Candidate reliability draw count must be positive")
    required = {"observed_tce_period_days", "observed_tce_mes", "koi_prad", "fpp_prob"}
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(f"Candidate table is missing {sorted(missing)}")
    evaluation = pd.DataFrame(
        {
            "period": candidates["observed_tce_period_days"],
            "MES": candidates["observed_tce_mes"],
            "Rp": candidates["koi_prad"],
        },
        index=candidates.index,
    )
    supported = (fit.domain.mask(evaluation) & candidates["fpp_prob"].notna()).to_numpy(bool)
    false_alarm = np.full((draws, len(candidates)), np.nan)
    total = np.full_like(false_alarm, np.nan)
    if supported.any():
        inside = evaluation.loc[supported]
        rng = np.random.default_rng(seed)
        theta = rng.multivariate_normal(fit.theta, fit.covariance, size=draws)
        x = _surface_features(inside, fit.domain)
        f_draws = _sigmoid(theta[:, : len(BASE_FEATURE_NAMES)] @ x.T)
        q_draws = np.zeros_like(f_draws)
        for experiment, weight in _validate_weights(DEFAULT_EXPERIMENT_WEIGHTS).items():
            experiment_frame = inside.copy()
            experiment_frame["experiment"] = experiment
            z = _q_features(experiment_frame, fit.domain, experiment_aware=fit.experiment_aware)
            q_draws += weight * _sigmoid(theta[:, len(BASE_FEATURE_NAMES) :] @ z.T)
        effectiveness = q_draws + f_draws * (1 - q_draws)
        reliability = (effectiveness - f_draws) / (effectiveness * (1 - f_draws))
        false_alarm[:, supported] = reliability
        total[:, supported] = (
            reliability * (1 - candidates.loc[supported, "fpp_prob"].to_numpy(float))[None, :]
        )
    return ReliabilityDraws(false_alarm=false_alarm, total=total, supported=supported)


def _asymmetric_normal_draws(
    centre: np.ndarray,
    upper_error: np.ndarray,
    lower_error: np.ndarray,
    draws: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if (
        not np.isfinite(centre).all()
        or not np.isfinite(upper_error).all()
        or not np.isfinite(lower_error).all()
        or np.any(centre <= 0)
        or np.any(upper_error < 0)
        or np.any(lower_error < 0)
    ):
        raise ValueError("Asymmetric measurement inputs are invalid")
    normal = rng.standard_normal((draws, len(centre)))
    scale = np.where(normal >= 0, upper_error[None, :], lower_error[None, :])
    sampled = centre[None, :] + normal * scale
    retry = sampled <= 0
    attempts = 0
    while retry.any() and attempts < 100:
        replacement = rng.standard_normal(int(retry.sum()))
        candidate_index = np.where(retry)[1]
        replacement_scale = np.where(
            replacement >= 0,
            upper_error[candidate_index],
            lower_error[candidate_index],
        )
        sampled[retry] = centre[candidate_index] + replacement * replacement_scale
        retry = sampled <= 0
        attempts += 1
    if retry.any():
        raise RuntimeError("Could not draw positive candidate measurements")
    return sampled


def draw_candidate_imputations(
    candidates: pd.DataFrame,
    reliability: ReliabilityDraws,
    domain: OccurrenceDomain,
    *,
    unsupported_false_alarm_reliability: float,
    radius_error_scale: float = 1.0,
    seed: int = 161803,
) -> CandidateImputations:
    """Draw validity and asymmetric period/radius measurements for every KOI."""
    required = {
        "koi_period",
        "koi_period_err1",
        "koi_period_err2",
        "koi_prad",
        "koi_prad_err1",
        "koi_prad_err2",
        "fpp_prob",
    }
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(f"Candidate measurement table is missing {sorted(missing)}")
    if (
        reliability.total.ndim != 2
        or reliability.total.shape[1] != len(candidates)
        or reliability.supported.shape != (len(candidates),)
        or not 0 <= unsupported_false_alarm_reliability <= 1
        or not np.isfinite(radius_error_scale)
        or radius_error_scale < 0
    ):
        raise ValueError("Candidate imputation contract is invalid")
    draws = reliability.total.shape[0]
    probability = reliability.total.copy()
    unsupported = ~reliability.supported
    probability[:, unsupported] = (
        unsupported_false_alarm_reliability
        * (1 - candidates.loc[unsupported, "fpp_prob"].to_numpy(float))[None, :]
    )
    if not np.isfinite(probability).all() or np.any((probability < 0) | (probability > 1)):
        raise ValueError("Candidate reliability probabilities must remain inside [0,1]")
    rng = np.random.default_rng(seed)
    periods = _asymmetric_normal_draws(
        candidates["koi_period"].to_numpy(float),
        candidates["koi_period_err1"].to_numpy(float),
        np.abs(candidates["koi_period_err2"].to_numpy(float)),
        draws,
        rng,
    )
    radii = _asymmetric_normal_draws(
        candidates["koi_prad"].to_numpy(float),
        radius_error_scale * candidates["koi_prad_err1"].to_numpy(float),
        radius_error_scale * np.abs(candidates["koi_prad_err2"].to_numpy(float)),
        draws,
        rng,
    )
    included = (rng.random(probability.shape) < probability) & domain.mask(periods, radii)
    return CandidateImputations(periods, radii, included, probability)
