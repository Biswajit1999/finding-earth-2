"""Scientific contract tests; no bulk archive request in the test suite."""

import io
import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from astropy.io import ascii
from astropy.table import Table

from earth2.population import archive, reliability
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
    parse_robovetter_ipac,
    parse_stars,
)
from earth2.population.reliability import (
    AnalysisPopulation,
    ReliabilityDomain,
    build_analysis_population,
    classify_observed_false_alarms,
    clean_false_alarm_experiments,
    parse_droplist,
    parse_fpp,
    reliability_grid,
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


def ipac_bytes(frame, runtype="INJ1"):
    table = Table.from_pandas(frame)
    table.meta["keywords"] = {"runtype": {"value": runtype}, "nrows": {"value": len(frame)}}
    output = io.StringIO()
    ascii.write(table, output, format="ipac")
    # The archive's metadata uses unquoted runtype, unlike the astropy writer.
    return output.getvalue().replace(f"'{runtype}'", runtype).encode()


def false_alarm_fixture():
    return pd.DataFrame(
        {
            "TCE_ID": ["000000001-01", "000000002-01"],
            "KIC": [1, 2],
            "Disp": ["FP", "PC"],
            "Score": [0.0, 0.8],
            "NTL": [1, 0],
            "SS": [0, 0],
            "CO": [0, 0],
            "EM": [0, 0],
            "period": [370.0, 250.0],
            "MES": [8.0, 12.0],
            "NTran": [0, 5],
            "Rp": [1.0, 2.0],
        }
    )


def koi_fixture():
    return pd.DataFrame(
        {
            "kepid": [1, 2],
            "kepoi_name": ["K00001.01", "K00002.01"],
            "koi_pdisposition": ["CANDIDATE", "FALSE POSITIVE"],
            "koi_score": [0.9, 0.1],
            "koi_period": [300.0, 100.0],
            "koi_prad": [1.0, 1.0],
            "koi_model_snr": [12.0, 10.0],
            "koi_tce_plnt_num": [1, 1],
            "koi_fpflag_nt": [0, 1],
            "koi_fpflag_ss": [0, 0],
            "koi_fpflag_co": [0, 0],
            "koi_fpflag_ec": [0, 0],
        }
    )


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


def test_false_alarm_parser_requires_exact_experiment_and_consistent_ids():
    payload = ipac_bytes(false_alarm_fixture(), runtype="INV")
    parsed = parse_robovetter_ipac(payload, experiment="INV")
    assert len(parsed) == 2
    assert parsed.attrs["declared_nrows"] == 2
    assert parsed.attrs["zero_ntran_rows"] == 1
    with pytest.raises(ValueError, match="SCR1"):
        parse_robovetter_ipac(payload, experiment="SCR1")
    bad_flag = false_alarm_fixture()
    bad_flag.loc[0, "NTL"] = 2
    with pytest.raises(ValueError, match="binary"):
        parse_robovetter_ipac(ipac_bytes(bad_flag, runtype="INV"), experiment="INV")
    bad_id = false_alarm_fixture()
    bad_id.loc[0, "KIC"] = 999
    with pytest.raises(ValueError, match="disagree"):
        parse_robovetter_ipac(ipac_bytes(bad_id, runtype="INV"), experiment="INV")


def test_pinned_reliability_support_parsers_preserve_missing_fpp():
    drop = parse_droplist(b"# known signals\nTCE_ID\n1-1\n000000002-01\n", experiment="INV")
    assert drop["TCE_ID"].tolist() == ["000000001-01", "000000002-01"]
    with pytest.raises(ValueError, match="duplicate"):
        parse_droplist(b"TCE_ID\n1-1\n1-1\n", experiment="INV")

    payload = (
        b"# provenance\nrowid,kepid,kepoi_name,fpp_koi_period,fpp_prob\n"
        b"1,1,K00001.01,300,0.25\n2,2,K00002.01,100,\n"
    )
    fpp = parse_fpp(payload)
    assert fpp["fpp_prob"].isna().sum() == 1
    assert fpp.loc[0, "fpp_prob"] == pytest.approx(0.25)
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        parse_fpp(payload.replace(b"0.25", b"1.25"))


def test_reliability_cleaning_classification_and_unclipped_equation():
    experiments = {
        experiment: false_alarm_fixture().copy() for experiment in ("INV", "SCR1", "SCR2", "SCR3")
    }
    drop_lists = {
        experiment: pd.DataFrame({"TCE_ID": ["000000002-01"]}) for experiment in experiments
    }
    clean, audit = clean_false_alarm_experiments(experiments, drop_lists, [1, 2])
    assert len(clean) == 4
    assert clean["Disp"].eq("FP").all()
    assert sum(row["drop_list_matches"] for row in audit) == 4

    observed, observed_audit = classify_observed_false_alarms(
        false_alarm_fixture(), [1, 2], manual_false_alarm_tces=[]
    )
    assert observed["observed_false_alarm"].tolist() == [True, False]
    assert observed_audit["observed_false_alarms"] == 1

    uncleaned = pd.concat(
        [frame.assign(experiment=name) for name, frame in experiments.items()],
        ignore_index=True,
    )
    grid = reliability_grid(
        uncleaned,
        observed,
        [50, 600],
        [7, 30],
        domain=ReliabilityDomain(),
        posterior_draws=1000,
        minimum_synthetic_trials=1,
        minimum_observed_trials=1,
    )
    assert grid.loc[0, "synthetic_trials_unique"] == 8
    assert grid.loc[0, "false_alarm_effectiveness"] == pytest.approx(0.5)
    assert grid.loc[0, "observed_false_alarm_fraction"] == pytest.approx(0.5)
    assert grid.loc[0, "false_alarm_reliability_point"] == pytest.approx(0)
    assert grid.loc[0, "status"] == "diagnostic_supported"
    assert set(
        grid.loc[
            0,
            [
                "false_alarm_effectiveness_label",
                "observed_false_alarm_fraction_label",
                "false_alarm_reliability_label",
            ],
        ]
    ) == {"SIMULATED", "OBSERVED", "MODEL-INFERRED"}


def test_analysis_population_contract_keeps_score_separate_from_reliability():
    fpp = pd.DataFrame(
        {
            "rowid": [1, 2],
            "kepid": [1, 2],
            "kepoi_name": ["K00001.01", "K00002.01"],
            "fpp_koi_period": [300.0, 100.0],
            "fpp_prob": [0.25, np.nan],
        }
    )
    population, audit = build_analysis_population(
        star_fixture(),
        koi_fixture(),
        fpp,
        false_alarm_fixture(),
        population=AnalysisPopulation(),
    )
    eligible = population.loc[population["eligible"]].iloc[0]
    assert eligible["kepoi_name"] == "K00001.01"
    assert eligible["published_comparison_box"]
    assert eligible["astrophysical_planet_probability"] == pytest.approx(0.75)
    assert not eligible["robovetter_score_is_candidate_reliability"]
    assert pd.isna(eligible["false_alarm_reliability"])
    assert audit["eligible_candidates"] == 1
    assert audit["koi_score_used_as_reliability"] is False


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


def test_archive_manifest_only_checkout_rehydrates_pinned_payload(tmp_path, monkeypatch):
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
    raw = tmp_path / original["raw_path"]
    raw.unlink()

    _, rehydrated = archive.fetch_product(tmp_path, "stars", session=session)

    assert rehydrated == original
    assert raw.read_bytes() == payload
    assert session.calls == 2


def test_archive_manifest_only_checkout_rejects_upstream_drift(tmp_path, monkeypatch):
    payload = star_fixture().to_csv(index=False).encode()
    manifest = {
        "source_url": archive.SPECS["stars"]["url"],
        "sha256": "0" * 64,
        "bytes": len(payload),
        "row_count": 3,
    }
    path = tmp_path / "data/manifests/population/dr25_stars.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(manifest))

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
        def get(self, *args, **kwargs):
            return Response()

    with pytest.raises(ValueError, match="does not match pinned manifest"):
        archive.fetch_product(tmp_path, "stars", session=Session())
    assert not (tmp_path / "data/raw/kepler_dr25/stars.csv").exists()


def test_support_manifest_only_checkout_rehydrates_pinned_payload(tmp_path, monkeypatch):
    payload = b"pinned support payload"
    frame = pd.DataFrame({"TCE_ID": ["000000001-01"]})

    class Response:
        headers = {"Content-Length": str(len(payload))}
        url = reliability.RAW_BASE + reliability.SUPPORT_SPECS["droplist_inv"]["filename"]

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

    monkeypatch.setattr(reliability, "validate_support_payload", lambda *args: frame)
    monkeypatch.setattr(reliability.subprocess, "check_output", lambda *a, **k: "a" * 40)
    monkeypatch.setattr(reliability.shutil, "which", lambda x: x)
    session = Session()
    _, original = reliability.fetch_support_product(
        tmp_path, "droplist_inv", session=session
    )
    raw = tmp_path / original["raw_path"]
    raw.unlink()

    _, rehydrated = reliability.fetch_support_product(
        tmp_path, "droplist_inv", session=session
    )

    assert rehydrated == original
    assert raw.read_bytes() == payload
    assert session.calls == 2
