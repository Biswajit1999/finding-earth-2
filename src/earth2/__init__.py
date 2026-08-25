"""
earth2 -- Finding Earth 2.0 in Distant Worlds.

A reproducible, data-driven search for potentially Earth-like worlds across the
public astronomical archives.

The package is organised as a linear, deterministic scientific pipeline::

    data_sources  ->  crossmatch  ->  preprocessing  ->  habitability
                                                     ->  uncertainty
                                                     ->  ranking      ->  reporting

Every stage writes provenance alongside its output. No stage invents a value it
did not receive from an archive; missing measurements stay missing and are
carried through the pipeline as explicit coverage penalties rather than being
silently imputed.
"""

from __future__ import annotations

__version__ = "1.0.1"
__author__ = "Biswajit Jana"
__license__ = "MIT"

__all__ = ["__version__", "__author__", "__license__"]
