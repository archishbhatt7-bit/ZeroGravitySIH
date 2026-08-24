from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class FormationGroup:
    """Represents a group of satellites flying in formation or co-located."""
    name: str                    # e.g., "ISS Complex", "PIESAT Formation"
    reason: str                  # e.g., "docked_modules", "formation_flying", "rideshare_dispersing"
    norad_ids: list[int]
    object_names: list[str]


# Known formation configurations
KNOWN_FORMATIONS = {
    'iss_core': [25544, 49044],  # ISS and related core modules
    'iss_keywords': ['ISS ', 'ZARYA', 'NAUKA', 'PROGRESS-MS', 'SOYUZ-MS', 
                     'DRAGON CRS', 'CYGNUS NG', 'HTV-X'],
    'css_keywords': ['TIANHE', 'WENTIAN', 'MENGTIAN', 'TIANZHOU', 'SHENZHOU', 'CSS ('],
    'tandem': [('TERRASAR-X', 'TANDEM-X')],
    'mev_dockings': [
        ('INTELSAT 10-02', 'MEV-2'),
        ('INTELSAT 901', 'MEV-1'),
    ],
}


def detect_formations(
    names: list[str],
    norad_ids: list[int],
    positions: list[tuple[float, float, float]] | None = None,  # km, TEME
    velocities: list[tuple[float, float, float]] | None = None,  # km/s, TEME
    cospar_ids: list[str] | None = None,
) -> list[FormationGroup]:
    """
    Detect satellite formations from a list of objects.
    
    Args:
        names: Object names
        norad_ids: NORAD catalog IDs
        positions: Optional position vectors (km, TEME)
        velocities: Optional velocity vectors (km/s, TEME)
        cospar_ids: Optional COSPAR/international designators
        
    Returns:
        List of detected formation groups
    """
    if len(names) != len(norad_ids):
        raise ValueError("names and norad_ids must have same length")
    
    n_objects = len(names)
    formations = []
    assigned = set()  # Track which objects are already in a formation
    
    # Build lookup dictionaries
    name_to_idx = {i: names[i] for i in range(n_objects)}
    norad_to_idx = {norad_ids[i]: i for i in range(n_objects)}
    idx_to_norad = {i: norad_ids[i] for i in range(n_objects)}
    
    # 1. Check for ISS complex
    iss_indices = []
    for i in range(n_objects):
        if norad_ids[i] in KNOWN_FORMATIONS['iss_core']:
            iss_indices.append(i)
            continue
        name_upper = names[i].upper()
        if any(keyword.upper() in name_upper for keyword in KNOWN_FORMATIONS['iss_keywords']):
            iss_indices.append(i)
    
    if iss_indices:
        formations.append(FormationGroup(
            name="ISS Complex",
            reason="docked_modules",
            norad_ids=[norad_ids[i] for i in iss_indices],
            object_names=[names[i] for i in iss_indices]
        ))
        assigned.update(iss_indices)
    
    # 2. Check for CSS complex
    css_indices = []
    for i in range(n_objects):
        if i in assigned:
            continue
        name_upper = names[i].upper()
        if any(keyword.upper() in name_upper for keyword in KNOWN_FORMATIONS['css_keywords']):
            css_indices.append(i)
    
    if css_indices:
        formations.append(FormationGroup(
            name="CSS Complex",
            reason="docked_modules",
            norad_ids=[norad_ids[i] for i in css_indices],
            object_names=[names[i] for i in css_indices]
        ))
        assigned.update(css_indices)
    
    # 3. Check for known pairs (TanDEM, MEV dockings)
    for pair in KNOWN_FORMATIONS['tandem']:
        indices = []
        for i in range(n_objects):
            if i in assigned:
                continue
            name_upper = names[i].upper()
            if any(p.upper() in name_upper for p in pair):
                indices.append(i)
        if len(indices) >= 2:
            formations.append(FormationGroup(
                name="TanDEM-X Formation",
                reason="formation_flying",
                norad_ids=[norad_ids[i] for i in indices],
                object_names=[names[i] for i in indices]
            ))
            assigned.update(indices)
    
    for pair in KNOWN_FORMATIONS['mev_dockings']:
        indices = []
        for i in range(n_objects):
            if i in assigned:
                continue
            name_upper = names[i].upper()
            if any(p.upper() in name_upper for p in pair):
                indices.append(i)
        if len(indices) == 2:
            formations.append(FormationGroup(
                name=f"{pair[0]}/{pair[1]} Docking",
                reason="docked_servicing",
                norad_ids=[norad_ids[i] for i in indices],
                object_names=[names[i] for i in indices]
            ))
            assigned.update(indices)
    
    # 4. Check for common prefix formations (PIESAT, TIANHUI, etc.)
    prefix_groups = {}
    for i in range(n_objects):
        if i in assigned:
            continue
        name = names[i].upper()
        
        # PIESAT pattern
        if 'PIESAT' in name:
            key = 'PIESAT'
            if key not in prefix_groups:
                prefix_groups[key] = []
            prefix_groups[key].append(i)
        # TIANHUI pattern
        elif 'TIANHUI' in name:
            key = 'TIANHUI'
            if key not in prefix_groups:
                prefix_groups[key] = []
            prefix_groups[key].append(i)
        # O3B pattern
        elif 'O3B' in name:
            key = 'O3B'
            if key not in prefix_groups:
                prefix_groups[key] = []
            prefix_groups[key].append(i)
    
    for prefix, indices in prefix_groups.items():
        if len(indices) >= 2:
            formations.append(FormationGroup(
                name=f"{prefix} Formation",
                reason="formation_flying",
                norad_ids=[norad_ids[i] for i in indices],
                object_names=[names[i] for i in indices]
            ))
            assigned.update(indices)
    
    # 5. Velocity-based detection (requires positions and velocities)
    if positions and velocities and len(positions) == n_objects and len(velocities) == n_objects:
        for i in range(n_objects):
            if i in assigned:
                continue
            for j in range(i + 1, n_objects):
                if j in assigned:
                    continue
                
                # Calculate distance
                dx = positions[j][0] - positions[i][0]
                dy = positions[j][1] - positions[i][1]
                dz = positions[j][2] - positions[i][2]
                distance = (dx**2 + dy**2 + dz**2)**0.5
                
                # Calculate relative velocity
                dvx = velocities[j][0] - velocities[i][0]
                dvy = velocities[j][1] - velocities[i][1]
                dvz = velocities[j][2] - velocities[i][2]
                rel_velocity = (dvx**2 + dvy**2 + dvz**2)**0.5
                
                # Check if co-located (within 5km and rel_vel < 0.05 km/s)
                if distance <= 5.0 and rel_velocity < 0.05:
                    formations.append(FormationGroup(
                        name=f"Co-located Pair ({names[i]}/{names[j]})",
                        reason="velocity_based",
                        norad_ids=[norad_ids[i], norad_ids[j]],
                        object_names=[names[i], names[j]]
                    ))
                    assigned.update([i, j])
                    break
    
    # 6. COSPAR/launch-based detection
    if cospar_ids and len(cospar_ids) == n_objects:
        launch_groups = {}
        for i in range(n_objects):
            if i in assigned or not cospar_ids[i]:
                continue
            # Extract launch designator (e.g., "2025-313A" -> "2025-313")
            match = re.match(r'(\d{4}-\d+)', cospar_ids[i])
            if match:
                launch_id = match.group(1)
                if launch_id not in launch_groups:
                    launch_groups[launch_id] = []
                launch_groups[launch_id].append(i)
        
        # Check if objects from same launch are within 5km
        if positions:
            for launch_id, indices in launch_groups.items():
                if len(indices) < 2:
                    continue
                
                # Check if launch is within 30 days (approximate from year-launch number)
                # For simplicity, we'll group all from same launch if they're close
                close_pairs = []
                for i in indices:
                    for j in indices:
                        if i >= j:
                            continue
                        dx = positions[j][0] - positions[i][0]
                        dy = positions[j][1] - positions[i][1]
                        dz = positions[j][2] - positions[i][2]
                        distance = (dx**2 + dy**2 + dz**2)**0.5
                        
                        if distance <= 5.0:
                            if i not in [idx for pair in close_pairs for idx in pair]:
                                if j not in [idx for pair in close_pairs for idx in pair]:
                                    close_pairs.append((i, j))
                
                # Group all close pairs from same launch
                if close_pairs:
                    all_indices = set()
                    for pair in close_pairs:
                        all_indices.update(pair)
                    
                    formations.append(FormationGroup(
                        name=f"Rideshare Group ({launch_id})",
                        reason="rideshare_dispersing",
                        norad_ids=[norad_ids[i] for i in all_indices],
                        object_names=[names[i] for i in all_indices]
                    ))
                    assigned.update(all_indices)
    
    logger.debug("Detected %d formations from %d objects", len(formations), n_objects)
    return formations


