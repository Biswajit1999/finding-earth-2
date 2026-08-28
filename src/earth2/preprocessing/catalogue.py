"""Build the analysis catalogue from retrieved archive tables.

This is the stage where raw archive columns become quantities the scoring engine
is allowed to use. Three principles govern it:

1. **Never invent a measurement.** A missing value stays missing. Nothing is
   imputed to an Earth value, a population median, or a convenient default.

2. **Record how every derived value was obtained.** Each derived quantity
   ``x`` is accompanied by ``x_source`` naming whether it came from the
   catalogue, was derived from other columns, or is absent.

3. **Distinguish a measurement from an inference.** The single most important
   application of this is planetary mass -- see :func:`classify_mass_provenance`.

Mass provenance
---------------
``pscomppars`` reports a mass for ~99.5% of planets, which is misleading. The
``pl_bmassprov`` column reveals what those masses actually are:

===========================  =========  ===============================================
pl_bmassprov                 Count      What it means
===========================  =========  ===============================================
``Mass``                     ~2,400     A genuinely measured mass.
``M-R relationship``         ~3,000     NOT measured. Predicted from the radius via a
                                        mass-radius relation.
``Msini``                    ~900       Radial-velocity minimum mass. A LOWER limit;
                                        the true mass is M/sin(i) >= this.
``Msin(i)/sin(i)``           ~15        Msini de-projected using an inclination from
                                        elsewhere.
===========================  =========  ===============================================

Using an M-R-relationship mass to compute density or escape velocity produces a
quantity that carries no information beyond the radius it was derived from. The
Earth Similarity Index would then appear to combine four independent properties
while in fact being driven by one. This module flags such masses so downstream
scoring can discount them, and the observational-confidence score penalises
them explicitly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from earth2.constants import BOND_ALBEDO_EARTH, SOLAR_SYSTEM_CONTROLS
from earth2.habitability import esi as esi_mod
from earth2.habitability import hz as hz_mod
from earth2.provenance import TransformLedger

__all__ = [
    "MASS_CLASSES",
    "add_derived_quantities",
    "attach_atmosphere_availability",
    "attach_gaia_crossmatch",
    "attach_reference_evidence",
    "build_catalogue",
    "classify_mass_provenance",
    "derive_equilibrium_temperature",
    "derive_insolation",
    "solar_system_control_frame",
]

#: Mass provenance classes, ordered from strongest to weakest evidence.
MASS_CLASSES: tuple[str, ...] = (
    "measured",             # direct dynamical mass
    "msini_deprojected",    # Msini/sin(i) using an external inclination
    "msini_lower_limit",    # RV minimum mass; true mass is >= this
    "upper_limit",          # reported as an upper limit only
    "inferred_mass_radius",  # predicted from radius; carries no new information
    "missing",
)

# Linear-valued parameters used to compare the composite ``pscomppars`` row
# with the archive's coherent default solution in ``ps``. ``st_lum`` is
# deliberately excluded because it is logarithmic in the archive, so a simple
# fractional difference would be physically meaningless.
_SOLUTION_COMPARE_PARAMS: tuple[str, ...] = (
    "pl_rade", "pl_bmasse", "pl_orbper", "pl_orbsmax", "pl_insol", "pl_eqt",
    "pl_dens", "pl_orbeccen", "st_teff", "st_rad", "st_mass", "sy_dist",
)

# Parameters whose per-value reference links are present on ``pscomppars``.
_COMPOSITE_SOURCE_PARAMS: tuple[str, ...] = (
    "pl_rade", "pl_bmasse", "pl_orbper", "pl_orbsmax", "pl_insol", "pl_eqt",
    "pl_dens", "pl_orbeccen", "st_teff", "st_rad", "st_mass", "st_lum",
    "st_met", "st_age", "sy_dist",
)


def classify_mass_provenance(df: pd.DataFrame) -> pd.Series:
    """Classify what each planet's mass actually is.

    The archive's ``pl_bmasse`` column mixes measured masses, RV minimum masses
    and radius-derived predictions without distinction. Scoring cannot treat
    those as equivalent evidence, so this resolves them into
    :data:`MASS_CLASSES`.

    The limit flag takes precedence over the provenance string: a value reported
    as an upper limit is not a measurement regardless of how it was obtained.
    """
    prov = df.get("pl_bmassprov", pd.Series(index=df.index, dtype=object)).astype("string")
    mass = pd.to_numeric(df.get("pl_bmasse"), errors="coerce")
    lim = pd.to_numeric(df.get("pl_bmasselim"), errors="coerce")

    out = pd.Series("missing", index=df.index, dtype=object)

    has_mass = mass.notna() & (mass > 0)
    p = prov.fillna("")

    out[has_mass & p.str.contains("M-R", case=False, na=False)] = "inferred_mass_radius"
    out[has_mass & p.str.fullmatch(r"\s*Mass\s*", case=False, na=False)] = "measured"
    out[has_mass & p.str.contains(r"Msin\(i\)/sin\(i\)", case=False, regex=True, na=False)] = "msini_deprojected"
    out[has_mass & p.str.fullmatch(r"\s*Msini\s*", case=False, na=False)] = "msini_lower_limit"

    # Anything with a mass but an unrecognised provenance string is treated as
    # measured only if the archive did not flag it as a limit; otherwise the
    # limit classification wins.
    unknown = has_mass & (out == "missing")
    out[unknown] = "measured"

    out[has_mass & lim.eq(1)] = "upper_limit"
    out[~has_mass] = "missing"
    return out


def derive_insolation(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Incident stellar flux in Earth units, with its source.

    Preference order:

    1. ``pl_insol`` from the catalogue.
    2. Derived as ``S = L / a^2`` with ``L = 10**st_lum`` (the archive stores
       stellar luminosity as log10 solar) and ``a`` the semi-major axis in au.

    Distance from the star alone is never used -- a planet 1 au from an M dwarf
    and a planet 1 au from an F star receive wildly different fluxes, and flux is
    what sets habitable-zone membership.
    """
    insol = pd.to_numeric(df.get("pl_insol"), errors="coerce")
    lum_log = pd.to_numeric(df.get("st_lum"), errors="coerce")
    a = pd.to_numeric(df.get("pl_orbsmax"), errors="coerce")

    with np.errstate(invalid="ignore", divide="ignore"):
        derived = (10.0**lum_log) / (a**2)
    derived = derived.replace([np.inf, -np.inf], np.nan)

    use_cat = insol.notna() & (insol > 0)
    value = insol.where(use_cat, derived)
    value = value.where(value > 0)

    source = pd.Series("missing", index=df.index, dtype=object)
    source[value.notna() & use_cat] = "catalogue"
    source[value.notna() & ~use_cat] = "derived_from_luminosity_and_semimajor_axis"
    return value, source


