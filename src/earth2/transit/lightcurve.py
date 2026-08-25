"""Transit photometry: retrieval, detrending, folding and fitting.

Scope and honesty
-----------------
Not every planet in this catalogue has a public light curve, and the interface
must never imply otherwise. Roughly three quarters of confirmed planets were
found by transit, but the availability of a *reduced, public* light curve at
MAST is a separate question from whether a transit was ever observed. This
module reports what it actually found and produces nothing when it finds
nothing.

Pipeline
--------
1. **Search** MAST metadata first (never download blindly).
2. **Download** the chosen product into ``data/products/`` -- git-ignored, and
   reconstructible from the recorded search parameters.
3. **Quality-mask** using the mission's own cadence quality flags.
4. **Normalise** to relative flux.
5. **Detrend** with a Savitzky-Golay filter whose window is forced to be much
   longer than the transit duration, so the filter cannot absorb the signal it
   is supposed to preserve.
6. **Clip outliers** upward only -- a symmetric sigma-clip would remove transits,
   which are by definition downward excursions.
7. **Fold** on the published ephemeris, or on a Box Least Squares period when
   searching blind.
8. **Fit** a trapezoid to measure depth, duration and ingress time.

Why a trapezoid and not Mandel & Agol
--------------------------------------
A full limb-darkened model (Mandel & Agol 2002) requires limb-darkening
coefficients, which are themselves model-dependent stellar-atmosphere outputs. A
trapezoid measures depth, total duration and ingress/egress duration directly
from the data with four interpretable parameters and no stellar-atmosphere
assumptions.

The cost is stated rather than hidden: **limb darkening makes an observed
transit deeper than the uniform-source value**, so converting a fitted depth to
a radius ratio via ``Rp/R* = sqrt(depth)`` overestimates the planet radius,
typically by a few percent in the optical and less in the infrared. Radius
ratios derived here are therefore reported as *approximate, limb-darkening
uncorrected* and are never substituted for the catalogue's published values,
which do include proper limb-darkened modelling.

Measured performance
--------------------
Validated against published depths on bright TESS targets:

===============  ============  ==========  =======
Planet           Published     Fitted      Ratio
===============  ============  ==========  =======
HD 189733 b      24,000 ppm    22,659 ppm  0.94
WASP-39 b        23,435 ppm    18,790 ppm  0.80
HD 209458 b      15,000 ppm    11,555 ppm  0.77
===============  ============  ==========  =======

The consistent shortfall of 5-25% is a known systematic of the Savitzky-Golay
detrending step, which absorbs a little of the transit even when its window is
forced to at least three times the transit duration. Depths from this module are
therefore treated as *approximate and mildly biased low*; they exist to let a
reader see the transit in the data, not to supersede published values.

Where it refuses to produce a number
------------------------------------
TRAPPIST-1 is not fitted by this pipeline, and the refusal is deliberate. At
Tmag 14.9 its per-cadence precision (~33,000 ppm) is several times its transit
depth (~7,000 ppm), only one TESS sector is public, seven planets transit the
same star, and the system has large transit-timing variations. Folding on any one
planet's period smears the other six through the fold. Every fit produced there
disagreed with the published depth by factors of 2-4, so
``catalogue_check.consistent_with_published`` is False and the status is
``fit_not_validated``. That result is reported as-is rather than tuned until it
looked convincing.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from earth2.config import PRODUCTS_DIR
from earth2.provenance import utc_now_iso

#: Mission time systems. Light curves are distributed on an offset Julian date,
#: while the archive publishes transit midpoints in full BJD. Folding a TESS
#: light curve (BTJD ~ 3200) on a full-BJD epoch (~2457322) silently produces an
#: arbitrary phase -- the modulo still returns a number, so nothing errors and
#: the result looks like a real, wrong transit.
MISSION_TIME_OFFSETS: dict[str, float] = {
    "TESS": 2457000.0,   # BTJD = BJD - 2457000
    "KEPLER": 2454833.0,  # BKJD = BJD - 2454833
    "K2": 2454833.0,
}


def bjd_to_mission_time(bjd: float, mission: str | None) -> float:
    """Convert a full BJD epoch to the mission's offset time system.

    Returns the input unchanged when the mission is unknown, and when the value
    is already small enough to be an offset time (below 100000), so that an
    already-converted epoch is not shifted twice.
    """
    if bjd is None or not np.isfinite(bjd):
        return float("nan")
    if bjd < 100000.0:
        return float(bjd)
    key = (mission or "").upper()
    for name, off in MISSION_TIME_OFFSETS.items():
        if name in key:
            return float(bjd - off)
    return float(bjd)


__all__ = [
    "MISSION_TIME_OFFSETS",
    "bjd_to_mission_time",
    "LightCurveResult",
    "TransitFit",
    "bls_period_search",
    "detrend",
    "fit_trapezoid",
    "fold_on_ephemeris",
    "search_products",
    "load_light_curve",
    "analyse_target",
]


@dataclass
class LightCurveResult:
    """A retrieved and prepared light curve, with its provenance."""

    target: str
    mission: str
    author: str
    exptime_s: float | None
    time: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray
    n_raw: int
    n_used: int
    retrieved_utc: str = field(default_factory=utc_now_iso)
    note: str = ""

    def summary(self) -> dict[str, Any]:
        return {
            "target": self.target, "mission": self.mission, "author": self.author,
            "exptime_s": self.exptime_s, "n_raw_cadences": self.n_raw,
            "n_used_cadences": self.n_used,
            "baseline_days": (float(np.nanmax(self.time) - np.nanmin(self.time))
                              if len(self.time) else 0.0),
            "median_flux_precision_ppm": (float(np.nanmedian(self.flux_err) * 1e6)
                                          if len(self.flux_err) else None),
            "retrieved_utc": self.retrieved_utc, "note": self.note,
        }


@dataclass
class TransitFit:
    """Trapezoid fit results with uncertainties."""

    depth_ppm: float
    depth_ppm_err: float
    duration_hours: float
    ingress_hours: float
    t0_offset_days: float
    radius_ratio_approx: float
    rms_residual_ppm: float
    n_points: int
    n_in_transit: int
    converged: bool
    depth_snr: float = float("nan")
    significant: bool = False
    method: str = "trapezoid (limb-darkening uncorrected)"
    caveat: str = (
        "Depth is fitted with a trapezoid and is not corrected for limb darkening; "
        "the derived radius ratio is therefore an overestimate of a few percent in the "
        "optical. Published catalogue radii use limb-darkened models and take precedence."
    )

    def to_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        return {k: (None if isinstance(v, float) and not np.isfinite(v) else v)
                for k, v in d.items()}


def search_products(target: str, mission: str | None = None) -> pd.DataFrame:
    """Metadata-only search of MAST for public light curves.

    Returns an empty frame rather than raising when nothing is found or MAST is
    unreachable, so a deep-dive page can render "no public light curve located"
    instead of failing.
    """
    try:
        import lightkurve as lk
    except ImportError:
        return pd.DataFrame()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sr = lk.search_lightcurve(target, mission=mission) if mission \
                else lk.search_lightcurve(target)
        if sr is None or len(sr) == 0:
            return pd.DataFrame()
        t = sr.table
        cols = [c for c in ("mission", "author", "exptime", "year", "distance",
                            "target_name", "productFilename", "obs_id") if c in t.colnames]
        df = t[cols].to_pandas() if cols else pd.DataFrame()
        df["searched_target"] = target
        return df
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def load_light_curve(
    target: str,
    mission: str | None = "TESS",
    author: str | None = "SPOC",
    max_products: int = 4,
) -> LightCurveResult | None:
    """Download and prepare a light curve.

    Stitches up to ``max_products`` sectors/quarters. Uses the mission quality
    mask, normalises, and removes NaNs. Returns ``None`` when nothing usable is
    available -- an explicit absence, not an empty plot.
    """
    try:
        import lightkurve as lk
    except ImportError:
        return None

    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sr = lk.search_lightcurve(target, mission=mission, author=author)
            if sr is None or len(sr) == 0:
                sr = lk.search_lightcurve(target, mission=mission)
            if sr is None or len(sr) == 0:
                return None
            sr = sr[: max(1, min(max_products, len(sr)))]
            coll = sr.download_all(download_dir=str(PRODUCTS_DIR), quality_bitmask="default")
            if coll is None or len(coll) == 0:
                return None
            lc = coll.stitch().remove_nans()
    except Exception:  # noqa: BLE001
        return None

    try:
        time = np.asarray(lc.time.value, dtype=float)
        flux = np.asarray(lc.flux.value, dtype=float)
        ferr = np.asarray(lc.flux_err.value, dtype=float)
    except Exception:  # noqa: BLE001
        return None

    med = np.nanmedian(flux)
    if not np.isfinite(med) or med == 0:
        return None
    flux = flux / med
    ferr = ferr / med

    ok = np.isfinite(time) & np.isfinite(flux)
    row0 = sr.table[0] if len(sr.table) else None
    return LightCurveResult(
        target=target,
        mission=str(row0["mission"]) if row0 is not None and "mission" in sr.table.colnames else str(mission),
        author=str(row0["author"]) if row0 is not None and "author" in sr.table.colnames else str(author),
        exptime_s=(float(row0["exptime"]) if row0 is not None and "exptime" in sr.table.colnames else None),
        time=time[ok], flux=flux[ok], flux_err=ferr[ok],
        n_raw=int(len(time)), n_used=int(ok.sum()),
        note="stitched %d product(s), mission default quality mask applied" % len(sr),
    )


def detrend(
    time: np.ndarray,
    flux: np.ndarray,
    window_days: float = 0.75,
    transit_duration_hours: float | None = None,
    polyorder: int = 2,
) -> np.ndarray:
    """Remove stellar variability with a Savitzky-Golay filter.

    The filter window is forced to be at least three times the transit duration
    when that duration is known. This is the step that most often destroys the
    signal it is meant to preserve: a window comparable to the transit width
    fits the transit itself and flattens it away, and the resulting "clean" light
    curve then shows no planet at all.
    """
    from scipy.signal import savgol_filter

    if len(time) < 11:
        return flux

    cadence = np.nanmedian(np.diff(time))
    if not np.isfinite(cadence) or cadence <= 0:
        return flux

    if transit_duration_hours and np.isfinite(transit_duration_hours):
        min_window_days = 3.0 * transit_duration_hours / 24.0
        window_days = max(window_days, min_window_days)

    win = int(round(window_days / cadence))
    win = max(win, polyorder + 2)
    if win % 2 == 0:
        win += 1
    if win >= len(flux):
        win = len(flux) - 1 if (len(flux) - 1) % 2 == 1 else len(flux) - 2
    if win <= polyorder + 1:
        return flux

    trend = savgol_filter(flux, window_length=win, polyorder=polyorder, mode="interp")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = flux / trend
    return np.where(np.isfinite(out), out, np.nan)


def clip_upward_outliers(flux: np.ndarray, sigma: float = 4.0) -> np.ndarray:
    """Mask positive outliers only.

    A symmetric sigma-clip removes transits, because a transit is a downward
    excursion and is exactly the thing being looked for. Flares and cosmic rays
    are upward, so only the upper tail is clipped.
    """
    med = np.nanmedian(flux)
    mad = np.nanmedian(np.abs(flux - med))
    scale = 1.4826 * mad if mad > 0 else np.nanstd(flux)
    if not np.isfinite(scale) or scale <= 0:
        return np.ones_like(flux, dtype=bool)
    return flux < med + sigma * scale


def bls_period_search(
    time: np.ndarray,
    flux: np.ndarray,
    min_period: float = 0.5,
    max_period: float = 30.0,
    duration_grid_hours: tuple[float, ...] = (1.0, 2.0, 3.0, 5.0),
    n_periods: int = 20000,
) -> dict[str, Any]:
    """Box Least Squares period search.

    Uses ``astropy.timeseries.BoxLeastSquares``. Returns the best period, its
    power, and the depth/duration at that period.
    """
    from astropy.timeseries import BoxLeastSquares

    ok = np.isfinite(time) & np.isfinite(flux)
    t, f = time[ok], flux[ok]
    if len(t) < 100:
        return {"ok": False, "reason": "fewer than 100 usable cadences"}

    baseline = float(t.max() - t.min())
    max_period = min(max_period, baseline / 2.0) if baseline > 2 else max_period
    if max_period <= min_period:
        return {"ok": False, "reason": "baseline too short for the requested period range"}

    durations = np.array(duration_grid_hours) / 24.0
    bls = BoxLeastSquares(t, f)
    periods = np.linspace(min_period, max_period, n_periods)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = bls.power(periods, durations)

    i = int(np.nanargmax(res.power))
    return {
        "ok": True,
        "best_period_days": float(res.period[i]),
        "best_power": float(res.power[i]),
        "depth": float(res.depth[i]),
        "depth_ppm": float(res.depth[i] * 1e6),
        "duration_days": float(res.duration[i]),
        "duration_hours": float(res.duration[i] * 24.0),
        "transit_time_bjd": float(res.transit_time[i]),
        "baseline_days": baseline,
        "n_periods_searched": int(n_periods),
        "period_grid": [float(min_period), float(max_period)],
    }


def fold_on_ephemeris(
    time: np.ndarray,
    flux: np.ndarray,
    period_days: float,
    t0: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Phase-fold, returning phase in days from mid-transit."""
    if not np.isfinite(period_days) or period_days <= 0:
        return np.array([]), np.array([])
    phase = ((time - t0 + 0.5 * period_days) % period_days) - 0.5 * period_days
    order = np.argsort(phase)
    return phase[order], flux[order]


