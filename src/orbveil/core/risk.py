from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    score: float          # 0-100
    category: str         # CRITICAL/HIGH/MEDIUM/LOW/NEGLIGIBLE
    miss_distance_km: float
    relative_velocity_km_s: float
    time_to_tca_hours: float | None
    factors: dict         # breakdown of contributing factors
    recommendation: str   # human-readable action recommendation


def assess_risk(
    miss_distance_km: float,
    relative_velocity_km_s: float,
    obj1_rcs: str = "UNKNOWN",  # SMALL/MEDIUM/LARGE/UNKNOWN
    obj2_rcs: str = "UNKNOWN",
    obj1_maneuverable: bool = False,
    obj2_maneuverable: bool = False,
    tca: datetime | None = None,
    now: datetime | None = None,
    **kwargs,
) -> RiskAssessment:
    """
    Assess collision risk for a satellite conjunction event.
    
    Args:
        miss_distance_km: Predicted miss distance in kilometers
        relative_velocity_km_s: Relative velocity in km/s
        obj1_rcs: Radar cross-section size category (SMALL/MEDIUM/LARGE/UNKNOWN)
        obj2_rcs: Radar cross-section size category (SMALL/MEDIUM/LARGE/UNKNOWN)
        obj1_maneuverable: Whether object 1 can perform avoidance maneuvers
        obj2_maneuverable: Whether object 2 can perform avoidance maneuvers
        tca: Time of closest approach (if None, time urgency not considered)
    
    Returns:
        RiskAssessment with score, category, and recommendation
    """
    # Calculate individual risk factors
    distance_score = _calculate_distance_score(miss_distance_km)
    velocity_score = _calculate_velocity_score(relative_velocity_km_s)
    size_multiplier = _calculate_size_multiplier(obj1_rcs, obj2_rcs)
    maneuver_multiplier = _calculate_maneuver_multiplier(obj1_maneuverable, obj2_maneuverable)
    time_to_tca_hours = None
    urgency_multiplier = 1.0
    
    if tca is not None:
        if now is None:
            now = datetime.now(timezone.utc)
        if tca.tzinfo is None:
            tca = tca.replace(tzinfo=timezone.utc)
        time_delta = tca - now
        time_to_tca_hours = time_delta.total_seconds() / 3600
        urgency_multiplier = _calculate_urgency_multiplier(time_to_tca_hours)
    
    # Combine factors: base score from distance and velocity, then apply multipliers
    base_score = (distance_score * 0.6) + (velocity_score * 0.4)
    adjusted_score = base_score * size_multiplier * maneuver_multiplier * urgency_multiplier
    
    # Floor: extremely close approaches (< 0.5 km) are always CRITICAL regardless of maneuverability
    if miss_distance_km < 0.5 and relative_velocity_km_s > 0.1:
        adjusted_score = max(adjusted_score, 85.0)
    
    # Clamp to 0-100
    final_score = max(0.0, min(100.0, adjusted_score))
    
    # Categorize
    category = _categorize_score(final_score)
    
    # Generate recommendation
    recommendation = _generate_recommendation(category, obj1_maneuverable, obj2_maneuverable)
    
    # Build factor breakdown
    factors = {
        "distance_score": round(distance_score, 2),
        "velocity_score": round(velocity_score, 2),
        "size_multiplier": round(size_multiplier, 2),
        "maneuver_multiplier": round(maneuver_multiplier, 2),
        "urgency_multiplier": round(urgency_multiplier, 2),
        "base_score": round(base_score, 2),
    }
    
    logger.debug("Risk assessment: score=%.2f, category=%s, miss=%.3f km", final_score, category, miss_distance_km)
    return RiskAssessment(
        score=round(final_score, 2),
        category=category,
        miss_distance_km=miss_distance_km,
        relative_velocity_km_s=relative_velocity_km_s,
        time_to_tca_hours=round(time_to_tca_hours, 2) if time_to_tca_hours is not None else None,
        factors=factors,
        recommendation=recommendation,
    )


