"""Tests for streetworks.idee - Spain's national road-transport network
(IGN, over IDEE's INSPIRE WFS).

Credential-free, live-verified 2026-08-15 - see the module docstring in
``streetworks.idee.client``. The XML fixtures are REAL, trimmed
live-pull responses:

- ``idee_roads_live_pull.xml`` - 2 real ``tn-ro:Road`` features
  (``CONCORDIA``, 1 link; ``ARQUIMEDES``, 2 links), fetched via
  ``RESOURCEID`` so there is no ``next`` link.
- ``idee_roads_page1_live_pull.xml`` - 1 real ``tn-ro:Road`` fetched with
  ``COUNT=1``, carrying a real ``next`` pagination link.
- ``idee_roadlinks_live_pull.xml`` - the 3 real ``tn-ro:RoadLink``
  features those two Roads' ``net:link`` hrefs point at, fetched in one
  real batched ``RESOURCEID`` request.

The one unresolved-link scenario (a broken cross-reference) is not
reproducible on demand from a live pull - the original investigation
found it non-systemic (1 of 3 sampled) - so that one case uses a small,
clearly-labelled synthetic fixture instead, matching this SDK's existing
practice for genuinely non-reproducible edge cases (e.g. ASFINAG's
synthetic DATEX fixture).
"""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from streetworks.idee import BASE_URL, IdeeTransportesClient

FIXTURES = Path(__file__).parent / "fixtures"
ROADS_XML = (FIXTURES / "idee_roads_live_pull.xml").read_bytes()
ROADS_PAGE1_XML = (FIXTURES / "idee_roads_page1_live_pull.xml").read_bytes()
ROADLINKS_XML = (FIXTURES / "idee_roadlinks_live_pull.xml").read_bytes()

_EMPTY_PAGE_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"
    numberMatched="0" numberReturned="0"/>
"""

# A synthetic Road whose one net:link href points at an id deliberately
# absent from ROADLINKS_XML - the broken-cross-reference case the
# original investigation found real but not reproducible on demand.
_ROAD_WITH_BROKEN_LINK_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"
    xmlns:gml="http://www.opengis.net/gml/3.2"
    numberMatched="1" numberReturned="1">
  <wfs:member>
    <tn-ro:Road xmlns:tn-ro="http://inspire.ec.europa.eu/schemas/tn-ro/4.0"
        gml:id="TN-RO_ROAD_SYNTHETIC_BROKEN">
      <net:inspireId xmlns:net="http://inspire.ec.europa.eu/schemas/net/4.0">
        <base:Identifier xmlns:base="http://inspire.ec.europa.eu/schemas/base/3.3">
          <base:localId>SYNTHETIC_BROKEN</base:localId>
          <base:namespace>ES.SCNE.IGR-RT</base:namespace>
        </base:Identifier>
      </net:inspireId>
      <net:link xmlns:net="http://inspire.ec.europa.eu/schemas/net/4.0"
          xmlns:xlink="http://www.w3.org/1999/xlink"
          xlink:href="https://servicios.idee.es/wfs-inspire/transportes?SERVICE=WFS&amp;REQUEST=GetFeature&amp;ID=TN-RO_ROADLINK_DOES_NOT_EXIST#TN-RO_ROADLINK_DOES_NOT_EXIST"/>
      <tn:geographicalName xmlns:tn="http://inspire.ec.europa.eu/schemas/tn/4.0">
        <gn:GeographicalName xmlns:gn="http://inspire.ec.europa.eu/schemas/gn/4.0">
          <gn:spelling>
            <gn:SpellingOfName><gn:text>SYNTHETIC ROAD</gn:text></gn:SpellingOfName>
          </gn:spelling>
        </gn:GeographicalName>
      </tn:geographicalName>
      <tn-ro:localRoadCode>1</tn-ro:localRoadCode>
    </tn-ro:Road>
  </wfs:member>
</wfs:FeatureCollection>
"""

_EMPTY_ROADLINKS_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"
    numberMatched="0" numberReturned="0"/>
"""


def _mock_roads_and_links() -> None:
    def _dispatch(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        if "RESOURCEID" in params:
            return httpx.Response(200, content=ROADLINKS_XML)
        return httpx.Response(200, content=ROADS_XML)

    respx.get(BASE_URL).mock(side_effect=_dispatch)


@respx.mock
def test_iter_roads_needs_no_credentials_and_resolves_geometry():
    _mock_roads_and_links()
    with IdeeTransportesClient() as idee:
        roads = list(idee.iter_roads())

    assert len(roads) == 2
    concordia = next(r for r in roads if r.name == "CONCORDIA")
    arquimedes = next(r for r in roads if r.name == "ARQUIMEDES")

    assert concordia.unresolved_links == 0
    assert concordia.geometry is not None
    assert concordia.geometry.crs == "EPSG:4258"
    assert concordia.geometry.parts is not None
    assert len(concordia.geometry.parts) == 1  # one real RoadLink

    assert arquimedes.unresolved_links == 0
    assert arquimedes.geometry is not None
    assert len(arquimedes.geometry.parts) == 2  # two real RoadLinks


@respx.mock
def test_iter_roads_carries_real_road_codes_and_inspire_id():
    _mock_roads_and_links()
    with IdeeTransportesClient() as idee:
        roads = list(idee.iter_roads())

    concordia = next(r for r in roads if r.name == "CONCORDIA")
    assert concordia.national_road_code == "0809602044"
    assert concordia.local_road_code == "48"
    assert concordia.inspire_local_id == "VIAL_LI80960000289"
    assert concordia.inspire_namespace == "ES.SCNE.IGR-RT"
    assert concordia.id == "TN-RO_ROAD_VIAL_LI80960000289"


@respx.mock
def test_iter_roads_follows_the_servers_own_next_link():
    call_count = 0

    def _dispatch(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        params = request.url.params
        if "RESOURCEID" in params:
            return httpx.Response(200, content=ROADLINKS_XML)
        call_count += 1
        if params.get("STARTINDEX") == "1":
            return httpx.Response(200, content=_EMPTY_PAGE_XML)
        return httpx.Response(200, content=ROADS_PAGE1_XML)

    respx.get(BASE_URL).mock(side_effect=_dispatch)

    with IdeeTransportesClient() as idee:
        roads = list(idee.iter_roads(count=1))

    assert len(roads) == 1  # page1's one road, then the empty terminal page
    assert call_count == 2  # the real next link was actually followed, not ignored


@respx.mock
def test_a_broken_cross_reference_is_counted_not_raised():
    def _dispatch(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        if "RESOURCEID" in params:
            return httpx.Response(200, content=_EMPTY_ROADLINKS_XML)
        return httpx.Response(200, content=_ROAD_WITH_BROKEN_LINK_XML)

    respx.get(BASE_URL).mock(side_effect=_dispatch)

    with IdeeTransportesClient() as idee:
        roads = list(idee.iter_roads())

    assert len(roads) == 1
    road = roads[0]
    assert road.unresolved_links == 1
    assert road.geometry is None  # never fabricated
    assert road.name == "SYNTHETIC ROAD"  # the rest of the road is still usable
