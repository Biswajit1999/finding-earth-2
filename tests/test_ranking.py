"""Ranking sanity tests.

These are the regression tests the brief calls "essential": a clearly
non-habitable giant planet must not rank as highly terrestrial/habitable merely
because some unrelated dimension resembles Earth, and missing data must not
silently default to an Earth-like value.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from earth2.ranking import rank_catalogue, rocky_plausibility
from earth2.ranking.scores import MASS_CLASS_QUALITY, score_conservative_habitability


def _base_row(**overrides):
    row = {
        "pl_name": "Test b", "hostname": "Test", "is_control": False,
        "pl_rade": 1.0, "pl_bmasse": 1.0, "mass_class": "measured",
        "hz_conservative_prob": 1.0, "hz_conservative": 1.0,
        "pl_rade_p50": 1.0, "insol_used": 1.0, "teq_used": 255.0,
        "esi_global_p50": 1.0, "esi_global_p16": 0.95, "esi_global_p84": 1.0, "esi_global": 1.0,
        "mc_uncertainty_coverage": 1.0, "n_references": 5.0, "n_param_sets": 5.0,
        "rade_rel_spread": 0.0, "st_teff": 5780.0, "st_rad": 1.0, "tran_flag": 1,
        "sy_jmag": 8.0, "pl_bmasseerr1": 0.05,
    }
    row.update(overrides)
    return row


def test_hot_jupiter_does_not_rank_highly_habitable():
    """An ultra-hot Jupiter with excellent measurements must score near zero on
    the composite index despite strong observational confidence."""
    df = pd.DataFrame([_base_row(
        pl_name="Hot Jupiter b",
        pl_rade=12.0, pl_bmasse=300.0,  # Jupiter-scale
        hz_conservative_prob=0.0, hz_conservative=0.0,  # not in HZ
        insol_used=5000.0, teq_used=2200.0,
        esi_global_p50=0.05, esi_global=0.05,
        mass_class="measured", mc_uncertainty_coverage=1.0,
        n_references=10.0,
    )])
    ranked = rank_catalogue(df)
    idx = float(ranked["earth2_index"].iloc[0])
    assert idx < 0.15, f"Hot Jupiter scored {idx}, expected near-zero despite good measurements"


def test_earth_like_planet_ranks_highly():
    df = pd.DataFrame([_base_row()])
    ranked = rank_catalogue(df)
    idx = float(ranked["earth2_index"].iloc[0])
    assert idx > 0.85


def test_missing_mass_does_not_default_to_earth_mass():
    """A planet with no mass at all must not be scored as if mass=1 Earth mass."""
    row = _base_row(pl_bmasse=np.nan, mass_class="missing")
    df = pd.DataFrame([row])
    ranked = rank_catalogue(df)
    # observational confidence must reflect the missing mass via mass_class weight
    conf = float(ranked["score_observational_confidence"].iloc[0])
    full_conf_row = pd.DataFrame([_base_row()])
    full_conf = float(rank_catalogue(full_conf_row)["score_observational_confidence"].iloc[0])
    assert conf < full_conf


def test_inferred_mass_scores_lower_confidence_than_measured():
    measured = pd.DataFrame([_base_row(mass_class="measured")])
    inferred = pd.DataFrame([_base_row(mass_class="inferred_mass_radius")])
    c_measured = float(rank_catalogue(measured)["score_observational_confidence"].iloc[0])
    c_inferred = float(rank_catalogue(inferred)["score_observational_confidence"].iloc[0])
    assert c_measured > c_inferred


def test_mass_class_quality_is_monotonic_measured_best():
    assert MASS_CLASS_QUALITY["measured"] == 1.0
    assert MASS_CLASS_QUALITY["inferred_mass_radius"] < MASS_CLASS_QUALITY["measured"]
    assert MASS_CLASS_QUALITY["missing"] == 0.0


def test_rocky_plausibility_decreases_with_radius():
    small = float(rocky_plausibility(pd.Series([1.0])).iloc[0])
    large = float(rocky_plausibility(pd.Series([3.0])).iloc[0])
    assert small > large


def test_rocky_plausibility_nan_for_missing_radius():
    result = rocky_plausibility(pd.Series([np.nan]))
    assert np.isnan(float(result.iloc[0]))


def test_conservative_habitability_is_product_not_sum():
    """A rocky planet outside the HZ AND a non-rocky planet inside the HZ must
    both score low -- neither term alone should be enough."""
    df_out_hz_rocky = pd.DataFrame([_base_row(
        hz_conservative_prob=0.0, pl_rade_p50=1.0,
    )])
    df_in_hz_giant = pd.DataFrame([_base_row(
        hz_conservative_prob=1.0, pl_rade_p50=8.0,
    )])
    s1 = float(score_conservative_habitability(df_out_hz_rocky).iloc[0])
    s2 = float(score_conservative_habitability(df_in_hz_giant).iloc[0])
    assert s1 < 0.1
    assert s2 < 0.1


def test_low_teff_valid_fraction_discounts_habitability_score():
    """A host near/below the Kopparapu polynomial's 2600 K validity floor
    (TRAPPIST-1 at 2566 K is the case the Monte Carlo module names explicitly)
    yields hz_conservative_prob as a nanmean over only the small fraction of
    Monte Carlo draws whose sampled Teff happened to land in range. Left
    unweighted, a planet where only 9% of draws were even evaluable could read
    as "100% HZ probability" -- confusing the model's inapplicability for
    confident evidence. The valid fraction must pull the score down sharply."""
    confident = pd.DataFrame([_base_row(
        hz_conservative_prob=1.0, hz_teff_valid_fraction=1.0,
    )])
    edge_case = pd.DataFrame([_base_row(
        hz_conservative_prob=1.0, hz_teff_valid_fraction=0.09,
    )])
    s_confident = float(score_conservative_habitability(confident).iloc[0])
    s_edge = float(score_conservative_habitability(edge_case).iloc[0])
    assert s_confident > 0.9
    assert s_edge < 0.15
    assert s_edge == pytest.approx(s_confident * 0.09, rel=1e-9)


def test_missing_valid_fraction_defaults_to_fully_valid():
    """Catalogues produced before hz_teff_valid_fraction existed must score
    exactly as they did before -- the new discount is a no-op when the column
    is simply absent, not a silent penalty for old data."""
    df_without_column = pd.DataFrame([_base_row(hz_conservative_prob=1.0)])
    assert "hz_teff_valid_fraction" not in df_without_column.columns
    df_explicit_full_validity = pd.DataFrame([_base_row(
        hz_conservative_prob=1.0, hz_teff_valid_fraction=1.0,
    )])
    s_without_column = float(score_conservative_habitability(df_without_column).iloc[0])
    s_explicit = float(score_conservative_habitability(df_explicit_full_validity).iloc[0])
    assert s_without_column == pytest.approx(s_explicit, rel=1e-9)


def test_disqualifying_component_drags_composite_toward_zero():
    """Geometric-mean non-compensation: one near-zero component must dominate
    even when every other component is perfect."""
    df = pd.DataFrame([_base_row(
        hz_conservative_prob=0.0, hz_conservative=0.0,  # disqualifying
        esi_global_p50=1.0, mc_uncertainty_coverage=1.0, n_references=10.0,
    )])
    ranked = rank_catalogue(df)
    idx = float(ranked["earth2_index"].iloc[0])
    assert idx < 0.2


def test_solar_system_controls_excluded_from_rank_numbering():
    df = pd.DataFrame([
        _base_row(pl_name="Earth", is_control=True),
        _base_row(pl_name="Candidate b", is_control=False),
    ])
    ranked = rank_catalogue(df)
    control_rank = ranked.loc[ranked.pl_name == "Earth", "earth2_rank"].iloc[0]
    assert pd.isna(control_rank)


def test_solar_system_controls_excluded_from_summary_top_candidates():
    """Regression test: Earth/Mars must never appear in the summary's
    top_candidates list. They are scored by the identical functions as real
    exoplanets (deliberately), so they carry a normal-looking earth2_index and
    rankable=True, and sorting by raw index value alone pulls them into a
    'top candidates' list unless is_control is excluded first. This produced
    an unlabelled 'rank 0: Earth' row in the generated README until fixed."""
    from earth2.reporting.summary import build_analysis_summary

    df = pd.DataFrame([
        _base_row(pl_name="Earth", is_control=True, earth2_index=0.95),
        _base_row(pl_name="Candidate b", is_control=False, earth2_index=0.5),
    ])
    ranked = rank_catalogue(df)
    summary = build_analysis_summary(ranked, candidates=ranked)
    names = [c["pl_name"] for c in summary["ranking"]["top_candidates"]]
    assert "Earth" not in names
    assert "Candidate b" in names
