"""Entity resolution. Never joins astronomical data on string similarity."""

from __future__ import annotations

from earth2.crossmatch.resolve import (
    ALIAS_LOOKUP_URL,
    CatalogueIds,
    MatchResult,
    build_alias_table,
    coordinate_crossmatch,
    extract_catalogue_ids,
    resolve_system,
)

__all__ = [
    "ALIAS_LOOKUP_URL", "CatalogueIds", "MatchResult", "build_alias_table",
    "coordinate_crossmatch", "extract_catalogue_ids", "resolve_system",
]
