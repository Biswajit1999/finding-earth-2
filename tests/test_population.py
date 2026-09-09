"""Scientific contract tests; no bulk archive request in the test suite."""

import io
import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from astropy.io import ascii
from astropy.table import Table

from earth2.population import archive
from earth2.population.completeness import (
    SurveyContract,
    binomial_efficiency,
    detection_probability,
)
from earth2.population.geometry import semimajor_axis_au, transit_probability
from earth2.population.kepler import (
    STELLAR_COLUMNS,
    StellarSelection,
    empirical_grid,
    join_injections,
    parse_ipac,
    parse_stars,
)


def star_fixture():
    frame = pd.DataFrame({key: [1.0, 1.0, 1.0] for key in STELLAR_COLUMNS})
    frame["kepid"] = [1, 2, 3]
    frame["teff"] = 5772.0
    frame["logg"] = 4.4
    frame["st_delivname"] = "q1_q17_dr25_stellar"
    return frame


def injection_fixture():
    return pd.DataFrame(
        {
            "KIC_ID": [1, 2, 3],
            "i_period": [10.0, 100.0, 300.0],
            "i_ror": [0.00916] * 3,
            "i_b": [0.1] * 3,
            "i_dor": [10.0] * 3,
            "Expected_MES": [15.0, 10.0, 3.0],
            "Recovered": [1, 1, 0],
            "TCE_ID": ["1-1", "2-1", None],
            "N_Transit": [100.0, 10.0, 1.5],
            "EB_injection": [0] * 3,
            "Offset_from_source": [0] * 3,
        }
    )


def vetting_fixture():
    return pd.DataFrame(
        {
            "TCE_ID": ["000000001-01", "000000002-01"],
            "KIC": [1, 2],
            "Disp": ["PC", "FP"],
            "Score": [0.9, 0.1],
        }
    )


def ipac_bytes(frame):
    table = Table.from_pandas(frame)
    table.meta["keywords"] = {"runtype": {"value": "INJ1"}, "nrows": {"value": len(frame)}}
    output = io.StringIO()
    ascii.write(table, output, format="ipac")
    # The archive's metadata uses unquoted runtype, unlike the astropy writer.
    return output.getvalue().replace("'INJ1'", "INJ1").encode()


def test_earth_geometry_and_eccentric_orientation():
    assert semimajor_axis_au(365.256, 1) == pytest.approx(1, rel=3e-5)
    p = transit_probability(1, 1, 1)
    assert p == pytest.approx(0.00465047, rel=1e-5)
    assert transit_probability(1, 1, 1, 0.5, np.pi / 2) == pytest.approx(2 * p)
    assert transit_probability(1, 1, 1, 0.5, -np.pi / 2) == pytest.approx(p / 1.5)
    assert transit_probability(1, 1, 1, criterion="any_overlap") > p
    with pytest.raises(ValueError, match="intersects"):
        transit_probability(1, 1, 0.01, 0.9)
    with pytest.raises(ValueError):
        transit_probability(1, 1, 1, 1)


def test_window_counted_once_and_no_reliability_argument():
    assert detection_probability(0.01, 0.8, 0.9, window=0.5) == pytest.approx(0.0036)
    assert detection_probability(0.01, 0.4, 0.9, pipeline_includes_window=True) == pytest.approx(
        0.0036
    )
    with pytest.raises(ValueError, match="twice"):
        detection_probability(1, 1, 1, window=1, pipeline_includes_window=True)
    with pytest.raises(ValueError, match="required"):
        detection_probability(1, 1, 1)
    with pytest.raises(TypeError):
        detection_probability(1, 1, 1, window=1, reliability=0.9)
    with pytest.raises(ValueError):
        detection_probability(1, np.nan, 1, window=1)


def test_selection_contract_rejects_calibration_transfer():
    contract = SurveyContract("Kepler", "DR25", "GK", "centre_crossing", "calibration1")
    contract.require_match(contract)
    for field, value in [
        ("release", "DR24"),
        ("target_sample", "M"),
        ("transit_criterion", "any_overlap"),
        ("calibration", "calibration2"),
    ]:
        with pytest.raises(ValueError):
            contract.require_match(replace(contract, **{field: value}))


def test_empty_and_extreme_binomial_cells():
    result = binomial_efficiency([0, 0, 10], [0, 10, 10])
    assert np.isnan(result["mean"][0])
    assert result["upper"][1] > 0
    assert result["lower"][2] < 1
    assert result["mean"][1] + result["mean"][2] == pytest.approx(1)
    for k, n in [(-1, 10), (11, 10), (1.5, 10), (1, np.inf)]:
        with pytest.raises(ValueError):
            binomial_efficiency(k, n)


