"""TLE (Two-Line Element) parsing and management.

This module provides TLE parsing using the sgp4 library, with a clean
Pythonic interface for working with orbital elements.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sgp4.api import Satrec, WGS72
from sgp4.earth_gravity import wgs72

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TLE:
    """A parsed Two-Line Element set.

    Attributes:
        name: Satellite name (line 0, if provided).
        line1: Raw TLE line 1.
        line2: Raw TLE line 2.
        norad_id: NORAD catalog number.
        epoch: Epoch as a UTC datetime.
        inclination_deg: Orbital inclination in degrees.
        raan_deg: Right ascension of ascending node in degrees.
        eccentricity: Orbital eccentricity (dimensionless).
        arg_perigee_deg: Argument of perigee in degrees.
        mean_anomaly_deg: Mean anomaly in degrees.
        mean_motion_rev_per_day: Mean motion in revolutions per day.
        bstar: BSTAR drag term.
        satrec: Underlying sgp4 Satrec object for propagation.
    """

    name: str
    line1: str
    line2: str
    norad_id: int
    epoch: datetime
    inclination_deg: float
    raan_deg: float
    eccentricity: float
    arg_perigee_deg: float
    mean_anomaly_deg: float
    mean_motion_rev_per_day: float
    bstar: float
    satrec: Satrec = field(repr=False, compare=False)

    @classmethod
    def from_lines(cls, line1: str, line2: str, name: str = "") -> TLE:
        """Parse a TLE from two (or three) lines.

        Args:
            line1: TLE line 1 (69 characters).
            line2: TLE line 2 (69 characters).
            name: Optional satellite name (line 0).

        Returns:
            A parsed TLE object.

        Raises:
            ValueError: If the TLE lines are malformed.
        """
        line1 = line1.strip()
        line2 = line2.strip()

        if len(line1) != 69 or not line1.startswith("1"):
            logger.error("Invalid TLE line 1: %r", line1)
            raise ValueError(f"Invalid TLE line 1: {line1!r}")
        if len(line2) != 69 or not line2.startswith("2"):
            logger.error("Invalid TLE line 2: %r", line2)
            raise ValueError(f"Invalid TLE line 2: {line2!r}")

        sat = Satrec.twoline2rv(line1, line2, WGS72)

        # Extract epoch
        year = int(line1[18:20])
        year = year + 2000 if year < 57 else year + 1900
        day_of_year = float(line1[20:32])
        epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(
            days=day_of_year - 1
        )

        norad_id = int(line1[2:7].strip())

        logger.debug("Parsed TLE for NORAD %d (epoch %s)", norad_id, epoch.isoformat())

        return cls(
            name=name.strip(),
            line1=line1,
            line2=line2,
            norad_id=norad_id,
            epoch=epoch,
            inclination_deg=sat.inclo * 180.0 / math.pi,
            raan_deg=sat.nodeo * 180.0 / math.pi,
            eccentricity=sat.ecco,
            arg_perigee_deg=sat.argpo * 180.0 / math.pi,
            mean_anomaly_deg=sat.mo * 180.0 / math.pi,
            mean_motion_rev_per_day=sat.no_kozai * 1440 / (2 * math.pi),
            bstar=sat.bstar,
            satrec=sat,
        )

    def __str__(self) -> str:
        header = f"0 {self.name}\n" if self.name else ""
        return f"{header}{self.line1}\n{self.line2}"


def parse_tle(text: str) -> list[TLE]:
    """Parse one or more TLEs from text.

    Handles both 2-line and 3-line (with name) formats.

    Args:
        text: Raw TLE text, one or more TLE sets separated by newlines.

    Returns:
        A list of parsed TLE objects.
    """
    lines = [l.rstrip() for l in text.strip().splitlines() if l.strip()]
    tles: list[TLE] = []
    i = 0

    while i < len(lines):
        if lines[i].startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
            tles.append(TLE.from_lines(lines[i], lines[i + 1]))
            i += 2
        elif (
            not lines[i].startswith("1 ")
            and not lines[i].startswith("2 ")
            and i + 2 < len(lines)
            and lines[i + 1].startswith("1 ")
            and lines[i + 2].startswith("2 ")
        ):
            tles.append(TLE.from_lines(lines[i + 1], lines[i + 2], name=lines[i]))
            i += 3
        else:
            i += 1  # skip unrecognized lines

    logger.debug("Parsed %d TLEs from text", len(tles))
    return tles
