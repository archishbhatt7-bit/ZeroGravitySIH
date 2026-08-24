from __future__ import annotations

"""Physical constants and default thresholds for orbital mechanics.

All values in SI units unless otherwise noted.
"""

# --- Earth parameters (WGS-84) ---
EARTH_RADIUS_KM: float = 6378.137
"""Equatorial radius of Earth in km."""

EARTH_MU_KM3_S2: float = 398600.4418
"""Earth gravitational parameter (GM) in km³/s²."""

EARTH_J2: float = 1.08262668e-3
"""Earth J2 oblateness coefficient."""

EARTH_ROTATION_RAD_S: float = 7.2921150e-5
"""Earth rotation rate in rad/s."""

# --- Default screening thresholds ---
DEFAULT_MISS_DISTANCE_KM: float = 5.0
"""Default miss distance threshold for conjunction screening in km."""

DEFAULT_PC_THRESHOLD: float = 1e-4
"""Default collision probability threshold for alerting."""

DEFAULT_SCREENING_WINDOW_DAYS: float = 7.0
"""Default forward screening window in days."""

# --- Common hard-body radii ---
HARD_BODY_RADIUS_SMALL_M: float = 1.0
"""Hard-body radius for small satellites (<100 kg) in meters."""

HARD_BODY_RADIUS_MEDIUM_M: float = 5.0
"""Hard-body radius for medium satellites (100-1000 kg) in meters."""

HARD_BODY_RADIUS_LARGE_M: float = 20.0
"""Hard-body radius for large satellites/upper stages in meters."""

# --- Orbit regime boundaries ---
LEO_MAX_ALT_KM: float = 2000.0
"""Maximum altitude for Low Earth Orbit in km."""

MEO_MAX_ALT_KM: float = 35786.0
"""Maximum altitude for Medium Earth Orbit in km."""

GEO_ALT_KM: float = 35786.0
"""Geostationary orbit altitude in km."""