def derive_equilibrium_temperature(
    df: pd.DataFrame,
    insolation: pd.Series,
    albedo: float = BOND_ALBEDO_EARTH,
) -> tuple[pd.Series, pd.Series]:
    """Equilibrium temperature in K, with its source.

    Computed self-consistently from insolation wherever insolation is available::

        T_eq = 278.5 K * S^(1/4) * (1 - A)^(1/4)

    with ``A`` the Bond albedo, default Earth's 0.306.

    Deriving from insolation is *preferred over* the catalogue's ``pl_eqt``
    because the catalogue value is taken from whichever paper reported it, and
    different papers assume different albedos -- commonly A = 0, sometimes
    A = 0.3. Mixing those produces a temperature column that is internally
    inconsistent by up to ~9%, which matters a great deal given that the ESI
    temperature term has by far the largest weight exponent (5.58).

    The catalogue value is used only as a fallback where insolation is unknown,
    and the row is flagged so the inconsistency is visible.
    """
    s = pd.to_numeric(insolation, errors="coerce")
    with np.errstate(invalid="ignore"):
        derived = 278.5 * (s ** 0.25) * ((1.0 - albedo) ** 0.25)

    cat = pd.to_numeric(df.get("pl_eqt"), errors="coerce")

    value = derived.where(derived.notna(), cat)
    source = pd.Series("missing", index=df.index, dtype=object)
    source[derived.notna()] = f"derived_from_insolation_albedo_{albedo:.3f}"
    source[derived.isna() & cat.notna()] = "catalogue_heterogeneous_albedo"
    return value, source


