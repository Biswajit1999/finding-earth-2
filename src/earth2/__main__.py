"""Command-line entry point.

    python -m earth2 sync       retrieve every registered archive dataset
    python -m earth2 sync-gaia  cross-match confirmed-planet hosts against Gaia DR3
    python -m earth2 analyse    run the scientific pipeline and write results/
    python -m earth2 figures    draw the publication figures
    python -m earth2 deepdive   build deep-dive analyses for the top candidates
    python -m earth2 export     write browser-ready JSON for the website
    python -m earth2 report     regenerate README statistics from the results
    python -m earth2 all        sync -> analyse -> figures -> deepdive -> export

Each stage is independent and idempotent, reads what the previous stage wrote,
and can be re-run alone.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from earth2 import __version__


def _load_results():
    import pandas as pd

    from earth2.config import RESULTS_DIR

    p = RESULTS_DIR / "analysis_catalogue.parquet"
    if not p.exists():
        raise SystemExit(
            "No analysis output found. Run `python -m earth2 analyse` first."
        )
    ranking = pd.read_parquet(p)
    coverage_p = RESULTS_DIR / "data_coverage.csv"
    coverage = pd.read_csv(coverage_p) if coverage_p.exists() else pd.DataFrame()
    summary_p = RESULTS_DIR / "analysis_summary.json"
    summary = json.loads(summary_p.read_text(encoding="utf-8")) if summary_p.exists() else {}
    return ranking, coverage, summary


def cmd_sync(args: argparse.Namespace) -> int:
    from earth2 import sync

    outcomes = sync.run(only=args.only, force=args.force)
    return 0 if all(o.status == "ok" for o in outcomes) else 1


def cmd_sync_gaia(args: argparse.Namespace) -> int:
    """Cross-match every confirmed-planet host against Gaia DR3 by exact source_id.

    Runs after `sync`, not as part of it: this crossmatch reads the
    gaia_dr3_id column out of the already-synced nasa_pscomppars table rather
    than being an independent per-table archive pull like the rest of
    `dataset_specs()`.
    """
    from earth2.config import PROCESSED_DIR
    from earth2.data_sources.gaia import (
        crossmatch_summary,
        fetch_gaia_crossmatch,
        hosts_with_gaia_ids,
    )

    p = PROCESSED_DIR / "nasa_pscomppars.parquet"
    if not p.exists():
        print("No synced pscomppars table found. Run `python -m earth2 sync` first.")
        return 1

    import pandas as pd

    pscomppars = pd.read_parquet(p)
    hosts = hosts_with_gaia_ids(pscomppars)
    print("Gaia DR3 crossmatch")
    print("=" * 66)
    print(f"  {len(hosts)} of {pscomppars['hostname'].nunique()} host systems have a "
          "gaia_dr3_id recorded by the NASA archive")
    if hosts.empty:
        print("  nothing to cross-match")
        return 0

    gaia, manifest = fetch_gaia_crossmatch(hosts["source_id"].tolist(), use_cache=not args.force)
    # Gaia's own response is keyed by source_id only; attach_gaia_crossmatch
    # joins on hostname downstream, so the hostname<->source_id mapping from
    # hosts_with_gaia_ids() must be carried along here or it is lost entirely.
    gaia = hosts.merge(gaia, on="source_id", how="inner")
    out_path = PROCESSED_DIR / "gaia_dr3_crossmatch.parquet"
    gaia.to_parquet(out_path)
    stats = crossmatch_summary(hosts, gaia)
    print(f"  matched {stats['n_hosts_crossmatched']} hosts "
          f"({manifest.notes.split(' (exact')[0]})")
    print(f"  {stats['n_ruwe_above_1p4']} hosts with RUWE > 1.4 (possible unresolved binary)")
    print(f"  {stats['n_non_single_star_flagged']} hosts flagged non_single_star by Gaia")
    print("-" * 66)
    print(f"  wrote {out_path}")
    return 0


def cmd_analyse(args: argparse.Namespace) -> int:
    from earth2.pipeline import run_analysis

    run_analysis(n_monte_carlo=args.samples, seed=args.seed)
    return 0


def cmd_figures(args: argparse.Namespace) -> int:
    import pandas as pd

    from earth2.config import FIGURES_DIR, PROCESSED_DIR
    from earth2.reporting.figures import generate_all

    ranking, coverage, _ = _load_results()
    ts_path = PROCESSED_DIR / "nasa_transitspec.parquet"
    ts = pd.read_parquet(ts_path) if ts_path.exists() else None

    print("Generating figures")
    print("=" * 66)
    written = generate_all(ranking, coverage, FIGURES_DIR, transitspec=ts)
    print("-" * 66)
    print("  %d figures written to %s" % (len(written), FIGURES_DIR))
    return 0


def cmd_deepdive(args: argparse.Namespace) -> int:
    import pandas as pd

    from earth2.config import PROCESSED_DIR, RESULTS_DIR
    from earth2.reporting.deepdive import build_deep_dive, select_deep_dive_targets

    ranking, _, _ = _load_results()

    def load(name: str):
        p = PROCESSED_DIR / (name + ".parquet")
        return pd.read_parquet(p) if p.exists() else None

    prov_p = RESULTS_DIR / "measurement_provenance.csv.gz"
    provenance = pd.read_csv(prov_p) if prov_p.exists() else None
    ident_p = RESULTS_DIR / "candidate_identifiers.csv"
    identifiers = pd.read_csv(ident_p) if ident_p.exists() else None

    targets = select_deep_dive_targets(ranking, n=args.n)
    print("Deep-dive analysis for %d top-ranked systems" % len(targets))
    print("=" * 66)
    for t in targets:
        print(f"  {t}")

    out_dir = RESULTS_DIR / "deepdive"
    out_dir.mkdir(parents=True, exist_ok=True)
    previous_by_planet = {}
    for existing in out_dir.glob("*.json"):
        try:
            previous = json.loads(existing.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if previous.get("planet"):
            previous_by_planet[str(previous["planet"])] = previous
    # Clear stale per-planet files before writing the current target set: the
    # ranking can reorder between runs (e.g. after a methodology fix), and a
    # planet that drops out of the top N must not leave its old deep-dive JSON
    # behind looking like a still-current result.
    for stale in out_dir.glob("*.json"):
        stale.unlink()
    dives = []
    for t in targets:
        dd = build_deep_dive(
            t, ranking,
            provenance=provenance,
            transitspec=load("nasa_transitspec"),
            emissionspec=load("nasa_emissionspec"),
            identifiers=identifiers,
            run_transit=args.transit,
            run_rv=args.rv,
            previous=previous_by_planet.get(t),
        )
        dives.append(dd)
        slug = t.replace(" ", "_").replace("/", "-")
        from earth2.reporting.jsonio import dump_json

        (out_dir / (slug + ".json")).write_text(dump_json(dd, indent=1), encoding="utf-8")
    print("-" * 66)
    print("  %d deep dives written to %s" % (len(dives), out_dir))
    return 0


def cmd_validate_transit(args: argparse.Namespace) -> int:
    from earth2.config import RESULTS_DIR
    from earth2.transit.validation import write_validation

    ranking, _, _ = _load_results()
    print("Validating the transit pipeline against known planets")
    print("=" * 66)
    p = write_validation(ranking, RESULTS_DIR / "transit_validation.json")
    res = json.loads(p.read_text(encoding="utf-8"))
    for t in res["targets"]:
        print("  %-14s %-18s published %8s ppm  fitted %8s ppm  ratio %5s  %s" % (
            t["planet"], t.get("status", "?"),
            ("{:.0f}".format(t["published_depth_ppm"])) if t.get("published_depth_ppm") else "-",
            ("{:.0f}".format(t["fitted_depth_ppm"])) if t.get("fitted_depth_ppm") else "-",
            ("{:.2f}".format(t["ratio_fitted_to_published"])) if t.get("ratio_fitted_to_published") else "-",
            "VALIDATED" if t.get("validated") else "not validated"))
    print("-" * 66)
    print("  %d of %d attempted targets validated" % (res["n_validated"], res["n_attempted"]))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    import pandas as pd

    from earth2.config import PROCESSED_DIR, RESULTS_DIR, WEB_DATA_DIR
    from earth2.reporting.webexport import export_all
    from earth2.spectroscopy import spectrum_inventory
    from earth2.sync import read_sync_state

    ranking, coverage, summary = _load_results()

    prov_p = RESULTS_DIR / "measurement_provenance.csv.gz"
    provenance = pd.read_csv(prov_p) if prov_p.exists() else None

    def load(name: str):
        p = PROCESSED_DIR / (name + ".parquet")
        return pd.read_parquet(p) if p.exists() else None

    inv = spectrum_inventory(load("nasa_transitspec"), load("nasa_emissionspec"), min_points=4)

    tv_p = RESULTS_DIR / "transit_validation.json"
    transit_validation = json.loads(tv_p.read_text(encoding="utf-8")) if tv_p.exists() else None

    dd_dir = RESULTS_DIR / "deepdive"
    dives = []
    if dd_dir.exists():
        for p in sorted(dd_dir.glob("*.json")):
            dives.append(json.loads(p.read_text(encoding="utf-8")))

    print("Exporting browser-ready data")
    print("=" * 66)
    written = export_all(
        ranking, summary, coverage, WEB_DATA_DIR,
        deep_dives=dives, spectra_inventory=inv, provenance=provenance,
        sync_state=read_sync_state(), transit_validation=transit_validation,
        transitspec=load("nasa_transitspec"),
        emissionspec=load("nasa_emissionspec"),
        spectra_archive_index=load("nasa_spectra_index"),
    )
    total = 0
    for k, p in written.items():
        size = p.stat().st_size
        gz = Path(str(p) + ".gz")
        gz_size = gz.stat().st_size if gz.exists() else 0
        total += gz_size or size
        print("  %-18s %8.1f KB  (gz %6.1f KB)" % (k, size / 1024, gz_size / 1024))
    print("-" * 66)
    print("  %d products, %.1f KB transferred (gzipped)" % (len(written), total / 1024))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from earth2.reporting.readme import write_readme

    path = write_readme()
    print(f"Regenerated {path} from the analysis results.")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    for fn, ns in (
        (cmd_sync, argparse.Namespace(only=None, force=args.force)),
        (cmd_sync_gaia, argparse.Namespace(force=args.force)),
        (cmd_analyse, argparse.Namespace(samples=args.samples, seed=args.seed)),
        (cmd_figures, argparse.Namespace()),
        (cmd_deepdive, argparse.Namespace(n=args.n, transit=args.transit, rv=args.rv)),
        (cmd_validate_transit, argparse.Namespace()),
        (cmd_export, argparse.Namespace()),
        (cmd_report, argparse.Namespace()),
    ):
        print()
        rc = fn(ns)
        if rc != 0 and fn not in (cmd_sync, cmd_sync_gaia):
            return rc
    return 0


def build_parser() -> argparse.ArgumentParser:
    from earth2.config import N_MONTE_CARLO, RANDOM_SEED

    p = argparse.ArgumentParser(
        prog="earth2",
        description="Finding Earth 2.0 -- a reproducible search for potentially "
                    "Earth-like worlds across the public astronomical archives.",
    )
    p.add_argument("--version", action="version", version="earth2 " + __version__)
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("sync", help="retrieve archive datasets")
    s.add_argument("--only", nargs="*", default=None, help="limit to these dataset ids")
    s.add_argument("--force", action="store_true", help="bypass the local cache")
    s.set_defaults(func=cmd_sync)

    g = sub.add_parser("sync-gaia", help="cross-match confirmed-planet hosts against Gaia DR3")
    g.add_argument("--force", action="store_true", help="bypass the local cache")
    g.set_defaults(func=cmd_sync_gaia)

    a = sub.add_parser("analyse", help="run the scientific pipeline")
    a.add_argument("--samples", type=int, default=N_MONTE_CARLO,
                   help="Monte Carlo draws per planet (default %(default)s)")
    a.add_argument("--seed", type=int, default=RANDOM_SEED)
    a.set_defaults(func=cmd_analyse)

    f = sub.add_parser("figures", help="draw publication figures")
    f.set_defaults(func=cmd_figures)

    d = sub.add_parser("deepdive", help="build deep-dive analyses for top candidates")
    d.add_argument("-n", type=int, default=10, help="number of systems (default %(default)s)")
    d.add_argument("--transit", action="store_true", help="fetch and fit MAST light curves")
    d.add_argument("--rv", action="store_true", help="fetch DACE radial velocities")
    d.set_defaults(func=cmd_deepdive)

    v = sub.add_parser("validate-transit",
                       help="run the transit pipeline against planets with known depths")
    v.set_defaults(func=cmd_validate_transit)

    e = sub.add_parser("export", help="write browser-ready JSON")
    e.set_defaults(func=cmd_export)

    r = sub.add_parser("report", help="regenerate the README from results")
    r.set_defaults(func=cmd_report)

    al = sub.add_parser("all", help="run the whole pipeline")
    al.add_argument("--force", action="store_true")
    al.add_argument("--samples", type=int, default=N_MONTE_CARLO)
    al.add_argument("--seed", type=int, default=RANDOM_SEED)
    al.add_argument("-n", type=int, default=10)
    al.add_argument("--transit", action="store_true")
    al.add_argument("--rv", action="store_true")
    al.set_defaults(func=cmd_all)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
