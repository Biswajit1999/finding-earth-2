"""The analysis pipeline.

One deterministic path from retrieved archive tables to published results::

    load -> build catalogue -> propagate uncertainties -> rank -> report

Every stage appends to a :class:`~earth2.provenance.TransformLedger`, which is
written alongside the results so any published number can be traced back through
the transformations that produced it to the archive row it came from.

Run with ``python -m earth2 analyse``.
"""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import pandas as pd

from earth2 import __version__
from earth2.config import (
    N_MONTE_CARLO,
    PROCESSED_DIR,
    RANDOM_SEED,
    RESULTS_DIR,
    ensure_dirs,
)
from earth2.preprocessing import build_catalogue
from earth2.provenance import ManifestStore, TransformLedger, utc_now_iso
from earth2.provenance.reflink import measurement_provenance_table, reference_summary
from earth2.ranking import ScoreWeights, rank_catalogue
from earth2.reporting.summary import build_analysis_summary, coverage_table, write_summary
from earth2.uncertainty import propagate_catalogue, summarise_samples

__all__ = ["load_processed", "run_analysis"]

#: Result artefacts written by a full run.
RESULT_FILES = {
    "ranking_csv": "candidate_ranking.csv",
    "ranking_parquet": "candidate_ranking.parquet",
    "coverage_csv": "data_coverage.csv",
    "summary_json": "analysis_summary.json",
    "provenance_json": "provenance_manifest.json",
    "ledger_json": "transformation_ledger.json",
    "catalogue_parquet": "analysis_catalogue.parquet",
    "measurement_provenance_csv": "measurement_provenance.csv.gz",
}


def load_processed(name: str) -> pd.DataFrame | None:
    """Load a synced archive table, or None if it was never retrieved."""
    p = PROCESSED_DIR / (name + ".parquet")
    if not p.exists():
        return None
    return pd.read_parquet(p)


def _softwareversions() -> dict[str, str]:
    import platform

    import astropy
    import scipy

    return {
        "earth2": __version__,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "astropy": astropy.__version__,
        "platform": platform.platform(),
    }


