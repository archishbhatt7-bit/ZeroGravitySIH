# Examples

Five real-world workflows you can copy-paste and adapt.

---

## 1. Screen a Satellite Against the Full Catalog

Screen a specific satellite (e.g., Sentinel-2A) against all active objects.

```python
import requests
from zerogravity import parse_tle, screen

# Fetch TLEs
sentinel_text = requests.get(
    "https://celestrak.org/NORAD/elements/gp.php?CATNR=40697&FORMAT=TLE"
).text
catalog_text = requests.get(
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=TLE"
).text

sentinel = parse_tle(sentinel_text)[0]
catalog = parse_tle(catalog_text)

print(f"Screening Sentinel-2A against {len(catalog)} objects...")

# Screen 7 days ahead, flag anything within 5 km
events = screen(sentinel, catalog, days=7, threshold_km=5.0, step_minutes=10.0)

print(f"Found {len(events)} close approaches\n")

for e in events[:20]:
    print(
        f"  NORAD {e.secondary_norad_id:>6d} | "
        f"{e.miss_distance_km:8.3f} km | "
        f"{e.relative_velocity_km_s:6.2f} km/s | "
        f"TCA {e.tca:%Y-%m-%d %H:%M}"
    )
```

---

## 2. Daily Conjunction Screening for a Constellation

Run all-on-all screening for a Starlink shell using `screen_catalog()`.

```python
import requests
from datetime import datetime, timezone
from zerogravity import parse_tle, screen_catalog

# Fetch Starlink TLEs
starlink_text = requests.get(
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=TLE"
).text
catalog = parse_tle(starlink_text)
print(f"Loaded {len(catalog)} Starlink TLEs")

# Screen next 24 hours, 5 km threshold, skip TLEs older than 3 days
now = datetime.now(timezone.utc)
events = screen_catalog(
    catalog,
    hours=24,
    step_minutes=10.0,
    threshold_km=5.0,
    max_tle_age_days=3.0,
    reference_time=now,
)

print(f"\nFound {len(events)} close pairs in next 24h")

# Group by severity
critical = [e for e in events if e.miss_distance_km < 1.0]
watch = [e for e in events if 1.0 <= e.miss_distance_km < 3.0]
routine = [e for e in events if e.miss_distance_km >= 3.0]

print(f"  🔴 Critical (<1 km): {len(critical)}")
print(f"  🟡 Watch (1-3 km):   {len(watch)}")
print(f"  🟢 Routine (3+ km):  {len(routine)}")

# Detail on critical events
for e in critical:
    print(f"\n  ⚠️  NORAD {e.primary_norad_id} vs {e.secondary_norad_id}")
    print(f"     Miss: {e.miss_distance_km:.3f} km | Vel: {e.relative_velocity_km_s:.2f} km/s")
    print(f"     TCA:  {e.tca:%Y-%m-%d %H:%M:%S UTC}")
```

---

## 3. Parse and Analyze CDM Data

Parse CDMs from Space-Track and extract key metrics.

```python
from zerogravity import CDM, SpaceTrackClient
import numpy as np

# Option A: Parse a CDM file directly
cdm_text = open("conjunction_report.cdm").read()
cdm = CDM.from_kvn(cdm_text)

# Option B: Fetch CDMs from Space-Track
client = SpaceTrackClient("you@email.com", "password")
cdms = client.fetch_cdms(norad_id=25544, days=7)

# Analyze each CDM
for cdm in cdms:
    print(f"Message: {cdm.message_id}")
    print(f"  TCA:        {cdm.tca:%Y-%m-%d %H:%M:%S UTC}")
    print(f"  Miss:       {cdm.miss_distance_km:.3f} km")
    print(f"  Rel speed:  {cdm.relative_speed_km_s:.2f} km/s")
    print(
        f"  Pc:         {cdm.collision_probability:.2e}"
        if cdm.collision_probability
        else "  Pc:         N/A"
    )
    print(f"  Object 1:   {cdm.object1.name} (NORAD {cdm.object1.designator})")
    print(f"  Object 2:   {cdm.object2.name} (NORAD {cdm.object2.designator})")
    print(f"  Maneuverable: {cdm.object1.maneuverable} / {cdm.object2.maneuverable}")

    # Extract state vectors and covariance for your own Pc calculation
    pos1 = np.array([cdm.object1.x_km, cdm.object1.y_km, cdm.object1.z_km])
    vel1 = np.array([cdm.object1.x_dot_km_s, cdm.object1.y_dot_km_s, cdm.object1.z_dot_km_s])
    cov1 = cdm.object1.covariance  # 6x6 NDArray or None

    if cov1 is not None:
        # Position uncertainty (1-sigma, RSS)
        pos_sigma = np.sqrt(cov1[0, 0] + cov1[1, 1] + cov1[2, 2])
        print(f"  Obj1 pos σ: {pos_sigma:.4f} km")
    print()
```

