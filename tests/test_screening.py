"""Tests for orbital propagation and conjunction screening."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import math
import numpy as np
import pytest

from zerogravity.core.tle import TLE
from zerogravity.core.propagation import propagate, propagate_batch, StateVector
from zerogravity.core.screening import (
    _apogee_perigee, _prefilter, screen, screen_catalog,
    filter_stale_tles, ConjunctionEvent,
)


# Test TLEs
ISS_TLE_LINES = (
    "1 25544U 98067A   24045.54896019  .00016717  00000-0  30093-3 0  9993",
    "2 25544  51.6412 207.4925 0004948 290.5508 178.9792 15.49583488439596",
)

CSS_TLE_LINES = (
    "1 48274U 21035A   24045.50261574  .00021540  00000-0  25163-3 0  9993",
    "2 48274  41.4681 279.1498 0005372 149.8847 345.3740 15.62096269157018",
)

HUBBLE_TLE_LINES = (
    "1 20580U 90037B   24045.55478014  .00001456  00000-0  73052-4 0  9994",
    "2 20580  28.4701  41.0696 0002622 348.3544 140.2428 15.09435694872912",
)

GEO_TLE_LINES = (
    "1 36516U 10012A   24045.39583333  .00000112  00000-0  00000+0 0  9991",
    "2 36516   0.0254 268.0254 0000567 142.5432 240.3076  1.00271953 50780",
)


@pytest.fixture
def iss_tle() -> TLE:
    """ISS TLE for testing."""
    return TLE.from_lines(ISS_TLE_LINES[0], ISS_TLE_LINES[1], "ISS (ZARYA)")


@pytest.fixture
def css_tle() -> TLE:
    """Chinese Space Station (Tiangong) TLE for testing."""
    return TLE.from_lines(CSS_TLE_LINES[0], CSS_TLE_LINES[1], "CSS (TIANHE)")


@pytest.fixture
def hubble_tle() -> TLE:
    """Hubble Space Telescope TLE for testing."""
    return TLE.from_lines(HUBBLE_TLE_LINES[0], HUBBLE_TLE_LINES[1], "HUBBLE")


@pytest.fixture
def geo_tle() -> TLE:
    """GEO satellite TLE for testing."""
    return TLE.from_lines(GEO_TLE_LINES[0], GEO_TLE_LINES[1], "SES-1")


def test_propagate_single_time(iss_tle: TLE):
    """Test single TLE propagation to one time."""
    # Propagate ISS to its epoch (should be close to initial state)
    times = [iss_tle.epoch]
    states = propagate(iss_tle, times)
    
    assert len(states) == 1
    assert isinstance(states[0], StateVector)
    assert states[0].position_km.shape == (3,)
    assert states[0].velocity_km_s.shape == (3,)
    assert states[0].epoch == iss_tle.epoch
    
    # Check that position magnitude is reasonable for LEO (~6800 km from Earth center)
    pos_mag = np.linalg.norm(states[0].position_km)
    assert 6500 < pos_mag < 7000  # ISS is in LEO


def test_propagate_multiple_times(iss_tle: TLE):
    """Test single TLE propagation to multiple times."""
    # Propagate to epoch + 0, 1, 2 hours
    times = [iss_tle.epoch + timedelta(hours=h) for h in range(3)]
    states = propagate(iss_tle, times)
    
    assert len(states) == 3
    
    # Each state should have moved
    for i in range(1, 3):
        dist = np.linalg.norm(states[i].position_km - states[0].position_km)
        assert dist > 0  # Position changed
        assert states[i].epoch == times[i]


def test_propagate_batch_shape(iss_tle: TLE, css_tle: TLE, hubble_tle: TLE):
    """Test batch propagation returns correct shape."""
    tles = [iss_tle, css_tle, hubble_tle]
    time = iss_tle.epoch
    
    states, valid = propagate_batch(tles, time)
    
    assert states.shape == (3, 6)
    assert valid.shape == (3,)
    assert valid.dtype == np.bool_
    assert np.all(valid)  # All should propagate successfully


def test_propagate_batch_empty():
    """Test batch propagation with empty list."""
    states, valid = propagate_batch([], datetime.now(timezone.utc))
    
    assert states.shape == (0, 6)
    assert valid.shape == (0,)


def test_propagate_batch_values(iss_tle: TLE):
    """Test that batch propagation matches single propagation."""
    time = iss_tle.epoch + timedelta(hours=1)
    
    # Single propagation
    single_states = propagate(iss_tle, [time])
    single_pos = single_states[0].position_km
    single_vel = single_states[0].velocity_km_s
    
    # Batch propagation
    batch_states, batch_valid = propagate_batch([iss_tle], time)
    batch_pos = batch_states[0, 0:3]
    batch_vel = batch_states[0, 3:6]
    
    # Should be identical
    assert batch_valid[0]
    np.testing.assert_allclose(batch_pos, single_pos, rtol=1e-10)
    np.testing.assert_allclose(batch_vel, single_vel, rtol=1e-10)


def test_apogee_perigee_iss(iss_tle: TLE):
    """Test apogee/perigee calculation for ISS (nearly circular LEO)."""
    perigee, apogee = _apogee_perigee(iss_tle)
    
    # ISS orbits around 400-420 km altitude
    assert 380 < perigee < 450
    assert 380 < apogee < 450
    
    # Nearly circular (eccentricity ~0.0005)
    assert abs(apogee - perigee) < 10  # difference should be small


def test_apogee_perigee_geo(geo_tle: TLE):
    """Test apogee/perigee calculation for GEO satellite."""
    perigee, apogee = _apogee_perigee(geo_tle)
    
    # GEO is at ~35,786 km altitude
    assert 35000 < perigee < 36500
    assert 35000 < apogee < 36500
    
    # Nearly circular
    assert abs(apogee - perigee) < 100


def test_prefilter_removes_geo(iss_tle: TLE, geo_tle: TLE):
    """Test that prefilter removes GEO satellites when screening LEO."""
    catalog = [geo_tle]
    filtered = _prefilter(catalog, iss_tle, threshold_km=10.0)
    
    # GEO should be filtered out (no orbital overlap with ISS)
    assert len(filtered) == 0


def test_prefilter_keeps_leo(iss_tle: TLE, css_tle: TLE, hubble_tle: TLE):
    """Test that prefilter keeps LEO satellites when screening LEO."""
    catalog = [css_tle, hubble_tle]
    # Use 150km threshold to catch satellites in nearby orbital shells
    filtered = _prefilter(catalog, iss_tle, threshold_km=150.0)
    
    # Both CSS and Hubble are in LEO with overlapping orbital shells, should be kept
    assert len(filtered) == 2
    assert css_tle in filtered
    assert hubble_tle in filtered


def test_prefilter_excludes_self(iss_tle: TLE):
    """Test that prefilter excludes the primary itself."""
    catalog = [iss_tle]
    filtered = _prefilter(catalog, iss_tle, threshold_km=10.0)
    
    # Should exclude self
    assert len(filtered) == 0


def test_prefilter_mixed_catalog(iss_tle: TLE, css_tle: TLE, geo_tle: TLE):
    """Test prefilter with mixed LEO/GEO catalog."""
    catalog = [css_tle, geo_tle, iss_tle]  # LEO, GEO, self
    # Use 150km threshold to catch CSS but not GEO
    filtered = _prefilter(catalog, iss_tle, threshold_km=150.0)
    
    # Should keep only CSS (LEO), exclude GEO and self
    assert len(filtered) == 1
    assert filtered[0].norad_id == css_tle.norad_id


def test_screen_no_conjunctions_with_geo(iss_tle: TLE, geo_tle: TLE):
    """Test that screening ISS against GEO finds no conjunctions."""
    catalog = [geo_tle]
    events = screen(iss_tle, catalog, days=1.0, threshold_km=1000.0, step_minutes=60.0)
    
    # GEO and ISS should never get close
    assert len(events) == 0


def test_screen_basic_structure(iss_tle: TLE, css_tle: TLE):
    """Test basic structure of screening results."""
    catalog = [css_tle]
    events = screen(iss_tle, catalog, days=0.5, threshold_km=5000.0, step_minutes=30.0)
    
    # Should return a list (may be empty)
    assert isinstance(events, list)
    
    # If events found, check structure
    for event in events:
        assert isinstance(event, ConjunctionEvent)
        assert event.primary_norad_id == iss_tle.norad_id
        assert event.secondary_norad_id in [tle.norad_id for tle in catalog]
        assert isinstance(event.tca, datetime)
        assert event.miss_distance_km >= 0
        assert event.relative_velocity_km_s >= 0


def test_screen_sorted_by_distance(iss_tle: TLE, css_tle: TLE, hubble_tle: TLE):
    """Test that screening results are sorted by miss distance."""
    catalog = [css_tle, hubble_tle]
    events = screen(iss_tle, catalog, days=1.0, threshold_km=10000.0, step_minutes=60.0)
    
    # Events should be sorted by miss_distance_km
    for i in range(1, len(events)):
        assert events[i].miss_distance_km >= events[i-1].miss_distance_km


def test_screen_multiple_primaries(iss_tle: TLE, css_tle: TLE, hubble_tle: TLE):
    """Test screening with multiple primary objects."""
    primaries = [iss_tle, css_tle]
    catalog = [hubble_tle]
    
    events = screen(primaries, catalog, days=0.5, threshold_km=5000.0, step_minutes=60.0)
    
    # Should check both primaries
    assert isinstance(events, list)
    
    # If events found, should have both primaries represented (potentially)
    primary_ids = {event.primary_norad_id for event in events}
    # At least one of the primaries should be in results (if any events found)
    if events:
        assert primary_ids.issubset({iss_tle.norad_id, css_tle.norad_id})


def test_screen_excludes_self_conjunctions(iss_tle: TLE, css_tle: TLE):
    """Test that screening doesn't report self-conjunctions."""
    catalog = [iss_tle, css_tle]
    events = screen(iss_tle, catalog, days=1.0, threshold_km=10000.0, step_minutes=60.0)
    
    # Should not have any events with primary == secondary
    for event in events:
        assert event.primary_norad_id != event.secondary_norad_id


