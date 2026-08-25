"""Monte Carlo uncertainty propagation tests."""

from __future__ import annotations

import numpy as np

from earth2.uncertainty import propagate_catalogue, sample_split_normal


def test_wider_uncertainty_widens_the_posterior():
    """A radius of 1.0 +/- 0.6 must have a wider posterior than 1.0 +/- 0.1."""
    rng_tight = np.random.default_rng(1)
    rng_wide = np.random.default_rng(1)

    tight = sample_split_normal(
        np.array([1.0]), np.array([0.1]), np.array([0.1]), 5000, rng_tight, positive=True
    )
    wide = sample_split_normal(
        np.array([1.0]), np.array([0.6]), np.array([0.6]), 5000, rng_wide, positive=True
    )
    assert np.std(wide) > np.std(tight) * 2


def test_positive_constraint_rejects_nonpositive_draws():
    rng = np.random.default_rng(0)
    # Large uncertainty relative to a small value would go negative under a
    # naive Gaussian; the positive constraint must prevent that.
    out = sample_split_normal(
        np.array([0.05]), np.array([1.0]), np.array([1.0]), 2000, rng, positive=True
    )
    finite = out[np.isfinite(out)]
    assert np.all(finite > 0)


def test_missing_uncertainty_yields_delta_function():
    rng = np.random.default_rng(0)
    out = sample_split_normal(
        np.array([1.0]), np.array([np.nan]), np.array([np.nan]), 100, rng, positive=True
    )
    assert np.allclose(out, 1.0)


def test_nan_value_propagates_as_all_nan_row():
    rng = np.random.default_rng(0)
    out = sample_split_normal(
        np.array([np.nan]), np.array([0.1]), np.array([0.1]), 50, rng, positive=True
    )
    assert np.all(np.isnan(out))


def test_propagate_catalogue_hz_probability_is_bounded():
    import pandas as pd

    df = pd.DataFrame({
        "pl_name": ["a", "b"],
        "pl_rade": [1.0, np.nan], "pl_radeerr1": [0.1, np.nan], "pl_radeerr2": [-0.1, np.nan],
        "pl_bmasse": [1.0, np.nan], "pl_bmasseerr1": [0.1, np.nan], "pl_bmasseerr2": [-0.1, np.nan],
        "st_teff": [5780.0, np.nan], "st_tefferr1": [50.0, np.nan], "st_tefferr2": [-50.0, np.nan],
        "st_lum": [0.0, np.nan],
        "pl_orbsmax": [1.0, np.nan],
        "pl_insol": [1.0, np.nan], "pl_insolerr1": [0.05, np.nan], "pl_insolerr2": [-0.05, np.nan],
    })
    result = propagate_catalogue(df, n_samples=500, seed=1)
    probs = result.frame["hz_conservative_prob"].dropna()
    assert ((probs >= 0) & (probs <= 1)).all()
    # The second row has no data at all: probability must be NaN, not 0.
    assert np.isnan(result.frame["hz_conservative_prob"].iloc[1])


def test_uncertainty_coverage_penalises_missing_error_bars():
    import pandas as pd

    with_errors = pd.DataFrame({
        "pl_name": ["a"], "pl_rade": [1.0], "pl_radeerr1": [0.1], "pl_radeerr2": [-0.1],
        "pl_bmasse": [1.0], "pl_bmasseerr1": [0.1], "pl_bmasseerr2": [-0.1],
        "st_teff": [5780.0], "st_tefferr1": [50.0], "st_tefferr2": [-50.0],
        "st_lum": [0.0], "pl_orbsmax": [1.0],
        "pl_insol": [1.0], "pl_insolerr1": [0.05], "pl_insolerr2": [-0.05],
    })
    without_errors = with_errors.copy()
    for c in ["pl_radeerr1", "pl_radeerr2", "pl_bmasseerr1", "pl_bmasseerr2",
              "st_tefferr1", "st_tefferr2", "pl_insolerr1", "pl_insolerr2"]:
        without_errors[c] = np.nan

    r1 = propagate_catalogue(with_errors, n_samples=200, seed=1)
    r2 = propagate_catalogue(without_errors, n_samples=200, seed=1)
    assert r1.frame["mc_uncertainty_coverage"].iloc[0] > r2.frame["mc_uncertainty_coverage"].iloc[0]