def add_derived_quantities(
    df: pd.DataFrame,
    albedo: float = BOND_ALBEDO_EARTH,
    ledger: TransformLedger | None = None,
) -> pd.DataFrame:
    """Attach flux, temperature, density, escape velocity, HZ and ESI columns."""
    out = df.copy()

    out["mass_class"] = classify_mass_provenance(out)
    out["mass_is_measured"] = out["mass_class"].isin(["measured", "msini_deprojected"])
    out["mass_is_inferred"] = out["mass_class"].eq("inferred_mass_radius")

    insol, insol_src = derive_insolation(out)
    out["insol_used"] = insol
    out["insol_source"] = insol_src

    teq, teq_src = derive_equilibrium_temperature(out, insol, albedo=albedo)
    out["teq_used"] = teq
    out["teq_source"] = teq_src
    out["teq_albedo_assumed"] = albedo

    # ESI (and the density / escape velocity it needs).
    esi_cols = esi_mod.esi_frame(
        out.assign(pl_eqt=out["teq_used"]),
        radius_col="pl_rade",
        mass_col="pl_bmasse",
        density_col="pl_dens",
        teq_col="pl_eqt",
    )
    for c in esi_cols.columns:
        out[c] = esi_cols[c]

    # Habitable-zone membership uses the self-consistent flux, not the catalogue
    # semi-major axis.
    teff = pd.to_numeric(out.get("st_teff"), errors="coerce")
    hz_cols = hz_mod.hz_membership(out["insol_used"].to_numpy(dtype=float),
                                   teff.to_numpy(dtype=float))
    for k, v in hz_cols.items():
        out[k] = v
    out["hz_position_conservative"] = hz_mod.hz_position(
        out["insol_used"].to_numpy(dtype=float), teff.to_numpy(dtype=float)
    )
    out["hz_teff_in_range"] = (teff >= hz_mod.HZ_TEFF_MIN) & (teff <= hz_mod.HZ_TEFF_MAX)

    # Explicitly-flagged extrapolation beyond the fit's validity range.
    #
    # This is not a corner case. TRAPPIST-1 -- the single most studied
    # temperate terrestrial system known -- has T_eff = 2566 K, which is 34 K
    # BELOW Kopparapu's 2600 K floor. Under a strict reading its planets have no
    # habitable-zone classification at all, which would silently remove the most
    # important system in the analysis from every habitable-zone count.
    #
    # Rather than quietly clamping (which would hide the problem) or quietly
    # dropping (which would distort the results), both evaluations are carried:
    # the strict one above, and a clamped one here that is permanently marked as
    # an extrapolation so no downstream consumer can mistake it for a supported
    # model evaluation.
    insol_arr = out["insol_used"].to_numpy(dtype=float)
    teff_arr = teff.to_numpy(dtype=float)
    teff_clamped = np.clip(teff_arr, hz_mod.HZ_TEFF_MIN, hz_mod.HZ_TEFF_MAX)
    teff_clamped = np.where(np.isfinite(teff_arr), teff_clamped, np.nan)

    out["hz_conservative_clamped"] = hz_mod.in_conservative_hz(insol_arr, teff_clamped)
    out["hz_optimistic_clamped"] = hz_mod.in_optimistic_hz(insol_arr, teff_clamped)
    out["hz_model_extrapolated"] = (
        np.isfinite(teff_arr)
        & ((teff_arr < hz_mod.HZ_TEFF_MIN) | (teff_arr > hz_mod.HZ_TEFF_MAX))
    )
    out["hz_teff_offset_from_range_k"] = np.where(
        teff_arr < hz_mod.HZ_TEFF_MIN, teff_arr - hz_mod.HZ_TEFF_MIN,
        np.where(teff_arr > hz_mod.HZ_TEFF_MAX, teff_arr - hz_mod.HZ_TEFF_MAX, 0.0),
    )

    if ledger is not None:
        ledger.add(
            "classify_mass_provenance",
            "Separate measured masses from radial-velocity minimum masses and from masses "
            "predicted by a mass-radius relation, which carry no information beyond radius.",
            inputs=["pl_bmasse", "pl_bmassprov", "pl_bmasselim"],
            outputs=["mass_class", "mass_is_measured", "mass_is_inferred"],
            n_rows_in=len(df), n_rows_out=len(out),
        )
        ledger.add(
            "derive_insolation",
            "Incident stellar flux in Earth units, from the catalogue where available, "
            "otherwise S = 10**st_lum / a^2.",
            inputs=["pl_insol", "st_lum", "pl_orbsmax"],
            outputs=["insol_used", "insol_source"],
            equation="S = L / a^2,  L = 10**st_lum",
            n_rows_in=len(df), n_rows_out=len(out),
        )
        ledger.add(
            "derive_equilibrium_temperature",
            "Equilibrium temperature derived self-consistently from insolation at a fixed "
            "Bond albedo, in preference to catalogue values that assume heterogeneous albedos.",
            inputs=["insol_used", "pl_eqt"],
            outputs=["teq_used", "teq_source"],
            equation="T_eq = 278.5 * S**0.25 * (1 - A)**0.25",
            parameters={"bond_albedo": albedo},
            n_rows_in=len(df), n_rows_out=len(out),
        )
        ledger.add(
            "earth_similarity_index",
            "Four-term two-tier Earth Similarity Index; temperature referenced to Earth's "
            "equilibrium temperature (254 K), not its surface temperature.",
            inputs=["pl_rade", "pl_dens_used", "pl_vesc_kms", "teq_used"],
            outputs=["esi_interior", "esi_surface", "esi_global"],
            equation="ESI_x = (1 - |(x-x0)/(x+x0)|)**(w/n)",
            citation="schulzemakuch2011",
            n_rows_in=len(df), n_rows_out=len(out),
        )
        ledger.add(
            "habitable_zone_membership",
            "Conservative and optimistic habitable-zone membership from incident flux and "
            "stellar effective temperature; NaN outside the fit's 2600-7200 K validity range.",
            inputs=["insol_used", "st_teff"],
            outputs=["hz_conservative", "hz_optimistic", "hz_position_conservative"],
            equation="S_eff = S_eff_sun + a*T + b*T^2 + c*T^3 + d*T^4,  T = Teff - 5780",
            citation="kopparapu2013,kopparapu2013erratum",
            n_rows_in=len(df), n_rows_out=len(out),
        )
    return out


