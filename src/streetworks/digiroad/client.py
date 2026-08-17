"""Digiroad - Finland's real national road/street network, over
Väylävirasto's (the Finnish Transport Infrastructure Agency) own open
WFS. This SDK's first Finnish streets/gazetteer coverage - a real
sibling to Finland's existing roadworks coverage (Digitraffic,
`streetworks.datex2.digitraffic`), from the same real government
department Fintraffic/Väylävirasto operates under, though a genuinely
different agency and dataset from Digitraffic's own live-situation feed.

**Found by checking a different agency from the one that looked
obvious first.** Maanmittauslaitos (MML, the National Land Survey)
publishes Finland's general topographic database (Maastotietokanta)
over a modern OGC API Features service - but it genuinely requires a
self-service API key (confirmed live: the bare endpoint returns `401`
with no key), so per this project's own access-boundary rules (no
registering accounts on the project's behalf - see
`docs/contributing/agent-boundaries.md`) it wasn't built against.
Checking further found Väylävirasto's own separate WFS deployment
instead - confirmed live, **genuinely keyless, no registration of any
kind** (`avoinapi.vaylapilvi.fi`) - which turned out to carry Digiroad,
Finland's real national road/street database (originally a joint
Finnish Transport Agency/municipality venture, now Väylävirasto's own),
not just the state-maintained "tiestotiedot" asset-management layers
that dominate this same deployment's real 328-layer catalogue.

**A real cartographic-view duplication, confirmed live before picking
one layer - the same trap TIGERweb's own layers 0-9 were.** Three real
layer names (`dr_tielinkki_hall_lk`, `dr_tielinkki_toim_lk`,
`dr_tielinkki_tielinkin_tyyppi`) all resolve to the exact same real
underlying table - identical field list, identical real national count
(3,363,654), confirmed by comparing `DescribeFeatureType` output and
`resultType=hits` across all three. This module uses
`dr_tielinkki_hall_lk`; the other two names are not separate data.

**Real field list** (confirmed live): `link_id` (a real Digiroad UUID,
segment-suffixed e.g. `"f4062096-...:1"`), `link_mmlid` (a second real
identifier, MML's own), `tienimi_su`/`tienimi_ru` (the real street name
in Finnish and Swedish - Finland's genuine bilingual convention, both
populated on the large majority of real named segments checked, e.g. a
live Helsinki bbox: 4,198/5,000 with a Finnish name, 4,190/5,000 with a
Swedish name), `hallinn_lk` (a real administrative-class code,
undecoded - no lookup table bundled, per this SDK's standing rule),
`kuntakoodi` (a real municipality code - kept as an `Identifier`, never
promoted to `administrative_area`, since it's a bare numeric code with
no accompanying decoded name field anywhere on this layer),
`tienumero`/`tieosanro` (a real road/section number, populated on
state-maintained roads only).

**Real 3D geometry - `Z` genuinely present and preserved through
reprojection, confirmed live.** Every real `LineString` vertex checked
carries a real elevation value in metres (e.g. `92.867`) - preserved
whether or not `srsName=EPSG:4326` is requested (confirmed live,
byte-comparable Z values either way). Per this SDK's own data-integrity
rule, Z is carried through exactly as given, never defaulted to zero.

**CRS: native `EPSG:3067` (ETRS89 / TM35FIN), real WGS84 only when
explicitly requested - confirmed live, the opposite default from
Iceland's own WFS.** A plain request with no `srsName` stays in the
native Finnish grid; `srsName=EPSG:4326` genuinely reprojects (confirmed
live, real Helsinki coordinates, `24.70, 61.00`-shaped). This module
always requests it explicitly. Unlike Gibraltar's and Iceland's own
GeoServer deployments, this one genuinely accepts
`application/geo+json` directly - no output-format workaround needed.

**Scale**: 3,363,654 real features nationally - TIGERweb/NRN-scale.
This server also enforces a real ~5,000-feature-per-request cap
regardless of a larger `count` (confirmed live). Querying without a
geographic filter is not recommended; every real example in this
module's tests and the smoke-test check uses a small real bounding box.

**Licence: Creative Commons Attribution 4.0 International, confirmed
live directly from the dataset's own real avoindata.fi catalogue
entry**: *"Väylävirasto on julkaissut rajapinnan Väyläviraston avoin
WFS-rajapinta lisenssillä Creative Commons Attribution 4.0
International License."*
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..ogc import OGCFeaturesClient

__all__ = ["BASE_URL", "STREETS_TYPE_NAME", "CRS", "DigiroadClient"]

JSON = dict[str, Any]

#: The real Väylävirasto open WFS deployment. See module docstring.
BASE_URL = "https://avoinapi.vaylapilvi.fi/vaylatiedot/ows"

#: The real Digiroad road-link layer - see module docstring for why
#: this is one of three identically-shaped real layer names.
STREETS_TYPE_NAME = "digiroad:dr_tielinkki_hall_lk"

#: Confirmed live: this layer's native CRS is EPSG:3067 (ETRS89 /
#: TM35FIN); real WGS84 output requires this to be requested explicitly
#: - see module docstring.
CRS = "EPSG:4326"


class DigiroadClient:
    """Fetch Finland's real Digiroad road/street network. No credentials
    required.

    >>> from streetworks.digiroad import DigiroadClient
    >>> from streetworks.common import from_digiroad_street
    >>> helsinki_bbox = (24.90, 60.14, 25.00, 60.22)  # (xmin, ymin, xmax, ymax), WGS84
    >>> with DigiroadClient() as digiroad:  # doctest: +SKIP
    ...     streets = [from_digiroad_street(f) for f in digiroad.iter_streets(bbox=helsinki_bbox)]
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def iter_streets(
        self, *, bbox: tuple[float, float, float, float] | None = None
    ) -> Iterator[JSON]:
        """Yield real road-link features (GeoJSON ``Feature`` dicts).

        ``bbox`` is ``(xmin, ymin, xmax, ymax)`` in WGS84 (EPSG:4326) - a
        geographic filter is **strongly recommended**: this layer has
        3,363,654 real features nationally, see module docstring.
        Querying without one will attempt to page the entire national
        dataset.
        """
        extra_params: dict[str, str] = {}
        if bbox is not None:
            xmin, ymin, xmax, ymax = bbox
            extra_params["BBOX"] = f"{xmin},{ymin},{xmax},{ymax},EPSG:4326"

        offset = 0
        while True:
            page_params = dict(extra_params)
            page_params["STARTINDEX"] = str(offset)
            payload = self._ogc.get_wfs_features(
                BASE_URL,
                type_name=STREETS_TYPE_NAME,
                srs_name=CRS,
                extra_params=page_params,
            )
            features = payload.get("features", [])
            if not features:
                return
            yield from features

            offset += len(features)
            total = payload.get("numberMatched")
            if total is not None and offset >= total:
                return

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> DigiroadClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
