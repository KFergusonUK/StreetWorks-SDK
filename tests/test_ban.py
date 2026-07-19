"""Tests for the France BAN (Base Adresse Nationale) gazetteer adapter.

Fixtures are real, trimmed:

* ``ban_search_housenumbers.json`` / ``ban_search_street.json`` /
  ``ban_reverse.json`` - live GETs against ``data.geopf.fr/geocodage``,
  2026-07.
* ``ban_search_cross_check.json`` / ``ban_bulk_csv_bal_sample.csv`` share one
  real address (267 Le Mas Renouard, Allenc, Lozère) so the API's ``banId``
  and the bulk ``csv-bal`` file's ``uid_adresse`` can be checked as the same
  identifier, not just similarly-shaped ones (see
  ``streetworks.ban.models``).
* ``ban_bulk_csv_bal_sample.csv`` / ``ban_bulk_csv_sample.csv`` are real
  rows from the Lozère (48) and Finistère (29) département bulk files -
  Finistère for the accented "Impasse des Chênes" grouping (6 real
  addresses, same toponyme prefix) and a real ``suffixe="bis"``; Lozère for
  the ``id_fantoir``/TOPO-code cross-reference (``48003_C365`` ->
  DGFiP TOPO's ``code_dep=48/code_commune=003/code_voie=C365``, confirmed
  live to return ``libelle="LE MAS POUGET"``, matching BAN's own
  ``nom_voie``).
"""

import csv
import gzip
import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.ban import AsyncBANClient, BANClient, bulk_url, iter_addresses, iter_addresses_csv
from streetworks.ban.client import GEOCODING_BASE_URL
from streetworks.ban.models import address_from_api_feature, address_from_bal_row
from streetworks.exceptions import RequestValidationError

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Model parsing - the geocoding API shape
# --------------------------------------------------------------------------- #


def test_address_from_api_feature_housenumber():
    feature = _load_json("ban_search_housenumbers.json")["features"][0]
    address = address_from_api_feature(feature)
    assert address.id == "75101_4461_00008"
    assert address.ban_id == "17755936-2d91-4f2d-9ceb-9c77bce57eda"
    assert address.toponyme_id == "75101_4461"
    assert address.housenumber == "8"
    assert address.street == "Rue des Halles"
    assert address.commune_insee == "75101"
    assert address.commune_nom == "Paris"
    assert address.postcode == "75001"
    assert address.lon == pytest.approx(2.347222)
    assert address.lat == pytest.approx(48.859393)
    assert address.raw is feature


def test_address_from_api_feature_accented_street_name():
    feature = _load_json("ban_search_housenumbers.json")["features"][1]
    address = address_from_api_feature(feature)
    assert address.street == "Rue Hallé"


def test_address_from_api_feature_street_type_has_no_housenumber():
    """A ``type="street"`` result (querying a street name with no number)
    has no housenumber - real live response, not synthesised - and its own
    ``id`` is already toponyme-level, matching the prefix housenumber rows
    on the same street derive to."""
    feature = _load_json("ban_search_street.json")["features"][0]
    address = address_from_api_feature(feature)
    assert address.housenumber is None
    assert address.id == "75101_4461"
    assert address.toponyme_id == "75101_4461"  # unchanged - no numero to strip


# --------------------------------------------------------------------------- #
# Model parsing - the csv-bal bulk shape, and cross-format identity
# --------------------------------------------------------------------------- #


