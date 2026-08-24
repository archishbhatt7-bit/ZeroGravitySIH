"""ZeroGravity hosted API client.

Provides a high-level interface to the ZeroGravity cloud service for
operators who want managed screening without running infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zerogravity.core.screening import ConjunctionEvent
    from zerogravity.core.tle import TLE

_DEFAULT_BASE_URL = "https://api.zerogravity.dev"


@dataclass
class ZeroGravity:
    """Client for the ZeroGravity hosted API.

    Args:
        api_key: Your ZeroGravity API key (starts with ``og_``).
        base_url: API base URL. Defaults to production.

    Example::

        og = ZeroGravity(api_key="og_live_abc123")
        catalog = og.load_catalog(operator="STARLINK")
        events = og.screen(catalog, threshold=1e-5)
    """

    api_key: str
    base_url: str = _DEFAULT_BASE_URL

    def load_catalog(self, *, operator: str | None = None) -> list[TLE]:
        """Load a TLE catalog from the ZeroGravity service.

        Args:
            operator: Filter by operator name.

        Returns:
            List of TLE objects.

        Raises:
            NotImplementedError: The hosted API is not yet available.
        """
        raise NotImplementedError(
            "The ZeroGravity hosted API is coming soon. "
            "Sign up at https://zerogravity.dev for early access."
        )

    def screen(
        self,
        catalog: list[TLE],
        *,
        threshold: float = 1e-4,
        days: float = 7.0,
    ) -> list[ConjunctionEvent]:
        """Screen a catalog for conjunctions via the hosted API.

        Args:
            catalog: TLEs to screen.
            threshold: Collision probability threshold.
            days: Screening window in days.

        Returns:
            List of conjunction events.

        Raises:
            NotImplementedError: The hosted API is not yet available.
        """
        raise NotImplementedError(
            "The ZeroGravity hosted API is coming soon. "
            "Sign up at https://zerogravity.dev for early access."
        )
