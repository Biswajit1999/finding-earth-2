"""Repository paths and pipeline-wide configuration.

Everything that touches the filesystem resolves through here, so that the whole
pipeline can be relocated (CI, container, a different checkout) by setting
``EARTH2_ROOT`` rather than by editing code.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Root resolution
# --------------------------------------------------------------------------
# src/earth2/config.py -> src/earth2 -> src -> <repo root>
_PACKAGE_DIR = Path(__file__).resolve().parent
_INFERRED_ROOT = _PACKAGE_DIR.parent.parent

ROOT = Path(os.environ.get("EARTH2_ROOT", _INFERRED_ROOT)).resolve()

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MANIFEST_DIR = DATA_DIR / "manifests"
SAMPLES_DIR = DATA_DIR / "samples"
PRODUCTS_DIR = DATA_DIR / "products"

RESULTS_DIR = ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
DOCS_DIR = ROOT / "docs"
REFERENCES_DIR = ROOT / "references"
WEB_DIR = ROOT / "web"
WEB_DATA_DIR = WEB_DIR / "public" / "data"

_ALL_DIRS = (
    DATA_DIR, RAW_DIR, PROCESSED_DIR, MANIFEST_DIR, SAMPLES_DIR, PRODUCTS_DIR,
    RESULTS_DIR, FIGURES_DIR, WEB_DATA_DIR,
)


def ensure_dirs() -> None:
    """Create every directory the pipeline writes into. Idempotent."""
    for d in _ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------------
# Single global seed. Every stochastic stage (Monte Carlo propagation, anomaly
# detection subsampling) derives its generator from this via
# ``numpy.random.default_rng(RANDOM_SEED + offset)`` so that stages are
# independently reproducible but do not share a stream.
RANDOM_SEED = 20260824

#: Monte Carlo draws per planet for uncertainty propagation.
#: 4000 keeps the 16th/84th percentiles stable to <0.5% between reruns while
#: leaving a full-catalogue run inside a couple of minutes.
N_MONTE_CARLO = int(os.environ.get("EARTH2_N_MC", "4000"))

# --------------------------------------------------------------------------
# Network behaviour
# --------------------------------------------------------------------------
HTTP_TIMEOUT = int(os.environ.get("EARTH2_HTTP_TIMEOUT", "300"))
HTTP_RETRIES = int(os.environ.get("EARTH2_HTTP_RETRIES", "4"))
HTTP_BACKOFF = float(os.environ.get("EARTH2_HTTP_BACKOFF", "2.0"))
from earth2 import __version__ as _EARTH2_VERSION  # noqa: E402

USER_AGENT = f"earth2/{_EARTH2_VERSION} (finding-earth-2; reproducible exoplanet habitability pipeline)"

#: Skip a re-download when the cached raw payload is younger than this.
CACHE_MAX_AGE_HOURS = float(os.environ.get("EARTH2_CACHE_HOURS", "24"))