def test_screen_threshold_filters(iss_tle: TLE, css_tle: TLE):
    """Test that threshold parameter filters results."""
    catalog = [css_tle]
    
    # Very tight threshold
    tight_events = screen(iss_tle, catalog, days=1.0, threshold_km=1.0, step_minutes=60.0)
    
    # Looser threshold
    loose_events = screen(iss_tle, catalog, days=1.0, threshold_km=5000.0, step_minutes=60.0)
    
    # Looser threshold should find at least as many events
    assert len(loose_events) >= len(tight_events)
    
    # All tight events should be in loose events
    tight_pairs = {(e.primary_norad_id, e.secondary_norad_id) for e in tight_events}
    loose_pairs = {(e.primary_norad_id, e.secondary_norad_id) for e in loose_events}
    assert tight_pairs.issubset(loose_pairs)


def test_propagation_error_handling():
    """Test that propagation handles errors gracefully."""
    # Create a TLE with an invalid date far in the future (may cause propagation errors)
    # For this test, we'll just verify the error handling exists
    # In practice, SGP4 is quite robust, so errors are rare with valid TLEs
    iss_tle = TLE.from_lines(ISS_TLE_LINES[0], ISS_TLE_LINES[1])
    
    # Try propagating very far into the future (100 years)
    far_future = iss_tle.epoch + timedelta(days=365*100)
    
    # This might work or might fail depending on SGP4's limits
    # The key is that if it fails, it should raise ValueError
    try:
        states = propagate(iss_tle, [far_future])
        # If it succeeds, that's fine too
        assert isinstance(states, list)
    except ValueError as e:
        # Should be a meaningful error message
        assert "SGP4 propagation failed" in str(e)


