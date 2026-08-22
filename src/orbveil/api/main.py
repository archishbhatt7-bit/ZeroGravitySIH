from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import requests
import asyncio
from datetime import datetime

from orbveil.core.tle import parse_tle, TLE
from orbveil.core.screening import screen_catalog, ConjunctionEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OrbVeil API",
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orbveil.api.main:app", host="0.0.0.0", port=8000, reload=True)
