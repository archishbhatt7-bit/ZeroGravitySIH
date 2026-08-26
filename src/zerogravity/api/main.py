import logging
import math
from datetime import datetime, timezone

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from sgp4.api import Satrec, jday

from zerogravity.core.formations import filter_formation_events
from zerogravity.core.probability import PcMethod, compute_pc
from zerogravity.core.risk import classify_events
from zerogravity.core.screening import screen_catalog
from zerogravity.core.tle import parse_tle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ZeroGravity API",
    description="API for satellite conjunction screening and visualization.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CELESTRAK_URL_ACTIVE = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
CELESTRAK_URL_FULL = "https://celestrak.org/NORAD/elements/gp.php?SPECIAL=gp-index&FORMAT=tle"

# Simple in-memory cache
cache = {
    "tles_active": [],
    "tles_full": [],
    "last_fetch_active": None,
    "last_fetch_full": None,
    "conjunctions": [],
    "last_screen_params": None,
    "last_screen_time": None,
}


async def fetch_tles_from_celestrak(data_source: str = "celestrak_active", max_objects: int = 1500):
    now = datetime.now(timezone.utc)
    cache_key = "tles_active" if data_source == "celestrak_active" else "tles_full"
    fetch_key = "last_fetch_active" if data_source == "celestrak_active" else "last_fetch_full"
    url = CELESTRAK_URL_ACTIVE if data_source == "celestrak_active" else CELESTRAK_URL_FULL

    # Cache for 1 hour
    if cache[cache_key] and cache[fetch_key] and (now - cache[fetch_key]).total_seconds() < 3600:
        return cache[cache_key][:max_objects] if max_objects > 0 else cache[cache_key]

    headers = {"User-Agent": "ZeroGravity/0.2.0 (contact: info@zerogravity.local)"}

    # Force use of local fallback to avoid Celestrak hanging
    import os
    fallback_path = os.path.join(os.path.dirname(__file__), "fallback_tles.txt")
    if os.path.exists(fallback_path):
        with open(fallback_path, "r", encoding="utf-8") as f:
            tles = parse_tle(f.read())
    else:
        raise Exception("Fallback TLE file not found")

    # Filter to Low Earth Orbit (LEO) only
    # LEO altitude <= 2000km corresponds to a mean motion >= 11.25 revs/day
    leo_tles = []
    for t in tles:
        try:
            mm = float(t.line2[52:63].strip())
            if mm >= 11.25:
                leo_tles.append(t)
        except Exception:
            pass

    tles = leo_tles
    import random
    random.seed(42)  # Consistent sample
    random.shuffle(tles)

    cache[cache_key] = tles
    cache[fetch_key] = now

    return tles[:max_objects] if max_objects > 0 else tles


def _tle_to_dict(tle):
    name = tle.name.upper()
    obj_type = "UNKNOWN"
    if " DEB" in name:
        obj_type = "DEBRIS"
    elif " R/B" in name or "ROCKET" in name:
        obj_type = "ROCKET_BODY"
    else:
        obj_type = "ACTIVE_SATELLITE"

    return {
        "name": tle.name,
        "norad_id": tle.norad_id,
        "object_type": obj_type,
        "epoch": tle.epoch.isoformat(),
        "inclination": tle.inclination_deg,
        "eccentricity": tle.eccentricity,
        "line1": tle.line1,
        "line2": tle.line2,
    }


def get_rcs_size(name):
    name = name.upper()
    if " DEB" in name:
        return "SMALL"
    if "ISS" in name or "CSS" in name:
        return "LARGE"
    return "MEDIUM"


def is_maneuverable(name):
    name = name.upper()
    if " DEB" in name or " R/B" in name:
        return False
    if "STARLINK" in name or "ONEWEB" in name or "IRIDIUM" in name:
        return True
    return False


# ─── Geodetic helpers ───────────────────────────────────────────────