def attach_reference_evidence(
    catalogue: pd.DataFrame,
    ps: pd.DataFrame,
    ledger: TransformLedger | None = None,
) -> pd.DataFrame:
    """Count independent published parameter sets per planet, from the `ps` table.

    ``pscomppars`` gives one composite row per planet and therefore cannot say
    how many groups have actually measured it. ``ps`` carries one row per
    published parameter set, so counting rows per planet -- and counting distinct
    ``pl_refname`` values -- measures how much independent literature stands
    behind a candidate.

    Also records the fractional spread in published radii, which exposes planets
    where the literature genuinely disagrees. A tight composite value sitting on
    top of two papers that differ by 40% is not a well-measured planet.

    The archive explicitly documents ``pscomppars`` as a best-per-parameter
    composite that may mix publications and therefore need not represent one
    internally coherent physical solution. We surface that distinction with:

    * the number of distinct per-parameter sources in the composite row;
    * whether more than one such source is used;
    * how much of the composite can be compared with the archive's coherent
      ``default_flag=1`` row in ``ps``; and
    * the median symmetric fractional difference over overlapping linear-valued
      parameters.

    These are diagnostics, not a penalty in the Earth-like ranking. Mixing
    sources can improve completeness and is not automatically bad science; the
    reader needs to see it rather than have the pipeline guess its meaning.
    """
    out = catalogue.copy()

    source_columns = [
        f"{parameter}_reflink"
        for parameter in _COMPOSITE_SOURCE_PARAMS
        if f"{parameter}_reflink" in out.columns
    ]

    def count_composite_sources(row: pd.Series) -> float:
        sources = {
            str(value).strip()
            for value in row[source_columns]
            if pd.notna(value) and str(value).strip()
        }
        return float(len(sources)) if sources else np.nan

    if source_columns:
        out["composite_parameter_source_count"] = out.apply(
            count_composite_sources, axis=1,
        )
    else:
        out["composite_parameter_source_count"] = np.nan
    source_count = pd.to_numeric(
        out["composite_parameter_source_count"], errors="coerce",
    )
    out["composite_uses_mixed_sources"] = source_count.gt(1).where(source_count.notna())

    if ps is None or ps.empty or "pl_name" not in ps.columns:
        out["n_param_sets"] = np.nan
        out["n_references"] = np.nan
        out["rade_rel_spread"] = np.nan
        out["default_solution_present"] = False
        out["default_solution_parameter_coverage"] = np.nan
        out["default_solution_overlap_count"] = np.nan
        out["composite_default_median_fractional_difference"] = np.nan
        return out

    g = ps.groupby("pl_name")
    agg = pd.DataFrame({
        "n_param_sets": g.size(),
        "n_references": g["pl_refname"].nunique() if "pl_refname" in ps.columns else g.size(),
    })

    if "pl_rade" in ps.columns:
        r = ps.groupby("pl_name")["pl_rade"]
        with np.errstate(invalid="ignore", divide="ignore"):
            spread = (r.max() - r.min()) / r.median()
        agg["rade_rel_spread"] = spread.replace([np.inf, -np.inf], np.nan)

    out = out.merge(agg, left_on="pl_name", right_index=True, how="left")

    default_flag = pd.to_numeric(
        ps.get("default_flag", pd.Series(np.nan, index=ps.index)),
        errors="coerce",
    )
    default_rows = ps.loc[default_flag.eq(1)].copy()
    if "rowupdate" in default_rows.columns:
        default_rows = default_rows.sort_values("rowupdate", ascending=False)
    default_rows = default_rows.drop_duplicates("pl_name").set_index("pl_name")

    solution_metrics: list[tuple[bool, float, float, float]] = []
    compare_params = [
        parameter for parameter in _SOLUTION_COMPARE_PARAMS
        if parameter in out.columns and parameter in default_rows.columns
    ]
    for _, composite in out.iterrows():
        name = composite.get("pl_name")
        if name not in default_rows.index:
            solution_metrics.append((False, np.nan, np.nan, np.nan))
            continue

        default = default_rows.loc[name]
        composite_values = pd.to_numeric(composite[compare_params], errors="coerce")
        default_values = pd.to_numeric(default[compare_params], errors="coerce")
        composite_present = composite_values.notna()
        overlap = composite_present & default_values.notna()
        n_composite = int(composite_present.sum())
        n_overlap = int(overlap.sum())
        coverage = n_overlap / n_composite if n_composite else np.nan

        differences: list[float] = []
        for parameter in np.asarray(compare_params)[overlap.to_numpy()]:
            a = float(composite_values[parameter])
            b = float(default_values[parameter])
            scale = abs(a) + abs(b)
            differences.append(0.0 if scale == 0.0 else 2.0 * abs(a - b) / scale)
        median_difference = float(np.median(differences)) if differences else np.nan
        solution_metrics.append((True, coverage, float(n_overlap), median_difference))

    metrics = pd.DataFrame(
        solution_metrics,
        index=out.index,
        columns=[
            "default_solution_present",
            "default_solution_parameter_coverage",
            "default_solution_overlap_count",
            "composite_default_median_fractional_difference",
        ],
    )
    for column in metrics:
        out[column] = metrics[column]

    if ledger is not None:
        ledger.add(
            "attach_reference_evidence",
            "Count independent published parameter sets and distinct references per planet; "
            "measure radius disagreement; and compare the mixed-source composite row with "
            "the archive's coherent default published solution.",
            inputs=["ps.pl_name", "ps.pl_refname", "ps.default_flag", "pscomppars.*_reflink"],
            outputs=[
                "n_param_sets", "n_references", "rade_rel_spread",
                "composite_parameter_source_count", "composite_uses_mixed_sources",
                "default_solution_parameter_coverage",
                "composite_default_median_fractional_difference",
            ],
            n_rows_in=len(catalogue), n_rows_out=len(out),
        )
    return out


