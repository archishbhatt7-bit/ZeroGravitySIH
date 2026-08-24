# QuickStart

Get from zero to your first conjunction screening in under 5 minutes.

## Install

```bash
pip install zerogravity
```

**Requirements:** Python 3.10+. Dependencies (`sgp4`, `numpy`, `scipy`) install automatically.

## Your First Screening in 10 Lines

Screen the ISS against active LEO objects using TLEs from CelesTrak:

```python
import requests
from zerogravity import parse_tle, screen

# Fetch current TLEs from CelesTrak
iss_text = requests.get("https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE").text
catalog_text = requests.get(
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=TLE"
).text

# Parse TLEs
iss = parse_tle(iss_text)[0]
catalog = parse_tle(catalog_text)

# Screen ISS against the catalog — 7 days, 10 km threshold
events = screen(iss, catalog, days=7, threshold_km=10.0)

# Print results
for e in events[:10]:
    print(f"NORAD {e.secondary_norad_id}: {e.miss_distance_km:.3f} km at {e.tca}")
```

## Understanding the Results

`screen()` returns a list of `ConjunctionEvent` objects, sorted by miss distance (closest first):

```python
event = events[0]
event.primary_norad_id  # 25544 (ISS)
event.secondary_norad_id  # NORAD ID of the other object
event.tca  # datetime — Time of Closest Approach (UTC)
event.miss_distance_km  # predicted miss distance
event.relative_velocity_km_s  # closing speed at TCA
```

**What the numbers mean:**

| Miss Distance | Severity | Action |
|---|---|---|
| < 1 km | 🔴 Critical | Prepare avoidance maneuver |
| 1–5 km | 🟡 Watch | Monitor with updated tracking |
| 5–10 km | 🟢 Awareness | Standard catalog maintenance |

**Relative velocity matters too.** A 1 km miss at 14 km/s (head-on LEO) is far more dangerous than 1 km at 0.01 km/s (co-orbital).

## Full Catalog Screening

For all-on-all screening (every object against every other), use `screen_catalog()` with KD-tree acceleration:

```python
from zerogravity import parse_tle, screen_catalog

catalog = parse_tle(open("catalog.tle").read())
events = screen_catalog(catalog, hours=24, threshold_km=5.0)

print(f"Found {len(events)} close approaches in 24 hours")
```

## Using Space-Track Instead of CelesTrak

If you have a [Space-Track.org](https://www.space-track.org) account:

```python
from zerogravity import SpaceTrackClient

client = SpaceTrackClient(identity="you@email.com", password="your_password")

# Fetch a single TLE
iss = client.fetch_tle(25544)

# Fetch the full active catalog
catalog = client.fetch_catalog(epoch=">now-3", decay_date="null-val")
```

## Next Steps

- **[API Reference](api-reference.md)** — Every function, every parameter
- **[Examples](examples.md)** — 5 real-world workflows you can copy-paste
