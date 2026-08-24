"""ZeroGravity Quickstart — parse a TLE and inspect orbital elements."""

from zerogravity import parse_tle

# ISS (ZARYA) TLE
tle_text = """
ISS (ZARYA)
1 25544U 98067A   24045.54896019  .00016717  00000-0  30093-3 0  9993
2 25544  51.6412 207.4925 0004948 290.5508 178.9792 15.49583488439596
""".strip()

# Parse it
tles = parse_tle(tle_text)
iss = tles[0]

print(f"Satellite: {iss.name}")
print(f"NORAD ID:  {iss.norad_id}")
print(f"Epoch:     {iss.epoch}")
print(f"Incl:      {iss.inclination_deg:.4f}°")
print(f"Ecc:       {iss.eccentricity:.7f}")
print(f"Period:    {1440 / iss.mean_motion_rev_per_day:.1f} min")

# When screening is available (v0.2+):
# from zerogravity import screen
# events = screen(norad_id=25544, days=7)
# for e in events:
#     print(f"{e.tca} | {e.miss_distance_km:.2f} km | Pc={e.probability:.2e}")