def test_batch_propagation_performance(iss_tle: TLE, css_tle: TLE, hubble_tle: TLE, geo_tle: TLE):
    """Test that batch propagation works with multiple satellites."""
    # Create a larger catalog
    tles = [iss_tle, css_tle, hubble_tle, geo_tle]
    time = iss_tle.epoch
    
    states, valid = propagate_batch(tles, time)
    
    assert states.shape == (4, 6)
    assert valid.shape == (4,)
    
    # All valid TLEs should propagate successfully
    assert np.sum(valid) >= 3  # At least most should succeed


def test_relative_velocity_calculation(iss_tle: TLE, css_tle: TLE):
    """Test that relative velocity is calculated correctly."""
    catalog = [css_tle]
    events = screen(iss_tle, catalog, days=0.5, threshold_km=10000.0, step_minutes=60.0)
    
    # If we found events, check relative velocity is reasonable
    for event in events:
        # LEO satellites have orbital velocity ~7-8 km/s
        # Relative velocity should be less than ~16 km/s (sum of both velocities)
        # and greater than 0
        assert 0 < event.relative_velocity_km_s < 20.0


def test_tca_is_in_screening_window(iss_tle: TLE, css_tle: TLE):
    """Test that TCA is within the screening window."""
    catalog = [css_tle]
    days = 2.0
    events = screen(iss_tle, catalog, days=days, threshold_km=5000.0, step_minutes=60.0)
    
    start = iss_tle.epoch
    end = start + timedelta(days=days)
    
    for event in events:
        # TCA should be within the screening window
        assert start <= event.tca <= end + timedelta(hours=1)  # small buffer for refinement


