"""Brussels Road Events - Brussels Mobility's own real-time traffic
events feed for the Brussels-Capital Region, credential-free.

Found while surveying Belgium's remaining regions after
:mod:`streetworks.datex2.belgium` (Flanders only, DATEX II v3,
non-permissive licence): Wallonia's own equivalent
("Événements routiers en Wallonie", on transportdata.be) turned out to
be genuinely credential-gated - access requires emailing SPW Mobilité
directly for a username/password, and usage sits under a contractual
arrangement, not an open licence - so it's parked, not built. Brussels'
own dataset ("Brussels Road Events", also catalogued on transportdata.be,
organisation Brussels Mobility) is different: genuinely keyless, and
**Creative Commons Zero (CC0)** - confirmed independently from both
transportdata.be's own resource metadata (``license_type`` states the
real CC0 URI) and Brussels Mobility's own documentation page
(https://data.mobility.brussels/fr/info/events/, also stating "CC0").
A separate, newer OGC API Features service on ``api.mobility.brussels``
does ask for a bearer token for some datasets - but this is not that
service; the real, live, catalogued resource URL for this dataset
resolves (via a real multi-hop redirect chain -
``data-mobility.brussels`` -> ``data.mobility.brussels`` ->
``api-mobility.irisnetlab.be``) to a plain unauthenticated JSON
endpoint, confirmed live.

**Confirmed live 2026-08-23**: a single ``GET`` on the catalogued URL
(``?events=all`` - omitting it returns zero features, confirmed) returns
a real GeoJSON ``FeatureCollection``, 287 real features. Every one
observed was ``datex_codes="RWK"``/``type_fr="Travaux "`` (French:
"works") - the dataset's own description also names incidents and
traffic jams as in scope, but none were live in this particular pull,
stated honestly rather than assumed proven against a mixed sample.
``iter_roadworks()`` filters on ``datex_codes == "RWK"`` regardless, so
it stays correct if/when other event types do appear.

**Genuinely bilingual (French/Dutch), like Flanders' own DATEX feed** -
every text field is duplicated as ``_fr``/``_nl`` pairs
(``type_fr``/``type_nl``, ``location_fr``/``location_nl``, etc.). French
is read as the canonical text field (matching this SDK's own choice for
Monaghan/Basque Country's bilingual fields), both kept on ``.raw``.

**A real source-encoding quirk, confirmed live, not a JSON artifact**:
some real French text embeds literal HTML entities inside otherwise
plain text, e.g. ``"Bande d&apos;arrêt d&apos;urgence obstruée"`` - the
source itself writes ``&apos;`` as four literal characters, not an
apostrophe. :mod:`streetworks.common.from_brussels` unescapes these
before use.

**Geometry is real ``Point`` GeoJSON, stated CRS is CRS84**
(``urn:ogc:def:crs:OGC:1.3:CRS84``) - WGS84 with the same lon/lat axis
order every other GeoJSON feed in this SDK already uses, so coordinates
are read the standard way, no reprojection needed.

**``road_type_fr`` distinguishes ``Street`` (285/287) from ``Ring``
(2/287)** - Brussels' own orbital motorway (R0) alongside ordinary
streets, genuinely comprehensive within the region, not motorway-only.

**No formal identity/grouping field beyond the GeoJSON feature ``id``**
(e.g. ``"events.095C592874E6DECE108EC92CAF2EEA33"``) - one ``Works`` per
feature, the same discipline as every other unstructured municipal/
operator feed in this SDK.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "ROADWORKS_CODE", "BrusselsClient"]

JSON = dict[str, Any]

#: The catalogued resource URL on transportdata.be - real multi-hop
#: redirect chain to a plain JSON endpoint, confirmed live. See module
#: docstring.
BASE_URL = "http://data-mobility.brussels/mobiris/events/?events=all"

#: The one real datex_codes value seen live, confirmed roadworks by its
#: own French label ("Travaux" = "works") - see module docstring.
ROADWORKS_CODE = "RWK"


class BrusselsClient:
    """Fetch Brussels Mobility's real-time Road Events feed. No
    credentials required.

    >>> from streetworks.brussels import BrusselsClient
    >>> from streetworks.common import from_brussels
    >>> with BrusselsClient() as client:  # doctest: +SKIP
    ...     works_list = from_brussels(list(client.iter_roadworks()))
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
        """Every real event feature, unfiltered - roadworks, plus
        whatever else the source's own scope covers (incidents, traffic
        jams), if any are live at pull time. See module docstring."""
        response = self._transport.request("GET", self.base_url)
        payload = response.json()
        yield from payload.get("features") or []

    def iter_roadworks(self) -> Iterator[JSON]:
        """Real features filtered to ``datex_codes == "RWK"`` (works) -
        see module docstring."""
        for feature in self.iter_events():
            if feature.get("properties", {}).get("datex_codes") == ROADWORKS_CODE:
                yield feature

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BrusselsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
