"""Monte Carlo propagation of catalogue parameter uncertainties.

Why this stage exists
---------------------
Ranking planets on nominal catalogue values pretends every number is exact. It
is not. A planet whose radius is 1.0 +/- 0.1 Earth radii and one whose radius is
1.0 +/- 0.6 are not equally Earth-sized, and a ranking that cannot tell them
apart is not measuring anything useful.

Every parameter with a reported uncertainty is therefore sampled, the derived
quantities are recomputed for every draw, and the *distribution* of each derived
quantity is reported rather than a single number.

The asymmetric-error problem
----------------------------
The archive reports separate upper (``err1``) and lower (``err2``) uncertainties,
and they are frequently very different -- a mass of 1.2 (+0.9, -0.4) is common.
Collapsing those to a symmetric sigma throws away real information about which
direction the measurement is better constrained in.

This module samples from a **two-piece (split) normal**: draw z ~ N(0,1), scale
by the upper sigma when z > 0 and by the lower sigma when z < 0. The result is
continuous, has the right mode, and reproduces each reported error bar on its own
side. It is the standard pragmatic choice for asymmetric catalogue errors and is
recorded as an assumption rather than presented as truth.

Physical constraints
--------------------
Radii, masses, temperatures and luminosities are positive. A wide error bar on a
small value can push a naive Gaussian draw negative. Such draws are rejected and
redrawn (bounded number of attempts), rather than clipped to zero, because
clipping piles probability mass on an unphysical boundary and biases the median.

Missing uncertainties -- an honest compromise
---------------------------------------------
Many catalogue entries carry a value but no uncertainty. There are two dishonest
options: invent an error bar, or drop the planet. This module does neither. It
samples such a parameter as a delta function at its nominal value and increments
``n_params_without_uncertainty`` for that planet.

The consequence -- an artificially *narrow* posterior -- is therefore visible in
the output and is penalised explicitly by the observational-confidence score in
:mod:`earth2.ranking`. A planet that looks precisely Earth-like only because
nobody published error bars must not outrank one that is genuinely well measured.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from earth2.config import N_MONTE_CARLO, RANDOM_SEED
from earth2.constants import BOND_ALBEDO_EARTH, RHO_EARTH_G_CM3, V_ESC_EARTH_KMS
from earth2.habitability import esi as esi_mod
from earth2.habitability import hz as hz_mod

__all__ = [
    "MonteCarloResult",
    "propagate_catalogue",
    "sample_split_normal",
    "summarise_samples",
]

#: Parameters propagated, mapped to whether they must stay strictly positive.
MC_PARAMETERS: dict[str, bool] = {
    "pl_rade": True,
    "pl_bmasse": True,
    "st_teff": True,
    "st_lum": False,     # log10 luminosity; may legitimately be negative
    "pl_orbsmax": True,
    "pl_insol": True,
}


def sample_split_normal(
    value: np.ndarray,
    err_up: np.ndarray,
    err_lo: np.ndarray,
    n_samples: int,
    rng: np.random.Generator,
    positive: bool = True,
    max_redraws: int = 8,
) -> np.ndarray:
    """Draw from a two-piece normal for each element of ``value``.

    Parameters
    ----------
    value
        Nominal values, shape ``(n,)``. NaN propagates as an all-NaN row.
    err_up, err_lo
        Upper and lower 1-sigma uncertainties, shape ``(n,)``, both given as
        positive magnitudes. NaN or zero yields a delta function at ``value``.
    n_samples
        Draws per element.
    positive
        Reject and redraw non-positive samples.

    Returns
    -------
    numpy.ndarray
        Shape ``(n, n_samples)``.
    """
    v = np.asarray(value, dtype=float).reshape(-1, 1)
    su = np.abs(np.asarray(err_up, dtype=float)).reshape(-1, 1)
    sl = np.abs(np.asarray(err_lo, dtype=float)).reshape(-1, 1)

    su = np.where(np.isfinite(su), su, 0.0)
    sl = np.where(np.isfinite(sl), sl, 0.0)

    z = rng.standard_normal(size=(v.shape[0], n_samples))
    sigma = np.where(z > 0, su, sl)
    out = v + z * sigma

    if positive:
        for _ in range(max_redraws):
            bad = np.isfinite(out) & (out <= 0)
            if not bad.any():
                break
            z_new = rng.standard_normal(size=out.shape)
            sigma_new = np.where(z_new > 0, su, sl)
            candidate = v + z_new * sigma_new
            out = np.where(bad, candidate, out)
        # Any sample still non-positive after the redraw budget is discarded
        # (NaN), not clipped -- clipping would pile mass on zero and bias the
        # median upward for poorly constrained small planets.
        out = np.where(np.isfinite(out) & (out <= 0), np.nan, out)

    return np.where(np.isfinite(v), out, np.nan)


@dataclass
class MonteCarloResult:
    """Per-planet summary statistics of the propagated distributions."""

    frame: pd.DataFrame
    n_samples: int
    seed: int
    parameters: list[str] = field(default_factory=list)


def _percentiles(a: np.ndarray, qs: Sequence[float]) -> dict[float, np.ndarray]:
    """Row-wise percentiles ignoring NaN, without warning on all-NaN rows."""
    out: dict[float, np.ndarray] = {}
    allnan = np.all(~np.isfinite(a), axis=1)
    safe = np.where(np.isfinite(a), a, np.nan)
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="All-NaN slice encountered")
        for q in qs:
            vals = np.full(a.shape[0], np.nan)
            if (~allnan).any():
                vals[~allnan] = np.nanpercentile(safe[~allnan], q, axis=1)
            out[q] = vals
    return out


def _chunk_indices(n: int, size: int) -> Iterable[tuple[int, int]]:
    for start in range(0, n, size):
        yield start, min(start + size, n)


def propagate_catalogue(
    catalogue: pd.DataFrame,
    n_samples: int = N_MONTE_CARLO,
    seed: int = RANDOM_SEED,
    albedo: float = BOND_ALBEDO_EARTH,
    chunk_size: int = 400,
) -> MonteCarloResult:
    """Propagate parameter uncertainties through every derived quantity.

    Derived per draw: bulk density, escape velocity, incident flux, equilibrium
    temperature, the four ESI terms, the global ESI, and habitable-zone
    membership under both the conservative and optimistic definitions.

    Returns median and 16th/84th percentiles for the continuous quantities and a
    *probability* for each habitable-zone membership -- the fraction of draws in
    which the planet falls inside the zone. A planet sitting on a zone boundary
    correctly reports ~0.5 rather than a spurious yes or no.
    """
    df = catalogue.reset_index(drop=True)
    n = len(df)
    rng = np.random.default_rng(seed)

    def col(name: str) -> np.ndarray:
        if name in df.columns:
            return pd.to_numeric(df[name], errors="coerce").to_numpy(dtype=float)
        return np.full(n, np.nan)

    # Count how many of the propagated parameters lack a usable uncertainty.
    missing_unc = np.zeros(n, dtype=int)
    present = np.zeros(n, dtype=int)
    for p in MC_PARAMETERS:
        v = col(p)
        e1 = np.abs(col(p + "err1"))
        e2 = np.abs(col(p + "err2"))
        has_v = np.isfinite(v)
        has_e = (np.isfinite(e1) & (e1 > 0)) | (np.isfinite(e2) & (e2 > 0))
        present += has_v.astype(int)
        missing_unc += (has_v & ~has_e).astype(int)

    results: dict[str, np.ndarray] = {
        k: np.full(n, np.nan)
        for k in (
            "esi_global_p16", "esi_global_p50", "esi_global_p84",
            "pl_rade_p16", "pl_rade_p50", "pl_rade_p84",
            "pl_bmasse_p16", "pl_bmasse_p50", "pl_bmasse_p84",
            "pl_dens_p16", "pl_dens_p50", "pl_dens_p84",
            "teq_p16", "teq_p50", "teq_p84",
            "insol_p16", "insol_p50", "insol_p84",
            "hz_conservative_prob", "hz_optimistic_prob",
            "hz_teff_valid_fraction",
            "esi_global_width",
        )
    }

    for lo, hi in _chunk_indices(n, chunk_size):
        sl = slice(lo, hi)
        m = hi - lo

        rade = sample_split_normal(col("pl_rade")[sl], col("pl_radeerr1")[sl],
                                   col("pl_radeerr2")[sl], n_samples, rng, positive=True)
        mass = sample_split_normal(col("pl_bmasse")[sl], col("pl_bmasseerr1")[sl],
                                   col("pl_bmasseerr2")[sl], n_samples, rng, positive=True)
        teff = sample_split_normal(col("st_teff")[sl], col("st_tefferr1")[sl],
                                   col("st_tefferr2")[sl], n_samples, rng, positive=True)
        lum = sample_split_normal(col("st_lum")[sl], col("st_lumerr1")[sl],
                                  col("st_lumerr2")[sl], n_samples, rng, positive=False)
        smax = sample_split_normal(col("pl_orbsmax")[sl], col("pl_orbsmaxerr1")[sl],
                                   col("pl_orbsmaxerr2")[sl], n_samples, rng, positive=True)
        insol_cat = sample_split_normal(col("pl_insol")[sl], col("pl_insolerr1")[sl],
                                        col("pl_insolerr2")[sl], n_samples, rng, positive=True)

        # Flux: catalogue draw where available, else derived from L and a.
        with np.errstate(invalid="ignore", divide="ignore"):
            insol_der = (10.0**lum) / (smax**2)
        insol = np.where(np.isfinite(insol_cat), insol_cat, insol_der)
        insol = np.where(np.isfinite(insol) & (insol > 0), insol, np.nan)

        with np.errstate(invalid="ignore", divide="ignore"):
            teq = 278.5 * (insol**0.25) * ((1.0 - albedo) ** 0.25)
            dens = RHO_EARTH_G_CM3 * mass / (rade**3)
            vesc = V_ESC_EARTH_KMS * np.sqrt(mass / rade)

        comps = esi_mod.esi_global(rade, dens, vesc, teq)
        esi_g = comps["esi_global"]

        # Habitable-zone membership per draw -> probability.
        teff_flat = teff.reshape(-1)
        insol_flat = insol.reshape(-1)
        cons = hz_mod.in_conservative_hz(insol_flat, teff_flat).reshape(m, n_samples)
        opt = hz_mod.in_optimistic_hz(insol_flat, teff_flat).reshape(m, n_samples)

        # A planet whose flux or host temperature is unknown yields an all-NaN
        # row here; that is "unknown", not "outside the zone", so the mean is
        # left as NaN rather than warned about.
        #
        # IMPORTANT: these probabilities are CONDITIONAL on the draw falling
        # inside the habitable-zone model's 2600-7200 K validity range, because
        # out-of-range draws return NaN and nanmean skips them. For a host near
        # a validity edge that conditioning is severe -- TRAPPIST-1 at 2566 K
        # has only a small fraction of draws in range, yet would report a
        # confident-looking probability computed from just those.
        #
        # hz_teff_valid_fraction records what fraction of draws the model
        # actually applied to, so the conditioning is always visible next to the
        # probability instead of being buried.
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Mean of empty slice")
            results["hz_conservative_prob"][sl] = np.nanmean(
                np.where(np.isfinite(cons), cons, np.nan), axis=1)
            results["hz_optimistic_prob"][sl] = np.nanmean(
                np.where(np.isfinite(opt), opt, np.nan), axis=1)

        in_range = (
            np.isfinite(teff)
            & (teff >= hz_mod.HZ_TEFF_MIN)
            & (teff <= hz_mod.HZ_TEFF_MAX)
        )
        results["hz_teff_valid_fraction"][sl] = in_range.mean(axis=1)

        for key, arr in (
            ("esi_global", esi_g), ("pl_rade", rade), ("pl_bmasse", mass),
            ("pl_dens", dens), ("teq", teq), ("insol", insol),
        ):
            pct = _percentiles(arr, (16, 50, 84))
            results[key + "_p16"][sl] = pct[16]
            results[key + "_p50"][sl] = pct[50]
            results[key + "_p84"][sl] = pct[84]

        results["esi_global_width"][sl] = (
            results["esi_global_p84"][sl] - results["esi_global_p16"][sl]
        )

    out = pd.DataFrame(results)
    out["mc_params_present"] = present
    out["mc_params_without_uncertainty"] = missing_unc
    with np.errstate(invalid="ignore", divide="ignore"):
        out["mc_uncertainty_coverage"] = np.where(
            present > 0, 1.0 - missing_unc / np.maximum(present, 1), np.nan
        )
    out["pl_name"] = df["pl_name"].values if "pl_name" in df.columns else np.arange(n)

    return MonteCarloResult(
        frame=out, n_samples=n_samples, seed=seed, parameters=list(MC_PARAMETERS)
    )


def summarise_samples(result: MonteCarloResult) -> dict[str, float]:
    """Headline diagnostics for the propagation run."""
    f = result.frame
    return {
        "n_planets": int(len(f)),
        "n_samples": int(result.n_samples),
        "seed": int(result.seed),
        "n_with_esi_posterior": int(f["esi_global_p50"].notna().sum()),
        "median_esi_width": float(f["esi_global_width"].median(skipna=True)),
        "n_hz_conservative_prob_gt_0p5": int((f["hz_conservative_prob"] > 0.5).sum()),
        "n_hz_conservative_prob_gt_0p9": int((f["hz_conservative_prob"] > 0.9).sum()),
        "mean_uncertainty_coverage": float(f["mc_uncertainty_coverage"].mean(skipna=True)),
    }
