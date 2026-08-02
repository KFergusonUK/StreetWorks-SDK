"""New Zealand: LINZ (Toitū Te Whenua, Land Information New Zealand) - the
gazetteer strand of this SDK's first New Zealand coverage (see also
:mod:`streetworks.nzta` for the works strand). Covers the current **NZ
Addresses** family - **not** the retired ``NZ Roads (Addressing)`` layer
(53382), deprecated March 2026 and retired end of June 2026, confirmed
gone as of this build.

.. attention::
   **Two genuinely different verification levels in one client, kept
   honest rather than blended.** :meth:`LinzClient.iter_addresses`
   (**NZ Addresses**, layer 123113) is **confirmed live** (2026-08-02)
   against a real, unauthenticated pull - a public ArcGIS Online mirror,
   no LINZ Data Service key needed at all. :meth:`LinzClient.iter_roads`/
   :meth:`~LinzClient.iter_road_sections` (**NZ Addresses: Roads**/
   **Road Sections**, layers 123110/123109) have **no such public
   mirror** - they need a real, registered LINZ Data Service (LDS) API
   key, which this build does not have (self-service registration needs a
   real account this session can't create). Built to the confirmed-live
   schema and WFS endpoint pattern (see below), but **never run against an
   authenticated response** - the same Trafikverket-shape scaffold, not a
   SA-style access block.

**NZ Addresses (123113) - the fully verified route, no key.** The layer's
own real metadata states it's also mirrored as a public ArcGIS Online
Feature Service (``LINZ NZ Addresses``, confirmed live ``"access":
"public"``) - so :meth:`iter_addresses` reuses the same
:class:`~streetworks.arcgis.client.ArcGISFeatureClient` every AU ArcGIS
provider does, rather than needing an LDS key at all. Licence **CC BY
4.0**, confirmed live from both the Koordinates layer metadata
(``license.type == "cc-by"``) and the ArcGIS item's own ``licenseInfo``
independently. Real total: **2,421,642** addresses (confirmed via the
layer's own ``feature_count``) - genuinely national scale, unlike
anything else this SDK has queried through ``ArcGISFeatureClient``
directly (TIGERweb's underlying dataset is larger, but always queried by
bounding box, never in full).

**A real, confirmed field-length quirk**: ``is_land`` is a real boolean
concept, but the live layer definition states it as
``esriFieldTypeString`` with **length 2** - so real values are
``"tr"``/``"fa"`` (truncated ``true``/``false``), not the words
themselves or a JSON boolean. Confirmed live across a 500-record sample
(278 ``"tr"``, 222 ``"fa"``, no other values). No canonical gazetteer
field carries this concept, so it stays on ``.raw`` only - see
:mod:`streetworks.common.from_linz`.

**NZ Addresses: Roads (123110) and Road Sections (123109) - schema
confirmed live from LINZ's own public Koordinates metadata API, real
sample rows included, but never queried through the real WFS.** The
Koordinates platform underneath LDS publishes real field lists **and a
real sample of attribute values** (not geometry) for every layer via a
public, keyless metadata endpoint
(``data.linz.govt.nz/services/api/v1.x/layers/{id}/versions/{v}/data/sample/``)
- confirmed live for both layers, giving genuine confidence in the field
shapes below beyond just the documented schema, even though no actual
``GetFeature`` query has ever been run. Real total: Roads **82,221**,
Road Sections **250,409** (both from the layers' own ``feature_count``).
Both **CC BY 4.0**, confirmed the same way as Addresses.

**The real WFS endpoint pattern** (confirmed live from the layer's own
``/services/`` listing, not guessed): Koordinates embeds the API key in
the URL **path**, not a query parameter or header -
``https://data.linz.govt.nz/services;key={api_key}/wfs/layer-{id}/?service=WFS&request=GetFeature&typeNames=layer-{id}&outputFormat=json``.
This module builds that URL itself and hands it to the existing
:class:`~streetworks.ogc.OGCFeaturesClient`, which already knows how to
issue a WFS ``GetFeature`` request and parse GeoJSON - no new transport
was needed, just the LDS-specific URL construction. **Pagination
(``startIndex``/``count``) is implemented to the WFS 2.0 standard, but
has never been exercised against a real response** - unlike
:class:`~streetworks.arcgis.client.ArcGISFeatureClient`'s own live-
verified pagination strategy, there is no equivalent live evidence here
yet that Koordinates' WFS genuinely honours ``startIndex``/``count`` the
way the spec says. Report back once you've run this against a real key -
see the module's own "help wanted" issue.

**The join headline: ``road_id`` is the real, shared field name across
all three layers' schemas** (confirmed live from each layer's own
metadata) - Addresses, Roads, and Road Sections. **Whether the same
numeric value cross-references between them is unconfirmed** - the real
Addresses sample and the real Roads/Road Sections samples pulled live so
far happen not to overlap (different random samples), and confirming a
genuine match needs a real WFS query this build has no key for. If
confirmed, this closes the address-street-segment join with a genuine
stated identifier - the USRN-analogue AU's G-NAF could not provide - see
:mod:`streetworks.common.from_linz`.

**No structured join to NZTA's works feed** - see :mod:`streetworks.nzta.client`'s
own module docstring: NZTA's real schema states no structured road/route
identifier, only free text, so there is nothing to join ``road_id``
against from the works side. LINZ stands on its own as this cluster's
gazetteer.

**Credentials**: none for :meth:`iter_addresses`. A free, self-service
LINZ Data Service API key for :meth:`iter_roads`/:meth:`iter_road_sections`
- register at `data.linz.govt.nz <https://data.linz.govt.nz/>`_, then
create a "Data access only" key from your account menu.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..arcgis.client import ArcGISFeatureClient
from ..ogc.client import OGCFeaturesClient

__all__ = [
    "ADDRESSES_BASE_URL",
    "ADDRESSES_LAYER",
    "LDS_BASE_URL",
    "ROADS_LAYER_ID",
    "ROAD_SECTIONS_LAYER_ID",
    "LinzClient",
]

JSON = dict[str, Any]

#: The public ArcGIS Online mirror of NZ Addresses (123113) - no LDS key
#: needed, confirmed live. See module docstring.
ADDRESSES_BASE_URL = "https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/LINZ_NZ_Addresses/FeatureServer"
ADDRESSES_LAYER = 0

#: The real LDS host - the API key is embedded in the URL path
#: (``;key=...``), Koordinates' own convention, confirmed live from the
#: layer's own /services/ listing. See module docstring.
LDS_BASE_URL = "https://data.linz.govt.nz"

#: Real LINZ layer ids - NZ Addresses: Roads / Road Sections. See module
#: docstring for why these need a real LDS key, unlike Addresses.
ROADS_LAYER_ID = 123110
ROAD_SECTIONS_LAYER_ID = 123109

#: A defensive cap on WFS pagination loops - never verified against a
#: real response (see module docstring), so this exists purely to stop a
#: malformed/looping server response from hanging a caller forever.
_MAX_PAGES = 10_000
_PAGE_SIZE = 1000


class LinzClient:
    """Fetch New Zealand address and road gazetteer data from LINZ.
    :meth:`iter_addresses` needs no credentials (a public ArcGIS mirror);
    :meth:`iter_roads`/:meth:`iter_road_sections` need a free, self-
    service LINZ Data Service API key - see module docstring for why the
    two routes have different verification levels.

    >>> from streetworks.linz import LinzClient
    >>> from streetworks.common import from_linz
    >>> with LinzClient() as linz:  # doctest: +SKIP
    ...     addresses = [from_linz(a) for a in linz.iter_addresses()]
    >>> with LinzClient(api_key=api_key) as linz:  # doctest: +SKIP
    ...     roads = [from_linz(r) for r in linz.iter_roads()]
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self._arcgis = ArcGISFeatureClient(client=client)
        self._ogc = OGCFeaturesClient(client=client)

    def iter_addresses(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Every real NZ Addresses feature (GeoJSON ``Feature`` dicts) -
        confirmed live, no credentials needed. See module docstring."""
        yield from self._arcgis.iter_features(
            ADDRESSES_BASE_URL, ADDRESSES_LAYER, where=where, out_fields="*", out_sr=4326
        )

    def _require_api_key(self) -> str:
        if not self.api_key:
            raise ValueError(
                "api_key is required for LDS WFS access (iter_roads/iter_road_sections) - "
                "register free at https://data.linz.govt.nz/ and create a 'Data access "
                "only' key. iter_addresses() needs no key at all - see module docstring."
            )
        return self.api_key

    def _iter_wfs_layer(self, layer_id: int) -> Iterator[JSON]:
        """Pages a real LDS WFS layer via ``startIndex``/``count`` (WFS
        2.0) - implemented to spec, never exercised against a real
        response, see module docstring."""
        api_key = self._require_api_key()
        base_url = f"{LDS_BASE_URL}/services;key={api_key}/wfs/"
        type_name = f"layer-{layer_id}"
        start_index = 0
        for _ in range(_MAX_PAGES):
            payload = self._ogc.get_wfs_features(
                base_url,
                type_name=type_name,
                extra_params={
                    "startIndex": str(start_index),
                    "count": str(_PAGE_SIZE),
                },
            )
            features = payload.get("features", [])
            yield from features
            if len(features) < _PAGE_SIZE:
                return
            start_index += _PAGE_SIZE

    def iter_roads(self) -> Iterator[JSON]:
        """Every real NZ Addresses: Roads feature (aggregated centrelines)
        - requires ``api_key``, never exercised against a real response,
        see module docstring."""
        yield from self._iter_wfs_layer(ROADS_LAYER_ID)

    def iter_road_sections(self) -> Iterator[JSON]:
        """Every real NZ Addresses: Road Sections feature (individual
        section geometries) - requires ``api_key``, never exercised
        against a real response, see module docstring."""
        yield from self._iter_wfs_layer(ROAD_SECTIONS_LAYER_ID)

    def close(self) -> None:
        self._arcgis.close()
        self._ogc.close()

    def __enter__(self) -> LinzClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
