from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OrbVeil API",
    description="API for satellite conjunction screening and visualization.",
    version="0.1.0",
)

# Allow CORS for the dashboard frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "OrbVeil API is running", "status": "ok"}

@app.get("/api/satellites")
async def get_satellites():
    # TODO: Connect to orbveil.core to fetch the catalog
    return {"satellites": []}

@app.get("/api/conjunctions")
async def get_conjunctions():
    # TODO: Return conjunction screening results
    return {"conjunctions": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orbveil.api.main:app", host="0.0.0.0", port=8000, reload=True)