def is_formation_pair(
    name1: str,
    name2: str,
    norad_id1: int,
    norad_id2: int,
    rel_velocity_km_s: float = 0.0,
    distance_km: float = 0.0,
) -> tuple[bool, str]:
    """
    Check if two objects form a formation pair.
    
    Args:
        name1, name2: Object names
        norad_id1, norad_id2: NORAD IDs
        rel_velocity_km_s: Relative velocity magnitude (km/s)
        distance_km: Distance between objects (km)
        
    Returns:
        (is_formation, reason_string)
    """
    name1_upper = name1.upper()
    name2_upper = name2.upper()
    
    # Check ISS complex
    iss_ids = set(KNOWN_FORMATIONS['iss_core'])
    iss_match = False
    if norad_id1 in iss_ids or norad_id2 in iss_ids:
        iss_match = True
    if not iss_match:
        for keyword in KNOWN_FORMATIONS['iss_keywords']:
            if keyword.upper() in name1_upper or keyword.upper() in name2_upper:
                iss_match = True
                break
    if iss_match:
        # Check if both are ISS-related
        iss_related_1 = norad_id1 in iss_ids or any(k.upper() in name1_upper for k in KNOWN_FORMATIONS['iss_keywords'])
        iss_related_2 = norad_id2 in iss_ids or any(k.upper() in name2_upper for k in KNOWN_FORMATIONS['iss_keywords'])
        if iss_related_1 and iss_related_2:
            return (True, "ISS Complex (docked_modules)")
    
    # Check CSS complex
    css_related_1 = any(k.upper() in name1_upper for k in KNOWN_FORMATIONS['css_keywords'])
    css_related_2 = any(k.upper() in name2_upper for k in KNOWN_FORMATIONS['css_keywords'])
    if css_related_1 and css_related_2:
        return (True, "CSS Complex (docked_modules)")
    
    # Check TanDEM pair
    if ('TERRASAR' in name1_upper and 'TANDEM' in name2_upper) or \
       ('TANDEM' in name1_upper and 'TERRASAR' in name2_upper):
        return (True, "TanDEM-X Formation (formation_flying)")
    
    # Check MEV dockings
    for pair in KNOWN_FORMATIONS['mev_dockings']:
        p0_upper, p1_upper = pair[0].upper(), pair[1].upper()
        if (p0_upper in name1_upper and p1_upper in name2_upper) or \
           (p1_upper in name1_upper and p0_upper in name2_upper):
            return (True, f"{pair[0]}/{pair[1]} Docking (docked_servicing)")
    
    # Check for common prefix formations
    if 'PIESAT' in name1_upper and 'PIESAT' in name2_upper:
        return (True, "PIESAT Formation (formation_flying)")
    if 'TIANHUI' in name1_upper and 'TIANHUI' in name2_upper:
        return (True, "TIANHUI Formation (formation_flying)")
    if 'O3B' in name1_upper and 'O3B' in name2_upper:
        return (True, "O3B Constellation (constellation_slots)")
    
    # Velocity-based check
    if distance_km > 0 and distance_km <= 5.0 and rel_velocity_km_s < 0.05:
        return (True, "Co-located (velocity_based)")
    
    # NOT a formation (e.g., Starlink satellites)
    return (False, "")