def _sgp4_at(satrec: Satrec, dt: datetime):
    """Propagate a satrec to a datetime. Returns (pos_km, vel_km_s) or (None, None)."""
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)
    err, pos, vel = satrec.sgp4(jd, fr)
    if err != 0:
        return None, None
    return np.array(pos), np.array(vel)


def _eci_to_geodetic(pos_km, dt: datetime):
    """Convert ECI (TEME) position to geodetic lat/lng/alt.

    Uses a simplified TEME→ECEF rotation (ignoring nutation/precession for speed)
    then converts ECEF to geodetic via iterative method.
    """
    # GMST angle
    # Julian date
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)
    jd_total = jd + fr

    # Greenwich Mean Sidereal Time (radians)
    T = (jd_total - 2451545.0) / 36525.0
    gmst = 67310.54841 + (876600 * 3600 + 8640184.812866) * T + 0.093104 * T**2 - 6.2e-6 * T**3
    gmst = math.radians((gmst % 86400) / 240.0)

    # Rotate TEME → ECEF
    cos_g = math.cos(gmst)
    sin_g = math.sin(gmst)
    x_ecef = pos_km[0] * cos_g + pos_km[1] * sin_g
    y_ecef = -pos_km[0] * sin_g + pos_km[1] * cos_g
    z_ecef = pos_km[2]

    # ECEF → Geodetic (WGS-84)
    a = 6378.137  # equatorial radius km
    f = 1 / 298.257223563
    e2 = 2 * f - f * f

    lon = math.atan2(y_ecef, x_ecef)
    p = math.sqrt(x_ecef**2 + y_ecef**2)
    lat = math.atan2(z_ecef, p * (1 - e2))  # initial guess

    for _ in range(5):  # iterate
        N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        lat = math.atan2(z_ecef + e2 * N * math.sin(lat), p)

    N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    alt = p / math.cos(lat) - N

    return math.degrees(lat), math.degrees(lon), alt


def _compute_conjunction_location(prim_tle, sec_tle, tca: datetime):
    """Compute the geographic location of a conjunction at TCA.
    Returns (lat, lng, alt_km) using the primary object's position.
    """
    try:
        prim_sat = Satrec.twoline2rv(prim_tle.line1, prim_tle.line2)
        pos, _ = _sgp4_at(prim_sat, tca)
        if pos is None:
            return 0.0, 0.0, 400.0  # fallback
        lat, lng, alt = _eci_to_geodetic(pos, tca)
        return round(lat, 4), round(lng, 4), round(alt, 2)
    except Exception:
        return 0.0, 0.0, 400.0


def _estimate_pc(prim_tle, sec_tle, tca: datetime, miss_distance_km: float):
    """Estimate collision probability using Foster 1992 method.

    Since TLEs don't carry covariance, we use scaled identity matrices
    where scale grows with TLE age (older = more uncertain).
    """
    try:
        prim_sat = Satrec.twoline2rv(prim_tle.line1, prim_tle.line2)
        sec_sat = Satrec.twoline2rv(sec_tle.line1, sec_tle.line2)

        pos1, vel1 = _sgp4_at(prim_sat, tca)
        pos2, vel2 = _sgp4_at(sec_sat, tca)

        if pos1 is None or pos2 is None:
            return None, None

        # Estimate position uncertainty from TLE age
        now = datetime.now(timezone.utc)
        prim_epoch = (
            prim_tle.epoch.replace(tzinfo=timezone.utc)
            if prim_tle.epoch.tzinfo is None
            else prim_tle.epoch
        )
        sec_epoch = (
            sec_tle.epoch.replace(tzinfo=timezone.utc)
            if sec_tle.epoch.tzinfo is None
            else sec_tle.epoch
        )

        prim_age_days = abs((now - prim_epoch).total_seconds()) / 86400
        sec_age_days = abs((now - sec_epoch).total_seconds()) / 86400

        # Position uncertainty grows ~1 km/day for SGP4/TLE
        sigma1_km = max(0.1, 0.5 + prim_age_days * 1.0)
        sigma2_km = max(0.1, 0.5 + sec_age_days * 1.0)

        # Build 6x6 covariance (position uncertainty only, velocity set small)
        cov1 = np.zeros((6, 6))
        cov1[0, 0] = cov1[1, 1] = cov1[2, 2] = sigma1_km**2
        cov1[3, 3] = cov1[4, 4] = cov1[5, 5] = 0.001**2  # velocity uncertainty

        cov2 = np.zeros((6, 6))
        cov2[0, 0] = cov2[1, 1] = cov2[2, 2] = sigma2_km**2
        cov2[3, 3] = cov2[4, 4] = cov2[5, 5] = 0.001**2

        result = compute_pc(
            pos1_km=pos1,
            vel1_km_s=vel1,
            pos2_km=pos2,
            vel2_km_s=vel2,
            cov1=cov1,
            cov2=cov2,
            hard_body_radius_m=20.0,
            method=PcMethod.FOSTER_1992,
        )

        return result.probability, "foster_1992_estimated"

    except Exception as e:
        logger.warning("Pc estimation failed: %s", e)
        return None, None


