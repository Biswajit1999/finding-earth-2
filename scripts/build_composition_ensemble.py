"""Build the Phase 6 probabilistic bulk-composition evidence products."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from earth2.composition import (  # noqa: E402
    CompositionConfig,
    infer_bulk_composition,
    otegi_mass,
    zeng_rocky_radius,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_seed(name: str, base: int) -> int:
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return base ^ int.from_bytes(digest[:4], "little")


def optional_number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")


def normalize_text_lf(path: Path) -> None:
    payload = path.read_bytes().replace(b"\r\n", b"\n")
    normalized = b"\n".join(line.rstrip() for line in payload.split(b"\n"))
    if normalized != payload:
        path.write_bytes(normalized)


def build_records(catalogue: pd.DataFrame, draws: int, seed: int) -> pd.DataFrame:
    radius = pd.to_numeric(catalogue["pl_rade"], errors="coerce")
    selected = catalogue.loc[radius.between(0.5, 4.0)].copy()
    records: list[dict[str, object]] = []
    correlation_column = (
        "mass_radius_correlation" if "mass_radius_correlation" in selected.columns else None
    )
    for _, row in selected.iterrows():
        name = str(row["pl_name"])
        mass_class = str(row.get("mass_class", "missing"))
        independent_mass = mass_class == "measured"
        correlation = (
            optional_number(row.get(correlation_column)) if correlation_column else None
        )
        model = infer_bulk_composition(
            radius_earth=float(row["pl_rade"]),
            radius_error_minus=optional_number(row.get("pl_radeerr2")),
            radius_error_plus=optional_number(row.get("pl_radeerr1")),
            mass_earth=optional_number(row.get("pl_bmasse")),
            mass_error_minus=optional_number(row.get("pl_bmasseerr2")),
            mass_error_plus=optional_number(row.get("pl_bmasseerr1")),
            independent_mass=independent_mass,
            mass_radius_correlation=correlation,
            config=CompositionConfig(
                draws=draws,
                seed=stable_seed(name, seed),
            ),
        )
        records.append(
            {
                "pl_name": name,
                "hostname": str(row.get("hostname", "")),
                "is_control": bool(row.get("is_control", False)),
                "radius_earth": float(row["pl_rade"]),
                "radius_error_plus": optional_number(row.get("pl_radeerr1")),
                "radius_error_minus": optional_number(row.get("pl_radeerr2")),
                "catalogue_mass_value_earth": optional_number(row.get("pl_bmasse")),
                "catalogue_mass_class": mass_class,
                "catalogue_mass_accepted_as_independent": independent_mass,
                "mass_use_reason": (
                    "catalogue class is an independent measured mass"
                    if independent_mass
                    else "mass excluded: only true measured masses support composition inference"
                ),
                "hz_conservative_probability": optional_number(
                    row.get("hz_conservative_prob")
                ),
                "earth2_rank": optional_number(row.get("earth2_rank")),
                **model,
            }
        )
    return pd.DataFrame.from_records(records)


def make_figure(records: pd.DataFrame, output_base: Path) -> None:
    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-composition-ensemble"
    figure, axes = plt.subplots(1, 2, figsize=(14.8, 6.8), constrained_layout=True)
    figure.patch.set_facecolor("#080b14")

    measured = records[
        records["catalogue_mass_accepted_as_independent"]
        & records["catalogue_mass_value_earth"].notna()
    ]
    scatter = axes[0].scatter(
        measured["radius_earth"],
        measured["catalogue_mass_value_earth"],
        c=measured["p_requires_volatiles_zeng"].fillna(0.5),
        cmap="magma",
        vmin=0,
        vmax=1,
        s=20,
        alpha=0.72,
        linewidths=0,
    )
    radius_grid = np.geomspace(0.8, 4, 200)
    mass_grid = np.geomspace(1, 8, 160)
    axes[0].plot(
        zeng_rocky_radius(mass_grid, 0.0),
        mass_grid,
        color="#52d3e1",
        label="Zeng CMF=0 rocky ceiling",
    )
    axes[0].plot(
        zeng_rocky_radius(mass_grid, 0.4),
        mass_grid,
        color="#9ee493",
        label="Zeng CMF=0.4",
    )
    axes[0].plot(
        radius_grid,
        otegi_mass(radius_grid, "rocky"),
        color="#ffd166",
        linestyle="--",
        label="Otegi rocky population",
    )
    axes[0].plot(
        radius_grid,
        otegi_mass(radius_grid, "volatile_rich"),
        color="#ef7184",
        linestyle="--",
        label="Otegi volatile-rich population",
    )
    axes[0].set(xscale="log", yscale="log", xlim=(0.5, 4), ylim=(0.3, 120))
    axes[0].set_xlabel("planet radius [Earth radii]")
    axes[0].set_ylabel("planet mass [Earth masses]")
    axes[0].set_title("01  Independent bulk measurements", loc="left")
    axes[0].legend(fontsize=8, loc="upper left")
    axes[0].grid(alpha=0.08, which="both")
    figure.colorbar(
        scatter,
        ax=axes[0],
        label="P(requires volatiles | Zeng Fe-Si envelope)",
        fraction=0.05,
    )

    compared = records[records["n_rocky_models_supported"] >= 3].copy()
    compared = compared.sort_values("p_rocky_model_range", ascending=False).head(16)
    compared = compared.sort_values("p_rocky_model_range")
    y = np.arange(len(compared))
    axes[1].hlines(
        y,
        compared["p_rocky_model_min"],
        compared["p_rocky_model_max"],
        color="#596377",
        linewidth=4,
    )
    axes[1].scatter(
        compared["p_rocky_rogers_radius_only"], y, label="Rogers radius baseline", color="#d7dde8"
    )
    axes[1].scatter(
        compared["p_rocky_zeng_fe_si_envelope"], y, label="Zeng Fe-Si envelope", color="#52d3e1"
    )
    axes[1].scatter(
        compared["p_rocky_otegi_equal_prior"], y, label="Otegi equal-prior", color="#ffd166"
    )
    axes[1].set_yticks(y, compared["pl_name"], fontsize=8)
    axes[1].set_xlim(-0.02, 1.02)
    axes[1].set_xlabel("model-conditional rocky probability")
    axes[1].set_title("02  Largest model disagreements", loc="left")
    axes[1].grid(alpha=0.10, axis="x")
    axes[1].legend(fontsize=8, loc="lower right")
    figure.suptitle(
        "Bulk composition is an ensemble result | MODEL-INFERRED",
        fontsize=15,
    )
    figure.savefig(output_base.with_suffix(".png"), dpi=220, facecolor="#080b14")
    figure.savefig(
        output_base.with_suffix(".svg"),
        facecolor="#080b14",
        metadata={"Date": None},
    )
    plt.close(figure)
    normalize_text_lf(output_base.with_suffix(".svg"))


def main() -> None:
    root = Path.cwd().resolve()
    output = root / "results/composition"
    output.mkdir(parents=True, exist_ok=True)
    source = root / "results/candidate_ranking.parquet"
    draws = 4000
    seed = 20260912
    records = build_records(pd.read_parquet(source), draws, seed)
    csv_path = output / "bulk_composition_ensemble.csv"
    json_path = output / "bulk_composition_ensemble.json"
    figure_base = output / "composition_model_disagreement"
    records.to_csv(csv_path, index=False, lineterminator="\n", float_format="%.10g")
    make_figure(records, figure_base)

    supported = records[records["n_rocky_models_supported"] >= 3]
    summary: dict[str, object] = {
        "schema_version": "1.0",
        "label": "MODEL-INFERRED",
        "title": "Probabilistic bulk-composition evidence ensemble",
        "source": {
            "path": source.relative_to(root).as_posix(),
            "sha256": sha256(source),
        },
        "implementation_sources": {
            "builder": {
                "path": Path(__file__).relative_to(root).as_posix(),
                "sha256": sha256(Path(__file__)),
            },
            "models": {
                "path": "src/earth2/composition/models.py",
                "sha256": sha256(root / "src/earth2/composition/models.py"),
            },
        },
        "sampling": {"draws_per_planet": draws, "base_seed": seed},
        "population": {
            "radius_domain_earth": [0.5, 4.0],
            "planets_with_radius_in_domain": int(len(records)),
            "independent_measured_masses": int(
                records["catalogue_mass_accepted_as_independent"].sum()
            ),
            "zeng_supported": int(records["p_rocky_zeng_fe_si_envelope"].notna().sum()),
            "otegi_supported": int(records["p_rocky_otegi_equal_prior"].notna().sum()),
        },
        "models": {
            "rogers_2015": {
                "role": "radius-only population baseline retained from v1",
                "validity_warning": "mostly short-period Kepler planets; not a universal composition posterior",
            },
            "zeng_sasselov_jacobsen_2016": {
                "role": "two-layer iron-silicate consistency envelope",
                "domain": "1-8 Earth masses; core-mass fraction 0-0.4",
            },
            "otegi_bouchy_helled_2020": {
                "role": "equal-prior comparison of empirical rocky and volatile-rich relations",
                "scatter_floor_dex": 0.20,
                "sensitivity_scatter_floor_dex": [0.10, 0.30],
            },
            "wolfgang_rogers_ford_2016": {
                "role": "radius-to-mass predictive reference only",
                "relation": "M=2.7 R^1.3; intrinsic mass scatter 1.9 Earth masses",
                "warning": "prediction is never relabelled as a dynamical mass",
            },
        },
        "model_disagreement": {
            "median_probability_range_three_model_subset": optional_number(
                supported["p_rocky_model_range"].median()
            ),
            "p90_probability_range_three_model_subset": optional_number(
                supported["p_rocky_model_range"].quantile(0.9)
            ),
            "largest_ranges": [
                {
                    "pl_name": str(row["pl_name"]),
                    "range": float(row["p_rocky_model_range"]),
                }
                for _, row in supported.nlargest(10, "p_rocky_model_range").iterrows()
            ],
        },
        "claim_boundary": (
            "Bulk mass and radius do not identify a unique interior. These model-conditional "
            "probabilities are not probabilities of habitability, surface conditions or life."
        ),
        "records": records.replace({np.nan: None}).to_dict(orient="records"),
    }
    write_json(json_path, summary)
    files = (csv_path, json_path, figure_base.with_suffix(".png"), figure_base.with_suffix(".svg"))
    manifest = {
        "schema_version": "1.0",
        "product": "Phase 6 probabilistic composition evidence ensemble",
        "files": {
            path.relative_to(root).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        },
    }
    write_json(output / "composition_products.json", manifest)
    print(
        f"Composition ensemble built: {len(records):,} radius-supported planets; "
        f"{int(records['catalogue_mass_accepted_as_independent'].sum()):,} independent masses",
        flush=True,
    )


if __name__ == "__main__":
    main()