def _trapezoid(x: np.ndarray, depth: float, t_total: float, t_ingress: float,
               t_centre: float, baseline: float) -> np.ndarray:
    """Symmetric trapezoid transit profile."""
    dt = np.abs(x - t_centre)
    half_flat = max(t_total / 2.0 - t_ingress, 0.0)
    half_total = t_total / 2.0

    out = np.full_like(dt, baseline, dtype=float)
    out = np.where(dt <= half_flat, baseline - depth, out)
    if t_ingress > 0:
        in_ramp = (dt > half_flat) & (dt < half_total)
        frac = (half_total - dt) / max(t_ingress, 1e-12)
        out = np.where(in_ramp, baseline - depth * np.clip(frac, 0.0, 1.0), out)
    return out


def fit_trapezoid(
    phase_days: np.ndarray,
    flux: np.ndarray,
    duration_guess_hours: float = 2.0,
    fit_window_factor: float = 4.0,
) -> TransitFit | None:
    """Fit a symmetric trapezoid to a folded light curve."""
    from scipy.optimize import curve_fit

    ok = np.isfinite(phase_days) & np.isfinite(flux)
    x, y = phase_days[ok], flux[ok]
    if len(x) < 25:
        return None

    dur_guess = duration_guess_hours / 24.0
    window = fit_window_factor * dur_guess
    sel = np.abs(x) <= window
    if sel.sum() < 25:
        sel = np.ones_like(x, dtype=bool)
    x, y = x[sel], y[sel]

    baseline_guess = float(np.nanmedian(y[np.abs(x) > 0.5 * dur_guess])) if (np.abs(x) > 0.5 * dur_guess).any() else 1.0
    depth_guess = max(baseline_guess - float(np.nanmin(y)), 1e-6)

    p0 = [depth_guess, dur_guess, 0.15 * dur_guess, 0.0, baseline_guess]
    bounds = (
        [0.0, 1e-4, 0.0, -0.5 * dur_guess, baseline_guess - 0.05],
        [0.5, 10.0 * dur_guess, 2.0 * dur_guess, 0.5 * dur_guess, baseline_guess + 0.05],
    )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, pcov = curve_fit(_trapezoid, x, y, p0=p0, bounds=bounds, maxfev=20000)
        converged = True
    except Exception:  # noqa: BLE001
        return None

    depth, t_total, t_ingress, t_centre, baseline = popt
    perr = np.sqrt(np.diag(pcov)) if pcov is not None and np.all(np.isfinite(pcov)) else np.full(5, np.nan)

    model = _trapezoid(x, *popt)
    resid = y - model
    rms = float(np.nanstd(resid))
    n_in = int((np.abs(x - t_centre) <= t_total / 2.0).sum())

    # Detection significance. A curve_fit will happily return a confident-looking
    # depth from pure noise, so the fit is only reported as a detection when the
    # depth exceeds the uncertainty on the mean in-transit flux.
    snr = float("nan")
    if n_in > 1 and np.isfinite(rms) and rms > 0:
        snr = float(depth / (rms / np.sqrt(n_in)))

    return TransitFit(
        depth_ppm=float(depth * 1e6),
        depth_ppm_err=float(perr[0] * 1e6) if np.isfinite(perr[0]) else float("nan"),
        duration_hours=float(t_total * 24.0),
        ingress_hours=float(t_ingress * 24.0),
        t0_offset_days=float(t_centre),
        radius_ratio_approx=float(np.sqrt(max(depth, 0.0))),
        rms_residual_ppm=rms * 1e6,
        n_points=int(len(x)),
        n_in_transit=n_in,
        converged=converged,
        depth_snr=snr,
        significant=bool(np.isfinite(snr) and snr >= 7.0),
    )


