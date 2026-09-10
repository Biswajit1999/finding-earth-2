"""Constrained, experiment-aware DR25 false-alarm reliability model.

The joint parameterisation enforces ``0 < F_FA < E_FA < 1`` so the Bryson et
al. reliability equation remains a probability without clipping. Model release
still depends on held-out real-data checks and deterministic synthetic recovery.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from earth2.population.reliability import ReliabilityDomain

BASE_FEATURE_NAMES = ("intercept", "log_period", "mes", "log_period_x_mes", "log_period2", "mes2")
EXPERIMENTS = ("INV", "SCR1", "SCR2", "SCR3")
DEFAULT_EXPERIMENT_WEIGHTS = {"INV": 0.5, "SCR1": 1 / 6, "SCR2": 1 / 6, "SCR3": 1 / 6}


def _sigmoid(value) -> np.ndarray:
    value = np.asarray(value, float)
    return 1 / (1 + np.exp(-np.clip(value, -35, 35)))


def _surface_features(frame: pd.DataFrame, domain: ReliabilityDomain) -> np.ndarray:
    missing = {"period", "MES"} - set(frame.columns)
    if missing:
        raise ValueError(f"Smooth reliability inputs are missing {sorted(missing)}")
    period = frame["period"].to_numpy(float)
    mes = frame["MES"].to_numpy(float)
    if not np.isfinite(period).all() or not np.isfinite(mes).all() or np.any(period <= 0):
        raise ValueError("Smooth reliability coordinates must be finite and period-positive")
    x = (
        2
        * (np.log(period) - np.log(domain.period_min_days))
        / (np.log(domain.period_max_days) - np.log(domain.period_min_days))
        - 1
    )
    y = 2 * (mes - domain.mes_min) / (domain.mes_max - domain.mes_min) - 1
    return np.column_stack([np.ones(len(frame)), x, y, x * y, x * x, y * y])


def _q_features(
    frame: pd.DataFrame, domain: ReliabilityDomain, *, experiment_aware: bool
) -> np.ndarray:
    base = _surface_features(frame, domain)
    if not experiment_aware:
        return base
    if "experiment" not in frame:
        raise ValueError("Experiment-aware prediction requires an experiment column")
    experiment = frame["experiment"].astype(str)
    if not experiment.isin(EXPERIMENTS).all():
        raise ValueError("Unknown false-alarm experiment")
    contrasts = np.column_stack([experiment.eq(name) for name in EXPERIMENTS[1:]]).astype(float)
    return np.column_stack([base, contrasts])


def _binary_outcome(values, *, name: str) -> np.ndarray:
    result = np.asarray(values, float)
    if result.ndim != 1 or not np.isfinite(result).all() or not np.isin(result, [0, 1]).all():
        raise ValueError(f"{name} must be a finite binary vector")
    if len(result) == 0 or np.unique(result).size != 2:
        raise ValueError(f"{name} must contain both outcomes")
    return result


def binary_metrics(truth, probability) -> dict[str, float]:
    truth = np.asarray(truth, float)
    probability = np.asarray(probability, float)
    if truth.shape != probability.shape or not np.isin(truth, [0, 1]).all():
        raise ValueError("Metric inputs must be aligned binary outcomes and probabilities")
    if not np.isfinite(probability).all() or np.any((probability <= 0) | (probability >= 1)):
        raise ValueError("Metric probabilities must be finite and strictly inside (0,1)")
    return {
        "rows": int(len(truth)),
        "observed_fraction": float(np.mean(truth)),
        "predicted_fraction": float(np.mean(probability)),
        "brier": float(np.mean((truth - probability) ** 2)),
        "log_loss": float(
            -np.mean(truth * np.log(probability) + (1 - truth) * np.log(1 - probability))
        ),
    }


@dataclass(frozen=True)
class JointReliabilityFit:
    theta: np.ndarray
    covariance: np.ndarray | None
    domain: ReliabilityDomain
    experiment_aware: bool
    l2_penalty: float
    converged: bool
    iterations: int
    gradient_norm: float
    objective: float
    synthetic_rows: int
    observed_rows: int
    synthetic_metrics: dict[str, float]
    observed_metrics: dict[str, float]

    @property
    def f_coefficients(self) -> np.ndarray:
        return self.theta[: len(BASE_FEATURE_NAMES)]

    @property
    def q_coefficients(self) -> np.ndarray:
        return self.theta[len(BASE_FEATURE_NAMES) :]

    @property
    def coefficient_names(self) -> tuple[str, ...]:
        q_names = tuple("q_" + name for name in BASE_FEATURE_NAMES)
        if self.experiment_aware:
            q_names += tuple("q_offset_" + name.lower() for name in EXPERIMENTS[1:])
        return tuple("f_" + name for name in BASE_FEATURE_NAMES) + q_names

    def to_dict(self) -> dict:
        return {
            "parameterisation": (
                "F_FA = logistic(X beta_f); q = logistic(Z beta_q); "
                "E_FA = F_FA + (1-F_FA)q; R_FA = (E_FA-F_FA)/(E_FA(1-F_FA))"
            ),
            "domain": asdict(self.domain),
            "experiment_aware": self.experiment_aware,
            "experiment_contrasts": list(EXPERIMENTS[1:]) if self.experiment_aware else [],
            "l2_penalty": self.l2_penalty,
            "converged": self.converged,
            "iterations": self.iterations,
            "gradient_norm": self.gradient_norm,
            "objective": self.objective,
            "synthetic_rows": self.synthetic_rows,
            "observed_rows": self.observed_rows,
            "coefficient_names": list(self.coefficient_names),
            "coefficients": [float(value) for value in self.theta],
            "covariance": self.covariance.tolist() if self.covariance is not None else None,
            "training_metrics": {
                "false_alarm_experiment": self.synthetic_metrics,
                "observed_tce": self.observed_metrics,
            },
        }


def fit_joint_reliability(
    synthetic: pd.DataFrame,
    observed: pd.DataFrame,
    *,
    domain: ReliabilityDomain = ReliabilityDomain(),
    experiment_aware: bool = True,
    l2_penalty: float = 0.1,
    compute_covariance: bool = True,
) -> JointReliabilityFit:
    """Fit joint binomial surfaces with a physical reliability constraint."""
    if not np.isfinite(l2_penalty) or l2_penalty <= 0:
        raise ValueError("A finite positive regularisation penalty is required")
    if "Disp" not in synthetic or "observed_false_alarm" not in observed:
        raise ValueError("Classified synthetic and observed outcomes are required")
    synthetic = synthetic.loc[domain.mask(synthetic)].copy()
    observed = observed.loc[domain.mask(observed)].copy()
    x_synthetic = _surface_features(synthetic, domain)
    z_synthetic = _q_features(synthetic, domain, experiment_aware=experiment_aware)
    x_observed = _surface_features(observed, domain)
    y_synthetic = _binary_outcome(synthetic["Disp"].eq("FP"), name="Synthetic rejection")
    y_observed = _binary_outcome(
        observed["observed_false_alarm"], name="Observed false-alarm classification"
    )
    n_f = x_synthetic.shape[1]
    n_parameters = n_f + z_synthetic.shape[1]

    def objective(theta: np.ndarray) -> tuple[float, np.ndarray]:
        beta_f, beta_q = theta[:n_f], theta[n_f:]
        f_synthetic = _sigmoid(x_synthetic @ beta_f)
        q_synthetic = _sigmoid(z_synthetic @ beta_q)
        effectiveness = q_synthetic + f_synthetic * (1 - q_synthetic)
        f_observed = _sigmoid(x_observed @ beta_f)
        effectiveness_safe = np.clip(effectiveness, 1e-12, 1 - 1e-12)
        f_observed_safe = np.clip(f_observed, 1e-12, 1 - 1e-12)
        loss = -np.sum(
            y_synthetic * np.log(effectiveness_safe)
            + (1 - y_synthetic) * np.log(1 - effectiveness_safe)
        ) - np.sum(
            y_observed * np.log(f_observed_safe) + (1 - y_observed) * np.log(1 - f_observed_safe)
        )
        loss += 0.5 * l2_penalty * float(theta[1:] @ theta[1:])

        d_loss_d_e = (effectiveness - y_synthetic) / (effectiveness_safe * (1 - effectiveness_safe))
        gradient_f = x_synthetic.T @ (
            d_loss_d_e * f_synthetic * (1 - f_synthetic) * (1 - q_synthetic)
        ) + x_observed.T @ (f_observed - y_observed)
        gradient_q = z_synthetic.T @ (
            d_loss_d_e * (1 - f_synthetic) * q_synthetic * (1 - q_synthetic)
        )
        gradient = np.r_[gradient_f, gradient_q]
        gradient += l2_penalty * np.r_[0, theta[1:]]
        return float(loss), gradient

    result = minimize(
        lambda theta: objective(theta),
        np.zeros(n_parameters),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": 3000, "ftol": 1e-12, "gtol": 1e-7},
    )
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError(f"Joint reliability optimisation failed: {result.message}")

    covariance = None
    if compute_covariance:
        hessian = np.empty((n_parameters, n_parameters))
        for column in range(n_parameters):
            step = 1e-4 * (1 + abs(result.x[column]))
            upper, lower = result.x.copy(), result.x.copy()
            upper[column] += step
            lower[column] -= step
            hessian[:, column] = (objective(upper)[1] - objective(lower)[1]) / (2 * step)
        hessian = (hessian + hessian.T) / 2
        eigenvalues, eigenvectors = np.linalg.eigh(hessian)
        if not np.isfinite(eigenvalues).all() or eigenvalues.max() <= 0:
            raise RuntimeError("Joint reliability Hessian is invalid")
        floor = max(eigenvalues.max() * 1e-10, 1e-10)
        covariance = (eigenvectors * (1 / np.maximum(eigenvalues, floor))) @ eigenvectors.T

    fit_without_metrics = JointReliabilityFit(
        theta=result.x,
        covariance=covariance,
        domain=domain,
        experiment_aware=experiment_aware,
        l2_penalty=l2_penalty,
        converged=bool(result.success),
        iterations=int(result.nit),
        gradient_norm=float(np.linalg.norm(result.jac)),
        objective=float(result.fun),
        synthetic_rows=len(synthetic),
        observed_rows=len(observed),
        synthetic_metrics={},
        observed_metrics={},
    )
    predicted_synthetic = predict_components(
        fit_without_metrics, synthetic, per_row_experiment=True
    )["false_alarm_effectiveness"]
    predicted_observed = predict_components(fit_without_metrics, observed)[
        "observed_false_alarm_fraction"
    ]
    return JointReliabilityFit(
        **{
            **fit_without_metrics.__dict__,
            "synthetic_metrics": binary_metrics(y_synthetic, predicted_synthetic),
            "observed_metrics": binary_metrics(y_observed, predicted_observed),
        }
    )


def _validate_weights(weights: dict[str, float]) -> dict[str, float]:
    if set(weights) != set(EXPERIMENTS):
        raise ValueError("Weights must name all four false-alarm experiments")
    values = np.asarray([weights[name] for name in EXPERIMENTS], float)
    if not np.isfinite(values).all() or np.any(values < 0) or not np.isclose(values.sum(), 1):
        raise ValueError("Experiment weights must be finite, non-negative and sum to one")
    return weights


def predict_components(
    fit: JointReliabilityFit,
    frame: pd.DataFrame,
    *,
    theta: np.ndarray | None = None,
    experiment_weights: dict[str, float] = DEFAULT_EXPERIMENT_WEIGHTS,
    per_row_experiment: bool = False,
) -> dict[str, np.ndarray]:
    """Evaluate F, E and physical R for rows inside or outside the fit domain."""
    parameters = fit.theta if theta is None else np.asarray(theta, float)
    if parameters.shape != fit.theta.shape:
        raise ValueError("Prediction parameter vector has the wrong shape")
    x = _surface_features(frame, fit.domain)
    beta_f = parameters[: len(BASE_FEATURE_NAMES)]
    beta_q = parameters[len(BASE_FEATURE_NAMES) :]
    false_alarm_fraction = _sigmoid(x @ beta_f)
    if per_row_experiment:
        q = _sigmoid(_q_features(frame, fit.domain, experiment_aware=fit.experiment_aware) @ beta_q)
    elif fit.experiment_aware:
        weights = _validate_weights(experiment_weights)
        q = np.zeros(len(frame))
        for experiment in EXPERIMENTS:
            evaluation = frame.copy()
            evaluation["experiment"] = experiment
            q += weights[experiment] * _sigmoid(
                _q_features(evaluation, fit.domain, experiment_aware=True) @ beta_q
            )
    else:
        q = _sigmoid(_q_features(frame, fit.domain, experiment_aware=False) @ beta_q)
    effectiveness = q + false_alarm_fraction * (1 - q)
    reliability = (effectiveness - false_alarm_fraction) / (
        effectiveness * (1 - false_alarm_fraction)
    )
    if not np.isfinite(reliability).all() or np.any(reliability <= 0) or np.any(reliability > 1):
        raise RuntimeError("Constrained reliability prediction left the probability space")
    return {
        "observed_false_alarm_fraction": false_alarm_fraction,
        "residual_rejection_probability": q,
        "false_alarm_effectiveness": effectiveness,
        "false_alarm_reliability": reliability,
    }


def deterministic_holdout(identifier: pd.Series, *, folds: int = 5, holdout: int = 0) -> pd.Series:
    if folds < 2 or not 0 <= holdout < folds:
        raise ValueError("Invalid deterministic holdout definition")
    return identifier.astype(str).map(
        lambda value: (
            int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big") % folds == holdout
        )
    )


def validate_held_out_data(
    synthetic: pd.DataFrame,
    observed: pd.DataFrame,
    *,
    domain: ReliabilityDomain = ReliabilityDomain(),
) -> dict:
    """Test experiment transfer and a deterministic observed-TCE holdout."""
    synthetic = synthetic.loc[domain.mask(synthetic)].copy()
    observed = observed.loc[domain.mask(observed)].copy()
    experiment_results = []
    for experiment in EXPERIMENTS:
        is_holdout = synthetic["experiment"].eq(experiment)
        fit = fit_joint_reliability(
            synthetic.loc[~is_holdout],
            observed,
            domain=domain,
            experiment_aware=False,
            compute_covariance=False,
        )
        truth = synthetic.loc[is_holdout, "Disp"].eq("FP").to_numpy(float)
        predicted = predict_components(fit, synthetic.loc[is_holdout])["false_alarm_effectiveness"]
        baseline_probability = np.full(
            len(truth), synthetic.loc[~is_holdout, "Disp"].eq("FP").mean()
        )
        model_metrics = binary_metrics(truth, predicted)
        baseline_metrics = binary_metrics(truth, baseline_probability)
        passed = (
            model_metrics["brier"] <= baseline_metrics["brier"]
            and model_metrics["log_loss"] <= baseline_metrics["log_loss"]
        )
        experiment_results.append(
            {
                "held_out_experiment": experiment,
                "model": model_metrics,
                "constant_training_fraction_baseline": baseline_metrics,
                "passed": bool(passed),
            }
        )

    observed_holdout = deterministic_holdout(observed["TCE_ID"])
    observed_fit = fit_joint_reliability(
        synthetic,
        observed.loc[~observed_holdout],
        domain=domain,
        experiment_aware=True,
        compute_covariance=False,
    )
    observed_truth = observed.loc[observed_holdout, "observed_false_alarm"].to_numpy(float)
    observed_prediction = predict_components(observed_fit, observed.loc[observed_holdout])[
        "observed_false_alarm_fraction"
    ]
    observed_baseline_probability = np.full(
        len(observed_truth), observed.loc[~observed_holdout, "observed_false_alarm"].mean()
    )
    observed_model_metrics = binary_metrics(observed_truth, observed_prediction)
    observed_baseline_metrics = binary_metrics(observed_truth, observed_baseline_probability)
    observed_passed = (
        observed_model_metrics["brier"] < observed_baseline_metrics["brier"]
        and observed_model_metrics["log_loss"] < observed_baseline_metrics["log_loss"]
    )
    return {
        "experiment_holdouts": experiment_results,
        "observed_tce_holdout": {
            "split": "SHA-256(TCE_ID) modulo 5 equals zero",
            "model": observed_model_metrics,
            "constant_training_fraction_baseline": observed_baseline_metrics,
            "passed": bool(observed_passed),
        },
        "passed": bool(all(result["passed"] for result in experiment_results) and observed_passed),
    }


def candidate_reliability_posterior(
    fit: JointReliabilityFit,
    candidates: pd.DataFrame,
    *,
    seed: int = 8675309,
    draws: int = 20000,
) -> pd.DataFrame:
    """Assign reliability only inside the model domain, conditional on fixed FPP."""
    if fit.covariance is None:
        raise ValueError("Candidate posterior requires a coefficient covariance")
    if draws < 1000:
        raise ValueError("At least 1000 posterior draws are required")
    required = {"observed_tce_period_days", "observed_tce_mes", "koi_prad", "fpp_prob"}
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(f"Candidate table is missing {sorted(missing)}")
    output = candidates.copy()
    output["false_alarm_reliability_p025"] = np.nan
    output["false_alarm_reliability_p50"] = np.nan
    output["false_alarm_reliability_p975"] = np.nan
    output["total_candidate_reliability_p025"] = np.nan
    output["total_candidate_reliability_p50"] = np.nan
    output["total_candidate_reliability_p975"] = np.nan
    evaluation = pd.DataFrame(
        {
            "period": output["observed_tce_period_days"],
            "MES": output["observed_tce_mes"],
            "Rp": output["koi_prad"],
        },
        index=output.index,
    )
    inside = fit.domain.mask(evaluation) & output["fpp_prob"].notna()
    if not inside.any():
        output["reliability_status"] = "outside_calibration_domain_or_missing_fpp"
        return output
    evaluation = evaluation.loc[inside]
    rng = np.random.default_rng(seed)
    draws_theta = rng.multivariate_normal(fit.theta, fit.covariance, size=draws)
    x = _surface_features(evaluation, fit.domain)
    f_draws = _sigmoid(draws_theta[:, : len(BASE_FEATURE_NAMES)] @ x.T)
    q_draws = np.zeros_like(f_draws)
    for experiment, weight in _validate_weights(DEFAULT_EXPERIMENT_WEIGHTS).items():
        experiment_frame = evaluation.copy()
        experiment_frame["experiment"] = experiment
        z = _q_features(experiment_frame, fit.domain, experiment_aware=True)
        q_draws += weight * _sigmoid(draws_theta[:, len(BASE_FEATURE_NAMES) :] @ z.T)
    effectiveness_draws = q_draws + f_draws * (1 - q_draws)
    reliability_draws = (effectiveness_draws - f_draws) / (effectiveness_draws * (1 - f_draws))
    quantiles = np.quantile(reliability_draws, [0.025, 0.5, 0.975], axis=0)
    fpp_planet_probability = 1 - output.loc[inside, "fpp_prob"].to_numpy(float)
    total = quantiles * fpp_planet_probability[None, :]
    output.loc[inside, "false_alarm_reliability_p025"] = quantiles[0]
    output.loc[inside, "false_alarm_reliability_p50"] = quantiles[1]
    output.loc[inside, "false_alarm_reliability_p975"] = quantiles[2]
    output.loc[inside, "total_candidate_reliability_p025"] = total[0]
    output.loc[inside, "total_candidate_reliability_p50"] = total[1]
    output.loc[inside, "total_candidate_reliability_p975"] = total[2]
    output["reliability_status"] = "outside_calibration_domain_or_missing_fpp"
    output.loc[inside, "reliability_status"] = "validated_model_conditional_on_fixed_fpp"
    output["false_alarm_reliability_label"] = "MODEL-INFERRED"
    output["total_candidate_reliability_label"] = "MODEL-INFERRED"
    return output


def run_synthetic_recovery(
    *,
    seed: int = 314159,
    replicates: int = 60,
    synthetic_rows: int = 4000,
    observed_rows: int = 2000,
    domain: ReliabilityDomain = ReliabilityDomain(),
) -> dict:
    """Recover a known joint reliability surface from artificial outcomes."""
    if replicates < 2 or synthetic_rows < 1000 or observed_rows < 500:
        raise ValueError("Synthetic recovery design is too small")
    rng = np.random.default_rng(seed)
    beta_f = np.array([1.4, 2.0, -0.4, 0.8, 0.4, 0.4])
    beta_q = np.array([2.5, -0.2, 0.1, 0.4, 0.3, -1.0, 0.5, 0.1, -0.2])

    def coordinates(rows: int, *, experiments: bool) -> pd.DataFrame:
        frame = pd.DataFrame(
            {
                "period": np.exp(
                    rng.uniform(
                        np.log(domain.period_min_days), np.log(domain.period_max_days), rows
                    )
                ),
                "MES": rng.uniform(domain.mes_min, domain.mes_max, rows),
                "Rp": rng.uniform(domain.radius_min_earth, domain.radius_max_earth, rows),
            }
        )
        if experiments:
            frame["experiment"] = rng.choice(EXPERIMENTS, rows)
        return frame

    evaluation = pd.DataFrame(
        [
            (period, mes, 1.0)
            for period in np.geomspace(55, 550, 9)
            for mes in np.linspace(7.5, 28, 7)
        ],
        columns=["period", "MES", "Rp"],
    )
    truth_fit = JointReliabilityFit(
        theta=np.r_[beta_f, beta_q],
        covariance=None,
        domain=domain,
        experiment_aware=True,
        l2_penalty=0.1,
        converged=True,
        iterations=0,
        gradient_norm=0,
        objective=0,
        synthetic_rows=0,
        observed_rows=0,
        synthetic_metrics={},
        observed_metrics={},
    )
    truth = predict_components(truth_fit, evaluation)
    errors = []
    convergence = 0
    for _ in range(replicates):
        synthetic = coordinates(synthetic_rows, experiments=True)
        observed = coordinates(observed_rows, experiments=False)
        synthetic_truth = predict_components(truth_fit, synthetic, per_row_experiment=True)[
            "false_alarm_effectiveness"
        ]
        observed_truth = predict_components(truth_fit, observed)["observed_false_alarm_fraction"]
        synthetic["Disp"] = np.where(rng.random(synthetic_rows) < synthetic_truth, "FP", "PC")
        observed["observed_false_alarm"] = rng.random(observed_rows) < observed_truth
        try:
            fitted = fit_joint_reliability(
                synthetic,
                observed,
                domain=domain,
                experiment_aware=True,
                compute_covariance=False,
            )
        except RuntimeError:
            continue
        convergence += 1
        prediction = predict_components(fitted, evaluation)
        errors.append(
            [
                float(
                    np.sqrt(
                        np.mean(
                            (
                                prediction["false_alarm_effectiveness"]
                                - truth["false_alarm_effectiveness"]
                            )
                            ** 2
                        )
                    )
                ),
                float(
                    np.sqrt(
                        np.mean(
                            (
                                prediction["observed_false_alarm_fraction"]
                                - truth["observed_false_alarm_fraction"]
                            )
                            ** 2
                        )
                    )
                ),
                float(
                    np.sqrt(
                        np.mean(
                            (
                                prediction["false_alarm_reliability"]
                                - truth["false_alarm_reliability"]
                            )
                            ** 2
                        )
                    )
                ),
            ]
        )
    if not errors:
        raise RuntimeError("Every synthetic recovery fit failed")
    errors_array = np.asarray(errors)
    mean_rmse = errors_array.mean(axis=0)
    p95_rmse = np.quantile(errors_array, 0.95, axis=0)
    passed = (
        convergence == replicates
        and mean_rmse[0] < 0.03
        and mean_rmse[1] < 0.04
        and mean_rmse[2] < 0.08
        and p95_rmse[2] < 0.15
    )
    return {
        "label": "SIMULATED",
        "seed": seed,
        "replicates": replicates,
        "converged_replicates": convergence,
        "synthetic_rows_per_replicate": synthetic_rows,
        "observed_rows_per_replicate": observed_rows,
        "evaluation_points": len(evaluation),
        "generating_family": "same constrained quadratic-logistic family used for fitting",
        "mean_rmse": {
            "false_alarm_effectiveness": float(mean_rmse[0]),
            "observed_false_alarm_fraction": float(mean_rmse[1]),
            "false_alarm_reliability": float(mean_rmse[2]),
        },
        "p95_rmse": {
            "false_alarm_effectiveness": float(p95_rmse[0]),
            "observed_false_alarm_fraction": float(p95_rmse[1]),
            "false_alarm_reliability": float(p95_rmse[2]),
        },
        "thresholds": {
            "all_replicates_converge": True,
            "mean_effectiveness_rmse_below": 0.03,
            "mean_false_alarm_fraction_rmse_below": 0.04,
            "mean_reliability_rmse_below": 0.08,
            "p95_reliability_rmse_below": 0.15,
        },
        "passed": bool(passed),
    }
