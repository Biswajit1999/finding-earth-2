"""Transit photometry: retrieval, detrending, folding, fitting."""

from __future__ import annotations

from earth2.transit.lightcurve import (
    LightCurveResult,
    TransitFit,
    analyse_target,
    bls_period_search,
    clip_upward_outliers,
    detrend,
    fit_trapezoid,
    fold_on_ephemeris,
    load_light_curve,
    search_products,
)
from earth2.transit.validation import VALIDATION_TARGETS, run_validation, write_validation

__all__ = [
    "LightCurveResult", "TransitFit", "analyse_target", "bls_period_search",
    "clip_upward_outliers", "detrend", "fit_trapezoid", "fold_on_ephemeris",
    "load_light_curve", "search_products",
    "VALIDATION_TARGETS", "run_validation", "write_validation",
]
