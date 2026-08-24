# API Reference

All public symbols are importable from the top-level `zerogravity` package:

```python
from zerogravity import parse_tle, screen, screen_catalog, compute_pc, CDM, SpaceTrackClient
```

---

## `zerogravity.core.tle` — TLE Parsing

### `parse_tle(text: str) -> list[TLE]`

Parse one or more TLEs from raw text. Handles both 2-line and 3-line (with name) formats. Skips unrecognized lines.

**Parameters:**

| Param | Type | Description |
|---|---|---|
| `text` | `str` | Raw TLE text — one or more TLE sets separated by newlines |

**Returns:** `list[TLE]`

```python
from zerogravity import parse_tle

text = """ISS (ZARYA)
1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9002
2 25544  51.6400 208.9163 0006703 300.3030  59.7487 15.49560722  8042"""

tles = parse_tle(text)
tle = tles[0]
tle.name  # "ISS (ZARYA)"
tle.norad_id  # 25544
tle.epoch  # datetime(2024, 1, 1, 12, 0, ..., tzinfo=UTC)
tle.inclination_deg  # 51.64
tle.eccentricity  # 0.0006703
tle.mean_motion_rev_per_day  # 15.4956...
```

### `TLE.from_lines(line1: str, line2: str, name: str = "") -> TLE`

Parse a single TLE from two lines. Raises `ValueError` if lines are malformed.

### `TLE` — Dataclass

Frozen dataclass with fields:

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Satellite name (line 0) |
| `line1` | `str` | Raw TLE line 1 |
| `line2` | `str` | Raw TLE line 2 |
| `norad_id` | `int` | NORAD catalog number |
| `epoch` | `datetime` | Epoch (UTC) |
| `inclination_deg` | `float` | Inclination (degrees) |
| `raan_deg` | `float` | Right ascension of ascending node (degrees) |
| `eccentricity` | `float` | Eccentricity |
| `arg_perigee_deg` | `float` | Argument of perigee (degrees) |
| `mean_anomaly_deg` | `float` | Mean anomaly (degrees) |
| `mean_motion_rev_per_day` | `float` | Mean motion (rev/day) |
| `bstar` | `float` | BSTAR drag term |
| `satrec` | `Satrec` | sgp4 Satrec object (for propagation) |

---

## `zerogravity.core.propagation` — Orbit Propagation

### `propagate(tle: TLE, times: list[datetime]) -> list[StateVector]`

Propagate a single TLE to multiple times using SGP4.

**Parameters:**

| Param | Type | Description |
|---|---|---|
| `tle` | `TLE` | Parsed TLE object |
| `times` | `list[datetime]` | UTC datetimes to propagate to |

**Returns:** `list[StateVector]`

**Raises:** `ValueError` if SGP4 propagation fails.

```python
from datetime import datetime, timezone, timedelta
from zerogravity import parse_tle, propagate

tle = parse_tle(tle_text)[0]
now = datetime.now(timezone.utc)
times = [now + timedelta(minutes=i * 10) for i in range(6)]

states = propagate(tle, times)
states[0].position_km  # np.array([x, y, z]) in TEME frame, km
states[0].velocity_km_s  # np.array([vx, vy, vz]) in TEME frame, km/s
states[0].epoch  # datetime
```

### `propagate_batch(tles: list[TLE], time: datetime) -> tuple[NDArray, NDArray]`

Propagate many TLEs to a single time using vectorized C-level SGP4 (`SatrecArray`). This is the fast path for large catalogs.

**Parameters:**

| Param | Type | Description |
|---|---|---|
| `tles` | `list[TLE]` | TLE objects to propagate |
| `time` | `datetime` | Single UTC datetime |

**Returns:** `tuple[NDArray[float64], NDArray[bool_]]`
- `positions_velocities`: shape `(n, 6)` — `[x, y, z, vx, vy, vz]` in km, km/s
- `valid_mask`: shape `(n,)` — `True` where propagation succeeded

