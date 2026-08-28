"""Mass-provenance classification and derived-quantity tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from earth2.preprocessing import (
    attach_gaia_crossmatch,
    attach_reference_evidence,
    classify_mass_provenance,
    derive_equilibrium_temperature,
    derive_insolation,
)


def test_reference_evidence_surfaces_mixed_composite_and_default_solution_agreement():
    catalogue = pd.DataFrame({
        "pl_name": ["Test b"],
        "pl_rade": [1.00],
        "pl_bmasse": [1.10],
        "pl_orbper": [365.0],
        "pl_rade_reflink": ["<a href='paper-a'>Paper A</a>"],
        "pl_bmasse_reflink": ["<a href='paper-b'>Paper B</a>"],
        "pl_orbper_reflink": ["<a href='paper-a'>Paper A</a>"],
    })
    ps = pd.DataFrame({
        "pl_name": ["Test b", "Test b"],
        "default_flag": [1, 0],
        "pl_refname": ["Paper A", "Paper B"],
        "pl_rade": [1.02, 1.20],
        "pl_bmasse": [1.00, 1.40],
        "pl_orbper": [365.0, 365.1],
    })

    out = attach_reference_evidence(catalogue, ps)

    assert out.loc[0, "composite_parameter_source_count"] == 2
    assert bool(out.loc[0, "composite_uses_mixed_sources"])
    assert bool(out.loc[0, "default_solution_present"])
    assert out.loc[0, "default_solution_overlap_count"] == 3
    assert out.loc[0, "default_solution_parameter_coverage"] == pytest.approx(1.0)
    assert out.loc[0, "composite_default_median_fractional_difference"] == pytest.approx(
        2 * 0.02 / 2.02,
    )


def test_reference_evidence_marks_missing_default_solution_without_inventing_agreement():
    catalogue = pd.DataFrame({
        "pl_name": ["Test b"],
        "pl_rade": [1.0],
        "pl_rade_reflink": ["Paper A"],
    })
    ps = pd.DataFrame({
        "pl_name": ["Test b"],
        "default_flag": [0],
        "pl_refname": ["Paper A"],
        "pl_rade": [1.0],
    })

    out = attach_reference_evidence(catalogue, ps)

    assert not bool(out.loc[0, "default_solution_present"])
    assert np.isnan(out.loc[0, "default_solution_parameter_coverage"])
    assert np.isnan(out.loc[0, "composite_default_median_fractional_difference"])


def test_measured_mass_classified_correctly():
    df = pd.DataFrame({"pl_bmasse": [1.0], "pl_bmassprov": ["Mass"], "pl_bmasselim": [0.0]})
    result = classify_mass_provenance(df)
    assert result.iloc[0] == "measured"


def test_mass_radius_relation_classified_as_inferred():
    df = pd.DataFrame({"pl_bmasse": [1.2], "pl_bmassprov": ["M-R relationship"], "pl_bmasselim": [0.0]})
    result = classify_mass_provenance(df)
    assert result.iloc[0] == "inferred_mass_radius"


def test_msini_classified_as_lower_limit():
    df = pd.DataFrame({"pl_bmasse": [1.0], "pl_bmassprov": ["Msini"], "pl_bmasselim": [0.0]})
    result = classify_mass_provenance(df)
    assert result.iloc[0] == "msini_lower_limit"


def test_limit_flag_overrides_provenance_string():
    """A value flagged as an upper limit is not a measurement, regardless of
    what the provenance string says."""
    df = pd.DataFrame({"pl_bmasse": [1.0], "pl_bmassprov": ["Mass"], "pl_bmasselim": [1.0]})
    result = classify_mass_provenance(df)
    assert result.iloc[0] == "upper_limit"


def test_missing_mass_classified_as_missing():
    df = pd.DataFrame({"pl_bmasse": [np.nan], "pl_bmassprov": [None], "pl_bmasselim": [np.nan]})
    result = classify_mass_provenance(df)
    assert result.iloc[0] == "missing"


def test_insolation_prefers_catalogue_value():
    df = pd.DataFrame({"pl_insol": [1.5], "st_lum": [0.0], "pl_orbsmax": [1.0]})
    value, source = derive_insolation(df)
    assert abs(float(value.iloc[0]) - 1.5) < 1e-9
    assert source.iloc[0] == "catalogue"


def test_insolation_derived_when_catalogue_missing():
    df = pd.DataFrame({"pl_insol": [np.nan], "st_lum": [0.0], "pl_orbsmax": [1.0]})
    value, source = derive_insolation(df)
    # L = 10**0 = 1, a = 1 -> S = 1
    assert abs(float(value.iloc[0]) - 1.0) < 1e-6
    assert source.iloc[0] == "derived_from_luminosity_and_semimajor_axis"


def test_insolation_missing_when_neither_available():
    df = pd.DataFrame({"pl_insol": [np.nan], "st_lum": [np.nan], "pl_orbsmax": [np.nan]})
    value, source = derive_insolation(df)
    assert np.isnan(float(value.iloc[0]))
    assert source.iloc[0] == "missing"


def test_equilibrium_temperature_derivation_matches_earth():
    df = pd.DataFrame({"pl_eqt": [np.nan]})
    insol = pd.Series([1.0])
    teq, source = derive_equilibrium_temperature(df, insol, albedo=0.306)
    # T_eq = 278.5 * 1^0.25 * (1-0.306)^0.25
    expected = 278.5 * (0.694 ** 0.25)
    assert abs(float(teq.iloc[0]) - expected) < 0.5
    assert "derived_from_insolation" in source.iloc[0]


def test_attach_gaia_crossmatch_joins_on_hostname_and_computes_parallax_distance():
    # A second, unmatched host is included deliberately: it is what forces a
    # NaN gap in gaia_source_id, which is exactly the condition that silently
    # promotes an int64 column through float64 (see the regression test
    # below) if the source_id column is not handled as a pre-stringified
    # value from the start.
    catalogue = pd.DataFrame({
        "pl_name": ["Test b", "Test c", "Unmatched d"],
        "hostname": ["Test Host", "Test Host", "No Gaia Host"],
        "sy_dist": [10.0, 10.0, 20.0],
    })
    gaia = pd.DataFrame({
        "hostname": ["Test Host"], "source_id": [123456789],
        "parallax": [100.0], "parallax_error": [0.05],
        "ruwe": [1.9], "non_single_star": [1],
        "pmra": [1.0], "pmdec": [2.0], "phot_g_mean_mag": [9.0],
    })
    out = attach_gaia_crossmatch(catalogue, gaia)
    # Both sibling planets share the same host and must both get the Gaia row.
    assert (out.loc[out["hostname"] == "Test Host", "gaia_source_id"] == "123456789").all()
    assert out.loc[out["hostname"] == "No Gaia Host", "gaia_source_id"].isna().all()
    # parallax 100 mas -> 1000/100 = 10 pc, matching sy_dist exactly here.
    assert out["gaia_distance_pc"].iloc[0] == pytest.approx(10.0)
    assert out["gaia_distance_disagreement_frac"].iloc[0] == pytest.approx(0.0, abs=1e-9)
    assert out["gaia_ruwe"].iloc[0] == pytest.approx(1.9)
    assert out["gaia_non_single_star"].iloc[0] == 1


def test_attach_gaia_crossmatch_preserves_source_id_precision_alongside_unmatched_hosts():
    """Gaia source_ids are up to 19 digits, beyond float64's 2^53 exact-integer
    range. A catalogue with even one unmatched host creates a NaN gap in
    gaia_source_id, and pandas silently promotes an int64 column with a NaN
    gap to float64 -- which would round a real id like
    2635476908753563008 to ...136 by the time attach_gaia_crossmatch returns,
    unless the column is handled as a string from the start."""
    real_source_id = 2635476908753563008  # TRAPPIST-1's actual Gaia DR3 source_id
    catalogue = pd.DataFrame({
        "pl_name": ["TRAPPIST-1 e", "Unmatched b"],
        "hostname": ["TRAPPIST-1", "No Gaia Host"],
        "sy_dist": [12.4, 20.0],
    })
    gaia = pd.DataFrame({
        "hostname": ["TRAPPIST-1"], "source_id": [real_source_id],
        "parallax": [80.0], "parallax_error": [0.05],
        "ruwe": [1.0], "non_single_star": [0],
        "pmra": [0.0], "pmdec": [0.0], "phot_g_mean_mag": [15.0],
    })
    out = attach_gaia_crossmatch(catalogue, gaia)
    assert out.loc[out["pl_name"] == "TRAPPIST-1 e", "gaia_source_id"].iloc[0] == str(real_source_id)


def test_attach_gaia_crossmatch_leaves_nan_for_hosts_without_a_match():
    catalogue = pd.DataFrame({
        "pl_name": ["Unmatched b"], "hostname": ["No Gaia Host"], "sy_dist": [50.0],
    })
    gaia = pd.DataFrame({
        "hostname": ["Some Other Host"], "source_id": [1], "parallax": [10.0],
        "parallax_error": [0.1], "ruwe": [1.0], "non_single_star": [0],
        "pmra": [0.0], "pmdec": [0.0], "phot_g_mean_mag": [10.0],
    })
    out = attach_gaia_crossmatch(catalogue, gaia)
    assert pd.isna(out["gaia_source_id"].iloc[0])
    assert np.isnan(out["gaia_distance_pc"].iloc[0])


def test_attach_gaia_crossmatch_handles_missing_gaia_table():
    catalogue = pd.DataFrame({"pl_name": ["X b"], "hostname": ["X"], "sy_dist": [5.0]})
    out = attach_gaia_crossmatch(catalogue, None)
    assert "gaia_source_id" in out.columns
    assert pd.isna(out["gaia_source_id"].iloc[0])


def test_attach_gaia_crossmatch_flags_large_distance_disagreement():
    catalogue = pd.DataFrame({
        "pl_name": ["Y b"], "hostname": ["Y"], "sy_dist": [100.0],
    })
    gaia = pd.DataFrame({
        "hostname": ["Y"], "source_id": [1], "parallax": [5.0],  # 1000/5 = 200 pc, not 100
        "parallax_error": [0.1], "ruwe": [1.0], "non_single_star": [0],
        "pmra": [0.0], "pmdec": [0.0], "phot_g_mean_mag": [10.0],
    })
    out = attach_gaia_crossmatch(catalogue, gaia)
    assert out["gaia_distance_disagreement_frac"].iloc[0] == pytest.approx(1.0, rel=1e-6)
