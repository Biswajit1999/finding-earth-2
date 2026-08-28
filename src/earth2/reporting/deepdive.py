"""Deep-dive analysis for the highest-ranking systems.

The systems analysed here are **selected from the computed ranking**, never
hard-coded. Whoever comes out on top after a re-sync is who gets a deep-dive
page. If the archives change and the ordering changes, the deep dives change
with it.

Each deep dive attempts, and honestly reports the outcome of:

* full catalogue parameters with uncertainties and per-measurement provenance,
* Monte Carlo posteriors and habitable-zone membership probability,
* the host star and the system's other planets,
* published atmospheric spectroscopy, where any exists,
* a transit light-curve analysis, where a public light curve exists and the fit
  validates against the published depth,
* a radial-velocity analysis with the activity cross-check, where DACE has
  public data,
* observability metrics for future characterisation.

"Honestly reports the outcome" is the operative phrase. Most candidates will
have no usable light curve, no public RV series, and no atmospheric spectrum,
because the worlds most similar to Earth are precisely the ones hardest to
observe. Each section records which of those applies rather than omitting the
section and leaving the reader to assume it was never attempted.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from earth2.provenance import utc_now_iso
from earth2.reporting.jsonio import dump_json

__all__ = ["build_deep_dive", "select_deep_dive_targets"]


def _preserved_analysis(
    previous: dict[str, Any] | None,
    key: str,
    *,
    requested: bool,
) -> dict[str, Any] | None:
    """Return a successful archived live analysis when no refresh was requested.

    Catalogue-only rebuilds must not silently replace expensive MAST or DACE
    retrievals with a ``not requested`` placeholder.  The original analysis is
    retained verbatim and annotated with the deep-dive build it came from.
    """
    if requested or not previous:
        return None
    prior = previous.get(key)
    if not isinstance(prior, dict):
        return None
    # The transit and RV pipelines pre-date the shared ``attempted`` field.
    # Their successful historical products use a substantive status instead.
    status = prior.get("status")
    has_live_product = prior.get("attempted") is True or status not in {
        None, "error", "unavailable", "no_data", "not_attempted",
    }
    if not has_live_product:
        return None

    preserved = deepcopy(prior)
    preserved["archive_status"] = {
        "preserved": True,
        "reason": "Live-source refresh was not requested for this catalogue rebuild.",
        "from_deep_dive_generated_utc": previous.get("generated_utc"),
    }
    return preserved


def _f(v: Any, nd: int = 4) -> float | None:
    """Round to a JSON-safe float, or None."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(x) else round(x, nd)


def _s(v: Any) -> str | None:
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    s = str(v)
    return None if s in ("nan", "<NA>", "None", "") else s


def _hz_boundaries_au(r: pd.Series) -> dict[str, float | None]:
    """Habitable-zone boundary distances in au, for the website's per-world
    orbit/HZ-annulus view (see web/components/three/SystemView.tsx).

    Reuses hz.hz_distance_au() directly rather than recomputing the flux
    boundary a second way -- this project's own rule against recomputing
    science in the frontend applies just as much to a new visualisation as
    to any existing one.
    """
    from earth2.habitability import hz as hz_mod

    teff = r.get("st_teff")
    log_lum = r.get("st_lum")
    if pd.isna(teff) or pd.isna(log_lum):
        return dict.fromkeys(hz_mod.BOUNDARIES)
    lum_lsun = 10.0 ** float(log_lum)
    return {
        b: _f(hz_mod.hz_distance_au(float(teff), lum_lsun, b), 5)
        for b in hz_mod.BOUNDARIES
    }


