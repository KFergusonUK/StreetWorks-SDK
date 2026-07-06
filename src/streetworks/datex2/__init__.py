"""DATEX II - the European standard for traffic and roadworks data exchange.

A streaming, namespace-tolerant parser for SituationPublication roadworks
(DATEX II v3 and v2), plus source adapters for National Access Point feeds.
The first adapter is the Netherlands' credential-free NDW open data.
"""

from .models import Location, Period, Situation, SituationRecord, Validity
from .ndw import BASE_URL, PLANNED_WORKS_FEED, NDWClient
from .parser import iter_roadworks, iter_situations

__all__ = [
    "iter_situations",
    "iter_roadworks",
    "Situation",
    "SituationRecord",
    "Validity",
    "Period",
    "Location",
    "NDWClient",
    "BASE_URL",
    "PLANNED_WORKS_FEED",
]
