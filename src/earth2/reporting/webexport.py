"""Export browser-ready data products.

The frontend contract
---------------------
The scientific pipeline is Python. The website consumes what that pipeline
*produced*; it never recomputes any of it in JavaScript::

    archives -> Python pipeline -> validated Parquet -> web export -> JSON -> React

There is one reason for this rule, and it is not architectural tidiness. If the
habitable-zone boundaries or the Earth Similarity Index were reimplemented in
TypeScript for the interface, there would be two implementations of the science
that could silently disagree, and the tested one would not be the one the reader
sees. The only computation the browser performs is **re-weighting the composite
index**, because that is an interactive control whose inputs -- the four
component scores -- were themselves computed in Python.

Format choices
--------------
The full catalogue ships **columnar** (one array per field) rather than as an
array of objects. For 6,354 planets across ~25 fields, repeating every key name
6,354 times costs roughly 4x the payload. Columnar plus gzip brings the whole
catalogue to a few hundred kilobytes, which is what makes an instant client-side
filter over the entire dataset viable.

Numbers are rounded at export. A radius is not known to 15 significant figures,
and shipping the float64 repr is both dishonest about precision and wasteful.
"""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import Galactocentric, SkyCoord

from earth2 import __version__
from earth2.provenance import ManifestStore, utc_now_iso
from earth2.reporting.jsonio import dump_json

__all__ = [
    "export_all",
    "export_catalogue_columnar",
    "export_galaxy",
    "export_universe",
    "write_json",
]

#: Sun's distance from the Galactic Centre. GRAVITY Collaboration (2019),
#: A&A 625, L10 -- measured from stellar orbits around Sgr A*, not assumed.
GALCEN_DISTANCE_KPC = 8.178
#: Sun's height above the Galactic midplane. Bennett & Bovy (2019),
#: MNRAS 482, 1417.
SUN_HEIGHT_PC = 20.8

#: Same grouping the frontend filter UI uses (web/components/universe/
#: UniverseExplorer.tsx's NAMED_METHODS) -- kept in sync by hand since one
#: is Python and the other TypeScript; every other discovery method groups
#: into "Other".
NAMED_METHODS = ("Transit", "Radial Velocity", "Microlensing", "Imaging", "Transit Timing Variations")