def _narrative_summary(r: pd.Series, planet: str, host: str) -> dict[str, str | None]:
    """Plain-language location/star/planet sentences for the candidate page.

    Every clause is built mechanically from a catalogue field that is
    already used elsewhere on this page (see host_star/planet_parameters
    above) -- this is not hand-authored per-planet copy, which would be
    unreproducible and would drift out of sync with the pipeline. A clause
    is simply omitted, never guessed, when its underlying field is missing.
    """

    def g(col: str) -> float | None:
        v = r.get(col)
        return float(v) if pd.notna(v) else None

    def n(x: float | None, nd: int = 2) -> str | None:
        if x is None:
            return None
        s = f"{x:.{nd}f}"
        return s.rstrip("0").rstrip(".") if "." in s else s

    # ---- location ----
    dist_pc = g("sy_dist")
    location = (
        f"{host} lies {n(dist_pc * 3.26156, 2)} light-years ({n(dist_pc, 3)} pc) from the Sun."
        if dist_pc is not None
        else None
    )

    # ---- host star ----
    spectral_type = _s(r.get("st_spectype"))
    teff = g("st_teff")
    mass_sun = g("st_mass")
    radius_sun = g("st_rad")
    star_clauses = []
    if spectral_type:
        star_clauses.append(f"{host} is a {spectral_type} star")
    else:
        star_clauses.append(f"{host} is the host star")
    physical = []
    if mass_sun is not None:
        physical.append(f"{n(mass_sun, 3)}× the Sun's mass")
    if radius_sun is not None:
        physical.append(f"{n(radius_sun, 3)}× its radius")
    if physical:
        star_clauses.append("with " + " and ".join(physical))
    if teff is not None:
        star_clauses.append(f"(effective temperature {n(teff, 0)} K, versus the Sun's 5772 K)")
    host_star_sentence = " ".join(star_clauses) + "." if len(star_clauses) > 1 or teff is not None else None

    n_stars = int(r["sy_snum"]) if pd.notna(r.get("sy_snum")) else None
    n_planets = int(r["sy_pnum"]) if pd.notna(r.get("sy_pnum")) else None
    system_sentence = None
    if n_stars is not None and n_planets is not None:
        star_part = "a single star" if n_stars == 1 else f"one of {n_stars} stars in this system"
        planet_part = "1 known planet" if n_planets == 1 else f"{n_planets} known planets"
        system_sentence = f"It is {star_part} hosting {planet_part}."

    # ---- planet ----
    radius_earth = g("pl_rade")
    mass_earth = g("pl_bmasse")
    mass_class = _s(r.get("mass_class"))
    period = g("pl_orbper")
    smaxis = g("pl_orbsmax")
    eccen = g("pl_orbeccen")
    insol = g("insol_used")
    teq = g("teq_used")

    planet_clauses = []
    if radius_earth is not None:
        planet_clauses.append(f"{planet} is {n(radius_earth, 2)}× Earth's radius")
    mass_phrase = {
        "measured": f"{n(mass_earth, 2)}× Earth's mass, directly measured",
        "msini_lower_limit": f"at least {n(mass_earth, 2)}× Earth's mass (a radial-velocity minimum mass, not the true mass)",
        "msini_deprojected": f"about {n(mass_earth, 2)}× Earth's mass (de-projected from a minimum mass)",
        "inferred_mass_radius": f"an estimated {n(mass_earth, 2)}× Earth's mass, inferred from its radius rather than measured",
        "upper_limit": f"no more than {n(mass_earth, 2)}× Earth's mass (an upper limit)",
    }.get(mass_class or "")
    if mass_earth is not None and mass_phrase:
        planet_clauses.append(mass_phrase)
    orbit_clause = None
    if period is not None and smaxis is not None:
        orbit_clause = f"completing one orbit every {n(period, 1)} days at {n(smaxis, 4)} AU"
        if eccen is not None and eccen > 0.02:
            orbit_clause += f", on a mildly eccentric orbit (e = {n(eccen, 2)})"
    planet_sentence = None
    if planet_clauses or orbit_clause:
        parts = [", ".join(planet_clauses)] if planet_clauses else []
        if orbit_clause:
            parts.append(orbit_clause)
        planet_sentence = ", ".join(parts) + "."

    climate_sentence = None
    if insol is not None and teq is not None:
        climate_sentence = (
            f"It receives about {n(insol, 2)}× the flux Earth gets from the Sun, for an "
            f"equilibrium temperature near {n(teq, 0)} K (Earth's is 254 K)."
        )

    return {
        "location": location,
        "host_star": host_star_sentence,
        "system": system_sentence,
        "planet": planet_sentence,
        "climate": climate_sentence,
    }


def select_deep_dive_targets(
    ranking: pd.DataFrame,
    n: int = 10,
    require_rankable: bool = True,
) -> list[str]:
    """Pick the top-ranked exoplanets for deep-dive treatment.

    Controls are excluded -- Earth does not need a candidate page -- and the
    selection is purely the computed ``earth2_index`` ordering.
    """
    df = ranking.copy()
    if "is_control" in df.columns:
        df = df[~df["is_control"].fillna(False).astype(bool)]
    if require_rankable and "rankable" in df.columns:
        df = df[df["rankable"].fillna(False).astype(bool)]
    df = df.dropna(subset=["earth2_index"])
    return df.nlargest(n, "earth2_index")["pl_name"].astype(str).tolist()


