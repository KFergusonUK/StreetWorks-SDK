"""Germany (Brandenburg) - the "WFS BB-BE Gazetteer", a joint
Brandenburg/Berlin gazetteer WFS run by LGB (Landesvermessung und
Geobasisinformation Brandenburg). This SDK's second German state-level
streets/gazetteer provider (after Hamburg's own GAGES), continuing the
"state fan-out" fallback path Germany's national streets investigation
left open - see `docs/germany-streets-investigation.md`.

**Real, live, keyless WFS - found via Brandenburg's own geoportal
metadata record, not guessed.** `geoportal.brandenburg.de`'s own
catalogue entry for "Deutschland-Online-Gazetteer Brandenburg mit
Berlin (WFS)" resolves to the real service endpoint,
`isk.geobasis-bb.de/ows/gazetteer_wfs` - confirmed live
(`GetCapabilities` returns a real 73 KB response, service title "WFS
BB-BE Gazetteer"). The service's own abstract states it directly: data
for house coordinates, streets and postal-code areas cover **both**
Brandenburg and Berlin (Berlin's own contribution sourced from
Geoportal Berlin's Amtliche Hauskoordinaten) - confirmed live in a real
500-record sample, 8/500 rows genuinely carry `land=11` (Berlin's real
ISO 3166-2:DE code), the rest `land=12` (Brandenburg's own code). This
build is scoped and documented as Brandenburg's own provider - the
real Berlin content is a genuine bonus, not claimed as exhaustive
Berlin coverage (unlike this SDK's own Hamburg build, which is a
complete state gazetteer).

**52,902 real street records, confirmed live via `resultType=hits` -
much larger than Hamburg's 9,639, consistent with Brandenburg's far
greater land area.**

**A real, confirmed GML-only WFS - no JSON output format exists,
checked live rather than assumed from the shared OGC client's own
JSON-first default.** `GetCapabilities` lists only GML output formats
for this feature type; a real `outputFormat=application/json` request
was tried and rejected with a genuine `400`
(`"This WFS is not configured to handle the output/input format
'application/json'"`). This module therefore doesn't use the shared
:class:`~streetworks.ogc.OGCFeaturesClient` (JSON-first) and instead
parses the real GML/XML response directly via the standard library's
own `xml.etree.ElementTree` - no `lxml`, matching this SDK's
stdlib-plus-httpx convention.

**Real, comprehensive per-record fields - richer than Hamburg's own
simpler schema.** `strassenname` (the real name), `ortsnamePost`/
`zusatzOrtsname` (the real postal town name and a real qualifier, e.g.
`"Brandenburg"`/`"an der Havel"` - together reconstructing the real
municipality name "Brandenburg an der Havel", confirmed against this
same record's own `gemeindename_normalisiert`), `postleitzahl` (postal
code), `postOrtsteil`/`ortsteilname` (real district names, not just
codes - unlike Hamburg's own unresolved Ortsteil code), `land` (the
real German state code), `strassenschluessel` (a real structured street
key), and a real `geographicExtent` **Polygon** (the street's areal
extent, not a point/line) - preserved unmodified as raw GML text, never
forced into `Coordinate.points`/`.parts`, the same discipline this SDK
already applies to Marousi's (Greece) own polygon-only schema.

**No credentials.** Licence: **Datenlizenz Deutschland - Namensnennung -
2.0**, confirmed live directly from this WFS's own `GetCapabilities`
`AccessConstraints` element, with a real, stated attribution string:
*"© GeoBasis-DE/LGB, dl-de/by-2-0, (Daten geändert)"*.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "TYPE_NAME", "BrandenburgStreetsClient"]

JSON = dict[str, Any]

#: The real, live, keyless WFS route - see module docstring.
BASE_URL = "https://isk.geobasis-bb.de/ows/gazetteer_wfs"

#: The real streets feature type - see module docstring.
TYPE_NAME = "app:Strassen"

_APP_NS = "http://www.deegree.org/app"
_GML_NS = "http://www.opengis.net/gml/3.2"
_WFS_NS = "http://www.opengis.net/wfs/2.0"

_DEFAULT_PAGE_SIZE = 5000

# Keeps the real "gml:" prefix on re-serialised geographicExtent GML
# (see below) instead of ElementTree's own auto-generated "ns0:" -
# faithful to the source, not a functional requirement (the namespace
# URI is identical either way).
ET.register_namespace("gml", _GML_NS)


def _parse_feature_collection(xml_bytes: bytes) -> list[JSON]:
    root = ET.fromstring(xml_bytes)  # noqa: S314 - a trusted government WFS endpoint
    records: list[JSON] = []
    for member in root.findall(f"{{{_WFS_NS}}}member"):
        street = member.find(f"{{{_APP_NS}}}Strassen")
        if street is None:
            continue
        record: JSON = {"gml_id": street.get(f"{{{_GML_NS}}}id")}
        for child in street:
            local_name = child.tag.split("}", 1)[-1]
            if local_name == "geographicExtent":
                record["geographicExtent_gml"] = "".join(
                    ET.tostring(grandchild, encoding="unicode") for grandchild in child
                )
            else:
                record[local_name] = child.text
        records.append(record)
    return records


class BrandenburgStreetsClient:
    """Fetch Brandenburg's real state street gazetteer (WFS BB-BE
    Gazetteer). No credentials required.

    >>> from streetworks.brandenburg import BrandenburgStreetsClient
    >>> from streetworks.common import from_brandenburg_street
    >>> with BrandenburgStreetsClient() as bb:  # doctest: +SKIP
    ...     streets = [from_brandenburg_street(r) for r in bb.iter_streets()]
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        page_size: int = _DEFAULT_PAGE_SIZE,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )
        self._page_size = page_size

    def iter_streets(self) -> Iterator[JSON]:
        """Yield every real Brandenburg (and real, non-exhaustive
        Berlin) street, paging via WFS 2.0's own `startIndex`/`count`
        until a page comes back short of the requested size. See module
        docstring."""
        start_index = 0
        while True:
            response = self._transport.request(
                "GET",
                BASE_URL,
                params={
                    "service": "WFS",
                    "request": "GetFeature",
                    "version": "2.0.0",
                    "typeNames": TYPE_NAME,
                    "count": str(self._page_size),
                    "startIndex": str(start_index),
                },
            )
            records = _parse_feature_collection(response.content)
            yield from records
            if len(records) < self._page_size:
                return
            start_index += len(records)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BrandenburgStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