def run_analysis(
    n_monte_carlo: int = N_MONTE_CARLO,
    seed: int = RANDOM_SEED,
    weights: ScoreWeights | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """Execute the full analysis and write every result artefact.

    Returns the analysis summary dictionary.
    """
    ensure_dirs()
    t_start = time.time()
    ledger = TransformLedger("earth2-analysis")

    def say(msg: str) -> None:
        if verbose:
            print(msg)

    say("Finding Earth 2.0 -- analysis pipeline")
    say("=" * 66)

    # ---------------------------------------------------------------- load
    pscomppars = load_processed("nasa_pscomppars")
    if pscomppars is None:
        raise FileNotFoundError(
            "No synced catalogue found. Run `python -m earth2 sync` first."
        )
    ps = load_processed("nasa_ps")
    transitspec = load_processed("nasa_transitspec")
    emissionspec = load_processed("nasa_emissionspec")
    spectra_index = load_processed("nasa_spectra_index")
    toi = load_processed("nasa_toi")
    koi = load_processed("nasa_koi_dr25")
    k2 = load_processed("nasa_k2pandc")
    tce = load_processed("nasa_tce_dr25")
    gaia = load_processed("gaia_dr3_crossmatch")

    ledger.add(
        "load_processed_tables",
        "Load synced archive tables from the local Parquet cache.",
        inputs=[k for k, v in [
            ("nasa_pscomppars", pscomppars), ("nasa_ps", ps),
            ("nasa_transitspec", transitspec), ("nasa_emissionspec", emissionspec),
            ("nasa_toi", toi), ("nasa_koi_dr25", koi), ("nasa_k2pandc", k2),
            ("nasa_tce_dr25", tce), ("gaia_dr3_crossmatch", gaia),
        ] if v is not None],
        outputs=["dataframes"],
        n_rows_in=0,
        n_rows_out=int(len(pscomppars)),
        software=json.dumps(_softwareversions()),
    )
    say("  loaded %d confirmed-planet rows" % len(pscomppars))

    # ------------------------------------------------------------ catalogue
    catalogue = build_catalogue(
        pscomppars, ps, transitspec, emissionspec, gaia, include_controls=True, ledger=ledger
    )
    say("  built catalogue: %d rows (%d controls)"
        % (len(catalogue), int(catalogue["is_control"].sum())))

    # ---------------------------------------------------------- uncertainty
    say("  propagating uncertainties (%d samples/planet, seed %d)..." % (n_monte_carlo, seed))
    t0 = time.time()
    mc = propagate_catalogue(catalogue, n_samples=n_monte_carlo, seed=seed)
    catalogue = catalogue.reset_index(drop=True).join(mc.frame.drop(columns=["pl_name"]))
    mc_stats = summarise_samples(mc)
    ledger.add(
        "monte_carlo_propagation",
        "Sample every parameter with a published uncertainty from a two-piece normal and "
        "recompute all derived quantities per draw, yielding posterior percentiles and "
        "habitable-zone membership probabilities.",
        inputs=list(mc.parameters),
        outputs=["esi_global_p16/p50/p84", "hz_conservative_prob", "hz_optimistic_prob"],
        parameters={"n_samples": n_monte_carlo, "seed": seed,
                    "distribution": "two-piece (split) normal"},
        n_rows_in=len(catalogue), n_rows_out=len(catalogue),
    )
    say("    done in %.1fs; %d planets have an ESI posterior"
        % (time.time() - t0, mc_stats["n_with_esi_posterior"]))

    # --------------------------------------------------------------- rank
    w = weights or ScoreWeights()
    ranked = rank_catalogue(catalogue, weights=w)
    ledger.add(
        "rank_candidates",
        "Compute four interpretable component scores and combine the weighted ones with a "
        "weighted GEOMETRIC mean, so a disqualifying component cannot be compensated by "
        "strong performance elsewhere.",
        inputs=["score_earth_similarity", "score_conservative_habitability",
                "score_observational_confidence", "score_characterisation_potential"],
        outputs=["earth2_index", "earth2_rank"],
        parameters={"weights": w.normalised(), "combination": "weighted geometric mean",
                    "epsilon_floor": 0.01},
        citation="kopparapu2013,schulzemakuch2011,rogers2015,kempton2018",
        n_rows_in=len(catalogue), n_rows_out=len(ranked),
    )
    n_rankable = int(ranked["rankable"].sum())
    say("  ranked %d of %d rows" % (n_rankable, len(ranked)))

    # ------------------------------------------------------------- outputs
    export_cols = [
        "pl_name", "hostname", "pl_letter", "is_control",
        "earth2_rank", "earth2_index", "rankable",
        "score_earth_similarity", "score_conservative_habitability",
        "score_observational_confidence", "score_characterisation_potential",
        "rank_earth_similarity", "rank_conservative_habitability",
        "rank_observational_confidence", "rank_characterisation_potential",
        "esi_global", "esi_global_p16", "esi_global_p50", "esi_global_p84",
        "esi_interior", "esi_surface",
        "hz_conservative", "hz_optimistic",
        "hz_conservative_prob", "hz_optimistic_prob", "hz_position_conservative",
        "hz_conservative_clamped", "hz_optimistic_clamped",
        "hz_model_extrapolated", "hz_teff_in_range", "hz_teff_valid_fraction",
        "hz_teff_offset_from_range_k",
        "rocky_plausibility",
        "pl_rade", "pl_radeerr1", "pl_radeerr2", "pl_rade_p16", "pl_rade_p50", "pl_rade_p84",
        "pl_bmasse", "pl_bmasseerr1", "pl_bmasseerr2", "mass_class",
        "pl_dens_used", "esi_density_source", "pl_vesc_kms",
        "insol_used", "insol_source", "teq_used", "teq_source", "teq_albedo_assumed",
        "pl_orbper", "pl_orbsmax", "pl_orbeccen",
        "st_teff", "st_rad", "st_mass", "st_lum", "st_met", "st_age", "st_spectype",
        "sy_dist", "ra", "dec", "sy_vmag", "sy_jmag", "sy_kmag", "sy_gaiamag", "sy_tmag",
        "gaia_source_id", "gaia_parallax_mas", "gaia_parallax_error_mas",
        "gaia_distance_pc", "gaia_distance_disagreement_frac",
        "gaia_ruwe", "gaia_non_single_star", "gaia_pmra_masyr", "gaia_pmdec_masyr",
        "discoverymethod", "disc_year", "disc_facility",
        "tran_flag", "rv_flag", "ttv_flag", "pl_controv_flag", "sy_snum", "sy_pnum",
        "n_references", "n_param_sets", "rade_rel_spread",
        "n_transmission_points", "n_emission_points", "has_atmosphere_data",
        "transmission_facilities", "emission_facilities",
        "st_nrvc", "st_nphot", "st_nspec",
        "mc_uncertainty_coverage", "mc_params_without_uncertainty",
        "tsm", "esm", "rv_semi_amplitude_ms",
        "tic_id", "hd_name", "hip_name",
    ]
    export_cols = [c for c in export_cols if c in ranked.columns]

    # Per-measurement reference links are NOT carried as raw HTML on every row:
    # they triple the CSV size and are unusable as-is. They are normalised into
    # results/measurement_provenance.csv instead -- one row per
    # (planet, parameter, source) with the ADS bibcode extracted.
    provenance_table = measurement_provenance_table(ranked)
    provenance_table.to_csv(
        RESULTS_DIR / RESULT_FILES["measurement_provenance_csv"],
        index=False, compression="gzip",
    )

    out = ranked[export_cols].sort_values(
        "earth2_index", ascending=False, na_position="last"
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    p_csv = RESULTS_DIR / RESULT_FILES["ranking_csv"]
    p_pq = RESULTS_DIR / RESULT_FILES["ranking_parquet"]
    out.to_csv(p_csv, index=False)
    out_pq = out.copy()
    for c in out_pq.columns:
        if out_pq[c].dtype == object:
            out_pq[c] = out_pq[c].astype("string")
    out_pq.to_parquet(p_pq, index=False, compression="snappy")

    cov = coverage_table(ranked)
    cov.to_csv(RESULTS_DIR / RESULT_FILES["coverage_csv"], index=False)

    # Full analysis catalogue (all columns) for downstream stages.
    cat_pq = ranked.copy()
    for c in cat_pq.columns:
        if cat_pq[c].dtype == object:
            cat_pq[c] = cat_pq[c].astype("string")
    cat_pq.to_parquet(RESULTS_DIR / RESULT_FILES["catalogue_parquet"],
                      index=False, compression="snappy")

    summary = build_analysis_summary(
        ranked,
        candidates=ranked,
        extra_tables={
            "toi": toi, "koi": koi, "k2": k2, "tce": tce,
            "transitspec": transitspec, "emissionspec": emissionspec,
            "spectra_index": spectra_index,
        },
        n_monte_carlo=n_monte_carlo,
        seed=seed,
    )
    summary["monte_carlo"].update(mc_stats)
    summary["measurement_provenance"] = reference_summary(provenance_table)
    summary["software"] = _softwareversions()
    summary["runtime_seconds"] = round(time.time() - t_start, 1)
    write_summary(summary, RESULTS_DIR / RESULT_FILES["summary_json"])

    # Provenance manifest: retrievals + transformations in one file.
    store = ManifestStore()
    provenance = {
        "generated_utc": utc_now_iso(),
        "earth2_version": __version__,
        "software": _softwareversions(),
        "retrievals": store.summary_rows(),
        "total_source_records": store.total_source_records(),
        "transformations": ledger.to_dict()["steps"],
    }
    (RESULTS_DIR / RESULT_FILES["provenance_json"]).write_text(
        json.dumps(provenance, indent=2, default=str) + "\n", encoding="utf-8"
    )
    ledger.save(RESULTS_DIR / RESULT_FILES["ledger_json"])

    say("-" * 66)
    say("  wrote %d result files to %s" % (len(RESULT_FILES), RESULTS_DIR))
    say("  %s source records | %d confirmed planets | %d in conservative HZ"
        % (format(summary["scale"]["total_source_records"], ","),
           summary["population"]["n_confirmed_planets"],
           summary["habitable_zone"]["n_in_conservative_hz_nominal"]))
    say("  completed in %.1fs" % (time.time() - t_start))
    return summary
