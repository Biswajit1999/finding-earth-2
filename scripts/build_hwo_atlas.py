"""Build the HPIC v1.1 atlas and catalog-conditioned imaging forecasts."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from earth2.constants import AU_M, R_EARTH_M  # noqa: E402
from earth2.habitability.hz import hz_distance_au  # noqa: E402
from earth2.missions.hwo import (  # noqa: E402
    CoronagraphScenario,
    deproject_minimum_mass,
    lambert_phase,
    orbital_geometry,
)

DRAW_COUNT = 512
EARTH_RADIUS_AU = R_EARTH_M / AU_M
IDENTIFIER_DTYPES = {
    "star_name": "string",
    "tic_id": "string",
    "gaia_dr2_id": "string",
    "gaia_dr3_id": "string",
    "hip_name": "string",
    "tm_name": "string",
    "tyc_name": "string",
    "wds_designation": "string",
    "simbad_name": "string",
    "hostname": "string",
}
SCENARIOS = (
    CoronagraphScenario("analytic_6m_500nm_3lambda_d", 6.0, 500.0, 3.0, 1e-10),
    CoronagraphScenario("analytic_8m_500nm_3lambda_d", 8.0, 500.0, 3.0, 1e-10),
    CoronagraphScenario("analytic_6m_750nm_3lambda_d", 6.0, 750.0, 3.0, 1e-10),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_rng(namespace: str, identity: str) -> np.random.Generator:
    payload = f"finding-earth-2|{namespace}|{identity}".encode()
    seed = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return np.random.default_rng(seed)


def numeric(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def quantiles(values: np.ndarray) -> tuple[float, float, float]:
    p16, p50, p84 = np.quantile(values[np.isfinite(values)], [0.16, 0.5, 0.84])
    return float(p16), float(p50), float(p84)


def split_normal_draws(
    rng: np.random.Generator,
    centre: float,
    error_minus: float | None,
    error_plus: float | None,
    *,
    lower: float,
    upper: float,
) -> np.ndarray:
    lower_sigma = abs(error_minus) if error_minus is not None and error_minus != 0 else 0.0
    upper_sigma = abs(error_plus) if error_plus is not None and error_plus != 0 else 0.0
    if lower_sigma == 0 and upper_sigma == 0:
        return np.full(DRAW_COUNT, np.clip(centre, lower, upper))
    if lower_sigma == 0:
        lower_sigma = upper_sigma
    if upper_sigma == 0:
        upper_sigma = lower_sigma
    standard = rng.normal(size=DRAW_COUNT)
    sigma = np.where(standard < 0, lower_sigma, upper_sigma)
    return np.clip(centre + standard * sigma, lower, upper)


def source_contract() -> tuple[dict[str, Any], Path, Path]:
    manifest_path = ROOT / "data/manifests/hwo_hpic.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_id = {dataset["dataset_id"]: dataset for dataset in manifest["datasets"]}
    hpic_path = ROOT / by_id["hpic_v1p1"]["table_path"]
    tss_path = ROOT / by_id["tss25_2025"]["table_path"]
    for dataset, path in ((by_id["hpic_v1p1"], hpic_path), (by_id["tss25_2025"], tss_path)):
        if not path.exists():
            raise FileNotFoundError(f"missing pinned HWO input: {path}")
        if path.stat().st_size != dataset["table_bytes"] or sha256(path) != dataset["table_sha256"]:
            raise RuntimeError(f"pinned HWO input failed size/hash contract: {path}")
    return manifest, hpic_path, tss_path


def load_catalogues(hpic_path: Path, tss_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    hpic = pd.read_csv(
        hpic_path,
        sep="|",
        na_values=["null", "’null’"],
        dtype=IDENTIFIER_DTYPES,
        low_memory=False,
    )
    tss = pd.read_csv(
        tss_path,
        na_values=["null", "’null’"],
        dtype={
            key: value
            for key, value in IDENTIFIER_DTYPES.items()
            if key in pd.read_csv(tss_path, nrows=0).columns
        },
        low_memory=False,
    )
    if len(hpic) != 12944 or len(tss) != 12944:
        raise RuntimeError("HWO input row count differs from the pinned release")
    if not hpic["star_name"].is_unique or not tss["star_name"].is_unique:
        raise RuntimeError("HWO source identity is not unique")
    if set(hpic["star_name"]) != set(tss["star_name"]):
        raise RuntimeError("TSS25 and HPIC identities do not form the same released star set")
    return hpic, tss


def build_atlas(hpic: pd.DataFrame, tss: pd.DataFrame) -> pd.DataFrame:
    atlas = hpic.merge(
        tss[["star_name", "TSS_tier"]], on="star_name", how="left", validate="one_to_one"
    )
    coordinates = SkyCoord(
        ra=pd.to_numeric(atlas["ra"], errors="coerce").to_numpy() * u.deg,
        dec=pd.to_numeric(atlas["dec"], errors="coerce").to_numpy() * u.deg,
        frame="icrs",
    ).galactic
    atlas["source_label"] = "OBSERVED"
    atlas["derived_geometry_label"] = "DERIVED"
    atlas["hpic_version"] = "1.1"
    atlas["hpic_doi"] = "10.5281/zenodo.17178761"
    atlas["tss25_release"] = "2025-09-24"
    atlas["tss25_doi"] = "10.5281/zenodo.17195128"
    atlas["galactic_l_deg"] = coordinates.l.deg
    atlas["galactic_b_deg"] = coordinates.b.deg
    log_luminosity = pd.to_numeric(atlas["st_lum"], errors="coerce")
    luminosity = 10**log_luminosity
    teff = pd.to_numeric(atlas["st_teff"], errors="coerce")
    distance = pd.to_numeric(atlas["sy_dist"], errors="coerce")
    atlas["luminosity_solar"] = luminosity
    atlas["eeid_au"] = np.sqrt(luminosity.where(luminosity > 0))
    atlas["eeid_angular_mas"] = 1000 * atlas["eeid_au"] / distance.where(distance > 0)
    for boundary in ("runaway_greenhouse", "maximum_greenhouse"):
        orbital_distance = hz_distance_au(
            teff.to_numpy(dtype=float), luminosity.to_numpy(dtype=float), boundary
        )
        atlas[f"hz_{boundary}_au"] = orbital_distance
        atlas[f"hz_{boundary}_mas"] = 1000 * orbital_distance / distance.to_numpy(dtype=float)
    atlas["tss25_membership_interpretation"] = (
        "community precursor-priority tier; not final HWO target selection"
    )
    return atlas


def sampled_orbit_summary(
    *,
    distance: np.ndarray,
    semi_major_axis: np.ndarray,
    eccentricity: np.ndarray,
    inclination: np.ndarray,
    omega: np.ndarray,
    mean_anomaly: np.ndarray,
    radius_earth: np.ndarray,
    albedo: np.ndarray,
) -> dict[str, Any]:
    orbital_radius, projected_au, phase = orbital_geometry(
        semi_major_axis, eccentricity, inclination, omega, mean_anomaly
    )
    separation = 1000 * projected_au / distance
    contrast = (
        albedo * lambert_phase(phase) * (radius_earth * EARTH_RADIUS_AU / orbital_radius) ** 2
    )
    separation_quantiles = quantiles(separation)
    contrast_quantiles = quantiles(contrast)
    probabilities = {}
    for scenario in SCENARIOS:
        limit = scenario.contrast_limit_at(separation)
        accessible = (
            np.isfinite(separation)
            & np.isfinite(contrast)
            & (separation >= scenario.iwa_mas)
            & (contrast >= limit)
        )
        if scenario.owa_mas is not None:
            accessible &= separation <= scenario.owa_mas
        probabilities[scenario.name] = float(np.mean(accessible))
    return {
        "separation_mas_p16": separation_quantiles[0],
        "separation_mas_p50": separation_quantiles[1],
        "separation_mas_p84": separation_quantiles[2],
        "contrast_p16": contrast_quantiles[0],
        "contrast_p50": contrast_quantiles[1],
        "contrast_p84": contrast_quantiles[2],
        "probabilities": probabilities,
    }


def build_exoearth_forecasts(atlas: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for _, row in atlas.iterrows():
        star_name = str(row["star_name"])
        distance = numeric(row.get("sy_dist"))
        distance_error = numeric(row.get("sy_disterr"))
        log_luminosity = numeric(row.get("st_lum"))
        log_luminosity_error = numeric(row.get("st_lumerr"))
        base = {
            "label": "FORECAST",
            "star_name": star_name,
            "gaia_dr3_id": row.get("gaia_dr3_id"),
            "tic_id": row.get("tic_id"),
            "tss25_tier": int(row["TSS_tier"]),
            "catalogue_conditioning": "HPIC_v1.1_distance_and_log_luminosity",
            "planet_hypothesis": "Earth-equivalent-insolation planet; existence not asserted",
            "draws": DRAW_COUNT,
        }
        if distance is None or distance <= 0 or log_luminosity is None:
            for scenario in SCENARIOS:
                records.append(
                    {
                        **base,
                        "scenario": scenario.name,
                        "status": "undetermined_missing_distance_or_luminosity",
                        "iwa_mas": scenario.iwa_mas,
                        "contrast_floor": scenario.contrast_floor,
                        "p_observable": None,
                    }
                )
            continue
        rng = stable_rng("exoearth", star_name)
        log_luminosity_draws = rng.normal(log_luminosity, log_luminosity_error or 0.0, DRAW_COUNT)
        luminosity = 10 ** np.clip(log_luminosity_draws, -8, 8)
        distance_draws = np.clip(
            rng.normal(distance, distance_error or 0.0, DRAW_COUNT), 1e-6, np.inf
        )
        semi_major_axis = np.sqrt(luminosity)
        eccentricity = rng.uniform(0.0, 0.2, DRAW_COUNT)
        inclination = np.arccos(rng.uniform(0.0, 1.0, DRAW_COUNT))
        omega = rng.uniform(0.0, 2 * np.pi, DRAW_COUNT)
        mean_anomaly = rng.uniform(0.0, 2 * np.pi, DRAW_COUNT)
        radius = rng.uniform(0.8, 1.2, DRAW_COUNT)
        albedo = rng.uniform(0.1, 0.4, DRAW_COUNT)
        summary = sampled_orbit_summary(
            distance=distance_draws,
            semi_major_axis=semi_major_axis,
            eccentricity=eccentricity,
            inclination=inclination,
            omega=omega,
            mean_anomaly=mean_anomaly,
            radius_earth=radius,
            albedo=albedo,
        )
        for scenario in SCENARIOS:
            records.append(
                {
                    **base,
                    "scenario": scenario.name,
                    "status": "catalogue_conditioned_scenario_probability",
                    "diameter_m": scenario.diameter_m,
                    "wavelength_nm": scenario.wavelength_nm,
                    "iwa_lambda_over_d": scenario.iwa_lambda_over_d,
                    "iwa_mas": scenario.iwa_mas,
                    "contrast_floor": scenario.contrast_floor,
                    "eeid_au_p50": float(np.median(semi_major_axis)),
                    **{key: value for key, value in summary.items() if key != "probabilities"},
                    "p_observable": summary["probabilities"][scenario.name],
                }
            )
    return pd.DataFrame(records)


def build_known_planet_forecasts(atlas: pd.DataFrame) -> pd.DataFrame:
    analysis = pd.read_parquet(ROOT / "results/analysis_catalogue.parquet")
    hpic_hosts = (
        atlas[atlas["hostname"].notna()]
        .sort_values("star_name")
        .drop_duplicates("hostname")[
            ["star_name", "hostname", "gaia_dr3_id", "tic_id", "TSS_tier", "sy_dist", "sy_disterr"]
        ]
    )
    planets = analysis[~analysis["is_control"].fillna(False)].merge(
        hpic_hosts, on="hostname", how="inner", suffixes=("", "_hpic"), validate="many_to_one"
    )
    records: list[dict[str, Any]] = []
    for _, row in planets.sort_values("pl_name").iterrows():
        planet = str(row["pl_name"])
        distance = numeric(row.get("sy_dist_hpic"))
        semi_major = numeric(row.get("pl_orbsmax"))
        radius = numeric(row.get("pl_rade"))
        base = {
            "label": "FORECAST",
            "pl_name": planet,
            "hostname": row["hostname"],
            "hpic_star_name": row["star_name"],
            "gaia_dr3_id": row.get("gaia_dr3_id_hpic"),
            "tss25_tier": int(row["TSS_tier"]),
            "mass_class": row.get("mass_class"),
            "draws": DRAW_COUNT,
        }
        if (
            distance is None
            or distance <= 0
            or semi_major is None
            or semi_major <= 0
            or radius is None
            or radius <= 0
        ):
            for scenario in SCENARIOS:
                records.append(
                    {
                        **base,
                        "scenario": scenario.name,
                        "status": "undetermined_missing_distance_semimajor_axis_or_radius",
                        "iwa_mas": scenario.iwa_mas,
                        "contrast_floor": scenario.contrast_floor,
                        "p_observable": None,
                    }
                )
            continue
        rng = stable_rng("known_planet", planet)
        distance_draws = split_normal_draws(
            rng,
            distance,
            numeric(row.get("sy_disterr_hpic")),
            numeric(row.get("sy_disterr_hpic")),
            lower=1e-6,
            upper=np.inf,
        )
        semi_major_draws = split_normal_draws(
            rng,
            semi_major,
            numeric(row.get("pl_orbsmaxerr2")),
            numeric(row.get("pl_orbsmaxerr1")),
            lower=1e-6,
            upper=np.inf,
        )
        radius_draws = split_normal_draws(
            rng,
            radius,
            numeric(row.get("pl_radeerr2")),
            numeric(row.get("pl_radeerr1")),
            lower=0.01,
            upper=30.0,
        )
        eccentricity_value = numeric(row.get("pl_orbeccen"))
        if eccentricity_value is None:
            eccentricity = rng.uniform(0.0, 0.2, DRAW_COUNT)
            eccentricity_treatment = "SCENARIO_uniform_0_0.2_missing_catalogue_eccentricity"
        else:
            eccentricity = split_normal_draws(
                rng,
                eccentricity_value,
                numeric(row.get("pl_orbeccenerr2")),
                numeric(row.get("pl_orbeccenerr1")),
                lower=0.0,
                upper=0.95,
            )
            eccentricity_treatment = "catalogue_value_with_asymmetric_uncertainty_when_available"
        inclination_value = numeric(row.get("pl_orbincl"))
        if inclination_value is None:
            inclination = np.arccos(rng.uniform(0.0, 1.0, DRAW_COUNT))
            inclination_treatment = "SCENARIO_isotropic_missing_catalogue_inclination"
        else:
            inclination_degrees = split_normal_draws(
                rng,
                inclination_value,
                numeric(row.get("pl_orbinclerr2")),
                numeric(row.get("pl_orbinclerr1")),
                lower=0.01,
                upper=179.99,
            )
            inclination = np.deg2rad(inclination_degrees)
            inclination_treatment = "catalogue_value_with_asymmetric_uncertainty_when_available"
        omega = rng.uniform(0.0, 2 * np.pi, DRAW_COUNT)
        mean_anomaly = rng.uniform(0.0, 2 * np.pi, DRAW_COUNT)
        albedo = rng.uniform(0.1, 0.4, DRAW_COUNT)
        summary = sampled_orbit_summary(
            distance=distance_draws,
            semi_major_axis=semi_major_draws,
            eccentricity=eccentricity,
            inclination=inclination,
            omega=omega,
            mean_anomaly=mean_anomaly,
            radius_earth=radius_draws,
            albedo=albedo,
        )
        mass_summary: dict[str, Any] = {
            "minimum_mass_earth": None,
            "true_mass_scenario_p16": None,
            "true_mass_scenario_p50": None,
            "true_mass_scenario_p84": None,
            "mass_inclination_treatment": "not_applicable",
        }
        minimum_mass = numeric(row.get("pl_bmasse"))
        if row.get("mass_class") == "msini_lower_limit" and minimum_mass is not None:
            true_mass = deproject_minimum_mass(minimum_mass, inclination)
            mass_p16, mass_p50, mass_p84 = quantiles(true_mass)
            mass_summary = {
                "minimum_mass_earth": minimum_mass,
                "true_mass_scenario_p16": mass_p16,
                "true_mass_scenario_p50": mass_p50,
                "true_mass_scenario_p84": mass_p84,
                "mass_inclination_treatment": (
                    "M_sin_i retained; true-mass distribution uses the same inclination draws"
                ),
            }
        for scenario in SCENARIOS:
            records.append(
                {
                    **base,
                    "scenario": scenario.name,
                    "status": "catalogue_conditioned_scenario_probability",
                    "diameter_m": scenario.diameter_m,
                    "wavelength_nm": scenario.wavelength_nm,
                    "iwa_lambda_over_d": scenario.iwa_lambda_over_d,
                    "iwa_mas": scenario.iwa_mas,
                    "contrast_floor": scenario.contrast_floor,
                    "geometric_albedo_prior": "SCENARIO_uniform_0.1_0.4",
                    "argument_periapsis_treatment": "SCENARIO_uniform_0_2pi_not_in_source",
                    "mean_anomaly_treatment": "SCENARIO_uniform_0_2pi_unknown_epoch",
                    "eccentricity_treatment": eccentricity_treatment,
                    "inclination_treatment": inclination_treatment,
                    **mass_summary,
                    **{key: value for key, value in summary.items() if key != "probabilities"},
                    "p_observable": summary["probabilities"][scenario.name],
                }
            )
    return pd.DataFrame(records)


def make_figure(atlas: pd.DataFrame, output: Path) -> None:
    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-hwo-atlas-v1"
    figure = plt.figure(figsize=(14, 6.5), constrained_layout=True)
    sky = figure.add_subplot(1, 2, 1, projection="mollweide")
    galactic_longitude = np.deg2rad(
        ((pd.to_numeric(atlas["galactic_l_deg"], errors="coerce") + 180) % 360) - 180
    )
    galactic_latitude = np.deg2rad(pd.to_numeric(atlas["galactic_b_deg"], errors="coerce"))
    sky.scatter(galactic_longitude, galactic_latitude, s=2, c="#68758e", alpha=0.35)
    for tier, color, size in ((2, "#59d9ed", 8), (1, "#ffc95c", 16)):
        selected = atlas["TSS_tier"].eq(tier)
        sky.scatter(
            galactic_longitude[selected],
            galactic_latitude[selected],
            s=size,
            c=color,
            alpha=0.9,
            label=f"TSS25 tier {tier}",
        )
    sky.set_title("12,944 HPIC v1.1 stars | OBSERVED catalogue membership")
    sky.grid(alpha=0.18)
    sky.legend(loc="lower left", fontsize=8)

    scale = figure.add_subplot(1, 2, 2)
    supported = atlas[
        pd.to_numeric(atlas["eeid_angular_mas"], errors="coerce").gt(0)
        & pd.to_numeric(atlas["sy_dist"], errors="coerce").gt(0)
    ]
    scale.scatter(
        supported["sy_dist"],
        supported["eeid_angular_mas"],
        s=3,
        c="#68758e",
        alpha=0.2,
        rasterized=True,
    )
    for tier, color, size in ((2, "#59d9ed", 12), (1, "#ffc95c", 22)):
        selected = supported["TSS_tier"].eq(tier)
        scale.scatter(
            supported.loc[selected, "sy_dist"],
            supported.loc[selected, "eeid_angular_mas"],
            s=size,
            c=color,
            alpha=0.8,
        )
    for scenario, linestyle in zip(SCENARIOS, ("-", "--", ":")):
        scale.axhline(
            scenario.iwa_mas,
            color="#f48fb1",
            linestyle=linestyle,
            linewidth=1.2,
            label=f"{scenario.name}: IWA {scenario.iwa_mas:.1f} mas",
        )
    scale.set(xlabel="HPIC distance [pc]", ylabel="Earth-equivalent-insolation angular scale [mas]")
    scale.set_yscale("log")
    scale.set_xlim(0, 50.5)
    scale.grid(alpha=0.17)
    scale.legend(fontsize=7, loc="upper right")
    scale.set_title("Analytic trade cases | SCENARIO, not a final HWO design")
    figure.suptitle("Habitable Worlds Observatory precursor atlas", fontsize=17)
    figure.savefig(output.with_suffix(".png"), dpi=220, facecolor="#080b14")
    figure.savefig(output.with_suffix(".svg"), facecolor="#080b14", metadata={"Date": None})
    plt.close(figure)
    svg = output.with_suffix(".svg")
    payload = svg.read_bytes().replace(b"\r\n", b"\n")
    normalized = b"\n".join(line.rstrip() for line in payload.split(b"\n")).decode("utf-8")
    clip_ids = re.findall(r'<clipPath id="(p[0-9a-f]+)">', normalized)
    for index, clip_id in enumerate(clip_ids):
        normalized = normalized.replace(clip_id, f"clip_path_{index}")
    with svg.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(normalized)


def write_products(
    source_manifest: dict[str, Any],
    atlas: pd.DataFrame,
    exoearth: pd.DataFrame,
    known_planets: pd.DataFrame,
) -> None:
    output = ROOT / "results/hwo"
    output.mkdir(parents=True, exist_ok=True)
    atlas_path = output / "hpic_v1p1_atlas.csv.gz"
    exoearth_path = output / "exoearth_accessibility.csv.gz"
    planets_path = output / "known_planet_accessibility.csv"
    for frame, path in ((atlas, atlas_path), (exoearth, exoearth_path)):
        frame.to_csv(
            path,
            index=False,
            lineterminator="\n",
            float_format="%.10g",
            compression={"method": "gzip", "compresslevel": 9, "mtime": 0},
        )
    known_planets.to_csv(planets_path, index=False, lineterminator="\n", float_format="%.10g")
    figure = output / "hwo_precursor_atlas"
    make_figure(atlas, figure)
    supported_exoearth = exoearth[
        exoearth["status"].eq("catalogue_conditioned_scenario_probability")
    ]
    supported_planets = known_planets[
        known_planets["status"].eq("catalogue_conditioned_scenario_probability")
    ]
    payload = {
        "schema_version": "1.0",
        "title": "HWO precursor atlas and direct-imaging scenario probabilities",
        "labels": ["OBSERVED", "DERIVED", "SCENARIO", "FORECAST"],
        "claim_boundary": (
            "HPIC/TSS25 are input and priority catalogues. Accessibility is a Monte Carlo "
            "forecast under generic analytic trade cases, not an HWO observation, yield, "
            "flight specification, exo-Earth occurrence result, or target selection."
        ),
        "source_manifest": "data/manifests/hwo_hpic.json",
        "source_manifest_sha256": sha256(ROOT / "data/manifests/hwo_hpic.json"),
        "catalogue": {
            "hpic_version": "1.1",
            "hpic_rows": len(atlas),
            "tss25_tiers": {
                str(int(key)): int(value)
                for key, value in atlas["TSS_tier"].value_counts().sort_index().items()
            },
            "known_planet_host_rows": int(atlas["hostname"].notna().sum()),
            "known_binary_rows": int(atlas["known_binary_fl"].eq(1).sum()),
            "gaia_binary_rows": int(atlas["gaia_binary_fl"].eq(1).sum()),
            "eeid_supported": int(atlas["eeid_angular_mas"].notna().sum()),
            "kopparapu_hz_supported": int(atlas["hz_runaway_greenhouse_mas"].notna().sum()),
        },
        "sampling": {
            "draws_per_target": DRAW_COUNT,
            "stellar_measurements": "Gaussian HPIC distance and log-luminosity errors",
            "exoearth_radius_prior_earth": "uniform[0.8,1.2]",
            "geometric_albedo_prior": "uniform[0.1,0.4]",
            "exoearth_eccentricity_prior": "uniform[0,0.2]",
            "unknown_orientation_prior": "isotropic in cos(inclination)",
            "unknown_argument_periapsis": "uniform[0,2pi]",
            "unknown_mean_anomaly": "uniform[0,2pi]",
        },
        "instrument_scenarios": [
            {
                "label": "SCENARIO",
                "name": scenario.name,
                "diameter_m": scenario.diameter_m,
                "wavelength_nm": scenario.wavelength_nm,
                "iwa_lambda_over_d": scenario.iwa_lambda_over_d,
                "iwa_mas": scenario.iwa_mas,
                "contrast_floor": scenario.contrast_floor,
                "interpretation": "generic analytic trade case; not a final HWO design",
            }
            for scenario in SCENARIOS
        ],
        "exoearth_forecast": {
            "rows": len(exoearth),
            "supported_stars": int(supported_exoearth["star_name"].nunique()),
            "by_scenario": {
                scenario.name: {
                    "mean_p_observable": float(
                        supported_exoearth.loc[
                            supported_exoearth["scenario"].eq(scenario.name), "p_observable"
                        ].mean()
                    ),
                    "stars_p_observable_ge_0p5": int(
                        supported_exoearth.loc[
                            supported_exoearth["scenario"].eq(scenario.name), "p_observable"
                        ]
                        .ge(0.5)
                        .sum()
                    ),
                }
                for scenario in SCENARIOS
            },
        },
        "known_planet_forecast": {
            "matched_planets": int(known_planets["pl_name"].nunique()),
            "matched_hosts": int(known_planets["hostname"].nunique()),
            "supported_planets": int(supported_planets["pl_name"].nunique()),
            "msini_planets_deprojected": int(
                known_planets.loc[
                    known_planets["mass_class"].eq("msini_lower_limit"), "pl_name"
                ].nunique()
            ),
        },
        "files": {
            "atlas": atlas_path.relative_to(ROOT).as_posix(),
            "exoearth_forecast": exoearth_path.relative_to(ROOT).as_posix(),
            "known_planet_forecast": planets_path.relative_to(ROOT).as_posix(),
        },
    }
    summary_path = output / "hwo_precursor_atlas.json"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    product_paths = [
        atlas_path,
        exoearth_path,
        planets_path,
        summary_path,
        figure.with_suffix(".png"),
        figure.with_suffix(".svg"),
    ]
    manifest = {
        "schema_version": "1.0",
        "product": "Phase 10 HWO precursor atlas and direct-imaging physics",
        "files": {
            path.relative_to(ROOT).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in product_paths
        },
    }
    (output / "hwo_products.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    manifest, hpic_path, tss_path = source_contract()
    hpic, tss = load_catalogues(hpic_path, tss_path)
    atlas = build_atlas(hpic, tss)
    exoearth = build_exoearth_forecasts(atlas)
    known_planets = build_known_planet_forecasts(atlas)
    write_products(manifest, atlas, exoearth, known_planets)
    print(
        "HWO atlas built: "
        f"{len(atlas):,} stars, {exoearth['star_name'].nunique():,} exo-Earth hypotheses, "
        f"{known_planets['pl_name'].nunique():,} matched known planets"
    )


if __name__ == "__main__":
    main()
