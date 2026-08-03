"""New York City: NYC DOT Street Construction Permits, over NYC Open
Data (Socrata) - the local follow-on the WZDx feed-registry harvest
deliberately scoped out. NY *State* (511NY, see :mod:`streetworks.wzdx`)
covers state highways; NYC's five boroughs are a separate authority
(NYC DOT) publishing a separate shape entirely - not WZDx at all.

.. attention::
   **Confirmed live (2026-08-02)** against a real, unauthenticated pull.
   No credentials required.

**This is a genuine permit register, not a traveller-info feed - the US
cousin of Street Manager.** `Street Construction Permits (2022-Present)
<https://data.cityofnewyork.us/Transportation/Street-Construction-Permits-2022-Present/tqtj-sjs8>`_
(Socrata id ``tqtj-sjs8``, real total **3,798,494** rows) records DOT's
own issued permits (utilities/contractors/agencies/homeowners), not
observed road conditions - the same "authorisation, not event" shape
Street Manager's permits have, and only this SDK's second
``source_grade=register`` source (after England). The 2013-2021 archive
(``c9sj-fmsg``) is a separate, historical dataset - out of scope here.

**No stated join to a street register - settles the brief's own hoped-
for question, honestly, not the way it hoped.** The full real 39-column
schema was checked directly: there is no LION ``segmentid`` (or any
other street-register identifier) anywhere on this dataset. Location is
only ever free text - ``onstreetname``/``fromstreetname``/
``tostreetname``/``boroughname`` - so :mod:`streetworks.common.from_nycdot`
never populates ``WorksSite.street_ref``, the same SA-``ROAD_NO``/NZTA
discipline this SDK holds everywhere: a name is not a join. A genuine
NYC LION gazetteer strand remains a real, separate, not-yet-built
follow-on, but it would join to nothing here even once built.

**Real geometry exists anyway - better than the join would have given
for plotting, even without one.** A real ``wkt`` column (plus a
redundant WKB-hex-encoded ``locationgeometry`` twin, not otherwise used)
is populated on **3,057,545/3,798,494 (80.5%)** of all real rows -
``LINESTRING`` (the majority), ``POINT``, and a real, confirmed-live
``MULTIPOINT`` shape (two endpoint markers of one work extent - added
support for this to :mod:`streetworks.common._wkt`, previously
unhandled). **Coordinates are NAD83 / New York Long Island (ftUS),
EPSG:2263** - inferred, not an explicitly stated SRID anywhere in the
dataset's own metadata, but confirmed by real coordinate value ranges
matching that projection's known NYC-area bounds (the near-universal
convention for NYC city-agency GIS data) - never silently reprojected to
WGS84, the same "label honestly, don't guess a formula" discipline
Tasmania's real GDA94/MGA zone 55 geometry already established for this
SDK. The remaining 19.5% of rows carry only the free-text cross-street
fields.

**Permit-type filtering needed real evidence, not the coarser
``permitseriesshortdesc`` alone.** Real series values: ``STREET OPENING
PERMIT`` (1,717,842, unambiguous carriageway work) and ``DOT IN-HOUSE
PAVING AND MILLING`` (118,656, DOT's own paving) are both clearly
roadworks - :meth:`NycDotClient.iter_roadworks` filters to these two.
``BUILDING OPERATION PERMIT`` (1,206,251, the second-largest series) is
genuinely mixed at the finer ``permittypedesc`` level: real sub-types
include street-occupying work (``OCCUPANCY OF ROADWAY AS STIPULATED``,
160,969; ``PLACE MATERIAL ON STREET``, 99,610) alongside clearly
non-roadway ones (``OCCUPANCY OF SIDEWALK AS STIPULATED``,
``PLACE/REMOVE BIKE SHARE STATION ON ST``) - no confident allowlist
could be built from the series field alone, so it's excluded from the
default filter rather than guessed at (the SA-``REC_TYPE`` discipline);
:meth:`iter_permits` (unfiltered) lets a caller build their own
``permittypedesc``-level filter. ``SIDEWALK CONSTRUCTION PERMIT`` and
``CANOPY PERMIT`` are confirmed non-carriageway, excluded per the source
brief's own scope.

**A real Works-umbrella grouping exists, matching Street Manager's own
shape** - ``applicationtrackingid`` genuinely groups multiple permits
(one real application had 226 real permits under it, a large paving job
spanning many street segments) - see
:mod:`streetworks.common.from_nycdot` for how this becomes one
``Works`` with several ``WorksSite`` entries, never one ``Works`` per
permit.

**Licence: unconfirmed, the same honest-gap tier as NDW/Digitraffic.**
NYC Open Data states no formal reuse licence (``license: None`` on the
dataset's own metadata) - only NYC.gov's general Terms of Use and a
no-warranty disclaimer, plus a stated attribution: "Department of
Transportation (DOT)".
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..socrata import SodaClient

__all__ = ["PERMITS_URL", "NycDotClient"]

JSON = dict[str, Any]

#: Street Construction Permits (2022-Present) - confirmed live, no
#: credentials. See module docstring. The 2013-2021 archive (c9sj-fmsg)
#: is a separate, historical, out-of-scope dataset.
PERMITS_URL = "https://data.cityofnewyork.us/resource/tqtj-sjs8.json"

#: Real, evidenced roadworks series - see module docstring for why
#: BUILDING OPERATION PERMIT (genuinely mixed at the finer
#: permittypedesc level) is deliberately excluded rather than guessed.
_ROADWORKS_WHERE = (
    "permitseriesshortdesc IN ('STREET OPENING PERMIT', 'DOT IN-HOUSE PAVING AND MILLING')"
)


class NycDotClient:
    """Fetch NYC DOT street construction permits from NYC Open Data. No
    credentials required.

    >>> from streetworks.nycdot import NycDotClient
    >>> from streetworks.common import from_nycdot
    >>> with NycDotClient() as nycdot:  # doctest: +SKIP
    ...     works = from_nycdot(list(nycdot.iter_roadworks()))
    """

    def __init__(self, *, app_token: str | None = None, client: httpx.Client | None = None) -> None:
        self._soda = SodaClient(app_token=app_token, client=client)

    def iter_permits(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Every real permit matching ``where`` - the raw, unfiltered
        register (150+ real permit types, not just roadworks). See
        module docstring for the real permit-series values."""
        yield from self._soda.iter_records(PERMITS_URL, where=where)

    def iter_roadworks(self, *, where: str = _ROADWORKS_WHERE) -> Iterator[JSON]:
        """Real permits filtered to the two confirmed roadworks series
        (``STREET OPENING PERMIT``, ``DOT IN-HOUSE PAVING AND MILLING``)
        - see module docstring for why ``BUILDING OPERATION PERMIT``
        isn't included by default."""
        yield from self.iter_permits(where=where)

    def close(self) -> None:
        self._soda.close()

    def __enter__(self) -> NycDotClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
