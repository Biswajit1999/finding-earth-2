"""Interpretable candidate scoring.

Design position
---------------
There is **no machine-learning model here, and that is deliberate.** Supervised
learning requires labelled examples. There are no labelled inhabited exoplanets,
and there is exactly one labelled habitable one. Any model claiming to "predict
habitability" is either fitting to a hand-made label (in which case it has
learned the label-maker's opinion, not physics) or fitting to nothing at all.

Instead every score below is an explicit function of published measurements,
each term is exposed alongside the total, and the weights are parameters the
reader can change.

Four scores, four different questions
-------------------------------------
=====================================  ==================================================
Score                                  Question it answers
=====================================  ==================================================
``score_earth_similarity``             How close are the bulk properties to Earth's?
``score_conservative_habitability``    Is this consistent with a temperate rocky world?
``score_observational_confidence``     How well is it actually measured?
``score_characterisation_potential``   How feasible is atmospheric follow-up?
=====================================  ==================================================

They are reported separately because they genuinely disagree. TRAPPIST-1 e is
better *measured* than TOI-700 d; TOI-700 d is marginally more Earth-*similar*.
Collapsing that into one number destroys the only interesting part of the result.

The composite index
-------------------
``earth2_index`` is a **weighted geometric mean**, not a weighted average.

This matters. Under an arithmetic mean, an ultra-hot Jupiter with excellent
measurements and superb observability scores respectably despite zero
habitability -- its strong components compensate for the disqualifying one. That
is precisely the failure mode the project's sanity tests forbid.

A geometric mean is non-compensatory: a near-zero component drags the whole index
toward zero regardless of the others. Scores are floored at a small epsilon
rather than zero so that ordering is preserved among the disqualified rather than
collapsing them all to an indistinguishable 0.

Characterisation potential is **excluded from the default index** (weight 0). It
measures how easy a planet is to *observe*, not how Earth-like it is, and it
structurally penalises non-transiting planets -- which would push Proxima Cen b
down the list for a reason that has nothing to do with its properties. It remains
available as a weightable component for readers who want to prioritise
follow-up targets, and is reported as a ranking in its own right.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from earth2.constants import M_JUP_IN_M_EARTH


def _numeric_col(df: pd.DataFrame, name: str) -> pd.Series:
    """Numeric column, or an all-NaN Series of the right length if absent.

    ``df.get(name)`` returns ``None`` for a missing column, and
    ``pd.to_numeric(None, errors="coerce")`` silently returns a bare scalar
    NaN rather than a Series -- which crashes the moment a caller chains
    ``.fillna()`` or ``.clip()`` onto it. The full pipeline catalogue always
    carries every column this module reads, so the gap is latent; this helper
    closes it so the scoring functions behave the same way whether they see
    the full catalogue or a partial DataFrame (as in tests or notebooks).
    """
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    return pd.Series(np.nan, index=df.index, dtype=float)


__all__ = [
    "DEFAULT_WEIGHTS",
    "FOLLOWUP_EPOCH_JD",
    "MASS_CLASS_QUALITY",
    "ScoreWeights",
    "angular_separation_mas",
    "emission_spectroscopy_metric",
    "ephemeris_uncertainty_minutes",
    "orbital_separation_au",
    "rank_catalogue",
    "reflected_light_contrast",
    "rocky_plausibility",
    "rv_semi_amplitude_ms",
    "score_characterisation_potential",
    "score_conservative_habitability",
    "score_earth_similarity",
    "score_observational_confidence",
    "transmission_spectroscopy_metric",
]

#: Floor applied before the geometric mean, so a disqualifying component drives
#: the index toward zero without erasing the ordering among disqualified planets.
EPS = 0.01

#: How much evidential weight each mass provenance class carries.
#: An M-R-relationship mass is a prediction from the radius, so it earns very
#: little: using it to compute density and escape velocity re-encodes the radius
#: rather than adding independent information.
MASS_CLASS_QUALITY: dict[str, float] = {
    "measured": 1.00,
    "msini_deprojected": 0.75,
    "msini_lower_limit": 0.50,
    "upper_limit": 0.20,
    "inferred_mass_radius": 0.10,
    "missing": 0.00,
}


@dataclass
class ScoreWeights:
    """Weights for the composite Earth-2.0 index.

    Defaults put the most weight on physical plausibility as a temperate rocky
    world, then Earth similarity, then how well the thing is actually measured.
    """

    earth_similarity: float = 0.35
    conservative_habitability: float = 0.40
    observational_confidence: float = 0.25
    characterisation_potential: float = 0.00

    def as_dict(self) -> dict[str, float]:
        return {
            "earth_similarity": self.earth_similarity,
            "conservative_habitability": self.conservative_habitability,
            "observational_confidence": self.observational_confidence,
            "characterisation_potential": self.characterisation_potential,
        }

    def normalised(self) -> dict[str, float]:
        d = self.as_dict()
        total = sum(v for v in d.values() if v > 0)
        if total <= 0:
            raise ValueError("At least one score weight must be positive")
        return {k: (v / total if v > 0 else 0.0) for k, v in d.items()}


DEFAULT_WEIGHTS = ScoreWeights()

# A fixed planning horizon keeps exports reproducible while answering a useful
# operational question: how uncertain will the predicted transit time be at
# the start of 2030? JD 2462502.5 is 2030-01-01 00:00 UTC.
FOLLOWUP_EPOCH_JD = 2462502.5

# IAU nominal terrestrial equatorial radius expressed in astronomical units.
EARTH_RADIUS_AU = 4.26352124542639e-5


# --------------------------------------------------------------------------
# Component 1: Earth similarity
# --------------------------------------------------------------------------
def score_earth_similarity(df: pd.DataFrame) -> pd.Series:
    """Median Earth Similarity Index from the Monte Carlo posterior.

    The MC median is used rather than the nominal ESI so that the score reflects
    the propagated uncertainty rather than a point estimate.
    """
    if "esi_global_p50" in df.columns:
        s = pd.to_numeric(df["esi_global_p50"], errors="coerce")
        fallback = _numeric_col(df, "esi_global")
        return s.where(s.notna(), fallback).clip(0.0, 1.0)
    return _numeric_col(df, "esi_global").clip(0.0, 1.0)


# --------------------------------------------------------------------------
# Component 2: conservative habitability
# --------------------------------------------------------------------------
def rocky_plausibility(
    radius_earth: pd.Series,
    r_transition: float = 1.6,
    width: float = 0.20,
) -> pd.Series:
    """Probability-like plausibility that a planet is rocky, from its radius.

    A logistic in radius centred on 1.6 Earth radii:

    * Rogers (2015), ApJ 801, 41 -- 1.6 R_Earth is where 50% of Kepler planets
      become less dense than pure MgSiO3, i.e. must carry volatile envelopes.
    * Fulton et al. (2017), AJ 154, 109 -- the radius valley at 1.5-2.0 R_Earth
      separates rocky super-Earths from gas-rich sub-Neptunes.

    The transition width is set so the score falls from ~0.9 at 1.15 R_Earth to
    ~0.1 at 2.05 R_Earth, spanning the observed valley rather than imposing a
    hard cut at a single radius the data does not support.

    Returns NaN where the radius is unknown -- an unmeasured planet is not
    assumed rocky.
    """
    r = pd.to_numeric(radius_earth, errors="coerce")
    with np.errstate(over="ignore"):
        p = 1.0 / (1.0 + np.exp((r - r_transition) / width))
    return pd.Series(np.where(np.isfinite(r), p, np.nan), index=r.index)


def score_conservative_habitability(df: pd.DataFrame) -> pd.Series:
    """Consistency with a conservatively-defined temperate rocky world.

    The product of three independent requirements:

    1. **Habitable-zone membership probability** under the conservative
       (runaway-greenhouse to maximum-greenhouse) definition, taken from the
       Monte Carlo so that a planet on the boundary scores ~0.5 rather than a
       spurious yes or no.
    2. **Host-temperature validity fraction** (``hz_teff_valid_fraction``):
       ``hz_conservative_prob`` is a nanmean *conditional* on the draw's host
       Teff landing inside the Kopparapu polynomial's stated 2600-7200 K
       range (see :mod:`earth2.uncertainty.montecarlo`). For a host near or
       below that floor -- TRAPPIST-1 at 2566 K is the case the module
       docstring there names explicitly -- only a small minority of draws are
       ever evaluated, and the mean of just those can read as a confident
       "in the zone" while the model mostly could not say anything at all.
       Multiplying by the valid fraction turns "100% HZ probability from 9%
       of draws" into a score of ~0.09, which is what that evidence actually
       supports. Missing (pre-Monte-Carlo) rows default to fully valid so this
       does not silently zero out catalogues run before this field existed.
    3. **Rocky plausibility** from the radius.

    A product rather than a sum: a temperate mini-Neptune and a rocky planet at
    1500 K both fail to be Earth-like, and neither should be rescued by the term
    it does satisfy.
    """
    hz = _numeric_col(df, "hz_conservative_prob")
    if hz.isna().all() and "hz_conservative" in df.columns:
        hz = pd.to_numeric(df["hz_conservative"], errors="coerce")

    valid_fraction = _numeric_col(df, "hz_teff_valid_fraction").fillna(1.0).clip(0.0, 1.0)

    radius = df.get("pl_rade_p50")
    if radius is None or pd.to_numeric(radius, errors="coerce").isna().all():
        radius = df.get("pl_rade")
    rocky = rocky_plausibility(pd.to_numeric(radius, errors="coerce"))

    return (hz * valid_fraction * rocky).clip(0.0, 1.0)


# --------------------------------------------------------------------------
# Component 3: observational confidence
# --------------------------------------------------------------------------
def score_observational_confidence(df: pd.DataFrame) -> pd.Series:
    """How much the measurements behind this candidate can be trusted.

    Five contributions, equally weighted unless stated:

    ``mass_quality``
        From :data:`MASS_CLASS_QUALITY`. The dominant term, because roughly half
        the catalogue's masses are predictions from the radius rather than
        measurements, and density, escape velocity and hence two of the four ESI
        terms depend on the mass.
    ``uncertainty_coverage``
        Fraction of propagated parameters that actually carried a published
        error bar. Directly penalises the delta-function sampling described in
        :mod:`earth2.uncertainty`, so a planet that looks precise only because
        nobody published uncertainties cannot outrank a genuinely tight one.
    ``reference_depth``
        Independent published parameter sets, saturating around five. One paper
        is not a consensus.
    ``literature_agreement``
        1 minus the fractional spread in published radii. Exposes candidates
        where papers disagree materially about the same planet.
    ``parameter_completeness``
        Fraction of the core physical parameters that are present at all.
    """
    idx = df.index

    mass_class = df.get("mass_class", pd.Series("missing", index=idx)).astype(str)
    mass_quality = mass_class.map(MASS_CLASS_QUALITY).astype(float).fillna(0.0)

    unc_cov = _numeric_col(df, "mc_uncertainty_coverage").fillna(0.0)

    n_ref = _numeric_col(df, "n_references")
    ref_depth = (np.log1p(n_ref.fillna(0.0)) / np.log1p(5.0)).clip(0.0, 1.0)

    spread = _numeric_col(df, "rade_rel_spread")
    agreement = (1.0 - spread.clip(0.0, 1.0)).fillna(0.5)

    core = ["pl_rade", "pl_bmasse", "insol_used", "teq_used", "st_teff", "st_rad"]
    present = pd.DataFrame(
        {c: pd.to_numeric(df[c], errors="coerce").notna() for c in core if c in df.columns}
    )
    completeness = present.mean(axis=1) if not present.empty else pd.Series(0.0, index=idx)

    score = (
        0.34 * mass_quality
        + 0.24 * unc_cov
        + 0.14 * ref_depth
        + 0.12 * agreement
        + 0.16 * completeness
    )
    return score.clip(0.0, 1.0)


# --------------------------------------------------------------------------
# Component 4: characterisation potential
# --------------------------------------------------------------------------
def transmission_spectroscopy_metric(df: pd.DataFrame) -> pd.Series:
    """Kempton et al. (2018) Transmission Spectroscopy Metric.

    Reference: Kempton, E. M.-R., Bean, J. L., Louie, D. R., et al. (2018),
    *A Framework for Prioritizing the TESS Planetary Candidates Most Amenable to
    Atmospheric Characterization*, PASP 130, 114401,
    doi:10.1088/1538-3873/aadf6f

    ::

        TSM = S * (R_p^3 * T_eq) / (M_p * R_star^2) * 10^(-m_J / 5)

    with R_p in Earth radii, M_p in Earth masses, R_star in solar radii, T_eq in
    kelvin, m_J the host J-band magnitude, and the scale factor S binned by
    planet radius (0.190 / 1.26 / 1.28 / 1.15).

    .. note::
       Kempton's T_eq is defined for **zero albedo** with full redistribution.
       The pipeline's working ``teq_used`` assumes a Bond albedo of 0.306, so it
       cannot be substituted directly. The zero-albedo temperature is recomputed
       here from the incident flux so the metric matches its published
       definition.

    Returns NaN for non-transiting planets: a transmission spectrum requires a
    transit, so the metric is undefined rather than zero.
    """
    rp = _numeric_col(df, "pl_rade")
    mp = _numeric_col(df, "pl_bmasse")
    rs = _numeric_col(df, "st_rad")
    mj = _numeric_col(df, "sy_jmag")
    insol = _numeric_col(df, "insol_used")

    # Kempton's zero-albedo equilibrium temperature.
    with np.errstate(invalid="ignore"):
        teq_a0 = 278.5 * (insol ** 0.25)

    scale = pd.Series(np.nan, index=df.index)
    scale[rp < 1.5] = 0.190
    scale[(rp >= 1.5) & (rp < 2.75)] = 1.26
    scale[(rp >= 2.75) & (rp < 4.0)] = 1.28
    scale[rp >= 4.0] = 1.15

    with np.errstate(invalid="ignore", divide="ignore"):
        tsm = scale * (rp**3 * teq_a0) / (mp * rs**2) * 10 ** (-mj / 5.0)

    transiting = _numeric_col(df, "tran_flag").fillna(0) == 1
    tsm = tsm.where(np.isfinite(tsm))
    return tsm.where(transiting)


def emission_spectroscopy_metric(df: pd.DataFrame) -> pd.Series:
    """Kempton et al. (2018) Emission Spectroscopy Metric.

    ::

        ESM = 4.29e6 * (B_7.5(T_day) / B_7.5(T_star)) * (R_p / R_star)^2 * 10^(-m_K/5)

    where ``B_7.5`` is the Planck function at 7.5 microns and the day-side
    temperature is taken as ``T_day = 1.10 * T_eq`` (zero-albedo).
    """
    rp = _numeric_col(df, "pl_rade")
    rs = _numeric_col(df, "st_rad")
    mk = _numeric_col(df, "sy_kmag")
    teff = _numeric_col(df, "st_teff")
    insol = _numeric_col(df, "insol_used")

    with np.errstate(invalid="ignore"):
        teq_a0 = 278.5 * (insol ** 0.25)
        t_day = 1.10 * teq_a0

    # Planck function at 7.5 micron, in arbitrary consistent units (the ratio is
    # what matters). hc/(lambda k) = 1918.9 K at 7.5 um.
    c2_over_lambda = 1918.9

    def planck_ratio(t_hot: pd.Series, t_star: pd.Series) -> pd.Series:
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            num = np.expm1(c2_over_lambda / t_star)
            den = np.expm1(c2_over_lambda / t_hot)
            return num / den

    ratio = planck_ratio(t_day, teff)

    # R_p and R_star must be in the same units; convert R_p from Earth radii to
    # solar radii (1 R_sun = 109.076 R_earth using IAU nominal equatorial values).
    r_earth_per_r_sun = 109.076
    with np.errstate(invalid="ignore", divide="ignore"):
        esm = 4.29e6 * ratio * ((rp / r_earth_per_r_sun) / rs) ** 2 * 10 ** (-mk / 5.0)

    transiting = _numeric_col(df, "tran_flag").fillna(0) == 1
    esm = esm.where(np.isfinite(esm))
    return esm.where(transiting)


def rv_semi_amplitude_ms(df: pd.DataFrame) -> pd.Series:
    """Expected radial-velocity semi-amplitude, m/s.

    ::

        K = 28.4329 m/s * (M_p sin i / M_Jup) * ((M_star + M_p)/M_Sun)^(-2/3)
                        * (P / 1 yr)^(-1/3) / sqrt(1 - e^2)

    Tells the reader whether a mass measurement is even feasible with current
    spectrographs -- an Earth-mass planet in the habitable zone of a Sun-like
    star produces K ~ 0.09 m/s, well below present-day precision.
    """
    mp_e = _numeric_col(df, "pl_bmasse")
    ms = _numeric_col(df, "st_mass")
    per_d = _numeric_col(df, "pl_orbper")
    ecc = _numeric_col(df, "pl_orbeccen").fillna(0.0).clip(0.0, 0.95)

    mp_j = mp_e / M_JUP_IN_M_EARTH
    total_mass = ms + mp_e / 332946.0  # planet mass in solar units
    per_yr = per_d / 365.25

    with np.errstate(invalid="ignore", divide="ignore"):
        k = (28.4329 * mp_j * total_mass ** (-2.0 / 3.0)
             * per_yr ** (-1.0 / 3.0) / np.sqrt(1.0 - ecc**2))
    return k.where(np.isfinite(k))


def ephemeris_uncertainty_minutes(
    df: pd.DataFrame,
    target_jd: float = FOLLOWUP_EPOCH_JD,
) -> pd.Series:
    """Forecast 1-sigma transit-time uncertainty at a fixed Julian Date.

    With no published covariance between epoch and period, the transparent
    first-order propagation is

    ``sigma_T(N) = sqrt(sigma_T0^2 + N^2 sigma_P^2)``.

    The larger absolute side of each asymmetric archive uncertainty is used.
    A value is returned only for transiting planets with a published midpoint,
    period, and both corresponding uncertainties. TTV-flagged systems retain
    the numeric forecast but carry ``ttv_flag`` separately because the linear
    ephemeris can be incomplete for them.
    """
    period = _numeric_col(df, "pl_orbper")
    midpoint = _numeric_col(df, "pl_tranmid")
    period_sigma = pd.concat(
        [_numeric_col(df, "pl_orbpererr1").abs(), _numeric_col(df, "pl_orbpererr2").abs()],
        axis=1,
    ).max(axis=1, skipna=False)
    midpoint_sigma = pd.concat(
        [_numeric_col(df, "pl_tranmiderr1").abs(), _numeric_col(df, "pl_tranmiderr2").abs()],
        axis=1,
    ).max(axis=1, skipna=False)

    with np.errstate(invalid="ignore", divide="ignore"):
        cycles = np.rint((target_jd - midpoint) / period).abs()
        sigma_days = np.sqrt(midpoint_sigma**2 + (cycles * period_sigma) ** 2)
    transiting = _numeric_col(df, "tran_flag").fillna(0).eq(1)
    valid = (
        transiting
        & period.gt(0)
        & midpoint.notna()
        & period_sigma.notna()
        & midpoint_sigma.notna()
    )
    return (sigma_days * 1440.0).where(valid & np.isfinite(sigma_days))


def orbital_separation_au(df: pd.DataFrame) -> pd.Series:
    """Nominal orbital separation, preferring measured semi-major axis.

    When the archive does not publish ``a``, derive it from period and stellar
    mass with Kepler's third law in solar units. This is a geometry diagnostic,
    not an orbit fit; eccentric orbits still need epoch-specific modelling.
    """
    measured = _numeric_col(df, "pl_orbsmax").where(_numeric_col(df, "pl_orbsmax") > 0)
    period_years = _numeric_col(df, "pl_orbper") / 365.25
    stellar_mass = _numeric_col(df, "st_mass")
    with np.errstate(invalid="ignore"):
        derived = (stellar_mass * period_years**2) ** (1.0 / 3.0)
    derived = derived.where((period_years > 0) & (stellar_mass > 0))
    return measured.where(measured.notna(), derived)


def angular_separation_mas(df: pd.DataFrame) -> pd.Series:
    """Nominal maximum star-planet angular separation in milliarcseconds.

    ``theta_mas = 1000 * a_au / d_pc``. This is the maximum circular-orbit
    scale, not a promise that a planet is outside a particular instrument's
    inner working angle at a requested observing epoch.
    """
    separation = orbital_separation_au(df)
    distance = _numeric_col(df, "sy_dist")
    with np.errstate(invalid="ignore", divide="ignore"):
        theta = 1000.0 * separation / distance
    return theta.where((distance > 0) & np.isfinite(theta))


def reflected_light_contrast(
    df: pd.DataFrame,
    geometric_albedo: float = 0.30,
) -> pd.Series:
    """Planet/star reflected-light contrast at quadrature.

    Assumes a Lambert sphere, for which the phase function at quadrature is
    ``1/pi``: ``contrast = A_g * (R_p/a)^2 / pi``. The geometric albedo is an
    explicit scenario assumption, not a measurement and not a ranking input.
    """
    radius_au = _numeric_col(df, "pl_rade") * EARTH_RADIUS_AU
    separation = orbital_separation_au(df)
    with np.errstate(invalid="ignore", divide="ignore"):
        contrast = geometric_albedo * (radius_au / separation) ** 2 / np.pi
    return contrast.where((separation > 0) & (radius_au > 0) & np.isfinite(contrast))


def score_characterisation_potential(df: pd.DataFrame) -> pd.Series:
    """Feasibility of atmospheric follow-up, scaled to [0, 1].

    Built from the TSM, log-scaled because the metric spans several orders of
    magnitude, and anchored so that Kempton's recommended threshold for small
    planets (TSM > 10 for R_p < 1.5 R_Earth) lands mid-scale.

    Planets with existing published atmospheric spectroscopy receive a modest
    bonus, since demonstrated observability is stronger evidence than a predicted
    metric.

    NaN for non-transiting planets, where the metric is undefined.
    """
    tsm = transmission_spectroscopy_metric(df)
    with np.errstate(invalid="ignore", divide="ignore"):
        scaled = (np.log10(tsm.where(tsm > 0)) + 1.0) / 3.0
    score = pd.Series(scaled, index=df.index).clip(0.0, 1.0)

    has_atmo = df.get("has_atmosphere_data")
    if has_atmo is not None:
        bonus = has_atmo.fillna(False).astype(bool).astype(float) * 0.10
        score = (score.fillna(0.0) + bonus).clip(0.0, 1.0).where(
            score.notna() | (bonus > 0)
        )
    return score


# --------------------------------------------------------------------------
# Composite
# --------------------------------------------------------------------------
def rank_catalogue(
    df: pd.DataFrame,
    weights: ScoreWeights | None = None,
) -> pd.DataFrame:
    """Attach all four component scores and the composite Earth-2.0 index.

    The composite is a weighted geometric mean over components with non-zero
    weight. A planet missing any weighted component cannot be ranked and receives
    NaN plus ``rankable = False``, rather than being scored on partial
    information and silently mixed in with fully-characterised candidates.
    """
    w = (weights or DEFAULT_WEIGHTS).normalised()
    out = df.copy()

    out["score_earth_similarity"] = score_earth_similarity(out)
    out["score_conservative_habitability"] = score_conservative_habitability(out)
    out["score_observational_confidence"] = score_observational_confidence(out)
    out["score_characterisation_potential"] = score_characterisation_potential(out)

    out["tsm"] = transmission_spectroscopy_metric(out)
    out["esm"] = emission_spectroscopy_metric(out)
    out["rv_semi_amplitude_ms"] = rv_semi_amplitude_ms(out)
    out["ephemeris_uncertainty_2030_minutes"] = ephemeris_uncertainty_minutes(out)
    out["followup_orbital_separation_au"] = orbital_separation_au(out)
    measured_separation = _numeric_col(out, "pl_orbsmax").gt(0)
    out["followup_separation_source"] = np.where(
        out["followup_orbital_separation_au"].notna(),
        np.where(measured_separation, "catalogue", "derived_from_period_and_stellar_mass"),
        "missing",
    )
    out["max_angular_separation_mas"] = angular_separation_mas(out)
    out["reflected_light_contrast_ag0p3"] = reflected_light_contrast(out)
    out["reflected_light_geometric_albedo_assumed"] = 0.30
    out["rocky_plausibility"] = rocky_plausibility(
        pd.to_numeric(out.get("pl_rade_p50", out.get("pl_rade")), errors="coerce")
    )

    active = {k: v for k, v in w.items() if v > 0}
    log_sum = pd.Series(0.0, index=out.index)
    usable = pd.Series(True, index=out.index)

    for name, weight in active.items():
        col = out["score_" + name]
        usable &= col.notna()
        floored = col.fillna(EPS).clip(lower=EPS, upper=1.0)
        log_sum = log_sum + weight * np.log(floored)

    index = np.exp(log_sum)
    out["earth2_index"] = index.where(usable)
    out["rankable"] = usable

    # Solar System controls are scored identically to exoplanets -- no
    # special-casing, because a hidden adjustment for the yardstick would
    # invalidate the comparison. But they are excluded from the rank *numbering*.
    #
    # The reason is specific: observational confidence measures how well the
    # ARCHIVE documents a target (published error bars, independent references,
    # mass provenance). A Solar System body has no archive parameter set, so it
    # scores low on that axis by construction -- Earth lands near 0.56 -- which
    # says nothing about how well Earth is actually measured. Ranking controls
    # against exoplanets on that axis would be meaningless in both directions.
    #
    # Their similarity and habitability scores ARE directly comparable and are
    # displayed as reference lines throughout.
    is_control = out.get("is_control")
    control_mask = (
        is_control.fillna(False).astype(bool)
        if is_control is not None
        else pd.Series(False, index=out.index)
    )
    out["is_control"] = control_mask

    rank_source = out["earth2_index"].where(~control_mask)
    out["earth2_rank"] = rank_source.rank(ascending=False, method="min").astype("Int64")

    for c in ("earth_similarity", "conservative_habitability",
              "observational_confidence", "characterisation_potential"):
        out["rank_" + c] = (
            out["score_" + c]
            .where(~control_mask)
            .rank(ascending=False, method="min")
            .astype("Int64")
        )

    out.attrs["score_weights"] = w
    out.attrs["control_note"] = (
        "Solar System controls are scored with the same functions as exoplanets but "
        "excluded from rank numbering: observational confidence measures archive "
        "documentation, which does not exist for Solar System bodies."
    )
    return out