```python
from datetime import datetime, timezone
from zerogravity import parse_tle, propagate_batch

catalog = parse_tle(catalog_text)
now = datetime.now(timezone.utc)

states, valid = propagate_batch(catalog, now)
print(f"{valid.sum()}/{len(catalog)} objects propagated successfully")
print(f"ISS position: {states[0, :3]} km")
```

### `StateVector` — Dataclass

| Field | Type | Description |
|---|---|---|
| `position_km` | `NDArray[float64]` | `[x, y, z]` in km (TEME) |
| `velocity_km_s` | `NDArray[float64]` | `[vx, vy, vz]` in km/s (TEME) |
| `epoch` | `datetime` | Time of this state |

---

## `zerogravity.core.screening` — Conjunction Screening

### `screen(primary, catalog, days=7.0, threshold_km=10.0, step_minutes=10.0) -> list[ConjunctionEvent]`

Screen primary object(s) against a catalog for close approaches.

**Algorithm:** Geometric prefilter → coarse time-stepped propagation → bisection refinement for accurate TCA.

**Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `primary` | `TLE \| list[TLE]` | — | Protected object(s) |
| `catalog` | `list[TLE]` | — | Objects to screen against |
| `days` | `float` | `7.0` | Screening window (days from primary epoch) |
| `threshold_km` | `float` | `10.0` | Miss distance threshold (km) |
| `step_minutes` | `float` | `10.0` | Coarse search step (minutes) |

**Returns:** `list[ConjunctionEvent]` sorted by miss distance (closest first).

```python
from zerogravity import parse_tle, screen

iss = parse_tle(iss_text)[0]
catalog = parse_tle(catalog_text)

events = screen(iss, catalog, days=3, threshold_km=5.0)
for e in events:
    print(f"{e.secondary_norad_id}: {e.miss_distance_km:.3f} km @ {e.tca}")
```

### `screen_catalog(tles, hours=24.0, step_minutes=10.0, threshold_km=10.0, max_tle_age_days=None, reference_time=None) -> list[ConjunctionEvent]`

All-on-all screening using vectorized propagation + KD-tree spatial indexing. Recommended for full-catalog screening.

**Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `tles` | `list[TLE]` | — | Full catalog |
| `hours` | `float` | `24.0` | Screening window (hours) |
| `step_minutes` | `float` | `10.0` | Propagation step (minutes) |
| `threshold_km` | `float` | `10.0` | Miss distance threshold (km) |
| `max_tle_age_days` | `float \| None` | `None` | Filter out stale TLEs |
| `reference_time` | `datetime \| None` | `None` | Start time (default: now UTC) |

**Returns:** `list[ConjunctionEvent]` sorted by miss distance.

```python
from zerogravity import parse_tle, screen_catalog

catalog = parse_tle(catalog_text)
events = screen_catalog(catalog, hours=48, threshold_km=5.0, max_tle_age_days=3)
```

### `filter_stale_tles(tles, max_age_days=3.0, reference_time=None) -> list[TLE]`

Remove TLEs older than `max_age_days` from the reference time.

**Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `tles` | `list[TLE]` | — | TLEs to filter |
| `max_age_days` | `float` | `3.0` | Maximum age (days) |
| `reference_time` | `datetime \| None` | `None` | Reference time (default: now UTC) |

**Returns:** `list[TLE]`

### `ConjunctionEvent` — Dataclass

| Field | Type | Description |
|---|---|---|
| `primary_norad_id` | `int` | NORAD ID of protected object |
| `secondary_norad_id` | `int` | NORAD ID of secondary object |
| `tca` | `datetime` | Time of closest approach (UTC) |
| `miss_distance_km` | `float` | Predicted miss distance (km) |
| `relative_velocity_km_s` | `float` | Relative velocity at TCA (km/s) |

---

## `zerogravity.core.risk` — Risk Assessment

### `assess_risk(miss_distance_km, relative_velocity_km_s, ...) -> RiskAssessment`

Score collision risk for a conjunction event on a 0–100 scale.

**Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `miss_distance_km` | `float` | — | Predicted miss distance (km) |
| `relative_velocity_km_s` | `float` | — | Relative velocity (km/s) |
| `obj1_rcs` | `str` | `"UNKNOWN"` | Object 1 radar cross-section: `SMALL`/`MEDIUM`/`LARGE`/`UNKNOWN` |
| `obj2_rcs` | `str` | `"UNKNOWN"` | Object 2 radar cross-section |
| `obj1_maneuverable` | `bool` | `False` | Can object 1 maneuver? |
| `obj2_maneuverable` | `bool` | `False` | Can object 2 maneuver? |
| `tca` | `datetime \| None` | `None` | Time of closest approach (for urgency scoring) |
| `now` | `datetime \| None` | `None` | Current time (default: now UTC) |

**Returns:** `RiskAssessment`

```python
from zerogravity.core.risk import assess_risk

result = assess_risk(
    miss_distance_km=0.8,
    relative_velocity_km_s=14.2,
    obj1_rcs="LARGE",
    obj1_maneuverable=True,
)
print(f"Score: {result.score}, Category: {result.category}")
print(result.recommendation)
# "CRITICAL ALERT: ..."
```

### `classify_events(events: list[dict]) -> list[RiskAssessment]`

Batch classify conjunction events. Each dict's keys match `assess_risk()` parameters.

```python
from zerogravity.core.risk import classify_events

assessments = classify_events(
    [
        {"miss_distance_km": 0.5, "relative_velocity_km_s": 10.0},
        {"miss_distance_km": 8.0, "relative_velocity_km_s": 3.0},
    ]
)
```

### `RiskAssessment` — Dataclass

| Field | Type | Description |
|---|---|---|
| `score` | `float` | 0–100 risk score |
| `category` | `str` | `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` / `NEGLIGIBLE` |
| `miss_distance_km` | `float` | Input miss distance |
| `relative_velocity_km_s` | `float` | Input relative velocity |
| `time_to_tca_hours` | `float \| None` | Hours until TCA |
| `factors` | `dict` | Breakdown: `distance_score`, `velocity_score`, `size_multiplier`, `maneuver_multiplier`, `urgency_multiplier`, `base_score` |
| `recommendation` | `str` | Human-readable action recommendation |

**Score thresholds:** ≥80 CRITICAL, ≥60 HIGH, ≥40 MEDIUM, ≥20 LOW, <20 NEGLIGIBLE.

---

## `zerogravity.core.formations` — Formation Detection

### `detect_formations(names, norad_ids, positions=None, velocities=None, cospar_ids=None) -> list[FormationGroup]`

Detect satellite formations from a list of objects. Uses name-based heuristics (ISS complex, CSS, TanDEM-X, MEV dockings, PIESAT/TIANHUI/O3B constellations), velocity-based co-location detection, and COSPAR launch-group analysis.

**Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `names` | `list[str]` | — | Object names |
| `norad_ids` | `list[int]` | — | NORAD catalog IDs |
| `positions` | `list[tuple[float,float,float]] \| None` | `None` | Position vectors (km, TEME) |
| `velocities` | `list[tuple[float,float,float]] \| None` | `None` | Velocity vectors (km/s, TEME) |
| `cospar_ids` | `list[str] \| None` | `None` | COSPAR/international designators |

**Returns:** `list[FormationGroup]`

```python
from zerogravity.core.formations import detect_formations

names = ["ISS (ZARYA)", "PROGRESS-MS 25", "SOYUZ-MS 26", "STARLINK-1234"]
norad_ids = [25544, 58000, 58001, 55000]

groups = detect_formations(names, norad_ids)
for g in groups:
    print(f"{g.name} ({g.reason}): {g.object_names}")
# ISS Complex (docked_modules): ['ISS (ZARYA)', 'PROGRESS-MS 25', 'SOYUZ-MS 26']
```

### `is_formation_pair(name1, name2, norad_id1, norad_id2, rel_velocity_km_s=0.0, distance_km=0.0) -> tuple[bool, str]`

Check if two specific objects form a formation pair.

**Returns:** `(is_formation, reason_string)` — reason is `""` if not a formation.

### `filter_formation_events(events, formations=None) -> tuple[list[dict], list[dict]]`