def classify_events(events: list[dict]) -> list[RiskAssessment]:
    """
    Batch classify a list of conjunction events.
    
    Args:
        events: List of event dictionaries with keys matching assess_risk parameters
    
    Returns:
        List of RiskAssessment objects
    """
    return [assess_risk(**event) for event in events]


def _calculate_distance_score(miss_distance_km: float) -> float:
    """
    Calculate risk score based on miss distance using exponential decay.
    <1 km = maximum risk, >25 km = negligible risk.
    """
    if miss_distance_km < 0:
        miss_distance_km = 0
    
    # Exponential decay: score = 100 * e^(-k * distance)
    # At 1 km, we want high score (~90)
    # At 25 km, we want low score (~5)
    k = 0.15  # decay constant (increased for steeper drop-off)
    score = 100 * math.exp(-k * miss_distance_km)
    
    return score


def _calculate_velocity_score(relative_velocity_km_s: float) -> float:
    """
    Calculate risk score based on relative velocity.
    Higher velocity = more kinetic energy = more dangerous collision.
    >10 km/s = maximum energy.
    """
    if relative_velocity_km_s < 0:
        relative_velocity_km_s = 0
    
    # Normalize to 0-100, with 10 km/s as max
    max_velocity = 10.0
    score = min(100.0, (relative_velocity_km_s / max_velocity) * 100)
    
    return score


def _calculate_size_multiplier(obj1_rcs: str, obj2_rcs: str) -> float:
    """
    Calculate size-based risk multiplier.
    Larger objects present greater collision risk.
    """
    size_weights = {
        "SMALL": 0.8,
        "MEDIUM": 1.0,
        "LARGE": 1.3,
        "UNKNOWN": 1.0,
    }
    
    weight1 = size_weights.get(obj1_rcs.upper(), 1.0)
    weight2 = size_weights.get(obj2_rcs.upper(), 1.0)
    
    # Use the maximum weight (worst case)
    return max(weight1, weight2)


def _calculate_maneuver_multiplier(obj1_maneuverable: bool, obj2_maneuverable: bool) -> float:
    """
    Calculate maneuverability-based risk multiplier.
    If neither can maneuver, risk is higher.
    If at least one can maneuver, risk is lower.
    """
    if not obj1_maneuverable and not obj2_maneuverable:
        # Neither can avoid - highest risk
        return 1.2
    elif obj1_maneuverable and obj2_maneuverable:
        # Both can avoid - lowest risk
        return 0.7
    else:
        # One can avoid - moderate risk
        return 0.85


def _calculate_urgency_multiplier(time_to_tca_hours: float) -> float:
    """
    Calculate time urgency multiplier.
    <6 hours = urgent, apply multiplier.
    """
    if time_to_tca_hours < 0:
        # TCA in the past - still dangerous if very recent
        return 1.0
    elif time_to_tca_hours < 6:
        # Urgent - less than 6 hours
        return 1.2
    elif time_to_tca_hours < 24:
        # Approaching soon
        return 1.1
    else:
        # More time available
        return 1.0


def _categorize_score(score: float) -> str:
    """Categorize risk score into severity levels."""
    if score >= 80:
        return "CRITICAL"
    elif score >= 60:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    elif score >= 20:
        return "LOW"
    else:
        return "NEGLIGIBLE"


def _generate_recommendation(category: str, obj1_maneuverable: bool, obj2_maneuverable: bool) -> str:
    """Generate human-readable action recommendation."""
    can_maneuver = obj1_maneuverable or obj2_maneuverable
    
    if category == "CRITICAL":
        if can_maneuver:
            return "IMMEDIATE ACTION REQUIRED: Execute collision avoidance maneuver now"
        else:
            return "CRITICAL ALERT: Neither object can maneuver - coordinate with operators immediately"
    elif category == "HIGH":
        if can_maneuver:
            return "Continuous monitoring required - prepare collision avoidance maneuver"
        else:
            return "High risk event - coordinate tracking and assessment with all operators"
    elif category == "MEDIUM":
        return "Monitor conjunction closely and update assessment as tracking improves"
    elif category == "LOW":
        return "Maintain awareness - routine monitoring sufficient"
    else:
        return "Negligible risk - standard catalog maintenance"
