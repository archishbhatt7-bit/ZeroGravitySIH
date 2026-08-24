"""Space-Track.org API client.

Provides authenticated access to the Space-Track catalog for fetching
TLEs, conjunction data messages, and satellite metadata.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)

from zerogravity.core.tle import TLE, parse_tle
from zerogravity.data.cdm import CDM


@dataclass
class SpaceTrackClient:
    """Client for the Space-Track.org REST API.

    Requires a Space-Track account. Register at https://www.space-track.org.

    Attributes:
        identity: Space-Track username/email.
        password: Space-Track password.
    """

    identity: str
    password: str
    _session: requests.Session = field(default_factory=requests.Session, repr=False)
    _authenticated: bool = field(default=False, repr=False)

    BASE_URL = "https://www.space-track.org"
    LOGIN_URL = f"{BASE_URL}/ajaxauth/login"

    def _login(self) -> None:
        """Authenticate with Space-Track.

        Stores session cookies for subsequent requests.

        Raises:
            requests.HTTPError: If authentication fails.
        """
        response = self._session.post(
            self.LOGIN_URL,
            data={"identity": self.identity, "password": self.password},
        )
        response.raise_for_status()

        # Check if login was successful
        if "error" in response.text.lower() or response.status_code != 200:
            logger.error("Space-Track authentication failed")
            raise requests.HTTPError(f"Space-Track authentication failed: {response.text}")

        logger.debug("Space-Track authentication successful")
        self._authenticated = True

    def _request(self, url: str) -> str:
        """Make authenticated request to Space-Track.

        Args:
            url: Full URL to request.

        Returns:
            Response text.

        Raises:
            requests.HTTPError: If the request fails.
        """
        if not self._authenticated:
            self._login()

        response = self._session.get(url)

        # If we get a 401, try re-authenticating once
        if response.status_code == 401:
            self._authenticated = False
            self._login()
            response = self._session.get(url)

        response.raise_for_status()
        return response.text

    def fetch_tle(self, norad_id: int) -> TLE:
        """Fetch the latest TLE for a NORAD catalog number.

        Args:
            norad_id: NORAD catalog number.

        Returns:
            The latest TLE for the object.

        Raises:
            ValueError: If no TLE is found for the given NORAD ID.
            requests.HTTPError: If the request fails.
        """
        url = (
            f"{self.BASE_URL}/basicspacedata/query/class/gp/"
            f"NORAD_CAT_ID/{norad_id}/orderby/EPOCH desc/limit/1/format/tle"
        )

        response_text = self._request(url)

        if not response_text.strip():
            raise ValueError(f"No TLE found for NORAD ID {norad_id}")

        tles = parse_tle(response_text)

        if not tles:
            raise ValueError(f"Failed to parse TLE for NORAD ID {norad_id}")

        return tles[0]

    def fetch_catalog(self, *, epoch: str = ">now-30", decay_date: str = "null-val") -> list[TLE]:
        """Fetch a catalog of TLEs.

        Args:
            epoch: Epoch filter (e.g., ">now-30" for TLEs within last 30 days).
            decay_date: Decay date filter ("null-val" for active satellites).

        Returns:
            List of TLE objects.

        Raises:
            requests.HTTPError: If the request fails.
        """
        url = (
            f"{self.BASE_URL}/basicspacedata/query/class/gp/"
            f"EPOCH/{epoch}/DECAY_DATE/{decay_date}/"
            f"orderby/NORAD_CAT_ID/format/tle"
        )

        response_text = self._request(url)

        if not response_text.strip():
            return []

        return parse_tle(response_text)

    def fetch_cdms(self, *, norad_id: int | None = None, days: int = 7) -> list[CDM]:
        """Fetch recent Conjunction Data Messages.

        Args:
            norad_id: Optional NORAD ID to filter CDMs for a specific object.
            days: Number of days to look back (default: 7).

        Returns:
            List of parsed CDM objects.

        Raises:
            requests.HTTPError: If the request fails.

        Note:
            CDMs may require special access permissions on Space-Track.
        """
        # Build query URL
        url_parts = [f"{self.BASE_URL}/basicspacedata/query/class/cdm_public"]

        if norad_id is not None:
            url_parts.append(f"SAT_1_ID/{norad_id}")

        url_parts.extend(["orderby/TCA desc", "limit/100", "format/kvn"])

        url = "/".join(url_parts)

        response_text = self._request(url)

        if not response_text.strip():
            return []

        # Split multiple CDMs (each starts with CCSDS_CDM_VERS)
        cdms: list[CDM] = []
        cdm_texts = response_text.split("CCSDS_CDM_VERS")

        for i, cdm_text in enumerate(cdm_texts):
            if not cdm_text.strip():
                continue

            # Restore the split header
            if i > 0:
                cdm_text = "CCSDS_CDM_VERS" + cdm_text

            try:
                cdm = CDM.from_kvn(cdm_text)
                cdms.append(cdm)
            except (ValueError, KeyError):
                # Skip malformed CDMs
                continue

        return cdms
