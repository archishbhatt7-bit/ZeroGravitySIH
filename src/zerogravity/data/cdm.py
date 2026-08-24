"""Conjunction Data Message (CDM) parser and writer.

CDMs are the standard format (CCSDS 508.0-B-1) for exchanging conjunction
assessment information between space operators and agencies.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger(__name__)
from numpy.typing import NDArray


@dataclass
class CDMObject:
    """One object's data within a CDM."""

    designator: str  # NORAD ID as string
    name: str
    international_designator: str
    ephemeris_name: str
    covariance_method: str
    maneuverable: str
    # Position/velocity in specified frame
    x_km: float
    y_km: float
    z_km: float
    x_dot_km_s: float
    y_dot_km_s: float
    z_dot_km_s: float
    # RTN covariance (lower-triangular, 6x6)
    covariance: NDArray[np.float64] | None  # shape (6,6), None if not provided


@dataclass
class CDM:
    """A parsed Conjunction Data Message."""

    ccsds_cdm_vers: str
    creation_date: datetime
    originator: str
    message_id: str
    tca: datetime
    miss_distance_km: float
    relative_speed_km_s: float
    collision_probability: float | None
    object1: CDMObject
    object2: CDMObject

    @classmethod
    def from_kvn(cls, text: str) -> CDM:
        """Parse a CDM from KVN (Key-Value Notation) format.

        Args:
            text: Raw CDM text in CCSDS KVN format.

        Returns:
            A parsed CDM object.

        Raises:
            ValueError: If the CDM is malformed or missing required fields.
        """
        lines = text.strip().splitlines()
        data: dict[str, str] = {}
        
        # Parse key-value pairs
        for line in lines:
            line = line.strip()
            if not line or line.startswith("COMMENT"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Remove units in brackets
                value = re.sub(r'\s*\[.*?\]\s*', '', value)
                data[key] = value

        # Parse header fields
        try:
            ccsds_cdm_vers = data.get("CCSDS_CDM_VERS", "1.0")
            creation_date = _parse_datetime(data["CREATION_DATE"])
            originator = data["ORIGINATOR"]
            message_id = data["MESSAGE_ID"]
            tca = _parse_datetime(data["TCA"])
            miss_distance_km = float(data["MISS_DISTANCE"])
            relative_speed_km_s = float(data["RELATIVE_SPEED"])
            
            # Collision probability is optional
            collision_probability = None
            if "COLLISION_PROBABILITY" in data:
                try:
                    collision_probability = float(data["COLLISION_PROBABILITY"])
                except (ValueError, KeyError):
                    pass

        except (KeyError, ValueError) as e:
            logger.error("Missing or invalid required CDM header field: %s", e)
            raise ValueError(f"Missing or invalid required CDM header field: {e}")

        # Parse objects - need to split data by OBJECT marker
        obj1_data: dict[str, str] = {}
        obj2_data: dict[str, str] = {}
        current_obj = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "OBJECT" in line and "=" in line:
                key, _, value = line.partition("=")
                if key.strip() == "OBJECT":
                    current_obj = value.strip()
                    continue
            
            if "=" in line and current_obj:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                value = re.sub(r'\s*\[.*?\]\s*', '', value)
                
                if current_obj == "OBJECT1":
                    obj1_data[key] = value
                elif current_obj == "OBJECT2":
                    obj2_data[key] = value

        # Parse each object
        try:
            object1 = _parse_cdm_object(obj1_data)
            object2 = _parse_cdm_object(obj2_data)
        except (KeyError, ValueError) as e:
            raise ValueError(f"Error parsing CDM object: {e}")

        return cls(
            ccsds_cdm_vers=ccsds_cdm_vers,
            creation_date=creation_date,
            originator=originator,
            message_id=message_id,
            tca=tca,
            miss_distance_km=miss_distance_km,
            relative_speed_km_s=relative_speed_km_s,
            collision_probability=collision_probability,
            object1=object1,
            object2=object2,
        )

    @classmethod
    def from_xml(cls, xml_text: str) -> CDM:
        """Parse a CDM from XML format.

        Args:
            xml_text: Raw CDM XML string.

        Returns:
            A parsed CDM object.

        Raises:
            ValueError: If the XML is malformed or missing required fields.
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")

        # Handle namespaces - detect if namespace is present
        ns_match = re.search(r'xmlns="([^"]+)"', xml_text)
        if ns_match:
            ns = {"ns": ns_match.group(1)}
            ns_prefix = "ns:"
        else:
            ns = {}
            ns_prefix = ""
        
        def find_text(elem, path: str, default: str | None = None) -> str:
            """Find element text, handling namespaces."""
            # Try with detected namespace
            if ns:
                node = elem.find(path.replace("//", f"//{ns_prefix}"), ns)
            else:
                node = elem.find(path)
            
            # Fallback: try without namespace
            if node is None:
                node = elem.find(path)
            
            if node is None:
                if default is not None:
                    return default
                raise ValueError(f"Missing required field: {path}")
            return node.text or ""

        try:
            # Parse header
            ccsds_cdm_vers = find_text(root, ".//CCSDS_CDM_VERS", "1.0")
            creation_date = _parse_datetime(find_text(root, ".//CREATION_DATE"))
            originator = find_text(root, ".//ORIGINATOR")
            message_id = find_text(root, ".//MESSAGE_ID")
            tca = _parse_datetime(find_text(root, ".//TCA"))
            miss_distance_km = float(find_text(root, ".//MISS_DISTANCE"))
            relative_speed_km_s = float(find_text(root, ".//RELATIVE_SPEED"))
            
            collision_probability = None
            prob_text = find_text(root, ".//COLLISION_PROBABILITY", "")
            if prob_text:
                try:
                    collision_probability = float(prob_text)
                except ValueError:
                    pass

            # Parse objects (segments) - try with and without namespace
            if ns:
                segments = root.findall(f".//{ns_prefix}segment", ns)
            else:
                segments = root.findall(".//segment")
            
            if not segments:
                # Fallback: try without namespace
                segments = root.findall(".//segment")
            if len(segments) < 2:
                raise ValueError("CDM must contain at least 2 segments (OBJECT1 and OBJECT2)")

            object1 = _parse_cdm_object_xml(segments[0])
            object2 = _parse_cdm_object_xml(segments[1])

        except (ValueError, IndexError) as e:
            raise ValueError(f"Error parsing CDM XML: {e}")

        return cls(
            ccsds_cdm_vers=ccsds_cdm_vers,
            creation_date=creation_date,
            originator=originator,
            message_id=message_id,
            tca=tca,
            miss_distance_km=miss_distance_km,
            relative_speed_km_s=relative_speed_km_s,
            collision_probability=collision_probability,
            object1=object1,
            object2=object2,
        )

    def to_kvn(self) -> str:
        """Export this CDM as KVN format text.

        Raises:
            NotImplementedError: CDM export is not yet implemented.
        """
        raise NotImplementedError("CDM export is planned for v0.2.")


def _parse_datetime(dt_str: str) -> datetime:
    """Parse CCSDS datetime format (ISO 8601). Returns timezone-aware UTC datetime."""
    # Handle both with and without fractional seconds
    dt_str = dt_str.strip()
    for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(dt_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Invalid datetime format: {dt_str}")


def _parse_cdm_object(data: dict[str, str]) -> CDMObject:
    """Parse a CDMObject from KVN key-value dict."""
    designator = data.get("OBJECT_DESIGNATOR", "")
    name = data.get("OBJECT_NAME", "")
    international_designator = data.get("INTERNATIONAL_DESIGNATOR", "")
    ephemeris_name = data.get("EPHEMERIS_NAME", "")
    covariance_method = data.get("COVARIANCE_METHOD", "")
    maneuverable = data.get("MANEUVERABLE", "")
    
    # Position and velocity
    x_km = float(data.get("X", 0))
    y_km = float(data.get("Y", 0))
    z_km = float(data.get("Z", 0))
    x_dot_km_s = float(data.get("X_DOT", 0))
    y_dot_km_s = float(data.get("Y_DOT", 0))
    z_dot_km_s = float(data.get("Z_DOT", 0))
    
    # Parse covariance matrix (RTN frame, lower-triangular)
    covariance = _parse_covariance_kvn(data)
    
    return CDMObject(
        designator=designator,
        name=name,
        international_designator=international_designator,
        ephemeris_name=ephemeris_name,
        covariance_method=covariance_method,
        maneuverable=maneuverable,
        x_km=x_km,
        y_km=y_km,
        z_km=z_km,
        x_dot_km_s=x_dot_km_s,
        y_dot_km_s=y_dot_km_s,
        z_dot_km_s=z_dot_km_s,
        covariance=covariance,
    )


def _parse_covariance_kvn(data: dict[str, str]) -> NDArray[np.float64] | None:
    """Build 6x6 symmetric covariance matrix from RTN lower-triangular elements.
    
    The covariance is provided as:
    CR_R, CT_R, CT_T, CN_R, CN_T, CN_N, 
    CRDOT_R, CRDOT_T, CRDOT_N, CRDOT_RDOT,
    CTDOT_R, CTDOT_T, CTDOT_N, CTDOT_RDOT, CTDOT_TDOT,
    CNDOT_R, CNDOT_T, CNDOT_N, CNDOT_RDOT, CNDOT_TDOT, CNDOT_NDOT
    """
    # Check if any covariance data exists
    if "CR_R" not in data:
        return None
    
    # Initialize 6x6 matrix
    cov = np.zeros((6, 6), dtype=np.float64)
    
    # Lower-triangular elements (row, col, key)
    elements = [
        (0, 0, "CR_R"),
        (1, 0, "CT_R"), (1, 1, "CT_T"),
        (2, 0, "CN_R"), (2, 1, "CN_T"), (2, 2, "CN_N"),
        (3, 0, "CRDOT_R"), (3, 1, "CRDOT_T"), (3, 2, "CRDOT_N"), (3, 3, "CRDOT_RDOT"),
        (4, 0, "CTDOT_R"), (4, 1, "CTDOT_T"), (4, 2, "CTDOT_N"), (4, 3, "CTDOT_RDOT"), (4, 4, "CTDOT_TDOT"),
        (5, 0, "CNDOT_R"), (5, 1, "CNDOT_T"), (5, 2, "CNDOT_N"), (5, 3, "CNDOT_RDOT"), (5, 4, "CNDOT_TDOT"), (5, 5, "CNDOT_NDOT"),
    ]
    
    for row, col, key in elements:
        if key in data:
            value = float(data[key])
            cov[row, col] = value
            # Mirror to upper triangle (symmetric matrix)
            if row != col:
                cov[col, row] = value
    
    return cov


def _parse_cdm_object_xml(segment: ET.Element) -> CDMObject:
    """Parse a CDMObject from XML segment element."""
    def find_text(path: str, default: str = "") -> str:
        # Try to find with any namespace
        node = segment.find(path)
        if node is None:
            # Try descendant search (.//)
            parts = path.split("//")
            if len(parts) > 1:
                node = segment.find(f".//{parts[-1]}")
        if node is None:
            # Iterate through all descendants
            for elem in segment.iter():
                if elem.tag.endswith(path.split("/")[-1]):
                    node = elem
                    break
        return node.text if node is not None and node.text else default
    
    designator = find_text(".//OBJECT_DESIGNATOR")
    name = find_text(".//OBJECT_NAME")
    international_designator = find_text(".//INTERNATIONAL_DESIGNATOR")
    ephemeris_name = find_text(".//EPHEMERIS_NAME")
    covariance_method = find_text(".//COVARIANCE_METHOD")
    maneuverable = find_text(".//MANEUVERABLE")
    
    x_km = float(find_text(".//X", "0"))
    y_km = float(find_text(".//Y", "0"))
    z_km = float(find_text(".//Z", "0"))
    x_dot_km_s = float(find_text(".//X_DOT", "0"))
    y_dot_km_s = float(find_text(".//Y_DOT", "0"))
    z_dot_km_s = float(find_text(".//Z_DOT", "0"))
    
    # Parse covariance
    covariance = _parse_covariance_xml(segment)
    
    return CDMObject(
        designator=designator,
        name=name,
        international_designator=international_designator,
        ephemeris_name=ephemeris_name,
        covariance_method=covariance_method,
        maneuverable=maneuverable,
        x_km=x_km,
        y_km=y_km,
        z_km=z_km,
        x_dot_km_s=x_dot_km_s,
        y_dot_km_s=y_dot_km_s,
        z_dot_km_s=z_dot_km_s,
        covariance=covariance,
    )


def _parse_covariance_xml(segment: ET.Element) -> NDArray[np.float64] | None:
    """Parse covariance matrix from XML segment."""
    def find_text(path: str) -> str | None:
        node = segment.find(path)
        if node is None:
            parts = path.split("//")
            if len(parts) > 1:
                node = segment.find(f".//{parts[-1]}")
        if node is None:
            for elem in segment.iter():
                if elem.tag.endswith(path.split("/")[-1]):
                    node = elem
                    break
        return node.text if node is not None else None
    
    # Check if covariance exists
    if find_text(".//CR_R") is None:
        return None
    
    cov = np.zeros((6, 6), dtype=np.float64)
    
    elements = [
        (0, 0, "CR_R"),
        (1, 0, "CT_R"), (1, 1, "CT_T"),
        (2, 0, "CN_R"), (2, 1, "CN_T"), (2, 2, "CN_N"),
        (3, 0, "CRDOT_R"), (3, 1, "CRDOT_T"), (3, 2, "CRDOT_N"), (3, 3, "CRDOT_RDOT"),
        (4, 0, "CTDOT_R"), (4, 1, "CTDOT_T"), (4, 2, "CTDOT_N"), (4, 3, "CTDOT_RDOT"), (4, 4, "CTDOT_TDOT"),
        (5, 0, "CNDOT_R"), (5, 1, "CNDOT_T"), (5, 2, "CNDOT_N"), (5, 3, "CNDOT_RDOT"), (5, 4, "CNDOT_TDOT"), (5, 5, "CNDOT_NDOT"),
    ]
    
    for row, col, key in elements:
        value_str = find_text(f".//{key}")
        if value_str:
            value = float(value_str)
            cov[row, col] = value
            if row != col:
                cov[col, row] = value
    
    return cov
