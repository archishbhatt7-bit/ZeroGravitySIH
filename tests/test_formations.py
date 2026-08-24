from __future__ import annotations

import pytest

from zerogravity.core.formations import (
    FormationGroup,
    detect_formations,
    filter_formation_events,
    is_formation_pair,
)


class TestFormationDetection:
    """Test suite for formation detection functionality."""

    def test_iss_complex_detection(self):
        """Test ISS complex is detected by NORAD IDs and keywords."""
        names = ["ISS (ZARYA)", "PROGRESS-MS 27", "DRAGON CRS-31", "STARLINK-1234"]
        norad_ids = [25544, 60001, 60002, 50000]

        formations = detect_formations(names, norad_ids)

        # Should detect ISS complex with 3 objects
        assert len(formations) == 1
        assert formations[0].name == "ISS Complex"
        assert formations[0].reason == "docked_modules"
        assert len(formations[0].norad_ids) == 3
        assert 25544 in formations[0].norad_ids
        assert 60001 in formations[0].norad_ids
        assert 60002 in formations[0].norad_ids
        assert 50000 not in formations[0].norad_ids  # Starlink not included

    def test_css_complex_detection(self):
        """Test Chinese Space Station complex detection."""
        names = ["CSS (TIANHE)", "TIANZHOU 8", "SHENZHOU-19", "WENTIAN", "MENGTIAN"]
        norad_ids = [48274, 60500, 60501, 53000, 53001]

        formations = detect_formations(names, norad_ids)

        assert len(formations) == 1
        assert formations[0].name == "CSS Complex"
        assert formations[0].reason == "docked_modules"
        assert len(formations[0].norad_ids) == 5

    def test_starlink_not_formation(self):
        """Test that different Starlink satellites are NOT detected as formation."""
        names = ["STARLINK-34117", "STARLINK-34081", "STARLINK-30125"]
        norad_ids = [61234, 61235, 61236]

        formations = detect_formations(names, norad_ids)

        # Should not detect any formations (different constellation members)
        assert len(formations) == 0

    def test_piesat_formation(self):
        """Test PIESAT formation detection."""
        names = ["PIESAT-A", "PIESAT-B", "PIESAT-C"]
        norad_ids = [45001, 45002, 45003]

        formations = detect_formations(names, norad_ids)

        assert len(formations) == 1
        assert formations[0].name == "PIESAT Formation"
        assert formations[0].reason == "formation_flying"
        assert len(formations[0].norad_ids) == 3

    def test_velocity_based_detection(self):
        """Test velocity-based co-located pair detection."""
        names = ["SAT-A", "SAT-B", "SAT-C"]
        norad_ids = [10001, 10002, 10003]

        # SAT-A and SAT-B are close with low relative velocity
        positions = [
            (7000.0, 0.0, 0.0),  # SAT-A
            (7002.0, 0.0, 0.0),  # SAT-B (2 km away)
            (8000.0, 0.0, 0.0),  # SAT-C (far away)
        ]
        velocities = [
            (0.0, 7.5, 0.0),  # SAT-A
            (0.0, 7.52, 0.0),  # SAT-B (rel vel = 0.02 km/s)
            (0.0, 7.0, 0.0),  # SAT-C
        ]

        formations = detect_formations(names, norad_ids, positions, velocities)

        assert len(formations) == 1
        assert formations[0].reason == "velocity_based"
        assert len(formations[0].norad_ids) == 2
        assert 10001 in formations[0].norad_ids
        assert 10002 in formations[0].norad_ids

    def test_cospar_rideshare_detection(self):
        """Test COSPAR-based rideshare payload detection."""
        names = ["PAYLOAD-1", "PAYLOAD-2", "PAYLOAD-3"]
        norad_ids = [70001, 70002, 70003]
        cospar_ids = ["2025-313A", "2025-313B", "2025-313C"]

        # All three within 5km
        positions = [
            (7000.0, 0.0, 0.0),
            (7003.0, 0.0, 0.0),
            (7004.5, 0.0, 0.0),
        ]

        formations = detect_formations(names, norad_ids, positions=positions, cospar_ids=cospar_ids)

        # Should detect rideshare group
        rideshare = [f for f in formations if "Rideshare" in f.name]
        assert len(rideshare) == 1
        assert rideshare[0].reason == "rideshare_dispersing"
        assert len(rideshare[0].norad_ids) >= 2  # At least 2 objects grouped

    def test_tandem_formation(self):
        """Test TanDEM-X formation detection."""
        names = ["TERRASAR-X", "TANDEM-X", "ANOTHER-SAT"]
        norad_ids = [31698, 36605, 40000]

        formations = detect_formations(names, norad_ids)

        assert len(formations) == 1
        assert formations[0].name == "TanDEM-X Formation"
        assert formations[0].reason == "formation_flying"
        assert len(formations[0].norad_ids) == 2

    def test_mev_docking(self):
        """Test MEV satellite servicing docking detection."""
        names = ["INTELSAT 10-02", "MEV-2"]
        norad_ids = [27384, 45017]

        formations = detect_formations(names, norad_ids)

        assert len(formations) == 1
        assert "MEV-2" in formations[0].name
        assert formations[0].reason == "docked_servicing"
        assert len(formations[0].norad_ids) == 2

    def test_tianhui_formation(self):
        """Test TIANHUI formation detection."""
        names = ["TIANHUI-1A", "TIANHUI-1B"]
        norad_ids = [36599, 36827]

        formations = detect_formations(names, norad_ids)

        assert len(formations) == 1
        assert formations[0].name == "TIANHUI Formation"
        assert formations[0].reason == "formation_flying"

    def test_is_formation_pair_iss(self):
        """Test is_formation_pair for ISS components."""
        is_formation, reason = is_formation_pair("ISS (ZARYA)", "PROGRESS-MS 27", 25544, 60001)

        assert is_formation is True
        assert "ISS Complex" in reason
        assert "docked_modules" in reason

    def test_is_formation_pair_css(self):
        """Test is_formation_pair for CSS components."""
        is_formation, reason = is_formation_pair("CSS (TIANHE)", "TIANZHOU 8", 48274, 60500)

        assert is_formation is True
        assert "CSS Complex" in reason

    def test_is_formation_pair_starlink_negative(self):
        """Test that Starlink satellites are NOT formation pairs."""
        is_formation, reason = is_formation_pair(
            "STARLINK-34117",
            "STARLINK-34081",
            61234,
            61235,
            rel_velocity_km_s=2.5,  # High relative velocity
            distance_km=100.0,  # Far apart
        )

        assert is_formation is False
        assert reason == ""

    def test_is_formation_pair_velocity_based(self):
        """Test velocity-based formation pair detection."""
        is_formation, reason = is_formation_pair(
            "SAT-A",
            "SAT-B",
            10001,
            10002,
            rel_velocity_km_s=0.02,  # Very low relative velocity
            distance_km=3.0,  # Close distance
        )

        assert is_formation is True
        assert "Co-located" in reason
        assert "velocity_based" in reason

    def test_filter_formation_events_basic(self):
        """Test filtering of conjunction events."""
        events = [
            {
                "name1": "ISS (ZARYA)",
                "name2": "PROGRESS-MS 27",
                "norad_id1": 25544,
                "norad_id2": 60001,
                "relative_velocity_km_s": 0.01,
                "miss_distance_km": 0.05,
            },
            {
                "name1": "SATELLITE-A",
                "name2": "SATELLITE-B",
                "norad_id1": 40000,
                "norad_id2": 40001,
                "relative_velocity_km_s": 14.5,
                "miss_distance_km": 0.5,
            },
        ]

        real_threats, formation_events = filter_formation_events(events)

        # ISS event should be filtered as formation
        assert len(formation_events) == 1
        assert formation_events[0]["norad_id1"] == 25544

        # Unknown satellite pair should be real threat
        assert len(real_threats) == 1
        assert real_threats[0]["norad_id1"] == 40000

    def test_filter_formation_events_with_formations(self):
        """Test filtering with pre-detected formations."""
        # Create a formation
        formations = [
            FormationGroup(
                name="Test Formation",
                reason="formation_flying",
                norad_ids=[50001, 50002, 50003],
                object_names=["SAT-1", "SAT-2", "SAT-3"],
            )
        ]

        events = [
            {
                "name1": "SAT-1",
                "name2": "SAT-2",
                "norad_id1": 50001,
                "norad_id2": 50002,
                "relative_velocity_km_s": 0.03,
                "miss_distance_km": 2.0,
            },
            {
                "name1": "SAT-1",
                "name2": "SAT-3",
                "norad_id1": 50001,
                "norad_id2": 50003,
                "relative_velocity_km_s": 0.04,
                "miss_distance_km": 3.0,
            },
            {
                "name1": "SAT-1",
                "name2": "DEBRIS-999",
                "norad_id1": 50001,
                "norad_id2": 99999,
                "relative_velocity_km_s": 12.0,
                "miss_distance_km": 0.8,
            },
        ]

        real_threats, formation_events = filter_formation_events(events, formations)

        # First two events are within the formation
        assert len(formation_events) == 2

        # Last event is a real threat
        assert len(real_threats) == 1
        assert real_threats[0]["norad_id2"] == 99999

    def test_mixed_scenario(self):
        """Test complex scenario with multiple formation types."""
        names = [
            "ISS (ZARYA)",  # ISS
            "PROGRESS-MS 27",  # ISS
            "CSS (TIANHE)",  # CSS
            "TIANZHOU 8",  # CSS
            "PIESAT-A",  # PIESAT formation
            "PIESAT-B",  # PIESAT formation
            "STARLINK-1234",  # Standalone
            "TERRASAR-X",  # TanDEM
            "TANDEM-X",  # TanDEM
        ]
        norad_ids = [25544, 60001, 48274, 60500, 45001, 45002, 50000, 31698, 36605]

        formations = detect_formations(names, norad_ids)

        # Should detect ISS, CSS, PIESAT, and TanDEM formations
        assert len(formations) == 4

        formation_names = [f.name for f in formations]
        assert "ISS Complex" in formation_names
        assert "CSS Complex" in formation_names
        assert "PIESAT Formation" in formation_names
        assert "TanDEM-X Formation" in formation_names

    def test_edge_case_empty_input(self):
        """Test handling of empty input."""
        formations = detect_formations([], [])
        assert len(formations) == 0

    def test_edge_case_single_object(self):
        """Test handling of single object."""
        formations = detect_formations(["ISS (ZARYA)"], [25544])
        # Single object should still be detected as ISS complex
        assert len(formations) == 1
        assert formations[0].name == "ISS Complex"

    def test_velocity_threshold_boundary(self):
        """Test velocity threshold at boundary (0.05 km/s)."""
        names = ["SAT-A", "SAT-B"]
        norad_ids = [10001, 10002]

        positions = [
            (7000.0, 0.0, 0.0),
            (7003.0, 0.0, 0.0),  # 3 km away
        ]

        # Test just below threshold (should be formation)
        velocities_below = [
            (0.0, 7.5, 0.0),
            (0.0, 7.549, 0.0),  # rel vel = 0.049 km/s
        ]
        formations = detect_formations(names, norad_ids, positions, velocities_below)
        assert len(formations) == 1

        # Test just above threshold (should NOT be formation)
        velocities_above = [
            (0.0, 7.5, 0.0),
            (0.0, 7.551, 0.0),  # rel vel = 0.051 km/s
        ]
        formations = detect_formations(names, norad_ids, positions, velocities_above)
        assert len(formations) == 0

    def test_distance_threshold_boundary(self):
        """Test distance threshold at boundary (5 km)."""
        names = ["SAT-A", "SAT-B"]
        norad_ids = [10001, 10002]

        velocities = [
            (0.0, 7.5, 0.0),
            (0.0, 7.52, 0.0),  # rel vel = 0.02 km/s (below threshold)
        ]

        # Test just below threshold (should be formation)
        positions_below = [
            (7000.0, 0.0, 0.0),
            (7004.9, 0.0, 0.0),  # 4.9 km away
        ]
        formations = detect_formations(names, norad_ids, positions_below, velocities)
        assert len(formations) == 1

        # Test just above threshold (should NOT be formation)
        positions_above = [
            (7000.0, 0.0, 0.0),
            (7005.1, 0.0, 0.0),  # 5.1 km away
        ]
        formations = detect_formations(names, norad_ids, positions_above, velocities)
        assert len(formations) == 0

    def test_mismatched_positions_velocities_length(self):
        """Test that mismatched positions/velocities array lengths raise ValueError or are handled."""
        names = ["SAT-A", "SAT-B"]
        norad_ids = [10001, 10002]
        positions = [(7000.0, 0.0, 0.0)]  # only 1
        velocities = [(0.0, 7.5, 0.0), (0.0, 7.5, 0.0)]  # 2
        # positions length != n_objects, so velocity-based detection is skipped (guard clause)
        formations = detect_formations(names, norad_ids, positions, velocities)
        # Should not crash; velocity-based detection simply skipped
        assert isinstance(formations, list)

    def test_empty_arrays(self):
        """Test detect_formations with completely empty arrays."""
        formations = detect_formations([], [])
        assert formations == []

    def test_single_non_iss_object(self):
        """Test single generic object — no formations possible."""
        formations = detect_formations(["RANDOM-SAT"], [99999])
        assert formations == []

    def test_names_norad_ids_length_mismatch_raises(self):
        """Test that mismatched names/norad_ids raises ValueError."""
        with pytest.raises(ValueError, match="same length"):
            detect_formations(["A", "B"], [1])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