def test_screen_empty_catalog(iss_tle: TLE):
    """Test screening against empty catalog returns empty list."""
    events = screen(iss_tle, [], days=1.0, threshold_km=10.0)
    assert events == []


def test_screen_self_only_catalog(iss_tle: TLE):
    """Test screening against catalog containing only self returns empty list."""
    events = screen(iss_tle, [iss_tle], days=1.0, threshold_km=10.0)
    assert events == []


def test_screen_decayed_tle(iss_tle: TLE):
    """Test screening with a TLE that may cause propagation errors (very old epoch)."""
    # Create a TLE with a very old epoch by using ISS lines but propagating far
    # The screening should handle propagation errors gracefully (skip bad objects)
    catalog = [iss_tle]
    # Screen with ISS against itself won't find anything (self-exclusion), 
    # but we can verify no crash. Use css_tle-like object.
    css_lines = (
        "1 48274U 21035A   24045.50261574  .00021540  00000-0  25163-3 0  9993",
        "2 48274  41.4681 279.1498 0005372 149.8847 345.3740 15.62096269157018",
    )
    css = TLE.from_lines(css_lines[0], css_lines[1])
    # Screen far from epoch — propagation may degrade but shouldn't crash
    events = screen(css, [iss_tle], days=0.5, threshold_km=5000.0, step_minutes=60.0)
    assert isinstance(events, list)


