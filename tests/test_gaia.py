"""Gaia DR3 crossmatch tests.

This integration is an exact source_id match, not a fuzzy one: extract_source_id
must never coerce a malformed or missing identifier into a false match, and
the chunked fetch must combine into exactly one manifest per logical dataset
even though it issues several HTTP requests under the hood.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from earth2.data_sources.gaia import (
    GAIA_COLUMNS,
    crossmatch_summary,
    extract_source_id,
    fetch_gaia_crossmatch,
    hosts_with_gaia_ids,
)


def test_extract_source_id_parses_the_archives_string_format():
    assert extract_source_id("Gaia DR3 4919009555730599936") == 4919009555730599936


def test_extract_source_id_is_case_insensitive_and_tolerates_whitespace():
    assert extract_source_id("gaia dr3  4919009555730599936") == 4919009555730599936


def test_extract_source_id_returns_none_for_missing_or_malformed_values():
    assert extract_source_id(None) is None
    assert extract_source_id(float("nan")) is None
    assert extract_source_id("") is None
    assert extract_source_id("Gaia DR2 4919009555730599936") is None  # wrong data release
    assert extract_source_id("not a gaia id at all") is None


def test_hosts_with_gaia_ids_collapses_to_one_row_per_host():
    df = pd.DataFrame([
        {"hostname": "TRAPPIST-1", "gaia_dr3_id": "Gaia DR3 2635476908753563008"},
        {"hostname": "TRAPPIST-1", "gaia_dr3_id": "Gaia DR3 2635476908753563008"},  # sibling planet
        {"hostname": "Proxima Cen", "gaia_dr3_id": "Gaia DR3 5853498713190525696"},
        {"hostname": "No Gaia Host", "gaia_dr3_id": None},
    ])
    out = hosts_with_gaia_ids(df)
    assert len(out) == 2
    assert set(out["hostname"]) == {"TRAPPIST-1", "Proxima Cen"}
    trappist_row = out[out["hostname"] == "TRAPPIST-1"].iloc[0]
    assert trappist_row["source_id"] == 2635476908753563008


def test_hosts_with_gaia_ids_missing_columns_returns_empty_frame():
    out = hosts_with_gaia_ids(pd.DataFrame({"hostname": ["X"]}))
    assert out.empty
    assert list(out.columns) == ["hostname", "source_id"]


def _fake_gaia_dataframe(source_ids):
    return pd.DataFrame({
        "source_id": source_ids,
        "ra": [10.0 * i for i in range(len(source_ids))],
        "dec": [20.0] * len(source_ids),
        "parallax": [100.0] * len(source_ids),
        "parallax_error": [0.05] * len(source_ids),
        "pmra": [0.0] * len(source_ids), "pmra_error": [0.01] * len(source_ids),
        "pmdec": [0.0] * len(source_ids), "pmdec_error": [0.01] * len(source_ids),
        "ruwe": [1.0] * len(source_ids), "non_single_star": [0] * len(source_ids),
        "phot_g_mean_mag": [10.0] * len(source_ids),
        "phot_bp_mean_mag": [10.5] * len(source_ids),
        "phot_rp_mean_mag": [9.5] * len(source_ids),
        "bp_rp": [1.0] * len(source_ids),
        "radial_velocity": [0.0] * len(source_ids),
        "radial_velocity_error": [0.5] * len(source_ids),
    })


def test_fetch_gaia_crossmatch_combines_chunks_into_one_manifest(tmp_path, monkeypatch):
    # Manifest.save() writes to the module-level MANIFEST_DIR; redirect it to a
    # scratch directory so this test cannot write into the real data/manifests/.
    monkeypatch.setattr("earth2.provenance.manifest.MANIFEST_DIR", tmp_path)

    source_ids = list(range(1, 11))  # 10 ids, chunk_size=4 -> 3 chunks

    def fake_post_adql(chunk_id, adql, use_cache):
        # Recover which ids were requested from the literal ADQL string.
        ids_in_query = [int(x) for x in adql.split("in (")[1].rstrip(")").split(",")]
        return _fake_gaia_dataframe(ids_in_query), "a" * 64, False

    with patch("earth2.data_sources.gaia._post_adql", side_effect=fake_post_adql):
        combined, manifest = fetch_gaia_crossmatch(source_ids, chunk_size=4, dataset_id="test_crossmatch")

    assert len(combined) == 10
    assert set(combined["source_id"]) == set(source_ids)
    assert manifest.dataset_id == "test_crossmatch"
    assert manifest.n_rows == 10
    assert "3 chunked TAP queries" in manifest.notes

    # Regression: total_source_records() sums every manifest file's n_rows
    # unconditionally. A separate manifest per chunk, alongside this aggregate
    # manifest for the same rows, would double- (or triple-) count every Gaia
    # row in that headline figure. Exactly one manifest file must exist.
    manifest_files = list(tmp_path.glob("*.json"))
    assert len(manifest_files) == 1
    assert manifest_files[0].name == "test_crossmatch.json"


def test_fetch_gaia_crossmatch_raises_on_empty_input():
    with pytest.raises(ValueError):
        fetch_gaia_crossmatch([])


def test_crossmatch_summary_counts_ruwe_and_non_single_star_flags():
    hosts = pd.DataFrame({"hostname": ["A", "B", "C"], "source_id": [1, 2, 3]})
    gaia = pd.DataFrame({
        "source_id": [1, 2, 3],
        "ruwe": [1.0, 1.8, np.nan],
        "non_single_star": [0, 1, 0],
    })
    summary = crossmatch_summary(hosts, gaia)
    assert summary["n_hosts_with_gaia_dr3_id"] == 3
    assert summary["n_hosts_crossmatched"] == 3
    assert summary["n_ruwe_above_1p4"] == 1
    assert summary["n_non_single_star_flagged"] == 1


def test_crossmatch_summary_empty_gaia_result():
    hosts = pd.DataFrame({"hostname": ["A"], "source_id": [1]})
    summary = crossmatch_summary(hosts, pd.DataFrame(columns=GAIA_COLUMNS))
    assert summary["n_hosts_crossmatched"] == 0
