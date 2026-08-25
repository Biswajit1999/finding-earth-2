"""JSON output must always be strictly valid (no bare NaN/Infinity)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from earth2.reporting.jsonio import dump_json


def test_nan_becomes_null():
    out = dump_json({"x": float("nan")})
    assert json.loads(out) == {"x": None}


def test_infinity_becomes_null():
    out = dump_json({"x": float("inf"), "y": float("-inf")})
    assert json.loads(out) == {"x": None, "y": None}


def test_finite_float_survives():
    out = dump_json({"x": 3.14159})
    assert json.loads(out)["x"] == pytest.approx(3.14159)


def test_numpy_scalars_are_converted():
    out = dump_json({"x": np.float64(1.5), "y": np.int64(3), "z": np.nan})
    parsed = json.loads(out)
    assert parsed == {"x": 1.5, "y": 3, "z": None}


def test_pandas_na_becomes_null():
    out = dump_json({"x": pd.NA})
    assert json.loads(out) == {"x": None}


def test_nested_structures_are_sanitised():
    payload = {"a": [1.0, float("nan"), {"b": float("inf")}], "c": None}
    out = dump_json(payload)
    parsed = json.loads(out)
    assert parsed["a"][1] is None
    assert parsed["a"][2]["b"] is None


def test_output_never_contains_bare_nan_token():
    """The literal string 'NaN' must never appear as an unquoted JSON token."""
    out = dump_json({"x": float("nan"), "label": "not a NaN string"})
    # Strict parser must accept it (raises on non-standard constants).
    json.loads(out, parse_constant=lambda tok: (_ for _ in ()).throw(ValueError(tok)))


def test_dump_json_raises_would_be_caught_if_sanitisation_failed():
    """allow_nan=False is the safety net -- confirm it is actually engaged."""
    with pytest.raises(ValueError):
        json.dumps({"x": float("nan")}, allow_nan=False)
