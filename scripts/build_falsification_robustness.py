"""Build Phase 13 Solar-System falsification and model-sensitivity products."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {
    "baseline": (0.35, 0.40, 0.25),
    "equal": (1 / 3, 1 / 3, 1 / 3),
    "similarity_emphasis": (0.60, 0.20, 0.20),
    "hz_emphasis": (0.20, 0.60, 0.20),
    "confidence_emphasis": (0.20, 0.20, 0.60),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def solar_controls(ranking: pd.DataFrame, composition: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "pl_name",
        "esi_global",
        "score_earth_similarity",
        "hz_conservative_prob",
        "rocky_plausibility",
        "earth2_index",
    ]
    controls = ranking[ranking["is_control"]][columns].copy()
    comp = composition[composition["is_control"]][
        ["pl_name", "p_rocky_rogers_radius_only", "p_rocky_zeng_fe_si_envelope", "p_rocky_otegi_equal_prior"]
    ]
    controls = controls.merge(comp, on="pl_name", how="left", validate="one_to_one")
    known_surface_outcome = {
        "Earth": "only known inhabited control",
        "Venus": "hostile runaway-greenhouse control",
        "Mars": "cold arid low-pressure control",
        "Mercury": "airless hot/cold control",
        "Jupiter": "gas-giant control",
    }
    controls["known_surface_outcome"] = controls["pl_name"].map(known_surface_outcome)
    controls["falsification_result"] = np.select(
        [controls["pl_name"].eq("Venus"), controls["pl_name"].eq("Earth")],
        [
            "ESI is high despite a hostile surface; similarity cannot establish habitability",
            "Earth reference is recovered by similarity, HZ, and supported rocky models",
        ],
        default="control exposes model scope or unsupported composition domain",
    )
    controls.insert(0, "label", "OBSERVED_CONTROL_WITH_DERIVED_MODEL_OUTPUTS")
    return controls


def robustness(
    ranking: pd.DataFrame,
    climate: pd.DataFrame,
    composition: pd.DataFrame,
    hwo: pd.DataFrame,
    atmosphere: pd.DataFrame,
) -> pd.DataFrame:
    planets = ranking[~ranking["is_control"]].copy()
    for name, (w_esi, w_hz, w_conf) in WEIGHTS.items():
        planets[f"weight_{name}"] = (
            w_esi * planets["score_earth_similarity"]
            + w_hz * planets["score_conservative_habitability"]
            + w_conf * planets["score_observational_confidence"]
        )
        planets[f"rank_{name}"] = planets[f"weight_{name}"].rank(
            ascending=False, method="min", na_option="bottom"
        )
    selected = planets.sort_values("earth2_rank").head(25).copy()
    rank_columns = [f"rank_{name}" for name in WEIGHTS]
    selected["legacy_rank_min"] = selected[rank_columns].min(axis=1)
    selected["legacy_rank_max"] = selected[rank_columns].max(axis=1)
    selected["legacy_rank_span"] = selected["legacy_rank_max"] - selected["legacy_rank_min"]
    result = selected[["pl_name", "earth2_rank", "legacy_rank_min", "legacy_rank_max", "legacy_rank_span"]]

    hz_columns = [column for column in climate if column.endswith("__p_current_hz")]
    hz = climate[["pl_name", "status", *hz_columns]].copy()
    hz["hz_model_probability_min"] = hz[hz_columns].min(axis=1)
    hz["hz_model_probability_max"] = hz[hz_columns].max(axis=1)
    hz["hz_model_probability_range"] = hz["hz_model_probability_max"] - hz["hz_model_probability_min"]
    result = result.merge(
        hz[["pl_name", "status", "hz_model_probability_min", "hz_model_probability_max", "hz_model_probability_range"]],
        on="pl_name",
        how="left",
    ).rename(columns={"status": "climate_status"})
    result = result.merge(
        composition[["pl_name", "p_rocky_model_min", "p_rocky_model_max", "p_rocky_model_range"]],
        on="pl_name",
        how="left",
    )
    hwo_ranges = hwo.groupby("pl_name", as_index=False)["p_observable"].agg(["min", "max"]).reset_index()
    hwo_ranges["hwo_accessibility_range"] = hwo_ranges["max"] - hwo_ranges["min"]
    result = result.merge(hwo_ranges, on="pl_name", how="left").rename(
        columns={"min": "hwo_accessibility_min", "max": "hwo_accessibility_max"}
    )
    atmosphere = atmosphere[["pl_name", "hydrogen_to_earth_air_signal_ratio"]]
    result = result.merge(atmosphere, on="pl_name", how="left")
    result.insert(0, "label", "MODEL-SENSITIVITY")
    return result


def make_figure(controls: pd.DataFrame, robust: pd.DataFrame, output: Path) -> None:
    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-falsification-v1"
    figure, axes = plt.subplots(1, 2, figsize=(14, 6.5), constrained_layout=True)
    figure.patch.set_facecolor("#080b14")
    for axis in axes:
        axis.set_facecolor("#080b14")
    x = np.arange(len(controls))
    axes[0].bar(x - 0.18, controls["esi_global"], 0.36, label="ESI", color="#52d3e1")
    axes[0].bar(x + 0.18, controls["hz_conservative_prob"], 0.36, label="HZ probability", color="#ffd166")
    axes[0].set_xticks(x, controls["pl_name"])
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title("Solar-System controls expose metric limits")
    axes[0].legend()
    display = robust.sort_values("legacy_rank_span").tail(15)
    y = np.arange(len(display))
    axes[1].barh(y, display["legacy_rank_span"], color="#c084fc")
    axes[1].set_yticks(y, display["pl_name"])
    axes[1].set_xlabel("rank span across five declared legacy-weight scenarios")
    axes[1].set_title("Candidate ordering is assumption-sensitive")
    figure.suptitle("How Finding Earth 2.0 can be wrong | CONTROL + MODEL-SENSITIVITY")
    figure.savefig(output.with_suffix(".png"), dpi=220, facecolor="#080b14")
    svg_path = output.with_suffix(".svg")
    figure.savefig(svg_path, facecolor="#080b14", metadata={"Date": None})
    # Matplotlib writes platform newlines into SVG text. Canonicalize them before
    # recording byte sizes and hashes so Git's LF normalization cannot invalidate
    # the committed product manifest on Linux checkouts.
    svg_text = svg_path.read_text(encoding="utf-8")
    with svg_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(svg_text.replace("\r\n", "\n").replace("\r", "\n"))
    plt.close(figure)


def main() -> None:
    paths = {
        "ranking": ROOT / "results/candidate_ranking.parquet",
        "climate": ROOT / "results/climate/continuous_hz.csv",
        "composition": ROOT / "results/composition/bulk_composition_ensemble.csv",
        "hwo": ROOT / "results/hwo/known_planet_accessibility.csv",
        "atmosphere": ROOT / "results/atmosphere/observability_scenarios.csv",
    }
    ranking = pd.read_parquet(paths["ranking"])
    climate = pd.read_csv(paths["climate"])
    composition = pd.read_csv(paths["composition"])
    hwo = pd.read_csv(paths["hwo"])
    atmosphere = pd.read_csv(paths["atmosphere"])
    controls = solar_controls(ranking, composition)
    robust = robustness(ranking, climate, composition, hwo, atmosphere)
    output = ROOT / "results/falsification"
    output.mkdir(parents=True, exist_ok=True)
    controls_path = output / "solar_system_controls.csv"
    robust_path = output / "candidate_model_sensitivity.csv"
    summary_path = output / "falsification_summary.json"
    figure_path = output / "falsification_and_robustness"
    controls.to_csv(controls_path, index=False, lineterminator="\n", float_format="%.10g")
    robust.to_csv(robust_path, index=False, lineterminator="\n", float_format="%.10g")
    make_figure(controls, robust, figure_path)
    venus = controls.set_index("pl_name").loc["Venus"]
    write_json(
        summary_path,
        {
            "schema_version": "1.0",
            "labels": ["OBSERVED_CONTROL_WITH_DERIVED_MODEL_OUTPUTS", "MODEL-SENSITIVITY"],
            "control_count": len(controls),
            "candidate_count": len(robust),
            "venus_esi": float(venus["esi_global"]),
            "venus_conservative_hz_probability": float(venus["hz_conservative_prob"]),
            "venus_falsification": str(venus["falsification_result"]),
            "legacy_weight_scenarios": WEIGHTS,
            "source_hashes": {path.relative_to(ROOT).as_posix(): sha256(path) for path in paths.values()},
            "claim_boundary": "Controls test model behaviour; they do not calibrate a probability of habitability. Sensitivity ranges measure dependence on the implemented model menu, not all plausible models.",
        },
    )
    files = [controls_path, robust_path, summary_path, figure_path.with_suffix(".png"), figure_path.with_suffix(".svg")]
    write_json(
        output / "falsification_products.json",
        {"schema_version": "1.0", "product": "Phase 13 falsification and robustness", "files": {path.relative_to(ROOT).as_posix(): {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in files}},
    )
    print(f"Falsification built: {len(controls)} controls, {len(robust)} candidate sensitivity rows")


if __name__ == "__main__":
    main()