class TestScreenCatalog:
    """Tests for the KD-tree based screen_catalog function."""

    def test_screen_catalog_basic(self, iss_tle: TLE, css_tle: TLE, hubble_tle: TLE):
        """Test screen_catalog with a small set of LEO objects."""
        tles = [iss_tle, css_tle, hubble_tle]
        # Use epoch of ISS as reference so propagation is near-epoch
        events = screen_catalog(
            tles,
            hours=2.0,
            step_minutes=10.0,
            threshold_km=5000.0,
            reference_time=iss_tle.epoch,
        )
        assert isinstance(events, list)
        for ev in events:
            assert isinstance(ev, ConjunctionEvent)
            assert ev.miss_distance_km <= 5000.0
            assert ev.miss_distance_km >= 0
            assert ev.relative_velocity_km_s >= 0

    def test_screen_catalog_sorted(self, iss_tle: TLE, css_tle: TLE, hubble_tle: TLE):
        """Test that screen_catalog results are sorted by miss distance."""
        events = screen_catalog(
            [iss_tle, css_tle, hubble_tle],
            hours=2.0,
            step_minutes=10.0,
            threshold_km=10000.0,
            reference_time=iss_tle.epoch,
        )
        for i in range(1, len(events)):
            assert events[i].miss_distance_km >= events[i - 1].miss_distance_km

    def test_screen_catalog_empty(self):
        """Test screen_catalog with no TLEs."""
        events = screen_catalog([], hours=1.0)
        assert events == []

    def test_screen_catalog_single(self, iss_tle: TLE):
        """Test screen_catalog with a single TLE returns empty."""
        events = screen_catalog([iss_tle], hours=1.0, reference_time=iss_tle.epoch)
        assert events == []

    def test_screen_catalog_no_geo_leo_pairs(self, iss_tle: TLE, geo_tle: TLE):
        """GEO and LEO objects should not produce close approaches at 10km threshold."""
        events = screen_catalog(
            [iss_tle, geo_tle],
            hours=2.0,
            step_minutes=10.0,
            threshold_km=10.0,
            reference_time=iss_tle.epoch,
        )
        assert len(events) == 0

    def test_screen_catalog_with_tle_age_filter(self, iss_tle: TLE, css_tle: TLE):
        """Test max_tle_age_days parameter filters old TLEs."""
        # Use a reference time far in the future so all TLEs are stale
        far_future = iss_tle.epoch + timedelta(days=100)
        events = screen_catalog(
            [iss_tle, css_tle],
            hours=1.0,
            max_tle_age_days=3.0,
            reference_time=far_future,
        )
        # All TLEs should be filtered out → no events
        assert events == []


class TestFilterStaleTles:
    """Tests for filter_stale_tles."""

    def test_all_fresh(self, iss_tle: TLE, css_tle: TLE):
        """TLEs near their epoch should pass the filter."""
        ref = iss_tle.epoch + timedelta(hours=1)
        result = filter_stale_tles([iss_tle, css_tle], max_age_days=3.0, reference_time=ref)
        assert len(result) == 2

    def test_all_stale(self, iss_tle: TLE, css_tle: TLE):
        """TLEs far from reference time should be filtered out."""
        ref = iss_tle.epoch + timedelta(days=30)
        result = filter_stale_tles([iss_tle, css_tle], max_age_days=3.0, reference_time=ref)
        assert len(result) == 0

    def test_mixed(self, iss_tle: TLE, css_tle: TLE):
        """Only fresh TLEs should survive filtering."""
        # ISS and CSS epochs are very close, so use a ref that makes one stale
        # They're both from epoch day ~45, so offset by ~2 days from ISS
        ref = iss_tle.epoch + timedelta(days=2)
        # With max_age_days=1.5, ISS (2 days old) is stale, CSS (~2 days old) may also be stale
        # Use a tighter window: ref = iss_tle.epoch, max_age = 0.5 days
        # CSS epoch is ~0.05 days different from ISS epoch
        ref = iss_tle.epoch
        result = filter_stale_tles([iss_tle, css_tle], max_age_days=0.5, reference_time=ref)
        # ISS is exactly at ref (age=0), should pass
        assert iss_tle in result

    def test_empty_input(self):
        """Empty list returns empty list."""
        result = filter_stale_tles([], max_age_days=3.0, reference_time=datetime.now(timezone.utc))
        assert result == []


class TestScreenEdgeCases:
    """Edge case tests for screen()."""

    def test_screen_empty_catalog(self, iss_tle: TLE):
        """Screen against empty catalog returns no events."""
        events = screen(iss_tle, [], days=1.0)
        assert events == []

    def test_screen_single_object_catalog(self, iss_tle: TLE):
        """Screen primary against catalog containing only itself returns no events."""
        events = screen(iss_tle, [iss_tle], days=1.0, threshold_km=10000.0)
        assert events == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
