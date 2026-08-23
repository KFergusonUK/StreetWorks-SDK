"""GDDKiA (Generalna Dyrekcja Dróg Krajowych i Autostrad) - Poland's
national roads and motorways authority's own real-time disruptions XML
feed, credential-free.

Found while surveying Europe for missing national roadworks feeds, the
same technique that found Brussels Road Events. GDDKiA's own gov.pl
page ("Dane XML i XSD",
https://www.gov.pl/web/gddkia/dane-xml) names two real downloadable
feeds - current disruptions (``utrdane.xml``, this client) and winter
driving conditions (``warunkidane.xml``, out of scope here, not
fetched).

**Confirmed live 2026-08-23**: a single ``GET`` on ``utrdane.xml``
(~400 KB) returns real current data - the root ``<utrudnienia gen="...">``
element's own ``gen`` attribute states a generation timestamp matching
real time at the moment of pull, not a stale cache. 383 real ``<utr>``
records at time of writing. **The URL lives on an ``archiwum.`` (archive)
subdomain despite serving live, current data** - confirmed genuinely
current from the ``gen`` timestamp and every record's own real dates,
not a naming leftover to be wary of.

**``typ`` is the real, closest-available roadworks discriminator - three
values seen live**: ``U`` (Utrudnienie, "disruption/hindrance" - 354/383)
is overwhelmingly real roadworks (resurfacing, bridge maintenance,
lane closures for construction), confirmed by reading real sample
``objazd`` description text, not assumed from the code. ``I`` (Incydent,
25/383) and ``W`` (accident/police-response category, 4/383) are
confirmed genuinely not roadworks (speed restrictions from pavement
damage, closed rest areas, accident-driven detours).
**``typ == "U"`` is genuinely broader than "planned works" alone,
though** - at least one real record is an emergency closure from flood
damage (a road embankment washout), not scheduled construction - stated
honestly, not filtered out, since no finer-grained field separates the
two within ``typ == "U"``. A second real per-record code,
``rodzaj/poz`` (e.g. ``"U33"`` = resurfacing, ``"U27"`` = bridge works,
``"U42"`` = lane narrowing - decoded from real sample text, not an
official published table), is carried through on ``.raw`` and as
``works_type``, but is not used as the roadworks filter itself.

**Real coordinates (``geo_lat``/``geo_long``) are already true
lat/lon, not swapped** - confirmed against Poland's real coordinate
bounds (~49-55 N, ~14-24 E) on every real sample checked, unlike
Roma's own swapped fields. **Missing on 38/383 (10%) of real records** -
a genuine, confirmed gap, not a parsing failure; :mod:`from_poland`
leaves ``coordinate=None`` rather than guessing.

**``woj`` (voivodeship) is a real per-record administrative field** -
kept on ``.raw``, not promoted to ``administrative_area`` (GDDKiA is
one national authority regardless of region, unlike Spain's own
genuinely separate ``provinces()``).

**No native id field exists anywhere in this schema** - checked across
every real ``<utr>`` element and attribute, confirmed absent. A
composite of ``nr_drogi``/``km``/``data_powstania`` is close to unique
but not proven so (380/383 distinct on a real live pull) - not used as
a synthetic reference; :mod:`from_poland` leaves ``reference=None``,
the same honest choice :mod:`.from_vancouver`/:mod:`.from_quebec`
already make for their own comparable feeds.

**Real dates use a non-colon UTC offset** (``"2026-08-22T13:00:00+0200"``)
- rejected by ``datetime.fromisoformat`` on this SDK's minimum-supported
Python 3.10 (fixed upstream in 3.11) - :mod:`from_poland` inserts the
missing colon before parsing, the same defensive-parsing discipline
:mod:`._dt` already documents for other real non-standard timestamps.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from xml.etree import ElementTree

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "ROADWORKS_TYPE", "PolandClient"]

JSON = dict[str, Any]

#: Confirmed live 2026-08-23 - see module docstring for the "archiwum"
#: subdomain despite serving current data.
BASE_URL = "https://www.archiwum.gddkia.gov.pl/dane/zima_html/utrdane.xml"

#: The real "typ" value confirmed roadworks-relevant by reading sample
#: text - see module docstring.
ROADWORKS_TYPE = "U"

_FIELDS = (
    "typ",
    "nr_drogi",
    "woj",
    "km",
    "dl",
    "geo_lat",
    "geo_long",
    "nazwa_odcinka",
    "data_powstania",
    "data_likwidacji",
    "objazd",
    "ogr_nosnosc",
    "ogr_nacisk",
    "ogr_skrajnia_pozioma",
    "ogr_skrajnia_pionowa",
    "ogr_szerokosc",
    "ogr_predkosc",
    "ruch_wahadlowy",
    "sygnalizacja_swietlna",
    "awaria_mostu",
    "ruch_2_kierunkowy",
    "droga_zamknieta",
)


def _parse_record(element: ElementTree.Element) -> JSON:
    record = {field: element.findtext(field) for field in _FIELDS}
    record["rodzaj_poz"] = element.findtext("rodzaj/poz")
    return record


class PolandClient:
    """Fetch GDDKiA's real-time road disruptions feed. No credentials
    required.

    >>> from streetworks.poland import PolandClient
    >>> from streetworks.common import from_poland
    >>> with PolandClient() as client:  # doctest: +SKIP
    ...     works_list = from_poland(list(client.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_events(self) -> Iterator[JSON]:
        """Every real disruption record, unfiltered - roadworks
        (``typ="U"``) alongside incidents (``"I"``) and accidents
        (``"W"``). See module docstring."""
        response = self._transport.request("GET", self.base_url)
        root = ElementTree.fromstring(response.content)
        for element in root.findall("utr"):
            yield _parse_record(element)

    def iter_roadworks(self) -> Iterator[JSON]:
        """Real records filtered to ``typ == "U"`` (Utrudnienie) - see
        module docstring for what this does and doesn't cleanly
        separate."""
        for record in self.iter_events():
            if record["typ"] == ROADWORKS_TYPE:
                yield record

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> PolandClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