def filter_formation_events(
    events: list[dict],
    formations: list[FormationGroup] | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Filter conjunction events to separate real threats from formation encounters.
    
    Args:
        events: List of conjunction events, each with keys:
                'name1', 'name2', 'norad_id1', 'norad_id2',
                'relative_velocity_km_s', 'miss_distance_km'
        formations: Optional pre-detected formations
        
    Returns:
        (real_threats, formation_events) tuple of event lists
    """
    real_threats = []
    formation_events = []
    
    # Build formation lookup if provided
    formation_pairs = set()
    if formations:
        for formation in formations:
            norad_list = formation.norad_ids
            for i in range(len(norad_list)):
                for j in range(i + 1, len(norad_list)):
                    # Store both orderings
                    formation_pairs.add((norad_list[i], norad_list[j]))
                    formation_pairs.add((norad_list[j], norad_list[i]))
    
    for event in events:
        norad_id1 = event.get('norad_id1')
        norad_id2 = event.get('norad_id2')
        
        # Check if this pair is in a known formation
        if formations and (norad_id1, norad_id2) in formation_pairs:
            formation_events.append(event)
            continue
        
        # Otherwise check using is_formation_pair
        is_formation, reason = is_formation_pair(
            name1=event.get('name1', ''),
            name2=event.get('name2', ''),
            norad_id1=norad_id1,
            norad_id2=norad_id2,
            rel_velocity_km_s=event.get('relative_velocity_km_s', 0.0),
            distance_km=event.get('miss_distance_km', 0.0),
        )
        
        if is_formation:
            formation_events.append(event)
        else:
            real_threats.append(event)
    
    return (real_threats, formation_events)
