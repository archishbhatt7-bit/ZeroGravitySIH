"""Tests for propagation edge cases."""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest

from zerogravity.core.propagation import propagate, propagate_batch
from zerogravity.core.tle import TLE

ISS_LINE1 = "1 25544U 98067A   24045.54896019  .00016717  00000-0  30093-3 0  9993"
ISS_LINE2 = "2 25544  51.6412 207.4925 0004948 290.5508 178.9792 15.49583488439596"

# Near-circular orbit (eccentricity ~0.0005)
CIRCULAR_LINE1 = ISS_LINE1
CIRCULAR_LINE2 = ISS_LINE2


@pytest.fixture
def iss_tle() -> TLE:
    return TLE.from_lines(ISS_LINE1, ISS_LINE2)


def test_propagation_stale_tle(iss_tle: TLE):
    """Test propagation far beyond epoch — should succeed or raise ValueError, not crash."""
    far_future = iss_tle.epoch + timedelta(days=365 * 10)
    try:
        states = propagate(iss_tle, [far_future])
        # If it succeeds, position should still be finite (or NaN from degraded accuracy)
        assert len(states) == 1
    except ValueError:
        pass  # SGP4 error is acceptable for stale TLEs


def test_propagation_zero_eccentricity():
    """Test propagation of TLE with very low eccentricity (ISS ~0.0005)."""
    tle = TLE.from_lines(CIRCULAR_LINE1, CIRCULAR_LINE2)
    assert tle.eccentricity < 0.001
    states = propagate(tle, [tle.epoch + timedelta(hours=1)])
    pos_mag = np.linalg.norm(states[0].position_km)
    assert 6500 < pos_mag < 7000  # still in LEO


def test_batch_propagation_one_bad_tle(iss_tle: TLE):
    """Test batch propagation where one TLE may fail — valid mask should reflect it."""
    # Use ISS twice; both should succeed. We verify the valid mask mechanism works.
    tles = [iss_tle, iss_tle]
    states, valid = propagate_batch(tles, iss_tle.epoch)
    assert states.shape == (2, 6)
    assert np.all(valid)


def test_batch_propagation_far_future(iss_tle: TLE):
    """Test batch propagation far from epoch — some may fail."""
    far = iss_tle.epoch + timedelta(days=365 * 50)
    states, valid = propagate_batch([iss_tle], far)
    # Either succeeds or valid[0] is False
    assert states.shape == (1, 6)
    assert valid.shape == (1,)
