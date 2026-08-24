"""Integration test: parse → propagate → screen end-to-end."""
from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest

from zerogravity.core.tle import TLE, parse_tle
from zerogravity.core.propagation import propagate
from zerogravity.core.screening import screen, ConjunctionEvent

# Hardcoded real TLEs (no network calls)
ISS_TLE_TEXT = """\
ISS (ZARYA)
1 25544U 98067A   24045.54896019  .00016717  00000-0  30093-3 0  9993
2 25544  51.6412 207.4925 0004948 290.5508 178.9792 15.49583488439596
"""

OTHER_TLES_TEXT = """\
CSS (TIANHE)
1 48274U 21035A   24045.50261574  .00021540  00000-0  25163-3 0  9993
2 48274  41.4681 279.1498 0005372 149.8847 345.3740 15.62096269157018
HST
1 20580U 90037B   24045.55478014  .00001456  00000-0  73052-4 0  9994
2 20580  28.4701  41.0696 0002622 348.3544 140.2428 15.09435694872912
NOAA 18
1 28654U 05018A   24045.52083333  .00000149  00000-0  10834-3 0  9994
2 28654  98.9710 100.7890 0014048 313.6230  46.3750 14.12905012970123
COSMOS 1408 DEB
1 51087U 82092HY  24045.40000000  .00013000  00000-0  73000-3 0  9999
2 51087  82.5600 120.3400 0050000 200.0000 160.0000 15.15000000 50000
FENGYUN 1C DEB
1 31141U 99025AYM 24045.50000000  .00003200  00000-0  42000-3 0  9999
2 31141  99.0700 200.1200 0030000 150.0000 210.0000 14.80000000 80000
"""


@pytest.fixture
def iss_tle() -> TLE:
    tles = parse_tle(ISS_TLE_TEXT)
    assert len(tles) == 1
    return tles[0]


@pytest.fixture
def catalog() -> list[TLE]:
    return parse_tle(OTHER_TLES_TEXT)


def test_parse_iss_tle(iss_tle: TLE):
    """Parse hardcoded ISS TLE."""
    assert iss_tle.norad_id == 25544
    assert iss_tle.name == "ISS (ZARYA)"


def test_propagate_iss_24h(iss_tle: TLE):
    """Propagate ISS 24 hours and verify position is in LEO range."""
    times = [iss_tle.epoch + timedelta(hours=h) for h in range(0, 25, 6)]
    states = propagate(iss_tle, times)
    assert len(states) == 5

    earth_radius_km = 6371.0
    for sv in states:
        r = np.linalg.norm(sv.position_km)
        alt = r - earth_radius_km
        # ISS altitude: ~400 km, allow 200-500 km
        assert 200 < alt < 500, f"ISS altitude {alt:.1f} km out of expected LEO range"


def test_screen_iss_against_catalog(iss_tle: TLE, catalog: list[TLE]):
    """Screen ISS against 5 hardcoded TLEs and verify result structure."""
    assert len(catalog) == 5
    events = screen(iss_tle, catalog, days=1.0, threshold_km=5000.0, step_minutes=60.0)
    assert isinstance(events, list)
    for event in events:
        assert isinstance(event, ConjunctionEvent)
        assert event.primary_norad_id == 25544
        assert event.miss_distance_km >= 0
        assert event.relative_velocity_km_s >= 0