def attach_atmosphere_availability(
    catalogue: pd.DataFrame,
    transitspec: pd.DataFrame | None = None,
    emissionspec: pd.DataFrame | None = None,
    ledger: TransformLedger | None = None,
) -> pd.DataFrame:
    """Attach real counts of published atmospheric spectroscopy per planet.

    These are counts of *planetary atmosphere* measurements -- transmission
    spectra and secondary-eclipse depths. They are deliberately kept separate
    from stellar spectra, which measure the star and say nothing directly about
    a planet's atmosphere.
    """
    out = catalogue.copy()
    out["n_transmission_points"] = 0
    out["n_emission_points"] = 0
    out["transmission_facilities"] = ""
    out["emission_facilities"] = ""

    if transitspec is not None and not transitspec.empty and "plntname" in transitspec.columns:
        g = transitspec.groupby("plntname")
        counts = g.size()
        fac = g["facility"].apply(lambda s: ", ".join(sorted({str(x) for x in s.dropna()}))) \
            if "facility" in transitspec.columns else None
        out["n_transmission_points"] = out["pl_name"].map(counts).fillna(0).astype(int)
        if fac is not None:
            out["transmission_facilities"] = out["pl_name"].map(fac).fillna("")

    if emissionspec is not None and not emissionspec.empty and "plntname" in emissionspec.columns:
        g = emissionspec.groupby("plntname")
        counts = g.size()
        fac = g["facility"].apply(lambda s: ", ".join(sorted({str(x) for x in s.dropna()}))) \
            if "facility" in emissionspec.columns else None
        out["n_emission_points"] = out["pl_name"].map(counts).fillna(0).astype(int)
        if fac is not None:
            out["emission_facilities"] = out["pl_name"].map(fac).fillna("")

    out["has_atmosphere_data"] = (out["n_transmission_points"] > 0) | (out["n_emission_points"] > 0)

    if ledger is not None:
        ledger.add(
            "attach_atmosphere_availability",
            "Count published transmission-spectrum and emission-spectrum measurements per "
            "planet. Planetary-atmosphere data only; stellar spectra are excluded.",
            inputs=["transitspec.plntname", "emissionspec.plntname"],
            outputs=["n_transmission_points", "n_emission_points", "has_atmosphere_data"],
            n_rows_in=len(catalogue), n_rows_out=len(out),
        )
    return out


