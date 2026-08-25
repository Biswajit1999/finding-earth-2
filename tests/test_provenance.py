"""Provenance chain tests: manifests, the transformation ledger, and
per-measurement reference-link parsing.

These three modules are what let a reader walk backwards from any published
number to the archive row and publication it came from -- the audit singled
out incomplete citation coverage and this is the machinery that coverage
claim rests on, so it is worth testing directly rather than only through the
full pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from earth2.provenance.ledger import TransformLedger
from earth2.provenance.manifest import Manifest, ManifestStore, sha256_bytes, sha256_file
from earth2.provenance.reflink import (
    measurement_provenance_table,
    parse_reflink,
    reference_summary,
)


# --------------------------------------------------------------------------
# reflink parsing
# --------------------------------------------------------------------------
def test_parse_reflink_extracts_publication_fields():
    html = (
        '<a refstr=STASSUN_ET_AL__2017 '
        'href=https://ui.adsabs.harvard.edu/abs/2017AJ....153..136S/abstract '
        'target=ref>Stassun et al. 2017</a>'
    )
    info = parse_reflink(html)
    assert info["ref_key"] == "STASSUN_ET_AL__2017"
    assert info["label"] == "Stassun et al. 2017"
    assert info["bibcode"] == "2017AJ....153..136S"
    assert info["kind"] == "publication"


def test_parse_reflink_flags_archive_calculated_values_separately():
    """A value computed BY THE ARCHIVE from other columns must never be
    reported as though a cited publication measured it directly."""
    html = '<a refstr=CALCULATED_VALUE href=/docs/pscp_calc.html target=_blank>Calculated Value</a>'
    info = parse_reflink(html)
    assert info["kind"] == "archive_calculated"
    assert info["url"] == "https://exoplanetarchive.ipac.caltech.edu/docs/pscp_calc.html"


def test_parse_reflink_unescapes_html_entities_in_labels():
    html = '<a refstr=X href=/y target=ref>Fulton &amp; Petigura 2018</a>'
    info = parse_reflink(html)
    assert info["label"] == "Fulton & Petigura 2018"


def test_parse_reflink_handles_missing_or_sentinel_values():
    for bad in (None, "", "   ", "nan", "None", "<NA>"):
        info = parse_reflink(bad)
        assert info["kind"] == "unknown"
        assert info["ref_key"] is None


def test_parse_reflink_unknown_when_no_ref_key_or_url():
    info = parse_reflink("plain text with no anchor at all")
    assert info["kind"] == "unknown"


def _provenance_frame():
    return pd.DataFrame([
        {
            "pl_name": "Test b", "pl_rade": 1.2,
            "pl_rade_reflink": (
                '<a refstr=SMITH_2020 href=https://ui.adsabs.harvard.edu/abs/'
                '2020ApJ...900..100S/abstract target=ref>Smith 2020</a>'
            ),
            "pl_bmasse": 1.1,
            "pl_bmasse_reflink": '<a refstr=CALCULATED_VALUE href=/docs/pscp_calc.html target=_blank>Calculated Value</a>',
        },
        {
            "pl_name": "Test c", "pl_rade": 2.0,
            "pl_rade_reflink": (
                '<a refstr=SMITH_2020 href=https://ui.adsabs.harvard.edu/abs/'
                '2020ApJ...900..100S/abstract target=ref>Smith 2020</a>'
            ),
            "pl_bmasse": float("nan"),
            "pl_bmasse_reflink": None,
        },
    ])


def test_measurement_provenance_table_discovers_reflink_columns_automatically():
    out = measurement_provenance_table(_provenance_frame())
    assert set(out["parameter"]) == {"pl_rade", "pl_bmasse"}
    # The NaN reflink for Test c/pl_bmasse must be skipped, not turned into a row.
    assert len(out[(out["pl_name"] == "Test c") & (out["parameter"] == "pl_bmasse")]) == 0


def test_measurement_provenance_table_carries_the_underlying_value():
    out = measurement_provenance_table(_provenance_frame(), parameters=["pl_rade"])
    row = out[out["pl_name"] == "Test b"].iloc[0]
    assert row["value"] == 1.2
    assert row["reference_key"] == "SMITH_2020"
    assert row["source_kind"] == "publication"


def test_reference_summary_counts_publications_and_calculated_values():
    prov = measurement_provenance_table(_provenance_frame())
    summary = reference_summary(prov)
    assert summary["n_links"] == 3  # 2x pl_rade (publication) + 1x pl_bmasse (calculated)
    assert summary["by_kind"]["publication"] == 2
    assert summary["by_kind"]["archive_calculated"] == 1
    assert summary["n_distinct_publications"] == 1  # both pl_rade rows cite the same SMITH_2020
    assert summary["archive_calculated_by_parameter"]["pl_bmasse"] == 1


def test_reference_summary_empty_input():
    assert reference_summary(pd.DataFrame()) == {"n_links": 0}


# --------------------------------------------------------------------------
# Transformation ledger
# --------------------------------------------------------------------------
def test_ledger_add_records_and_is_iterable_and_findable():
    led = TransformLedger("test_pipeline")
    led.add("compute_insolation", "Derive incident flux from luminosity and distance.",
            inputs=["st_lum", "pl_orbsmax"], outputs=["pl_insol_derived"],
            equation="S = L / a^2", citation="kopparapu2013", n_rows_in=10, n_rows_out=10)
    assert len(led) == 1
    assert list(led)[0].step == "compute_insolation"
    found = led.find("compute_insolation")
    assert found is not None
    assert found.citation == "kopparapu2013"
    assert led.find("nonexistent_step") is None


def test_ledger_to_dict_reports_step_count_and_name():
    led = TransformLedger("earth2")
    led.add("step_a", "First step.")
    led.add("step_b", "Second step.")
    d = led.to_dict()
    assert d["ledger"] == "earth2"
    assert d["n_steps"] == 2
    assert [s["step"] for s in d["steps"]] == ["step_a", "step_b"]


def test_ledger_save_and_load_round_trips(tmp_path: Path):
    led = TransformLedger("roundtrip")
    led.add("esi_global", "Compute the Earth Similarity Index.",
            inputs=["pl_rade", "pl_dens"], outputs=["esi_global"],
            equation="ESI = prod F_i^(w_i/4)", citation="schulzemakuch2011",
            parameters={"n": 4}, n_rows_in=6354, n_rows_out=5711)
    path = led.save(tmp_path / "ledger.json")
    assert path.exists()

    loaded = TransformLedger.load(path)
    assert len(loaded) == 1
    step = loaded.find("esi_global")
    assert step is not None
    assert step.citation == "schulzemakuch2011"
    assert step.parameters == {"n": 4}
    assert step.n_rows_out == 5711


def test_ledger_load_ignores_unknown_fields_from_a_newer_schema(tmp_path: Path):
    """A ledger file with an extra field the current dataclass doesn't know
    about must still load -- forward compatibility for the ledger format."""
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps({
        "ledger": "future", "steps": [
            {"step": "x", "description": "d", "some_future_field": "ignored"},
        ],
    }), encoding="utf-8")
    loaded = TransformLedger.load(path)
    assert len(loaded) == 1
    assert loaded.find("x") is not None


# --------------------------------------------------------------------------
# Manifests
# --------------------------------------------------------------------------
def test_sha256_bytes_is_deterministic_and_content_sensitive():
    a = sha256_bytes(b"hello world")
    b = sha256_bytes(b"hello world")
    c = sha256_bytes(b"hello world!")
    assert a == b
    assert a != c
    assert len(a) == 64


def test_sha256_file_matches_sha256_bytes(tmp_path: Path):
    p = tmp_path / "payload.bin"
    payload = b"some archive response bytes" * 100
    p.write_bytes(payload)
    assert sha256_file(p) == sha256_bytes(payload)


def _manifest(dataset_id="nasa_pscomppars", n_rows=6354, status="ok"):
    return Manifest(
        dataset_id=dataset_id, archive="NASA Exoplanet Archive",
        source_table="pscomppars", query="select * from pscomppars",
        request_url="https://exoplanetarchive.ipac.caltech.edu/TAP/sync?...",
        retrieved_utc="2026-08-24T02:30:00Z", n_rows=n_rows, n_columns=50,
        sha256="a" * 64, status=status,
    )


def test_manifest_store_total_source_records_sums_ok_and_partial_only(tmp_path: Path):
    for m in (
        _manifest("a", n_rows=100, status="ok"),
        _manifest("b", n_rows=50, status="partial"),
        _manifest("c", n_rows=9999, status="failed"),
    ):
        (tmp_path / f"{m.dataset_id}.json").write_text(
            json.dumps(m.to_dict()), encoding="utf-8"
        )
    store = ManifestStore(tmp_path)
    assert store.total_source_records() == 150  # failed retrieval must not count
    assert set(store.ids()) == {"a", "b", "c"}


def test_manifest_store_summary_rows_includes_short_hash_and_doi(tmp_path: Path):
    m = _manifest("a")
    m.doi = "10.26133/NEA12"
    (tmp_path / "a.json").write_text(json.dumps(m.to_dict()), encoding="utf-8")
    store = ManifestStore(tmp_path)
    rows = store.summary_rows()
    assert rows[0]["dataset_id"] == "a"
    assert rows[0]["sha256_short"] == "a" * 12
    assert rows[0]["doi"] == "10.26133/NEA12"


def test_manifest_store_skips_corrupt_manifest_files(tmp_path: Path):
    """A single unreadable manifest must not take down the whole provenance
    summary -- the reporting layer needs the rest of the archive list."""
    (tmp_path / "good.json").write_text(json.dumps(_manifest("good").to_dict()), encoding="utf-8")
    (tmp_path / "bad.json").write_text("{not valid json", encoding="utf-8")
    store = ManifestStore(tmp_path)
    all_manifests = store.all()
    assert len(all_manifests) == 1
    assert all_manifests[0].dataset_id == "good"


def test_manifest_store_empty_directory_returns_empty(tmp_path: Path):
    store = ManifestStore(tmp_path / "does_not_exist")
    assert store.ids() == []
    assert store.total_source_records() == 0