### Parse XML CDMs

```python
cdm = CDM.from_xml(open("conjunction_report.xml").read())
```

---

## 4. Detect Formation-Flying Pairs

Filter out formation encounters from conjunction screening results.

```python
import requests
from zerogravity import parse_tle, screen_catalog
from zerogravity.core.formations import detect_formations, filter_formation_events
from zerogravity.core.propagation import propagate_batch
from datetime import datetime, timezone

# Fetch a mixed catalog (stations, active sats)
catalog_text = requests.get(
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=TLE"
).text
tles = parse_tle(catalog_text)

# Propagate to get positions/velocities for formation detection
now = datetime.now(timezone.utc)
states, valid = propagate_batch(tles, now)

# Extract data for valid objects
valid_tles = [t for t, v in zip(tles, valid) if v]
valid_states = states[valid]

names = [t.name for t in valid_tles]
norad_ids = [t.norad_id for t in valid_tles]
positions = [tuple(valid_states[i, :3]) for i in range(len(valid_tles))]
velocities = [tuple(valid_states[i, 3:6]) for i in range(len(valid_tles))]

# Detect formations
formations = detect_formations(names, norad_ids, positions, velocities)

print(f"Detected {len(formations)} formations:\n")
for f in formations:
    print(f"  {f.name} ({f.reason})")
    for name in f.object_names:
        print(f"    - {name}")
    print()

# Now screen and filter out formation alerts
events = screen_catalog(valid_tles, hours=24, threshold_km=5.0, reference_time=now)

# Convert events to dicts for filter_formation_events
event_dicts = [
    {
        "name1": next((t.name for t in valid_tles if t.norad_id == e.primary_norad_id), ""),
        "name2": next((t.name for t in valid_tles if t.norad_id == e.secondary_norad_id), ""),
        "norad_id1": e.primary_norad_id,
        "norad_id2": e.secondary_norad_id,
        "miss_distance_km": e.miss_distance_km,
        "relative_velocity_km_s": e.relative_velocity_km_s,
    }
    for e in events
]

real_threats, formation_alerts = filter_formation_events(event_dicts, formations)
print(
    f"Screening results: {len(real_threats)} real threats, {len(formation_alerts)} formation encounters filtered"
)
```

---

## 5. Score Risk for Conjunction Events

Combine screening results with risk assessment for actionable alerts.

```python
import requests
from datetime import datetime, timezone
from zerogravity import parse_tle, screen
from zerogravity.core.risk import assess_risk, classify_events

# Screen ISS
iss_text = requests.get("https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE").text
catalog_text = requests.get(
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=TLE"
).text

iss = parse_tle(iss_text)[0]
catalog = parse_tle(catalog_text)
events = screen(iss, catalog, days=7, threshold_km=10.0)

# Assess risk for each event
now = datetime.now(timezone.utc)

for e in events[:10]:
    risk = assess_risk(
        miss_distance_km=e.miss_distance_km,
        relative_velocity_km_s=e.relative_velocity_km_s,
        obj1_rcs="LARGE",  # ISS is large
        obj1_maneuverable=True,  # ISS can maneuver
        tca=e.tca,
        now=now,
    )

    icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "NEGLIGIBLE": "⚪"}
    print(f"{icon[risk.category]} [{risk.category}] Score: {risk.score}")
    print(
        f"   NORAD {e.secondary_norad_id} | {e.miss_distance_km:.3f} km | {e.relative_velocity_km_s:.1f} km/s"
    )
    if risk.time_to_tca_hours is not None:
        print(f"   TCA in {risk.time_to_tca_hours:.1f} hours")
    print(f"   → {risk.recommendation}")
    print()

# Batch classification alternative
event_dicts = [
    {"miss_distance_km": e.miss_distance_km, "relative_velocity_km_s": e.relative_velocity_km_s}
    for e in events
]
assessments = classify_events(event_dicts)

# Summary
from collections import Counter

counts = Counter(a.category for a in assessments)
print("Summary:")
for cat in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE"]:
    print(f"  {cat}: {counts.get(cat, 0)}")
```
