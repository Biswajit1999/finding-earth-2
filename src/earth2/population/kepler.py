"""Strict DR25 INJ1 products and empirical experiment diagnostics.

An injection-conditioned recovery grid is not a population selection surface.
The actual injection proposal depends on stellar properties and MES. No real
occurrence inference is exported by this module.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from astropy import constants as c
from astropy.io import ascii

from earth2.population.completeness import binomial_efficiency

INJECTION_COLUMNS = {
    "KIC_ID",
    "i_period",
    "i_ror",
    "i_b",
    "i_dor",
    "Expected_MES",
    "Recovered",
    "TCE_ID",
    "EB_injection",
    "Offset_from_source",
    "N_Transit",
}
VETTING_COLUMNS = {"TCE_ID", "KIC", "Disp", "Score"}
STELLAR_COLUMNS = (
    "kepid",
    "teff",
    "teff_err1",
    "teff_err2",
    "logg",
    "mass",
    "radius",
    "radius_err1",
    "radius_err2",
    "feh",
    "dutycycle",
    "dataspan",
    "rrmscdpp06p0",
    "mesthres06p0",
    "cdppslplong",
    "cdppslpshrt",
    "st_delivname",
)


def require_columns(frame: pd.DataFrame, required: set[str]) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Archive schema drift: missing {sorted(missing)}")


def parse_ipac(payload: bytes, *, kind: str) -> pd.DataFrame:
    text = payload.decode("utf-8")
    if kind not in {"injections", "vetting"}:
        raise ValueError("Unsupported DR25 product kind")
    if not re.search(r"\\runtype\s*=\s*INJ1\b", text):
        raise ValueError("Expected the on-target INJ1 experiment")
    frame = ascii.read(text, format="ipac", guess=False).to_pandas()
    require_columns(frame, INJECTION_COLUMNS if kind == "injections" else VETTING_COLUMNS)
    declared = re.search(r"\\nrows\s*=\s*(\d+)", text)
    if declared and int(declared.group(1)) != len(frame):
        raise ValueError("Truncated or changed product: declared row count does not match")
    key = "KIC_ID" if kind == "injections" else "TCE_ID"
    if frame[key].isna().any() or frame[key].duplicated().any():
        raise ValueError(f"Missing or duplicate {key}")
    if kind == "injections":
        # The delivered table also contains code 2. These signals have matched
        # TCEs in the official recovery/vetting set; preserve the raw flag and
        # audit them separately rather than claiming correct-period recovery.
        if not frame["Recovered"].isin([0, 1, 2]).all():
            raise ValueError("Invalid recovered flag")
        if not (frame["EB_injection"].eq(0) & frame["Offset_from_source"].eq(0)).all():
            raise ValueError("INJ1 cannot contain off-target or binary injections")
        if frame.loc[frame["Recovered"].gt(0), "TCE_ID"].isna().any():
            raise ValueError("Recovered injection missing its TCE identifier")
    elif not frame["Disp"].isin(["PC", "FP"]).all():
        raise ValueError("Unknown Robovetter disposition")
    return frame


def parse_stars(payload: bytes) -> pd.DataFrame:
    stars = pd.read_csv(io.BytesIO(payload))
    require_columns(stars, set(STELLAR_COLUMNS))
    if stars["kepid"].isna().any() or stars["kepid"].duplicated().any():
        raise ValueError("Missing or duplicate target identifiers")
    if not stars["st_delivname"].eq("q1_q17_dr25_stellar").all():
        raise ValueError("Unexpected stellar release: do not mix injection radius conventions")
    return stars


def normalise_tce(value) -> str | None:
    if pd.isna(value):
        return None
    match = re.fullmatch(r"\s*(\d+)-(\d+)\s*", str(value))
    if not match:
        raise ValueError(f"Invalid TCE identifier: {value}")
    return f"{int(match[1]):09d}-{int(match[2]):02d}"


@dataclass(frozen=True)
class StellarSelection:
    teff_min: float = 4800.0
    teff_max: float = 6300.0
    logg_min: float = 4.0
    radius_max_solar: float = 1.5

    def select(self, stars: pd.DataFrame) -> pd.Series:
        if (
            not np.isfinite(
                [self.teff_min, self.teff_max, self.logg_min, self.radius_max_solar]
            ).all()
            or not 0 < self.teff_min < self.teff_max
            or self.radius_max_solar <= 0
        ):
            raise ValueError("Invalid stellar selection")
        finite = np.isfinite(
            stars[
                [
                    "teff",
                    "logg",
                    "radius",
                    "mass",
                    "dataspan",
                    "dutycycle",
                    "rrmscdpp06p0",
                    "mesthres06p0",
                ]
            ].to_numpy(float)
        ).all(axis=1)
        return (
            finite
            & stars["teff"].between(self.teff_min, self.teff_max)
            & stars["logg"].ge(self.logg_min)
            & stars["radius"].between(0, self.radius_max_solar, inclusive="right")
            & stars["mass"].gt(0)
            & stars["dataspan"].gt(0)
            & stars["dutycycle"].between(0, 1, inclusive="right")
            & stars["rrmscdpp06p0"].gt(0)
            & stars["mesthres06p0"].gt(0)
        )


def join_injections(
    injections: pd.DataFrame, vetting: pd.DataFrame, stars: pd.DataFrame
) -> pd.DataFrame:
    require_columns(injections, INJECTION_COLUMNS)
    require_columns(vetting, VETTING_COLUMNS)
    require_columns(stars, set(STELLAR_COLUMNS))
    inj = injections.copy()
    vet = vetting.copy()
    inj["tce_key"] = inj["TCE_ID"].map(normalise_tce)
    vet["tce_key"] = vet["TCE_ID"].map(normalise_tce)
    if vet["tce_key"].isna().any() or vet["tce_key"].duplicated().any():
        raise ValueError("Duplicate or missing normalised vetting TCE")
    out = inj.merge(
        vet[["tce_key", "Disp", "KIC"]],
        how="left",
        on="tce_key",
        validate="many_to_one",
        indicator="vetting_join",
    )
    recovered = out["Recovered"].gt(0)
    if out.loc[recovered, "tce_key"].duplicated().any():
        raise ValueError("Multiple injections cannot map to the same recovered TCE")
    if out.loc[recovered, "Disp"].isna().any():
        raise ValueError("Recovered injections have no matching vetting record")
    if not out.loc[recovered, "KIC_ID"].eq(out.loc[recovered, "KIC"]).all():
        raise ValueError("TCE identifier and target KIC disagree")
    out = out.merge(
        stars,
        how="left",
        left_on="KIC_ID",
        right_on="kepid",
        validate="many_to_one",
        indicator="stellar_join",
    )
    # Original DR25 stellar radius gives the injection's physical radius.
    out["injected_radius_earth"] = out["i_ror"] * out["radius"] * (c.R_sun.value / c.R_earth.value)
    out["pipeline_recovered"] = out["Recovered"].gt(0)
    out["recovery_code_2"] = out["Recovered"].eq(2)
    out["vetted_pc"] = out["pipeline_recovered"] & out["Disp"].eq("PC")
    return out


def empirical_grid(joined: pd.DataFrame, radius_edges, period_edges) -> pd.DataFrame:
    """Counts and Jeffreys intervals on injection-conditioned recovery, no extrapolation."""
    re_, pe = np.asarray(radius_edges, float), np.asarray(period_edges, float)
    for edges in (re_, pe):
        if (
            edges.ndim != 1
            or len(edges) < 2
            or not np.isfinite(edges).all()
            or np.any(edges <= 0)
            or np.any(np.diff(edges) <= 0)
        ):
            raise ValueError("Grid edges must be finite, positive and increasing")
    xy = joined[["injected_radius_earth", "i_period"]].to_numpy(float)
    valid = np.isfinite(xy).all(axis=1)
    n = np.histogram2d(xy[valid, 0], xy[valid, 1], bins=[re_, pe])[0]
    recovered = joined["pipeline_recovered"].to_numpy(bool) & valid
    vetted = joined["vetted_pc"].to_numpy(bool) & valid
    k = np.histogram2d(xy[recovered, 0], xy[recovered, 1], bins=[re_, pe])[0]
    v = np.histogram2d(xy[vetted, 0], xy[vetted, 1], bins=[re_, pe])[0]
    pipeline = binomial_efficiency(k, n)
    overall = binomial_efficiency(v, n)
    conditional = binomial_efficiency(v, k)
    rows = []
    for i in range(len(re_) - 1):
        for j in range(len(pe) - 1):
            row = {
                "radius_lower_earth": re_[i],
                "radius_upper_earth": re_[i + 1],
                "period_lower_days": pe[j],
                "period_upper_days": pe[j + 1],
                "n_injected": int(n[i, j]),
                "n_recovered": int(k[i, j]),
                "n_vetted_pc": int(v[i, j]),
                "label": "SIMULATED",
            }
            for name, result in (
                ("pipeline", pipeline),
                ("pipeline_and_vetting", overall),
                ("vetting_given_recovered", conditional),
            ):
                for key in ("mean", "lower", "upper"):
                    row[name + "_" + key] = float(result[key][i, j])
            rows.append(row)
    return pd.DataFrame(rows)