def write_json(obj: Any, path: Path, gzip_also: bool = True, indent: int | None = None) -> Path:
    """Write JSON, and a .gz sibling for static hosts that can serve it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # dump_json converts non-finite floats to null and then refuses to emit any
    # that slipped through. Bare NaN is a Python extension, not valid JSON, and
    # JSON.parse rejects it -- see earth2.reporting.jsonio.
    text = dump_json(obj, compact=True) if indent is None else dump_json(obj, indent=indent)
    path.write_text(text, encoding="utf-8")
    if gzip_also:
        with gzip.open(str(path) + ".gz", "wt", encoding="utf-8", compresslevel=9) as fh:
            fh.write(text)
    return path


def _col(df: pd.DataFrame, name: str, nd: int | None = None) -> list[Any]:
    """One column as a JSON-safe list, NaN -> None, rounded."""
    if name not in df.columns:
        return [None] * len(df)
    s = df[name]
    if nd is not None:
        s = pd.to_numeric(s, errors="coerce").round(nd)
        return [None if not np.isfinite(v) else (int(v) if nd == 0 else float(v))
                for v in s.to_numpy(dtype=float)]
    out: list[Any] = []
    for v in s:
        if v is None:
            out.append(None)
            continue
        try:
            if pd.isna(v):
                out.append(None)
                continue
        except (TypeError, ValueError):
            pass
        out.append(str(v) if not isinstance(v, (int, float, bool, np.bool_)) else v)
    return out


#: Catalogue fields shipped to the browser, with rounding precision.
#: `None` means "string field".
CATALOGUE_FIELDS: dict[str, int | None] = {
    "pl_name": None, "hostname": None,
    "earth2_index": 4, "earth2_rank": 0,
    "score_earth_similarity": 4, "score_conservative_habitability": 4,
    "score_observational_confidence": 4, "score_characterisation_potential": 4,
    "esi_global_p50": 4, "esi_global_p16": 4, "esi_global_p84": 4,
    "hz_conservative_prob": 4, "hz_optimistic_prob": 4,
    "hz_conservative": 0, "hz_optimistic": 0, "hz_model_extrapolated": None,
    "rocky_plausibility": 4,
    "pl_rade": 4, "pl_rade_p16": 4, "pl_rade_p84": 4,
    "pl_bmasse": 4, "mass_class": None,
    "pl_dens_used": 4, "pl_orbper": 5, "pl_orbsmax": 5, "pl_orbeccen": 4,
    "insol_used": 4, "teq_used": 1,
    "st_teff": 0, "st_rad": 4, "st_mass": 4, "st_lum": 4, "st_spectype": None,
    "sy_dist": 3, "ra": 5, "dec": 5,
    "sy_vmag": 3, "sy_jmag": 3, "sy_kmag": 3,
    "discoverymethod": None, "disc_year": 0, "disc_facility": None,
    "tran_flag": 0, "rv_flag": 0, "ttv_flag": 0,
    "n_references": 0, "mc_uncertainty_coverage": 4,
    "composite_parameter_source_count": 0,
    "composite_uses_mixed_sources": None,
    "default_solution_parameter_coverage": 4,
    "composite_default_median_fractional_difference": 4,
    "n_transmission_points": 0, "n_emission_points": 0,
    "tsm": 3, "esm": 3, "rv_semi_amplitude_ms": 4,
    "ephemeris_uncertainty_2030_minutes": 2,
    "max_angular_separation_mas": 3,
    "reflected_light_contrast_ag0p3": 14,
    "is_control": None, "rankable": None,
}


def export_catalogue_columnar(ranking: pd.DataFrame) -> dict[str, Any]:
    """The full analysed catalogue in columnar form."""
    df = ranking.copy()
    # Stable order: best first, controls last so they never head a default sort.
    df = df.sort_values(["is_control", "earth2_index"], ascending=[True, False],
                        na_position="last").reset_index(drop=True)

    columns: dict[str, list[Any]] = {}
    for field, nd in CATALOGUE_FIELDS.items():
        if field in (
            "is_control", "rankable", "hz_model_extrapolated",
            "composite_uses_mixed_sources",
        ):
            columns[field] = [bool(x) if x is not None and not pd.isna(x) else False
                              for x in df.get(field, pd.Series([False] * len(df)))]
        else:
            columns[field] = _col(df, field, nd)

    return {
        "generated_utc": utc_now_iso(),
        "earth2_version": __version__,
        "n_rows": int(len(df)),
        "format": "columnar",
        "note": (
            "One array per field, index-aligned. Solar System controls carry "
            "is_control=true and are comparison references, not exoplanet observations."
        ),
        "fields": list(CATALOGUE_FIELDS.keys()),
        "columns": columns,
    }


def export_universe(ranking: pd.DataFrame, max_points: int | None = None) -> dict[str, Any]:
    """3D positions for the interactive universe view.

    Converts right ascension, declination and distance into Cartesian
    coordinates in parsecs, using the standard equatorial convention::

        x = d cos(dec) cos(ra)
        y = d cos(dec) sin(ra)
        z = d sin(dec)

    Only planets with a real measured distance are included. A planet without a
    parallax-derived distance has no defensible position in a 3D map, and
    inventing one -- placing it at a default radius, or at the population median
    -- would put a fabricated point in a view the reader will read as
    observational. Those planets are counted and reported as excluded instead.
    """
    df = ranking.copy()
    if "is_control" in df.columns:
        df = df[~df["is_control"].fillna(False).astype(bool)]

    ra = pd.to_numeric(df.get("ra"), errors="coerce")
    dec = pd.to_numeric(df.get("dec"), errors="coerce")
    dist = pd.to_numeric(df.get("sy_dist"), errors="coerce")

    ok = ra.notna() & dec.notna() & dist.notna() & (dist > 0)
    n_excluded = int((~ok).sum())
    sub = df[ok].copy()

    if max_points and len(sub) > max_points:
        # Keep the highest-ranked, then a random but SEEDED sample of the rest, so
        # the view is reproducible and never silently reordered between builds.
        top = sub.nlargest(max_points // 2, "earth2_index")
        rest = sub.drop(top.index).sample(
            n=max_points - len(top), random_state=20260824
        )
        sub = pd.concat([top, rest])
        subsampled = True
    else:
        subsampled = False

    ra_r = np.radians(pd.to_numeric(sub["ra"], errors="coerce").to_numpy(dtype=float))
    dec_r = np.radians(pd.to_numeric(sub["dec"], errors="coerce").to_numpy(dtype=float))
    d = pd.to_numeric(sub["sy_dist"], errors="coerce").to_numpy(dtype=float)

    x = d * np.cos(dec_r) * np.cos(ra_r)
    y = d * np.cos(dec_r) * np.sin(ra_r)
    z = d * np.sin(dec_r)

    def r3(a: np.ndarray) -> list[float]:
        return [round(float(v), 3) for v in a]

    return {
        "generated_utc": utc_now_iso(),
        "n_points": int(len(sub)),
        "n_excluded_no_distance": n_excluded,
        "subsampled": subsampled,
        "coordinate_system": "Equatorial Cartesian, parsecs, Sun at origin",
        "note": (
            "Only planets with a measured system distance appear. Planets without one are "
            "excluded and counted, never placed at an invented distance."
        ),
        "x": r3(x), "y": r3(y), "z": r3(z),
        "name": [str(v) for v in sub["pl_name"]],
        "host": [str(v) for v in sub.get("hostname", pd.Series([""] * len(sub)))],
        "dist_pc": [round(float(v), 3) for v in d],
        "earth2_index": _col(sub, "earth2_index", 4),
        "esi": _col(sub, "esi_global_p50", 4),
        "hz_prob": _col(sub, "hz_conservative_prob", 3),
        "rade": _col(sub, "pl_rade", 3),
        "teq": _col(sub, "teq_used", 0),
        "st_teff": _col(sub, "st_teff", 0),
        "method": _col(sub, "discoverymethod", None),
        "disc_year": _col(sub, "disc_year", 0),
    }


def export_galaxy(ranking: pd.DataFrame) -> dict[str, Any]:
    """Every system's position in the Milky Way, plus real per-method detection shells.

    Converts equatorial (ra, dec, distance) to Galactocentric Cartesian
    coordinates via astropy, with the Sun's own position pinned to explicitly
    cited values (GALCEN_DISTANCE_KPC, SUN_HEIGHT_PC above) rather than
    whatever astropy's bundled default happens to be in the installed
    version -- the output must not silently drift if astropy is upgraded.

    The "detection shells" are the furthest distance this catalogue actually
    contains a confirmed detection at, per discovery method. That is a real,
    reproducible statistic about this dataset. It is deliberately NOT framed
    as an instrument sensitivity limit: how far a method can detect a planet
    depends on the target star's brightness and the planet's size, and
    stating a single number for "how far can Transit see" would need
    fabricated caveats to defend. "How far this method has found something,
    here" needs none.
    """
    df = ranking.copy()
    if "is_control" in df.columns:
        df = df[~df["is_control"].fillna(False).astype(bool)]

    ra = pd.to_numeric(df.get("ra"), errors="coerce")
    dec = pd.to_numeric(df.get("dec"), errors="coerce")
    dist = pd.to_numeric(df.get("sy_dist"), errors="coerce")

    ok = ra.notna() & dec.notna() & dist.notna() & (dist > 0)
    n_excluded = int((~ok).sum())
    sub = df[ok].copy()

    frame = Galactocentric(
        galcen_distance=GALCEN_DISTANCE_KPC * u.kpc,
        z_sun=SUN_HEIGHT_PC * u.pc,
    )
    coords = SkyCoord(
        ra=pd.to_numeric(sub["ra"], errors="coerce").to_numpy(dtype=float) * u.deg,
        dec=pd.to_numeric(sub["dec"], errors="coerce").to_numpy(dtype=float) * u.deg,
        distance=pd.to_numeric(sub["sy_dist"], errors="coerce").to_numpy(dtype=float) * u.pc,
        frame="icrs",
    )
    galcen = coords.transform_to(frame)
    x_kpc = galcen.x.to(u.kpc).value
    y_kpc = galcen.y.to(u.kpc).value
    z_kpc = galcen.z.to(u.kpc).value

    # The Sun's own position in this frame, by the same explicit convention
    # (astropy places it at (-galcen_distance, 0, z_sun); verified directly
    # against a test point at galactic l=0,b=0 during development rather than
    # assumed from documentation alone).
    sun_x_kpc = -GALCEN_DISTANCE_KPC
    sun_y_kpc = 0.0
    sun_z_kpc = SUN_HEIGHT_PC / 1000.0

    method_raw = sub.get("discoverymethod", pd.Series([None] * len(sub), index=sub.index))
    method_group = method_raw.where(method_raw.isin(NAMED_METHODS), "Other")
    dist_pc = pd.to_numeric(sub["sy_dist"], errors="coerce")
    method_shells_pc = {
        str(g): round(float(dist_pc[method_group == g].max()), 1)
        for g in [*NAMED_METHODS, "Other"]
        if (method_group == g).any()
    }

    def r3(a: np.ndarray) -> list[float]:
        return [round(float(v), 4) for v in a]

    return {
        "generated_utc": utc_now_iso(),
        "n_points": int(len(sub)),
        "n_excluded_no_distance": n_excluded,
        "coordinate_system": "Galactocentric Cartesian, kpc, Galactic Centre at origin",
        "note": (
            "Positions are computed from each system's real right ascension, declination "
            "and measured distance via the standard equatorial-to-Galactocentric transform "
            "(astropy). The Milky Way's own spiral structure shown behind these points is an "
            "illustrative schematic, not measured data -- we are inside the galaxy and cannot "
            "photograph its overall shape from outside it."
        ),
        "galcen_distance_kpc": GALCEN_DISTANCE_KPC,
        "galcen_distance_citation": "GRAVITY Collaboration (2019), A&A 625, L10",
        "sun_height_pc": SUN_HEIGHT_PC,
        "sun_height_citation": "Bennett & Bovy (2019), MNRAS 482, 1417",
        "sun_x_kpc": sun_x_kpc, "sun_y_kpc": sun_y_kpc, "sun_z_kpc": sun_z_kpc,
        "x_kpc": r3(x_kpc), "y_kpc": r3(y_kpc), "z_kpc": r3(z_kpc),
        "name": [str(v) for v in sub["pl_name"]],
        "host": [str(v) for v in sub.get("hostname", pd.Series([""] * len(sub)))],
        "dist_pc": [round(float(v), 3) for v in dist_pc],
        "earth2_index": _col(sub, "earth2_index", 4),
        "method": _col(sub, "discoverymethod", None),
        "disc_year": _col(sub, "disc_year", 0),
        "method_shells_pc": method_shells_pc,
        "method_shells_note": (
            "The furthest distance this catalogue actually contains a confirmed detection at, "
            "per method -- not a theoretical instrument sensitivity limit, which depends heavily "
            "on the target star's brightness and the planet's size."
        ),
    }


def export_all(
    ranking: pd.DataFrame,
    summary: dict[str, Any],
    coverage: pd.DataFrame,
    out_dir: Path,
    deep_dives: list[dict[str, Any]] | None = None,
    spectra_inventory: pd.DataFrame | None = None,
    provenance: pd.DataFrame | None = None,
    sync_state: dict[str, Any] | None = None,
    transit_validation: dict[str, Any] | None = None,
    transitspec: pd.DataFrame | None = None,
) -> dict[str, Path]:
    """Write every JSON product the website consumes."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    written["summary"] = write_json(summary, out_dir / "summary.json", indent=1)
    written["catalogue"] = write_json(export_catalogue_columnar(ranking), out_dir / "catalogue.json")
    written["universe"] = write_json(export_universe(ranking), out_dir / "universe.json")
    written["galaxy"] = write_json(export_galaxy(ranking), out_dir / "galaxy.json")

    written["coverage"] = write_json(
        {"generated_utc": utc_now_iso(), "rows": coverage.to_dict("records")},
        out_dir / "coverage.json", indent=1,
    )

    store = ManifestStore()
    written["provenance"] = write_json(
        {
            "generated_utc": utc_now_iso(),
            "total_source_records": store.total_source_records(),
            "datasets": store.summary_rows(),
            "sync_state": sync_state or {},
        },
        out_dir / "provenance.json", indent=1,
    )

    if transit_validation:
        written["transit_validation"] = write_json(
            transit_validation, out_dir / "transit_validation.json", indent=1
        )

    if spectra_inventory is not None and not spectra_inventory.empty:
        written["spectra_index"] = write_json(
            {"generated_utc": utc_now_iso(),
             "rows": spectra_inventory.to_dict("records")},
            out_dir / "spectra_index.json", indent=1,
        )

    # Every planet's full assembled spectrum (transmission, >=4 usable points),
    # not just the top-ranked deep-dive systems. The Spectral Lab needs to show
    # all ~97 planets with real published spectra, most of which are hot
    # Jupiters with no habitability interest but genuine atmospheric data.
    if transitspec is not None and not transitspec.empty:
        from earth2.spectroscopy import planet_spectrum

        spec_dir = out_dir / "spectra"
        spec_dir.mkdir(parents=True, exist_ok=True)
        names = (
            spectra_inventory[spectra_inventory["kind"] == "transmission"]["pl_name"].tolist()
            if spectra_inventory is not None and not spectra_inventory.empty
            else []
        )
        for name in names:
            spec = planet_spectrum(transitspec, name)
            if spec:
                slug = str(name).replace(" ", "_").replace("/", "-")
                write_json(spec, spec_dir / (slug + ".json"), gzip_also=False, indent=1)
        written["spectra_dir"] = spec_dir

    if deep_dives:
        dd_dir = out_dir / "deepdive"
        dd_dir.mkdir(parents=True, exist_ok=True)
        # Clear stale per-planet files first: the deep-dive target set can
        # change between runs (e.g. after a ranking-methodology fix), and a
        # planet that drops out must not leave a stale, still-reachable JSON
        # page behind under its old candidate URL.
        for stale in dd_dir.glob("*.json*"):
            stale.unlink()
        index = []
        for dd in deep_dives:
            slug = str(dd.get("planet", "unknown")).replace(" ", "_").replace("/", "-")
            write_json(dd, dd_dir / (slug + ".json"), gzip_also=True, indent=1)
            index.append({
                "planet": dd.get("planet"),
                "slug": slug,
                "hostname": dd.get("hostname"),
                "earth2_index": dd.get("ranking", {}).get("earth2_index"),
                "earth2_rank": dd.get("ranking", {}).get("earth2_rank"),
                "distance_pc": dd.get("host_star", {}).get("distance_pc"),
                "has_transmission_spectrum": bool(
                    dd.get("transmission_spectrum", {}).get("n_points", 0)
                ),
                "has_rv_analysis": dd.get("rv_analysis", {}).get("status") == "ok",
                "transit_status": dd.get("transit_analysis", {}).get("status"),
            })
        written["deepdive_index"] = write_json(
            {"generated_utc": utc_now_iso(), "systems": index},
            out_dir / "deepdive_index.json", indent=1,
        )

    # Reference bibliography derived from the actual provenance table.
    if provenance is not None and not provenance.empty:
        pubs = provenance[provenance["source_kind"] == "publication"]
        agg = (pubs.groupby(["reference_label", "reference_url", "bibcode"], dropna=False)
               .size().reset_index(name="n_measurements")
               .sort_values("n_measurements", ascending=False))
        written["references"] = write_json(
            {
                "generated_utc": utc_now_iso(),
                "n_distinct_publications": int(len(agg)),
                "n_measurement_links": int(len(pubs)),
                "note": (
                    "Compiled from the per-measurement reference links the NASA Exoplanet "
                    "Archive attaches to each composite parameter. Counts are the number of "
                    "measurements in this analysis traceable to each source."
                ),
                "references": agg.head(400).to_dict("records"),
            },
            out_dir / "references.json", indent=1,
        )

    return written
