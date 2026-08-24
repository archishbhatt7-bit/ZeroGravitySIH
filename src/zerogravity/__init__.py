"""
ZeroGravity — Satellite conjunction assessment for Python.

Open-source library for screening conjunctions, parsing CDMs,
and computing collision probability. Built for operators who
need transparency in safety-critical decisions.
"""

from __future__ import annotations

__version__ = "0.1.0-dev"

from zerogravity.core.probability import PcMethod, PcResult, compute_pc
from zerogravity.core.propagation import StateVector, propagate, propagate_batch
from zerogravity.core.screening import ConjunctionEvent, filter_stale_tles, screen, screen_catalog
from zerogravity.core.tle import TLE, parse_tle
from zerogravity.data.cdm import CDM, CDMObject
from zerogravity.data.spacetrack import SpaceTrackClient

__all__ = [
    "CDM",
    "TLE",
    "CDMObject",
    "ConjunctionEvent",
    "PcMethod",
    "PcResult",
    "SpaceTrackClient",
    "StateVector",
    "__version__",
    "compute_pc",
    "filter_stale_tles",
    "parse_tle",
    "propagate",
    "propagate_batch",
    "screen",
    "screen_catalog",
]