def attach_gaia_crossmatch(
    catalogue: pd.DataFrame,
    gaia: pd.DataFrame | None,
    ledger: TransformLedger | None = None,
) -> pd.DataFrame:
    """Attach Gaia DR3 astrometry from the exact-source_id crossmatch.

    Joins on ``hostname`` (the Gaia table is one row per host star; every
    sibling planet in a multi-planet system inherits the same host row, which
    is correct since they share a parallax and a RUWE). Adds an independent
    parallax-based distance (``gaia_distance_pc = 1000 / parallax_mas``,
    itself only valid for a positive parallax with reasonable relative
    precision) alongside the archive's own adopted ``sy_dist``, and a
    fractional-disagreement column between the two -- large disagreement is
    worth a reader's attention regardless of which side turns out to be
    right. ``gaia_ruwe`` above ~1.4 and ``gaia_non_single_star`` flag hosts
    whose single-star astrometric solution fit poorly or for whom Gaia's own
    pipeline found evidence of additional unresolved components; see
    :mod:`earth2.data_sources.gaia` for why this project treats this as
    context rather than folding it into any score.

    A planet whose host has no ``gaia_dr3_id`` recorded by the NASA archive
    (present for 92.5% of host systems) simply gets NaN in every Gaia column
    here, not a silently-substituted average.
    """
    out = catalogue.copy()
    # gaia_source_id is handled separately from the rest: it is a 19-digit
    # integer, beyond float64's 2^53 exact-integer range (see
    # earth2.data_sources.gaia.hosts_with_gaia_ids for the same trap). Every
    # OTHER Gaia column here is initialised to plain NaN, which forces
    # float64 the moment a caller assigns into it -- fine for a genuine
    # measurement, but if gaia_source_id were initialised the same way, the
    # int64 values .map() assigns in below would be silently downcast to
    # float64 immediately, before this function ever returns. Keeping it as
    # a pre-stringified object column from the start means no float64 stage
    # ever exists for it to lose precision in.
    numeric_gaia_cols = {
        "gaia_parallax_mas": "parallax", "gaia_parallax_error_mas": "parallax_error",
        "gaia_ruwe": "ruwe", "gaia_non_single_star": "non_single_star",
        "gaia_pmra_masyr": "pmra", "gaia_pmdec_masyr": "pmdec",
        "gaia_phot_g_mean_mag": "phot_g_mean_mag",
    }
    all_gaia_cols = ["gaia_source_id"] + list(numeric_gaia_cols)
    for out_col in numeric_gaia_cols:
        out[out_col] = np.nan
    out["gaia_source_id"] = None

    if gaia is None or gaia.empty or "hostname" not in gaia.columns:
        if ledger is not None:
            ledger.add(
                "attach_gaia_crossmatch",
                "Attach Gaia DR3 astrometry by exact source_id. No crossmatch table "
                "was available for this run; every Gaia column is NaN.",
                outputs=all_gaia_cols, n_rows_in=len(catalogue), n_rows_out=len(out),
            )
        return out

    g = gaia.drop_duplicates(subset=["hostname"]).set_index("hostname")
    if "source_id" in g.columns:
        out["gaia_source_id"] = out["hostname"].map(g["source_id"].astype(str))
    for out_col, gaia_col in numeric_gaia_cols.items():
        if gaia_col in g.columns:
            out[out_col] = out["hostname"].map(g[gaia_col])

    with np.errstate(invalid="ignore", divide="ignore"):
        out["gaia_distance_pc"] = np.where(
            out["gaia_parallax_mas"] > 0, 1000.0 / out["gaia_parallax_mas"], np.nan,
        )
        sy_dist = pd.to_numeric(out.get("sy_dist"), errors="coerce")
        out["gaia_distance_disagreement_frac"] = np.where(
            (sy_dist > 0) & np.isfinite(out["gaia_distance_pc"]),
            np.abs(out["gaia_distance_pc"] - sy_dist) / sy_dist,
            np.nan,
        )

    if ledger is not None:
        n_matched = int(out["gaia_source_id"].notna().sum())
        ledger.add(
            "attach_gaia_crossmatch",
            "Attach Gaia DR3 astrometry (parallax, proper motion, RUWE, "
            "non-single-star flag) by exact source_id, extracted from the NASA "
            "Exoplanet Archive's gaia_dr3_id column and joined on hostname.",
            inputs=["hostname", "gaia_dr3_crossmatch.source_id"],
            outputs=all_gaia_cols + ["gaia_distance_pc", "gaia_distance_disagreement_frac"],
            citation="GaiaDR3",
            n_rows_in=len(catalogue), n_rows_out=len(out),
            parameters={"n_planets_matched": n_matched},
        )
    return out