def _system_siblings(ranking: pd.DataFrame, hostname: str, exclude: str) -> list[dict[str, Any]]:
    sib = ranking[(ranking["hostname"].astype(str) == hostname)
                  & (ranking["pl_name"].astype(str) != exclude)]
    out = []
    for _, r in sib.iterrows():
        out.append({
            "pl_name": _s(r.get("pl_name")),
            "pl_rade": _f(r.get("pl_rade"), 3),
            "pl_bmasse": _f(r.get("pl_bmasse"), 3),
            "pl_orbper": _f(r.get("pl_orbper"), 5),
            "pl_orbsmax": _f(r.get("pl_orbsmax"), 5),
            "insol_used": _f(r.get("insol_used"), 4),
            "teq_used": _f(r.get("teq_used"), 1),
            "hz_conservative_prob": _f(r.get("hz_conservative_prob"), 3),
            "earth2_index": _f(r.get("earth2_index"), 4),
            "mass_class": _s(r.get("mass_class")),
        })
    return sorted(out, key=lambda d: (d["pl_orbper"] is None, d["pl_orbper"] or 0))


def build_deep_dive(
    planet: str,
    ranking: pd.DataFrame,
    provenance: pd.DataFrame | None = None,
    transitspec: pd.DataFrame | None = None,
    emissionspec: pd.DataFrame | None = None,
    run_transit: bool = False,
    run_rv: bool = False,
    identifiers: pd.DataFrame | None = None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble everything known about one candidate."""
    rows = ranking[ranking["pl_name"].astype(str) == planet]
    if rows.empty:
        return {"planet": planet, "status": "not_found"}
    r = rows.iloc[0]
    host = _s(r.get("hostname")) or ""

    dd: dict[str, Any] = {
        "planet": planet,
        "hostname": host,
        "generated_utc": utc_now_iso(),
        "narrative": _narrative_summary(r, planet, host),
        "visualisation_disclaimer": (
            "Any rendering of this world is a scientifically informed visualisation, not "
            "an image. No exoplanet has been imaged at surface resolution. Surface and "
            "cloud appearance are illustrative of a physically plausible class, not "
            "observations."
        ),

        "ranking": {
            "earth2_rank": (int(r["earth2_rank"]) if pd.notna(r.get("earth2_rank")) else None),
            "earth2_index": _f(r.get("earth2_index")),
            "scores": {
                "earth_similarity": _f(r.get("score_earth_similarity")),
                "conservative_habitability": _f(r.get("score_conservative_habitability")),
                "observational_confidence": _f(r.get("score_observational_confidence")),
                "characterisation_potential": _f(r.get("score_characterisation_potential")),
            },
            "component_ranks": {
                "earth_similarity": (int(r["rank_earth_similarity"])
                                     if pd.notna(r.get("rank_earth_similarity")) else None),
                "conservative_habitability": (int(r["rank_conservative_habitability"])
                                              if pd.notna(r.get("rank_conservative_habitability")) else None),
                "observational_confidence": (int(r["rank_observational_confidence"])
                                             if pd.notna(r.get("rank_observational_confidence")) else None),
            },
        },

        "planet_parameters": {
            "radius_earth": {"value": _f(r.get("pl_rade"), 4),
                             "err_upper": _f(r.get("pl_radeerr1"), 4),
                             "err_lower": _f(r.get("pl_radeerr2"), 4),
                             "p16": _f(r.get("pl_rade_p16"), 4),
                             "p50": _f(r.get("pl_rade_p50"), 4),
                             "p84": _f(r.get("pl_rade_p84"), 4)},
            "mass_earth": {"value": _f(r.get("pl_bmasse"), 4),
                           "err_upper": _f(r.get("pl_bmasseerr1"), 4),
                           "err_lower": _f(r.get("pl_bmasseerr2"), 4),
                           "class": _s(r.get("mass_class")),
                           "class_meaning": {
                               "measured": "A directly measured dynamical mass.",
                               "msini_lower_limit": "Radial-velocity minimum mass: the true mass is M/sin(i), so this is a LOWER limit.",
                               "msini_deprojected": "Minimum mass de-projected using an inclination from elsewhere.",
                               "inferred_mass_radius": "NOT measured. Predicted from the radius by a mass-radius relation, so it carries no information beyond the radius.",
                               "upper_limit": "Reported only as an upper limit.",
                               "missing": "No mass available.",
                           }.get(_s(r.get("mass_class")) or "missing", "")},
            "density_g_cm3": {"value": _f(r.get("pl_dens_used"), 4),
                              "source": _s(r.get("esi_density_source"))},
            "escape_velocity_kms": _f(r.get("pl_vesc_kms"), 3),
            "orbital_period_days": _f(r.get("pl_orbper"), 6),
            "semi_major_axis_au": _f(r.get("pl_orbsmax"), 6),
            "eccentricity": _f(r.get("pl_orbeccen"), 4),
            "insolation_earth": {"value": _f(r.get("insol_used"), 4),
                                 "source": _s(r.get("insol_source")),
                                 "p16": _f(r.get("insol_p16"), 4),
                                 "p84": _f(r.get("insol_p84"), 4)},
            "equilibrium_temperature_k": {"value": _f(r.get("teq_used"), 2),
                                          "source": _s(r.get("teq_source")),
                                          "albedo_assumed": _f(r.get("teq_albedo_assumed"), 3),
                                          "p16": _f(r.get("teq_p16"), 2),
                                          "p84": _f(r.get("teq_p84"), 2),
                                          "note": "Equilibrium temperature excludes greenhouse warming by construction. Earth's is 254 K against a 288 K surface."},
        },

        "host_star": {
            "name": host,
            "teff_k": _f(r.get("st_teff"), 1),
            "radius_sun": _f(r.get("st_rad"), 4),
            "mass_sun": _f(r.get("st_mass"), 4),
            "luminosity_log_sun": _f(r.get("st_lum"), 4),
            "metallicity_dex": _f(r.get("st_met"), 3),
            "age_gyr": _f(r.get("st_age"), 3),
            "spectral_type": _s(r.get("st_spectype")),
            "distance_pc": _f(r.get("sy_dist"), 3),
            "distance_ly": _f((r.get("sy_dist") or np.nan) * 3.26156, 3),
            "v_mag": _f(r.get("sy_vmag"), 3),
            "j_mag": _f(r.get("sy_jmag"), 3),
            "k_mag": _f(r.get("sy_kmag"), 3),
            "n_stars_in_system": (int(r["sy_snum"]) if pd.notna(r.get("sy_snum")) else None),
            "n_planets_in_system": (int(r["sy_pnum"]) if pd.notna(r.get("sy_pnum")) else None),
        },

        "gaia_crossmatch": (
            {
                "source_id": _s(r.get("gaia_source_id")),
                "parallax_mas": _f(r.get("gaia_parallax_mas"), 4),
                "parallax_error_mas": _f(r.get("gaia_parallax_error_mas"), 4),
                "distance_pc": _f(r.get("gaia_distance_pc"), 3),
                "distance_disagreement_vs_archive_pct": (
                    _f(float(r.get("gaia_distance_disagreement_frac")) * 100, 2)
                    if pd.notna(r.get("gaia_distance_disagreement_frac")) else None
                ),
                "ruwe": _f(r.get("gaia_ruwe"), 3),
                "ruwe_note": (
                    "RUWE > 1.4 is the conventional flag for a poorly-fit or "
                    "unresolved-binary single-star astrometric solution."
                    if pd.notna(r.get("gaia_ruwe")) and float(r.get("gaia_ruwe")) > 1.4
                    else None
                ),
                "non_single_star_flag": (
                    bool(r.get("gaia_non_single_star")) if pd.notna(r.get("gaia_non_single_star")) else None
                ),
                "proper_motion_mas_yr": {
                    "ra": _f(r.get("gaia_pmra_masyr"), 3), "dec": _f(r.get("gaia_pmdec_masyr"), 3),
                },
            }
            if pd.notna(r.get("gaia_source_id")) else None
        ),

        "habitable_zone": {
            "conservative_nominal": _f(r.get("hz_conservative"), 1),
            "optimistic_nominal": _f(r.get("hz_optimistic"), 1),
            "conservative_probability": _f(r.get("hz_conservative_prob"), 4),
            "optimistic_probability": _f(r.get("hz_optimistic_prob"), 4),
            "position_across_conservative_hz": _f(r.get("hz_position_conservative"), 4),
            "model_extrapolated": bool(r.get("hz_model_extrapolated", False)),
            "teff_offset_from_validity_k": _f(r.get("hz_teff_offset_from_range_k"), 1),
            "teff_valid_fraction_of_draws": _f(r.get("hz_teff_valid_fraction"), 4),
            "boundaries_seff": {
                k: _f(r.get("seff_" + k), 4) for k in
                ("recent_venus", "runaway_greenhouse", "moist_greenhouse",
                 "maximum_greenhouse", "early_mars")
                if ("seff_" + k) in ranking.columns
            },
            "boundaries_au": _hz_boundaries_au(r),
            "model": "Kopparapu et al. (2013), ApJ 765, 131, with the 2013 erratum coefficients",
        },

        "earth_similarity": {
            "esi_global": _f(r.get("esi_global"), 4),
            "esi_p16": _f(r.get("esi_global_p16"), 4),
            "esi_p50": _f(r.get("esi_global_p50"), 4),
            "esi_p84": _f(r.get("esi_global_p84"), 4),
            "esi_interior": _f(r.get("esi_interior"), 4),
            "esi_surface": _f(r.get("esi_surface"), 4),
            "caveat": "A similarity metric on bulk properties. Not a probability of habitability, and not evidence of life. Venus scores 0.93 on the same metric.",
        },

        "evidence": {
            "n_independent_references": (int(r["n_references"]) if pd.notna(r.get("n_references")) else None),
            "n_published_parameter_sets": (int(r["n_param_sets"]) if pd.notna(r.get("n_param_sets")) else None),
            "radius_literature_spread": _f(r.get("rade_rel_spread"), 4),
            "composite_parameter_source_count": (
                int(r["composite_parameter_source_count"])
                if pd.notna(r.get("composite_parameter_source_count")) else None
            ),
            "composite_uses_mixed_sources": (
                bool(r.get("composite_uses_mixed_sources"))
                if pd.notna(r.get("composite_uses_mixed_sources")) else None
            ),
            "default_solution_present": bool(r.get("default_solution_present", False)),
            "default_solution_parameter_coverage": _f(
                r.get("default_solution_parameter_coverage"), 4,
            ),
            "default_solution_overlap_count": (
                int(r["default_solution_overlap_count"])
                if pd.notna(r.get("default_solution_overlap_count")) else None
            ),
            "composite_default_median_fractional_difference": _f(
                r.get("composite_default_median_fractional_difference"), 4,
            ),
            "source_coherence_note": (
                "NASA's composite row may select different publications for different "
                "parameters. Mixed-source is a disclosure, not an automatic quality penalty."
            ),
            "uncertainty_coverage": _f(r.get("mc_uncertainty_coverage"), 4),
            "params_without_uncertainty": (int(r["mc_params_without_uncertainty"])
                                           if pd.notna(r.get("mc_params_without_uncertainty")) else None),
            "discovery_method": _s(r.get("discoverymethod")),
            "discovery_year": (int(r["disc_year"]) if pd.notna(r.get("disc_year")) else None),
            "discovery_facility": _s(r.get("disc_facility")),
            "detected_by_transit": bool(r.get("tran_flag", 0) == 1),
            "detected_by_radial_velocity": bool(r.get("rv_flag", 0) == 1),
            "controversial_flag": bool(r.get("pl_controv_flag", 0) == 1),
        },

        "observability": {
            "tsm": _f(r.get("tsm"), 3),
            "esm": _f(r.get("esm"), 3),
            "rv_semi_amplitude_ms": _f(r.get("rv_semi_amplitude_ms"), 4),
            "ephemeris_uncertainty_2030_minutes": _f(
                r.get("ephemeris_uncertainty_2030_minutes"), 2,
            ),
            "ephemeris_forecast_epoch": "2030-01-01",
            "ephemeris_ttv_flag": bool(r.get("ttv_flag", 0) == 1),
            "followup_orbital_separation_au": _f(
                r.get("followup_orbital_separation_au"), 6,
            ),
            "followup_separation_source": _s(r.get("followup_separation_source")),
            "max_angular_separation_mas": _f(r.get("max_angular_separation_mas"), 3),
            "reflected_light_contrast_ag0p3": _f(
                r.get("reflected_light_contrast_ag0p3"), 14,
            ),
            "reflected_light_assumptions": (
                "Geometric albedo 0.30, Lambert phase function at quadrature (1/pi). "
                "Scenario estimate only; not a measured contrast or detectability claim."
            ),
            "n_transmission_points": (int(r["n_transmission_points"])
                                      if pd.notna(r.get("n_transmission_points")) else 0),
            "n_emission_points": (int(r["n_emission_points"])
                                  if pd.notna(r.get("n_emission_points")) else 0),
            "n_rv_time_series": (int(r["st_nrvc"]) if pd.notna(r.get("st_nrvc")) else 0),
            "n_photometric_time_series": (int(r["st_nphot"]) if pd.notna(r.get("st_nphot")) else 0),
            "tsm_note": "Kempton et al. (2018) Transmission Spectroscopy Metric. Undefined for non-transiting planets.",
            "followup_note": (
                "Follow-up diagnostics are separate observing lanes and are not inputs to "
                "the default Earth-2.0 ranking."
            ),
        },

        "system": {"siblings": _system_siblings(ranking, host, planet)},
    }

    # ---------------- per-measurement provenance ----------------
    if provenance is not None and not provenance.empty:
        sub = provenance[provenance["pl_name"].astype(str) == planet]
        dd["measurement_provenance"] = [
            {
                "parameter": _s(x.get("parameter")),
                "parameter_label": _s(x.get("parameter_label")),
                "value": _f(x.get("value"), 6),
                "source_kind": _s(x.get("source_kind")),
                "reference_label": _s(x.get("reference_label")),
                "reference_url": _s(x.get("reference_url")),
                "bibcode": _s(x.get("bibcode")),
            }
            for _, x in sub.iterrows()
        ]

    # ---------------- identifiers ----------------
    if identifiers is not None and not identifiers.empty:
        idr = identifiers[identifiers["query_name"].astype(str) == planet]
        if not idr.empty:
            row = idr.iloc[0]
            dd["identifiers"] = {
                k.replace("planet_id_", ""): _s(row[k])
                for k in idr.columns if k.startswith("planet_id_") and _s(row[k])
            }
            dd["identifiers"]["system_name"] = _s(row.get("system_name"))
            aliases = _s(row.get("planet_aliases"))
            dd["aliases"] = aliases.split("|") if aliases else []

    # ---------------- atmospheric spectra ----------------
    from earth2.spectroscopy import planet_spectrum

    spec = planet_spectrum(transitspec, planet) if transitspec is not None else None
    if spec:
        dd["transmission_spectrum"] = spec
    else:
        dd["transmission_spectrum"] = {
            "available": False,
            "message": "No published transmission spectrum exists for this planet in the NASA Exoplanet Archive.",
        }

    # ---------------- transit photometry ----------------
    preserved_transit = _preserved_analysis(
        previous, "transit_analysis", requested=run_transit,
    )
    if preserved_transit is not None:
        dd["transit_analysis"] = preserved_transit
    elif run_transit and bool(r.get("tran_flag", 0) == 1):
        from earth2.transit import analyse_target as transit_analyse

        depth_pct = pd.to_numeric(pd.Series([r.get("pl_trandep")]), errors="coerce").iloc[0]
        dd["transit_analysis"] = transit_analyse(
            host,
            period_days=_f(r.get("pl_orbper"), 8),
            t0_bjd=_f(r.get("pl_tranmid"), 8),
            duration_hours=_f(r.get("pl_trandur"), 4),
            mission="TESS",
            max_products=1,
            search_period=False,
            expected_depth_ppm=(float(depth_pct) * 1e4 if pd.notna(depth_pct) else None),
        )
    else:
        dd["transit_analysis"] = {
            "attempted": False,
            "reason": ("Planet is not flagged as transiting; a light curve cannot show a transit."
                       if not bool(r.get("tran_flag", 0) == 1)
                       else "Transit analysis not requested for this build."),
        }

    # ---------------- radial velocity ----------------
    preserved_rv = _preserved_analysis(previous, "rv_analysis", requested=run_rv)
    if preserved_rv is not None:
        dd["rv_analysis"] = preserved_rv
    elif run_rv:
        from earth2.radial_velocity import analyse_target as rv_analyse

        dd["rv_analysis"] = rv_analyse(
            host,
            stellar_mass_sun=_f(r.get("st_mass"), 5),
            known_period_days=_f(r.get("pl_orbper"), 8),
        )
    else:
        dd["rv_analysis"] = {"attempted": False, "reason": "Not requested for this build."}

    return dd


def write_deep_dives(
    targets: list[str],
    ranking: pd.DataFrame,
    out_dir: Path,
    **kwargs: Any,
) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for t in targets:
        dd = build_deep_dive(t, ranking, **kwargs)
        slug = t.replace(" ", "_").replace("/", "-")
        p = out_dir / (slug + ".json")
        p.write_text(dump_json(dd, indent=1), encoding="utf-8")
        written.append(p)
    return written