def test_ipac_and_original_stellar_contracts():
    assert len(parse_ipac(ipac_bytes(injection_fixture()), kind="injections")) == 3
    payload = ipac_bytes(vetting_fixture())
    assert len(parse_ipac(payload, kind="vetting")) == 2
    with pytest.raises(ValueError, match="INJ1"):
        parse_ipac(payload.replace(b"INJ1", b"INJ2"), kind="vetting")
    with pytest.raises(ValueError, match="row count"):
        parse_ipac(
            payload.replace(b"nrows=2", b"nrows=3").replace(b"nrows = 2", b"nrows = 3"),
            kind="vetting",
        )
    stars = star_fixture()
    assert len(parse_stars(stars.to_csv(index=False).encode())) == 3
    stars.loc[0, "st_delivname"] = "supplemental"
    with pytest.raises(ValueError, match="release"):
        parse_stars(stars.to_csv(index=False).encode())


def test_join_normalises_ids_preserves_failure_and_uses_injected_radius():
    joined = join_injections(injection_fixture(), vetting_fixture(), star_fixture())
    assert joined["pipeline_recovered"].tolist() == [True, True, False]
    assert joined["vetted_pc"].tolist() == [True, False, False]
    assert joined["injected_radius_earth"].iloc[0] == pytest.approx(1, abs=0.002)
    with pytest.raises(ValueError, match="no matching"):
        join_injections(injection_fixture(), vetting_fixture().iloc[:1], star_fixture())
    wrong = vetting_fixture()
    wrong.loc[0, "KIC"] = 999
    with pytest.raises(ValueError, match="disagree"):
        join_injections(injection_fixture(), wrong, star_fixture())


def test_grid_counts_and_unsupported_cells():
    joined = join_injections(injection_fixture(), vetting_fixture(), star_fixture())
    grid = empirical_grid(joined, [0.5, 1.5, 3], [1, 50, 200, 500])
    assert grid["n_injected"].sum() == 3
    assert grid["n_recovered"].sum() == 2
    assert grid["n_vetted_pc"].sum() == 1
    assert grid.loc[grid["n_injected"].eq(0), "pipeline_mean"].isna().all()
    assert grid.loc[grid["n_recovered"].eq(0), "vetting_given_recovered_mean"].isna().all()
    assert set(grid["label"]) == {"SIMULATED"}


def test_archive_code_two_requires_matching_official_tce_and_remains_visible():
    injections = injection_fixture()
    injections.loc[0, "Recovered"] = 2
    parsed = parse_ipac(ipac_bytes(injections), kind="injections")
    joined = join_injections(parsed, vetting_fixture(), star_fixture())
    assert joined["recovery_code_2"].tolist() == [True, False, False]
    assert joined["pipeline_recovered"].sum() == 2
    with pytest.raises(ValueError, match="no matching"):
        join_injections(parsed, vetting_fixture().iloc[1:], star_fixture())
    injections.loc[0, "Recovered"] = 3
    with pytest.raises(ValueError, match="flag"):
        parse_ipac(ipac_bytes(injections), kind="injections")


def test_stellar_selection_rejects_nonfinite_and_records_missing_hosts():
    stars = star_fixture()
    stars.loc[1, "mass"] = np.inf
    stars.loc[2, "rrmscdpp06p0"] = np.nan
    assert StellarSelection().select(stars).tolist() == [True, False, False]
    joined = join_injections(injection_fixture(), vetting_fixture(), stars.iloc[:2])
    assert joined["kepid"].isna().sum() == 1


def test_archive_integrity_no_redating_or_network_on_cache(tmp_path, monkeypatch):
    payload = star_fixture().to_csv(index=False).encode()

    class Response:
        headers = {"Content-Length": str(len(payload))}
        url = archive.SPECS["stars"]["url"]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def raise_for_status(self):
            pass

        def iter_content(self, **kwargs):
            yield payload

    class Session:
        calls = 0

        def get(self, *args, **kwargs):
            self.calls += 1
            return Response()

    monkeypatch.setattr(archive.subprocess, "check_output", lambda *a, **k: "a" * 40)
    monkeypatch.setattr(archive.shutil, "which", lambda x: x)
    session = Session()
    _, original = archive.fetch_product(tmp_path, "stars", session=session)
    _, cached = archive.fetch_product(tmp_path, "stars", session=session)
    assert original == cached
    assert session.calls == 1
    raw = tmp_path / original["raw_path"]
    raw.write_bytes(payload + b"\n")
    with pytest.raises(ValueError, match="integrity"):
        archive.fetch_product(tmp_path, "stars", session=session)
    raw.write_bytes(payload)
    path = tmp_path / "data/manifests/population/dr25_stars.json"
    altered = json.loads(path.read_text())
    altered["row_count"] = 4
    path.write_text(json.dumps(altered))
    with pytest.raises(ValueError, match="row count"):
        archive.fetch_product(tmp_path, "stars", session=session)


def test_archive_incomplete_cache_fails_closed(tmp_path):
    raw = tmp_path / "data/raw/kepler_dr25/stars.csv"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"partial")
    with pytest.raises(ValueError, match="Incomplete"):
        archive.fetch_product(tmp_path, "stars")