# ─── Conjunction processing ─────────────────────────────────────────


def _process_conjunctions(events, tles, now, filter_formations):
    tle_dict = {t.norad_id: t for t in tles}

    event_dicts = []
    for ev in events:
        prim = tle_dict.get(ev.primary_norad_id)
        sec = tle_dict.get(ev.secondary_norad_id)
        if not prim or not sec:
            continue

        event_dicts.append(
            {
                "name1": prim.name,
                "name2": sec.name,
                "norad_id1": prim.norad_id,
                "norad_id2": sec.norad_id,
                "miss_distance_km": ev.miss_distance_km,
                "relative_velocity_km_s": ev.relative_velocity_km_s,
                "obj1_rcs": get_rcs_size(prim.name),
                "obj2_rcs": get_rcs_size(sec.name),
                "obj1_maneuverable": is_maneuverable(prim.name),
                "obj2_maneuverable": is_maneuverable(sec.name),
                "tca": ev.tca,
                "now": now,
            }
        )

    if filter_formations:
        real_threats, _ = filter_formation_events(event_dicts)
    else:
        real_threats = event_dicts

    assessments = classify_events(real_threats)

    results = []
    for idx, event in enumerate(real_threats):
        assessment = assessments[idx]
        prim_tle = tle_dict[event["norad_id1"]]
        sec_tle = tle_dict[event["norad_id2"]]

        prim_age = (now - prim_tle.epoch.replace(tzinfo=timezone.utc)).total_seconds() / 86400
        sec_age = (now - sec_tle.epoch.replace(tzinfo=timezone.utc)).total_seconds() / 86400

        confidence = "REDUCED" if (prim_age > 3 or sec_age > 3) else "NORMAL"

        # Compute geographic location at TCA
        tca_dt = event["tca"]
        lat, lng, alt = _compute_conjunction_location(prim_tle, sec_tle, tca_dt)

        # Estimate collision probability
        pc, pc_method = _estimate_pc(prim_tle, sec_tle, tca_dt, event["miss_distance_km"])

        results.append(
            {
                "primary": {
                    "name": event["name1"],
                    "norad_id": event["norad_id1"],
                    "rcs": event["obj1_rcs"],
                    "maneuverable": event["obj1_maneuverable"],
                    "object_type": _tle_to_dict(prim_tle)["object_type"],
                    "epoch": prim_tle.epoch.isoformat(),
                    "age_days": prim_age,
                    "line1": prim_tle.line1,
                    "line2": prim_tle.line2,
                },
                "secondary": {
                    "name": event["name2"],
                    "norad_id": event["norad_id2"],
                    "rcs": event["obj2_rcs"],
                    "maneuverable": event["obj2_maneuverable"],
                    "object_type": _tle_to_dict(sec_tle)["object_type"],
                    "epoch": sec_tle.epoch.isoformat(),
                    "age_days": sec_age,
                    "line1": sec_tle.line1,
                    "line2": sec_tle.line2,
                },
                "tca": event["tca"].isoformat(),
                "miss_distance_km": assessment.miss_distance_km,
                "relative_velocity_km_s": assessment.relative_velocity_km_s,
                "risk_score": assessment.score,
                "risk_category": assessment.category,
                "time_to_tca_hours": assessment.time_to_tca_hours,
                "factors": assessment.factors,
                "recommendation": assessment.recommendation,
                "confidence": confidence,
                "lat": lat,
                "lng": lng,
                "alt": alt,
                "collision_probability": pc,
                "probability_method": pc_method,
            }
        )

    results.sort(key=lambda x: (-x["risk_score"], x["tca"]))
    return results


