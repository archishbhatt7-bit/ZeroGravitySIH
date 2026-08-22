# OrbVeil Project Memory & Architecture Plan

**IMPORTANT NOTE FOR AI AGENTS:** 
If you are an AI assistant reading this file, you are likely working with the Frontend Developer on a separate workstation. Your primary goal is to build out the `dashboard/` directory using Vite, React, `react-globe.gl`, and vanilla CSS (Glassmorphism design). DO NOT modify the backend `src/orbveil/api/` logic unless absolutely necessary for CORS or testing. The backend is being handled by another developer.

---

## 1. Project Goal
Transform the OrbVeil Python library into a stunning, full-stack web dashboard. 
- **The Core Feature:** A gorgeous 3D interactive Earth that visualizes satellite orbits and pinpoints potential collision events (conjunctions) in real-time.
- **The UI:** A glassmorphic dashboard floating over the 3D globe, displaying risk assessments and satellite catalog data.

## 2. Division of Labor

### Backend Developer (Working in `src/orbveil/api/` & `src/orbveil/core/`)
- Runs FastAPI on `localhost:8000`
- Wraps the core OrbVeil KD-tree screening and Monte Carlo/Foster probability functions.
- Serves REST endpoints to feed data to the frontend.

### Frontend Developer (Working in `dashboard/`)
- Runs Vite Dev Server on `localhost:5173`
- Builds the React components and handles all 3D Globe interactions.
- Ensures a premium, dark-mode, neon-accented UI.

---

## 3. The API Contract (Mock Data vs Real Data)

While the Backend Developer builds the actual endpoints, the Frontend Developer should use these JSON structures to build and test the UI.

### A. Satellite Catalog (`GET /api/satellites`)
Used to populate the 3D globe and the search bar.
```json
{
  "satellites": [
    {
      "norad_id": 25544,
      "name": "ISS (ZARYA)",
      "lat": 45.2,
      "lng": -120.5,
      "alt": 0.06,
      "color": "cyan"
    }
  ]
}
```

### B. Conjunction Risk Feed (`GET /api/conjunctions`)
Used to populate the dashboard warning feed and draw glowing impact points on the globe.
```json
{
  "conjunctions": [
    {
      "primary_id": 25544,
      "secondary_id": 43013,
      "tca": "2026-08-25T14:30:00Z",
      "miss_distance_km": 2.4,
      "probability": 1.2e-4,
      "severity": "high",
      "lat": 12.3,
      "lng": 45.6,
      "alt": 0.06
    }
  ]
}
```

---

## 4. Frontend Design Guidelines
1. **Globe Integration:** Use `react-globe.gl` as the full-screen background (`z-index: 1`).
2. **Dashboard UI:** Use floating glassmorphism panels (`z-index: 10`). 
   - `background: rgba(20, 20, 25, 0.65)`
   - `backdrop-filter: blur(16px)`
3. **Animations:** Make sure data updates smoothly. When a user clicks a conjunction in the side panel, animate the globe's camera to focus on those `lat/lng/alt` coordinates.
4. **Development:** Use `npm run dev` in the `dashboard/` folder.

## 5. Launch Instructions
You can launch both the frontend and backend simultaneously from the root directory using:
- Windows: `.\start.bat`
- Mac/Linux: `./start.sh`
