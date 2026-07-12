"""Tests for the Norway (Statens vegvesen) DATEX II adapter.

**Pending live verification** - see the module docstring in
``streetworks.datex2.vegvesen``. The fixture
(``vegvesen_getsituation_sample.xml``) is not Norwegian data: it's two real
``MaintenanceWorks`` situations from Iceland's IRCA DATEX snapshotPull
service (the same ``snapshotPull``/``SituationPublication`` v3 interface,
confirmed live, credential-free), wrapped in the real SOAP envelope it
arrived in. It exists to prove the *parser-reuse hypothesis* - that a real,
SOAP-wrapped snapshotPull response parses through the existing shared
``iter_situations``/``iter_roadworks`` unchanged - not to assert anything
about Norway's actual feed shape, which remains unconfirmed until Phase 2.
"""

from pathlib import Path

import httpx
import pytest
import respx

from streetworks.datex2 import VegvesenClient, iter_roadworks, iter_situations
from streetworks.datex2.vegvesen import BASE_URL

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vegvesen_getsituation_sample.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def test_real_snapshotpull_response_parses_through_shared_parser():
    """The core Phase 1 hypothesis check: a real SOAP-wrapped snapshotPull
    document (s:Envelope/s:Body/pullSnapshotDataOutput/payload) parses with
    zero changes to the shared parser, which matches purely on local element
    names."""
    situations = list(iter_situations(FIXTURE_PATH))
    assert [s.id for s in situations] == ["IRCA_70463.0", "IRCA_71260.0"]

    first = situations[0].roadworks[0]
    assert first.record_type == "MaintenanceWorks"
    assert first.road_maintenance_type == "roadworks"
    assert first.probability_of_occurrence == "certain"
    assert first.location.kind == "PointLocation"
    assert first.location.point == (65.422844, -21.754923)

    # Streaming XML parser trade-off (same as NDW) - .raw stays unset.
    assert first.raw is None
    assert situations[0].raw is None

    # Regression check for the multilingual-comments bug (fixed alongside
    # the Iceland provider, see tests/test_datex2.py): this fixture's real
    # comment lists an empty lang="en" placeholder before the real lang="is"
    # text - the parser must return the real text, not the empty one.
    assert first.comments == (
        "Unnið við endurbyggingu vegarins, hann er grófur, ósléttur og "
        "seinfarinn, akið mjög varlega. Þetta er vinnusvæði!!",
    )


def test_iter_roadworks_filters_correctly():
    situations = list(iter_roadworks(FIXTURE_PATH))
    assert len(situations) == 2


def test_soap_envelope_does_not_confuse_validity_or_dates():
    situations = list(iter_situations(FIXTURE_PATH))
    works = situations[1].roadworks[0]
    assert works.validity.overall_start.isoformat() == "2026-07-12T11:55:57+00:00"
    assert works.validity.overall_end.isoformat() == "2026-07-17T12:55:00+00:00"
    assert works.location.point == (64.764, -22.266333)


def test_client_requires_exactly_one_auth_method():
    with pytest.raises(ValueError):
        VegvesenClient()
    with pytest.raises(ValueError):
        VegvesenClient(username="u", password="p", token="t")


@respx.mock
def test_client_basic_auth_fetches_and_parses():
    respx.get(f"{BASE_URL}/datexapi/GetSituation/pullsnapshotdata").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with VegvesenClient(username="u", password="p") as vegvesen:
        situations = list(vegvesen.iter_situations())
    assert len(situations) == 2

    request = respx.calls.last.request
    assert request.headers["Authorization"].startswith("Basic ")


@respx.mock
def test_client_bearer_auth_sends_token():
    respx.get(f"{BASE_URL}/datexapi/GetSituation/pullsnapshotdata").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with VegvesenClient(token="secret-token") as vegvesen:
        roadworks = list(vegvesen.iter_roadworks())
    assert len(roadworks) == 2

    request = respx.calls.last.request
    assert request.headers["Authorization"] == "Bearer secret-token"
