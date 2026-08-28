"""Generate the title-less figure set embedded in the LaTeX manuscript.

Journal figures get their label from the caption set underneath them by
LaTeX's own \\caption{} mechanism. An in-image title above the same figure
would repeat that label a second time in a different font, which is why every
figure used in ``paper/main.tex`` is drawn here inside :func:`earth2.reporting
.figures.no_titles`, producing a separate set from the titled versions used in
the README and website (where a figure appears with no adjacent caption text
and therefore does need its own title).

Usage::

    python scripts/generate_paper_figures.py

Reads the same ``results/analysis_catalogue.parquet`` the rest of the
reporting pipeline reads; run ``python -m earth2 analyse`` first if it does
not exist yet.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402

from earth2.config import PROCESSED_DIR, RESULTS_DIR, ROOT  # noqa: E402
from earth2.reporting.figures import (  # noqa: E402
    apply_style,
    fig_data_coverage,
    fig_discovery_timeline,
    fig_distance_distribution,
    fig_equilibrium_temperature,
    fig_evidence_matrix,
    fig_flux_radius_hz,
    fig_gaia_parallax_check,
    fig_hr_diagram,
    fig_hz_diagram,
    fig_mass_radius,
    fig_period_radius,
    fig_posterior_clouds,
    fig_ranking_distribution,
    fig_spectrum,
    fig_top_candidates,
    fig_uncertainty,
)
from earth2.spectroscopy import planet_spectrum  # noqa: E402

OUT_DIR = ROOT / "paper" / "figures"

# The research article on the website sits its own caption text under each
# figure exactly as the LaTeX manuscript does, so it needs this same
# title-less set, not the titled versions under results/figures/. Listed
# explicitly (a subset of what this script draws) so the web bundle ships
# only the figures the article actually embeds.
WEB_FIGURES_DIR = ROOT / "web" / "public" / "figures"
WEB_FIGURE_NAMES = (
    "data_coverage.png",
    "discovery_timeline.png",
    "distance_distribution.png",
    "equilibrium_temperature.png",
    "flux_radius_hz.png",
    "hz_diagram.png",
    "hr_diagram.png",
    "mass_radius.png",
    "period_radius.png",
    "posterior_clouds.png",
    "gaia_parallax_check.png",
    "ranking_distribution.png",
    "top_candidates.png",
    "transmission_spectrum.png",
    "uncertainty.png",
    "evidence_matrix.png",
)


def main() -> None:
    apply_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    catalogue_path = RESULTS_DIR / "analysis_catalogue.parquet"
    if not catalogue_path.exists():
        raise SystemExit(
            "No analysis output found. Run `python -m earth2 analyse` first."
        )
    df = pd.read_parquet(catalogue_path)
    coverage_path = RESULTS_DIR / "data_coverage.csv"
    coverage = pd.read_csv(coverage_path) if coverage_path.exists() else None

    # Local import so this module has no import-time dependency on the flag.
    from earth2.reporting import figures as figmod

    with figmod.no_titles():
        if coverage is not None:
            fig_data_coverage(coverage, OUT_DIR / "data_coverage.png")
        fig_discovery_timeline(df, OUT_DIR / "discovery_timeline.png")
        fig_mass_radius(df, OUT_DIR / "mass_radius.png")
        fig_flux_radius_hz(df, OUT_DIR / "flux_radius_hz.png")
        fig_hr_diagram(df, OUT_DIR / "hr_diagram.png")
        fig_hz_diagram(df, OUT_DIR / "hz_diagram.png")
        fig_period_radius(df, OUT_DIR / "period_radius.png")
        fig_equilibrium_temperature(df, OUT_DIR / "equilibrium_temperature.png")
        fig_distance_distribution(df, OUT_DIR / "distance_distribution.png")
        fig_evidence_matrix(df, OUT_DIR / "evidence_matrix.png")
        fig_posterior_clouds(df, OUT_DIR / "posterior_clouds.png")
        fig_gaia_parallax_check(df, OUT_DIR / "gaia_parallax_check.png")
        fig_ranking_distribution(df, OUT_DIR / "ranking_distribution.png")
        fig_top_candidates(df, OUT_DIR / "top_candidates.png")
        fig_uncertainty(df, OUT_DIR / "uncertainty.png")

        transitspec_path = PROCESSED_DIR / "nasa_transitspec.parquet"
        if transitspec_path.exists():
            ts = pd.read_parquet(transitspec_path)
            spec = planet_spectrum(ts, "WASP-39 b")
            if spec:
                fig_spectrum(spec, OUT_DIR / "transmission_spectrum.png")

    print("Wrote title-less figures to %s" % OUT_DIR)
    for p in sorted(OUT_DIR.glob("*.png")):
        print("  %s" % p.name)

    WEB_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    print("Copying the research-article subset to %s" % WEB_FIGURES_DIR)
    for name in WEB_FIGURE_NAMES:
        src = OUT_DIR / name
        if src.exists():
            shutil.copyfile(src, WEB_FIGURES_DIR / name)
            print("  %s" % name)


if __name__ == "__main__":
    main()
