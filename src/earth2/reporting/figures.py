"""Publication-quality figures, generated from the analysis output.

Every figure here is produced by code, from ``results/candidate_ranking.parquet``
and its companions. None is drawn by hand, and none contains a value that was
not computed by the pipeline. Re-running the analysis re-draws them.

Style
-----
Light background with dark text, deliberately. These figures appear in the
README on GitHub, which readers view in both light and dark themes; a dark
figure is unreadable in one of them and a light one is legible in both. The
website renders its own interactive charts in its own palette rather than
embedding these.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

__all__ = ["FIGURE_FUNCTIONS", "apply_style", "generate_all"]

# Palette: restrained, colour-blind-safe, and consistent across every figure.
INK = "#12161f"
MUTED = "#5b6472"
GRID = "#dde2ea"
ACCENT = "#1f6feb"      # scientific blue
WARM = "#c9761b"        # warm gold
TEAL = "#1a8a80"
CRIMSON = "#b02a37"
EARTH = "#2f7d32"
VIOLET = "#6f42c1"

METHOD_COLOURS = {
    "Transit": ACCENT,
    "Radial Velocity": WARM,
    "Microlensing": TEAL,
    "Imaging": VIOLET,
    "Transit Timing Variations": CRIMSON,
    "Eclipse Timing Variations": "#8a6d3b",
    "Pulsar Timing": "#495057",
    "Orbital Brightness Modulation": "#a0522d",
    "Astrometry": "#0b7285",
}


def apply_style() -> None:
    import matplotlib as mpl

    mpl.rcParams.update({
        "figure.dpi": 130,
        "savefig.dpi": 180,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "axes.labelsize": 10,
        "axes.titlesize": 11.5,
        "axes.titleweight": "600",
        "axes.labelcolor": INK,
        "axes.edgecolor": "#aeb6c2",
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "grid.alpha": 0.9,
        "axes.axisbelow": True,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "text.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def _planets(df: pd.DataFrame) -> pd.DataFrame:
    if "is_control" in df.columns:
        return df[~df["is_control"].fillna(False).astype(bool)]
    return df


def _controls(df: pd.DataFrame) -> pd.DataFrame:
    if "is_control" in df.columns:
        return df[df["is_control"].fillna(False).astype(bool)]
    return df.iloc[0:0]


def _source_note(ax, text: str = "NASA Exoplanet Archive | earth2 pipeline") -> None:
    ax.figure.text(0.995, 0.005, text, ha="right", va="bottom",
                   fontsize=7, color=MUTED, alpha=0.85)


#: When True, every _title() call below is a no-op. Set via no_titles() around
#: a generate_all() call for the LaTeX report: a journal figure gets its label
#: from the caption underneath it, and an in-image title above the same figure
#: would just repeat that text a second time in a different font.
SUPPRESS_TITLES = False


def _title(ax, text: str, **kw: Any) -> None:
    if not SUPPRESS_TITLES:
        ax.set_title(text, **kw)


class no_titles:
    """Context manager: draw figures without in-image titles.

    Used only for the title-less variants generated for the LaTeX manuscript.
    The default (titled) figures used in the README and website are
    unaffected outside this block.
    """

    def __enter__(self) -> None:
        global SUPPRESS_TITLES
        self._previous = SUPPRESS_TITLES
        SUPPRESS_TITLES = True

    def __exit__(self, *exc: Any) -> None:
        global SUPPRESS_TITLES
        SUPPRESS_TITLES = self._previous


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------
def fig_mass_radius(df: pd.DataFrame, out: Path) -> Path:
    """Mass-radius diagram, split by whether the mass was actually measured."""
    import matplotlib.pyplot as plt

    p = _planets(df)
    fig, ax = plt.subplots(figsize=(7.2, 5.2))

    measured = p[p["mass_class"].isin(["measured", "msini_deprojected"])]
    inferred = p[p["mass_class"] == "inferred_mass_radius"]
    msini = p[p["mass_class"] == "msini_lower_limit"]

    ax.scatter(inferred["pl_bmasse"], inferred["pl_rade"], s=6, c="#c9ced8",
               alpha=0.55, linewidths=0, label="Mass inferred from radius (n=%d)" % len(inferred))
    ax.scatter(msini["pl_bmasse"], msini["pl_rade"], s=9, c=WARM,
               alpha=0.5, linewidths=0, label="M sin i lower limit (n=%d)" % len(msini))
    ax.scatter(measured["pl_bmasse"], measured["pl_rade"], s=11, c=ACCENT,
               alpha=0.72, linewidths=0, label="Measured mass (n=%d)" % len(measured))

    for _, r in _controls(df).iterrows():
        if np.isfinite(r.get("pl_bmasse", np.nan)) and np.isfinite(r.get("pl_rade", np.nan)):
            ax.scatter(r["pl_bmasse"], r["pl_rade"], s=64, marker="*", c=EARTH,
                       edgecolors="white", linewidths=0.7, zorder=5)
            ax.annotate(r["pl_name"], (r["pl_bmasse"], r["pl_rade"]),
                        textcoords="offset points", xytext=(8, -9),
                        fontsize=8, color=EARTH, weight="600")

    # Constant-density reference curves.
    m = np.logspace(-1.2, 4.2, 200)
    for rho, lbl in [(1.0, r"1 g cm$^{-3}$"), (5.51, r"5.51 (Earth)"), (10.0, r"10 g cm$^{-3}$")]:
        r_curve = (m / (rho / 5.514)) ** (1 / 3)
        ax.plot(m, r_curve, ls="--", lw=0.8, c=MUTED, alpha=0.5)
        ax.annotate(lbl, (m[-1], r_curve[-1]), fontsize=7, color=MUTED,
                    ha="right", va="bottom")

    ax.axhline(1.6, color=CRIMSON, lw=0.9, ls=":", alpha=0.8)
    ax.annotate("1.6 R$_\\oplus$: above this most planets are not rocky (Rogers 2015)",
                (0.09, 1.68), fontsize=7.5, color=CRIMSON)

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"Planet mass  [M$_\oplus$]")
    ax.set_ylabel(r"Planet radius  [R$_\oplus$]")
    _title(ax, "Mass-radius diagram: what is measured and what is inferred")
    ax.set_xlim(0.05, 3e4); ax.set_ylim(0.3, 30)
    ax.legend(loc="upper left", markerscale=1.8)
    _source_note(ax)
    fig.savefig(out); plt.close(fig)
    return out


def fig_flux_radius_hz(df: pd.DataFrame, out: Path) -> Path:
    """Incident flux vs radius, with the conservative habitable zone marked."""
    import matplotlib.pyplot as plt

    p = _planets(df).copy()
    p = p[p["insol_used"].notna() & p["pl_rade"].notna()]

    fig, ax = plt.subplots(figsize=(7.2, 5.2))

    inhz = p[p["hz_conservative"] == 1]
    out_hz = p[p["hz_conservative"] != 1]

    ax.scatter(out_hz["insol_used"], out_hz["pl_rade"], s=6, c="#c9ced8",
               alpha=0.5, linewidths=0, label="Outside conservative HZ (n=%d)" % len(out_hz))
    sc = ax.scatter(inhz["insol_used"], inhz["pl_rade"], s=26,
                    c=inhz["earth2_index"], cmap="viridis", vmin=0, vmax=1,
                    alpha=0.95, linewidths=0.3, edgecolors="white",
                    label="In conservative HZ (n=%d)" % len(inhz), zorder=4)

    # The conservative HZ for a Sun-like star, as a shaded flux band.
    ax.axvspan(0.3507, 1.0385, color=EARTH, alpha=0.08, zorder=0)
    ax.annotate("Conservative HZ\n(Sun-like host)", (0.60, 18), fontsize=7.5,
                color=EARTH, ha="center")

    ax.axhline(1.6, color=CRIMSON, lw=0.9, ls=":", alpha=0.8)

    for _, r in _controls(df).iterrows():
        if np.isfinite(r.get("insol_used", np.nan)):
            ax.scatter(r["insol_used"], r["pl_rade"], s=64, marker="*", c=EARTH,
                       edgecolors="white", linewidths=0.7, zorder=6)
            ax.annotate(r["pl_name"], (r["insol_used"], r["pl_rade"]),
                        textcoords="offset points", xytext=(7, 2),
                        fontsize=8, color=EARTH, weight="600")

    cb = fig.colorbar(sc, ax=ax, pad=0.015)
    cb.set_label("Earth-2.0 index", fontsize=9)
    cb.outline.set_visible(False)  # type: ignore[operator]  # mpl stub: Spine not callable false positive

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.invert_xaxis()
    ax.set_xlabel(r"Incident stellar flux  [S$_\oplus$]   (hotter $\leftarrow$   $\rightarrow$ colder)")
    ax.set_ylabel(r"Planet radius  [R$_\oplus$]")
    _title(ax, "Stellar flux against planet radius")
    ax.set_ylim(0.3, 30)
    ax.legend(loc="lower left", markerscale=1.5)
    _source_note(ax)
    fig.savefig(out); plt.close(fig)
    return out


def fig_hr_diagram(df: pd.DataFrame, out: Path) -> Path:
    """Host-star HR diagram with the habitable-zone model validity range."""
    import matplotlib.pyplot as plt

    p = _planets(df)
    hosts = p.drop_duplicates(subset=["hostname"])
    hosts = hosts[hosts["st_teff"].notna() & hosts["st_lum"].notna()]

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    n_hz = hosts["hz_conservative"] == 1
    ax.scatter(hosts.loc[~n_hz, "st_teff"], hosts.loc[~n_hz, "st_lum"],
               s=7, c="#c2c8d2", alpha=0.6, linewidths=0, label="Host stars (n=%d)" % len(hosts))
    ax.scatter(hosts.loc[n_hz, "st_teff"], hosts.loc[n_hz, "st_lum"],
               s=26, c=ACCENT, alpha=0.9, linewidths=0.3, edgecolors="white",
               label="Hosts of conservative-HZ planets", zorder=4)

    ax.axvspan(2600, 7200, color=EARTH, alpha=0.07, zorder=0)
    ax.annotate("Kopparapu et al. (2013) validity: 2600-7200 K",
                (7200, ax.get_ylim()[1]), fontsize=7.5, color=EARTH,
                ha="left", va="top", rotation=0)

    ax.scatter([5772], [0.0], s=90, marker="*", c=WARM, edgecolors="white",
               linewidths=0.8, zorder=6)
    ax.annotate("Sun", (5772, 0.0), textcoords="offset points", xytext=(8, 4),
                fontsize=8.5, color=WARM, weight="600")

    ax.invert_xaxis()
    ax.set_xlabel(r"Stellar effective temperature  [K]")
    ax.set_ylabel(r"log$_{10}$ (L / L$_\odot$)")
    _title(ax, "Host-star Hertzsprung-Russell diagram")
    ax.legend(loc="lower left", markerscale=1.5)
    _source_note(ax)
    fig.savefig(out); plt.close(fig)
    return out


def fig_discovery_timeline(df: pd.DataFrame, out: Path) -> Path:
    """Cumulative discoveries by method -- the shape of observational bias."""
    import matplotlib.pyplot as plt

    p = _planets(df).copy()
    p["disc_year"] = pd.to_numeric(p["disc_year"], errors="coerce")
    p = p[p["disc_year"].notna()]

    methods = p["discoverymethod"].value_counts().head(6).index.tolist()
    years = np.arange(int(p["disc_year"].min()), int(p["disc_year"].max()) + 1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6),
                                   gridspec_kw={"width_ratios": [1.6, 1]})

    bottom = np.zeros(len(years))
    for m in methods:
        counts = np.array([int(((p["discoverymethod"] == m) & (p["disc_year"] == y)).sum())
                           for y in years], dtype=float)
        ax1.bar(years, counts, bottom=bottom, width=0.85,
                color=METHOD_COLOURS.get(m, MUTED), label=m, linewidth=0)
        bottom += counts
    ax1.set_xlabel("Discovery year")
    ax1.set_ylabel("Planets discovered")
    _title(ax1, "Confirmed exoplanet discoveries by year and method")
    ax1.legend(loc="upper left", ncol=2)

    vc = p["discoverymethod"].value_counts()
    ax2.barh(range(len(vc)), vc.values,
             color=[METHOD_COLOURS.get(m, MUTED) for m in vc.index], linewidth=0)
    ax2.set_yticks(range(len(vc)))
    ax2.set_yticklabels(vc.index, fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xscale("log")
    ax2.set_xlabel("Planets (log scale)")
    _title(ax2, "Detection method share")
    for i, v in enumerate(vc.values):
        ax2.annotate(f"{v:,}", (v, i), xytext=(4, 0), textcoords="offset points",
                     va="center", fontsize=7.5, color=MUTED)
    _source_note(ax2)
    fig.savefig(out); plt.close(fig)
    return out


def fig_data_coverage(coverage: pd.DataFrame, out: Path) -> Path:
    """How much of the catalogue is measured, and how much is quantified."""
    import matplotlib.pyplot as plt

    c = coverage.copy().sort_values("pct_with_value", ascending=True)
    fig, ax = plt.subplots(figsize=(8.2, 6.0))
    y = np.arange(len(c))

    ax.barh(y, c["pct_with_value"], height=0.62, color="#c8d6ea",
            label="Value present", linewidth=0)
    has_unc = c["pct_with_uncertainty"].notna()
    ax.barh(y[has_unc.to_numpy()], c.loc[has_unc, "pct_with_uncertainty"],
            height=0.34, color=ACCENT, label="Value AND published uncertainty", linewidth=0)

    ax.set_yticks(y)
    ax.set_yticklabels(c["quantity"], fontsize=8.5)
    ax.set_xlabel("Percentage of confirmed planets")
    ax.set_xlim(0, 100)
    _title(ax, "Data coverage: the gap is what looks measured but is not quantified")
    ax.legend(loc="lower right")
    for i, (v, _u) in enumerate(zip(c["pct_with_value"], c["pct_with_uncertainty"])):
        ax.annotate(f"{v:.0f}%", (v, i), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7.5, color=MUTED)
    _source_note(ax)
    fig.savefig(out); plt.close(fig)
    return out


def fig_ranking_distribution(df: pd.DataFrame, out: Path) -> Path:
    """Distribution of each component score across the ranked catalogue."""
    import matplotlib.pyplot as plt

    p = _planets(df)
    comps = [
        ("score_earth_similarity", "Earth similarity", ACCENT),
        ("score_conservative_habitability", "Conservative habitability", EARTH),
        ("score_observational_confidence", "Observational confidence", WARM),
        ("earth2_index", "Composite Earth-2.0 index", VIOLET),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.4))
    for ax, (col, label, colour) in zip(axes.ravel(), comps):
        v = pd.to_numeric(p.get(col), errors="coerce").dropna()
        ax.hist(v, bins=48, color=colour, alpha=0.85, linewidth=0)
        ax.set_yscale("log")
        ax.set_xlabel(label)
        ax.set_ylabel("Planets (log)")
        ax.set_xlim(0, 1)
        med = float(v.median()) if len(v) else np.nan
        if np.isfinite(med):
            ax.axvline(med, color=INK, lw=0.9, ls="--", alpha=0.7)
            ax.annotate(f"median {med:.3f}", (med, ax.get_ylim()[1]),
                        xytext=(4, -10), textcoords="offset points",
                        fontsize=7.5, color=INK, va="top")
        _title(ax, f"{label}  (n={len(v):,})", fontsize=10)
    fig.suptitle("Component score distributions across the analysed catalogue",
                 fontsize=12, weight="600")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _source_note(axes[1, 1])
    fig.savefig(out); plt.close(fig)
    return out


def fig_top_candidates(df: pd.DataFrame, out: Path, n: int = 15) -> Path:
    """Top candidates with their score decomposition and ESI uncertainty."""
    import matplotlib.pyplot as plt

    p = _planets(df).dropna(subset=["earth2_index"]).nlargest(n, "earth2_index")
    p = p.iloc[::-1]
    y = np.arange(len(p))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 6.0),
                                   gridspec_kw={"width_ratios": [1.25, 1]})

    parts = [
        ("score_earth_similarity", "Earth similarity", ACCENT),
        ("score_conservative_habitability", "Conservative habitability", EARTH),
        ("score_observational_confidence", "Observational confidence", WARM),
    ]
    h = 0.26
    for i, (col, label, colour) in enumerate(parts):
        ax1.barh(y + (i - 1) * h, pd.to_numeric(p[col], errors="coerce"),
                 height=h, color=colour, label=label, linewidth=0)
    ax1.set_yticks(y)
    ax1.set_yticklabels(p["pl_name"], fontsize=9)
    ax1.set_xlim(0, 1.02)
    ax1.set_ylim(-0.7, len(p) - 0.3)
    ax1.set_xlabel("Component score")
    _title(ax1, "Score decomposition")
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=3, fontsize=8.5)

    lo = pd.to_numeric(p["esi_global_p16"], errors="coerce")
    mid = pd.to_numeric(p["esi_global_p50"], errors="coerce")
    hi = pd.to_numeric(p["esi_global_p84"], errors="coerce")
    ax2.hlines(y, lo, hi, color=MUTED, lw=2.2, alpha=0.65)
    colours = [CRIMSON if mc == "inferred_mass_radius" else
               (WARM if mc == "msini_lower_limit" else ACCENT)
               for mc in p["mass_class"]]
    ax2.scatter(mid, y, s=42, c=colours, zorder=4, edgecolors="white", linewidths=0.7)
    ax2.set_yticks(y); ax2.set_yticklabels([])
    ax2.set_ylim(-0.7, len(p) - 0.3)
    ax2.set_xlabel("Earth Similarity Index (median, 16th-84th percentile)")
    _title(ax2, "ESI posterior and mass provenance")

    from matplotlib.lines import Line2D
    ax2.legend(handles=[
        Line2D([], [], marker="o", ls="", color=ACCENT, label="Measured mass"),
        Line2D([], [], marker="o", ls="", color=WARM, label="M sin i lower limit"),
        Line2D([], [], marker="o", ls="", color=CRIMSON, label="Mass inferred from radius"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=3, fontsize=8.5)

    fig.suptitle("Top Earth-2.0 candidates from the computed ranking",
                 fontsize=12.5, weight="600")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    _source_note(ax2)
    fig.savefig(out); plt.close(fig)
    return out


def fig_hz_diagram(df: pd.DataFrame, out: Path) -> Path:
    """Habitable zone in stellar-temperature vs incident-flux space."""
    import matplotlib.pyplot as plt

    from earth2.habitability import hz as hzmod

    p = _planets(df)
    p = p[p["st_teff"].notna() & p["insol_used"].notna()]
    small = p[p["pl_rade"] < 2.0]

    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    teff = np.linspace(2600, 7200, 400)

    rv = hzmod.seff_boundary(teff, "recent_venus")
    rg = hzmod.seff_boundary(teff, "runaway_greenhouse")
    mg = hzmod.seff_boundary(teff, "maximum_greenhouse")
    em = hzmod.seff_boundary(teff, "early_mars")

    ax.fill_betweenx(teff, em, rv, color=WARM, alpha=0.12, label="Optimistic HZ")
    ax.fill_betweenx(teff, mg, rg, color=EARTH, alpha=0.20, label="Conservative HZ")
    for b, ls in [(rv, ":"), (rg, "-"), (mg, "-"), (em, ":")]:
        ax.plot(b, teff, color=INK, lw=0.8, ls=ls, alpha=0.55)

    ax.scatter(p["insol_used"], p["st_teff"], s=5, c="#ccd2dc", alpha=0.45,
               linewidths=0, label="All confirmed planets")
    sc = ax.scatter(small["insol_used"], small["st_teff"], s=20,
                    c=small["earth2_index"], cmap="viridis", vmin=0, vmax=1,
                    alpha=0.9, linewidths=0.25, edgecolors="white",
                    label=r"R$_p$ < 2 R$_\oplus$", zorder=4)

    # Solar System controls all sit at the Sun's temperature, so their labels
    # would overprint each other on a shared horizontal line. Stagger vertically
    # and draw a leader line back to each marker.
    ctrl = _controls(df).copy()
    ctrl = ctrl[pd.to_numeric(ctrl["insol_used"], errors="coerce").notna()]
    ctrl = ctrl.sort_values("insol_used", ascending=False)
    for i, (_, r) in enumerate(ctrl.iterrows()):
        ax.scatter(r["insol_used"], r["st_teff"], s=70, marker="*", c=CRIMSON,
                   edgecolors="white", linewidths=0.7, zorder=6)
        dy = 260 * (1 if i % 2 == 0 else -1) * (1 + i // 2 * 0.55)
        ax.annotate(
            r["pl_name"], (r["insol_used"], r["st_teff"]),
            xytext=(r["insol_used"], r["st_teff"] + dy), textcoords="data",
            fontsize=8, color=CRIMSON, weight="600", ha="center",
            va="bottom" if dy > 0 else "top",
            arrowprops={"arrowstyle": "-", "color": CRIMSON, "lw": 0.6, "alpha": 0.55,
                            "shrinkA": 1, "shrinkB": 3},
        )

    cb = fig.colorbar(sc, ax=ax, pad=0.015)
    cb.set_label("Earth-2.0 index", fontsize=9); cb.outline.set_visible(False)  # type: ignore[operator]  # mpl stub: Spine not callable false positive

    ax.set_xscale("log"); ax.invert_xaxis()
    ax.set_xlim(2e3, 1e-3)
    ax.set_ylim(2400, 7600)
    ax.set_xlabel(r"Incident stellar flux  [S$_\oplus$]")
    ax.set_ylabel("Stellar effective temperature  [K]")
    _title(ax, "Habitable-zone boundaries after Kopparapu et al. (2013, erratum)")

    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor=WARM, alpha=0.25, label="Optimistic HZ"),
        Patch(facecolor=EARTH, alpha=0.35, label="Conservative HZ"),
        Line2D([], [], marker="o", ls="", ms=4, color="#ccd2dc",
               label="All confirmed planets (n=%d)" % len(p)),
        Line2D([], [], marker="o", ls="", ms=6, color="#3b528b",
               label=r"R$_p$ < 2 R$_\oplus$ (n=%d), shaded by index" % len(small)),
        Line2D([], [], marker="*", ls="", ms=10, color=CRIMSON,
               label="Solar System controls"),
    ], loc="upper left", fontsize=8)
    _source_note(ax)
    fig.savefig(out); plt.close(fig)
    return out


def fig_uncertainty(df: pd.DataFrame, out: Path) -> Path:
    """What uncertainty propagation actually does to the ranking."""
    import matplotlib.pyplot as plt

    p = _planets(df)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.6))

    w = pd.to_numeric(p["esi_global_p84"], errors="coerce") - \
        pd.to_numeric(p["esi_global_p16"], errors="coerce")
    cov = pd.to_numeric(p["mc_uncertainty_coverage"], errors="coerce")
    ok = w.notna() & cov.notna()
    sc = ax1.scatter(cov[ok], w[ok], s=7, c=pd.to_numeric(p.loc[ok, "esi_global_p50"],
                                                          errors="coerce"),
                     cmap="viridis", alpha=0.55, linewidths=0)
    ax1.set_xlabel("Fraction of parameters with a published uncertainty")
    ax1.set_ylabel("ESI 68% credible width")
    _title(ax1, "Posterior width against uncertainty coverage")
    cb = fig.colorbar(sc, ax=ax1, pad=0.015); cb.set_label("ESI median", fontsize=8.5)
    cb.outline.set_visible(False)  # type: ignore[operator]  # mpl stub: Spine not callable false positive

    prob = pd.to_numeric(p["hz_conservative_prob"], errors="coerce").dropna()
    ax2.hist(prob, bins=40, color=EARTH, alpha=0.85, linewidth=0)
    ax2.set_yscale("log")
    ax2.set_xlabel("Conservative habitable-zone membership probability")
    ax2.set_ylabel("Planets (log)")
    _title(ax2, "HZ membership is a probability, not a yes/no")
    ax2.annotate("planets on a zone edge\nland near 0.5, as they should",
                 (0.5, ax2.get_ylim()[1] * 0.25), fontsize=7.5, color=MUTED, ha="center")
    fig.tight_layout()
    _source_note(ax2)
    fig.savefig(out); plt.close(fig)
    return out


def fig_spectrum(spectrum: dict[str, Any], out: Path) -> Path | None:
    """A published transmission spectrum with expected molecular band positions."""
    import matplotlib.pyplot as plt

    if not spectrum or not spectrum.get("points"):
        return None

    pts = spectrum["points"]
    wl = np.array([p["wavelength_um"] for p in pts], dtype=float)
    dep = np.array([p["depth_ppm"] for p in pts], dtype=float)
    err = np.array([p["depth_ppm_err"] if p["depth_ppm_err"] is not None else np.nan
                    for p in pts], dtype=float)

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    ax.errorbar(wl, dep, yerr=err, fmt="o", ms=2.4, lw=0.6, elinewidth=0.6,
                color=ACCENT, ecolor="#9db8dd", alpha=0.85, capsize=0)

    shown = 0
    for band in spectrum.get("expected_bands", []):
        if band["colour_role"] not in ("primary", "biosignature_context"):
            continue
        colour = EARTH if band["colour_role"] == "biosignature_context" else WARM
        for b in band["bands_um"]:
            ax.axvline(b, color=colour, lw=0.7, ls="--", alpha=0.45)
        ax.annotate(band["species"], (band["bands_um"][0], ax.get_ylim()[1]),
                    fontsize=7.5, color=colour, rotation=90,
                    va="top", ha="right", alpha=0.9)
        shown += 1

    ax.set_xlabel(r"Wavelength  [$\mu$m]")
    ax.set_ylabel("Transit depth  [ppm]")
    _title(ax, "%s -- published transmission spectrum (%d points, %s)"
                 % (spectrum["planet"], spectrum["n_points"],
                    ", ".join(spectrum["facilities"][:2]) or "multiple facilities"))
    ax.figure.text(0.5, -0.02,
                   "Dashed lines mark where these species absorb. They are NOT detections.",
                   ha="center", fontsize=7.8, color=CRIMSON)
    _source_note(ax, "NASA Exoplanet Archive transitspec | earth2 pipeline")
    fig.savefig(out); plt.close(fig)
    return out


def fig_period_radius(df: pd.DataFrame, out: Path) -> Path:
    """Period-radius diagram: the classic exoplanet-population plot.

    Every confirmed planet, coloured by discovery method, on log-log axes.
    Top-ranked Earth-2.0 candidates are outlined and labelled so a reader can
    see where they sit relative to the full known population -- almost all in
    the short-period corner that transit and RV surveys are sensitive to.
    """
    import matplotlib.pyplot as plt

    p = _planets(df)
    p = p[p["pl_orbper"].notna() & p["pl_rade"].notna()]

    fig, ax = plt.subplots(figsize=(7.6, 5.6))
    for method, colour in METHOD_COLOURS.items():
        sub = p[p["discoverymethod"] == method]
        if sub.empty:
            continue
        ax.scatter(sub["pl_orbper"], sub["pl_rade"], s=7, c=colour, alpha=0.55,
                   linewidths=0, label="%s (n=%d)" % (method, len(sub)))
    other = p[~p["discoverymethod"].isin(METHOD_COLOURS)]
    if not other.empty:
        ax.scatter(other["pl_orbper"], other["pl_rade"], s=7, c=MUTED, alpha=0.4,
                   linewidths=0, label="Other (n=%d)" % len(other))

    top = p.dropna(subset=["earth2_index"]).nlargest(8, "earth2_index")
    ax.scatter(top["pl_orbper"], top["pl_rade"], s=46, facecolors="none",
              edgecolors=INK, linewidths=1.1, zorder=5)

    # The top candidates cluster within a factor of ~20 in period and ~1.5 in
    # radius, so inline offset labels collide. Labels are spread along a fixed
    # row beneath the cluster, ordered by period, each with a thin leader line
    # back to its point -- same device as the posterior-cloud and HZ figures.
    top_sorted = top.sort_values("pl_orbper")
    label_y = 0.42
    log_lo, log_hi = np.log10(1.5), np.log10(400.0)
    for i, (_, r) in enumerate(top_sorted.iterrows()):
        lx = 10 ** (log_lo + (i + 0.5) * (log_hi - log_lo) / len(top_sorted))
        ax.plot([r["pl_orbper"], lx], [r["pl_rade"], label_y], color=INK,
                lw=0.5, alpha=0.5, zorder=4)
        ax.annotate(r["pl_name"], (lx, label_y), fontsize=6.5, color=INK,
                    ha="center", va="top", rotation=90)

    ax.scatter([365.256], [1.0], s=80, marker="*", c=EARTH, edgecolors="white",
              linewidths=0.7, zorder=6)
    ax.annotate("Earth", (365.256, 1.0), textcoords="offset points", xytext=(7, -4),
                fontsize=8, color=EARTH, weight="600")

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_ylim(0.28, 45)
    ax.set_xlabel("Orbital period  [days]")
    ax.set_ylabel(r"Planet radius  [R$_\oplus$]")
    _title(ax, "Period-radius diagram: where the known population sits")
    ax.legend(loc="upper left", fontsize=7, markerscale=1.6, ncol=1)
    _source_note(ax)
    fig.savefig(out); plt.close(fig)
    return out


def fig_equilibrium_temperature(df: pd.DataFrame, out: Path) -> Path:
    """Equilibrium-temperature distribution with the Sun-like habitable band.

    The shaded band is not an arbitrary illustrative range: it is the
    conservative habitable-zone flux boundaries (Kopparapu et al. 2013,
    erratum) evaluated at the Sun's effective temperature and converted to
    equilibrium temperature at the same Bond albedo (0.306) this project uses
    everywhere else, so the figure is derived from the identical model as the
    rest of the pipeline rather than a separately chosen illustrative range.
    """
    import matplotlib.pyplot as plt

    from earth2.constants import BOND_ALBEDO_EARTH
    from earth2.habitability import hz as hzmod

    p = _planets(df)
    teq = pd.to_numeric(p["teq_used"], errors="coerce").dropna()
    teq = teq[(teq > 0) & (teq < 4000)]

    def teq_at(boundary: str) -> float:
        s = float(hzmod.seff_boundary(5780.0, boundary))
        return 278.5 * s**0.25 * (1 - BOND_ALBEDO_EARTH) ** 0.25

    t_inner_cons = teq_at("runaway_greenhouse")
    t_outer_cons = teq_at("maximum_greenhouse")
    t_inner_opt = teq_at("recent_venus")
    t_outer_opt = teq_at("early_mars")

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    ax.axvspan(t_outer_opt, t_inner_opt, color=WARM, alpha=0.10, zorder=0)
    ax.axvspan(t_outer_cons, t_inner_cons, color=EARTH, alpha=0.18, zorder=0)
    ax.hist(teq, bins=np.logspace(np.log10(teq.min()), np.log10(teq.max()), 70).tolist(),
           color=ACCENT, alpha=0.85, linewidth=0)

    ax.axvline(254.0, color=EARTH, lw=1.1, ls="--", alpha=0.8)
    # The Earth line and the HZ band label sit within ~15% of each other in
    # log-x, so a rotated in-band label and a vertical line label would
    # overlap directly. The HZ label goes ABOVE the axes (in the margin,
    # using axes-fraction y) and the Earth label goes to the LEFT of its line
    # at a fixed height, so the two never share the same region.
    ax.annotate("conservative HZ (Sun-like host)",
                ((t_inner_cons * t_outer_cons) ** 0.5, 1.015),
                xycoords=("data", "axes fraction"), fontsize=8, color=EARTH,
                ha="center", va="bottom")
    ax.annotate("Earth, 254 K", (254.0, 0.9), xycoords=("data", "axes fraction"),
                xytext=(-10, 0), textcoords="offset points", fontsize=8,
                color=EARTH, ha="right", va="center")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Equilibrium temperature  [K]  (Bond albedo 0.306)")
    ax.set_ylabel("Planets (log)")
    _title(ax, "Equilibrium-temperature distribution across the analysed catalogue", pad=20)
    _source_note(ax)
    fig.savefig(out); plt.close(fig)
    return out


def fig_distance_distribution(df: pd.DataFrame, out: Path) -> Path:
    """Distance distribution, with the computed top candidates marked.

    Demonstrates the discovery-distance selection effect directly: the
    highest-ranked candidates cluster at a few to a few tens of parsecs,
    because a temperate Earth-sized planet is only detectable at all around
    the nearest, quietest stars with current instruments.
    """
    import matplotlib.pyplot as plt

    p = _planets(df)
    dist = pd.to_numeric(p["sy_dist"], errors="coerce").dropna()
    dist = dist[dist > 0]

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    ax.hist(dist, bins=np.logspace(np.log10(max(dist.min(), 1)), np.log10(dist.max()), 60).tolist(),
           color=VIOLET, alpha=0.82, linewidth=0)

    top = p.dropna(subset=["earth2_index", "sy_dist"]).nlargest(8, "earth2_index")
    ymax = ax.get_ylim()[1]
    # Sibling planets in the same system (TRAPPIST-1 e/f/g, GJ 1002 b/c) sit at
    # an identical distance and would otherwise print overlapping labels on
    # the same vertical line. Grouping by host merges them into one label per
    # line, which is also more informative than three near-duplicate lines.
    groups = sorted(
        top.groupby("hostname"), key=lambda kv: float(kv[1]["sy_dist"].iloc[0])
    )
    # Two systems can sit within a few percent of each other in distance (GJ
    # 1061 and Teegarden's Star both do here), too close for rotated labels on
    # separate lines to avoid touching. Alternating the label's starting
    # height resolves it without needing to know in advance which pairs clash.
    for i, (host, grp) in enumerate(groups):
        d = float(grp["sy_dist"].iloc[0])
        letters = sorted(n.replace(host, "").strip() for n in grp["pl_name"])
        label = host + " " + "/".join(letters) if len(grp) > 1 else grp["pl_name"].iloc[0]
        ax.axvline(d, color=WARM, lw=0.9, alpha=0.75, zorder=4)
        y_start = ymax if i % 2 == 0 else ymax * 0.4
        ax.annotate(label, (d, y_start), xytext=(-3, -4),
                    textcoords="offset points", rotation=90, fontsize=6.6,
                    color=WARM, ha="right", va="top")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("System distance  [pc]")
    ax.set_ylabel("Planets (log)")
    _title(ax, "Distance distribution: top candidates sit in the nearest tail")
    _source_note(ax)
    fig.savefig(out); plt.close(fig)
    return out


def fig_gaia_parallax_check(df: pd.DataFrame, out: Path) -> Path:
    """Independent distance cross-check: the archive's adopted distance
    against 1000/parallax computed directly from this project's own Gaia DR3
    crossmatch (:mod:`earth2.data_sources.gaia`).

    The two are largely independent measurements of the same quantity (the
    archive's sy_dist is very often itself Gaia-parallax-derived by the
    original publication, but not always the same Gaia data release or the
    same processing), so points sitting on the 1:1 line are a genuine
    consistency check rather than a tautology. Coloured by RUWE: a point far
    off the line that also has a high RUWE is a candidate whose host may be
    an unresolved binary, which can bias exactly the parameters (stellar
    radius, hence planet radius) this project's ranking depends on.
    """
    import matplotlib.pyplot as plt

    p = _planets(df)
    sub = p[["sy_dist", "gaia_distance_pc", "gaia_ruwe", "pl_name", "earth2_index"]].copy()
    sub["sy_dist"] = pd.to_numeric(sub["sy_dist"], errors="coerce")
    sub["gaia_distance_pc"] = pd.to_numeric(sub["gaia_distance_pc"], errors="coerce")
    sub["gaia_ruwe"] = pd.to_numeric(sub["gaia_ruwe"], errors="coerce")
    sub = sub.dropna(subset=["sy_dist", "gaia_distance_pc"])
    sub = sub[(sub["sy_dist"] > 0) & (sub["gaia_distance_pc"] > 0)]

    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    if sub.empty:
        ax.text(0.5, 0.5, "No Gaia DR3 crossmatch available for this run",
               ha="center", va="center", color=MUTED, transform=ax.transAxes)
        _title(ax, "Independent distance cross-check: archive vs. Gaia DR3 parallax")
        fig.savefig(out); plt.close(fig)
        return out

    lo = min(sub["sy_dist"].min(), sub["gaia_distance_pc"].min()) * 0.85
    hi = max(sub["sy_dist"].max(), sub["gaia_distance_pc"].max()) * 1.15
    ax.plot([lo, hi], [lo, hi], color=MUTED, lw=1.0, ls="--", zorder=1, label="Perfect agreement")

    ruwe = sub["gaia_ruwe"].clip(upper=3.0)
    sc = ax.scatter(sub["sy_dist"], sub["gaia_distance_pc"], c=ruwe, cmap="magma_r",
                    s=16, alpha=0.75, linewidths=0, vmin=1.0, vmax=3.0, zorder=3)
    high_ruwe = sub[sub["gaia_ruwe"] > 1.4]
    ax.scatter(high_ruwe["sy_dist"], high_ruwe["gaia_distance_pc"], facecolors="none",
              edgecolors=WARM, linewidths=0.9, s=42, zorder=4,
              label=f"RUWE > 1.4 (n={len(high_ruwe)}, possible unresolved binary)")

    cb = fig.colorbar(sc, ax=ax, pad=0.015)
    cb.set_label("Gaia RUWE (clipped at 3.0)", fontsize=9)
    cb.outline.set_visible(False)  # type: ignore[operator]  # mpl stub: Spine not callable false positive

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel("Archive adopted distance, sy_dist  [pc]")
    ax.set_ylabel("Gaia DR3 parallax distance, 1000/parallax  [pc]")
    _title(ax, "Independent distance cross-check: archive vs. Gaia DR3 parallax")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
    _source_note(ax, "NASA Exoplanet Archive + Gaia DR3 | earth2 pipeline")
    fig.savefig(out); plt.close(fig)
    return out


def fig_evidence_matrix(df: pd.DataFrame, out: Path, n: int = 22) -> Path:
    """Data-confidence / evidence-coverage matrix for the top candidates.

    Each cell is a distinct evidential fact, not a decorative colour scale:
    mass provenance quality, propagated-uncertainty coverage, published
    reference depth, and the availability of each independent observational
    modality (transit photometry, radial velocity, atmospheric spectroscopy).
    A high Earth-2.0 index sitting on a mostly-empty row is exactly the
    warning sign this figure exists to surface.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    # Unlike the barh-based figures elsewhere in this module, imshow already
    # places row 0 at the TOP of the axes, so the top-ranked candidate must
    # stay first in the frame rather than being reversed to the bottom.
    p = _planets(df).dropna(subset=["earth2_index"]).nlargest(n, "earth2_index")

    mass_q = {
        "measured": 1.0, "msini_deprojected": 0.75, "msini_lower_limit": 0.5,
        "upper_limit": 0.2, "inferred_mass_radius": 0.1, "missing": 0.0,
    }
    cols = [
        ("Mass\nprovenance", p["mass_class"].map(mass_q).fillna(0.0)),
        ("Uncertainty\ncoverage", pd.to_numeric(p["mc_uncertainty_coverage"], errors="coerce").fillna(0.0)),
        ("Reference\ndepth", (np.log1p(pd.to_numeric(p["n_references"], errors="coerce").fillna(0))
                              / np.log1p(10)).clip(0, 1)),
        ("HZ model\nvalid", (~p["hz_model_extrapolated"].fillna(False).astype(bool)).astype(float)),
        ("Transiting", pd.to_numeric(p["tran_flag"], errors="coerce").fillna(0).clip(0, 1)),
        ("RV\ndetected", pd.to_numeric(p["rv_flag"], errors="coerce").fillna(0).clip(0, 1)),
        ("Atmospheric\nspectrum", (pd.to_numeric(p["n_transmission_points"], errors="coerce").fillna(0) > 0).astype(float)),
    ]
    matrix = np.column_stack([c[1].to_numpy(dtype=float) for c in cols])
    labels = [c[0] for c in cols]

    cmap = LinearSegmentedColormap.from_list("evidence", ["#1b2030", "#1a4d6b", "#1f8f7a", "#8fd14f"])

    fig, ax = plt.subplots(figsize=(8.6, 0.34 * len(p) + 1.8))
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0, vmax=1)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_yticks(range(len(p)))
    ax.set_yticklabels(p["pl_name"], fontsize=8)
    ax.set_xticks(np.arange(-0.5, len(labels), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(p), 1), minor=True)
    ax.grid(which="minor", color=INK, linewidth=1.2)
    ax.tick_params(which="minor", length=0)
    ax.tick_params(which="major", length=0)

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            v = matrix[i, j]
            txt = "✓" if v >= 0.999 else ("–" if v <= 0.001 else "%.2f" % v)
            ax.text(j, i, txt, ha="center", va="center", fontsize=7.5,
                    color="white" if v < 0.6 else INK)

    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cb.set_label("Evidence strength", fontsize=8)
    _title(ax, "Data-confidence matrix: what actually backs each top candidate", fontsize=11.5)
    _source_note(ax)
    fig.tight_layout()
    fig.savefig(out); plt.close(fig)
    return out


