"""
ZeroGravity — Satellite conjunction assessment for Python.

Open-source library for screening conjunctions, parsing CDMs,
and computing collision probability. Built for operators who
need transparency in safety-critical decisions.
"""

from __future__ import annotations

__version__ = "0.1.0-dev"

from zerogravity.core.tle import TLE, parse_tle
from zerogravity.core.propagation import propagate, propagate_batch, StateVector
from zerogravity.core.screening import screen, screen_catalog, filter_stale_tles, ConjunctionEvent
from zerogravity.core.probability import compute_pc, PcMethod, PcResult
from zerogravity.data.cdm import CDM, CDMObject
from zerogravity.data.spacetrack import SpaceTrackClient

__all__ = [
    "__version__",
    "TLE",
    "parse_tle",
    "propagate",
    "propagate_batch",
    "StateVector",
    "screen",
    "screen_catalog",
    "filter_stale_tles",
    "ConjunctionEvent",
    "compute_pc",
    "PcMethod",
    "PcResult",
    "CDM",
    "CDMObject",
    "SpaceTrackClient",
]
