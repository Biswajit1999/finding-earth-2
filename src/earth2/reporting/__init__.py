"""Derived statistics and generated documentation.

Every published number originates here, computed from analysis output at build
time. Nothing is hand-typed into the README or the website.
"""

from __future__ import annotations

from earth2.reporting.summary import (
    build_analysis_summary,
    coverage_table,
    dataset_inventory,
    write_summary,
)

__all__ = [
    "build_analysis_summary", "coverage_table", "dataset_inventory", "write_summary",
    "figures", "deepdive", "webexport", "readme",
]
