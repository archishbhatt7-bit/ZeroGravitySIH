<<<<<<< HEAD
from fastapi import FastAPI, BackgroundTasks, HTTPException
=======
from fastapi import FastAPI, Query
>>>>>>> a5ea05b (feat: implement Space Debris Tracking & Collision Risk Dashboard - Add satellite.js for real orbital position computation - Add ObjectInfoPanel, RiskBreakdownChart, LoadingOverlay components - Enhance backend API with health endpoint, confidence tags, data source selector - Expand Zustand store with layer visibility, auto-refresh, TLE staleness filters - Update TopBar, ControlPanel, ConjunctionList, EventDetail with full feature set - Add satellite.js type declarations)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
<<<<<<< HEAD
import requests
import asyncio
from datetime import datetime

from orbveil.core.tle import parse_tle, TLE
from orbveil.core.screening import screen_catalog, ConjunctionEvent
=======
import httpx
from datetime import datetime, timezone, timedelta

from orbveil.core.tle import parse_tle
from orbveil.core.screening import screen_catalog
from orbveil.core.risk import classify_events
from orbveil.core.formations import filter_formation_events
>>>>>>> a5ea05b (feat: implement Space Debris Tracking & Collision Risk Dashboard - Add satellite.js for real orbital position computation - Add ObjectInfoPanel, RiskBreakdownChart, LoadingOverlay components - Enhance backend API with health endpoint, confidence tags, data source selector - Expand Zustand store with layer visibility, auto-refresh, TLE staleness filters - Update TopBar, ControlPanel, ConjunctionList, EventDetail with full feature set - Add satellite.js type declarations)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ZeroGravity API",
    description="API for satellite conjunction screening and visualization.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
# Global in-memory cache
class AppState:
    catalog: list[TLE] = []
    conjunctions: list[ConjunctionEvent] = []
    is_screening: bool = False
    last_update: datetime = None

state = AppState()

def fetch_active_catalog() -> list[TLE]:
    """Fetch the active satellite catalog from CelesTrak."""
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    logger.info("Fetching TLE catalog from CelesTrak...")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    tles = parse_tle(response.text)
    logger.info(f"Loaded {len(tles)} satellites into catalog.")
    return tles

def run_screening_job():
    """Background job to run conjunction screening on the catalog."""
    if state.is_screening or not state.catalog:
        return
    
    state.is_screening = True
    try:
        logger.info("Starting background conjunction screening...")
        # Screen the first 1000 satellites against each other for a 24h window
        # to ensure it completes quickly for the dashboard demo.
        subset = state.catalog[:1000]
        events = screen_catalog(
            tles=subset,
            hours=24.0,
            step_minutes=10.0,
            threshold_km=15.0  # Slightly larger threshold to guarantee we find some events for the UI
        )
        state.conjunctions = events
        state.last_update = datetime.now()
        logger.info(f"Screening complete. Found {len(events)} potential conjunctions.")
    except Exception as e:
        logger.error(f"Screening failed: {e}")
    finally:
        state.is_screening = False

@app.on_event("startup")
async def startup_event():
    """Initialize catalog and kick off screening on server start."""
    try:
        state.catalog = fetch_active_catalog()
        # Run screening in a separate thread so it doesn't block startup
        asyncio.get_event_loop().run_in_executor(None, run_screening_job)
    except Exception as e:
        logger.error(f"Failed to fetch catalog on startup: {e}")

@app.get("/")
async def root():
    return {
        "message": "OrbVeil API is running",
        "catalog_size": len(state.catalog),
        "conjunctions_found": len(state.conjunctions),
        "is_screening_running": state.is_screening
    }

@app.get("/api/satellites")
async def get_satellites(limit: int = 1500):
    """
    Return a list of satellites with their raw TLE lines.
    The frontend (react-globe.gl + satellite.js) will compute the lat/lng locally for 60fps animation.
    """
    if not state.catalog:
        raise HTTPException(status_code=503, detail="Catalog is still loading")
    
    data = []
    # Limit returned satellites to keep JSON payload manageable for browser
    for tle in state.catalog[:limit]:
        data.append({
            "norad_id": tle.norad_id,
            "name": tle.name or f"SAT-{tle.norad_id}",
            "line1": tle.line1,
            "line2": tle.line2
        })
    return {"satellites": data}

@app.get("/api/conjunctions")
async def get_conjunctions():
    """Return the latest detected conjunction events."""
    data = []
    for ev in state.conjunctions:
        data.append({
            "primary_id": ev.primary_norad_id,
            "secondary_id": ev.secondary_norad_id,
            "tca": ev.tca.isoformat(),
            "miss_distance_km": ev.miss_distance_km,
            "relative_velocity_km_s": ev.relative_velocity_km_s,
            "severity": "high" if ev.miss_distance_km < 5.0 else "medium"
        })
    return {
        "conjunctions": data,
        "is_updating": state.is_screening,
        "last_update": state.last_update.isoformat() if state.last_update else None
    }

