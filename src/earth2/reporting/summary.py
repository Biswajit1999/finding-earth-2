"""Derived statistics for the README, the website and the research article.

Every number published by this project is produced here, from the analysis
output, at build time. Nothing is typed by hand into documentation. If the
archives change and the pipeline is re-run, the documentation changes with it.

That constraint is the whole point: a README quoting "6,000+ planets" that was
true in 2023 is a fabricated statistic by 2026.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from earth2 import __version__
from earth2.provenance import ManifestStore, utc_now_iso

__all__ = [
    "build_analysis_summary",
    "coverage_table",
    "dataset_inventory",
    "write_summary",
]


def _int(x: Any) -> int:
    try:
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return 0
        return int(x)
    except (TypeError, ValueError):
        return 0


def dataset_inventory(store: ManifestStore | None = None) -> dict[str, Any]:
    """What was retrieved, from where, and how much of it."""
    store = store or ManifestStore()
    rows = store.summary_rows()
    ok = [r for r in rows if r["status"] in ("ok", "partial")]
    return {
        "n_datasets": len(rows),
        "n_datasets_ok": len(ok),
        "n_datasets_failed": len([r for r in rows if r["status"] == "failed"]),
        "total_source_records": sum(_int(r["n_rows"]) for r in ok),
        "archives": sorted({r["archive"] for r in ok}),
        "datasets": rows,
    }


def coverage_table(catalogue: pd.DataFrame) -> pd.DataFrame:
    """Per-quantity data-coverage counts across the analysed catalogue.

    Reports, for each physical quantity, how many planets have it at all and how
    many have it *with* a published uncertainty. The gap between those two
    columns is the part of the catalogue that looks measured but is not
    quantified, and it is large.
    """
    df = catalogue[~catalogue.get("is_control", pd.Series(False, index=catalogue.index)).fillna(False).astype(bool)]
    n = len(df)

    quantities = [
        ("Planet radius", "pl_rade"),
        ("Planet mass", "pl_bmasse"),
        ("Bulk density", "pl_dens"),
        ("Orbital period", "pl_orbper"),
        ("Semi-major axis", "pl_orbsmax"),
        ("Orbital eccentricity", "pl_orbeccen"),
        ("Incident flux", "insol_used"),
        ("Equilibrium temperature", "teq_used"),
        ("Stellar effective temperature", "st_teff"),
        ("Stellar radius", "st_rad"),
        ("Stellar mass", "st_mass"),
        ("Stellar luminosity", "st_lum"),
        ("Stellar metallicity", "st_met"),
        ("Stellar age", "st_age"),
        ("System distance", "sy_dist"),
    ]

    rows: list[dict[str, Any]] = []
    for label, col in quantities:
        if col not in df.columns:
            continue
        v = pd.to_numeric(df[col], errors="coerce")
        has_value = int(v.notna().sum())

        e1 = pd.to_numeric(df.get(col + "err1"), errors="coerce") if col + "err1" in df else None
        e2 = pd.to_numeric(df.get(col + "err2"), errors="coerce") if col + "err2" in df else None
        uncertainty_applicable = e1 is not None or e2 is not None
        if uncertainty_applicable:
            has_err = np.zeros(len(df), dtype=bool)
            if e1 is not None:
                has_err |= (e1.notna() & (e1.abs() > 0)).to_numpy()
            if e2 is not None:
                has_err |= (e2.notna() & (e2.abs() > 0)).to_numpy()
            has_uncertainty: int | None = int((v.notna().to_numpy() & has_err).sum())
        else:
            # No err1/err2 columns exist for this quantity at all (e.g. insol_used,
            # teq_used are derived, not catalogue fields with published errors).
            # pandas writes a bare Python None to CSV as an empty cell, not the
            # magic number -1 -- a reader must not have to know that -1 means
            # "not applicable" for this row.
            has_uncertainty = None

        rows.append({
            "quantity": label,
            "column": col,
            "n_with_value": has_value,
            "pct_with_value": round(100.0 * has_value / n, 2) if n else 0.0,
            "uncertainty_applicable": uncertainty_applicable,
            "n_with_uncertainty": has_uncertainty,
            "pct_with_uncertainty": (
                round(100.0 * has_uncertainty / n, 2)
                if n and has_uncertainty is not None else None
            ),
        })
    return pd.DataFrame(rows)


def build_analysis_summary(
    catalogue: pd.DataFrame,
    candidates: pd.DataFrame | None = None,
    extra_tables: dict[str, pd.DataFrame] | None = None,
    store: ManifestStore | None = None,
    n_monte_carlo: int | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Assemble every statistic the project publishes.

    Counts are computed over exoplanets only; Solar System controls are counted
    separately and never folded into a planet total.
    """
    extra_tables = extra_tables or {}
    ctrl = catalogue.get("is_control", pd.Series(False, index=catalogue.index)).fillna(False).astype(bool)
    planets = catalogue[~ctrl]
    n = len(planets)

    def notna(col: str) -> pd.Series:
        # planets.get(col) returns a bare None -- not a Series -- when the
        # column is absent entirely, which pd.to_numeric then silently turns
        # into a scalar NaN rather than raising. The full pipeline catalogue
        # always carries every column referenced below, so this never fires
        # in production, but it crashed the first version of this function's
        # own regression test with a partial DataFrame. See the identical fix
        # (_numeric_col) in earth2.ranking.scores for the fuller explanation.
        if col not in planets.columns:
            return pd.Series(False, index=planets.index)
        return pd.to_numeric(planets[col], errors="coerce").notna()

    def numeric_col(col: str) -> pd.Series:
        """Same fix as notna() above, but returning the values, not just presence."""
        if col not in planets.columns:
            return pd.Series(np.nan, index=planets.index, dtype=float)
        return pd.to_numeric(planets[col], errors="coerce")

    mass_class = planets.get("mass_class", pd.Series(dtype=object)).astype(str)

    hz_cons = pd.to_numeric(planets.get("hz_conservative"), errors="coerce")
    hz_opt = pd.to_numeric(planets.get("hz_optimistic"), errors="coerce")
    hz_cons_p = pd.to_numeric(planets.get("hz_conservative_prob"), errors="coerce")
    hz_opt_p = pd.to_numeric(planets.get("hz_optimistic_prob"), errors="coerce")
    hz_cons_cl = pd.to_numeric(planets.get("hz_conservative_clamped"), errors="coerce")
    hz_opt_cl = pd.to_numeric(planets.get("hz_optimistic_clamped"), errors="coerce")

    radius = pd.to_numeric(planets.get("pl_rade"), errors="coerce")

    inventory = dataset_inventory(store)

    # Candidate tables from the other archives (TOI / KOI / K2), counted as
    # candidates -- explicitly NOT as planets.
    candidate_counts: dict[str, Any] = {}
    toi = extra_tables.get("toi")
    if toi is not None and "tfopwg_disp" in toi.columns:
        candidate_counts["tess_toi_total"] = int(len(toi))
        candidate_counts["tess_toi_by_disposition"] = {
            str(k): int(v) for k, v in toi["tfopwg_disp"].value_counts(dropna=False).items()
        }
    koi = extra_tables.get("koi")
    if koi is not None and "koi_disposition" in koi.columns:
        candidate_counts["kepler_koi_total"] = int(len(koi))
        candidate_counts["kepler_koi_by_disposition"] = {
            str(k): int(v) for k, v in koi["koi_disposition"].value_counts(dropna=False).items()
        }
    k2 = extra_tables.get("k2")
    if k2 is not None and "disposition" in k2.columns:
        candidate_counts["k2_total"] = int(len(k2))
        candidate_counts["k2_by_disposition"] = {
            str(k): int(v) for k, v in k2["disposition"].value_counts(dropna=False).items()
        }
    tce = extra_tables.get("tce")
    if tce is not None:
        candidate_counts["kepler_tce_detections"] = int(len(tce))

    # Atmospheric spectroscopy -- real counts, planetary atmospheres only.
    ts = extra_tables.get("transitspec")
    es = extra_tables.get("emissionspec")
    spec_index = extra_tables.get("spectra_index")
    atmosphere: dict[str, Any] = {
        "transmission_measurement_rows": int(len(ts)) if ts is not None else 0,
        "emission_measurement_rows": int(len(es)) if es is not None else 0,
        "planets_with_transmission_spectra": int(
            (pd.to_numeric(planets.get("n_transmission_points"), errors="coerce") > 0).sum()
        ),
        "planets_with_emission_spectra": int(
            (pd.to_numeric(planets.get("n_emission_points"), errors="coerce") > 0).sum()
        ),
    }
    if ts is not None and "facility" in ts.columns:
        atmosphere["transmission_facilities"] = {
            str(k): int(v) for k, v in ts["facility"].value_counts().head(12).items()
        }
    if spec_index is not None and "spec_type" in spec_index.columns:
        atmosphere["archived_spectrum_files_by_type"] = {
            str(k): int(v) for k, v in spec_index["spec_type"].value_counts(dropna=False).items()
        }

    summary: dict[str, Any] = {
        "generated_utc": utc_now_iso(),
        "earth2_version": __version__,
        "monte_carlo": {"n_samples": n_monte_carlo, "seed": seed},

        "scale": {
            "total_source_records": inventory["total_source_records"],
            "n_datasets_retrieved": inventory["n_datasets_ok"],
            "archives": inventory["archives"],
        },

        "population": {
            "n_confirmed_planets": n,
            "n_unique_host_systems": int(planets["hostname"].nunique()) if "hostname" in planets else 0,
            "n_solar_system_controls": int(ctrl.sum()),
            "n_multi_planet_systems": int(
                (planets.groupby("hostname").size() > 1).sum()
            ) if "hostname" in planets else 0,
            "discovery_methods": {
                str(k): int(v)
                for k, v in planets.get("discoverymethod", pd.Series(dtype=object))
                .value_counts().items()
            },
            "discovery_year_range": [
                _int(pd.to_numeric(planets.get("disc_year"), errors="coerce").min()),
                _int(pd.to_numeric(planets.get("disc_year"), errors="coerce").max()),
            ],
        },

        "measurement_coverage": {
            "n_with_radius": int(notna("pl_rade").sum()),
            "n_with_any_mass_value": int(notna("pl_bmasse").sum()),
            "n_with_measured_mass": int(mass_class.isin(["measured", "msini_deprojected"]).sum()),
            "n_with_msini_lower_limit": int(mass_class.eq("msini_lower_limit").sum()),
            "n_with_mass_inferred_from_radius": int(mass_class.eq("inferred_mass_radius").sum()),
            "n_with_mass_upper_limit_only": int(mass_class.eq("upper_limit").sum()),
            "n_with_insolation": int(notna("insol_used").sum()),
            "n_with_equilibrium_temperature": int(notna("teq_used").sum()),
            "n_with_stellar_teff": int(notna("st_teff").sum()),
            "n_with_distance": int(notna("sy_dist").sum()),
            "mass_class_breakdown": {
                str(k): int(v) for k, v in mass_class.value_counts().items()
            },
        },

        "observational_products": {
            "n_with_rv_time_series": int(
                (pd.to_numeric(planets.get("st_nrvc"), errors="coerce") > 0).sum()
            ),
            "n_with_photometric_time_series": int(
                (pd.to_numeric(planets.get("st_nphot"), errors="coerce") > 0).sum()
            ),
            "n_with_stellar_spectra": int(
                (pd.to_numeric(planets.get("st_nspec"), errors="coerce") > 0).sum()
            ),
            "n_detected_by_transit": int(
                (pd.to_numeric(planets.get("tran_flag"), errors="coerce") == 1).sum()
            ),
            "n_detected_by_radial_velocity": int(
                (pd.to_numeric(planets.get("rv_flag"), errors="coerce") == 1).sum()
            ),
        },

        "gaia_crossmatch": {
            "_note": (
                "Exact source_id crossmatch against Gaia DR3, extracted from the NASA "
                "Exoplanet Archive's own gaia_dr3_id column -- no coordinate matching. "
                "A host with no gaia_dr3_id recorded by the archive has no row here; "
                "see earth2.data_sources.gaia and docs/DATA_SOURCES.md."
            ),
            "n_hosts_matched": (
                int(planets.drop_duplicates(subset=["hostname"])["gaia_source_id"].notna().sum())
                if "gaia_source_id" in planets.columns and "hostname" in planets.columns
                else 0
            ),
            "n_ruwe_above_1p4": int((numeric_col("gaia_ruwe") > 1.4).sum()),
            "n_non_single_star_flagged": int((numeric_col("gaia_non_single_star").fillna(0) > 0).sum()),
            "median_distance_disagreement_pct": (
                round(float(disagreement.median() * 100), 3)
                if (disagreement := numeric_col("gaia_distance_disagreement_frac")).notna().any()
                else None
            ),
        },

        "habitable_zone": {
            "_note": (
                "'strict' counts evaluate the Kopparapu et al. (2013) fit only within its "
                "stated 2600-7200 K validity range. 'incl_extrapolated' additionally counts "
                "hosts outside that range with the temperature clamped to the boundary, "
                "flagged as extrapolation. The gap between the two is dominated by "
                "TRAPPIST-1, whose host at 2566 K sits 34 K below the floor."
            ),
            "n_in_conservative_hz_nominal": int((hz_cons == 1).sum()),
            "n_in_optimistic_hz_nominal": int((hz_opt == 1).sum()),
            "n_hz_undetermined": int(hz_cons.isna().sum()),
            "n_hosts_outside_model_validity": int(
                planets.get("hz_model_extrapolated", pd.Series(False, index=planets.index))
                .fillna(False).astype(bool).sum()
            ),
            "n_in_conservative_hz_incl_extrapolated": int((hz_cons_cl == 1).sum()),
            "n_in_optimistic_hz_incl_extrapolated": int((hz_opt_cl == 1).sum()),
            "n_conservative_hz_prob_gt_0p5": int((hz_cons_p > 0.5).sum()),
            "n_conservative_hz_prob_gt_0p9": int((hz_cons_p > 0.9).sum()),
            "n_optimistic_hz_prob_gt_0p5": int((hz_opt_p > 0.5).sum()),
            "n_conservative_hz_and_below_1p6_re": int(
                ((hz_cons == 1) & (radius < 1.6)).sum()
            ),
            "n_conservative_hz_and_below_1p6_re_with_measured_mass": int(
                ((hz_cons == 1) & (radius < 1.6)
                 & mass_class.isin(["measured", "msini_deprojected"])).sum()
            ),
            "n_conservative_hz_and_below_1p6_re_incl_extrapolated": int(
                ((hz_cons_cl == 1) & (radius < 1.6)).sum()
            ),
            "n_conservative_hz_and_below_1p6_re_with_measured_mass_incl_extrapolated": int(
                ((hz_cons_cl == 1) & (radius < 1.6)
                 & mass_class.isin(["measured", "msini_deprojected"])).sum()
            ),
        },

        "atmosphere": atmosphere,
        "candidates": candidate_counts,
    }

    if candidates is not None and not candidates.empty:
        # Solar System controls are scored by the identical functions as real
        # exoplanets (deliberately -- see ranking/scores.py), which means they
        # also carry rankable=True and a normal-looking earth2_index. Without
        # excluding is_control here, Earth and Mars sort into this list by raw
        # index value and appear as an unlabelled "rank 0" alongside genuine
        # candidates -- exactly the control/candidate conflation this project
        # exists to avoid. The website's own candidate lists already exclude
        # is_control (see web/lib/data.ts); this is the same rule applied to
        # the JSON summary that feeds the README and any other consumer.
        exo_only = candidates
        if "is_control" in candidates.columns:
            exo_only = candidates[~candidates["is_control"].fillna(False).astype(bool)]
        rankable = exo_only[exo_only.get("rankable", True).fillna(False).astype(bool)]
        summary["ranking"] = {
            "n_rankable": int(len(rankable)),
            "n_not_rankable": int(len(exo_only) - len(rankable)),
            "weights": candidates.attrs.get("score_weights", {}),
            "top_candidates": [
                {
                    "rank": _int(r.get("earth2_rank")),
                    "pl_name": str(r.get("pl_name")),
                    "hostname": str(r.get("hostname")),
                    "earth2_index": round(float(r.get("earth2_index", np.nan)), 4),
                    "earth_similarity": round(float(r.get("score_earth_similarity", np.nan)), 4),
                    "conservative_habitability": round(
                        float(r.get("score_conservative_habitability", np.nan)), 4),
                    "observational_confidence": round(
                        float(r.get("score_observational_confidence", np.nan)), 4),
                    "mass_class": str(r.get("mass_class")),
                    "pl_rade": (None if not np.isfinite(pd.to_numeric(r.get("pl_rade"), errors="coerce"))
                                else round(float(r.get("pl_rade")), 3)),
                    "sy_dist_pc": (None if not np.isfinite(pd.to_numeric(r.get("sy_dist"), errors="coerce"))
                                   else round(float(r.get("sy_dist")), 2)),
                }
                for _, r in rankable.sort_values("earth2_index", ascending=False).head(25).iterrows()
            ],
        }

    summary["provenance"] = inventory
    return summary


def write_summary(summary: dict[str, Any], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    return path
