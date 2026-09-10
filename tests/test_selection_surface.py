"""Physical and statistical contracts for the DR25 selection surface."""

import numpy as np
import pandas as pd
import pytest
from astropy import constants as c
from scipy.special import expit

from earth2.population.geometry import semimajor_axis_au
from earth2.population.selection_surface import (
    deterministic_target_holdout,
    fit_selection_model,
    phase_averaged_window_probability,
    predict_injection_rows,
    raw_expected_mes,
    target_averaged_surface,
    transit_duration_hours,
)


def synthetic_injections(rows=900, seed=314159):
    rng = np.random.default_rng(seed)
    period = np.exp(rng.uniform(np.log(50), np.log(500), rows))
    planet_radius = np.exp(rng.uniform(np.log(0.5), np.log(2), rows))
    stellar_radius = rng.uniform(0.75, 1.35, rows)
    stellar_mass = rng.uniform(0.75, 1.25, rows)
    dataspan = rng.uniform(1250, 1470, rows)
    duty = rng.uniform(0.78, 0.96, rows)
    cdpp = np.exp(rng.uniform(np.log(25), np.log(350), rows))
    slope_long = rng.normal(-0.48, 0.05, rows)
    slope_short = rng.normal(-0.50, 0.05, rows)
    radius_ratio = planet_radius * c.R_earth.value / (stellar_radius * c.R_sun.value)
    semimajor = semimajor_axis_au(period, stellar_mass)
    scaled_axis = semimajor / (stellar_radius * c.R_sun.value / c.au.value)
    impact = rng.uniform(0.01, 0.99, rows)
    duration = transit_duration_hours(period, radius_ratio, impact, scaled_axis)
    raw_mes = raw_expected_mes(
        period,
        radius_ratio,
        duration,
        dataspan,
        duty,
        cdpp,
        slope_long,
        slope_short,
    )
    expected_mes = raw_mes * np.exp(rng.normal(0, 0.08, rows))
    window = phase_averaged_window_probability(dataspan, duty, period)
    pipeline_probability = expit(
        3.1 * np.log(expected_mes / 7) + 1.8 * (window - 0.5) - 0.25 * np.log(period / 100)
    )
    vetting_probability = expit(1.4 + 1.0 * np.log(expected_mes / 7) - 0.35 * np.log(period / 100))
    recovered = rng.random(rows) < pipeline_probability
    vetted = recovered & (rng.random(rows) < vetting_probability)
    return pd.DataFrame(
        {
            "KIC_ID": np.arange(10_000_000, 10_000_000 + rows),
            "kepid": np.arange(10_000_000, 10_000_000 + rows),
            "i_period": period,
            "injected_radius_earth": planet_radius,
            "i_ror": radius_ratio,
            "i_b": impact,
            "i_dor": scaled_axis,
            "Expected_MES": expected_mes,
            "pipeline_recovered": recovered,
            "vetted_pc": vetted,
            "mass": stellar_mass,
            "radius": stellar_radius,
            "logg": rng.uniform(4.1, 4.65, rows),
            "teff": rng.uniform(4800, 6300, rows),
            "dataspan": dataspan,
            "dutycycle": duty,
            "rrmscdpp06p0": cdpp,
            "cdppslplong": slope_long,
            "cdppslpshrt": slope_short,
        }
    )


def test_duration_window_and_mes_obey_physical_scalings():
    semimajor = semimajor_axis_au(365.256, 1)
    scaled_axis = semimajor / (c.R_sun.value / c.au.value)
    duration = transit_duration_hours(365.256, 0.00916, 0, scaled_axis)
    assert 12 < duration < 14
    with pytest.raises(ValueError, match="physical"):
        transit_duration_hours(365.256, 0.00916, 1.01, scaled_axis)

    assert phase_averaged_window_probability(200, 1, 100) == pytest.approx(0)
    assert phase_averaged_window_probability(250, 1, 100) == pytest.approx(0.5)
    assert phase_averaged_window_probability(300, 1, 100) == pytest.approx(1)
    probabilities = phase_averaged_window_probability(500, [0.5, 0.8, 1], 100)
    assert np.all(np.diff(probabilities) > 0)

    baseline = raw_expected_mes(100, 0.01, 6, 1000, 0.9, 100, -0.5, -0.5)
    assert raw_expected_mes(100, 0.02, 6, 1000, 0.9, 100, -0.5, -0.5) == pytest.approx(4 * baseline)
    assert raw_expected_mes(100, 0.01, 6, 4000, 0.9, 100, -0.5, -0.5) == pytest.approx(2 * baseline)


def test_target_holdout_is_stable_and_keeps_targets_together():
    identifiers = pd.Series([1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
    first = deterministic_target_holdout(identifiers)
    second = deterministic_target_holdout(identifiers)
    assert first.equals(second)
    assert first.groupby(identifiers).nunique().eq(1).all()
    with pytest.raises(ValueError, match="Invalid"):
        deterministic_target_holdout(identifiers, folds=1)


def test_fitted_model_and_survey_surface_are_bounded_and_factorized():
    injections = synthetic_injections()
    model = fit_selection_model(injections)
    predictions = predict_injection_rows(model, injections.iloc[:100])
    for name in (
        "pipeline_including_window",
        "vetting_given_recovered",
        "pipeline_and_vetting",
    ):
        assert np.all((predictions[name] >= 0) & (predictions[name] <= 1))
    assert np.allclose(
        predictions["pipeline_and_vetting"],
        predictions["pipeline_including_window"] * predictions["vetting_given_recovered"],
    )

    stars = injections.drop_duplicates("kepid").iloc[:12]
    surface = target_averaged_surface(
        model,
        stars,
        periods=[50, 200, 500],
        radii=[0.5, 1, 2],
        chunk_size=5,
    )
    assert len(surface) == 9
    probability_columns = [
        "mean_transit_geometry",
        "mean_phase_window",
        "mean_pipeline_including_window",
        "mean_vetting_given_recovered",
        "mean_pipeline_and_vetting",
        "mean_total_selection",
    ]
    assert np.all((surface[probability_columns] >= 0) & (surface[probability_columns] <= 1))
    assert np.all(surface["mean_total_selection"] <= surface["mean_transit_geometry"])
    assert np.allclose(
        surface["effective_stars"],
        surface["target_stars"] * surface["mean_total_selection"],
    )
    by_period = surface.pivot(
        index="planet_radius_earth", columns="period_days", values="effective_stars"
    )
    assert np.all(by_period.loc[2].to_numpy() >= by_period.loc[0.5].to_numpy())


def test_surface_rejects_an_invalid_stellar_denominator():
    injections = synthetic_injections()
    model = fit_selection_model(injections)
    stars = injections.iloc[:2].copy()
    stars.loc[stars.index[0], "cdppslplong"] = np.nan
    with pytest.raises(ValueError, match="invalid physical"):
        target_averaged_surface(model, stars, periods=[50, 500], radii=[0.5, 2])
