import math

import pytest

from earth2.futures.distance import distance_summary, extragalactic_feasibility


def test_distance_and_relativity_contract() -> None:
    result = distance_summary(10.0, (0.1, 0.9, 0.99))
    assert result["signal_round_trip_years"] == pytest.approx(2 * result["distance_ly"])
    assert result["travel"][0]["earth_frame_years"] == pytest.approx(result["distance_ly"] / 0.1)
    assert result["travel"][2]["gamma"] == pytest.approx(1 / math.sqrt(1 - 0.99**2))
    assert result["travel"][2]["traveller_proper_years"] < result["travel"][2]["earth_frame_years"]


def test_inverse_square_and_resolution_scaling() -> None:
    near = extragalactic_feasibility(10)
    far = extragalactic_feasibility(100)
    assert near["stellar_bolometric_flux_w_m2"] / far["stellar_bolometric_flux_w_m2"] == pytest.approx(100)
    assert far["diffraction_diameter_separate_1au_m"] / near["diffraction_diameter_separate_1au_m"] == pytest.approx(10)
    assert near["earth_quadrature_contrast"] == far["earth_quadrature_contrast"]


@pytest.mark.parametrize("value", [0, -1, float("nan")])
def test_invalid_distance_is_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        distance_summary(value)