@app.post("/api/conjunctions/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    """Manually trigger a new screening run."""
    if state.is_screening:
        return {"status": "already_running"}
    
    background_tasks.add_task(run_screening_job)
    return {"status": "started"}
=======
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
    "last_screen_time": None
}

async def fetch_tles_from_celestrak(data_source: str = "celestrak_active", max_objects: int = 1500):
    now = datetime.now(timezone.utc)
    cache_key = "tles_active" if data_source == "celestrak_active" else "tles_full"
    fetch_key = "last_fetch_active" if data_source == "celestrak_active" else "last_fetch_full"
    url = CELESTRAK_URL_ACTIVE if data_source == "celestrak_active" else CELESTRAK_URL_FULL

    # Cache for 1 hour
    if cache[cache_key] and cache[fetch_key] and (now - cache[fetch_key]).total_seconds() < 3600:
        return cache[cache_key][:max_objects] if max_objects > 0 else cache[cache_key]
        
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60.0)
        response.raise_for_status()
        tles = parse_tle(response.text)
        
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
        "line2": tle.line2
    }

def get_rcs_size(name):
    name = name.upper()
    if " DEB" in name: return "SMALL"
    if "ISS" in name or "CSS" in name: return "LARGE"
    return "MEDIUM"

def is_maneuverable(name):
    name = name.upper()
    if " DEB" in name or " R/B" in name: return False
    if "STARLINK" in name or "ONEWEB" in name or "IRIDIUM" in name: return True
    return False

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
            "last_fetch_active": cache["last_fetch_active"].isoformat() if cache["last_fetch_active"] else None,
            "last_fetch_full": cache["last_fetch_full"].isoformat() if cache["last_fetch_full"] else None,
        }
    }

@app.get("/api/satellites")
async def get_satellites(
    max_objects: int = Query(1500, description="Max objects to return"),
    data_source: str = Query("celestrak_active", description="Data source")
):
    tles = await fetch_tles_from_celestrak(data_source, max_objects)
    return {"satellites": [_tle_to_dict(t) for t in tles]}

@app.get("/api/conjunctions")
async def get_conjunctions(
    hours: float = Query(24.0, description="Screening window in hours"),
    threshold_km: float = Query(10.0, description="Miss distance threshold in km"),
    filter_formations: bool = Query(True, description="Filter known formations"),
    stale_tle_days: float = Query(None, description="Max TLE age in days"),
    data_source: str = Query("celestrak_active", description="Data source"),
    max_objects: int = Query(1500, description="Max objects to screen")
):
    tles = await fetch_tles_from_celestrak(data_source, max_objects)
    
    now = datetime.now(timezone.utc)
    params = (hours, threshold_km, filter_formations, stale_tle_days, data_source, max_objects)
    
    if (cache["conjunctions"] and cache["last_screen_time"] and 
        cache["last_screen_params"] == params and 
        (now - cache["last_screen_time"]).total_seconds() < 3600):
        return {"conjunctions": cache["conjunctions"]}

    events = screen_catalog(
        tles=tles,
        hours=hours,
        step_minutes=10.0,
        threshold_km=threshold_km,
        max_tle_age_days=stale_tle_days,
        reference_time=now
    )
    
    tle_dict = {t.norad_id: t for t in tles}
    
    event_dicts = []
    for ev in events:
        prim = tle_dict.get(ev.primary_norad_id)
        sec = tle_dict.get(ev.secondary_norad_id)
        if not prim or not sec: continue
        
        event_dicts.append({
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
            "now": now
        })
        
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
        
        # Approximate TCA lat/lon/alt by just returning empty strings for now.
        # Frontend can compute it via satellite.js when it clicks 'Focus on Globe'.
        
        results.append({
            "primary": {
                "name": event["name1"],
                "norad_id": event["norad_id1"],
                "rcs": event["obj1_rcs"],
                "maneuverable": event["obj1_maneuverable"],
                "object_type": _tle_to_dict(prim_tle)["object_type"],
                "epoch": prim_tle.epoch.isoformat(),
                "age_days": prim_age
            },
            "secondary": {
                "name": event["name2"],
                "norad_id": event["norad_id2"],
                "rcs": event["obj2_rcs"],
                "maneuverable": event["obj2_maneuverable"],
                "object_type": _tle_to_dict(sec_tle)["object_type"],
                "epoch": sec_tle.epoch.isoformat(),
                "age_days": sec_age
            },
            "tca": event["tca"].isoformat(),
            "miss_distance_km": assessment.miss_distance_km,
            "relative_velocity_km_s": assessment.relative_velocity_km_s,
            "risk_score": assessment.score,
            "risk_category": assessment.category,
            "time_to_tca_hours": assessment.time_to_tca_hours,
            "factors": assessment.factors,
            "recommendation": assessment.recommendation,
            "confidence": confidence
        })
        
    results.sort(key=lambda x: (-x["risk_score"], x["tca"]))
    
    cache["conjunctions"] = results
    cache["last_screen_params"] = params
    cache["last_screen_time"] = now
    
    return {"conjunctions": results}
>>>>>>> a5ea05b (feat: implement Space Debris Tracking & Collision Risk Dashboard - Add satellite.js for real orbital position computation - Add ObjectInfoPanel, RiskBreakdownChart, LoadingOverlay components - Enhance backend API with health endpoint, confidence tags, data source selector - Expand Zustand store with layer visibility, auto-refresh, TLE staleness filters - Update TopBar, ControlPanel, ConjunctionList, EventDetail with full feature set - Add satellite.js type declarations)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orbveil.api.main:app", host="0.0.0.0", port=8000, reload=True)