def fig_posterior_clouds(df: pd.DataFrame, out: Path, n: int = 6, n_samples: int = 6000) -> Path:
    """Monte Carlo posterior clouds for the top candidates: real uncertainty, not error bars.

    Draws fresh samples for radius and mass from each candidate's own
    published (asymmetric, two-piece-normal) uncertainties using the same
    sampler the pipeline itself uses (`earth2.uncertainty.sample_split_normal`),
    then plots the joint radius-density cloud. A tight cloud is a well-measured
    planet; a smeared one is not, and the difference is only visible by
    plotting the distribution itself rather than a single point with error bars.
    """
    import matplotlib
    import matplotlib.pyplot as plt

    from earth2.constants import RHO_EARTH_G_CM3
    from earth2.uncertainty import sample_split_normal

    p = _planets(df).dropna(subset=["earth2_index"]).nlargest(n, "earth2_index")
    rng = np.random.default_rng(20260824)

    fig, ax = plt.subplots(figsize=(7.8, 6.4))
    colours = matplotlib.colormaps["viridis"](np.linspace(0.08, 0.92, len(p)))

    medians = []
    rade_bounds = []  # (p1, p99) per candidate, to size the x-axis to the data actually drawn
    for (_, r), colour in zip(p.iterrows(), colours):
        rade = sample_split_normal(
            np.array([r["pl_rade"]]), np.array([abs(r.get("pl_radeerr1", 0.05) or 0.05)]),
            np.array([abs(r.get("pl_radeerr2", 0.05) or 0.05)]), n_samples, rng, positive=True,
        ).ravel()
        mass = sample_split_normal(
            np.array([r["pl_bmasse"]]), np.array([abs(r.get("pl_bmasseerr1", 0.1) or 0.1)]),
            np.array([abs(r.get("pl_bmasseerr2", 0.1) or 0.1)]), n_samples, rng, positive=True,
        ).ravel()
        with np.errstate(invalid="ignore", divide="ignore"):
            dens = RHO_EARTH_G_CM3 * mass / (rade**3)
        ok = np.isfinite(rade) & np.isfinite(dens)
        ax.scatter(rade[ok], dens[ok], s=3, color=colour, alpha=0.05, linewidths=0)
        mx, my = float(np.nanmedian(rade[ok])), float(np.nanmedian(dens[ok]))
        ax.scatter([mx], [my], s=30, color=colour, edgecolors="white", linewidths=0.6, zorder=5)
        medians.append((mx, my, r["pl_name"], colour))
        rade_bounds.append((float(np.percentile(rade[ok], 1)), float(np.percentile(rade[ok], 99))))

    # Size the x-axis to the candidates actually plotted rather than a fixed
    # guess: the current top-ranked set happens to cluster within ~1.0-1.2
    # R_Earth, and a wide fixed range compresses every cloud into an
    # unreadable sliver against empty axis. A generous 35% pad on each side
    # keeps the clouds legible while still framing Earth (1 R_Earth) as the
    # reference point even if every candidate sits to one side of it.
    data_lo = min(lo for lo, _ in rade_bounds + [(1.0, 1.0)])
    data_hi = max(hi for _, hi in rade_bounds + [(1.0, 1.0)])
    pad = (data_hi - data_lo) * 0.35
    x_lo, x_hi = max(0.0, data_lo - pad), data_hi + pad

    # The medians cluster tightly in radius (most top candidates ARE close to
    # 1 R_Earth), so inline offset labels collide. Instead, label slots are
    # spread evenly along the top margin, ordered left-to-right by radius, with
    # a thin leader line back to each point -- the same device used for the
    # Solar System labels in the HZ diagram, for the same reason.
    medians.sort(key=lambda t: t[0])
    y_top = 11.4
    for i, (mx, my, name, colour) in enumerate(medians):
        lx = x_lo + (i + 0.5) * (x_hi - x_lo) / len(medians)
        ly = y_top - (i % 2) * 0.55
        ax.plot([mx, lx], [my, ly], color=colour, lw=0.6, alpha=0.6, zorder=4)
        ax.annotate(name, (lx, ly), fontsize=8, color=tuple(colour[:3]) + (1.0,),
                    weight="600", ha="center", va="bottom")

    ax.scatter([1.0], [5.514], s=90, marker="*", c=EARTH, edgecolors="white",
              linewidths=0.8, zorder=6)
    ax.annotate("Earth", (1.0, 5.514), textcoords="offset points", xytext=(8, -4),
                fontsize=9, color=EARTH, weight="600")

    ax.set_xlabel(r"Planet radius  [R$_\oplus$]")
    ax.set_ylabel(r"Bulk density  [g cm$^{-3}$]")
    _title(ax, "Monte Carlo posterior clouds: propagated uncertainty for the top candidates")
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(0, 12)
    _source_note(ax, "NASA Exoplanet Archive | earth2 Monte Carlo (%d draws/planet)" % n_samples)
    fig.savefig(out); plt.close(fig)
    return out