# ─── Routes ─────────────────────────────────────────────────────────


@app.get("/")
async def root():
    return {"message": "ZeroGravity API is running", "status": "ok"}


@app.get("/api/health")
async def health():
    now = datetime.now(timezone.utc)
    return {
        "status": "ok",
        "timestamp": now.isoformat(),
        "cache": {
            "tles_active_count": len(cache["tles_active"]),
            "tles_full_count": len(cache["tles_full"]),
            "last_fetch_active": cache["last_fetch_active"].isoformat()
            if cache["last_fetch_active"]
            else None,
            "last_fetch_full": cache["last_fetch_full"].isoformat()
            if cache["last_fetch_full"]
            else None,
        },
    }


@app.get("/api/stats")
async def get_stats():
    """Get aggregate statistics for the dashboard TopBar."""
    now = datetime.now(timezone.utc)
    if not cache["tles_active"]:
        await fetch_tles_from_celestrak("celestrak_active", max_objects=1500)

    tles = cache["tles_active"]
    active = 0
    debris = 0
    rocket = 0
    for tle in tles:
        name = tle.name.upper()
        if " DEB" in name:
            debris += 1
        elif " R/B" in name or "ROCKET" in name:
            rocket += 1
        else:
            active += 1

    conjunctions = cache["conjunctions"]
    critical = sum(1 for c in conjunctions if c["risk_category"] == "CRITICAL")
    high = sum(1 for c in conjunctions if c["risk_category"] == "HIGH")
    medium = sum(1 for c in conjunctions if c["risk_category"] == "MEDIUM")
    low = sum(1 for c in conjunctions if c["risk_category"] == "LOW")

    avg_miss = (
        sum(c["miss_distance_km"] for c in conjunctions) / len(conjunctions) if conjunctions else 0
    )
    closest = min(c["miss_distance_km"] for c in conjunctions) if conjunctions else 0

    return {
        "total_tracked": len(tles),
        "active_satellites": active,
        "debris": debris,
        "rocket_bodies": rocket,
        "conjunctions_total": len(conjunctions),
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "avg_miss_distance_km": round(avg_miss, 2),
        "closest_approach_km": round(closest, 2),
        "last_update": cache["last_screen_time"].isoformat() if cache["last_screen_time"] else None,
    }


@app.get("/api/satellites")
async def get_satellites(
    max_objects: int = Query(1500, description="Max objects to return"),
    data_source: str = Query("celestrak_active", description="Data source"),
):
    tles = await fetch_tles_from_celestrak(data_source, max_objects)
    return {"satellites": [_tle_to_dict(t) for t in tles]}


