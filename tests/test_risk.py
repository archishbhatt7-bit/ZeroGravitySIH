from __future__ import annotations

from datetime import datetime, timedelta, timezone

from zerogravity.core.risk import RiskAssessment, assess_risk, classify_events


class TestRiskAssessment:
    """Test suite for satellite conjunction risk assessment."""

    def test_extreme_close_approach(self):
        """Test scenario: extremely close approach (0.1 km)."""
        result = assess_risk(
            miss_distance_km=0.1,
            relative_velocity_km_s=10.0,
            obj1_maneuverable=True,  # At least one can maneuver
        )
        assert result.score >= 80, "Extremely close approach should be CRITICAL"
        assert result.category == "CRITICAL"
        assert "IMMEDIATE ACTION" in result.recommendation

    def test_zero_distance_collision(self):
        """Test edge case: zero distance (collision)."""
        result = assess_risk(
            miss_distance_km=0.0,
            relative_velocity_km_s=10.0,
        )
        assert result.score >= 80, "Zero distance should be CRITICAL"
        assert result.category == "CRITICAL"

    def test_zero_velocity_docked(self):
        """Test edge case: zero velocity (docked/formation flying)."""
        result = assess_risk(
            miss_distance_km=0.01,
            relative_velocity_km_s=0.0,
        )
        # High distance score, but low velocity score
        assert result.score > 0
        # Should still be concerning due to very close distance
        assert result.category in ["CRITICAL", "HIGH", "MEDIUM"]

    def test_very_high_velocity(self):
        """Test edge case: very high velocity (>10 km/s)."""
        result = assess_risk(
            miss_distance_km=0.5,
            relative_velocity_km_s=15.0,
        )
        assert result.score >= 70, "Very high velocity + close approach = high risk"
        assert result.category in ["CRITICAL", "HIGH"]

    def test_safe_distance(self):
        """Test scenario: safe distance (>25 km)."""
        result = assess_risk(
            miss_distance_km=30.0,
            relative_velocity_km_s=5.0,
            obj1_maneuverable=True,  # At least one can maneuver
        )
        assert result.score < 20, "Large separation should be NEGLIGIBLE"
        assert result.category == "NEGLIGIBLE"

    def test_iss_maneuverable_large(self):
        """Test ISS-like scenario: large maneuverable satellite."""
        result = assess_risk(
            miss_distance_km=1.5,
            relative_velocity_km_s=8.0,
            obj1_rcs="LARGE",
            obj1_maneuverable=True,
            obj2_rcs="MEDIUM",
            obj2_maneuverable=False,
        )
        # Large object increases risk, but maneuverability reduces it
        assert result.score > 20
        assert result.factors["size_multiplier"] >= 1.3
        assert result.factors["maneuver_multiplier"] < 1.0
        assert "maneuver" in result.recommendation.lower()

    def test_debris_on_debris_neither_maneuverable(self):
        """Test debris-on-debris: neither can maneuver."""
        result = assess_risk(
            miss_distance_km=2.0,
            relative_velocity_km_s=6.0,
            obj1_rcs="SMALL",
            obj1_maneuverable=False,
            obj2_rcs="SMALL",
            obj2_maneuverable=False,
        )
        # Neither can maneuver increases risk significantly
        assert result.factors["maneuver_multiplier"] > 1.0
        assert (
            "Neither object" in result.recommendation
            or "coordinate" in result.recommendation.lower()
        )

    def test_starlink_both_maneuverable(self):
        """Test Starlink-on-Starlink: both can maneuver."""
        result = assess_risk(
            miss_distance_km=2.0,
            relative_velocity_km_s=6.0,
            obj1_rcs="SMALL",
            obj1_maneuverable=True,
            obj2_rcs="SMALL",
            obj2_maneuverable=True,
        )
        # Both can maneuver reduces risk
        assert result.factors["maneuver_multiplier"] < 1.0
        assert result.score < 60  # Should not be HIGH unless very close

    def test_urgency_multiplier_imminent(self):
        """Test time urgency: <6 hours to TCA."""
        tca = datetime.now(timezone.utc) + timedelta(hours=3)
        result = assess_risk(
            miss_distance_km=1.0,
            relative_velocity_km_s=7.0,
            tca=tca,
        )
        assert result.time_to_tca_hours is not None
        assert result.time_to_tca_hours < 6
        assert result.factors["urgency_multiplier"] > 1.0

    def test_urgency_multiplier_distant_future(self):
        """Test time urgency: >24 hours to TCA."""
        tca = datetime.now(timezone.utc) + timedelta(hours=48)
        result = assess_risk(
            miss_distance_km=1.0,
            relative_velocity_km_s=7.0,
            tca=tca,
        )
        assert result.time_to_tca_hours > 24
        assert result.factors["urgency_multiplier"] == 1.0

    def test_score_ordering_distance(self):
        """Test that closer approaches always score higher."""
        result_1km = assess_risk(miss_distance_km=1.0, relative_velocity_km_s=5.0)
        result_2km = assess_risk(miss_distance_km=2.0, relative_velocity_km_s=5.0)
        result_5km = assess_risk(miss_distance_km=5.0, relative_velocity_km_s=5.0)

        assert result_1km.score > result_2km.score
        assert result_2km.score > result_5km.score

    def test_score_ordering_velocity(self):
        """Test that higher velocities always score higher."""
        # Use larger distance to avoid hitting the 100 ceiling
        result_3kms = assess_risk(miss_distance_km=5.0, relative_velocity_km_s=3.0)
        result_7kms = assess_risk(miss_distance_km=5.0, relative_velocity_km_s=7.0)
        result_12kms = assess_risk(miss_distance_km=5.0, relative_velocity_km_s=12.0)

        assert result_12kms.score > result_7kms.score
        assert result_7kms.score > result_3kms.score

    def test_category_thresholds(self):
        """Test that score thresholds map correctly to categories."""
        # Test boundary conditions
        scenarios = [
            (0.1, 10.0, "LARGE", "LARGE", False, False, "CRITICAL"),  # Should be >=80
            (4.5, 5.0, "LARGE", "MEDIUM", False, False, "HIGH"),  # Should be >=60
            (6.0, 5.0, "MEDIUM", "MEDIUM", False, False, "MEDIUM"),  # Should be >=40
            (8.0, 5.0, "SMALL", "SMALL", True, True, "LOW"),  # Should be >=20
            (30.0, 2.0, "SMALL", "SMALL", True, True, "NEGLIGIBLE"),  # Should be <20
        ]

        for distance, velocity, rcs1, rcs2, m1, m2, expected_cat in scenarios:
            result = assess_risk(
                miss_distance_km=distance,
                relative_velocity_km_s=velocity,
                obj1_rcs=rcs1,
                obj2_rcs=rcs2,
                obj1_maneuverable=m1,
                obj2_maneuverable=m2,
            )
            assert result.category == expected_cat, (
                f"Distance={distance}, Velocity={velocity}, RCS=({rcs1},{rcs2}), "
                f"Maneuver=({m1},{m2}) should be {expected_cat}, got {result.category} "
                f"(score={result.score})"
            )

    def test_unknown_rcs(self):
        """Test handling of UNKNOWN RCS values."""
        result = assess_risk(
            miss_distance_km=2.0,
            relative_velocity_km_s=6.0,
            obj1_rcs="UNKNOWN",
            obj2_rcs="UNKNOWN",
        )
        assert result.factors["size_multiplier"] == 1.0
        assert result.score > 0

    def test_case_insensitive_rcs(self):
        """Test that RCS values are case-insensitive."""
        result_upper = assess_risk(
            miss_distance_km=2.0,
            relative_velocity_km_s=6.0,
            obj1_rcs="LARGE",
            obj2_rcs="SMALL",
        )
        result_lower = assess_risk(
            miss_distance_km=2.0,
            relative_velocity_km_s=6.0,
            obj1_rcs="large",
            obj2_rcs="small",
        )
        assert result_upper.score == result_lower.score

    def test_classify_events_batch(self):
        """Test batch classification of multiple events."""
        events = [
            {
                "miss_distance_km": 0.5,
                "relative_velocity_km_s": 9.0,
                "obj1_rcs": "LARGE",
                "obj2_rcs": "MEDIUM",
            },
            {
                "miss_distance_km": 5.0,
                "relative_velocity_km_s": 4.0,
                "obj1_maneuverable": True,
            },
            {
                "miss_distance_km": 25.0,
                "relative_velocity_km_s": 2.0,
            },
        ]

        results = classify_events(events)

        assert len(results) == 3
        assert all(isinstance(r, RiskAssessment) for r in results)
        assert results[0].score > results[1].score > results[2].score
        assert results[0].category in ["CRITICAL", "HIGH"]
        assert results[2].category in ["NEGLIGIBLE", "LOW"]

    def test_risk_assessment_dataclass_fields(self):
        """Test that RiskAssessment contains all required fields."""
        result = assess_risk(
            miss_distance_km=1.5,
            relative_velocity_km_s=6.5,
        )

        assert hasattr(result, "score")
        assert hasattr(result, "category")
        assert hasattr(result, "miss_distance_km")
        assert hasattr(result, "relative_velocity_km_s")
        assert hasattr(result, "time_to_tca_hours")
        assert hasattr(result, "factors")
        assert hasattr(result, "recommendation")

        assert isinstance(result.score, float)
        assert isinstance(result.category, str)
        assert isinstance(result.factors, dict)
        assert isinstance(result.recommendation, str)

        # Check factors dict contents
        assert "distance_score" in result.factors
        assert "velocity_score" in result.factors
        assert "size_multiplier" in result.factors
        assert "maneuver_multiplier" in result.factors
        assert "urgency_multiplier" in result.factors
        assert "base_score" in result.factors

    def test_score_clamped_to_100(self):
        """Test that score never exceeds 100 even with extreme multipliers."""
        tca = datetime.now(timezone.utc) + timedelta(hours=2)
        result = assess_risk(
            miss_distance_km=0.01,
            relative_velocity_km_s=15.0,
            obj1_rcs="LARGE",
            obj2_rcs="LARGE",
            obj1_maneuverable=False,
            obj2_maneuverable=False,
            tca=tca,
        )
        assert result.score <= 100.0
        assert result.category == "CRITICAL"

    def test_large_objects_increase_risk(self):
        """Test that larger RCS increases risk score."""
        result_small = assess_risk(
            miss_distance_km=2.0,
            relative_velocity_km_s=6.0,
            obj1_rcs="SMALL",
            obj2_rcs="SMALL",
        )
        result_large = assess_risk(
            miss_distance_km=2.0,
            relative_velocity_km_s=6.0,
            obj1_rcs="LARGE",
            obj2_rcs="LARGE",
        )
        assert result_large.score > result_small.score

    def test_classify_events_empty(self):
        """Test classify_events with empty list returns empty list."""
        results = classify_events([])
        assert results == []

    def test_classify_events_missing_keys(self):
        """Test classify_events with events missing optional keys uses defaults."""
        events = [{"miss_distance_km": 1.0, "relative_velocity_km_s": 5.0}]
        results = classify_events(events)
        assert len(results) == 1
        assert results[0].factors["size_multiplier"] == 1.0  # UNKNOWN default

    def test_urgency_tca_in_past(self):
        """Test risk assessment when TCA is in the past."""
        tca = datetime.now(timezone.utc) - timedelta(hours=2)
        result = assess_risk(
            miss_distance_km=1.0,
            relative_velocity_km_s=7.0,
            tca=tca,
        )
        # Past TCA should have urgency_multiplier of 1.0
        assert result.factors["urgency_multiplier"] == 1.0
        assert result.time_to_tca_hours < 0

    def test_one_maneuverable_reduces_risk(self):
        """Test that having at least one maneuverable object reduces risk."""
        result_neither = assess_risk(
            miss_distance_km=2.0,
            relative_velocity_km_s=6.0,
            obj1_maneuverable=False,
            obj2_maneuverable=False,
        )
        result_one = assess_risk(
            miss_distance_km=2.0,
            relative_velocity_km_s=6.0,
            obj1_maneuverable=True,
            obj2_maneuverable=False,
        )
        result_both = assess_risk(
            miss_distance_km=2.0,
            relative_velocity_km_s=6.0,
            obj1_maneuverable=True,
            obj2_maneuverable=True,
        )

        # Risk should decrease as maneuverability increases
        assert result_neither.score > result_one.score
        assert result_one.score > result_both.score
