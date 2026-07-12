"""Shared ISO-8601 timestamp parsing, tolerant of non-standard fractional-
second precision.

``datetime.fromisoformat`` only accepts 0/3/6-digit fractional seconds on
Python < 3.11. Real feeds don't respect that: National Highways emits
2-digit fractions (``"...29.29Z"``, see ``streetworks.datex2``), WA's WZDx
feed emits 7-digit ones (``"...32.3308699+00:00"``) - both broke a naive
``fromisoformat`` call on 3.10. Extracted here so the same fix doesn't need
re-deriving (or re-breaking) in every provider that hits it.
"""

from __future__ import annotations

import re
from datetime import datetime

__all__ = ["parse_iso8601"]

_FRACTIONAL_SECONDS = re.compile(r"\.(\d+)")


def parse_iso8601(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp, padding/truncating fractional-second
    precision to 6 digits before handing off to ``datetime.fromisoformat``.
    Returns ``None`` for empty input or anything that still doesn't parse -
    never raises, since source data is never guaranteed clean."""
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    match = _FRACTIONAL_SECONDS.search(value)
    if match:
        micros = match.group(1)[:6].ljust(6, "0")
        value = f"{value[: match.start()]}.{micros}{value[match.end() :]}"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
