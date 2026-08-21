"""Vancouver "Road Ahead" roadworks - the City of Vancouver's own real,
live, keyless OpenDataSoft Explore API v2.1 deployment, found while
surveying Canadian municipal portals beyond the provincial/territorial
911 platform (see :mod:`streetworks.na511`). The same platform
:mod:`streetworks.paris` and :mod:`streetworks.opendatasoft.france_departements`
already consume - :class:`~streetworks.opendatasoft.OpenDataSoftClient`
is reused directly here, no new fetch/pagination code needed.

**Three real, distinct datasets, not one - confirmed live 2026-08-21:**
``road-ahead-current-road-closures`` (27 real records), ``road-ahead-
projects-under-construction`` (80) and ``road-ahead-upcoming-projects``
(228). None of the three states its own tier as a per-record field - the
tier is real and stated at the *dataset* level (each is its own
Vancouver-published resource, not a status column), so
:func:`streetworks.common.from_vancouver` takes ``status`` as an explicit
caller-supplied label per call, the same design
:func:`~streetworks.common.from_wzdx` already uses for ``territory``/
``administrative_area`` (one client, several distinct real resources,
nothing derivable from the records alone).

**Real field list** (confirmed live via all three datasets):
``project``/``location`` (confirmed live to always be identical -
0 real differences found across every record sampled - only ``location``
is used, ``project`` is redundant), ``street`` (real but **always
null** - 0/100+ real records sampled across all three datasets carry a
value, confirmed, not assumed sparse), ``comp_date`` (a real completion
date, never null - the *only* date field this source states; there is no
start-date field at all, a genuine, confirmed gap, not an oversight),
``url_link``, ``geom`` (a GeoJSON ``Feature`` wrapper; real geometry
types seen live: ``LineString``, ``MultiLineString``, and
``GeometryCollection`` - the last mixing ``LineString``s and real
``Polygon``s in one record, too structurally varied to decompose
generically), ``geo_point_2d`` (a plain ``{"lon":..., "lat":...}`` dict -
confirmed live to be populated on every real record checked, unlike
``geom``'s own varying shape, so this is the one reliable representative
point).

**Licence: Open Government Licence - Vancouver**, confirmed live via the
dataset's own Explore API metadata (``license`` field).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..opendatasoft.client import OpenDataSoftClient

__all__ = [
    "BASE_URL",
    "CURRENT_CLOSURES_DATASET",
    "UNDER_CONSTRUCTION_DATASET",
    "UPCOMING_DATASET",
    "VancouverClient",
]

JSON = dict[str, Any]

#: Vancouver's own real OpenDataSoft deployment - confirmed live, no key
#: required. See module docstring.
BASE_URL = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets"

CURRENT_CLOSURES_DATASET = "road-ahead-current-road-closures"
UNDER_CONSTRUCTION_DATASET = "road-ahead-projects-under-construction"
UPCOMING_DATASET = "road-ahead-upcoming-projects"


class VancouverClient:
    """Fetch Vancouver's real "Road Ahead" roadworks datasets. No
    credentials required.

    >>> from streetworks.vancouver import VancouverClient
    >>> from streetworks.common import from_vancouver
    >>> with VancouverClient() as vancouver:  # doctest: +SKIP
    ...     works_list = from_vancouver(
    ...         list(vancouver.iter_current_closures()), status="Current closure"
    ...     )
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ods = OpenDataSoftClient(client=client)

    def _records_url(self, dataset: str) -> str:
        return f"{BASE_URL}/{dataset}/records"

    def iter_current_closures(self) -> Iterator[JSON]:
        """Every real record from ``road-ahead-current-road-closures``."""
        yield from self._ods.iter_records(self._records_url(CURRENT_CLOSURES_DATASET))

    def iter_under_construction(self) -> Iterator[JSON]:
        """Every real record from ``road-ahead-projects-under-construction``."""
        yield from self._ods.iter_records(self._records_url(UNDER_CONSTRUCTION_DATASET))

    def iter_upcoming(self) -> Iterator[JSON]:
        """Every real record from ``road-ahead-upcoming-projects``."""
        yield from self._ods.iter_records(self._records_url(UPCOMING_DATASET))

    def close(self) -> None:
        self._ods.close()

    def __enter__(self) -> VancouverClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
