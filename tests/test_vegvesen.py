"""Tests for the Norway (Statens vegvesen) DATEX II adapter.

**Phase 2 confirmed (2026-07-30)** - see the module docstring in
``streetworks.datex2.vegvesen``, including the now-resolved mixed-CRS
geometry finding (see ``tests/test_common_datex2.py`` and
``tests/test_crs.py`` for the resolution itself - this file covers the
parser/client layer only, where ``Location.points`` and ``.srs_name`` stay
raw, exactly as the source states them). Two fixtures:

- ``vegvesen_getsituation_sample.xml`` is not Norwegian data: it's two
  real ``MaintenanceWorks`` situations from Iceland's IRCA DATEX
  snapshotPull service, wrapped in the real SOAP envelope it arrived in.
  It exists to prove the *parser-reuse hypothesis* on a structurally
  identical document - the Phase 1 groundwork that turned out to predict
  Norway's own real shape correctly.
- ``vegvesen_real_pull.xml`` is two real Norwegian ``MaintenanceWorks``
  situations, trimmed from a real, credentialed pull (2026-07-30, by a
  tester running ``scripts/smoke_test.py`` with real HTTP Basic
  credentials), wrapped in the real bare ``messageContainer`` envelope
  Norway's REST path actually returns (no SOAP, unlike Iceland's). One
  record is genuine WGS84 (Oslo); the other is genuine UTM zone 33N
  (``srsName="25833"``, a bridge in Kristiansund) - deliberately kept as
  a pair to regression-test the real mixed-CRS finding.
"""

from pathlib import Path

import httpx
import pytest
import respx

from streetworks.datex2 import VegvesenClient, iter_roadworks, iter_situations
from streetworks.datex2.vegvesen import BASE_URL

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vegvesen_getsituation_sample.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()

REAL_PULL_PATH = Path(__file__).parent / "fixtures" / "vegvesen_real_pull.xml"


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


# --------------------------------------------------------------------------- #
# Real Norwegian data (2026-07-30) - see vegvesen_real_pull.xml
# --------------------------------------------------------------------------- #


def test_real_norwegian_pull_confirms_genuine_datex_v3_bare_messagecontainer():
    """Real finding: the REST-path response is a bare messageContainer,
    not the SOAP envelope Iceland's fixture arrives in - the shared
    parser handles both, but Norway's own real shape is simpler."""
    situations = list(iter_situations(REAL_PULL_PATH))
    assert [s.id for s in situations] == [
        "NPRA_HBT_04-06-2025.94764",
        "NPRA_HBT_29-10-2025.173277",
    ]
    for s in situations:
        works = s.roadworks[0]
        assert works.record_type == "MaintenanceWorks"
        assert works.road_maintenance_type == "roadworks"
        assert works.comments == ("Vegarbeid.",)  # real Norwegian text


def test_real_norwegian_pull_confirms_mixed_crs_within_one_feed():
    """The single most important real finding: coordinates are mixed CRS
    within the same feed. One real record is genuine WGS84 (Oslo, a
    ``pointCoordinates`` point with no ``srsName`` - DATEX
    ``pointCoordinates`` is WGS84 by spec, never declares one); the other
    is genuine UTM zone 33N (a Kristiansund bridge, a ``gmlLineString``/
    posList with real ``srsName="25833"``). At this layer both still come
    back as plain, raw ``(float, float)`` values in the source's own
    document order/CRS - this parser layer doesn't resolve CRS or axis
    order (that's ``streetworks.common.from_vegvesen``'s job, see
    ``tests/test_common_datex2.py``); it now at least captures the real
    declaration via ``Location.srs_name``, letting a caller resolve it."""
    situations = list(iter_situations(REAL_PULL_PATH))

    oslo = situations[0].roadworks[0]
    assert oslo.location.point == (59.946438, 10.712339)  # genuine WGS84 range
    assert oslo.location.srs_name is None  # pointCoordinates never declares one

    kristiansund = situations[1].roadworks[0]
    assert kristiansund.location.point == (133396.39, 7018386.84)  # genuine UTM33N range
    assert kristiansund.location.srs_name == "25833"
    # Raw posList document order is (easting, northing) here - the opposite
    # axis convention from pointCoordinates' explicit (lat, lon) - resolving
    # that is from_vegvesen's job, not this layer's (see module docstring).
    lat, lon = kristiansund.location.point
    assert not (-90 <= lat <= 90 and -180 <= lon <= 180)  # not plausible as WGS84
