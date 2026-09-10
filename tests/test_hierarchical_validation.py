"""Deterministic smoke test for expanded occurrence-recovery machinery."""

from earth2.population.hierarchical_validation import quick_validation, validation_scenarios


def test_required_validation_scenarios_and_quick_recovery_are_finite():
    names = {scenario.name for scenario in validation_scenarios()}
    assert names == {
        "flat_population",
        "power_law_population",
        "broken_radius_population",
        "earth_box_population",
        "low_completeness",
        "finite_injection_uncertainty",
        "reliability_perturbation",
        "stellar_radius_uncertainty",
        "wrong_completeness_negative_control",
    }
    result = quick_validation()
    assert result["label"] == "SIMULATED"
    assert result["finite"]