def solar_system_control_frame() -> pd.DataFrame:
    """Solar System bodies as explicitly-labelled comparison controls.

    These are NOT exoplanet observations and must never be counted as such.
    ``is_control`` follows them through every downstream table, figure and
    interface element.
    """
    rows: list[dict] = []
    for name, p in SOLAR_SYSTEM_CONTROLS.items():
        r = dict(p)
        r["pl_name"] = name
        r["hostname"] = "Sun"
        r["discoverymethod"] = "Solar System reference"
        r["disc_facility"] = "Solar System"
        r["pl_bmassprov"] = "Mass"
        r["is_control"] = True
        r["default_flag"] = 1
        r["tran_flag"] = 0
        r["rv_flag"] = 0
        rows.append(r)
    return pd.DataFrame(rows)


def build_catalogue(
    pscomppars: pd.DataFrame,
    ps: pd.DataFrame | None = None,
    transitspec: pd.DataFrame | None = None,
    emissionspec: pd.DataFrame | None = None,
    gaia: pd.DataFrame | None = None,
    include_controls: bool = True,
    albedo: float = BOND_ALBEDO_EARTH,
    ledger: TransformLedger | None = None,
) -> pd.DataFrame:
    """Assemble the full analysis catalogue.

    Returns one row per confirmed planet, plus Solar System controls when
    requested, with every derived quantity accompanied by its source.
    """
    base = pscomppars.copy()
    base["is_control"] = False

    if include_controls:
        controls = solar_system_control_frame()
        base = pd.concat([base, controls], ignore_index=True, sort=False)

    # Numeric coercion: the archive ships several numeric columns as strings when
    # a row carries a limit flag or an empty field.
    numeric_cols = [
        "pl_rade", "pl_bmasse", "pl_dens", "pl_orbper", "pl_orbsmax", "pl_orbeccen",
        "pl_insol", "pl_eqt", "pl_orbincl", "pl_trandep", "pl_trandur", "pl_ratror",
        "pl_ratdor", "pl_imppar", "st_teff", "st_rad", "st_mass", "st_lum", "st_met",
        "st_age", "st_logg", "sy_dist", "sy_plx", "ra", "dec",
        "sy_vmag", "sy_kmag", "sy_jmag", "sy_gaiamag", "sy_tmag",
        "pl_ntranspec", "pl_nespec", "pl_ndispec", "st_nrvc", "st_nphot", "st_nspec",
    ]
    for c in numeric_cols:
        if c in base.columns:
            base[c] = pd.to_numeric(base[c], errors="coerce")
        # error columns too
        for suf in ("err1", "err2", "lim"):
            cc = c + suf
            if cc in base.columns:
                base[cc] = pd.to_numeric(base[cc], errors="coerce")

    cat = add_derived_quantities(base, albedo=albedo, ledger=ledger)
    cat = attach_reference_evidence(cat, ps, ledger=ledger)
    cat = attach_atmosphere_availability(cat, transitspec, emissionspec, ledger=ledger)
    cat = attach_gaia_crossmatch(cat, gaia, ledger=ledger)

    # Controls have no archive literature; make that explicit rather than 0.
    if include_controls:
        m = cat["is_control"].fillna(False).astype(bool)
        for c in (
            "n_param_sets", "n_references", "rade_rel_spread",
            "composite_parameter_source_count", "composite_uses_mixed_sources",
            "default_solution_present", "default_solution_parameter_coverage",
            "default_solution_overlap_count",
            "composite_default_median_fractional_difference",
        ):
            if c in cat.columns:
                cat.loc[m, c] = np.nan

    return cat
