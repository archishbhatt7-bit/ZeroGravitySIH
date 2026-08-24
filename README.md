# 🛰️ ZeroGravity

**Open-source satellite conjunction screening for Python.**

Screen the full public catalog for close approaches, compute collision probability, parse CDMs. Built for engineers who need transparency in safety-critical decisions.

[![PyPI](https://img.shields.io/pypi/v/zerogravity?color=blue)](https://pypi.org/project/zerogravity/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/ncdrone/zerogravity/actions/workflows/tests.yml/badge.svg)](https://github.com/ncdrone/zerogravity/actions)

```bash
pip install zerogravity
```

## Screen ISS in 5 Lines

```python
from zerogravity import parse_tle, screen

catalog = parse_tle(open("catalog.tle").read())
iss = next(s for s in catalog if s.satnum == 25544)
events = screen(iss, catalog, days=7, threshold_km=10.0)

for e in events:
    print(f"NORAD {e.secondary_norad_id}: {e.miss_distance_km:.2f} km at {e.tca}")
```

## Why ZeroGravity?

Every major conjunction assessment tool is closed-source. When your satellite's safety depends on a collision probability number, you should be able to read the code that computed it.

| | ZeroGravity | Orekit | poliastro | AGI STK | CARA (18 SDS) |
|---|---|---|---|---|---|
| **Language** | Python | Java | Python (archived) | C++/.NET | Internal |
| **Open source** | ✅ Apache 2.0 | ✅ Apache 2.0 | ✅ (archived) | ❌ Commercial | ❌ Gov only |
| **Conjunction screening** | ✅ Full catalog | ✅ | ❌ | ✅ | ✅ |
| **Collision probability** | ✅ Foster + MC | ✅ Multiple | ❌ | ✅ | ✅ |
| **CDM parsing** | ✅ KVN + XML | ✅ | ❌ | ✅ | N/A |
| **Install** | `pip install` | Maven + config | `pip install` | Installer | N/A |
| **Scope** | CA-focused | Full astrodynamics | General orbital mechanics | Everything | CA operations |

**ZeroGravity's niche:** Python-native, pip-installable, focused entirely on conjunction assessment. No JVM, no XML configuration, no license keys. Five lines to screen a satellite.

> **Note:** poliastro, the main Python orbital mechanics library, [was archived in 2024](https://github.com/poliastro/poliastro). ZeroGravity fills the conjunction assessment gap in the Python space ecosystem.

## What It Does

- **Web Dashboard & API** — Interactive 3D Earth visualization of satellite orbits and potential collision events using a React/Vite frontend and FastAPI backend.
- **Full catalog screening** — 30,070 objects (active satellites, debris, rocket bodies, unknown objects) in ~15-20 seconds via KD-tree spatial indexing + batch SGP4
- **Debris-on-payload screening** — identify threats from rocket bodies, defunct satellites, and tracked debris
- **Collision probability** — Foster (1992) analytical method + Monte Carlo sampling
- **CDM parsing** — CCSDS 508.0-B-1 standard (KVN + XML formats)
- **Space-Track integration** — fetch TLEs, catalog, and CDMs directly
- **Daily screening capable** — automated conjunction assessment for operational satellite safety
- **Validated** — cross-validated daily against 340+ real CDMs from 18th Space Defense Squadron ([results](https://zerogravity.com/validation))

## Benchmarks

Tested on Jetson Orin Nano ($249, ARM, 8GB) — your laptop will be faster:

| Operation | Scale | Time |
|---|---|---|
| Full catalog propagation (batch SGP4) | 30,070 objects | ~40 ms |
| Orbital shell prefilter | 30,070 → ~800 | <1 ms |
| KD-tree construction | ~800 objects × 168 steps | ~80 ms |
| Conjunction screening (7 days) | 1 vs full catalog | ~15-20 sec |
| Collision probability (Foster 1992) | 1 event | <1 ms |
| Collision probability (Monte Carlo, 100k) | 1 event | ~200 ms |
| CDM parsing (KVN) | 1 message | <1 ms |

## Validation

Cross-validated daily against real Conjunction Data Messages from the 18th Space Defense Squadron. Latest results:

| Metric | Result |
|---|---|
| CDMs tested | **340** |
| Success rate | **100%** (all conjunctions independently detected) |
| Median miss distance error | **0.94 km** (vs SP-based CDM ground truth) |
| Mean TCA offset | **< 1 minute** (99% within 60 seconds) |
| Within 5 km of CDM | **84%** |
| Within 10 km of CDM | **92%** |

The sub-1 km median error reflects the difference between SGP4/TLE propagation and precision SP ephemerides used by 18th SDS. For screening (finding events to investigate), this is well within operational utility. Full validation methodology and live results at [zerogravity.com/validation](https://zerogravity.com/validation).

## Usage

### Compute Collision Probability

```python
from zerogravity import compute_pc, PcMethod
import numpy as np

result = compute_pc(
    pos1_km=np.array([7000.0, 0.0, 0.0]),
    vel1_km_s=np.array([0.0, 7.5, 0.0]),
    pos2_km=np.array([7000.3, 0.0, 0.4]),
    vel2_km_s=np.array([0.0, -6.5, 1.5]),
    cov1=np.eye(6) * 0.07**2,
    cov2=np.eye(6) * 0.07**2,
    hard_body_radius_m=20.0,
    method=PcMethod.FOSTER_1992,
)
print(f"Pc = {result.probability:.2e}")
```

### Parse CDMs

```python
from zerogravity import CDM

cdm = CDM.from_kvn(open("conjunction.kvn").read())
print(f"TCA: {cdm.tca}")
print(f"Miss distance: {cdm.miss_distance_km:.3f} km")
print(f"Pc: {cdm.collision_probability:.2e}")
```

### Fetch from Space-Track

```python
from zerogravity import SpaceTrackClient

client = SpaceTrackClient(identity="you@email.com", password="password")
catalog = client.fetch_catalog()
cdms = client.fetch_cdms(days=7)
```

## Web Dashboard

ZeroGravity includes a full-stack web dashboard that visualizes satellite orbits and pinpoints potential collision events in real-time.

- **Backend:** FastAPI REST API wrapping the core screening and probability functions.
- **Frontend:** React + Vite application featuring a glassmorphic UI and 3D globe visualization (`react-globe.gl`).

### Launching the Dashboard

You can launch both the frontend and backend simultaneously from the root directory:

**Windows:**
```cmd
.\start.bat
```

**Mac/Linux:**
```bash
./start.sh
```

- API runs on `http://localhost:8000`
- Dashboard runs on `http://localhost:5173`

## How It Works

### Screening Pipeline

```
Full catalog (30,070 objects: active, debris, rocket bodies, unknown)
    │
    ▼
┌─────────────────────────┐
│ Orbital Shell Prefilter  │  Compare apogee/perigee bounds
│ ~85% eliminated          │  No propagation needed
└─────────────────────────┘
    │ ~800 candidates
    ▼
┌─────────────────────────┐
│ Batch SGP4 Propagation   │  SatrecArray (C-level, vectorized)
│ 168 time steps (7 days)  │  ~40ms for full catalog
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ KD-Tree Spatial Query    │  Per time step, find pairs within threshold
│ O(n log n) construction  │
└─────────────────────────┘
    │ flagged pairs
    ▼
┌─────────────────────────┐
│ TCA Refinement           │  Bisection search
│ ~1 second precision      │  Sub-second propagation steps
└─────────────────────────┘
    │
    ▼
  Conjunction events with TCA, miss distance, relative velocity
```

### Collision Probability

- **Foster (1992)** — projects combined position covariance onto the B-plane (perpendicular to relative velocity), integrates bivariate normal PDF over the hard-body disk via numerical quadrature.
- **Monte Carlo** — samples from combined position uncertainty, counts B-plane impacts. Useful for validation and non-Gaussian uncertainty.

## Modules

| Module | Description |
|---|---|
| `zerogravity.core.tle` | TLE parsing (wraps sgp4) |
| `zerogravity.core.propagation` | SGP4 propagation + batch via SatrecArray |
| `zerogravity.core.screening` | Conjunction screening with orbital shell prefilter + KD-tree |
| `zerogravity.core.probability` | Collision probability (Foster 1992 + Monte Carlo) |
| `zerogravity.data.cdm` | CDM parser (CCSDS 508.0-B-1, KVN + XML) |
| `zerogravity.data.spacetrack` | Space-Track.org API client |

## Limitations

Being honest about what ZeroGravity is and isn't:

- **SGP4/TLE only** — no high-precision numerical propagation (SP). Position errors grow with propagation time (~1 km at epoch, worse at 7 days). This is inherent to TLE data, not a bug.
- **No orbit determination** — we don't generate covariance from observations. Covariance comes from CDMs or user input.
- **No maneuver planning** — we tell you about conjunctions, not how to avoid them.
- **Single-threaded** — fast enough for single-satellite operations, not optimized for constellation-scale screening (6,000+ primaries).
- **No atmospheric drag modeling beyond SGP4's built-in** — during geomagnetic storms, TLE accuracy degrades.
- **Not a replacement for operational CA services** — 18th SDS and commercial providers use SP ephemerides with much higher fidelity. ZeroGravity is for independent screening, research, education, and small teams.

## Roadmap

- [ ] Numerical propagation option for owner ephemerides
- [ ] GPU-accelerated Monte Carlo (CUDA)
- [ ] Constellation-scale screening (multiprocessing)
- [ ] Covariance realism assessment
- [ ] REST API wrapper for operational deployment
- [ ] Conjunction visualization

## Getting the Catalog

You need a TLE catalog file. Options:

1. **Space-Track.org** (recommended) — free account, full catalog via API
   ```python
   from zerogravity import SpaceTrackClient

   client = SpaceTrackClient(identity="you@email.com", password="pw")
   catalog = client.fetch_catalog()
   ```
2. **CelesTrak** — `https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle` (active satellites only)
3. **CelesTrak Full Catalog** — `https://celestrak.org/NORAD/elements/gp.php?SPECIAL=gp-index&FORMAT=tle` (all 30K+ objects)
4. **Your own TLE file** — any standard two-line element format

## Data Sources

ZeroGravity screens the complete public catalog from trusted sources:

- **TLE Data**: CelesTrak and Space-Track.org provide Two-Line Element sets maintained by the 18th Space Defense Squadron (formerly JSpOC)
- **Full Catalog**: 30,070 tracked objects including:
  - Active satellites (payloads)
  - Rocket bodies (spent upper stages)
  - Debris (collision fragments, mission-related objects)
  - Unknown/unclassified objects
- **Object Classification**: SATCAT (Satellite Catalog) metadata provides object type, launch date, country, and operational status
- **CDMs**: Conjunction Data Messages from Space-Track.org provide high-fidelity state vectors and covariance for close approaches detected by 18 SDS

This comprehensive approach ensures debris-on-payload screening — identifying threats from defunct satellites and orbital debris that represent the majority of conjunction risk.

## Development

```bash
git clone https://github.com/ncdrone/zerogravity.git
cd zerogravity
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

## License

Apache 2.0 — use it, modify it, build on it. See [LICENSE](LICENSE).

## References

- Foster, J.L. (1992). "The Analytic Basis for Debris Avoidance Operations for the International Space Station"
- Chan, F.K. (1997). "Spacecraft Collision Probability"
- Alfano, S. (2005). "A Numerical Implementation of Spherical Object Collision Probability"
- CCSDS 508.0-B-1: "Conjunction Data Message" standard
- Vallado, D.A. "Fundamentals of Astrodynamics and Applications"

---

Built by [Autmori](https://autmori.com). Safety-critical tools should be transparent.
