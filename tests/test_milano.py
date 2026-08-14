"""Tests for the Milan (Avvisi di manomissione) adapter.

Credential-free, live-verified 2026-08-14 - see the module docstring in
``streetworks.milano.client``. ``milano_manomissione_live_pull.json``
holds 4 REAL features trimmed from a real, unauthenticated pull (139
total): one water-utility notice from 2021 (the one real historical
outlier in the live data - kept as-is, not dropped), one electricity,
one gas, and one sewage notice, all current/2026. Not synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_milano
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.milano import MANOMISSIONE_URL, MilanoClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "milano_manomissione_live_pull.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())
FEATURES = FIXTURE_JSON["features"]


def _by_reference(features: list[dict], reference: str) -> dict:
    for f in features:
        if f["properties"]["Numero di protocollo ingresso"] == reference:
            return f
    raise AssertionError(f"no feature with reference {reference!r}")


def _mock_feed() -> None:
    respx.get(MANOMISSIONE_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_returns_every_feature_unfiltered():
    _mock_feed()
    with MilanoClient() as milano:
        features = list(milano.iter_roadworks())
    assert len(features) == len(FEATURES)


def test_client_requires_no_credentials():
    MilanoClient()


# --------------------------------------------------------------------------- #
# Converter - one Works per feature, no grouping
# --------------------------------------------------------------------------- #


def test_from_milano_produces_one_works_per_feature_no_grouping():
    works_list = from_milano(FEATURES)
    assert len(works_list) == len(FEATURES)
    assert all(len(w.sites) == 1 for w in works_list)


def test_from_milano_reference_is_protocol_number():
    works_list = from_milano(FEATURES)
    refs = {w.reference for w in works_list}
    assert "449600/2026" in refs


def test_from_milano_coordinate_is_flipped_to_lat_lon():
    """Genuine WGS84 (not projected, unlike Oslo/Helsinki) - GeoJSON's
    (lon, lat) must be flipped to this SDK's (lat, lon)."""
    feature = _by_reference(FEATURES, "449600/2026")
    works_list = from_milano([feature])
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.crs == "EPSG:4326"
    # real Milan latitude is ~45.x, longitude ~9.x - lat must come first.
    assert 44 < coord.value[0] < 46
    assert 8 < coord.value[1] < 10


def test_from_milano_works_type_preserves_source_capitalisation_verbatim():
    """The source itself is inconsistent ("Acqua Potabile" vs "Acqua
    potabile") - this converter must not normalise it away."""
    feature_2026 = _by_reference(FEATURES, "449600/2026")
    assert from_milano([feature_2026])[0].sites[0].works_type == "Elettricità"


def test_from_milano_promoter_is_concession_holder():
    feature = _by_reference(FEATURES, "449600/2026")
    works_list = from_milano([feature])
    assert works_list[0].promoter is not None


def test_from_milano_territory_and_administrative_area():
    works_list = from_milano(FEATURES)
    assert all(w.territory == "Italy" for w in works_list)
    assert all(w.administrative_area == "Comune di Milano" for w in works_list)
    assert all(w.source_grade == SourceGrade.REGISTER for w in works_list)


def test_from_milano_date_confidence_is_always_estimated():
    """No explicit status field exists - only planned dates."""
    works_list = from_milano(FEATURES)
    assert all(
        s.date_confidence is DateConfidence.ESTIMATED for w in works_list for s in w.sites
    )


def test_from_milano_historical_outlier_is_kept_not_dropped():
    """A real 2021 row (already long past-dated) must still convert
    cleanly, not be silently dropped or reinterpreted."""
    feature = _by_reference(FEATURES, "300240/2021")
    works_list = from_milano([feature])
    assert len(works_list) == 1
    site = works_list[0].sites[0]
    assert site.proposed_start is not None
    assert site.proposed_start.year == 2021


def test_from_milano_street_ref_is_never_populated():
    works_list = from_milano(FEATURES)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_milano_location_description_combines_street_and_number():
    feature = _by_reference(FEATURES, "449600/2026")
    works_list = from_milano([feature])
    desc = works_list[0].sites[0].location_description
    assert desc is not None
    assert "Nome via" not in desc  # sanity: real value substituted, not the key name
