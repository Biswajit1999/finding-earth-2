"""Spectroscopy module tests.

harmonise_transit_depths is the most consequential function here: the module's
own docstring notes that every one of WASP-39 b's 1,625 measurements is stored
as a radius ratio rather than a percentage, so reading only `plntransdep`
silently produces an empty spectrum for the best-observed planet in the
table. These tests pin that exact case down, plus the scale-height factor
that separately governs whether a planet's atmosphere even looks observable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from earth2.spectroscopy.spectra import (
    atmospheric_scale_height_km,
    bands_in_range,
    emission_spectrum,
    harmonise_emission_depths,
    harmonise_transit_depths,
    planet_spectrum,
    spectrum_inventory,
    transmission_signal_ppm,
)


def test_bands_in_range_returns_only_species_with_a_band_inside_the_window():
    hits = bands_in_range(1.30, 1.50)
    species = {h["species"] for h in hits}
    assert "H2O" in species  # 1.40 um band
    assert "CH4" in species  # 1.40 um band
    assert "CO2" not in species  # nearest CO2 band (1.60) is outside this window
    for h in hits:
        assert h["status"] == "expected_band_position"


def test_harmonise_transit_depths_uses_radius_ratio_when_percent_is_absent():
    """The WASP-39 b case from the module docstring: every row stores only
    plnratror, never plntransdep. depth_ppm must still be populated."""
    df = pd.DataFrame([
        {"plntname": "WASP-39 b", "plnratror": 0.1456, "plnratrorerr1": 0.001,
         "plnratrorerr2": -0.001, "centralwavelng": 1.4},
    ])
    out = harmonise_transit_depths(df)
    expected_ppm = (0.1456 ** 2) * 1e6
    assert out["depth_ppm"].iloc[0] == pytest.approx(expected_ppm, rel=1e-6)
    assert out["depth_source"].iloc[0] == "plnratror_squared"
    assert not np.isnan(out["depth_ppm_err"].iloc[0])


def test_harmonise_transit_depths_prefers_percent_when_both_present():
    df = pd.DataFrame([
        {"plntname": "X b", "plntransdep": 1.5, "plnratror": 0.05,
         "centralwavelng": 1.0},
    ])
    out = harmonise_transit_depths(df)
    assert out["depth_ppm"].iloc[0] == pytest.approx(1.5 * 1e4)
    assert out["depth_source"].iloc[0] == "plntransdep_percent"


def test_harmonise_transit_depths_marks_missing_when_neither_column_present():
    df = pd.DataFrame([{"plntname": "Y b", "centralwavelng": 2.0}])
    out = harmonise_transit_depths(df)
    assert out["depth_source"].iloc[0] == "missing"
    assert np.isnan(out["depth_ppm"].iloc[0])


def test_harmonise_emission_depths_converts_percent_to_ppm_and_temperature():
    df = pd.DataFrame([
        {
            "plntname": "WASP-33 b",
            "especlipdep": 0.12,
            "especlipdeperr1": 0.01,
            "especlipdeperr2": -0.02,
            "espbritemp": 3100.0,
            "centralwavelng": 4.5,
        }
    ])
    out = harmonise_emission_depths(df)
    assert out["depth_ppm"].iloc[0] == pytest.approx(1200.0)
    assert out["depth_ppm_err"].iloc[0] == pytest.approx(150.0)
    assert out["brightness_temperature_k"].iloc[0] == pytest.approx(3100.0)
    assert out["depth_source"].iloc[0] == "especlipdep_percent"


def test_atmospheric_scale_height_earth_like_is_kilometre_scale():
    h = atmospheric_scale_height_km(teq_k=254.0, mass_earth=1.0, radius_earth=1.0,
                                    mean_molecular_weight_amu=29.0)
    assert 5.0 < h < 12.0  # Earth's real scale height is ~8.5 km


def test_atmospheric_scale_height_h_he_default_overstates_by_an_order_of_magnitude():
    """docs/RESEARCH_NOTES.md: the H/He default (2.3 amu) overstates an Earth
    twin's observability relative to a realistic N2/O2 atmosphere (29 amu) by
    roughly the ratio of molecular weights."""
    h_he = atmospheric_scale_height_km(254.0, 1.0, 1.0, mean_molecular_weight_amu=2.3)
    h_n2 = atmospheric_scale_height_km(254.0, 1.0, 1.0, mean_molecular_weight_amu=29.0)
    ratio = h_he / h_n2
    assert 8.0 < ratio < 15.0


def test_atmospheric_scale_height_nan_for_invalid_inputs():
    assert np.isnan(atmospheric_scale_height_km(float("nan"), 1.0, 1.0))
    assert np.isnan(atmospheric_scale_height_km(254.0, 1.0, 0.0))
    assert np.isnan(atmospheric_scale_height_km(254.0, -1.0, 1.0))


def test_transmission_signal_scales_with_scale_height():
    small = transmission_signal_ppm(1.0, 1.0, scale_height_km=8.5)
    large = transmission_signal_ppm(1.0, 1.0, scale_height_km=85.0)
    assert large == pytest.approx(small * 10.0, rel=1e-9)


def test_transmission_signal_nan_for_non_positive_stellar_radius():
    assert np.isnan(transmission_signal_ppm(1.0, 0.0, 8.5))


def _spectrum_df():
    return pd.DataFrame([
        {"plntname": "WASP-39 b", "plnratror": 0.146, "centralwavelng": 1.1,
         "facility": "JWST", "instrument": "NIRSpec"},
        {"plntname": "WASP-39 b", "plnratror": 0.148, "centralwavelng": 1.4,
         "facility": "JWST", "instrument": "NIRSpec"},
        {"plntname": "WASP-39 b", "plnratror": 0.150, "centralwavelng": 4.3,
         "facility": "JWST", "instrument": "MIRI"},
        {"plntname": "Other b", "plntransdep": 2.0, "centralwavelng": 1.2,
         "facility": "HST", "instrument": "WFC3"},
    ])


def test_planet_spectrum_assembles_sorted_points_for_the_requested_planet():
    spec = planet_spectrum(_spectrum_df(), "WASP-39 b")
    assert spec is not None
    assert spec["n_points"] == 3
    assert spec["wavelength_range_um"] == [1.1, 4.3]
    wavelengths = [p["wavelength_um"] for p in spec["points"]]
    assert wavelengths == sorted(wavelengths)
    assert "CO2" in {b["species"] for b in spec["expected_bands"]}
    assert "not detections" in spec["caveat"] or "not" in spec["caveat"]


def test_planet_spectrum_returns_none_when_planet_not_found():
    assert planet_spectrum(_spectrum_df(), "Nonexistent b") is None


def test_planet_spectrum_returns_none_below_min_points():
    assert planet_spectrum(_spectrum_df(), "Other b", min_points=5) is None


def test_emission_spectrum_keeps_eclipse_geometry_and_source_metadata():
    es = pd.DataFrame([
        {
            "plntname": "WASP-33 b",
            "especlipdep": 0.11,
            "centralwavelng": 1.1,
            "facility": "HST",
            "instrument": "WFC3",
            "plntreflink": (
                "<a href=https://ui.adsabs.harvard.edu/abs/2015ApJ...806..146H/abstract>"
                "Haynes et al. 2015</a>"
            ),
        },
        {
            "plntname": "WASP-33 b",
            "especlipdep": 0.13,
            "centralwavelng": 4.5,
            "facility": "Spitzer",
            "instrument": "IRAC",
        },
    ])
    spec = emission_spectrum(es, "WASP-33 b", min_points=2)
    assert spec is not None
    assert spec["kind"] == "emission"
    assert spec["n_points"] == 2
    assert spec["points"][0]["depth_ppm"] == pytest.approx(1100.0)
    assert spec["references"] == [{
        "label": "Haynes et al. 2015",
        "url": "https://ui.adsabs.harvard.edu/abs/2015ApJ...806..146H/abstract",
    }]


def test_spectrum_inventory_separates_transmission_and_emission_and_filters_by_min_points():
    ts = _spectrum_df()
    es = pd.DataFrame([
        {"plntname": "WASP-39 b", "especlipdep": 100.0, "centralwavelng": 4.5, "facility": "JWST"},
        {"plntname": "WASP-39 b", "especlipdep": 110.0, "centralwavelng": 4.6, "facility": "JWST"},
    ])
    inv = spectrum_inventory(ts, es, min_points=2)
    kinds = set(zip(inv["pl_name"], inv["kind"]))
    assert ("WASP-39 b", "transmission") in kinds
    assert ("WASP-39 b", "emission") in kinds
    # "Other b" has only 1 transmission point, below min_points=2.
    assert ("Other b", "transmission") not in kinds


def test_spectrum_inventory_empty_inputs_return_empty_frame():
    out = spectrum_inventory(None, None)
    assert out.empty