Separate conjunction events into real threats vs. formation encounters.

**Parameters:**

| Param | Type | Description |
|---|---|---|
| `events` | `list[dict]` | Events with keys: `name1`, `name2`, `norad_id1`, `norad_id2`, `relative_velocity_km_s`, `miss_distance_km` |
| `formations` | `list[FormationGroup] \| None` | Pre-detected formations (optional) |

**Returns:** `(real_threats, formation_events)` — two lists of event dicts.

### `FormationGroup` — Dataclass

| Field | Type | Description |
|---|---|---|
| `name` | `str` | e.g. "ISS Complex" |
| `reason` | `str` | `docked_modules` / `formation_flying` / `docked_servicing` / `velocity_based` / `rideshare_dispersing` |
| `norad_ids` | `list[int]` | NORAD IDs in the group |
| `object_names` | `list[str]` | Object names in the group |

---

## `zerogravity.core.probability` — Collision Probability

### `compute_pc(pos1_km, vel1_km_s, pos2_km, vel2_km_s, cov1, cov2, hard_body_radius_m=20.0, method=PcMethod.FOSTER_1992, mc_samples=100_000) -> PcResult`

Compute collision probability from state vectors and covariance matrices.

**Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `pos1_km` | `NDArray` | — | Primary position (km, ECI) |
| `vel1_km_s` | `NDArray` | — | Primary velocity (km/s, ECI) |
| `pos2_km` | `NDArray` | — | Secondary position (km, ECI) |
| `vel2_km_s` | `NDArray` | — | Secondary velocity (km/s, ECI) |
| `cov1` | `NDArray` | — | Primary 6×6 covariance (km, km/s) |
| `cov2` | `NDArray` | — | Secondary 6×6 covariance (km, km/s) |
| `hard_body_radius_m` | `float` | `20.0` | Combined hard-body radius (meters) |
| `method` | `PcMethod` | `FOSTER_1992` | `PcMethod.FOSTER_1992` or `PcMethod.MONTE_CARLO` |
| `mc_samples` | `int` | `100_000` | Monte Carlo samples (only for MC method) |

**Returns:** `PcResult`

```python
import numpy as np
from zerogravity import compute_pc, PcMethod

result = compute_pc(
    pos1_km=np.array([6800.0, 0.0, 0.0]),
    vel1_km_s=np.array([0.0, 7.5, 0.0]),
    pos2_km=np.array([6800.5, 0.1, 0.0]),
    vel2_km_s=np.array([0.0, -7.5, 0.0]),
    cov1=np.diag([0.1, 0.1, 0.1, 1e-4, 1e-4, 1e-4]),
    cov2=np.diag([0.1, 0.1, 0.1, 1e-4, 1e-4, 1e-4]),
    hard_body_radius_m=20.0,
)
print(f"Pc = {result.probability:.2e}")
print(f"Mahalanobis distance = {result.mahalanobis_distance:.2f}")
```

### `PcMethod` — Enum

- `PcMethod.FOSTER_1992` — B-plane projection + numerical integration (default, deterministic)
- `PcMethod.MONTE_CARLO` — Sample-based estimation (stochastic, set `mc_samples`)

### `PcResult` — Dataclass

| Field | Type | Description |
|---|---|---|
| `probability` | `float` | Collision probability (0–1) |
| `method` | `PcMethod` | Method used |
| `combined_hard_body_radius_m` | `float` | Hard-body radius (meters) |
| `mahalanobis_distance` | `float \| None` | Statistical distance |
| `samples` | `int \| None` | MC samples (if applicable) |

---

## `zerogravity.data.cdm` — CDM Parsing

### `CDM.from_kvn(text: str) -> CDM`

Parse a Conjunction Data Message from CCSDS KVN (Key-Value Notation) format.

```python
from zerogravity import CDM

cdm = CDM.from_kvn(open("conjunction.cdm").read())
print(f"TCA: {cdm.tca}")
print(f"Miss distance: {cdm.miss_distance_km} km")
print(f"Pc: {cdm.collision_probability}")
print(f"Object 1: {cdm.object1.name} (NORAD {cdm.object1.designator})")
```

