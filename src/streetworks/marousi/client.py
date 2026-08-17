"""Δήμος Αμαρουσίου (Marousi, Greece) - a real municipal street-name
register, over the municipality's own GeoServer WFS. This SDK's first
Greek gazetteer coverage - a pilot for a real, genuine per-municipality
fan-out, not a national build (Greece's roadworks side is a documented,
unavailable scaffold - see `streetworks.greece`'s own module docstring
- and its national geospatial infrastructure is either genuinely
unreachable or blocked, see below).

**Why a municipality, not a country - investigated live, not
assumed.** Greece's official INSPIRE geoportal (`geodata.gov.gr`) times
out completely on every real connection attempt (confirmed live,
several independent tries) - the same real connectivity failure this
SDK's own `streetworks.greece` module already documented for
`nap.gov.gr`, suggesting a broader real characteristic of this
country's government geospatial hosting, not a one-off. The national
cadastre (`ktimatologio.gr`) returns a real `403`. What's real and
reachable instead is Greece's national open-data catalogue
(`data.gov.gr`, a real CKAN portal) - which does list street data, but
comprehensively fragmented: 580 real datasets matching "streets"/"road
network" search terms, each published independently by one of Greece's
many Δήμοι (municipalities), in inconsistent formats (static ZIP
shapefiles for most, a real minority as live WFS). Marousi (a real
Athens suburb) was picked as the pilot because it's one of the few with
a genuinely live, queryable WFS rather than a static download.

**Real, live, keyless WFS - confirmed live, not assumed from the
catalogue listing alone.** `gis.maroussi.gr/geoserver/wfs` - 721 real
street-extent polygon features, **100% carrying a real, non-blank
name** (`onoma_is`) - confirmed against the complete real dataset, not
a sample. Real, recognisable Greek street names confirmed live:
`"ΑΓΑΜΕΜΝΟΝΟΣ"` (Agamemnon), `"25ΗΣ ΜΑΡΤΙΟΥ"` (25th of March - Greek
Independence Day, a common Greek street name).

**A real GeoJSON output-format quirk, the same one Gibraltar's and
Iceland's own GeoServer deployments have.** This server rejects
`application/geo+json` outright (a real `400`) - only plain
`application/json` works, passed explicitly rather than relying on
`streetworks.ogc.OGCFeaturesClient`'s own documented default.

**CRS: native `EPSG:2100` (GGRS87 / Greek Grid), real WGS84 only when
explicitly requested - confirmed live.** A plain request with no
`srsName` stays in the native Greek grid; `srsName=EPSG:4326` genuinely
reprojects (confirmed live, real Marousi coordinates,
`23.78, 38.02`-shaped).

**Geometry is real `MultiPolygon`, always single-part on this real
dataset (confirmed against all 721 real features) - a real street
extent, not a centreline.** No stated point/line field exists anywhere
on this minimal three-field schema (`id`/`geom`/`onoma_is`), so per the
same discipline `from_guernsey_street` already established for its own
real polygon-only layer, this converter never forces the ring into
`Coordinate.points` (documented for line vertices, not polygon rings) -
every real `Street` this module produces carries `GeometryGrade.ABSENT`
on the canonical geometry field, with the real polygon preserved
unmodified in `.raw`.

**Licence: genuinely unstated, not found either way - checked, not
assumed present.** Every one of the 580 real municipal datasets on
`data.gov.gr` checked (Marousi included) shows `license_id: None` -
"License not specified," a real, consistent gap across the whole
catalogue, not an oversight on this one dataset. Built on the project
owner's explicit instruction, the same basis Jersey shipped on -
confirm your own reuse/redistribution rights before redistributing
data pulled through this module further downstream.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..ogc import OGCFeaturesClient

__all__ = ["BASE_URL", "STREETS_TYPE_NAME", "CRS", "MarousiStreetsClient"]

JSON = dict[str, Any]

#: The real Marousi municipal GeoServer deployment. See module docstring.
BASE_URL = "https://gis.maroussi.gr/geoserver/wfs"

#: The real street-name polygon layer - see module docstring.
STREETS_TYPE_NAME = "maroussi:pol_csv_name_odoi"

#: Confirmed live: this layer's native CRS is EPSG:2100 (GGRS87 / Greek
#: Grid); real WGS84 output requires this to be requested explicitly -
#: see module docstring.
CRS = "EPSG:4326"


class MarousiStreetsClient:
    """Fetch Marousi's real street-name register. No credentials
    required.

    >>> from streetworks.marousi import MarousiStreetsClient
    >>> from streetworks.common import from_marousi_street
    >>> with MarousiStreetsClient() as marousi:  # doctest: +SKIP
    ...     streets = [from_marousi_street(f) for f in marousi.iter_streets()]
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def iter_streets(self) -> Iterator[JSON]:
        """Yield every real street feature (GeoJSON ``Feature`` dicts).
        A real 721-feature dataset - small enough that a single page
        (this module requests 2000) covers it, confirmed live."""
        payload = self._ogc.get_wfs_features(
            BASE_URL,
            type_name=STREETS_TYPE_NAME,
            output_format="application/json",
            srs_name=CRS,
            extra_params={"COUNT": "2000"},
        )
        yield from payload.get("features", [])

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> MarousiStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