@app.get("/api/satellites/search")
async def search_satellites(
    q: str = Query(..., min_length=1, description="Search query (name or NORAD ID)"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
):
    """Search for satellites by name (substring) or NORAD ID (exact)."""
    tles = cache["tles_active"]
    if not tles:
        tles = await fetch_tles_from_celestrak("celestrak_active", max_objects=1500)

    q_upper = q.strip().upper()
    results = []

    # If query is numeric, try exact NORAD ID match first
    is_numeric = q.strip().isdigit()
    target_norad = int(q.strip()) if is_numeric else None

    for tle in tles:
        if len(results) >= limit:
            break

        matched = False
        if target_norad is not None and tle.norad_id == target_norad or q_upper in tle.name.upper():
            matched = True

        if matched:
            sat_dict = _tle_to_dict(tle)
            # Compute current position
            try:
                sat = Satrec.twoline2rv(tle.line1, tle.line2)
                now = datetime.now(timezone.utc)
                pos, vel = _sgp4_at(sat, now)
                if pos is not None:
                    lat, lng, alt = _eci_to_geodetic(pos, now)
                    sat_dict["lat"] = round(lat, 4)
                    sat_dict["lng"] = round(lng, 4)
                    sat_dict["alt"] = round(alt, 2)
                    if vel is not None:
                        sat_dict["velocity_km_s"] = round(float(np.linalg.norm(vel)), 3)
            except Exception:
                pass

            results.append(sat_dict)

    return {"results": results, "count": len(results)}


@app.get("/api/orbits/{norad_id}")
async def get_orbit_path(norad_id: int = Path(..., description="NORAD ID of the satellite")):
    """Get the raw TLE for a specific satellite so the client can propagate its orbit path."""
    tles = cache["tles_active"] or await fetch_tles_from_celestrak("celestrak_active")

    for tle in tles:
        if tle.norad_id == norad_id:
            return {
                "norad_id": tle.norad_id,
                "name": tle.name,
                "line1": tle.line1,
                "line2": tle.line2,
            }

    raise HTTPException(status_code=404, detail="Satellite not found in catalog")


@app.get("/api/screen/{norad_id}")
async def screen_satellite(
    norad_id: int = Path(..., description="NORAD ID to screen"),
    hours: float = Query(24.0, description="Screening window in hours"),
    threshold_km: float = Query(10.0, description="Miss distance threshold in km"),
    filter_formations: bool = Query(True, description="Filter known formations"),
):
    """On-demand screening for a specific satellite."""
    tles = cache["tles_active"] or await fetch_tles_from_celestrak("celestrak_active")

    primary_tle = next((t for t in tles if t.norad_id == norad_id), None)
    if not primary_tle:
        raise HTTPException(status_code=404, detail="Target satellite not found in catalog")

    now = datetime.now(timezone.utc)

    events = screen_catalog(
        tles=tles,
        hours=hours,
        step_minutes=10.0,
        threshold_km=threshold_km,
        max_tle_age_days=None,
        reference_time=now,
    )

    # Filter out events that don't involve the target satellite
    target_events = [
        ev for ev in events if ev.primary_norad_id == norad_id or ev.secondary_norad_id == norad_id
    ]

    results = _process_conjunctions(target_events, tles, now, filter_formations)
    return {"conjunctions": results}


@app.get("/api/conjunctions")
async def get_conjunctions(
    hours: float = Query(24.0, description="Screening window in hours"),
    threshold_km: float = Query(10.0, description="Miss distance threshold in km"),
    filter_formations: bool = Query(True, description="Filter known formations"),
    stale_tle_days: float = Query(None, description="Max TLE age in days"),
    data_source: str = Query("celestrak_active", description="Data source"),
    max_objects: int = Query(-1, description="Max objects to screen (-1 for all)"),
):
    tles = await fetch_tles_from_celestrak(data_source, max_objects)

    now = datetime.now(timezone.utc)
    params = (hours, threshold_km, filter_formations, stale_tle_days, data_source, max_objects)

    if (
        cache["conjunctions"]
        and cache["last_screen_time"]
        and cache["last_screen_params"] == params
        and (now - cache["last_screen_time"]).total_seconds() < 3600
    ):
        return {"conjunctions": cache["conjunctions"], "total_screened": len(tles)}

    events = screen_catalog(
        tles=tles,
        hours=hours,
        step_minutes=10.0,
        threshold_km=threshold_km,
        max_tle_age_days=stale_tle_days,
        reference_time=now,
    )

    results = _process_conjunctions(events, tles, now, filter_formations)

    cache["conjunctions"] = results
    cache["last_screen_params"] = params
    cache["last_screen_time"] = now

    return {"conjunctions": results, "total_screened": len(tles)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("zerogravity.api.main:app", host="0.0.0.0", port=8000, reload=True)
