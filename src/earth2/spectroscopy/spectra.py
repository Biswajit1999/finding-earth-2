"""Atmospheric spectroscopy: assembling and annotating published spectra.

What this module works with
---------------------------
The NASA Exoplanet Archive's ``transitspec`` and ``emissionspec`` tables hold
published, per-bandpass measurements of **planetary atmospheres**:

* transmission -- transit depth as a function of wavelength, from starlight
  filtered through the planet's limb during transit;
* emission -- secondary-eclipse depth, i.e. the planet's own thermal emission.

This is emphatically **not** the same thing as a high-resolution stellar
spectrum. A stellar spectrum measures the star; it constrains the host, and it
is what radial-velocity and stellar-activity work is built on, but it carries no
direct information about a planet's atmosphere. The project keeps the two in
separate tables, separate counts, and separate parts of the interface, and never
adds them together to inflate a total.

The unit problem
----------------
The archive reports the same physical quantity two different ways depending on
what the source paper published:

* ``plntransdep`` -- transit depth as a **percentage**  (63% of rows)
* ``plnratror``   -- planet-to-star **radius ratio** Rp/R*  (37% of rows)

They are related by ``depth = (Rp/R*)^2``. A spectrum assembled from only one
column silently drops a third to two-thirds of its points -- for WASP-39 b,
every one of its 1,625 measurements is stored as a radius ratio, so reading
``plntransdep`` alone yields an empty spectrum for the best-observed planet in
the table. :func:`harmonise_transit_depths` converts both to parts per million
and records which column each point came from.

Language discipline
-------------------
A feature near a molecular band is **not** a detection. This module annotates
*expected band positions* so a reader can see where a species would absorb, and
labels them as such. It never asserts that a molecule is present. Claims of
detection belong to the peer-reviewed analyses cited alongside each spectrum,
not to a band overlay drawn by this code.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

__all__ = [
    "MOLECULAR_BANDS",
    "atmospheric_scale_height_km",
    "bands_in_range",
    "harmonise_transit_depths",
    "planet_spectrum",
    "spectrum_inventory",
    "transmission_signal_ppm",
]

#: Approximate central wavelengths (microns) of absorption bands relevant to
#: exoplanet atmospheres, with the width over which the band is usually
#: discussed. Positions are indicative band centres for annotation only; real
#: band structure is temperature-, pressure- and resolution-dependent.
#:
#: Compiled from standard exoplanet-atmosphere references, principally
#: Madhusudhan, N. (2019), *Exoplanetary Atmospheres: Key Insights, Challenges,
#: and Prospects*, Annual Review of Astronomy and Astrophysics 57, 617,
#: doi:10.1146/annurev-astro-081817-051846
#:
#: ``biosignature_relevance`` records why a species is discussed in a
#: biosignature context. It is NOT a claim that the species indicates life --
#: see :mod:`earth2.spectroscopy.biosignature`.
MOLECULAR_BANDS: dict[str, dict[str, Any]] = {
    "H2O": {
        "label": "Water",
        "bands_um": [0.94, 1.13, 1.40, 1.90, 2.70, 6.20],
        "colour_role": "primary",
        "biosignature_relevance": (
            "Indicates volatiles and is required for surface liquid water, but water "
            "vapour is abundant in hot gas giants and is not itself a biosignature."
        ),
    },
    "CO2": {
        "label": "Carbon dioxide",
        "bands_um": [1.60, 2.00, 2.70, 4.30, 15.0],
        "colour_role": "primary",
        "biosignature_relevance": (
            "Confirms an atmosphere exists and constrains its mean molecular weight. "
            "Abiotic and abundant on Venus and Mars."
        ),
    },
    "CH4": {
        "label": "Methane",
        "bands_um": [1.15, 1.40, 1.70, 2.30, 3.30, 7.70],
        "colour_role": "primary",
        "biosignature_relevance": (
            "Biologically produced on Earth, but also outgassed abiotically by "
            "serpentinisation and volcanism. Interesting mainly in DISEQUILIBRIUM with "
            "O2, not on its own."
        ),
    },
    "CO": {
        "label": "Carbon monoxide",
        "bands_um": [2.30, 4.60],
        "colour_role": "secondary",
        "biosignature_relevance": (
            "Generally an anti-biosignature: abundant CO alongside O2 suggests "
            "photochemical rather than biological oxygen production."
        ),
    },
    "O2": {
        "label": "Molecular oxygen",
        "bands_um": [0.69, 0.76, 1.27],
        "colour_role": "biosignature_context",
        "biosignature_relevance": (
            "Earth's dominant biosignature gas, but with well-documented abiotic "
            "production routes -- photolysis of water with hydrogen escape, and CO2 "
            "photolysis around M dwarfs. Not diagnostic in isolation."
        ),
    },
    "O3": {
        "label": "Ozone",
        "bands_um": [0.60, 9.60],
        "colour_role": "biosignature_context",
        "biosignature_relevance": (
            "A photochemical proxy for O2 detectable at lower abundance, inheriting "
            "every abiotic-oxygen ambiguity that O2 has."
        ),
    },
    "NH3": {
        "label": "Ammonia",
        "bands_um": [1.50, 2.00, 10.5],
        "colour_role": "secondary",
        "biosignature_relevance": "Disequilibrium species in some atmospheric contexts.",
    },
    "SO2": {
        "label": "Sulphur dioxide",
        "bands_um": [4.00, 7.30, 8.70],
        "colour_role": "secondary",
        "biosignature_relevance": (
            "Volcanic and photochemical. Its JWST detection in WASP-39 b is evidence "
            "of photochemistry, not of biology."
        ),
    },
    "Na": {
        "label": "Sodium",
        "bands_um": [0.589],
        "colour_role": "secondary",
        "biosignature_relevance": "Alkali resonance line; a classic hot-Jupiter atmospheric probe.",
    },
    "K": {
        "label": "Potassium",
        "bands_um": [0.767],
        "colour_role": "secondary",
        "biosignature_relevance": "Alkali resonance line; a classic hot-Jupiter atmospheric probe.",
    },
}


def bands_in_range(wl_min: float, wl_max: float) -> list[dict[str, Any]]:
    """Expected molecular bands falling inside a wavelength window.

    Returned for annotation only. The presence of a band position inside a
    spectrum's coverage says nothing about whether the species was detected.
    """
    out: list[dict[str, Any]] = []
    for species, info in MOLECULAR_BANDS.items():
        hits = [b for b in info["bands_um"] if wl_min <= b <= wl_max]
        if hits:
            out.append({
                "species": species,
                "label": info["label"],
                "bands_um": hits,
                "colour_role": info["colour_role"],
                "biosignature_relevance": info["biosignature_relevance"],
                "status": "expected_band_position",
            })
    return out


def harmonise_transit_depths(ts: pd.DataFrame) -> pd.DataFrame:
    """Convert both depth representations to parts per million.

    ``plntransdep`` is a percentage; ``plnratror`` is Rp/R*. Since
    ``depth = (Rp/R*)^2``::

        depth_ppm = plntransdep [%] * 1e4
        depth_ppm = plnratror^2 * 1e6

    Uncertainties are propagated for the radius-ratio branch by the standard
    first-order rule ``sigma_depth = 2 * (Rp/R*) * sigma_ratio``, in the same
    ppm units.

    Adds ``depth_ppm``, ``depth_ppm_err``, and ``depth_source`` recording which
    column supplied each point.
    """
    df = ts.copy()

    def col(name: str) -> pd.Series:
        # df.get(name) returns a bare None -- not a Series -- for a column
        # that is absent entirely, and pd.to_numeric(None, errors="coerce")
        # silently returns a scalar NaN rather than a Series, which crashes
        # the moment a caller chains .abs()/.notna()/.where() onto it. The
        # full pipeline's transitspec/emissionspec tables always carry every
        # column referenced below (even if all-NaN), so this is latent in
        # production, but not for a partial DataFrame such as a test fixture
        # or a trimmed-down notebook table.
        if name in df.columns:
            return pd.to_numeric(df[name], errors="coerce")
        return pd.Series(np.nan, index=df.index, dtype=float)

    dep_pct = col("plntransdep")
    dep_e1 = col("plntransdeperr1").abs()
    dep_e2 = col("plntransdeperr2").abs()

    ror = col("plnratror")
    ror_e1 = col("plnratrorerr1").abs()
    ror_e2 = col("plnratrorerr2").abs()

    depth_from_pct = dep_pct * 1e4
    err_from_pct = pd.concat([dep_e1, dep_e2], axis=1).mean(axis=1) * 1e4

    with np.errstate(invalid="ignore"):
        depth_from_ror = (ror**2) * 1e6
        ror_err = pd.concat([ror_e1, ror_e2], axis=1).mean(axis=1)
        err_from_ror = 2.0 * ror * ror_err * 1e6

    use_pct = depth_from_pct.notna()
    df["depth_ppm"] = depth_from_pct.where(use_pct, depth_from_ror)
    df["depth_ppm_err"] = err_from_pct.where(use_pct, err_from_ror)
    df["depth_source"] = np.where(
        use_pct, "plntransdep_percent",
        np.where(depth_from_ror.notna(), "plnratror_squared", "missing"),
    )
    df["wavelength_um"] = col("centralwavelng")
    df["bandwidth_um"] = col("bandwidth")
    return df


def atmospheric_scale_height_km(
    teq_k: float,
    mass_earth: float,
    radius_earth: float,
    mean_molecular_weight_amu: float = 2.3,
) -> float:
    """Atmospheric pressure scale height, km.

    ``H = k T / (mu m_H g)``

    The default mean molecular weight of 2.3 amu is the usual hydrogen-helium
    value used for gas-dominated atmospheres. For a secondary atmosphere
    (N2/CO2, like Earth's 29 or Venus's 43) the scale height -- and therefore the
    transmission signal -- is roughly an order of magnitude smaller. Passing the
    H/He default for a terrestrial planet overestimates its observability by
    about that factor, so the value used must always be stated.
    """
    k_b = 1.380649e-23
    m_h = 1.67262192e-27
    g_earth = 9.80665

    if not all(np.isfinite([teq_k, mass_earth, radius_earth])) or radius_earth <= 0:
        return float("nan")
    g = g_earth * mass_earth / (radius_earth**2)
    if g <= 0:
        return float("nan")
    h_m = (k_b * teq_k) / (mean_molecular_weight_amu * m_h * g)
    return h_m / 1000.0


def transmission_signal_ppm(
    radius_earth: float,
    stellar_radius_sun: float,
    scale_height_km: float,
    n_scale_heights: float = 5.0,
) -> float:
    """Expected transmission-spectrum amplitude, ppm.

    The annulus of atmosphere probed during transit changes the effective planet
    radius by roughly ``n_scale_heights * H``::

        signal = 2 * n * H * R_p / R_star^2

    Five scale heights is the conventional estimate for the observable extent of
    a transmission feature.
    """
    r_earth_km = 6371.0
    r_sun_km = 695700.0
    if not all(np.isfinite([radius_earth, stellar_radius_sun, scale_height_km])):
        return float("nan")
    if stellar_radius_sun <= 0:
        return float("nan")
    rp_km = radius_earth * r_earth_km
    rs_km = stellar_radius_sun * r_sun_km
    return 2.0 * n_scale_heights * scale_height_km * rp_km / (rs_km**2) * 1e6


def planet_spectrum(
    ts: pd.DataFrame,
    planet: str,
    min_points: int = 1,
) -> dict[str, Any] | None:
    """Assemble one planet's transmission spectrum, sorted by wavelength.

    Returns ``None`` when the planet has no usable points, rather than an empty
    structure that a caller might render as a flat line.
    """
    df = harmonise_transit_depths(ts)
    sub = df[df["plntname"].astype(str) == planet].copy()
    sub = sub[sub["wavelength_um"].notna() & sub["depth_ppm"].notna()]
    if len(sub) < max(1, min_points):
        return None
    sub = sub.sort_values("wavelength_um")

    wl_min = float(sub["wavelength_um"].min())
    wl_max = float(sub["wavelength_um"].max())

    facilities = sorted({str(x) for x in sub.get("facility", pd.Series(dtype=object)).dropna()})
    instruments = sorted({str(x) for x in sub.get("instrument", pd.Series(dtype=object)).dropna()})

    return {
        "planet": planet,
        "kind": "transmission",
        "n_points": int(len(sub)),
        "wavelength_range_um": [wl_min, wl_max],
        "facilities": facilities,
        "instruments": instruments,
        "depth_sources": {
            str(k): int(v) for k, v in sub["depth_source"].value_counts().items()
        },
        "expected_bands": bands_in_range(wl_min, wl_max),
        "points": [
            {
                "wavelength_um": round(float(r["wavelength_um"]), 5),
                "bandwidth_um": (None if not np.isfinite(r["bandwidth_um"])
                                 else round(float(r["bandwidth_um"]), 5)),
                "depth_ppm": round(float(r["depth_ppm"]), 2),
                "depth_ppm_err": (None if not np.isfinite(r["depth_ppm_err"])
                                  else round(float(r["depth_ppm_err"]), 2)),
                "source": str(r["depth_source"]),
                "facility": (None if pd.isna(r.get("facility")) else str(r.get("facility"))),
                "instrument": (None if pd.isna(r.get("instrument")) else str(r.get("instrument"))),
            }
            for _, r in sub.iterrows()
        ],
        "caveat": (
            "Annotated band positions mark where a species would absorb. They are not "
            "detections. Detection claims belong to the cited analyses."
        ),
    }


def spectrum_inventory(
    ts: pd.DataFrame | None = None,
    es: pd.DataFrame | None = None,
    min_points: int = 4,
) -> pd.DataFrame:
    """Which planets have usable published atmospheric spectra, and how much.

    Counts only points that survive harmonisation into a usable depth, so the
    inventory reflects what can actually be plotted rather than raw row counts.
    """
    rows: list[dict[str, Any]] = []

    if ts is not None and not ts.empty:
        h = harmonise_transit_depths(ts)
        h = h[h["wavelength_um"].notna() & h["depth_ppm"].notna()]
        g = h.groupby("plntname")
        for name, sub in g:
            rows.append({
                "pl_name": str(name),
                "kind": "transmission",
                "n_points": int(len(sub)),
                "wl_min_um": float(sub["wavelength_um"].min()),
                "wl_max_um": float(sub["wavelength_um"].max()),
                "n_facilities": int(sub["facility"].nunique()) if "facility" in sub else 0,
                "facilities": ", ".join(sorted({str(x) for x in sub.get("facility", pd.Series(dtype=object)).dropna()})[:4]),
            })

    if es is not None and not es.empty and "plntname" in es.columns:
        e = es.copy()
        e["depth_ppm"] = pd.to_numeric(e.get("especlipdep"), errors="coerce")
        e["wavelength_um"] = pd.to_numeric(e.get("centralwavelng"), errors="coerce")
        e = e[e["wavelength_um"].notna() & e["depth_ppm"].notna()]
        for name, sub in e.groupby("plntname"):
            rows.append({
                "pl_name": str(name),
                "kind": "emission",
                "n_points": int(len(sub)),
                "wl_min_um": float(sub["wavelength_um"].min()),
                "wl_max_um": float(sub["wavelength_um"].max()),
                "n_facilities": int(sub["facility"].nunique()) if "facility" in sub else 0,
                "facilities": ", ".join(sorted({str(x) for x in sub.get("facility", pd.Series(dtype=object)).dropna()})[:4]),
            })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out[out["n_points"] >= min_points].sort_values(
        ["n_points"], ascending=False
    ).reset_index(drop=True)
