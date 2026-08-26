"""Conjunction screening — identify close approaches between space objects."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree
from sgp4.api import Satrec, SatrecArray, jday

from zerogravity.core.propagation import propagate_batch
from zerogravity.core.tle import TLE
from zerogravity.utils.constants import EARTH_MU_KM3_S2 as MU
from zerogravity.utils.constants import EARTH_RADIUS_KM as RE

logger = logging.getLogger(__name__)


@dataclass
class ConjunctionEvent:
    """A predicted close approach between two space objects.

    Attributes:
        primary_norad_id: NORAD ID of the primary (protected) object.
        secondary_norad_id: NORAD ID of the secondary object.
        tca: Time of closest approach (UTC).
        miss_distance_km: Predicted miss distance in km.
        relative_velocity_km_s: Relative velocity at TCA in km/s.
    """

    primary_norad_id: int
    secondary_norad_id: int
    tca: datetime
    miss_distance_km: float
    relative_velocity_km_s: float


def _apogee_perigee(tle: TLE) -> tuple[float, float]:
    """Compute apogee and perigee altitude in km from TLE orbital elements.

    Args:
        tle: TLE object with orbital elements.

    Returns:
        Tuple of (perigee_altitude_km, apogee_altitude_km).
    """
    n_rad_per_sec = tle.mean_motion_rev_per_day * 2 * math.pi / 86400.0
    a = (MU / (n_rad_per_sec**2)) ** (1.0 / 3.0)
    perigee_radius = a * (1 - tle.eccentricity)
    apogee_radius = a * (1 + tle.eccentricity)
    return perigee_radius - RE, apogee_radius - RE


def _prefilter(tles: list[TLE], primary: TLE, threshold_km: float) -> list[TLE]:
    """Fast geometric prefilter based on orbital shell overlap.

    Only keeps TLEs whose orbital altitude range overlaps with the primary's
    altitude range (accounting for threshold).

    Args:
        tles: List of candidate TLE objects to filter.
        primary: Primary TLE object.
        threshold_km: Miss distance threshold in km.

    Returns:
        Filtered list of TLEs that could potentially approach the primary.
    """
    primary_perigee, primary_apogee = _apogee_perigee(primary)

    filtered = []
    for tle in tles:
        if tle.norad_id == primary.norad_id:
            continue
        secondary_perigee, secondary_apogee = _apogee_perigee(tle)
        if (
            primary_perigee - threshold_km <= secondary_apogee
            and primary_apogee + threshold_km >= secondary_perigee
        ):
            filtered.append(tle)

    return filtered


def _sgp4_single(
    satrec: Satrec, t: datetime
) -> tuple[NDArray[np.float64], NDArray[np.float64], bool]:
    """Propagate a single satrec to a datetime. Returns (pos, vel, valid)."""
    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)
    error_code, pos, vel = satrec.sgp4(jd, fr)
    if error_code != 0:
        return np.zeros(3), np.zeros(3), False
    return np.array(pos), np.array(vel), True


def screen(
    primary: TLE | list[TLE],
    catalog: list[TLE],
    days: float = 7.0,
    threshold_km: float = 10.0,
    step_minutes: float = 10.0,
) -> list[ConjunctionEvent]:
    """Screen for conjunctions between primary object(s) and a catalog.

    Uses a multi-stage algorithm:
    1. Geometric prefilter to eliminate impossible pairs
    2. Coarse time-stepped propagation to find potential close approaches
    3. Fine refinement by bisection to determine accurate TCA

    Args:
        primary: Single TLE or list of TLEs to screen (protected objects).
        catalog: Catalog of TLEs to screen against.
        days: Screening window in days from primary epoch.
        threshold_km: Miss distance threshold in km.
        step_minutes: Time step for coarse search in minutes.

    Returns:
        List of ConjunctionEvent objects sorted by miss distance.
    """
    primaries = [primary] if isinstance(primary, TLE) else primary

    all_events: list[ConjunctionEvent] = []

    for prim in primaries:
        candidates = _prefilter(catalog, prim, threshold_km)
        if not candidates:
            logger.debug("No candidates for NORAD %d after prefilter", prim.norad_id)
            continue

        logger.debug("Screening NORAD %d against %d candidates", prim.norad_id, len(candidates))

        start_time = prim.epoch
        end_time = start_time + timedelta(days=days)
        step_delta = timedelta(minutes=step_minutes)

        # C2 fix: batch primary + candidates together
        batch_tles = [prim] + candidates
        potential_windows: dict[int, list[tuple[datetime, float, NDArray]]] = {}

        current_time = start_time
        while current_time <= end_time:
            states, valid = propagate_batch(batch_tles, current_time)
            if not valid[0]:
                current_time += step_delta
                continue

            prim_pos = states[0, 0:3]

            for i, cand in enumerate(candidates):
                idx = i + 1  # offset by 1 since primary is at index 0
                if not valid[idx]:
                    continue

                cand_pos = states[idx, 0:3]
                distance = float(np.linalg.norm(prim_pos - cand_pos))

                if distance <= threshold_km:
                    if cand.norad_id not in potential_windows:
                        potential_windows[cand.norad_id] = []
                    potential_windows[cand.norad_id].append(
                        (current_time, distance, states[idx, :])
                    )

            current_time += step_delta

        # Step 3: Refine each potential conjunction
        for sec_norad_id, windows in potential_windows.items():
            if not windows:
                continue

            secondary = next(c for c in candidates if c.norad_id == sec_norad_id)

            for t_detect, dist_detect, sec_state in windows:
                t_start = t_detect - step_delta / 2
                t_end = t_detect + step_delta / 2

                tca, min_dist, rel_vel = _refine_tca(
                    prim, secondary, t_start, t_end, initial_step_sec=step_minutes * 30
                )

                if min_dist <= threshold_km:
                    duplicate = False
                    for existing in all_events:
                        if (
                            existing.primary_norad_id == prim.norad_id
                            and existing.secondary_norad_id == sec_norad_id
                            and abs((existing.tca - tca).total_seconds()) < 300
                        ):
                            if min_dist < existing.miss_distance_km:
                                existing.tca = tca
                                existing.miss_distance_km = min_dist
                                existing.relative_velocity_km_s = rel_vel
                            duplicate = True
                            break

                    if not duplicate:
                        all_events.append(
                            ConjunctionEvent(
                                primary_norad_id=prim.norad_id,
                                secondary_norad_id=sec_norad_id,
                                tca=tca,
                                miss_distance_km=min_dist,
                                relative_velocity_km_s=rel_vel,
                            )
                        )

    all_events.sort(key=lambda e: e.miss_distance_km)
    return all_events


def _refine_tca(
    primary: TLE,
    secondary: TLE,
    t_start: datetime,
    t_end: datetime,
    initial_step_sec: float = 1800.0,
) -> tuple[datetime, float, float]:
    """Refine time of closest approach by bisection.

    Uses direct satrec.sgp4() calls for efficiency (C1 fix).

    Args:
        primary: Primary TLE.
        secondary: Secondary TLE.
        t_start: Start of search window.
        t_end: End of search window.
        initial_step_sec: Initial step size in seconds.

    Returns:
        Tuple of (tca, miss_distance_km, relative_velocity_km_s).
    """
    step_sec = initial_step_sec
    min_step = 1.0

    best_time = t_start
    best_dist = float("inf")
    best_rel_vel = 0.0

    prim_sat = primary.satrec
    sec_sat = secondary.satrec

    while step_sec >= min_step:
        current = t_start
        while current <= t_end:
            # C1 fix: direct sgp4 calls instead of propagate_batch
            prim_pos, prim_vel, prim_ok = _sgp4_single(prim_sat, current)
            if prim_ok:
                sec_pos, sec_vel, sec_ok = _sgp4_single(sec_sat, current)
                if sec_ok:
                    distance = float(np.linalg.norm(prim_pos - sec_pos))
                    if distance < best_dist:
                        best_dist = distance
                        best_time = current
                        best_rel_vel = float(np.linalg.norm(prim_vel - sec_vel))

            current += timedelta(seconds=step_sec)

        t_start = max(t_start, best_time - timedelta(seconds=step_sec))
        t_end = min(t_end, best_time + timedelta(seconds=step_sec))
        step_sec /= 2

    return best_time, best_dist, best_rel_vel


def filter_stale_tles(
    tles: list[TLE],
    max_age_days: float = 3.0,
    reference_time: datetime | None = None,
) -> list[TLE]:
    """Filter out TLEs older than max_age_days from reference_time.

    Args:
        tles: List of TLE objects to filter.
        max_age_days: Maximum age in days. TLEs older than this are excluded.
        reference_time: Reference time for age calculation. Defaults to now (UTC).

    Returns:
        List of TLEs that are fresher than max_age_days.
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    cutoff = timedelta(days=max_age_days)
    fresh = []
    for tle in tles:
        epoch = tle.epoch
        if epoch.tzinfo is None:
            epoch = epoch.replace(tzinfo=timezone.utc)
        age = abs(reference_time - epoch)
        if age <= cutoff:
            fresh.append(tle)

    logger.debug(
        "filter_stale_tles: %d/%d TLEs within %.1f days", len(fresh), len(tles), max_age_days
    )
    return fresh


