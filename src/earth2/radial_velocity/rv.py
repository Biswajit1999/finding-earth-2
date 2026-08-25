"""Radial-velocity analysis.

Data source
-----------
The Data & Analysis Center for Exoplanets (DACE), University of Geneva, serves
public radial-velocity time series through the ``dace-query`` package. Public
data requires no authentication; private programme data does, and this project
uses only the public holdings.

DACE returns not only velocities and their uncertainties but the **stellar
activity indicators measured from the same spectra** -- log R'HK, H-alpha, the
Ca II H&K S-index, the cross-correlation function FWHM and bisector span. That
matters more than it might appear, and it is the reason this module exists in
the form it does.

The central problem in radial velocity
--------------------------------------
A star is not a rigid sphere. Spots, plage and convective inhibition rotate in
and out of view, distorting the spectral lines and producing an apparent
velocity shift that is periodic on the **stellar rotation period** and its
harmonics. Such a signal has no planet in it at all.

This has repeatedly produced planet claims that were later withdrawn. The
discipline that guards against it is simple and non-negotiable:

    Compute the periodogram of the activity indicators alongside the
    periodogram of the velocities, and compare the peaks.

If a candidate period coincides with a peak in log R'HK, H-alpha, the S-index,
or the bisector span, the signal is consistent with stellar activity and must
not be presented as a planet without further argument.

:func:`analyse_target` therefore always returns activity periodograms next to
the RV periodogram, and explicitly flags coincidences. It does not hide them,
and it does not require the reader to know to ask.

Instrument offsets
------------------
Different spectrographs -- and the same spectrograph before and after a hardware
intervention -- have different velocity zero points. HARPS's 2015 fibre upgrade
is the canonical example. Combining instruments without fitting an offset per
instrument injects a step function into the time series, which a periodogram
happily converts into spurious long-period power. This module separates by
instrument, subtracts a per-instrument median, and reports the offsets it
removed.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from earth2.constants import M_JUP_IN_M_EARTH
from earth2.provenance import utc_now_iso

__all__ = [
    "ACTIVITY_INDICATORS",
    "RVDataset",
    "analyse_target",
    "fetch_dace_timeseries",
    "lomb_scargle",
    "planet_mass_from_k",
    "remove_instrument_offsets",
]

DACE_CITATION = (
    "This research has made use of the Data & Analysis Center for Exoplanets (DACE), "
    "operated by the University of Geneva. "
    "Buchschacher, N., Segransan, D., Udry, S., Diaz, R. (2015), ASP Conference Series 495, 7."
)
DACE_URL = "https://dace.unige.ch/"

#: Activity indicators DACE provides, with human labels. Each is measured from
#: the same spectrum that produced the velocity, so a shared periodicity is
#: strong evidence that the "velocity" is a line-shape effect.
ACTIVITY_INDICATORS: dict[str, str] = {
    "spectro_rhk": "log R'HK (chromospheric emission)",
    "spectro_halpha": "H-alpha index",
    "spectro_ca": "Ca II H&K index",
    "spectro_smw": "Mount Wilson S-index",
    "ccf_fwhm": "CCF FWHM (line width)",
    "ccf_bispan": "CCF bisector span (line asymmetry)",
    "ccf_contrast": "CCF contrast (line depth)",
}


@dataclass
class RVDataset:
    """A retrieved radial-velocity time series with its provenance."""

    target: str
    time: np.ndarray            # reduced JD
    rv: np.ndarray              # m/s
    rv_err: np.ndarray          # m/s
    instrument: np.ndarray
    frame: pd.DataFrame = field(repr=False, default_factory=pd.DataFrame)
    n_raw: int = 0
    n_used: int = 0
    retrieved_utc: str = field(default_factory=utc_now_iso)

    def summary(self) -> dict[str, Any]:
        base = float(np.nanmax(self.time) - np.nanmin(self.time)) if len(self.time) else 0.0
        return {
            "target": self.target,
            "n_measurements_raw": int(self.n_raw),
            "n_measurements_used": int(self.n_used),
            "baseline_days": round(base, 2),
            "baseline_years": round(base / 365.25, 2),
            "instruments": {str(k): int(v) for k, v in
                            pd.Series(self.instrument).value_counts().items()},
            "median_uncertainty_ms": (round(float(np.nanmedian(self.rv_err)), 3)
                                      if len(self.rv_err) else None),
            "rv_rms_ms": round(float(np.nanstd(self.rv)), 3) if len(self.rv) else None,
            "retrieved_utc": self.retrieved_utc,
            "source": "DACE (public)",
            "citation": DACE_CITATION,
        }


def fetch_dace_timeseries(target: str, apply_qc: bool = True) -> RVDataset | None:
    """Retrieve a public RV time series from DACE.

    ``apply_qc`` keeps only measurements whose data-reduction quality flag
    passed. Returns ``None`` if DACE is unavailable or has no public data for
    the target -- an explicit absence rather than an empty plot.
    """
    try:
        from dace_query.spectroscopy import Spectroscopy
    except ImportError:
        return None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df = Spectroscopy.get_timeseries(
                target=target, sorted_by_instrument=False, output_format="pandas"
            )
    except Exception:  # noqa: BLE001
        return None

    if df is None or len(df) == 0:
        return None

    n_raw = len(df)
    work = df.copy()
    if apply_qc and "drs_qc" in work.columns:
        work = work[work["drs_qc"].astype(bool)]

    for c in ("rjd", "rv", "rv_err"):
        if c not in work.columns:
            return None
        work[c] = pd.to_numeric(work[c], errors="coerce")
    work = work.dropna(subset=["rjd", "rv", "rv_err"])
    if work.empty:
        return None

    inst = (work["instrument_name"] if "instrument_name" in work.columns
            else work.get("ins_mode", pd.Series(["unknown"] * len(work))))

    return RVDataset(
        target=target,
        time=work["rjd"].to_numpy(dtype=float),
        rv=work["rv"].to_numpy(dtype=float),
        rv_err=work["rv_err"].to_numpy(dtype=float),
        instrument=np.asarray(inst.astype(str)),
        frame=work,
        n_raw=int(n_raw),
        n_used=int(len(work)),
    )


def remove_instrument_offsets(
    rv: np.ndarray,
    instrument: np.ndarray,
) -> tuple[np.ndarray, dict[str, float]]:
    """Subtract a per-instrument median velocity.

    Returns the offset-corrected velocities and the offsets removed. Reported
    rather than silently applied, because the offsets are physically meaningful:
    a large one usually marks a genuine instrumental change, and combining data
    across it without a correction manufactures long-period power.
    """
    out = np.array(rv, dtype=float, copy=True)
    offsets: dict[str, float] = {}
    for name in pd.unique(instrument):
        m = instrument == name
        if m.sum() == 0:
            continue
        off = float(np.nanmedian(out[m]))
        out[m] -= off
        offsets[str(name)] = round(off, 4)
    return out, offsets


def lomb_scargle(
    time: np.ndarray,
    values: np.ndarray,
    errors: np.ndarray | None = None,
    min_period_days: float = 1.0,
    max_period_days: float | None = None,
    samples_per_peak: int = 12,
    n_top: int = 6,
) -> dict[str, Any]:
    """Generalised Lomb-Scargle periodogram with false-alarm probabilities.

    Uses ``astropy.timeseries.LombScargle`` with a floating mean (the
    "generalised" periodogram of Zechmeister & Kuerster 2009), which is the
    correct choice for RV data where the systemic velocity is unknown.

    False-alarm probabilities use the Baluev (2008) analytic approximation.
    An FAP is the probability of a peak that strong arising from noise ALONE --
    it is not the probability that a planet exists, and a low FAP on a signal
    that also appears in the activity indicators means only that the activity
    signal is strong.
    """
    from astropy.timeseries import LombScargle

    ok = np.isfinite(time) & np.isfinite(values)
    t, y = time[ok], values[ok]
    dy = errors[ok] if errors is not None and len(errors) == len(ok) else None
    if len(t) < 12:
        return {"ok": False, "reason": "fewer than 12 usable points"}

    baseline = float(t.max() - t.min())
    if max_period_days is None:
        max_period_days = max(baseline, 2 * min_period_days)
    if baseline <= 0:
        return {"ok": False, "reason": "zero baseline"}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ls = LombScargle(t, y, dy) if dy is not None else LombScargle(t, y)
        freq, power = ls.autopower(
            minimum_frequency=1.0 / max_period_days,
            maximum_frequency=1.0 / min_period_days,
            samples_per_peak=samples_per_peak,
            normalization="standard",
        )

    periods = 1.0 / freq
    order = np.argsort(power)[::-1]

    # Collect distinct peaks (not adjacent grid points of the same peak).
    peaks: list[dict[str, Any]] = []
    taken: list[float] = []
    for i in order:
        p = float(periods[i])
        if any(abs(np.log10(p) - np.log10(q)) < 0.02 for q in taken):
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fap = float(ls.false_alarm_probability(power[i], method="baluev"))
        except Exception:  # noqa: BLE001
            fap = float("nan")
        peaks.append({"period_days": round(p, 5), "power": round(float(power[i]), 5),
                      "fap": fap})
        taken.append(p)
        if len(peaks) >= n_top:
            break

    # Downsample the curve for transport to a browser.
    step = max(1, len(periods) // 3000)
    return {
        "ok": True,
        "n_points": int(len(t)),
        "baseline_days": round(baseline, 2),
        "period_range": [float(min_period_days), float(max_period_days)],
        "peaks": peaks,
        "best_period_days": peaks[0]["period_days"] if peaks else None,
        "best_fap": peaks[0]["fap"] if peaks else None,
        "curve": {
            "period_days": [round(float(x), 5) for x in periods[::step][::-1]],
            "power": [round(float(x), 5) for x in power[::step][::-1]],
        },
        "method": "generalised Lomb-Scargle (floating mean), Baluev FAP",
    }


def planet_mass_from_k(
    k_ms: float,
    period_days: float,
    stellar_mass_sun: float,
    eccentricity: float = 0.0,
) -> float:
    """Minimum planet mass (M sin i) in Earth masses from an RV semi-amplitude.

    Inverts the standard relation. The result is a **lower limit**: without the
    orbital inclination, only ``M sin i`` is constrained.
    """
    if not all(np.isfinite([k_ms, period_days, stellar_mass_sun])):
        return float("nan")
    if period_days <= 0 or stellar_mass_sun <= 0:
        return float("nan")
    per_yr = period_days / 365.25
    ecc = min(max(eccentricity, 0.0), 0.95)
    m_jup = (k_ms / 28.4329) * (stellar_mass_sun ** (2.0 / 3.0)) * (per_yr ** (1.0 / 3.0)) \
        * np.sqrt(1.0 - ecc**2)
    return float(m_jup * M_JUP_IN_M_EARTH)


def _fit_sinusoid(
    t: np.ndarray, y: np.ndarray, dy: np.ndarray | None, period: float
) -> dict[str, Any]:
    """Least-squares circular-orbit fit at a fixed period."""
    from scipy.optimize import curve_fit

    def model(x, k, phase, offset):
        return k * np.sin(2 * np.pi * x / period + phase) + offset

    try:
        sigma = dy if dy is not None and np.all(np.isfinite(dy)) and np.all(dy > 0) else None
        p0 = [np.nanstd(y), 0.0, np.nanmedian(y)]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, pcov = curve_fit(model, t, y, p0=p0, sigma=sigma,
                                   absolute_sigma=sigma is not None, maxfev=20000)
        perr = np.sqrt(np.diag(pcov))
        resid = y - model(t, *popt)

        k = abs(float(popt[0]))
        k_err = float(perr[0])
        rms = float(np.nanstd(resid))
        k_snr = (k / k_err) if (np.isfinite(k_err) and k_err > 0) else float("nan")

        # Reliability gate.
        #
        # curve_fit returns an amplitude for ANY input, including pure noise at a
        # fixed period. On TRAPPIST-1 -- 33 velocities of a faint M8 dwarf over
        # 3.2 years -- it returned K = 18 m/s with a residual scatter of
        # 1848 m/s, implying M sin i = 10 Earth masses for a planet known to be
        # about one. Three conditions must hold before the fit is reported as a
        # measurement rather than as a diagnostic.
        n_pts = int(len(t))
        reasons: list[str] = []
        if n_pts < 20:
            reasons.append("fewer than 20 velocities (%d)" % n_pts)
        if not (np.isfinite(k_snr) and k_snr >= 3.0):
            reasons.append(f"amplitude significance below 3 sigma (K/sigma_K = {k_snr:.1f})")
        if np.isfinite(rms) and k > 0 and rms > 5.0 * k:
            reasons.append(f"residual scatter {rms:.1f} m/s exceeds five times the fitted "
                           f"amplitude {k:.1f} m/s")

        reliable = not reasons
        return {
            "ok": True,
            "semi_amplitude_ms": round(k, 4),
            "semi_amplitude_err_ms": round(k_err, 4),
            "semi_amplitude_snr": (round(k_snr, 2) if np.isfinite(k_snr) else None),
            "offset_ms": round(float(popt[2]), 4),
            "residual_rms_ms": round(rms, 4),
            "n_points": n_pts,
            "reliable": reliable,
            "unreliable_because": reasons,
            "model": "circular (fixed period, fitted amplitude/phase/offset)",
            "caveat": (
                "Eccentricity is not fitted; a Keplerian fit is required for eccentric orbits."
                if reliable else
                "THIS FIT IS NOT A MEASUREMENT. The data cannot support an amplitude at this "
                "period; the value is reported only so the failure is visible."
            ),
        }
    except Exception:  # noqa: BLE001
        return {"ok": False}


def analyse_target(
    target: str,
    stellar_mass_sun: float | None = None,
    known_period_days: float | None = None,
    min_period_days: float = 1.0,
    activity_match_tolerance: float = 0.05,
) -> dict[str, Any]:
    """Full RV analysis for one target, including the activity cross-check.

    The activity cross-check is not optional and not buried: any RV peak whose
    period lies within ``activity_match_tolerance`` (fractional) of a peak in any
    activity indicator is reported as a coincidence, with the indicator named.
    """
    out: dict[str, Any] = {
        "target": target, "analysed_utc": utc_now_iso(), "status": "no_data",
        "source": "DACE (public)", "citation": DACE_CITATION, "source_url": DACE_URL,
    }

    ds = fetch_dace_timeseries(target)
    if ds is None:
        out["message"] = "No public radial-velocity time series located at DACE for this target."
        return out

    out["dataset"] = ds.summary()

    rv_corrected, offsets = remove_instrument_offsets(ds.rv, ds.instrument)
    out["instrument_offsets_removed_ms"] = offsets
    out["instrument_offset_note"] = (
        "A per-instrument median was subtracted. Combining spectrographs -- or one "
        "spectrograph across a hardware intervention -- without this injects a step "
        "into the time series, which a periodogram converts into spurious long-period power."
    )

    max_p = max(ds.time.max() - ds.time.min(), 2 * min_period_days)
    rv_ls = lomb_scargle(ds.time, rv_corrected, ds.rv_err,
                         min_period_days=min_period_days, max_period_days=max_p)
    out["rv_periodogram"] = rv_ls

    # Activity indicators from the same spectra.
    activity: dict[str, Any] = {}
    for col, label in ACTIVITY_INDICATORS.items():
        if col not in ds.frame.columns:
            continue
        v = pd.to_numeric(ds.frame[col], errors="coerce").to_numpy(dtype=float)
        if np.isfinite(v).sum() < 12:
            continue
        res = lomb_scargle(ds.time, v, None,
                           min_period_days=min_period_days, max_period_days=max_p, n_top=4)
        if res.get("ok"):
            res["label"] = label
            # Trim curves for indicators; only peaks are needed for the cross-check.
            res.pop("curve", None)
            activity[col] = res
    out["activity_periodograms"] = activity

    # Cross-check.
    coincidences: list[dict[str, Any]] = []
    if rv_ls.get("ok"):
        for peak in rv_ls["peaks"]:
            p = peak["period_days"]
            for col, res in activity.items():
                for apeak in res["peaks"]:
                    ap = apeak["period_days"]
                    if ap <= 0:
                        continue
                    if abs(p - ap) / ap <= activity_match_tolerance:
                        coincidences.append({
                            "rv_period_days": p,
                            "rv_power": peak["power"],
                            "indicator": col,
                            "indicator_label": ACTIVITY_INDICATORS.get(col, col),
                            "indicator_period_days": ap,
                            "fractional_difference": round(abs(p - ap) / ap, 4),
                            "interpretation": (
                                "This RV period coincides with a periodicity in a stellar "
                                "activity indicator measured from the same spectra. The signal "
                                "is consistent with stellar activity and must not be treated as "
                                "a planet without further argument."
                            ),
                        })
    out["activity_coincidences"] = coincidences
    out["n_activity_coincidences"] = len(coincidences)

    # Optional circular fit at a known or best period.
    fit_period = known_period_days or (rv_ls.get("best_period_days") if rv_ls.get("ok") else None)
    if fit_period:
        fit = _fit_sinusoid(ds.time, rv_corrected, ds.rv_err, float(fit_period))
        if fit.get("ok"):
            fit["period_days"] = float(fit_period)
            fit["period_source"] = "published" if known_period_days else "periodogram peak"
            if stellar_mass_sun and np.isfinite(stellar_mass_sun):
                msini = round(
                    planet_mass_from_k(fit["semi_amplitude_ms"], float(fit_period),
                                       float(stellar_mass_sun)), 4)
                if fit.get("reliable"):
                    fit["msini_earth"] = msini
                    fit["msini_note"] = (
                        "Minimum mass only; the true mass is M/sin(i) >= this value."
                    )
                else:
                    # Do not publish a mass derived from an amplitude the data
                    # cannot support. Keep it under a name no consumer will
                    # mistake for a result.
                    fit["msini_earth"] = None
                    fit["msini_earth_if_fit_were_reliable"] = msini
                    fit["msini_note"] = (
                        "No mass is reported: the amplitude fit failed its reliability "
                        "checks, so any mass derived from it would be meaningless."
                    )

            # Does the fitted period coincide with a flagged activity signal?
            fit["period_matches_activity_indicator"] = any(
                abs(c["rv_period_days"] - float(fit_period)) / float(fit_period)
                <= activity_match_tolerance
                for c in coincidences
            )
            # Phase-folded curve for display.
            phase = (ds.time % fit_period) / fit_period
            order = np.argsort(phase)
            step = max(1, len(order) // 800)
            fit["folded"] = {
                "phase": [round(float(x), 5) for x in phase[order][::step]],
                "rv_ms": [round(float(x), 4) for x in rv_corrected[order][::step]],
                "rv_err_ms": [round(float(x), 4) for x in ds.rv_err[order][::step]],
            }
        out["keplerian_fit"] = fit

    out["status"] = "ok"
    return out
