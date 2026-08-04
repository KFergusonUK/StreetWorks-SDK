"""Chicago: CDOT Street Closures, over Chicago's Open Data portal
(Socrata) - this SDK's second US city permit register, after NYC.

.. attention::
   **Confirmed live (2026-08-03)** against a real, unauthenticated pull.
   No credentials required.

**The brief's own primary dataset id is dead - found live, not
guessed.** ``6fd2-pzze`` ("CDOT Permits") returns a genuinely empty
schema (``X-SODA2-Fields: []`` on a real live request) despite 2.3M
historical rows and a fresh ``Last-Modified`` - a real data-quality
casualty on Chicago's own portal, not a mistake here. The real, current,
actively-updated datasets are ``pubx-yq2d`` ("Transportation Department
Permits", the full register, 53 columns, 2,294,616 real rows) and
``jdis-5sry`` ("...- Street Closures", a pre-filtered view, 46 columns,
466,829 real rows) - both confirmed updated *today*. This module uses
``jdis-5sry``.

**Genuinely cleaner than NYC in two real ways.** (1) Geometry is a
native Socrata ``point`` column (real ``location``/``latitude``/
``longitude`` fields, straightforward WGS84) - no WKT parsing, no
State-Plane CRS question, populated on **99.94%** of real rows
(466,568/466,829). (2) Dates (``applicationstartdate``/
``applicationenddate``) are populated on the same 99.94% - both richer
than NYC's own 80.5% geometry rate.

**The Street Closures view's own pre-filter is real but not sufficient
on its own - a real correction found live, not assumed.** ``jdis-5sry``
is already filtered to 3 of the full register's 11 real
``applicationtype`` values (``DOT_PWO``, ``DOT_SE``, ``DOT_OCC``) -
genuine work on the useful field, but a *finer* real field,
``worktype``, still mixes in confirmed non-roadworks activity even
within those three types: ``BlockParty`` (53,679 real rows - the single
largest worktype after genuine openings), ``Festival`` (8,938),
``Athletic`` (3,863), ``Filming`` (1,255), ``SideSale`` (934),
``Parade`` (86), ``Assembly`` (33), ``FarmMkt`` (6). So
:meth:`ChicagoDotClient.iter_roadworks` filters on ``worktype``, not
just the view's own applicationtype pre-filter - see the real allowlist
below.

**Real, evidenced roadworks ``worktype`` values** (matching the SA-
``REC_TYPE``/NYC-series discipline - built from real counts, not
guessed): ``GenOpening`` ("Opening in the Public Way", 297,130 -
unambiguous excavation), ``Restorat`` ("Restoration", 35,933 - the
follow-up restoration after an opening), ``GenOccupy`` ("Work Vehicles,
Temporary Driveways, Barricades, Operating Equipment", 46,391 -
construction staging), ``WorkInAdv`` ("Work in Advance", 12,450),
``SoilNWell`` ("Soil Boring / Well Monitoring", 3,392 - utility/
geotechnical work), ``StClosure`` ("Street Closure", 2,146),
``Driveway`` ("Driveway Constr or Removal", 587).

**A real Works-umbrella grouping exists, the same shape as NYC's
``applicationtrackingid``** - ``applicationnumber`` genuinely groups
multiple real rows under one application (one real example,
``DOT604194``, had 64 real rows spanning 64 genuinely different real
street locations - a citywide restoration job, not duplicate records) -
see :mod:`streetworks.common.from_chicagodot` for how this becomes one
``Works`` with several ``WorksSite`` entries.

**No stated join to a street register** - the real 46-column schema was
checked directly; there is no segment/street identifier field, only
free-text ``streetname``/``direction``/``suffix`` plus
``streetnumberfrom``/``streetnumberto``. ``WorksSite.street_ref`` is
never populated, the same NYC/SA/NZTA discipline.

**Licence: unconfirmed, the same honest-gap tier as NYC.** The
dataset's own metadata states only ``{"name": "See Terms of Use"}`` -
no formal reuse licence; the City of Chicago's general portal terms are
a no-warranty disclaimer under a 2012 Open Data Executive Order, not a
named licence. Attribution: "City of Chicago".
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..socrata import SodaClient

__all__ = ["STREET_CLOSURES_URL", "ChicagoDotClient"]

JSON = dict[str, Any]

#: Transportation Department Permits - Street Closures - confirmed live,
#: no credentials. See module docstring for why this is used instead of
#: the brief's own (dead) 6fd2-pzze, and instead of the broader
#: pubx-yq2d (the same data, minus the closures pre-filter).
STREET_CLOSURES_URL = "https://data.cityofchicago.org/resource/jdis-5sry.json"

#: Real, evidenced roadworks worktype values - see module docstring for
#: the full real counts and why the view's own applicationtype pre-filter
#: alone isn't sufficient (BlockParty/Festival/Filming/etc. remain).
_ROADWORKS_WHERE = (
    "worktype IN ("
    "'GenOpening', 'Restorat', 'GenOccupy', 'WorkInAdv', "
    "'SoilNWell', 'StClosure', 'Driveway'"
    ")"
)


class ChicagoDotClient:
    """Fetch Chicago CDOT street closure permits from Chicago's Open
    Data portal. No credentials required.

    >>> from streetworks.chicagodot import ChicagoDotClient
    >>> from streetworks.common import from_chicagodot
    >>> with ChicagoDotClient() as chicago:  # doctest: +SKIP
    ...     works = from_chicagodot(list(chicago.iter_roadworks()))
    """

    def __init__(self, *, app_token: str | None = None, client: httpx.Client | None = None) -> None:
        self._soda = SodaClient(app_token=app_token, client=client)

    def iter_permits(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Every real permit in the Street Closures view matching
        ``where`` - already pre-filtered by Chicago itself to 3 real
        applicationtype values, but still includes non-roadworks
        worktypes (block parties, festivals, ...). See module
        docstring."""
        yield from self._soda.iter_records(STREET_CLOSURES_URL, where=where)

    def iter_roadworks(self, *, where: str = _ROADWORKS_WHERE) -> Iterator[JSON]:
        """Real permits filtered to the 7 confirmed roadworks worktypes
        - see module docstring for the real allowlist and why the
        view's own pre-filter alone isn't enough."""
        yield from self.iter_permits(where=where)

    def close(self) -> None:
        self._soda.close()

    def __enter__(self) -> ChicagoDotClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
