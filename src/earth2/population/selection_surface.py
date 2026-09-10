"""Survey-wide DR25 selection surface calibrated by on-target injections.

The model predicts the combined pipeline-plus-window recovery measured by INJ1,
then applies a separate conditional Robovetter completeness model and transit
geometry. It uses every selected target when constructing survey exposure.
Candidate reliability is not a detection factor and is absent from this module.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from astropy import constants as c
from scipy.optimize import minimize
from scipy.stats import binom

from earth2.population.geometry import semimajor_axis_au, transit_probability
from earth2.population.smooth_reliability import binary_metrics

MES_FEATURE_NAMES = (
    "intercept",
    "log_raw_mes",
    "log_period",
    "log_duration",
    "duty_cycle",
    "log_dataspan",
    "cdpp_slope_long",
    "cdpp_slope_short",
    "log_stellar_radius",
    "stellar_logg",
    "stellar_teff_offset_1000k",
)
DETECTION_FEATURE_NAMES = (
    "intercept",
    "log_mes_over_7",
    "log_period_scaled",
    "window_logit_scaled",
    "log_period_scaled_squared",
)


@dataclass(frozen=True)
class SelectionDomain:
    period_min_days: float = 50.0
    period_max_days: float = 500.0
    radius_min_earth: float = 0.5
    radius_max_earth: float = 2.0

    def mask(self, frame: pd.DataFrame) -> pd.Series:
        required = {"i_period", "injected_radius_earth"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Injection frame is missing {sorted(missing)}")
        bounds = np.asarray(list(asdict(self).values()), float)
        if (
            not np.isfinite(bounds).all()
            or np.any(bounds <= 0)
            or self.period_min_days >= self.period_max_days
            or self.radius_min_earth >= self.radius_max_earth
        ):
            raise ValueError("Selection domain is invalid")
        return frame["i_period"].between(self.period_min_days, self.period_max_days) & frame[
            "injected_radius_earth"
        ].between(self.radius_min_earth, self.radius_max_earth)


def transit_duration_hours(period_days, radius_ratio, impact, a_over_rstar) -> np.ndarray:
    """Circular first-to-fourth-contact duration for a transiting orientation."""
    period, ratio, b, scaled_axis = np.broadcast_arrays(
        np.asarray(period_days, float),
        np.asarray(radius_ratio, float),
        np.asarray(impact, float),
        np.asarray(a_over_rstar, float),
    )
    if (
        not all(np.isfinite(value).all() for value in (period, ratio, b, scaled_axis))
        or np.any(period <= 0)
        or np.any(ratio < 0)
        or np.any((b < 0) | (b > 1))
        or np.any(scaled_axis <= 1)
    ):
        raise ValueError("Transit duration inputs are outside their physical domain")
    chord = np.sqrt(np.maximum((1 + ratio) ** 2 - b**2, 0))
    argument = chord / scaled_axis
    if np.any(argument > 1):
        raise ValueError("Transit chord exceeds the circular orbit")
    return period * 24 / np.pi * np.arcsin(argument)


def phase_averaged_window_probability(dataspan_days, duty_cycle, period_days) -> np.ndarray:
    """Probability of observing at least three transits over random orbital phase.

    The phase average mixes floor(dataspan/period) and the adjacent integer
    opportunity count. Each opportunity is observed independently with the
    target's DR25 duty cycle.
    """
    span, duty, period = np.broadcast_arrays(
        np.asarray(dataspan_days, float),
        np.asarray(duty_cycle, float),
        np.asarray(period_days, float),
    )
    if (
        not np.isfinite(span).all()
        or not np.isfinite(duty).all()
        or not np.isfinite(period).all()
        or np.any(span <= 0)
        or np.any((duty <= 0) | (duty > 1))
        or np.any(period <= 0)
    ):
        raise ValueError("Window inputs must be finite with positive spans/periods and 0<duty<=1")
    opportunities = span / period
    lower = np.floor(opportunities).astype(int)
    phase_fraction = opportunities - lower
    return (1 - phase_fraction) * binom.sf(2, lower, duty) + phase_fraction * binom.sf(
        2, lower + 1, duty
    )


def raw_expected_mes(
    period_days,
    radius_ratio,
    duration_hours,
    dataspan_days,
    duty_cycle,
    cdpp_6hr_ppm,
    cdpp_slope_long,
    cdpp_slope_short,
) -> np.ndarray:
    """Transparent six-hour-CDPP signal-to-noise approximation before calibration."""
    period, ratio, duration, span, duty, cdpp, slope_long, slope_short = np.broadcast_arrays(
        *[
            np.asarray(value, float)
            for value in (
                period_days,
                radius_ratio,
                duration_hours,
                dataspan_days,
                duty_cycle,
                cdpp_6hr_ppm,
                cdpp_slope_long,
                cdpp_slope_short,
            )
        ]
    )
    if (
        not all(
            np.isfinite(value).all()
            for value in (period, ratio, duration, span, duty, cdpp, slope_long, slope_short)
        )
        or np.any(period <= 0)
        or np.any(ratio <= 0)
        or np.any(duration <= 0)
        or np.any(span <= 0)
        or np.any((duty <= 0) | (duty > 1))
        or np.any(cdpp <= 0)
    ):
        raise ValueError("MES inputs are outside their calibrated physical domain")
    slope = np.where(duration >= 6, slope_long, slope_short)
    duration_noise = cdpp * (duration / 6) ** slope
    expected_observed_transits = span * duty / period
    return ratio**2 * 1_000_000 / duration_noise * np.sqrt(expected_observed_transits)


def _mes_features(
    raw_mes,
    period_days,
    duration_hours,
    duty_cycle,
    dataspan_days,
    cdpp_slope_long,
    cdpp_slope_short,
    stellar_radius_solar,
    stellar_logg,
    stellar_teff,
) -> np.ndarray:
    values = np.broadcast_arrays(
        *[
            np.asarray(value, float)
            for value in (
                raw_mes,
                period_days,
                duration_hours,
                duty_cycle,
                dataspan_days,
                cdpp_slope_long,
                cdpp_slope_short,
                stellar_radius_solar,
                stellar_logg,
                stellar_teff,
            )
        ]
    )
    raw, period, duration, duty, span, slope_long, slope_short, radius, logg, teff = values
    if (
        not all(np.isfinite(value).all() for value in values)
        or np.any(raw <= 0)
        or np.any(period <= 0)
        or np.any(duration <= 0)
        or np.any(span <= 0)
        or np.any(radius <= 0)
    ):
        raise ValueError("MES calibration features must be finite and positive where required")
    return np.column_stack(
        [
            np.ones(raw.size),
            np.log(raw).ravel(),
            np.log(period).ravel(),
            np.log(duration).ravel(),
            duty.ravel(),
            np.log(span).ravel(),
            slope_long.ravel(),
            slope_short.ravel(),
            np.log(radius).ravel(),
            logg.ravel(),
            ((teff - 5500) / 1000).ravel(),
        ]
    )


@dataclass(frozen=True)
class MesCalibration:
    coefficients: np.ndarray
    covariance: np.ndarray
    ridge_penalty: float
    training_rows: int
    log_residual_rmse: float
    log_residual_bias: float
    expected_mes_min: float
    expected_mes_max: float

    def predict(
        self,
        raw_mes,
        period_days,
        duration_hours,
        duty_cycle,
        dataspan_days,
        cdpp_slope_long,
        cdpp_slope_short,
        stellar_radius_solar,
        stellar_logg,
        stellar_teff,
    ) -> np.ndarray:
        shape = np.broadcast(
            np.asarray(raw_mes), np.asarray(period_days), np.asarray(duration_hours)
        ).shape
        features = _mes_features(
            raw_mes,
            period_days,
            duration_hours,
            duty_cycle,
            dataspan_days,
            cdpp_slope_long,
            cdpp_slope_short,
            stellar_radius_solar,
            stellar_logg,
            stellar_teff,
        )
        return np.exp(features @ self.coefficients).reshape(shape)

    def to_dict(self) -> dict:
        return {
            "feature_names": list(MES_FEATURE_NAMES),
            "coefficients": self.coefficients.tolist(),
            "covariance": self.covariance.tolist(),
            "ridge_penalty": self.ridge_penalty,
            "training_rows": self.training_rows,
            "training_log_residual_rmse": self.log_residual_rmse,
            "training_log_residual_bias": self.log_residual_bias,
            "training_expected_mes_range": [self.expected_mes_min, self.expected_mes_max],
        }


@dataclass(frozen=True)
class DetectionFit:
    coefficients: np.ndarray
    covariance: np.ndarray
    l2_penalty: float
    training_rows: int
    metrics: dict[str, float]
    monotonic_mes: bool
    monotonic_window: bool

    def predict(self, features: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-np.clip(features @ self.coefficients, -35, 35)))

    def to_dict(self) -> dict:
        return {
            "feature_names": list(DETECTION_FEATURE_NAMES),
            "coefficients": self.coefficients.tolist(),
            "covariance": self.covariance.tolist(),
            "l2_penalty": self.l2_penalty,
            "training_rows": self.training_rows,
            "training_metrics": self.metrics,
            "constraints": {
                "nondecreasing_with_expected_mes": self.monotonic_mes,
                "nondecreasing_with_window_probability": self.monotonic_window,
            },
            "covariance_interpretation": (
                "Local inverse-Hessian approximation conditional on this model family; "
                "draws for constrained coefficients must respect their fitted bounds"
            ),
        }


@dataclass(frozen=True)
class SelectionModel:
    domain: SelectionDomain
    mes_calibration: MesCalibration
    pipeline_including_window: DetectionFit
    vetting_given_recovered: DetectionFit
    impact_quadrature_nodes: int = 5

    def to_dict(self) -> dict:
        return {
            "label": "MODEL-INFERRED",
            "domain": asdict(self.domain),
            "mes_calibration": self.mes_calibration.to_dict(),
            "pipeline_including_window": self.pipeline_including_window.to_dict(),
            "vetting_given_recovered": self.vetting_given_recovered.to_dict(),
            "impact_parameter_marginalization": (
                f"{self.impact_quadrature_nodes}-node Gauss-Legendre integral over b in [0,1]"
            ),
            "probability_contract": (
                "total selection = centre-crossing geometry × INJ1-calibrated pipeline including "
                "window × Robovetter PC probability conditional on recovery"
            ),
        }


def _injection_physics(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    required = {
        "i_period",
        "i_ror",
        "i_b",
        "i_dor",
        "dataspan",
        "dutycycle",
        "rrmscdpp06p0",
        "cdppslplong",
        "cdppslpshrt",
        "radius",
        "logg",
        "teff",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Joined injection frame is missing {sorted(missing)}")
    period = frame["i_period"].to_numpy(float)
    duration = transit_duration_hours(period, frame["i_ror"], frame["i_b"], frame["i_dor"])
    raw_mes = raw_expected_mes(
        period,
        frame["i_ror"],
        duration,
        frame["dataspan"],
        frame["dutycycle"],
        frame["rrmscdpp06p0"],
        frame["cdppslplong"],
        frame["cdppslpshrt"],
    )
    window = phase_averaged_window_probability(frame["dataspan"], frame["dutycycle"], period)
    return {"period": period, "duration": duration, "raw_mes": raw_mes, "window": window}


def fit_mes_calibration(
    frame: pd.DataFrame,
    physics: dict[str, np.ndarray],
    training_mask,
    *,
    ridge_penalty: float = 1e-3,
) -> MesCalibration:
    if not np.isfinite(ridge_penalty) or ridge_penalty < 0:
        raise ValueError("MES ridge penalty must be finite and non-negative")
    expected = frame["Expected_MES"].to_numpy(float)
    mask = np.asarray(training_mask, bool) & np.isfinite(expected) & (expected > 0)
    if mask.sum() < len(MES_FEATURE_NAMES) * 10:
        raise ValueError("Too few positive Expected_MES rows for calibration")
    features = _mes_features(
        physics["raw_mes"][mask],
        physics["period"][mask],
        physics["duration"][mask],
        frame.loc[mask, "dutycycle"],
        frame.loc[mask, "dataspan"],
        frame.loc[mask, "cdppslplong"],
        frame.loc[mask, "cdppslpshrt"],
        frame.loc[mask, "radius"],
        frame.loc[mask, "logg"],
        frame.loc[mask, "teff"],
    )
    target = np.log(expected[mask])
    penalty = np.diag(np.r_[0, np.repeat(ridge_penalty, features.shape[1] - 1)])
    normal = features.T @ features + penalty
    coefficients = np.linalg.solve(normal, features.T @ target)
    residual = target - features @ coefficients
    dof = max(1, len(target) - len(coefficients))
    covariance = np.linalg.pinv(normal) * float(residual @ residual / dof)
    return MesCalibration(
        coefficients=coefficients,
        covariance=covariance,
        ridge_penalty=ridge_penalty,
        training_rows=int(mask.sum()),
        log_residual_rmse=float(np.sqrt(np.mean(residual**2))),
        log_residual_bias=float(np.mean(residual)),
        expected_mes_min=float(expected[mask].min()),
        expected_mes_max=float(expected[mask].max()),
    )


def _detection_features(expected_mes, period_days, window, domain: SelectionDomain) -> np.ndarray:
    mes, period, probability = np.broadcast_arrays(
        np.asarray(expected_mes, float),
        np.asarray(period_days, float),
        np.asarray(window, float),
    )
    if (
        not np.isfinite(mes).all()
        or not np.isfinite(period).all()
        or not np.isfinite(probability).all()
        or np.any(mes <= 0)
        or np.any(period <= 0)
        or np.any((probability < 0) | (probability > 1))
    ):
        raise ValueError("Detection features are outside their probability domain")
    u = np.log(mes / 7)
    x = (
        2
        * (np.log(period) - np.log(domain.period_min_days))
        / (np.log(domain.period_max_days) - np.log(domain.period_min_days))
        - 1
    )
    clipped_window = np.clip(probability, 1e-8, 1 - 1e-8)
    w = np.log(clipped_window / (1 - clipped_window)) / 12
    return np.column_stack(
        [
            np.ones(mes.size),
            u.ravel(),
            x.ravel(),
            w.ravel(),
            (x * x).ravel(),
        ]
    )


def _fit_detection(
    features,
    outcome,
    training_mask,
    *,
    l2_penalty=0.1,
    monotonic_mes=True,
    monotonic_window=False,
) -> DetectionFit:
    if not np.isfinite(l2_penalty) or l2_penalty < 0:
        raise ValueError("Detection L2 penalty must be finite and non-negative")
    x = np.asarray(features, float)[np.asarray(training_mask, bool)]
    y = np.asarray(outcome, float)[np.asarray(training_mask, bool)]
    if len(y) < x.shape[1] * 10 or np.unique(y).size != 2:
        raise ValueError("Detection calibration needs both outcomes and sufficient rows")

    def objective(coefficients):
        linear = x @ coefficients
        probability = 1 / (1 + np.exp(-np.clip(linear, -35, 35)))
        loss = np.logaddexp(0, linear).sum() - y @ linear
        loss += 0.5 * l2_penalty * float(coefficients[1:] @ coefficients[1:])
        gradient = x.T @ (probability - y)
        gradient += l2_penalty * np.r_[0, coefficients[1:]]
        return float(loss), gradient

    bounds: list[tuple[float | None, float | None]] = [(None, None)] * x.shape[1]
    if monotonic_mes:
        bounds[1] = (0, None)
    if monotonic_window:
        bounds[3] = (0, None)
    result = minimize(
        lambda coefficients: objective(coefficients),
        np.zeros(x.shape[1]),
        jac=True,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 3000, "ftol": 1e-12, "gtol": 1e-7},
    )
    if not result.success:
        raise RuntimeError(f"Selection calibration failed: {result.message}")
    probability = 1 / (1 + np.exp(-np.clip(x @ result.x, -35, 35)))
    weights = probability * (1 - probability)
    hessian = x.T @ (x * weights[:, None])
    hessian += np.diag(np.r_[0, np.repeat(l2_penalty, x.shape[1] - 1)])
    return DetectionFit(
        coefficients=result.x,
        covariance=np.linalg.pinv(hessian),
        l2_penalty=l2_penalty,
        training_rows=len(y),
        metrics=binary_metrics(y, probability),
        monotonic_mes=monotonic_mes,
        monotonic_window=monotonic_window,
    )


def _calibrated_injection_mes(
    calibration: MesCalibration, frame: pd.DataFrame, physics: dict[str, np.ndarray]
) -> np.ndarray:
    return calibration.predict(
        physics["raw_mes"],
        physics["period"],
        physics["duration"],
        frame["dutycycle"],
        frame["dataspan"],
        frame["cdppslplong"],
        frame["cdppslpshrt"],
        frame["radius"],
        frame["logg"],
        frame["teff"],
    )


def fit_selection_model(
    joined: pd.DataFrame,
    *,
    domain: SelectionDomain = SelectionDomain(),
    training_mask=None,
    mes_ridge_penalty: float = 1e-3,
    detection_l2_penalty: float = 0.1,
) -> SelectionModel:
    """Fit MES, combined recovery and conditional vetting on one fixed domain."""
    frame = joined.loc[domain.mask(joined)].copy().reset_index(drop=True)
    if not {"pipeline_recovered", "vetted_pc", "Expected_MES"}.issubset(frame.columns):
        raise ValueError("Joined injection outcomes are incomplete")
    if training_mask is None:
        training = np.ones(len(frame), bool)
    else:
        training = np.asarray(training_mask, bool)
        if training.shape != (len(frame),):
            raise ValueError("Training mask does not match the domain-filtered injections")
    physics = _injection_physics(frame)
    calibration = fit_mes_calibration(frame, physics, training, ridge_penalty=mes_ridge_penalty)
    expected_mes = _calibrated_injection_mes(calibration, frame, physics)
    features = _detection_features(expected_mes, physics["period"], physics["window"], domain)
    recovered = frame["pipeline_recovered"].to_numpy(bool)
    pipeline = _fit_detection(
        features,
        recovered,
        training,
        l2_penalty=detection_l2_penalty,
        monotonic_window=True,
    )
    recovered_training = training[recovered]
    vetting = _fit_detection(
        features[recovered],
        frame.loc[recovered, "vetted_pc"],
        recovered_training,
        l2_penalty=detection_l2_penalty,
    )
    return SelectionModel(domain, calibration, pipeline, vetting)


def predict_injection_rows(model: SelectionModel, frame: pd.DataFrame) -> dict[str, np.ndarray]:
    physics = _injection_physics(frame)
    expected_mes = _calibrated_injection_mes(model.mes_calibration, frame, physics)
    features = _detection_features(expected_mes, physics["period"], physics["window"], model.domain)
    pipeline = model.pipeline_including_window.predict(features)
    vetting = model.vetting_given_recovered.predict(features)
    return {
        **physics,
        "calibrated_expected_mes": expected_mes,
        "pipeline_including_window": pipeline,
        "vetting_given_recovered": vetting,
        "pipeline_and_vetting": pipeline * vetting,
    }


def deterministic_target_holdout(kepid: pd.Series, *, folds=5, holdout=0) -> pd.Series:
    if folds < 2 or not 0 <= holdout < folds:
        raise ValueError("Invalid target holdout definition")
    return kepid.astype(int).map(
        lambda value: (
            int.from_bytes(hashlib.sha256(str(value).encode()).digest()[:8], "big") % folds
            == holdout
        )
    )


def validate_injection_holdout(
    joined: pd.DataFrame,
    *,
    domain: SelectionDomain = SelectionDomain(),
    folds: int = 5,
    holdout: int = 0,
    mes_ridge_penalty: float = 1e-3,
    detection_l2_penalty: float = 0.1,
) -> dict:
    """Evaluate the complete approximation on unseen injected targets."""
    frame = joined.loc[domain.mask(joined)].copy().reset_index(drop=True)
    holdout_mask = deterministic_target_holdout(
        frame["KIC_ID"], folds=folds, holdout=holdout
    ).to_numpy(bool)
    model = fit_selection_model(
        frame,
        domain=domain,
        training_mask=~holdout_mask,
        mes_ridge_penalty=mes_ridge_penalty,
        detection_l2_penalty=detection_l2_penalty,
    )
    prediction = predict_injection_rows(model, frame.loc[holdout_mask])
    test = frame.loc[holdout_mask]
    expected = test["Expected_MES"].to_numpy(float)
    valid_mes = np.isfinite(expected) & (expected > 0)
    log_residual = np.log(prediction["calibrated_expected_mes"][valid_mes]) - np.log(
        expected[valid_mes]
    )
    recovery_truth = test["pipeline_recovered"].to_numpy(float)
    overall_truth = test["vetted_pc"].to_numpy(float)
    recovered = test["pipeline_recovered"].to_numpy(bool)
    vetting_truth = test.loc[recovered, "vetted_pc"].to_numpy(float)
    metrics = {
        "mes": {
            "rows": int(valid_mes.sum()),
            "log_rmse": float(np.sqrt(np.mean(log_residual**2))),
            "log_bias": float(np.mean(log_residual)),
            "fraction_within_25_percent": float(np.mean(np.abs(log_residual) <= np.log(1.25))),
        },
        "pipeline_including_window": binary_metrics(
            recovery_truth, prediction["pipeline_including_window"]
        ),
        "vetting_given_recovered": binary_metrics(
            vetting_truth, prediction["vetting_given_recovered"][recovered]
        ),
        "pipeline_and_vetting": binary_metrics(overall_truth, prediction["pipeline_and_vetting"]),
    }
    baselines = {
        "pipeline_including_window": binary_metrics(
            recovery_truth,
            np.full(len(test), frame.loc[~holdout_mask, "pipeline_recovered"].mean()),
        ),
        "vetting_given_recovered": binary_metrics(
            vetting_truth,
            np.full(
                recovered.sum(),
                frame.loc[~holdout_mask & frame["pipeline_recovered"], "vetted_pc"].mean(),
            ),
        ),
        "pipeline_and_vetting": binary_metrics(
            overall_truth,
            np.full(len(test), frame.loc[~holdout_mask, "vetted_pc"].mean()),
        ),
    }
    predictive_pass = all(
        metrics[name][metric] < baselines[name][metric]
        for name in baselines
        for metric in ("brier", "log_loss")
    )
    mes_pass = metrics["mes"]["log_rmse"] < 0.2 and abs(metrics["mes"]["log_bias"]) < 0.02
    return {
        "split": (f"SHA-256(KIC_ID) modulo {folds} equals {holdout}; target-level holdout"),
        "fold": holdout,
        "folds": folds,
        "domain_rows": len(frame),
        "training_rows": int((~holdout_mask).sum()),
        "holdout_rows": int(holdout_mask.sum()),
        "metrics": metrics,
        "constant_training_fraction_baselines": baselines,
        "thresholds": {
            "mes_log_rmse_below": 0.2,
            "absolute_mes_log_bias_below": 0.02,
            "all_probability_brier_and_log_losses_improve_over_constant_baseline": True,
        },
        "passed": bool(mes_pass and predictive_pass),
    }


def target_averaged_surface(
    model: SelectionModel,
    selected_stars: pd.DataFrame,
    periods,
    radii,
    *,
    chunk_size: int = 4000,
) -> pd.DataFrame:
    """Evaluate every selected star and integrate impact parameter in chunks."""
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
    ):
        raise ValueError("Selected stellar denominator contains invalid physical inputs")
    period_values = np.asarray(periods, float)
    radius_values = np.asarray(radii, float)
    if (
        period_values.ndim != 1
        or radius_values.ndim != 1
        or not np.isfinite(period_values).all()
        or not np.isfinite(radius_values).all()
        or np.any(np.diff(period_values) <= 0)
        or np.any(np.diff(radius_values) <= 0)
        or period_values[0] < model.domain.period_min_days
        or period_values[-1] > model.domain.period_max_days
        or radius_values[0] < model.domain.radius_min_earth
        or radius_values[-1] > model.domain.radius_max_earth
    ):
        raise ValueError("Surface coordinates must increase within the selection domain")
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive")
    shape = (len(radius_values), len(period_values))
    sums = {
        name: np.zeros(shape)
        for name in (
            "geometry",
            "window",
            "pipeline",
            "vetting",
            "pipeline_vetting",
            "selection",
            "mes_below",
            "mes_above",
        )
    }
    impact_nodes, impact_weights = np.polynomial.legendre.leggauss(model.impact_quadrature_nodes)
    impact_nodes = (impact_nodes + 1) / 2
    impact_weights = impact_weights / 2
    p_grid = period_values[None, None, :]
    rp_grid = radius_values[None, :, None]
    for start in range(0, len(selected_stars), chunk_size):
        stars = selected_stars.iloc[start : start + chunk_size]
        star_values = {
            name: stars[name].to_numpy(float)[:, None, None] for name in required if name != "kepid"
        }
        stellar_radius = star_values["radius"]
        stellar_mass = star_values["mass"]
        semimajor = semimajor_axis_au(p_grid, stellar_mass)
        stellar_radius_au = stellar_radius * c.R_sun.value / c.au.value
        scaled_axis = semimajor / stellar_radius_au
        radius_ratio = rp_grid * c.R_earth.value / (stellar_radius * c.R_sun.value)
        geometry = transit_probability(stellar_radius, rp_grid, semimajor)
        window = phase_averaged_window_probability(
            star_values["dataspan"], star_values["dutycycle"], p_grid
        )
        integrated_pipeline = np.zeros_like(geometry)
        integrated_vetting = np.zeros_like(geometry)
        integrated_joint = np.zeros_like(geometry)
        below = np.zeros_like(geometry)
        above = np.zeros_like(geometry)
        for impact, weight in zip(impact_nodes, impact_weights):
            duration = transit_duration_hours(p_grid, radius_ratio, impact, scaled_axis)
            raw_mes = raw_expected_mes(
                p_grid,
                radius_ratio,
                duration,
                star_values["dataspan"],
                star_values["dutycycle"],
                star_values["rrmscdpp06p0"],
                star_values["cdppslplong"],
                star_values["cdppslpshrt"],
            )
            expected_mes = model.mes_calibration.predict(
                raw_mes,
                p_grid,
                duration,
                star_values["dutycycle"],
                star_values["dataspan"],
                star_values["cdppslplong"],
                star_values["cdppslpshrt"],
                stellar_radius,
                star_values["logg"],
                star_values["teff"],
            )
            features = _detection_features(
                expected_mes,
                p_grid + np.zeros_like(geometry),
                window + np.zeros_like(geometry),
                model.domain,
            )
            pipeline = model.pipeline_including_window.predict(features).reshape(geometry.shape)
            vetting = model.vetting_given_recovered.predict(features).reshape(geometry.shape)
            integrated_pipeline += weight * pipeline
            integrated_vetting += weight * vetting
            integrated_joint += weight * pipeline * vetting
            below += weight * (expected_mes < model.mes_calibration.expected_mes_min)
            above += weight * (expected_mes > model.mes_calibration.expected_mes_max)
        sums["geometry"] += geometry.sum(axis=0)
        sums["window"] += np.broadcast_to(window, geometry.shape).sum(axis=0)
        sums["pipeline"] += integrated_pipeline.sum(axis=0)
        sums["vetting"] += integrated_vetting.sum(axis=0)
        sums["pipeline_vetting"] += integrated_joint.sum(axis=0)
        sums["selection"] += (geometry * integrated_joint).sum(axis=0)
        sums["mes_below"] += below.sum(axis=0)
        sums["mes_above"] += above.sum(axis=0)

    rows = []
    target_count = len(selected_stars)
    for radius_index, radius in enumerate(radius_values):
        for period_index, period in enumerate(period_values):
            index = radius_index, period_index
            rows.append(
                {
                    "period_days": period,
                    "planet_radius_earth": radius,
                    "target_stars": target_count,
                    "mean_transit_geometry": sums["geometry"][index] / target_count,
                    "mean_phase_window": sums["window"][index] / target_count,
                    "mean_pipeline_including_window": sums["pipeline"][index] / target_count,
                    "mean_vetting_given_recovered": sums["vetting"][index] / target_count,
                    "mean_pipeline_and_vetting": sums["pipeline_vetting"][index] / target_count,
                    "mean_total_selection": sums["selection"][index] / target_count,
                    "effective_stars": sums["selection"][index],
                    "fraction_impact_target_evaluations_below_mes_training": sums["mes_below"][
                        index
                    ]
                    / target_count,
                    "fraction_impact_target_evaluations_above_mes_training": sums["mes_above"][
                        index
                    ]
                    / target_count,
                    "label": "MODEL-INFERRED",
                }
            )
    return pd.DataFrame(rows)
