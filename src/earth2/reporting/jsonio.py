"""Strictly-valid JSON output.

Python's :func:`json.dumps` will happily emit bare ``NaN``, ``Infinity`` and
``-Infinity`` tokens. Those are a Python extension, **not** valid JSON, and
every standards-compliant parser rejects them::

    JSON.parse('{"x": NaN}')
    // SyntaxError: Unexpected token 'N'

This project produces a great many missing values by design -- an unmeasured
planet mass is the normal case -- and pandas turns ``None`` into ``NaN`` inside
any float column on the way out. Without sanitisation the browser cannot read
its own data files.

Every JSON write in the project goes through :func:`dump_json`, which converts
non-finite floats to ``null`` and then sets ``allow_nan=False`` so that anything
missed raises at build time rather than shipping a broken file.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["dump_json", "json_safe"]


def json_safe(obj: Any) -> Any:
    """Recursively replace non-finite numbers with None and normalise numpy types.

    ``NaN`` means "not measured" throughout this project, and ``null`` is the
    JSON spelling of that. The conversion is deliberate and lossless in meaning:
    both say "no value here".
    """
    if obj is None:
        return None

    # numpy scalars -> python scalars
    if isinstance(obj, np.generic):
        obj = obj.item()

    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, (int, str, bool)):
        return obj
    if isinstance(obj, np.ndarray):
        return [json_safe(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [json_safe(v) for v in obj]

    # pandas NA / NaT and anything else exotic
    try:
        import pandas as pd

        if obj is pd.NaT or (not isinstance(obj, (list, dict)) and pd.isna(obj)):
            return None
    except (TypeError, ValueError, ImportError):
        pass

    return str(obj)


def dump_json(obj: Any, indent: int | None = None, compact: bool = False) -> str:
    """Serialise to strictly-valid JSON.

    ``allow_nan=False`` is a guard, not a formality: if anything slips past
    :func:`json_safe` the build fails loudly here instead of writing a file the
    browser cannot parse.
    """
    safe = json_safe(obj)
    if compact:
        return json.dumps(safe, separators=(",", ":"), allow_nan=False)
    return json.dumps(safe, indent=indent, allow_nan=False, default=str)


def write_json_file(obj: Any, path: Path, indent: int | None = 1) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_json(obj, indent=indent) + "\n", encoding="utf-8")
    return path
