"""Toronto Road Restrictions/Closures - the City of Toronto's own real,
live, keyless feed, found while surveying Canadian municipal portals
alongside :mod:`streetworks.vancouver`. Confirmed live 2026-08-21: 2,274
real records, ``GET https://secure.toronto.ca/opendata/cart/road_restrictions/v3?format=json``,
no key required.

**A real, confirmed JSON defect in the source, worked around here, not
silently ignored.** One real record (of 2,274) has a stray, un-escaped
backslash inside a free-text ``description`` value
(``"WATER \\ SEWER"``, evidently meant as ``"WATER / SEWER"``) - a
genuine live bug in Toronto's own export, not a fetch/encoding error on
this SDK's side. Confirmed narrow, not systemic: a full scan of the raw
2,274-record, 3.3 MB response found exactly one backslash that isn't
part of a valid JSON escape sequence. :func:`_repair_json` escapes any
such stray backslash before parsing - a defensive, source-agnostic fix
(it does nothing to a response that doesn't have this defect), not a
guess at Toronto's own intent.

**Every real record is roadworks-relevant - no filter needed.**
``type`` has exactly two real values confirmed live: ``"CONSTRUCTION"``
(1,823 records) and ``"ROAD_CLOSED"`` (451) - and every real
``ROAD_CLOSED`` record carries ``subType == "ROAD_CLOSED_CONSTRUCTION"``
(451/451, an exact match), confirming both are genuinely construction-
caused, not e.g. an event closure. No non-roadworks ``type`` value was
observed.

**Real field list** (confirmed live): ``id`` (a real stable identifier,
e.g. ``"Tor-RD52026-4934"``), ``road``, ``name`` (a real, already-composed
location description, e.g. ``"Kennedy Rd 103 m North of Hepc to 44 m
North of Radnor Ave"``), ``district`` (real Toronto districts, e.g.
``"SCARBOROUGH"``, ``"ETOBICOKE"``, plus real boundary-spanning combos
like ``"YORK and NORTH YORK"``), ``latitude``/``longitude`` (plain WGS84
decimal fields, always populated - 0/2,274 null, confirmed live),
``roadClass``, ``planned``/``severityOverride``, ``source``/
``workEventType``/``permitType`` (confirmed live to always carry the
identical value across all three - only one is genuinely needed) -
**real and often rich (organisation names like "Waterfront Toronto",
"Metrolinx", "TTC"; activity descriptions like "Storage of materials and
equipment") on 1,324/2,274 real records, but a genuine, confirmed export
defect leaves the other 950/2,274 (42%) holding the identical literal
placeholder string** ``'{"tabledata":[{"Option":"Transportation
Services"'`` **instead of real text** - carried through as-is, per this
SDK's "state what the source states" discipline, not filtered or
guessed at. ``createdTime``/``lastUpdated``/``startTime``/``endTime``
(Unix epoch **milliseconds** - confirmed by magnitude), ``workPeriod``,
``expired`` (always ``0`` in the real pull - this endpoint appears to
only ever return currently-valid closures), ``contractor`` (real and
populated on 2,214/2,274 records - genuinely richer than most roadworks
sources this SDK has), ``description`` (real free-text impact/work
detail), ``specialEvent``, ``fromRoad``/``toRoad``/``atRoad``,
``directionsAffected`` (a real, clean 2-value enum:
``"ONE_DIRECTION"``/``"BOTH_DIRECTIONS"``), per-day
``scheduleMonday``-``scheduleSunday`` fields, ``URL``, ``geoPolyline`` (a
real but bespoke string format - comma-joined ``[lon,lat]`` bracket
pairs, **not** JSON array syntax and **not** Google's Encoded Polyline
Algorithm Format used elsewhere in this SDK - :func:`_parse_polyline`
extracts every real pair via regex), ``maxImpact``/``currImpact``.

**Licence: not specified** - the CKAN catalogue entry states
``license_id: "notspecified"``, the same honest-gap tier this SDK
already gives Jersey RoadWorkx and NYC DOT.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "TorontoClient"]

JSON = dict[str, Any]

#: Confirmed live, no key required. See module docstring.
BASE_URL = "https://secure.toronto.ca/opendata/cart/road_restrictions/v3"

#: Matches a valid two-character JSON escape (group 1) or a lone
#: backslash (unmatched group 1) - matching greedily left-to-right so a
#: real ``\\`` pair is consumed as one valid unit rather than its second
#: backslash being mistaken for the start of its own escape. See
#: module docstring for the one real, confirmed stray occurrence this
#: guards against.
_ESCAPE_OR_STRAY_BACKSLASH = re.compile(r'\\(["\\/bfnrtu])|\\')

#: A real ``[lon,lat]`` pair inside Toronto's own bespoke geoPolyline
#: string format - see module docstring.
_POLYLINE_PAIR = re.compile(r"\[(-?[\d.]+),(-?[\d.]+)\]")


def _repair_json(text: str) -> str:
    """Escapes any stray backslash not already part of a valid JSON
    escape sequence - see module docstring. A no-op on a response
    without this defect."""

    def _repl(match: re.Match[str]) -> str:
        return match.group(0) if match.group(1) else "\\\\"

    return _ESCAPE_OR_STRAY_BACKSLASH.sub(_repl, text)


def parse_polyline(value: str | None) -> tuple[tuple[float, float], ...]:
    """Parse Toronto's own bespoke ``geoPolyline`` string format into
    real ``(lon, lat)`` pairs, native GeoJSON order - see module
    docstring for why this isn't Google's Encoded Polyline Algorithm
    Format (:mod:`streetworks.na511`'s own case) or plain JSON."""
    if not value:
        return ()
    return tuple((float(lon), float(lat)) for lon, lat in _POLYLINE_PAIR.findall(value))


class TorontoClient:
    """Fetch the City of Toronto's real Road Restrictions/Closures feed.
    No credentials required.

    >>> from streetworks.toronto import TorontoClient
    >>> from streetworks.common import from_toronto
    >>> with TorontoClient() as toronto:  # doctest: +SKIP
    ...     works_list = from_toronto(list(toronto.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def iter_roadworks(self) -> Iterator[JSON]:
        """Every real closure record - a single request, the whole real
        feed (2,274 records at investigation time) in one response. See
        module docstring for why no ``type`` filter is applied."""
        response = self._transport.request(
            "GET", BASE_URL, params={"format": "json"}
        )
        payload = json.loads(_repair_json(response.text))
        yield from payload.get("Closure") or []

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> TorontoClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
