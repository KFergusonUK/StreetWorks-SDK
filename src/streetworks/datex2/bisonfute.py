"""France (Bison Futé / DIRs) roadworks - DATEX II v2, credential-free.

Bison Futé (the French national traffic-info service) publishes road events
for the non-concessionary national road network (the state-run RRN, managed
by the DIRs - Directions Interdépartementales des Routes) as open DATEX II
v2, from the "Tipi" platform - no registration, no API key.

**Confirmed live, 2026-07**: a single ``GET`` on ``content.xml`` (~2.8 MB,
a SOAP-enveloped ``d2LogicalModel``) returns 256 real situations, 170 of
them roadworks (150 ``MaintenanceWorks``, 20 ``ConstructionWorks``). This
is standard DATEX II v2, so it's parsed through the same shared
:func:`~streetworks.datex2.parser.iter_situations_full` /
:func:`~streetworks.datex2.parser.iter_roadworks_full` NDW/Iceland use -
no new parse path. The ``_full`` (non-streaming) variant is used rather
than NDW's streaming one because ~2.8 MB is nowhere near the scale that
exists for (NDW's ~170 MB), so there's no reason to give up ``.raw``
fidelity - populated here the same way as Iceland.

**Location, verified across the whole feed, not one sample**: every single
roadworks record (170/170) carries WGS84 coordinates *alongside* an Alert-C
reference - confirmed live, not assumed. Coordinates are taken for
``Location.points``; Alert-C is preserved (not decoded) in
``alert_c_location``, same as every other DATEX adapter. Many records use a
**TPEG linear location** (a segment's ``from``/``to`` endpoints, each with
their own coordinates) rather than a single point or a ``posList`` -
France's real data is what surfaced two genuine gaps in the *shared* XML
parser (not France-specific bugs, just never exercised before):

1. ``alert_c_location`` used to return the raw numeric location-table code
   (e.g. ``"17855"``) instead of the human-readable name (``"Fos"``) sitting
   right next to it - fixed in
   :func:`~streetworks.datex2.parser._parse_location` (prefers
   ``alertCLocationName``, tried across both the primary and secondary
   point locations if one is an empty placeholder, falling back to the raw
   code only if every name is genuinely absent - 161/170 real records get a
   name, 2/170 genuinely have none anywhere, matching the honest fallback).
2. TPEG linear locations used to keep only whichever endpoint's
   ``pointCoordinates`` happened to appear first in document order (``to``,
   here) and silently drop the other - fixed to capture both ``from`` and
   ``to`` as a real 2-point line (140/170 real records are TPEG-linear; the
   other 30 are plain points).

That 2-point line survives all the way to
:class:`~streetworks.common.Coordinate` too - ``points`` there used to not
exist at all (every converter, not just this one, collapsed line geometry
to a single point); see that class's docstring.

**``administrative_area`` (DIR region)**: confirmed genuinely stated on
170/170 roadworks records via ``source/sourceIdentification`` (e.g.
``"Direction interdépartementale des routes/DIR Sud-Ouest"``) - but this is
a *different*, coarser field from what the shared parser exposes as
``SituationRecord.source_name`` (which reads the sibling ``sourceName``
field, a much finer sub-office like ``"CEI de Rostrenen"`` or
``"District Sud (Foix)"``). ``sourceIdentification`` isn't on the shared
model, so :func:`dir_regions` reads it straight from each record's ``.raw``
XML ``Element`` (populated because this client uses the non-streaming
parser) - the same shape of solution as Digitraffic's ``provinces()``
helper, just sourced from XML instead of JSON.

**Licence and attribution** (confirmed via the official dataset page,
https://www.data.gouv.fr/datasets/evenements-routiers-sur-le-reseau-routier-national-non-concede):
published under the **Licence Ouverte / Open Licence 2.0** (Etalab) - free
reuse, redistribution, and commercial exploitation permitted. Etalab 2.0's
standard attribution requirement is to cite the source and the last-update
date (no single mandated wording, unlike Iceland's IRCA licence) - cite
"Bison Futé / Directions Interdépartementales des Routes (DIR), via
transport.data.gouv.fr" wherever French roadworks data from this module is
displayed or redistributed.

**Scope**: only the non-concessionary national network (the RRN, DIR-run).
The private autoroute concessionaires publish separately and are out of
scope here.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Situation, SituationRecord
from .parser import _local
from .parser import iter_roadworks_full as _iter_roadworks_full
from .parser import iter_situations_full as _iter_situations_full

__all__ = ["BASE_URL", "CONTENT_PATH", "BisonFuteClient", "dir_regions"]

BASE_URL = "https://tipi.bison-fute.gouv.fr"
CONTENT_PATH = "bison-fute-ouvert/publicationsDIR/Evenementiel-DIR/grt/RRN/content.xml"


def _source_identification(record: SituationRecord) -> str | None:
    if record.raw is None:
        return None
    for element in record.raw.iter():
        if _local(element.tag) == "sourceIdentification":
            return (element.text or "").strip() or None
    return None


def dir_regions(situations: list[Situation]) -> dict[str, str]:
    """Map ``situation.id -> DIR region name`` (e.g. ``"Direction
    interdépartementale des routes/DIR Sud-Ouest"``) for every roadworks
    situation that states one - pass the result to
    ``streetworks.common.from_datex2(situation, administrative_area=...)``,
    since a ``Situation`` alone doesn't carry it. See module docstring for
    why this reads ``.raw`` directly rather than ``source_name``."""
    result: dict[str, str] = {}
    for situation in situations:
        if not situation.roadworks:
            continue
        source = _source_identification(situation.roadworks[0])
        if source:
            result[situation.id] = source
    return result


class BisonFuteClient:
    """Fetch French national roadworks (non-concessionary network) from
    Bison Futé. No credentials required.

    >>> from streetworks.datex2.bisonfute import BisonFuteClient, dir_regions
    >>> from streetworks.common import from_datex2
    >>> with BisonFuteClient() as bf:
    ...     situations = list(bf.iter_roadworks())
    >>> regions = dir_regions(situations)
    >>> for situation in situations:
    ...     works = from_datex2(
    ...         situation, territory="France",
    ...         administrative_area=regions.get(situation.id),
    ...     )
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_events(self) -> bytes:
        """``GET content.xml`` - the raw DATEX II XML response body (all
        current road events on the non-concessionary national network)."""
        response = self._transport.request("GET", f"{self.base_url}/{CONTENT_PATH}")
        return response.content

    def iter_situations(self) -> Iterator[Situation]:
        yield from _iter_situations_full(io.BytesIO(self.get_events()))

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record (``MaintenanceWorks``/``ConstructionWorks``)."""
        yield from _iter_roadworks_full(io.BytesIO(self.get_events()))

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BisonFuteClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