def screen_catalog(
    tles: list[TLE],
    hours: float = 24.0,
    step_minutes: float = 10.0,
    threshold_km: float = 10.0,
    max_tle_age_days: float | None = None,
    reference_time: datetime | None = None,
) -> list[ConjunctionEvent]:
    """Screen all objects against all objects using batch propagation + KD-tree.

    This is the recommended approach for full-catalog screening.
    Uses SatrecArray for vectorized propagation and cKDTree for spatial indexing.

    Args:
        tles: List of TLE objects to screen (the full catalog).
        hours: Screening window in hours from reference_time.
        step_minutes: Time step in minutes for the propagation grid.
        threshold_km: Miss distance threshold in km.
        max_tle_age_days: If set, filter out TLEs older than this many days.
        reference_time: Start time for screening. Defaults to now (UTC).

    Returns:
        List of ConjunctionEvent objects sorted by miss distance.
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    # Optional TLE age filtering
    if max_tle_age_days is not None:
        tles = filter_stale_tles(tles, max_tle_age_days, reference_time)

    if len(tles) < 2:
        logger.info("screen_catalog: fewer than 2 TLEs, nothing to screen")
        return []

    logger.info(
        "screen_catalog: %d objects, %.0fh window, %.0fmin step, %.1fkm threshold",
        len(tles),
        hours,
        step_minutes,
        threshold_km,
    )

    # Build SatrecArray for vectorized propagation
    satrecs = [t.satrec for t in tles]
    sat_arr = SatrecArray(satrecs)
    norad_ids = [t.norad_id for t in tles]

    # Time grid
    steps = int(hours * 60 / step_minutes) + 1
    base_jd, base_fr = jday(
        reference_time.year,
        reference_time.month,
        reference_time.day,
        reference_time.hour,
        reference_time.minute,
        reference_time.second + reference_time.microsecond / 1e6,
    )
    jd = np.full(steps, base_jd)
    fr = base_fr + np.arange(steps) * (step_minutes / 1440.0)

    # Batch propagation: all objects × all timesteps
    logger.debug("Propagating %d objects × %d timesteps...", len(tles), steps)
    e, r_arr, v_arr = sat_arr.sgp4(jd, fr)
    # r_arr shape: (n_sats, n_times, 3), v_arr same

    # Screen with KD-tree at each timestep to find coarse approaches
    coarse_pairs: dict[tuple[int, int], list[tuple[datetime, float, NDArray, NDArray]]] = {}

    for ti in range(steps):
        pos = r_arr[:, ti, :]
        valid = ~np.isnan(pos[:, 0])
        idx_map = np.where(valid)[0]
        pos_valid = pos[valid]

        if len(pos_valid) < 2:
            continue

        tree = cKDTree(pos_valid)
        close = tree.query_pairs(threshold_km)

        dt = reference_time + timedelta(minutes=ti * step_minutes)

        for a, b in close:
            real_a, real_b = int(idx_map[a]), int(idx_map[b])
            key = (min(real_a, real_b), max(real_a, real_b))
            dist = float(np.linalg.norm(pos_valid[a] - pos_valid[b]))
            
            if key not in coarse_pairs:
                coarse_pairs[key] = []
            coarse_pairs[key].append((dt, dist, v_arr[real_a, ti, :], v_arr[real_b, ti, :]))

    # Refine TCA for coarse approaches
    logger.debug("Refining TCA for %d potential pairs...", len(coarse_pairs))
    all_events: list[ConjunctionEvent] = []
    
    # We need a lookup for TLE objects since _refine_tca requires them
    tle_by_id = {t.norad_id: t for t in tles}
    
    step_delta = timedelta(minutes=step_minutes)

    for key, windows in coarse_pairs.items():
        id_a, id_b = norad_ids[key[0]], norad_ids[key[1]]
        prim = tle_by_id[id_a]
        sec = tle_by_id[id_b]
        
        for dt, dist, v_a, v_b in windows:
            t_start = dt - step_delta / 2
            t_end = dt + step_delta / 2
            
            # Sub-second refinement
            tca, min_dist, rel_vel = _refine_tca(
                prim, sec, t_start, t_end, initial_step_sec=step_minutes * 30
            )
            
            if min_dist <= threshold_km:
                duplicate = False
                for existing in all_events:
                    if (
                        existing.primary_norad_id == id_a
                        and existing.secondary_norad_id == id_b
                        and abs((existing.tca - tca).total_seconds()) < 300
                    ):
                        if min_dist < existing.miss_distance_km:
                            existing.tca = tca
                            existing.miss_distance_km = min_dist
                            existing.relative_velocity_km_s = rel_vel
                        duplicate = True
                        break
                
                if not duplicate:
                    all_events.append(
                        ConjunctionEvent(
                            primary_norad_id=id_a,
                            secondary_norad_id=id_b,
                            tca=tca,
                            miss_distance_km=round(min_dist, 4),
                            relative_velocity_km_s=round(rel_vel, 4),
                        )
                    )

    all_events.sort(key=lambda ev: ev.miss_distance_km)
    logger.info("screen_catalog: found %d close pairs", len(all_events))
    return all_events
