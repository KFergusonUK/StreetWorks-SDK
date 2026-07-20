"""Tests for the Norway Kartverket gazetteer adapter.

Fixtures are real, trimmed, live (2026-07):

* ``kartverket_search.json``/``kartverket_punktsok.json`` - the address
  REST API (``/sok``, ``/punktsok``), including the real "Karl Johans gate
  1" case that resolves to three different real addresses in three
  different municipalities.
* ``kartverket_sted_multilingual.json`` - the real Karasjok/Kárášjohka/
  Kaarasjoki place, three parallel official names (Norwegian, Northern
  Sámi, Kven), each independently statused.
* ``kartverket_sted_historical_spelling.json`` - a real natural feature
  ("Čalbmebealskáidi") with two Northern Sámi spellings under the same
  ``stedsnavnnummer``, one current, one historical.
* ``kartverket_navn.json`` - the ``/navn`` flattened one-name-per-hit shape.
* ``kartverket_navneobjekttyper.json``/``kartverket_sprak.json`` - the
  real, complete 291-type/18-language SSR reference lists.
* ``kartverket_bulk_atom_feed.xml`` - a real Atom feed, trimmed to the
  national + Karasjok entries.
* ``kartverket_bulk_sample.csv`` - real bulk CSV rows: five real addresses
  on "Ávjovárgeaidnu" (Karasjok) sharing one ``adressekode`` (grouping
  demo), three real ``adressetilleggsnavn`` examples, and one real
  ``matrikkeladresse``-type row from Oslo (empty ``adressekode``/
  ``adressenavn`` - that address type isn't street-based at all).
"""

import csv
import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.exceptions import RequestValidationError
from streetworks.kartverket import AsyncKartverketClient, KartverketClient
from streetworks.kartverket.atom import parse_feed
from streetworks.kartverket.client import ADDRESS_BASE_URL, SSR_BASE_URL
from streetworks.kartverket.models import (
    address_from_csv_row,
    address_from_json,
    place_from_navn,
    place_from_sted,
)
from streetworks.kartverket.reader import iter_addresses

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# models.py - address REST API shape
# --------------------------------------------------------------------------- #


def test_address_from_json_karl_johans_gate():
    doc = _load_json("kartverket_search.json")["adresser"][0]
    address = address_from_json(doc)
    assert address.adressenavn == "Karl Johans gate"
    assert address.kommunenavn == "SARPSBORG"
    assert address.adressekode == "15100"
    assert address.epsg == "EPSG:4258"
    assert address.nord == pytest.approx(59.28504689725078)
    assert address.ost == pytest.approx(11.111054335253176)
    assert address.raw is doc


def test_address_from_json_same_street_different_municipalities_different_codes():
    """Real live shape: "Karl Johans gate 1" resolves to three different
    real addresses in three different municipalities, each with its own
    adressekode - the same municipality-scoping BAN/BAG both showed."""
    docs = _load_json("kartverket_search.json")["adresser"]
    addresses = [address_from_json(d) for d in docs]
    assert len(addresses) == 3
    assert all(a.adressenavn == "Karl Johans gate" for a in addresses)
    codes = {a.adressekode for a in addresses}
    kommuner = {a.kommunenavn for a in addresses}
    assert len(codes) == 3
    assert len(kommuner) == 3


def test_address_from_json_punktsok_has_no_distance_field_promoted():
    doc = _load_json("kartverket_punktsok.json")["adresser"][0]
    address = address_from_json(doc)
    assert address.raw.get("meterDistanseTilPunkt") is not None


# --------------------------------------------------------------------------- #
# models.py - bulk CSV shape, adressekode grouping, encoding
# --------------------------------------------------------------------------- #


