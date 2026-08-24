"""Orbital propagation via SGP4."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)
from numpy.typing import NDArray
from sgp4.api import SatrecArray, jday

from zerogravity.core.tle import TLE


@dataclass
class StateVector:
    """Position and velocity in TEME frame.

    Attributes:
        position_km: [x, y, z] position in km.
        velocity_km_s: [vx, vy, vz] velocity in km/s.
        epoch: Time of this state vector.
    """

    position_km: NDArray[np.float64]  # shape (3,)
    velocity_km_s: NDArray[np.float64]  # shape (3,)
    epoch: datetime


def propagate(tle: TLE, times: list[datetime]) -> list[StateVector]:
    """Propagate a single TLE to multiple times using SGP4.

    Args:
        tle: A parsed TLE object.
        times: List of UTC datetimes to propagate to.

    Returns:
        List of StateVector objects, one per requested time.

    Raises:
        ValueError: If SGP4 propagation fails (error code != 0).
    """
    result = []
    satrec = tle.satrec

    for t in times:
        # Convert datetime to Julian date
        jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)

        # Propagate using SGP4
        error_code, pos, vel = satrec.sgp4(jd, fr)

        if error_code != 0:
            logger.warning(
                "SGP4 propagation failed for NORAD %d at %s: error code %d",
                tle.norad_id,
                t,
                error_code,
            )
            raise ValueError(
                f"SGP4 propagation failed for NORAD {tle.norad_id} at {t}: error code {error_code}"
            )

        result.append(
            StateVector(
                position_km=np.array(pos, dtype=np.float64),
                velocity_km_s=np.array(vel, dtype=np.float64),
                epoch=t,
            )
        )

    logger.debug("Propagated NORAD %d to %d times", tle.norad_id, len(times))
    return result


def propagate_batch(
    tles: list[TLE], time: datetime
) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
    """Propagate many TLEs to a single time using vectorized SGP4.

    Uses SatrecArray for C-level batch propagation (fast path for large catalogs).

    Args:
        tles: List of TLE objects to propagate.
        time: Single UTC datetime to propagate all objects to.

    Returns:
        Tuple of:
            - positions_velocities: Array of shape (n, 6) with [x,y,z,vx,vy,vz] in km, km/s
            - valid_mask: Boolean array of shape (n,) indicating which propagations succeeded
    """
    if not tles:
        return np.empty((0, 6), dtype=np.float64), np.empty(0, dtype=np.bool_)

    # Extract satrec objects and create SatrecArray
    satrecs = [tle.satrec for tle in tles]
    satrec_array = SatrecArray(satrecs)

    # Convert time to Julian date
    jd, fr = jday(
        time.year,
        time.month,
        time.day,
        time.hour,
        time.minute,
        time.second + time.microsecond / 1e6,
    )

    # Convert to numpy arrays (SatrecArray requires arrays, not scalars)
    jd_array = np.array([jd], dtype=np.float64)
    fr_array = np.array([fr], dtype=np.float64)

    # Batch propagate
    # Output shape: errors (n,1), positions (n,1,3), velocities (n,1,3)
    errors, positions, velocities = satrec_array.sgp4(jd_array, fr_array)

    # Create valid mask (error code 0 means success)
    # Squeeze to remove the time dimension since we only have one time
    valid_mask = errors[:, 0] == 0

    # Combine positions and velocities into single array
    n = len(tles)
    result = np.empty((n, 6), dtype=np.float64)
    result[:, 0:3] = positions[:, 0, :]  # Remove time dimension
    result[:, 3:6] = velocities[:, 0, :]  # Remove time dimension

    return result, valid_mask