def _bal_rows() -> list[dict]:
    with open(FIXTURES / "ban_bulk_csv_bal_sample.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def test_api_ban_id_matches_bulk_uid_adresse_uuid():
    """The same real address (267 Le Mas Renouard, Allenc) returns the same
    permanent identifier from both access routes - confirmed live, not
    assumed from matching field shapes."""
    api_feature = _load_json("ban_search_cross_check.json")["features"][0]
    api_address = address_from_api_feature(api_feature)
    bal_row = next(r for r in _bal_rows() if r["cle_interop"] == "48003_c436_00267")
    bal_address = address_from_bal_row(bal_row)
    assert api_address.id == bal_address.id == "48003_c436_00267"
    assert api_address.ban_id == bal_address.ban_id == "26377563-1431-4cc5-8f8e-da743bd849d9"
    assert api_address.toponyme_id == bal_address.toponyme_id == "48003_c436"


def test_toponyme_id_groups_real_addresses_on_the_same_street():
    """6 real addresses on Impasse des Chênes (Argol, Finistère) - the
    derived toponyme_id, not a literal BAN field (see models.py), groups
    them cleanly."""
    addresses = [address_from_bal_row(r) for r in _bal_rows()]
    chenes = [a for a in addresses if a.street == "Impasse des Chênes"]
    assert len(chenes) == 6
    assert {a.toponyme_id for a in chenes} == {"29001_428m6b"}
    assert {a.housenumber for a in chenes} == {"2", "3", "4", "5", "6", "7"}


def test_bal_suffixe_bis_preserved():
    row = next(r for r in _bal_rows() if r["cle_interop"] == "29001_0015_00004_bis")
    address = address_from_bal_row(row)
    assert address.housenumber == "4"
    assert address.suffix == "bis"
    assert address.toponyme_id == "29001_0015"
    assert address.street == "Place de l’Eglise"


def test_bal_format_has_no_postcode_column():
    """csv-bal genuinely has no postcode column (postcodes don't map 1:1 to
    communes in France) - never guessed, always None from this route."""
    row = next(r for r in _bal_rows() if r["cle_interop"] == "48003_c436_00267")
    address = address_from_bal_row(row)
    assert address.postcode is None
    assert "code_postal" not in row  # the fixture itself proves the column is absent


def test_bal_commune_deleguee_reaches_raw():
    row = next(r for r in _bal_rows() if r["cle_interop"] == "29003_6jax56_00001")
    address = address_from_bal_row(row)
    assert address.commune_nom == "Audierne"
    assert address.raw["commune_deleguee_nom"] == "Audierne"


# --------------------------------------------------------------------------- #
# Model parsing - the plain csv bulk shape, and the id_fantoir/TOPO finding
# --------------------------------------------------------------------------- #


def test_csv_format_has_no_ban_id():
    addresses = list(iter_addresses_csv(FIXTURES / "ban_bulk_csv_sample.csv"))
    assert all(a.ban_id is None for a in addresses)


def test_csv_format_id_fantoir_is_topo_length_not_old_fantoir_length():
    """Despite the column's name, every populated real value is 9 characters
    (commune INSEE + 4-char street code) once the underscore is stripped -
    the DGFiP TOPO-era length, confirmed against a real département sample,
    never the old 10-character FANTOIR one - see models.py's module
    docstring for the confirmed-live BAN/TOPO join this enables."""
    addresses = list(iter_addresses_csv(FIXTURES / "ban_bulk_csv_sample.csv"))
    populated = [a for a in addresses if a.raw["id_fantoir"]]
    assert populated  # the fixture includes at least one real populated row
    for address in populated:
        stripped = address.raw["id_fantoir"].replace("_", "")
        assert len(stripped) == 9, address.raw["id_fantoir"]


def test_csv_format_id_fantoir_matches_toponyme_id():
    addresses = iter_addresses_csv(FIXTURES / "ban_bulk_csv_sample.csv")
    row = next(a for a in addresses if a.id == "48003_c365_00110")
    assert row.raw["id_fantoir"] == "48003_C365"
    assert row.toponyme_id == "48003_c365"  # same commune+street-code, case aside


def test_csv_format_accented_name_round_trips():
    addresses = list(iter_addresses_csv(FIXTURES / "ban_bulk_csv_sample.csv"))
    chenes = next(a for a in addresses if a.id == "29001_428m6b_00004")
    assert chenes.street == "Impasse des Chênes"
    assert chenes.raw["nom_afnor"] == "IMPASSE DES CHENES"  # ASCII-folded sibling, also real


# --------------------------------------------------------------------------- #
# reader.py - streaming, gzip transparency, bulk_url()
# --------------------------------------------------------------------------- #


def test_iter_addresses_streams_bal_fixture():
    addresses = list(iter_addresses(FIXTURES / "ban_bulk_csv_bal_sample.csv"))
    assert len(addresses) == 9


def test_iter_addresses_accepts_gzip(tmp_path):
    gz_path = tmp_path / "sample.csv.gz"
    raw = (FIXTURES / "ban_bulk_csv_bal_sample.csv").read_bytes()
    with gzip.open(gz_path, "wb") as f:
        f.write(raw)
    addresses = list(iter_addresses(gz_path))
    assert len(addresses) == 9


def test_iter_addresses_accepts_open_stream():
    with open(FIXTURES / "ban_bulk_csv_bal_sample.csv", encoding="utf-8", newline="") as f:
        addresses = list(iter_addresses(f))
    assert len(addresses) == 9


def test_bulk_url_departement_and_national():
    assert bulk_url("75") == (
        "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv-bal/adresses-75.csv.gz"
    )
    assert bulk_url("2A", format="csv") == (
        "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-2A.csv.gz"
    )
    assert bulk_url() == (
        "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv-bal/adresses-france.csv.gz"
    )


# --------------------------------------------------------------------------- #
# client.py - search/reverse (respx-mocked) and streamed downloads
# --------------------------------------------------------------------------- #


@respx.mock
def test_client_search_parses_real_response():
    respx.get(f"{GEOCODING_BASE_URL}/search").mock(
        return_value=httpx.Response(200, json=_load_json("ban_search_housenumbers.json"))
    )
    with BANClient() as ban:
        results = ban.search("8 rue des halles paris")
    assert len(results) == 3
    assert results[0].id == "75101_4461_00008"
    assert results[0].ban_id == "17755936-2d91-4f2d-9ceb-9c77bce57eda"


@respx.mock
def test_client_search_passes_query_params():
    route = respx.get(f"{GEOCODING_BASE_URL}/search").mock(
        return_value=httpx.Response(200, json=_load_json("ban_search_street.json"))
    )
    with BANClient() as ban:
        ban.search("Rue des Halles", citycode="75101", limit=5, type="street")
    request = route.calls.last.request
    assert request.url.params["q"] == "Rue des Halles"
    assert request.url.params["citycode"] == "75101"
    assert request.url.params["type"] == "street"


@respx.mock
def test_client_reverse_parses_real_response():
    respx.get(f"{GEOCODING_BASE_URL}/reverse").mock(
        return_value=httpx.Response(200, json=_load_json("ban_reverse.json"))
    )
    with BANClient() as ban:
        results = ban.reverse(2.347222, 48.859393)
    assert len(results) == 3
    assert results[0].raw["properties"]["distance"] == 0


@respx.mock
def test_client_search_error_maps_to_request_validation_error():
    """Real live shape (missing ``q``): {"code":400,"message":"Failed
    parsing query","detail":[...]}."""
    error_body = {
        "code": 400,
        "message": "Failed parsing query",
        "detail": ["q: required param"],
    }
    respx.get(f"{GEOCODING_BASE_URL}/search").mock(
        return_value=httpx.Response(400, json=error_body)
    )
    with BANClient() as ban, pytest.raises(RequestValidationError, match="Failed parsing query"):
        ban.search("")


@respx.mock
def test_client_download_departement_streams(tmp_path):
    respx.get(
        "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv-bal/adresses-48.csv.gz"
    ).mock(return_value=httpx.Response(200, content=b"gzip-bytes-stand-in"))
    with BANClient() as ban:
        path = ban.download_departement("48", tmp_path / "dept48.csv.gz")
    assert path.read_bytes() == b"gzip-bytes-stand-in"


@respx.mock
async def test_async_client_search_parses_real_response():
    respx.get(f"{GEOCODING_BASE_URL}/search").mock(
        return_value=httpx.Response(200, json=_load_json("ban_search_housenumbers.json"))
    )
    async with AsyncBANClient() as ban:
        results = await ban.search("8 rue des halles paris")
    assert len(results) == 3