### `CDM.from_xml(xml_text: str) -> CDM`

Parse a CDM from XML format (CCSDS 508.0-B-1).

### `CDM` — Dataclass

| Field | Type | Description |
|---|---|---|
| `ccsds_cdm_vers` | `str` | CDM version |
| `creation_date` | `datetime` | When the CDM was created |
| `originator` | `str` | Organization that created the CDM |
| `message_id` | `str` | Unique message identifier |
| `tca` | `datetime` | Time of closest approach |
| `miss_distance_km` | `float` | Miss distance (km) |
| `relative_speed_km_s` | `float` | Relative speed (km/s) |
| `collision_probability` | `float \| None` | Pc (may be absent) |
| `object1` | `CDMObject` | Primary object data |
| `object2` | `CDMObject` | Secondary object data |

### `CDMObject` — Dataclass

| Field | Type | Description |
|---|---|---|
| `designator` | `str` | NORAD ID as string |
| `name` | `str` | Object name |
| `international_designator` | `str` | COSPAR ID |
| `ephemeris_name` | `str` | Ephemeris source |
| `covariance_method` | `str` | Covariance calculation method |
| `maneuverable` | `str` | Maneuverability status |
| `x_km`, `y_km`, `z_km` | `float` | Position (km) |
| `x_dot_km_s`, `y_dot_km_s`, `z_dot_km_s` | `float` | Velocity (km/s) |
| `covariance` | `NDArray \| None` | 6×6 RTN covariance matrix |

---

## `zerogravity.data.spacetrack` — Space-Track API

### `SpaceTrackClient(identity: str, password: str)`

Authenticated client for the [Space-Track.org](https://www.space-track.org) REST API.

### `client.fetch_tle(norad_id: int) -> TLE`

Fetch the latest TLE for a NORAD catalog number.

**Raises:** `ValueError` if no TLE found, `requests.HTTPError` on network errors.

### `client.fetch_catalog(*, epoch: str = ">now-30", decay_date: str = "null-val") -> list[TLE]`

Fetch a catalog of TLEs. Default: active satellites with TLEs from the last 30 days.

| Param | Type | Default | Description |
|---|---|---|---|
| `epoch` | `str` | `">now-30"` | Epoch filter |
| `decay_date` | `str` | `"null-val"` | `"null-val"` = still in orbit |

### `client.fetch_cdms(*, norad_id: int | None = None, days: int = 7) -> list[CDM]`

Fetch recent Conjunction Data Messages. Requires CDM access permissions on Space-Track.

| Param | Type | Default | Description |
|---|---|---|---|
| `norad_id` | `int \| None` | `None` | Filter by NORAD ID |
| `days` | `int` | `7` | Look-back days |

```python
from zerogravity import SpaceTrackClient

client = SpaceTrackClient("you@email.com", "password")
iss = client.fetch_tle(25544)
cdms = client.fetch_cdms(norad_id=25544, days=3)
```

---

## `zerogravity.utils.constants`

Useful constants importable from `zerogravity.utils.constants`:

| Constant | Value | Description |
|---|---|---|
| `EARTH_RADIUS_KM` | 6378.137 | Equatorial radius (km) |
| `EARTH_MU_KM3_S2` | 398600.4418 | Gravitational parameter (km³/s²) |
| `DEFAULT_MISS_DISTANCE_KM` | 5.0 | Default screening threshold |
| `DEFAULT_PC_THRESHOLD` | 1e-4 | Default Pc alert threshold |
| `HARD_BODY_RADIUS_SMALL_M` | 1.0 | Small satellite (<100 kg) |
| `HARD_BODY_RADIUS_MEDIUM_M` | 5.0 | Medium satellite (100–1000 kg) |
| `HARD_BODY_RADIUS_LARGE_M` | 20.0 | Large satellite / upper stage |
| `LEO_MAX_ALT_KM` | 2000.0 | LEO boundary |
| `GEO_ALT_KM` | 35786.0 | GEO altitude |
