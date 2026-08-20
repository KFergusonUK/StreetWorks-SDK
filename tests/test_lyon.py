"""Tests for streetworks.lyon and streetworks.common.from_lyon.

Fixture is real trimmed WFS GeoJSON data
(tests/fixtures/lyon_roadworks.json), captured live 2026-08-20 from
Métropole de Lyon's own real GeoServer WFS - see
streetworks.lyon.client's module docstring for the full investigation.
6 real records: 5 from the first page (all real `intervenant="Autre"`,
the overwhelming majority shape) plus one real record with
`intervenant="Grand Lyon"` (gid 415565), found by scanning the whole
live 351-feature layer for the rare non-"Autre" case. Polygon rings
trimmed to 5 real vertices each - this converter only ever reads the
first ring's first vertex.
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import DateConfidence, from_lyon
from streetworks.lyon import BASE_URL, TYPE_NAME, LyonClient

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "lyon_roadworks.json").read_text())
_FEATURES = {f["properties"]["gid"]: f for f in FIXTURE["features"]}


@respx.mock
def test_iter_roadworks_yields_real_features():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    with LyonClient() as lyon:
        features = list(lyon.iter_roadworks())
    assert len(features) == 6
    assert features[0]["properties"]["nom"] == "Avenue Rockefeller"


@respx.mock
def test_iter_roadworks_requests_the_real_type_name():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    with LyonClient() as lyon:
        list(lyon.iter_roadworks())
    params = dict(httpx.QueryParams(route.calls.last.request.url.query))
    assert params["TYPENAMES"] == TYPE_NAME
    assert params["SRSNAME"] == "EPSG:4326"


def test_real_road_status_and_works_type():
    works = from_lyon([_FEATURES[415605]])
    w = works[0]
    site = w.sites[0]
    assert w.reference == "415605"
    assert site.location_description == "Avenue Rockefeller"
    assert site.status == "Circulation alternée"
    assert site.works_type == "Travaux voirie"
    assert w.territory == "France"
    assert w.administrative_area == "Métropole de Lyon"


def test_date_only_dates_localised_to_europe_paris():
    works = from_lyon([_FEATURES[415605]])
    site = works[0].sites[0]
    assert str(site.proposed_start) == "2026-08-17 00:00:00+02:00"
    assert str(site.proposed_end) == "2026-08-21 00:00:00+02:00"
    assert site.date_confidence is DateConfidence.VERIFIED


def test_multipolygon_first_ring_first_vertex_used_never_a_centroid():
    works = from_lyon([_FEATURES[415605]])
    coordinate = works[0].coordinate
    assert coordinate.crs == "EPSG:4326"
    assert coordinate.points is None  # never forced from a polygon ring
    assert coordinate.parts is None
    lat, lon = coordinate.value
    assert 45.6 < lat < 45.9  # real Lyon bounds
    assert 4.7 < lon < 5.0
    # The real polygon survives unmodified in raw, never discarded.
    assert works[0].raw["geometry"]["type"] == "MultiPolygon"


def test_intervenant_mostly_autre_but_real_value_carried_through():
    # 347/351 real records state the uninformative literal "Autre" - not
    # suppressed, still mapped, since it's what the source states.
    autre_works = from_lyon([_FEATURES[415605]])
    assert autre_works[0].promoter == "Autre"

    grand_lyon_works = from_lyon([_FEATURES[415565]])
    assert grand_lyon_works[0].promoter == "Grand Lyon"
