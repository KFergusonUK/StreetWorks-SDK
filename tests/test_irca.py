"""Tests for the Iceland (IRCA/Vegagerðin) DATEX II adapter.

The fixture (three real situations, trimmed) is from a live fetch against
``https://datex.vegagerdin.is/situationpublication3_1/SituationService``,
2026-07 - confirmed reachable with no credentials/API key/IP allow-listing
required, across multiple independent fetches (see module docstring in
streetworks.datex2.irca). Two ``MaintenanceWorks`` situations plus one
``NonWeatherRelatedRoadConditions`` situation (not roadworks - exercises
the roadworks filter), the latter also confirming the multilingual-comments
fix doesn't just skip empties: it still returns the first value when that
one is genuinely non-empty (this record's ``lang="en"`` entry has real
text, unlike the other two).
"""

from pathlib import Path
from xml.etree.ElementTree import Element

import httpx
import respx

from streetworks.datex2 import IcelandClient, iter_roadworks_full, iter_situations_full
from streetworks.datex2._snapshotpull import SOAP_ACTION
from streetworks.datex2.irca import SITUATION_ENDPOINT

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "irca_situations.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def test_parses_real_situations():
    situations = list(iter_situations_full(FIXTURE_PATH))
    assert [s.id for s in situations] == ["IRCA_67862.0", "IRCA_70818.0", "IRCA_71223.0"]


def test_iter_roadworks_excludes_non_weather_related_road_conditions():
    roadworks = list(iter_roadworks_full(FIXTURE_PATH))
    assert [s.id for s in roadworks] == ["IRCA_67862.0", "IRCA_70818.0"]


def test_maintenance_works_fields():
    situations = list(iter_situations_full(FIXTURE_PATH))
    works = situations[0].roadworks[0]
    assert works.record_type == "MaintenanceWorks"
    assert works.road_maintenance_type == "roadworks"
    assert works.probability_of_occurrence == "certain"
    assert works.location.kind == "PointLocation"
    assert works.location.point == (63.939644, -20.964005)
    assert works.source_name is None  # no <source> element on any real record seen


def test_raw_is_populated_unlike_the_streaming_parser():
    # IcelandClient uses iter_situations_full (whole-document parse, no
    # element.clear()), since the ~250 KB response is small enough that
    # .raw fidelity doesn't need to be traded for memory bounding - unlike
    # NDW/Norway, which stream and clear elements on much larger feeds.
    situations = list(iter_situations_full(FIXTURE_PATH))
    situation = situations[0]
    record = situation.roadworks[0]
    assert isinstance(situation.raw, Element)
    assert isinstance(record.raw, Element)
    assert situation.raw.get("id") == "IRCA_67862.0"
    assert record.raw.get("id") == "IRCA_67862.0_1"


def test_multilingual_comment_skips_empty_placeholder():
    situations = list(iter_situations_full(FIXTURE_PATH))
    works = situations[1].roadworks[0]
    assert works.comments == (
        "Stikur hafa verið teknar upp og kantar lagaðir, slitlagið er "
        "holótt og mjög ílla farið. Akið varlega.",
    )


def test_multilingual_comment_still_returns_genuinely_first_value():
    # This record's lang="en" entry is real (not an empty placeholder) -
    # confirms the fix takes the first NON-EMPTY value, not always the last.
    situations = list(iter_situations_full(FIXTURE_PATH))
    non_roadworks = next(s for s in situations if not s.roadworks)
    record = non_roadworks.records[0]
    assert record.record_type == "NonWeatherRelatedRoadConditions"
    assert record.comments == (
        "Road work: Loose gravel, drive with care, speed reduced to 50 km",
    )


@respx.mock
def test_client_posts_correct_soap_envelope_and_action():
    route = respx.post(SITUATION_ENDPOINT).mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with IcelandClient() as irca:
        situations = list(irca.iter_situations())
    assert len(situations) == 3
    assert isinstance(situations[0].raw, Element)

    request = route.calls.last.request
    assert request.headers["SOAPAction"] == f'"{SOAP_ACTION}"'
    assert b"pullSnapshotData" in request.content


@respx.mock
def test_client_iter_roadworks_filters():
    respx.post(SITUATION_ENDPOINT).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with IcelandClient() as irca:
        roadworks = list(irca.iter_roadworks())
    assert len(roadworks) == 2
