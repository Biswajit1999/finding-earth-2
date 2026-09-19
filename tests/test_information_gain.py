"""Scientific contracts for expected information gain."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from earth2.decision.information_gain import (
    bernoulli_test_information_gain,
    correlated_gaussian_target_information_gain,
    gaussian_expected_information_gain,
    gaussian_posterior_sigma,
    gaussian_transfer_break_even_correlation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_linear_gaussian_eig_has_analytic_unit_snr_value():
    assert gaussian_expected_information_gain(1.0, 1.0) == pytest.approx(0.5 * np.log(2))
    assert gaussian_posterior_sigma(1.0, 1.0) == pytest.approx(1 / np.sqrt(2))


def test_more_precise_observation_has_more_information():
    values = gaussian_expected_information_gain(1.0, np.array([2.0, 1.0, 0.5]))
    assert np.all(np.diff(values) > 0)


def test_invalid_gaussian_scales_are_rejected():
    with pytest.raises(ValueError):
        gaussian_expected_information_gain(1.0, 0.0)
    with pytest.raises(ValueError):
        gaussian_posterior_sigma(np.nan, 1.0)


def test_correlated_measurement_transfers_only_supported_information():
    correlations = np.array([0.0, 0.5, 0.9, 1.0])
    transferred = correlated_gaussian_target_information_gain(2.0, 3.0, correlations, 0.4)
    assert transferred[0] == pytest.approx(0.0)
    assert np.all(np.diff(transferred) > 0)
    assert transferred[-1] == pytest.approx(gaussian_expected_information_gain(3.0, 0.4))


def test_transfer_break_even_recovers_direct_information_threshold():
    direct = gaussian_expected_information_gain(0.3, 0.04)
    threshold = gaussian_transfer_break_even_correlation(direct, 0.08, 0.005)
    transferred = correlated_gaussian_target_information_gain(0.3, 0.08, threshold, 0.005)
    assert transferred == pytest.approx(direct)


def test_invalid_transfer_inputs_are_rejected():
    with pytest.raises(ValueError, match="correlation"):
        correlated_gaussian_target_information_gain(1.0, 1.0, 1.01, 0.1)
    with pytest.raises(ValueError, match="non-negative"):
        gaussian_transfer_break_even_correlation(-0.1, 1.0, 0.1)


def test_perfect_binary_test_recovers_prior_entropy():
    p = 0.3
    expected_entropy = -(p * np.log(p) + (1 - p) * np.log(1 - p))
    assert bernoulli_test_information_gain(p, sensitivity=1.0, specificity=1.0) == pytest.approx(
        expected_entropy
    )


def test_uninformative_binary_test_has_zero_eig():
    assert bernoulli_test_information_gain(0.5, sensitivity=0.5, specificity=0.5) == pytest.approx(
        0.0, abs=1e-14
    )


def test_built_information_gain_product_preserves_claim_boundaries():
    output = ROOT / "results/information_gain"
    summary = json.loads((output / "information_gain.json").read_text())
    assert summary["label"] == "SIMULATED"
    assert summary["candidate_count"] == 25
    assert summary["action_count"] == 6
    assert summary["row_count"] == 150
    assert summary["supported_rows"] == 83
    assert {item["action_id"] for item in summary["withheld_actions"]} == {
        "ephemeris_refinement",
        "xuv_observation",
        "transmission_spectrum",
        "direct_imaging_detection",
        "albedo_measurement",
        "atmospheric_presence_test",
    }
    assert "Cost and time are not modelled" in summary["claim_boundary"]
    audit = summary["objective_conditioned_audit"]
    assert audit["objective"] == "planet radius uncertainty"
    assert audit["assumed_absolute_correlation_ceiling"] == 0.9
    assert audit["eligible_target_count"] > 0
    assert audit["indirect_wins_at_or_below_ceiling"] <= audit["scalar_stellar_action_wins"]
    assert all(row["label"] == "SENSITIVITY" for row in audit["rows"])

    manifest = json.loads((output / "information_gain_products.json").read_text())
    for relative, metadata in manifest["files"].items():
        path = ROOT / relative
        assert path.stat().st_size == metadata["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
