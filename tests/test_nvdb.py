"""Tests for the Norway NVDB street-geometry adapter.

Fixtures are real, trimmed, live (2026-07): ``nvdb_veglenkesekvenser.json``
(3 real road link sequences, Kristiansand/kommune 4201), ``nvdb_adresser.json``
(8 real `Adresse` objects - 5 from Kristiansand, including "Solstadheia"
[a real address spanning two different link sequences] and two real
"Fjebuveien" objects sharing one real `adressekode`; 3 from Karasjok
[kommune 5610], real Sámi-language street names), and
``nvdb_adresse_dalveien.json`` (the single real "Dalveien" object this
brief's investigation used throughout - `adressekode` 1140, spanning
link sequences 384 and 2399262).
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.nvdb import NVDBClient
from streetworks.nvdb.client import VEGNETT_BASE_URL, VEGOBJEKTER_BASE_URL
from streetworks.nvdb.models import vegadresse_from_response, veglenkesekvens_from_response

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _adresser():
    doc = _load_json("nvdb_adresser.json")
    return [vegadresse_from_response(o) for o in doc["objekter"]]


# --------------------------------------------------------------------------- #
# models.py - real response parsing, the topology-vs-naming finding
# --------------------------------------------------------------------------- #


def test_veglenkesekvens_from_response_is_purely_topological():
    doc = _load_json("nvdb_veglenkesekvenser.json")
    seq = veglenkesekvens_from_response(doc["objekter"][0])
    assert seq.veglenkesekvensid
    assert len(seq.veglenker) >= 1
    first = seq.veglenker[0]
    assert first.geometry is not None and first.geometry.startswith("LINESTRING Z")
    assert first.srid == 5973
    # No name field anywhere on the sequence or its raw data - confirmed
    # live, see the models module docstring.
    assert "navn" not in doc["objekter"][0]


def test_veglenke_carries_real_linear_referencing():
    doc = _load_json("nvdb_veglenkesekvenser.json")
    seq = veglenkesekvens_from_response(doc["objekter"][0])
    positions = [(v.startposisjon, v.sluttposisjon) for v in seq.veglenker]
    assert all(p[0] is not None and p[1] is not None for p in positions)
    # At least one real sub-link is a genuine fraction, not just 0.0-1.0.
    assert any(0.0 < p[1] < 1.0 for p in positions)


def test_vegadresse_from_response_real_dalveien():
    doc = _load_json("nvdb_adresse_dalveien.json")
    a = vegadresse_from_response(doc)
    assert a.adressenavn == "Dalveien"
    assert a.adressekode == "1140"
    assert a.toponyme_id() == "1140"
    assert a.geometry is not None and a.geometry.startswith("LINESTRING Z")
    assert a.srid == 5973


def test_vegadresse_can_span_multiple_veglenkesekvenser():
    """The genuinely important structural finding: one real address
    (Dalveien, adressekode 1140) is placed on two different, unrelated
    link sequences - Norway's naming layer and topological layer are not
    nested the way BD TOPO's voie_nommee/troncon_de_route are."""
    doc = _load_json("nvdb_adresse_dalveien.json")
    a = vegadresse_from_response(doc)
    assert a.veglenkesekvens_ids == (384, 2399262)


def test_real_multi_sequence_example_in_adresser_fixture():
    solstadheia = next(a for a in _adresser() if a.adressenavn == "Solstadheia")
    assert len(solstadheia.veglenkesekvens_ids) == 2
    assert solstadheia.adressekode == "6705"


def test_real_addresses_sharing_one_adressekode_agree_on_name():
    """Two distinct real Adresse objects (different `id`s - 917728065 and
    917728066) share one real adressekode (1069) and, confirmed live,
    the same adressenavn - the join is internally consistent."""
    fjebuveien = [a for a in _adresser() if a.adressekode == "1069"]
    assert len(fjebuveien) == 2
    assert {a.id for a in fjebuveien} == {917728065, 917728066}
    assert {a.adressenavn for a in fjebuveien} == {"Fjebuveien"}


def test_real_sami_language_names_from_karasjok():
    karasjok = [a for a in _adresser() if a.kommune == "5610"]
    assert len(karasjok) == 3
    names = {a.adressenavn for a in karasjok}
    assert names == {"Ávjovárgeaidnu", "Badjenjárga", "Ájonjárga"}


# --------------------------------------------------------------------------- #
# client.py - REST queries (respx-mocked)
# --------------------------------------------------------------------------- #


@respx.mock
def test_client_veglenkesekvenser_parses_real_response():
    respx.get(f"{VEGNETT_BASE_URL}/veglenkesekvenser").mock(
        return_value=httpx.Response(200, json=_load_json("nvdb_veglenkesekvenser.json"))
    )
    with NVDBClient() as nvdb:
        results = nvdb.veglenkesekvenser(kommune=4201)
    assert len(results) == 3


@respx.mock
def test_client_sends_x_client_header():
    route = respx.get(f"{VEGNETT_BASE_URL}/veglenkesekvenser").mock(
        return_value=httpx.Response(200, json=_load_json("nvdb_veglenkesekvenser.json"))
    )
    with NVDBClient(client_name="my-real-app", contact="dev@example.com") as nvdb:
        nvdb.veglenkesekvenser(kommune=4201, count=3)
    request = route.calls.last.request
    assert request.headers["X-Client"] == "my-real-app"
    assert request.headers["X-Kontaktperson"] == "dev@example.com"
    assert request.url.params["kommune"] == "4201"
    assert request.url.params["antall"] == "3"


@respx.mock
def test_client_adresser_parses_real_response_and_requests_inkluder_alle():
    route = respx.get(f"{VEGOBJEKTER_BASE_URL}/vegobjekter/538").mock(
        return_value=httpx.Response(200, json=_load_json("nvdb_adresser.json"))
    )
    with NVDBClient() as nvdb:
        results = nvdb.adresser(kommune=4201)
    assert len(results) == 8
    assert route.calls.last.request.url.params["inkluder"] == "alle"


@respx.mock
def test_client_query_error_maps_to_request_validation_error():
    """Real live shape (X-Client missing/rejected): a JSON problem-detail
    body, HTTP 400 - confirmed live."""
    from streetworks.exceptions import RequestValidationError

    error_body = {
        "detail": "X-Client må være satt når du kaller API Les V4.",
        "status": 400,
        "title": "Ugyldig forespørsel",
    }
    respx.get(f"{VEGNETT_BASE_URL}/veglenkesekvenser").mock(
        return_value=httpx.Response(400, json=error_body)
    )
    with NVDBClient() as nvdb, pytest.raises(RequestValidationError):
        nvdb.veglenkesekvenser()


@respx.mock
async def test_async_client_veglenkesekvenser_parses_real_response():
    from streetworks.nvdb import AsyncNVDBClient

    respx.get(f"{VEGNETT_BASE_URL}/veglenkesekvenser").mock(
        return_value=httpx.Response(200, json=_load_json("nvdb_veglenkesekvenser.json"))
    )
    async with AsyncNVDBClient() as nvdb:
        results = await nvdb.veglenkesekvenser(kommune=4201)
    assert len(results) == 3