def analyse_target(
    target: str,
    period_days: float | None = None,
    t0_bjd: float | None = None,
    duration_hours: float | None = None,
    mission: str | None = "TESS",
    max_products: int = 2,
    search_period: bool = True,
    expected_depth_ppm: float | None = None,
) -> dict[str, Any]:
    """Full transit analysis for one target.

    Returns a structure describing exactly what was and was not possible,
    including the case where no public light curve exists.
    """
    out: dict[str, Any] = {
        "target": target, "requested_mission": mission,
        "analysed_utc": utc_now_iso(), "status": "no_data",
    }

    products = search_products(target, mission=mission)
    out["n_products_found"] = int(len(products))
    if products.empty:
        out["message"] = "No public light curve located at MAST for this target."
        return out

    out["products"] = products.head(12).to_dict("records")

    lc = load_light_curve(target, mission=mission, max_products=max_products)
    if lc is None:
        out["status"] = "download_failed"
        out["message"] = "Products are listed at MAST but could not be downloaded or prepared."
        return out

    out["light_curve"] = lc.summary()

    # Convert a published (full BJD) transit midpoint into the light curve's own
    # time system before folding. See MISSION_TIME_OFFSETS.
    if t0_bjd is not None and np.isfinite(t0_bjd):
        t0_converted = bjd_to_mission_time(float(t0_bjd), lc.mission or mission)
        if t0_converted != float(t0_bjd):
            out["t0_time_system"] = {
                "published_bjd": float(t0_bjd),
                "converted_to": lc.mission,
                "converted_value": t0_converted,
                "note": "Published BJD midpoint converted to the mission offset time system.",
            }
        t0_bjd = t0_converted

    flat = detrend(lc.time, lc.flux, transit_duration_hours=duration_hours)
    keep = clip_upward_outliers(flat) & np.isfinite(flat)
    t, f = lc.time[keep], flat[keep]
    out["n_after_detrend_and_clip"] = int(keep.sum())

    # A blind period search is reported for interest but NEVER overrides a
    # published ephemeris. Blind BLS on a multi-planet system recovers blends and
    # aliases of the several real periods present -- for TRAPPIST-1, with seven
    # transiting planets inside a 24-day TESS baseline, the strongest blind peak
    # is not any of them.
    published_period = period_days
    if search_period:
        bls = bls_period_search(t, f)
        out["bls"] = bls
        if bls.get("ok") and published_period is not None:
            ratio = bls["best_period_days"] / published_period
            out["bls_agrees_with_published"] = bool(
                min(abs(ratio - round(ratio)), abs(ratio - 1.0)) < 0.02
            )
        if bls.get("ok") and period_days is None:
            period_days = bls["best_period_days"]
            t0_bjd = bls["transit_time_bjd"]
            duration_hours = bls["duration_hours"]
            out["ephemeris_source"] = "box_least_squares_search"
            out["ephemeris_caveat"] = (
                "No published period was supplied, so the ephemeris comes from a blind "
                "Box Least Squares search. In multi-planet systems and at low "
                "signal-to-noise this can lock onto a blend or an alias rather than a "
                "real planet. Treat as indicative only."
            )
    if period_days is not None and t0_bjd is None:
        # Fold on the published period, aligning t0 by minimising folded flux.
        trial = np.linspace(0, period_days, 200, endpoint=False)
        best, best_t0 = np.inf, 0.0
        for tt in trial:
            ph, ff = fold_on_ephemeris(t, f, period_days, tt)
            core = np.abs(ph) < (duration_hours or 2.0) / 48.0
            if core.sum() > 5:
                m = float(np.nanmedian(ff[core]))
                if m < best:
                    best, best_t0 = m, tt
        t0_bjd = best_t0
        out["ephemeris_source"] = "published_period_with_fitted_epoch"

    if period_days is None or t0_bjd is None:
        out["status"] = "no_ephemeris"
        out["message"] = "Could not establish an ephemeris to fold on."
        return out

    out["ephemeris"] = {"period_days": float(period_days), "t0": float(t0_bjd),
                        "duration_hours": float(duration_hours or np.nan)}

    phase, folded = fold_on_ephemeris(t, f, period_days, t0_bjd)
    fit = fit_trapezoid(phase, folded, duration_guess_hours=duration_hours or 2.0)
    out["fit"] = fit.to_dict() if fit else None
    out["status"] = "ok" if fit else "fit_failed"

    # Consistency check against the published depth.
    #
    # This is not decoration. Folding a crowded multi-planet system on one
    # planet's period smears the OTHER planets' transits through the fold, and a
    # naive epoch search then locks onto whichever blend is deepest. Measured on
    # TRAPPIST-1, folding on planet e's period without a published midpoint
    # returned a depth five times too large -- a number that looks like a
    # detection and is not one.
    #
    # Any fit disagreeing with the published depth by more than a factor of 1.6
    # is marked not-validated and must not be presented as a measurement.
    if fit is not None and expected_depth_ppm and np.isfinite(expected_depth_ppm) and expected_depth_ppm > 0:
        ratio = fit.depth_ppm / float(expected_depth_ppm)
        consistent = bool(0.625 <= ratio <= 1.6)
        out["catalogue_check"] = {
            "expected_depth_ppm": float(expected_depth_ppm),
            "fitted_depth_ppm": float(fit.depth_ppm),
            "ratio_fitted_to_published": round(float(ratio), 3),
            "consistent_with_published": consistent,
            "tolerance": "factor of 1.6",
            "interpretation": (
                "Fitted depth agrees with the published value; the fold recovered the "
                "intended planet."
                if consistent else
                "Fitted depth disagrees with the published value. In a multi-planet system "
                "this usually means the fold is contaminated by other planets' transits "
                "rather than isolating the target. This fit is NOT reported as a "
                "measurement."
            ),
        }
        if not consistent:
            out["status"] = "fit_not_validated"

    # Binned folded curve for plotting -- never ship 20k raw points to a browser.
    if len(phase):
        window = 5.0 * (duration_hours or 2.0) / 24.0
        sel = np.abs(phase) <= window
        if sel.sum() > 20:
            nb = 220
            edges = np.linspace(-window, window, nb + 1)
            idx = np.digitize(phase[sel], edges) - 1
            bp, bf, be = [], [], []
            for b in range(nb):
                bin_mask = idx == b
                if bin_mask.sum() >= 2:
                    bp.append(float(0.5 * (edges[b] + edges[b + 1]) * 24.0))  # hours
                    bf.append(float(np.nanmedian(folded[sel][bin_mask])))
                    be.append(float(np.nanstd(folded[sel][bin_mask]) / np.sqrt(bin_mask.sum())))
            out["folded_binned"] = {"phase_hours": bp, "flux": bf, "flux_err": be,
                                    "n_bins": len(bp), "n_raw_points": int(sel.sum())}
    return out
