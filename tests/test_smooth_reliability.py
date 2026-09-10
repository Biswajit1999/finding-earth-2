"""Tests for the constrained DR25 reliability surface."""

from __future__ import annotations

import numpy as np
import pandas as pd

from earth2.population.reliability import ReliabilityDomain
from earth2.population.smooth_reliability import (
    JointReliabilityFit,
    candidate_reliability_posterior,
    deterministic_holdout,
    fit_joint_reliability,
    predict_components,
)


def known_fit() -> JointReliabilityFit:
    return JointReliabilityFit(
        theta=np.array(
            [
                1.4,
                2.0,
                -0.4,
                0.8,
                0.4,
                0.4,
                2.5,
                -0.2,
                0.1,
                0.4,
                0.3,
                -1.0,
                0.5,
                0.1,
                -0.2,
            ]
        ),
        covariance=np.eye(15) * 1e-4,
        domain=ReliabilityDomain(),
        experiment_aware=True,
        l2_penalty=0.1,
        converged=True,
        iterations=1,
        gradient_norm=0,
        objective=0,
        synthetic_rows=0,
        observed_rows=0,
        synthetic_metrics={},
        observed_metrics={},
    )


def artificial_samples(seed=123, synthetic_rows=1800, observed_rows=900):
    rng = np.random.default_rng(seed)
    domain = ReliabilityDomain()

    def coordinates(rows, experiments):
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
            frame["experiment"] = rng.choice(["INV", "SCR1", "SCR2", "SCR3"], rows)
        return frame

    synthetic = coordinates(synthetic_rows, True)
    observed = coordinates(observed_rows, False)
    truth = known_fit()
    effectiveness = predict_components(truth, synthetic, per_row_experiment=True)[
        "false_alarm_effectiveness"
    ]
    false_alarm_fraction = predict_components(truth, observed)["observed_false_alarm_fraction"]
    synthetic["Disp"] = np.where(rng.random(synthetic_rows) < effectiveness, "FP", "PC")
    observed["observed_false_alarm"] = rng.random(observed_rows) < false_alarm_fraction
    return synthetic, observed


def test_joint_model_fit_and_predictions_stay_in_probability_space():
    synthetic, observed = artificial_samples()
    fit = fit_joint_reliability(synthetic, observed)
    evaluation = pd.DataFrame(
        {"period": [55.0, 300.0, 590.0], "MES": [7.2, 12.0, 29.5], "Rp": [1.0] * 3}
    )
    predicted = predict_components(fit, evaluation)
    assert fit.converged
    assert fit.covariance is not None
    assert len(fit.coefficient_names) == 15
    assert np.all(
        predicted["false_alarm_effectiveness"] > predicted["observed_false_alarm_fraction"]
    )
    assert np.all(
        (predicted["false_alarm_reliability"] > 0) & (predicted["false_alarm_reliability"] <= 1)
    )


def test_candidate_posterior_withholds_out_of_domain_rows():
    candidates = pd.DataFrame(
        {
            "kepoi_name": ["K00001.01", "K00002.01"],
            "observed_tce_period_days": [300.0, 300.0],
            "observed_tce_mes": [10.0, 31.0],
            "koi_prad": [1.0, 1.0],
            "fpp_prob": [0.25, 0.25],
        }
    )
    result = candidate_reliability_posterior(known_fit(), candidates, draws=1000)
    assert result.loc[0, "reliability_status"] == "validated_model_conditional_on_fixed_fpp"
    assert 0 < result.loc[0, "false_alarm_reliability_p50"] <= 1
    assert (
        result.loc[0, "total_candidate_reliability_p50"]
        < result.loc[0, "false_alarm_reliability_p50"]
    )
    assert result.loc[1, "reliability_status"] == "outside_calibration_domain_or_missing_fpp"
    assert np.isnan(result.loc[1, "false_alarm_reliability_p50"])


def test_deterministic_holdout_is_stable_and_nontrivial():
    identifiers = pd.Series([f"{index:09d}-01" for index in range(100)])
    first = deterministic_holdout(identifiers)
    second = deterministic_holdout(identifiers)
    assert first.equals(second)
    assert 10 < first.sum() < 30