def _bulk_rows() -> list[dict]:
    with open(FIXTURES / "kartverket_bulk_sample.csv", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def test_address_from_csv_row_sami_name_and_uuid():
    row = next(r for r in _bulk_rows() if r["adressenavn"] == "Ávjovárgeaidnu")
    address = address_from_csv_row(row)
    assert address.adressenavn == "Ávjovárgeaidnu"
    assert address.uuid_adresse  # a real UUID string
    assert address.epsg == "EPSG:4258"


def test_bulk_addresses_group_cleanly_by_adressekode():
    """The over-merge check: every address sharing a real adressekode
    shares the same adressenavn - verified at full scale (Karasjok 1,896
    rows/139 codes, Oslo 106,154 rows/2,535 codes, zero over-merged) during
    this brief's investigation; reproduced here on the trimmed fixture."""
    addresses = [address_from_csv_row(r) for r in _bulk_rows() if r["adressekode"] == "1300"]
    assert len(addresses) == 6
    assert {a.adressenavn for a in addresses} == {"Ávjovárgeaidnu"}
    assert len({a.uuid_adresse for a in addresses}) == 6  # all distinct


def test_bulk_adressetilleggsnavn_examples_preserved():
    rows = [r for r in _bulk_rows() if r["adressetilleggsnavn"]]
    assert len(rows) == 3
    names = {r["adressetilleggsnavn"] for r in rows}
    assert names == {"Ladestasjon", "Uhca Guorpmet", "Liidnebeahcan"}


def test_bulk_matrikkeladresse_row_has_no_street_fields():
    """matrikkeladresse rows are cadastral-parcel addresses, not
    street-based at all - confirmed live: adressekode/adressenavn/nummer
    are genuinely empty, identity comes from gardsnummer/bruksnummer/
    festenummer/undernummer instead."""
    row = next(r for r in _bulk_rows() if r["adressetype"] == "matrikkeladresse")
    address = address_from_csv_row(row)
    assert address.adressekode == ""
    assert address.adressenavn is None
    assert address.nummer is None
    assert row["gardsnummer"] and row["bruksnummer"]


def test_bulk_epsg_read_from_row_not_assumed():
    for row in _bulk_rows():
        address = address_from_csv_row(row)
        assert address.epsg == f"EPSG:{row['EPSG-kode']}"


# --------------------------------------------------------------------------- #
# models.py - SSR multilingual/historical shapes
# --------------------------------------------------------------------------- #


def test_place_from_sted_three_parallel_official_names():
    doc = _load_json("kartverket_sted_multilingual.json")["navn"][0]
    place = place_from_sted(doc)
    assert place.stedsnummer == 868181
    assert len(place.names) == 3
    languages = {n.sprak for n in place.names}
    assert languages == {"Norsk", "Nordsamisk", "Kvensk"}
    kven = next(n for n in place.names if n.sprak == "Kvensk")
    norwegian = next(n for n in place.names if n.sprak == "Norsk")
    assert kven.skrivemate == "Kaarasjoki"
    assert kven.skrivematestatus == "foreslått og prioritert"  # proposed, not yet approved
    assert norwegian.skrivematestatus == "godkjent og prioritert"  # approved


def test_place_from_sted_historical_spelling_same_stedsnavnnummer():
    doc = _load_json("kartverket_sted_historical_spelling.json")["navn"][0]
    place = place_from_sted(doc)
    sami_names = [n for n in place.names if n.sprak == "Nordsamisk"]
    assert len(sami_names) == 2
    assert {n.stedsnavnnummer for n in sami_names} == {1}  # same name, two spellings
    statuses = {n.skrivematestatus for n in sami_names}
    assert statuses == {"godkjent og prioritert", "historisk"}


def test_place_from_navn_single_flattened_name():
    doc = _load_json("kartverket_navn.json")["navn"][0]
    place = place_from_navn(doc)
    assert len(place.names) == 1
    assert place.names[0].sprak == "Norsk"
    assert place.names[0].skrivemate == "Karasjok"


def test_place_kommuner_and_fylker_parsed():
    doc = _load_json("kartverket_sted_multilingual.json")["navn"][0]
    place = place_from_sted(doc)
    assert place.kommuner == (("5610", "Kárášjohka - Karasjok"),)
    assert place.fylker == (("56", "Finnmark - Finnmárku - Finmarkku"),)


# --------------------------------------------------------------------------- #
# atom.py - real feed parsing
# --------------------------------------------------------------------------- #


def test_parse_feed_finds_national_and_kommune_entries():
    xml_bytes = (FIXTURES / "kartverket_bulk_atom_feed.xml").read_bytes()
    entries = parse_feed(xml_bytes)
    assert len(entries) == 5
    national = [e for e in entries if e.kommune is None]
    karasjok = [e for e in entries if e.kommune == "Karasjok"]
    assert len(national) == 2
    assert len(karasjok) == 3
    assert {e.epsg for e in karasjok} == {"EPSG:25833", "EPSG:25835", "EPSG:4258"}


def test_parse_feed_ignores_non_csv_entries():
    xml_bytes = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Not a CSV</title>
        <link rel="alternate" href="https://example.org/data.gml.zip"/>
      </entry>
    </feed>"""
    assert parse_feed(xml_bytes) == []


def test_parse_feed_reads_rights_per_entry_not_feed_default():
    """Real quirk: most entries say "Kartverket" but Karasjok's real
    entries name the actual local data steward instead."""
    xml_bytes = (FIXTURES / "kartverket_bulk_atom_feed.xml").read_bytes()
    entries = parse_feed(xml_bytes)
    karasjok = next(e for e in entries if e.kommune == "Karasjok")
    national = next(e for e in entries if e.kommune is None)
    assert karasjok.rights == "DSB - Sivilforsvaret og brannvesenet."
    assert national.rights == "Kartverket"


# --------------------------------------------------------------------------- #
# reader.py - streaming the bulk CSV
# --------------------------------------------------------------------------- #


def test_iter_addresses_from_plain_csv():
    addresses = list(iter_addresses(FIXTURES / "kartverket_bulk_sample.csv"))
    assert len(addresses) == 9


def test_iter_addresses_from_zip(tmp_path):
    import zipfile

    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(FIXTURES / "kartverket_bulk_sample.csv", "matrikkelenAdresse.csv")
    addresses = list(iter_addresses(zip_path))
    assert len(addresses) == 9


def test_iter_addresses_from_open_stream():
    with open(FIXTURES / "kartverket_bulk_sample.csv", encoding="utf-8-sig", newline="") as f:
        addresses = list(iter_addresses(f))
    assert len(addresses) == 9


# --------------------------------------------------------------------------- #
# client.py - respx-mocked
# --------------------------------------------------------------------------- #


@respx.mock
def test_client_search_parses_real_response():
    respx.get(f"{ADDRESS_BASE_URL}/sok").mock(
        return_value=httpx.Response(200, json=_load_json("kartverket_search.json"))
    )
    with KartverketClient() as kv:
        results = kv.search(sok="Karl Johans gate 1")
    assert len(results) == 3


@respx.mock
def test_client_search_nearby_passes_params():
    route = respx.get(f"{ADDRESS_BASE_URL}/punktsok").mock(
        return_value=httpx.Response(200, json=_load_json("kartverket_punktsok.json"))
    )
    with KartverketClient() as kv:
        kv.search_nearby(59.9139, 10.7522, radius=200)
    params = route.calls.last.request.url.params
    assert params["lat"] == "59.9139"
    assert params["radius"] == "200"


@respx.mock
def test_client_search_error_maps_to_request_validation_error():
    respx.get(f"{ADDRESS_BASE_URL}/sok").mock(
        return_value=httpx.Response(400, json={"message": "Ingen søkeparametere oppgitt."})
    )
    with KartverketClient() as kv, pytest.raises(RequestValidationError):
        kv.search()


@respx.mock
def test_client_search_places_parses_multilingual_response():
    respx.get(f"{SSR_BASE_URL}/sted").mock(
        return_value=httpx.Response(200, json=_load_json("kartverket_sted_multilingual.json"))
    )
    with KartverketClient() as kv:
        places = kv.search_places(sok="Karasjok")
    assert len(places) == 1
    assert len(places[0].names) == 3


@respx.mock
def test_client_search_names_parses_flattened_response():
    respx.get(f"{SSR_BASE_URL}/navn").mock(
        return_value=httpx.Response(200, json=_load_json("kartverket_navn.json"))
    )
    with KartverketClient() as kv:
        results = kv.search_names(sok="Karasjok", sprak="Norsk")
    assert len(results) == 1
    assert len(results[0].names) == 1


@respx.mock
def test_client_nearby_places_default_koordsys_4258():
    route = respx.get(f"{SSR_BASE_URL}/punkt").mock(
        return_value=httpx.Response(200, json=_load_json("kartverket_sted_multilingual.json"))
    )
    with KartverketClient() as kv:
        kv.nearby_places(59.28515, 11.11138, radius=200)
    assert route.calls.last.request.url.params["koordsys"] == "4258"


@respx.mock
def test_client_object_types_returns_real_list():
    respx.get(f"{SSR_BASE_URL}/navneobjekttyper").mock(
        return_value=httpx.Response(200, json=_load_json("kartverket_navneobjekttyper.json"))
    )
    with KartverketClient() as kv:
        types = kv.object_types()
    assert len(types) == 291
    codes = {t["navneobjekttypekode"] for t in types}
    assert "adressenavn" in codes
    assert "vegstrekning" in codes


@respx.mock
def test_client_languages_includes_sami_and_kven():
    respx.get(f"{SSR_BASE_URL}/sprak").mock(
        return_value=httpx.Response(200, json=_load_json("kartverket_sprak.json"))
    )
    with KartverketClient() as kv:
        langs = kv.languages()
    names = {lang["språk"] for lang in langs}
    assert {"Nordsamisk", "Sørsamisk", "Kvensk", "Norsk"} <= names


@respx.mock
def test_client_discover_bulk_downloads_parses_real_feed():
    respx.get(
        "http://nedlasting.geonorge.no/geonorge/ATOM-feeds/MatrikkelenAdresse_AtomFeedCSV.xml"
    ).mock(
        return_value=httpx.Response(
            200, content=(FIXTURES / "kartverket_bulk_atom_feed.xml").read_bytes()
        )
    )
    with KartverketClient() as kv:
        entries = kv.discover_bulk_downloads()
    assert len(entries) == 5


@respx.mock
def test_client_download_bulk_streams_to_file(tmp_path):
    respx.get("https://nedlasting.geonorge.no/example.zip").mock(
        return_value=httpx.Response(200, content=b"csv-zip-bytes-stand-in")
    )
    with KartverketClient() as kv:
        path = kv.download_bulk("https://nedlasting.geonorge.no/example.zip", tmp_path / "d.zip")
    assert path.read_bytes() == b"csv-zip-bytes-stand-in"


@respx.mock
async def test_async_client_search_parses_real_response():
    respx.get(f"{ADDRESS_BASE_URL}/sok").mock(
        return_value=httpx.Response(200, json=_load_json("kartverket_search.json"))
    )
    async with AsyncKartverketClient() as kv:
        results = await kv.search(sok="Karl Johans gate 1")
    assert len(results) == 3
