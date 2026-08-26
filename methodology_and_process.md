# ZeroGravity Methodology & Process

This document outlines the core scientific methodology behind ZeroGravity's conjunction screening algorithms, as well as the software development and validation processes used to maintain the project.

## 1. Scientific Methodology

ZeroGravity is designed for full catalog conjunction screening and collision probability analysis using public Two-Line Element (TLE) data.

### 1.1 Screening Pipeline
The conjunction screening pipeline processes over 30,000 objects (active payloads, debris, rocket bodies) efficiently through multiple filtering stages:

1. **Orbital Shell Prefilter:** Compares apogee/perigee bounds to eliminate objects that can never intersect geometrically, discarding ~85% of pairs without the need for propagation.
2. **Batch SGP4 Propagation:** Propagates the remaining ~800 candidate objects across the required time window (e.g., 7 days) in vectorized batches using a C-level `SatrecArray`.
3. **KD-Tree Spatial Query:** At each propagation time step, constructs a KD-tree to identify pairs within a specified spatial threshold in $O(n \log n)$ time.
4. **TCA Refinement:** Performs a bisection search around identified close approaches to pinpoint the exact Time of Closest Approach (TCA) to sub-second precision.

### 1.2 Collision Probability ($P_c$)
Once a conjunction is identified, ZeroGravity computes the probability of collision using two methods:
- **Foster (1992):** An analytical method that projects combined position covariance onto the B-plane (perpendicular to relative velocity) and integrates the bivariate normal PDF over the hard-body disk via numerical quadrature.
- **Monte Carlo:** Samples from combined position uncertainty to count B-plane impacts, serving as a robust fallback and validation tool for non-Gaussian uncertainty distributions.

---

## 2. Validation Process

Safety-critical tools require extreme transparency and rigorous validation. ZeroGravity is cross-validated daily against real Conjunction Data Messages (CDMs) issued by the 18th Space Defense Squadron (18 SDS).

### 2.1 Validation Metrics
- **Success Rate:** 100% of conjunctions in the test set must be independently detected.
- **Miss Distance Error:** Tracked against precision SP ephemerides used by 18 SDS (current median error: ~0.94 km).
- **TCA Offset:** Evaluated against ground truth to ensure sub-minute accuracy.

*Note: SGP4/TLE propagation inherently lacks the precision of numerical SP ephemerides. ZeroGravity is validated for operational screening (flagging events for investigation) rather than definitive maneuver planning.*

---

## 3. Development & Architecture Process

ZeroGravity is structured as a full-stack application, divided into a Python-based core/backend and a React-based frontend dashboard.

### 3.1 Backend Process (Python / FastAPI)
- **Role:** Handles heavy computation (KD-tree screening, Foster/MC probability) and serves REST endpoints.
- **Data Flow:** Retrieves TLEs and CDMs from Space-Track.org or local files, processes the data, and exposes JSON responses to the frontend.
- **Execution:** Runs via `uvicorn` on port 8000.

### 3.2 Frontend Process (React / Vite)
- **Role:** Provides an immersive, 3D command-center UI for visualizing orbits and conjunctions.
- **Design Methodology (Glassmorphism):** Uses a "Hero Background" layout with a full-screen `react-globe.gl` instance. UI panels float above the globe with translucent, frosted glass effects (`backdrop-filter: blur(24px)`), relying on neon accents (Cyan, Amber, Crimson) to denote risk severity.
- **Execution:** Runs via Vite Dev Server on port 5173.

### 3.3 Collaboration & API Contract
Development relies on strict API contracts between the frontend and backend. The frontend utilizes mock JSON structures during UI prototyping to ensure non-blocking development. When the backend endpoints (`/api/satellites`, `/api/conjunctions`) are finalized, the frontend switches from mock data to real-time screening results.