FIGURE_FUNCTIONS: dict[str, Callable[[pd.DataFrame, Path], Path]] = {
    "mass_radius": fig_mass_radius,
    "flux_radius_hz": fig_flux_radius_hz,
    "hr_diagram": fig_hr_diagram,
    "discovery_timeline": fig_discovery_timeline,
    "ranking_distribution": fig_ranking_distribution,
    "top_candidates": fig_top_candidates,
    "hz_diagram": fig_hz_diagram,
    "uncertainty": fig_uncertainty,
    "period_radius": fig_period_radius,
    "equilibrium_temperature": fig_equilibrium_temperature,
    "distance_distribution": fig_distance_distribution,
    "evidence_matrix": fig_evidence_matrix,
    "posterior_clouds": fig_posterior_clouds,
    "gaia_parallax_check": fig_gaia_parallax_check,
}


def generate_all(
    ranking: pd.DataFrame,
    coverage: pd.DataFrame,
    out_dir: Path,
    transitspec: pd.DataFrame | None = None,
    verbose: bool = True,
) -> list[Path]:
    """Draw every figure. A failure in one does not stop the rest."""
    apply_style()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for name, fn in FIGURE_FUNCTIONS.items():
        target = out_dir / (name + ".png")
        try:
            fn(ranking, target)
            written.append(target)
            if verbose:
                print(f"    [fig] {target.name}")
        except Exception as exc:  # noqa: BLE001
            if verbose:
                print(f"    [fig] FAILED {name}: {str(exc)[:140]}")

    try:
        p = fig_data_coverage(coverage, out_dir / "data_coverage.png")
        written.append(p)
        if verbose:
            print("    [fig] data_coverage.png")
    except Exception as exc:  # noqa: BLE001
        if verbose:
            print(f"    [fig] FAILED data_coverage: {str(exc)[:140]}")

    if transitspec is not None and not transitspec.empty:
        from earth2.spectroscopy import planet_spectrum, spectrum_inventory

        inv = spectrum_inventory(transitspec, None, min_points=20)
        inv = inv[inv["kind"] == "transmission"]
        if not inv.empty:
            best = str(inv.iloc[0]["pl_name"])
            spec = planet_spectrum(transitspec, best)
            if spec is None:
                # spectrum_inventory already required >=20 usable points for
                # `best` to appear here, so this should not happen -- but
                # planet_spectrum has its own (looser) filtering, and a caller
                # must not assume the two always agree.
                if verbose:
                    print(f"    [fig] FAILED spectrum: no usable points for {best}")
            else:
                try:
                    spec_path = fig_spectrum(spec, out_dir / "transmission_spectrum.png")
                    if spec_path:
                        written.append(spec_path)
                        if verbose:
                            print(f"    [fig] transmission_spectrum.png ({best})")
                except Exception as exc:  # noqa: BLE001
                    if verbose:
                        print(f"    [fig] FAILED spectrum: {str(exc)[:140]}")

    return written
