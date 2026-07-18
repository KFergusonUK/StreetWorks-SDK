"""Typed model for Autobahn GmbH roadworks (Germany's national motorway
network).

Every real record observed live carries geometry as a ``LineString``
(2,873/2,873 in a full 113-road fetch, 2-767 vertices) - not a single
point - so, unlike DATEX/WZDx, there's no "Point" case to normalise
against; :attr:`Roadworks.points` is always the line. ``coordinate`` (one
representative point, native ``(lat, long)`` order from the source's own
``coordinate`` field) and ``points`` (the full line, native GeoJSON
``(lon, lat)`` order from ``geometry.coordinates``) are kept in their own
native axis orders here, same as WZDx's ``Geometry`` - the explicit flip
happens in ``streetworks.common.from_autobahn``, not here.

There is no genuine road-number field on a record - the road only comes
from the request path (redundantly echoed in ``title``'s prefix), so
:attr:`Roadworks.road` is set by the client from whichever road it fetched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

__all__ = ["Roadworks"]

JSON = dict[str, Any]

#: The two real ``display_type`` values observed live. ``ROADWORKS`` always
#: carries a verified ``startTimestamp``; ``SHORT_TERM_ROADWORKS`` never
#: does (0/1,184 in a full fetch) - dates for that class come only from
#: free text, see :mod:`streetworks.autobahn.parser`.
DISPLAY_TYPES = frozenset({"ROADWORKS", "SHORT_TERM_ROADWORKS"})


@dataclass
class Roadworks:
    """One roadworks item from Autobahn GmbH's ``services/roadworks``
    endpoint. Every field beyond ``identifier``/``road`` is optional -
    parsing never raises on a malformed record, it degrades to
    ``None``/``()`` and the original JSON item is always kept on ``raw``.
    """

    identifier: str
    road: str
    title: str | None = None
    subtitle: str | None = None
    description: tuple[str, ...] = ()
    display_type: str | None = None
    is_blocked: bool | None = None
    future: bool | None = None
    impact_lower: str | None = None
    impact_upper: str | None = None
    impact_symbols: tuple[str, ...] = ()
    #: One representative point, native ``(lat, long)`` order (the source's
    #: own ``coordinate`` field - redundant with ``points[0]`` but reversed
    #: axis order, since that field is genuinely lat/long, not lon/lat).
    coordinate: tuple[float, float] | None = None
    #: Full line geometry, native GeoJSON ``(lon, lat)`` order, straight
    #: from ``geometry.coordinates`` - reversed from ``coordinate`` above.
    points: tuple[tuple[float, float], ...] = ()
    #: The record's own start. Verified (``is_start_verified``) when read
    #: from the real ``startTimestamp`` field (``ROADWORKS`` only); estimated
    #: (extracted from ``description`` free text) otherwise - see the parser
    #: module docstring for the exact shapes handled and their coverage.
    start: datetime | None = None
    is_start_verified: bool = False
    #: The record's own end - always estimated-grade, since no end-date
    #: field exists anywhere in the API, verified or otherwise.
    end: datetime | None = None
    #: The *overall measure's* end date (``"(Ende der Gesamtmaßnahme: ...)"``
    #: in the description) - a coarser, group-level date shared by every
    #: record under the same :attr:`identifier_prefix`, confirmed live
    #: (624/624 real multi-record groups agree on it, zero disagreements).
    #: Not the same thing as :attr:`end`, which is this one record's own
    #: phase end.
    overall_end: datetime | None = None
    raw: JSON = field(default_factory=dict)

    @property
    def identifier_prefix(self) -> str:
        """The works-level grouping key - the part of ``identifier`` before
        its first ``--``. Confirmed live: within one road's response,
        records sharing this prefix always agree on ``overall_end``
        (624/624 real multi-record groups) and are genuinely the phases of
        one works, not a coincidence - see
        :func:`streetworks.common.from_autobahn`."""
        prefix, _, _ = self.identifier.partition("--")
        return prefix

    @property
    def is_short_term(self) -> bool:
        return self.display_type == "SHORT_TERM_ROADWORKS"
