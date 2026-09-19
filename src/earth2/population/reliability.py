"""Pinned DR25 reliability inputs and non-parametric diagnostic contracts.

This module deliberately stops before assigning a reliability to an individual
planet candidate. The observed, inverted and scrambled samples first expose the
finite cell counts and the algebraic reliability diagnostic. A smooth model and
its uncertainty must pass separate validation before entering an occurrence
likelihood.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from earth2.population.completeness import binomial_efficiency
from earth2.population.kepler import ROBOVETTER_COLUMNS, StellarSelection, normalise_tce

REPOSITORY = "https://github.com/stevepur/DR25-occurrence-public"
REPOSITORY_COMMIT = "d200f54b6f0df49e0dae530e69983cdce5397bfb"
RAW_BASE = (
    "https://raw.githubusercontent.com/stevepur/DR25-occurrence-public/"
    + REPOSITORY_COMMIT
    + "/data/"
)

SUPPORT_SPECS: dict[str, dict] = {
    "droplist_inv": {
        "filename": "kplr_droplist_inv.txt",
        "experiment": "INV",
        "expected_rows": 4583,
        "sha256": "e9ba1d8b530fd7954793044d461792301cfed7eed4255a530495ba6c37abd500",
        "git_blob_sha1": "14e8bdc473046e2fc9437e230793d401d30b62f9",
    },
    "droplist_scr1": {
        "filename": "kplr_droplist_scr1.txt",
        "experiment": "SCR1",
        "expected_rows": 10973,
        "sha256": "d434f3eaed4aa4b84d938b36a874a2a1edb706e9f21ad940de470019b22b6036",
        "git_blob_sha1": "c00438b535c316a1b5a4775b0b4b3b6bfc8a7869",
    },
    "droplist_scr2": {
        "filename": "kplr_droplist_scr2.txt",
        "experiment": "SCR2",
        "expected_rows": 10901,
        "sha256": "2532b7389072ab0e41ed89933fc103ff6a7168680e14d9bf138f37468d95379e",
        "git_blob_sha1": "f53cf218b724f22fd47554f81ced2743749f59ab",
    },
    "droplist_scr3": {
        "filename": "kplr_droplist_scr3.txt",
        "experiment": "SCR3",
        "expected_rows": 11399,
        "sha256": "4c1c313df6e6574c1b54cf6410601dab23009b3e2209cea924a2b219cb5b11a7",
        "git_blob_sha1": "29dce339b322eadd3e3f2259f7a2bcfd1cdb827a",
    },
    "koifpp": {
        "filename": "q1_q17_dr25_koifpp.txt",
        "experiment": None,
        "expected_rows": 8054,
        "sha256": "ffeeb339d67d032bf7b9617d3f6efa597af58f0b8abfd808471beaac992c15da",
        "git_blob_sha1": "dc584a93d7d45a703cede85fa802d9b390a45dfa",
    },
}

FPP_COLUMNS = {"rowid", "kepid", "kepoi_name", "fpp_koi_period", "fpp_prob"}
KOI_COLUMNS = {
    "kepid",
    "kepoi_name",
    "koi_pdisposition",
    "koi_score",
    "koi_period",
    "koi_prad",
    "koi_model_snr",
    "koi_tce_plnt_num",
    "koi_fpflag_nt",
    "koi_fpflag_ss",
    "koi_fpflag_co",
    "koi_fpflag_ec",
}

# These NTL=0 observed false positives were retained as instrumental artifacts
# after visual inspection in the pinned occurrence-code notebook. The other
# NTL=0 observed false positives are treated as astrophysical false positives.
MANUAL_FALSE_ALARM_TCES = frozenset(
    {
        "002716853-02",
        "004371172-01",
        "004557341-01",
        "009394762-01",
        "011401822-02",
    }
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()  # noqa: S324


def parse_droplist(payload: bytes, *, experiment: str) -> pd.DataFrame:
    """Parse a pinned known-signal drop list without discarding its identifiers."""
    if experiment not in {"INV", "SCR1", "SCR2", "SCR3"}:
        raise ValueError("Unsupported drop-list experiment")
    lines = [
        line.strip()
        for line in payload.decode("utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines or lines[0] != "TCE_ID":
        raise ValueError("Drop-list schema drift: expected a TCE_ID header")
    identifiers = [normalise_tce(value) for value in lines[1:]]
    if any(value is None for value in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError("Drop list contains a missing or duplicate TCE identifier")
    frame = pd.DataFrame({"TCE_ID": identifiers})
    frame.attrs["experiment"] = experiment
    return frame


def parse_fpp(payload: bytes) -> pd.DataFrame:
    """Parse the DR25 astrophysical false-positive probabilities."""
    frame = pd.read_csv(io.BytesIO(payload), comment="#")
    missing = FPP_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"FPP schema drift: missing {sorted(missing)}")
    if frame["rowid"].isna().any() or frame["rowid"].duplicated().any():
        raise ValueError("FPP table has a missing or duplicate row identifier")
    if frame["kepoi_name"].isna().any() or frame["kepoi_name"].duplicated().any():
        raise ValueError("FPP table has a missing or duplicate KOI identifier")
    if not frame["kepoi_name"].astype(str).str.fullmatch(r"K\d{5}\.\d{2}").all():
        raise ValueError("FPP table has an invalid KOI identifier")
    if frame["kepid"].isna().any() or not np.all(frame["kepid"].to_numpy(float) > 0):
        raise ValueError("FPP table has an invalid target identifier")
    periods = frame["fpp_koi_period"].to_numpy(float)
    finite_fpp = frame["fpp_prob"].dropna().to_numpy(float)
    if not np.isfinite(periods).all() or np.any(periods <= 0):
        raise ValueError("FPP table has an invalid period")
    if not np.isfinite(finite_fpp).all() or np.any((finite_fpp < 0) | (finite_fpp > 1)):
        raise ValueError("FPP probabilities must be in [0, 1] or explicitly missing")
    return frame


def validate_support_payload(payload: bytes, kind: str) -> pd.DataFrame:
    if kind not in SUPPORT_SPECS:
        raise ValueError(f"Unsupported DR25 reliability support product: {kind}")
    spec = SUPPORT_SPECS[kind]
    if _sha256(payload) != spec["sha256"]:
        raise ValueError(f"Pinned SHA-256 mismatch for {kind}")
    if _git_blob_sha1(payload) != spec["git_blob_sha1"]:
        raise ValueError(f"Pinned Git blob mismatch for {kind}")
    frame = (
        parse_fpp(payload)
        if kind == "koifpp"
        else parse_droplist(payload, experiment=spec["experiment"])
    )
    if len(frame) != spec["expected_rows"]:
        raise ValueError(
            f"Unexpected {kind} row count: {len(frame)}; expected {spec['expected_rows']}"
        )
    return frame


def fetch_support_product(
    root: Path, kind: str, *, session=None, max_bytes: int = 5_000_000
) -> tuple[pd.DataFrame, dict]:
    """Fetch or verify one commit-pinned reliability support product.

    A manifest-only clean checkout may restore its ignored raw file only when
    the downloaded source, commit, bytes, digest and row count all match the
    committed manifest. Raw-only partial caches remain invalid.
    """
    if kind not in SUPPORT_SPECS:
        raise ValueError(f"Unsupported DR25 reliability support product: {kind}")
    spec = SUPPORT_SPECS[kind]
    source_url = RAW_BASE + spec["filename"]
    raw = root / "data/raw/kepler_dr25" / f"{kind}.txt"
    manifest_path = root / "data/manifests/population" / f"dr25_{kind}.json"
    if raw.exists() and not manifest_path.exists():
        raise ValueError(f"Incomplete cache for {kind}: raw payload has no manifest")
    pinned_manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else None
    )
    if raw.exists() and pinned_manifest is not None:
        payload = raw.read_bytes()
        if (
            pinned_manifest["source_url"] != source_url
            or pinned_manifest["repository_commit"] != REPOSITORY_COMMIT
            or pinned_manifest["sha256"] != _sha256(payload)
            or pinned_manifest["bytes"] != len(payload)
        ):
            raise ValueError(f"Cache integrity or source mismatch for {kind}")
        frame = validate_support_payload(payload, kind)
        if pinned_manifest["row_count"] != len(frame):
            raise ValueError("Cached support manifest row count mismatch")
        return frame, pinned_manifest

    owned_session = session is None
    if owned_session:
        session = requests.Session()
        session.mount(
            "https://",
            HTTPAdapter(
                max_retries=Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET"],
                )
            ),
        )
    try:
        with session.get(source_url, stream=True, timeout=(20, 120)) as response:
            response.raise_for_status()
            if int(response.headers.get("Content-Length", 0)) > max_bytes:
                raise ValueError("Support product exceeds configured download bound")
            chunks, total = [], 0
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("Support product exceeds configured download bound")
                chunks.append(chunk)
            payload = b"".join(chunks)
            resolved_url = response.url
    finally:
        if owned_session:
            session.close()

    frame = validate_support_payload(payload, kind)
    if pinned_manifest is not None:
        if (
            pinned_manifest["source_url"] != source_url
            or pinned_manifest["repository_commit"] != REPOSITORY_COMMIT
            or pinned_manifest["sha256"] != _sha256(payload)
            or pinned_manifest["bytes"] != len(payload)
            or pinned_manifest["row_count"] != len(frame)
        ):
            raise ValueError(f"Downloaded payload does not match pinned manifest for {kind}")
        raw.parent.mkdir(parents=True, exist_ok=True)
        with raw.open("xb") as stream:
            stream.write(payload)
        return frame, pinned_manifest

    git = shutil.which("git.exe") or shutil.which("git")
    if git is None:
        raise RuntimeError("Git is required to record software provenance")
    software_commit = subprocess.check_output(
        [git, "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    manifest = {
        "schema_version": "1.0",
        "product": kind,
        "survey": "Kepler",
        "release": "DR25",
        "experiment": spec["experiment"],
        "source_url": source_url,
        "resolved_url": resolved_url,
        "repository": REPOSITORY,
        "repository_commit": REPOSITORY_COMMIT,
        "upstream_git_blob_sha1": spec["git_blob_sha1"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": len(frame),
        "missing_fpp_probabilities": int(frame["fpp_prob"].isna().sum())
        if kind == "koifpp"
        else None,
        "sha256": _sha256(payload),
        "bytes": len(payload),
        "software_commit": software_commit,
        "adapter_sha256": _sha256(Path(__file__).read_bytes()),
        "raw_path": raw.relative_to(root).as_posix(),
        "evidence_role": "Known-signal exclusions"
        if kind.startswith("droplist_")
        else "Astrophysical false-positive probability",
        "licence": "Not asserted; retain upstream attribution and consult source terms.",
    }
    if manifest["missing_fpp_probabilities"] is None:
        del manifest["missing_fpp_probabilities"]
    raw.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with raw.open("xb") as stream:
        stream.write(payload)
    with manifest_path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return frame, manifest


@dataclass(frozen=True)
class ReliabilityDomain:
    period_min_days: float = 50.0
    period_max_days: float = 600.0
    radius_min_earth: float = 0.5
    radius_max_earth: float = 15.0
    mes_min: float = 7.0
    mes_max: float = 30.0

    def mask(self, frame: pd.DataFrame) -> pd.Series:
        values = np.asarray(list(asdict(self).values()), float)
        if not np.isfinite(values).all() or np.any(values <= 0):
            raise ValueError("Reliability domain bounds must be finite and positive")
        if (
            self.period_min_days >= self.period_max_days
            or self.radius_min_earth >= self.radius_max_earth
            or self.mes_min >= self.mes_max
        ):
            raise ValueError("Reliability domain bounds are reversed")
        required = {"period", "Rp", "MES"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Reliability frame is missing {sorted(missing)}")
        return (
            frame["period"].between(self.period_min_days, self.period_max_days)
            & frame["Rp"].between(self.radius_min_earth, self.radius_max_earth)
            & frame["MES"].between(self.mes_min, self.mes_max)
        )


@dataclass(frozen=True)
class AnalysisPopulation:
    period_min_days: float = 50.0
    period_max_days: float = 500.0
    radius_min_earth: float = 0.5
    radius_max_earth: float = 2.0
    comparison_period_min_days: float = 237.0
    comparison_period_max_days: float = 500.0
    comparison_radius_min_earth: float = 0.75
    comparison_radius_max_earth: float = 1.5


def clean_false_alarm_experiments(
    experiments: dict[str, pd.DataFrame],
    drop_lists: dict[str, pd.DataFrame],
    selected_kepids,
) -> tuple[pd.DataFrame, list[dict]]:
    """Apply experiment-matched known-signal exclusions and the stellar sample."""
    expected = {"INV", "SCR1", "SCR2", "SCR3"}
    if set(experiments) != expected or set(drop_lists) != expected:
        raise ValueError("Reliability cleaning requires INV and all three SCR experiments")
    selected = {int(value) for value in selected_kepids}
    frames, audit = [], []
    for experiment in ("INV", "SCR1", "SCR2", "SCR3"):
        frame = experiments[experiment].copy()
        missing = ROBOVETTER_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"{experiment} schema is missing {sorted(missing)}")
        drop = drop_lists[experiment]
        if set(drop.columns) != {"TCE_ID"} or drop["TCE_ID"].duplicated().any():
            raise ValueError(f"Invalid {experiment} drop list")
        identifiers = set(drop["TCE_ID"])
        dropped = frame["TCE_ID"].isin(identifiers)
        target = frame["KIC"].astype(int).isin(selected)
        kept = frame.loc[~dropped & target].copy()
        kept["experiment"] = experiment
        kept["evidence_label"] = "SIMULATED"
        frames.append(kept)
        audit.append(
            {
                "experiment": experiment,
                "input_rows": len(frame),
                "drop_list_rows": len(drop),
                "drop_list_matches": int(dropped.sum()),
                "drop_list_ids_absent_from_delivered_table": int(
                    len(identifiers - set(frame.TCE_ID))
                ),
                "rows_after_drop_list": int((~dropped).sum()),
                "rows_after_stellar_selection": len(kept),
            }
        )
    return pd.concat(frames, ignore_index=True), audit


def classify_observed_false_alarms(
    observed: pd.DataFrame,
    selected_kepids,
    *,
    banned_tces=(),
    manual_false_alarm_tces=MANUAL_FALSE_ALARM_TCES,
) -> tuple[pd.DataFrame, dict]:
    """Separate instrumental false alarms from astrophysical false positives."""
    missing = ROBOVETTER_COLUMNS - set(observed.columns)
    if missing:
        raise ValueError(f"Observed TCE schema is missing {sorted(missing)}")
    selected = {int(value) for value in selected_kepids}
    banned = {normalise_tce(value) for value in banned_tces}
    manual = {normalise_tce(value) for value in manual_false_alarm_tces}
    all_ids = set(observed["TCE_ID"])
    frame = observed.loc[
        observed["KIC"].astype(int).isin(selected) & ~observed["TCE_ID"].isin(banned)
    ].copy()
    frame["observed_false_alarm"] = frame["NTL"].eq(1) | frame["TCE_ID"].isin(manual)
    frame["astrophysical_false_positive"] = frame["Disp"].eq("FP") & ~frame["observed_false_alarm"]
    frame["evidence_label"] = "OBSERVED"
    audit = {
        "input_rows": len(observed),
        "banned_tce_ids": len(banned),
        "banned_tce_matches": int(observed["TCE_ID"].isin(banned).sum()),
        "manual_false_alarm_ids": len(manual),
        "manual_false_alarm_ids_present": len(manual & all_ids),
        "rows_after_stellar_selection_and_ban": len(frame),
        "observed_false_alarms": int(frame["observed_false_alarm"].sum()),
        "astrophysical_false_positives": int(frame["astrophysical_false_positive"].sum()),
    }
    return frame, audit


def _validate_edges(edges, *, name: str) -> np.ndarray:
    values = np.asarray(edges, float)
    if (
        values.ndim != 1
        or len(values) < 2
        or not np.isfinite(values).all()
        or np.any(np.diff(values) <= 0)
    ):
        raise ValueError(f"{name} edges must be finite and strictly increasing")
    return values


def reliability_grid(
    synthetic: pd.DataFrame,
    observed: pd.DataFrame,
    period_edges,
    mes_edges,
    *,
    domain: ReliabilityDomain = ReliabilityDomain(),
    seed: int = 24051990,
    posterior_draws: int = 20000,
    minimum_synthetic_trials: int = 100,
    minimum_observed_trials: int = 20,
) -> pd.DataFrame:
    """Build an auditable cell diagnostic for Bryson et al. Eq. 8.

    The four manipulation files are pooled as unique delivered trials. This is
    intentionally distinct from the published occurrence-code design weighting,
    which repeats the single INV sample three times to match three SCR samples.
    """
    pe = _validate_edges(period_edges, name="Period")
    me = _validate_edges(mes_edges, name="MES")
    if pe[0] != domain.period_min_days or pe[-1] != domain.period_max_days:
        raise ValueError("Period grid must span the declared reliability domain")
    if me[0] != domain.mes_min or me[-1] != domain.mes_max:
        raise ValueError("MES grid must span the declared reliability domain")
    if posterior_draws < 1000 or minimum_synthetic_trials <= 0 or minimum_observed_trials <= 0:
        raise ValueError("Reliability sampling and support thresholds are too small")
    if "observed_false_alarm" not in observed:
        raise ValueError("Observed false-alarm classification is required")

    synth = synthetic.loc[domain.mask(synthetic)]
    obs = observed.loc[domain.mask(observed)]
    synth_n = np.histogram2d(synth["period"], synth["MES"], bins=[pe, me])[0].astype(int)
    synth_fp = np.histogram2d(
        synth.loc[synth["Disp"].eq("FP"), "period"],
        synth.loc[synth["Disp"].eq("FP"), "MES"],
        bins=[pe, me],
    )[0].astype(int)
    obs_n = np.histogram2d(obs["period"], obs["MES"], bins=[pe, me])[0].astype(int)
    obs_fa = np.histogram2d(
        obs.loc[obs["observed_false_alarm"], "period"],
        obs.loc[obs["observed_false_alarm"], "MES"],
        bins=[pe, me],
    )[0].astype(int)
    effectiveness = binomial_efficiency(synth_fp, synth_n)
    observed_fraction = binomial_efficiency(obs_fa, obs_n)
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(len(pe) - 1):
        for j in range(len(me) - 1):
            ns, ks = int(synth_n[i, j]), int(synth_fp[i, j])
            no, ko = int(obs_n[i, j]), int(obs_fa[i, j])
            e = ks / ns if ns else np.nan
            f = ko / no if no else np.nan
            point = 1 - (f / (1 - f)) * ((1 - e) / e) if e > 0 and f < 1 else np.nan
            q025 = q50 = q975 = physical_fraction = np.nan
            if ns and no:
                e_draw = rng.beta(ks + 0.5, ns - ks + 0.5, posterior_draws)
                f_draw = rng.beta(ko + 0.5, no - ko + 0.5, posterior_draws)
                r_draw = 1 - (f_draw / (1 - f_draw)) * ((1 - e_draw) / e_draw)
                q025, q50, q975 = np.quantile(r_draw, [0.025, 0.5, 0.975])
                physical_fraction = float(np.mean((r_draw >= 0) & (r_draw <= 1)))
            if not ns or not no:
                status = "undefined_empty_component"
            elif ns < minimum_synthetic_trials or no < minimum_observed_trials:
                status = "low_finite_sample_support"
            elif not np.isfinite(point) or not 0 <= point <= 1:
                status = "point_outside_probability_space"
            else:
                status = "diagnostic_supported"
            rows.append(
                {
                    "period_lower_days": pe[i],
                    "period_upper_days": pe[i + 1],
                    "mes_lower": me[j],
                    "mes_upper": me[j + 1],
                    "synthetic_trials_unique": ns,
                    "synthetic_rejected_as_fp": ks,
                    "false_alarm_effectiveness": e,
                    "false_alarm_effectiveness_lower": effectiveness["lower"][i, j],
                    "false_alarm_effectiveness_upper": effectiveness["upper"][i, j],
                    "false_alarm_effectiveness_label": "SIMULATED",
                    "observed_tces": no,
                    "observed_instrumental_false_alarms": ko,
                    "observed_false_alarm_fraction": f,
                    "observed_false_alarm_fraction_lower": observed_fraction["lower"][i, j],
                    "observed_false_alarm_fraction_upper": observed_fraction["upper"][i, j],
                    "observed_false_alarm_fraction_label": "OBSERVED",
                    "false_alarm_reliability_point": point,
                    "false_alarm_reliability_p025_raw": q025,
                    "false_alarm_reliability_p50_raw": q50,
                    "false_alarm_reliability_p975_raw": q975,
                    "posterior_draw_fraction_in_probability_space": physical_fraction,
                    "false_alarm_reliability_label": "MODEL-INFERRED",
                    "status": status,
                }
            )
    return pd.DataFrame(rows)


def build_analysis_population(
    stars: pd.DataFrame,
    koi: pd.DataFrame,
    fpp: pd.DataFrame,
    observed: pd.DataFrame,
    *,
    stellar_selection: StellarSelection = StellarSelection(),
    population: AnalysisPopulation = AnalysisPopulation(),
) -> tuple[pd.DataFrame, dict]:
    """Apply one explicit stellar/candidate/domain contract to every DR25 KOI."""
    missing = KOI_COLUMNS - set(koi.columns)
    if missing:
        raise ValueError(f"KOI schema is missing {sorted(missing)}")
    if koi["kepoi_name"].isna().any() or koi["kepoi_name"].duplicated().any():
        raise ValueError("KOI identifiers must be present and unique")
    flags = ["koi_fpflag_nt", "koi_fpflag_ss", "koi_fpflag_co", "koi_fpflag_ec"]
    if not koi[flags].isin([0, 1]).all().all():
        raise ValueError("KOI false-positive flags must be binary")
    if len(fpp) != len(koi):
        raise ValueError("FPP and KOI release row counts differ")

    selected_kepids = set(stars.loc[stellar_selection.select(stars), "kepid"].astype(int).tolist())
    frame = koi.copy()
    tce_number = frame["koi_tce_plnt_num"].to_numpy(float)
    if not np.isfinite(tce_number).all() or np.any(tce_number != np.floor(tce_number)):
        raise ValueError("KOI TCE planet numbers must be finite integers")
    frame["TCE_ID"] = [
        f"{int(kepid):09d}-{int(number):02d}"
        for kepid, number in zip(frame["kepid"], frame["koi_tce_plnt_num"])
    ]
    if frame["TCE_ID"].duplicated().any():
        raise ValueError("Constructed KOI TCE identifiers are not unique")
    frame = frame.merge(
        fpp,
        on=["kepid", "kepoi_name"],
        how="left",
        validate="one_to_one",
        indicator="fpp_join",
    )
    if not frame["fpp_join"].eq("both").all():
        raise ValueError("Every KOI must match the pinned FPP release by target and KOI")

    observed_columns = observed[["TCE_ID", "Disp", "Score", "MES", "period"]].rename(
        columns={
            "Disp": "observed_tce_disposition",
            "Score": "observed_tce_score",
            "MES": "observed_tce_mes",
            "period": "observed_tce_period_days",
        }
    )
    frame = frame.merge(observed_columns, on="TCE_ID", how="left", validate="one_to_one")
    frame["stellar_selected"] = frame["kepid"].astype(int).isin(selected_kepids)
    frame["catalog_candidate"] = frame["koi_pdisposition"].eq("CANDIDATE") & frame[flags].eq(0).all(
        axis=1
    )
    frame["within_inference_domain"] = frame["koi_period"].between(
        population.period_min_days, population.period_max_days
    ) & frame["koi_prad"].between(population.radius_min_earth, population.radius_max_earth)
    frame["eligible"] = (
        frame["stellar_selected"]
        & frame["catalog_candidate"]
        & frame["within_inference_domain"]
        & np.isfinite(frame[["koi_model_snr", "koi_period", "koi_prad"]]).all(axis=1)
    )
    frame["published_comparison_box"] = (
        frame["eligible"]
        & frame["koi_period"].between(
            population.comparison_period_min_days, population.comparison_period_max_days
        )
        & frame["koi_prad"].between(
            population.comparison_radius_min_earth, population.comparison_radius_max_earth
        )
    )
    frame["astrophysical_planet_probability"] = 1 - frame["fpp_prob"]
    frame["astrophysical_planet_probability_label"] = "MODEL-INFERRED"
    frame["robovetter_score_is_candidate_reliability"] = False
    frame["false_alarm_reliability"] = np.nan
    frame["total_candidate_reliability"] = np.nan
    frame["reliability_status"] = "pending_validated_smooth_false_alarm_model"

    period_difference = (frame["koi_period"] - frame["fpp_koi_period"]).abs()
    eligible = frame["eligible"]
    audit = {
        "stellar_selection": asdict(stellar_selection),
        "population_contract": asdict(population),
        "archive_stellar_rows": len(stars),
        "selected_stars": len(selected_kepids),
        "koi_rows": len(frame),
        "catalog_candidates_after_flag_contract": int(frame["catalog_candidate"].sum()),
        "eligible_candidates": int(eligible.sum()),
        "published_comparison_box_candidates": int(frame["published_comparison_box"].sum()),
        "eligible_missing_fpp": int(frame.loc[eligible, "fpp_prob"].isna().sum()),
        "eligible_missing_observed_tce": int(
            frame.loc[eligible, "observed_tce_disposition"].isna().sum()
        ),
        "fpp_rows_with_missing_probability": int(frame["fpp_prob"].isna().sum()),
        "fpp_period_mismatch_over_one_day": int((period_difference > 1).sum()),
        "koi_score_used_as_reliability": False,
        "candidate_reliability_assignment": "pending_validated_smooth_false_alarm_model",
        "labels": {
            "catalog_and_tce_fields": "OBSERVED",
            "astrophysical_planet_probability": "MODEL-INFERRED",
            "future_false_alarm_reliability": "MODEL-INFERRED",
        },
    }
    return frame.sort_values(
        ["eligible", "koi_period", "koi_prad"], ascending=[False, True, True]
    ), audit
