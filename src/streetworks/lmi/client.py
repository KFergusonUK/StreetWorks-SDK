"""Landmælingar Íslands (National Land Survey of Iceland) - IS 50V, the
national 1:50,000 base map's real road-network layer. This SDK's first
Icelandic streets/gazetteer coverage, and a real sibling to Iceland's
existing roadworks coverage: both this layer's own real
``gagnaeigandi`` (data-owner) field and IRCA's own roadworks feed point
to the same real agency, Vegagerðin (the Icelandic Road Administration)
- confirmed live, not assumed from the two providers just happening to
both be Icelandic.

**Real, live, keyless WFS - confirmed live by walking the service's own
full `GetCapabilities` (473 real layers), not assumed from the layer
name alone.** `IS_50V:samgongur_linur` ("transport lines") is the real
road-segment layer - 58,266 real features nationally, confirmed via
`resultType=hits`. A separate `INSPIRE:is_tn_ro_lmi_roadlink` layer also
exists on this deployment (Iceland's own INSPIRE Transport Networks
publication) but wasn't the one built here - this native layer carries
real names directly, avoiding the "geometry with no identity" outcome
several other providers' own INSPIRE layers had (Germany's BKG,
Gibraltar's own `TN_RoadTransportNetwork_RoadLink`).

**Real names on 48,959/58,266 (84.0%) of features - confirmed live
against the complete real dataset, not a sample, and not a naive
`IS NOT NULL` check.** A first check using `nafnfitju IS NOT NULL`
alone suggested 99.98% - wrong, and caught before shipping: the real
majority of unnamed rows store a literal single-space string (`" "`),
not a database `NULL`, so that filter alone missed them. The real,
correct 84.0% coverage still checks at both ends of the density
spectrum: `"Gnúpverjavegur"` (a real rural connecting road) and
`"Laugavegur"` (Reykjavík's own main shopping street, 63 real segments)
- this layer covers dense urban streets, not just inter-town routes.
`from_lmi_street` treats both a real blank string and a real `NULL` as
no name, never fabricating one.

**Real field list** (confirmed live): `objectid`, `uuid` (a real,
per-feature unique id), `nafnfitju` (the real name), `vegnr`/`kaflanr`
(a real route number + section number, e.g. `"325"`/`"01"` -
Vegagerðin's own road-numbering scheme, alongside the name, not instead
of it - unlike Monaghan's own numbered-only roads), `vegflokkun`/
`vegflokkun_text_is` (a real classification code plus the source's own
Icelandic-language label, e.g. `"Tengivegur"` - connecting road),
`slitlag`/`slitlag_text_is` (surface type, e.g. `"Malarvegur"` - gravel
road), `einingvegakerfis`/`einingvegakerfis_text_is` (road-system unit
type - real values seen: `"Vegur"` road, `"Göng"` tunnel),
`gagnaeigandi` (data owner - `"Vg"`, Vegagerðin), `dagsuppfaerslu` (a
real last-updated date), `heimild` (real data-source description, e.g.
`"GPS-mæling"` - GPS survey).

**A real GeoJSON output-format quirk, the same one Gibraltar's own
GeoServer has.** This server rejects `application/geo+json` outright
(a real `400`) - only plain `application/json` works, passed explicitly
rather than relying on `streetworks.ogc.OGCFeaturesClient`'s own
documented default. Unlike Gibraltar's own view-backed layer, this one
paginates cleanly with plain `COUNT`/`STARTINDEX` - no `sortBy`
workaround needed, confirmed live (real, distinct `objectid`s at
offsets 0 and 1000).

**CRS: real WGS84 by default, no `srsName` override needed - confirmed
live.** A plain request with no `srsName` at all already returns
`"crs":{"name":"urn:ogc:def:crs:EPSG::4326"}` and real WGS84-shaped
coordinates - this module requests it explicitly anyway, the same
harmless-but-correct choice this SDK makes elsewhere.

**Genuinely multi-part `MultiLineString` geometry on a real minority of
records** (8/2000 in a live sample, ~0.4%) - `Coordinate.parts` is
always used where a real feature has more than one line, the same
discipline `from_gibraltar`/`from_tigerweb` already established, never
a first-line-only shortcut.

**Licence: Creative Commons Attribution 4.0 International, confirmed
live directly from Landmælingar Íslands' own licence page**
(`lmi.is`, in Icelandic): *"Opin gögn Landmælinga Íslands eru gefin út
skv. Creative Commons Attribution 4.0 International License"* - with a
real stated attribution format (name Landmælingar Íslands, the dataset
name, and the date the data were fetched, e.g. *"Inniheldur gögn frá
IS 50V gagnagrunni Landmælinga Íslands frá 12/2020"*).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..exceptions import TruncatedResultError
from ..ogc import OGCFeaturesClient

__all__ = ["BASE_URL", "STREETS_TYPE_NAME", "CRS", "LmiStreetsClient"]

JSON = dict[str, Any]

#: The real Landmælingar Íslands WFS deployment. See module docstring.
BASE_URL = "https://gis.lmi.is/geoserver/wfs"

#: The real, national road-segment layer - see module docstring.
STREETS_TYPE_NAME = "IS_50V:samgongur_linur"

#: Confirmed live: this service's real f=json output is WGS84 by
#: default - see module docstring.
CRS = "EPSG:4326"

_PAGE_SIZE = 5000


class LmiStreetsClient:
    """Fetch Iceland's real national road network. No credentials
    required.

    >>> from streetworks.lmi import LmiStreetsClient
    >>> from streetworks.common import from_lmi_street
    >>> with LmiStreetsClient() as lmi:  # doctest: +SKIP
    ...     streets = [from_lmi_street(f) for f in lmi.iter_streets()]
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def iter_streets(self) -> Iterator[JSON]:
        """Yield every real road-segment feature (GeoJSON ``Feature``
        dicts). Raises :class:`~streetworks.exceptions.TruncatedResultError`
        rather than silently returning a partial result if a page comes
        back short of what the server itself says exists."""
        offset = 0
        while True:
            payload = self._ogc.get_wfs_features(
                BASE_URL,
                type_name=STREETS_TYPE_NAME,
                output_format="application/json",
                srs_name=CRS,
                extra_params={"COUNT": str(_PAGE_SIZE), "STARTINDEX": str(offset)},
            )
            features = payload.get("features", [])
            yield from features

            total = payload.get("numberMatched")
            received_so_far = offset + len(features)
            if not features or len(features) < _PAGE_SIZE:
                if total is not None and received_so_far < total:
                    raise TruncatedResultError(
                        f"{STREETS_TYPE_NAME}: expected {total} real features, "
                        f"only received {received_so_far} - the layer may have "
                        "grown past this module's page size."
                    )
                return
            offset += len(features)

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> LmiStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
