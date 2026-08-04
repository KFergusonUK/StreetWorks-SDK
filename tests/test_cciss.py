"""Tests for the CCISS (Italy) traffic bulletin RSS provider.

``cciss_rss.xml`` holds 8 REAL items trimmed from a real, unauthenticated
pull of https://www.cciss.it/rss (2026-08-03) - chosen to cover the real
shapes found live: weather with no temporal clause ("pioggia"), roadworks
with no temporal clause ("lavori"), a single-start-time breakdown, a
single-start-time roadworks item, a real multi-day roadworks range
("tratto chiuso causa lavori dalle 21:35 del 3 alle 05:00 del 4 agosto
2026"), a single-location ("a ...") roadworks item, a same-day time-range
demonstration (non-roadworks), and a weather-caused incident
(non-roadworks) - not synthetic.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx
import respx

from streetworks.cciss import RSS_URL, CcissClient
from streetworks.cciss.client import parse_feed
from streetworks.common import from_cciss
from streetworks.common.models import DateConfidence, SourceGrade

CCISS_RSS = (Path(__file__).parent / "fixtures" / "cciss_rss.xml").read_text(encoding="utf-8")


def _by_road_and_type(items, road: str, event_type: str):
    return next(i for i in items if i.road == road and i.event_type == event_type)


def test_weather_item_has_no_temporal_clause_and_is_not_roadworks():
    items = parse_feed(CCISS_RSS)
    item = _by_road_and_type(items, "A5 Torino-Courmayeur", "pioggia")
    assert item.is_roadworks is False
    assert item.start is None
    assert item.location_from == "Svincolo Pont Saint Martin"
    assert item.location_to == "Svincolo Chatillon-Saint Vincent"


def test_roadworks_item_with_no_temporal_clause():
    """A real 'lavori' item with no stated start time - never fabricated."""
    items = parse_feed(CCISS_RSS)
    item = _by_road_and_type(items, "A5 Torino-Courmayeur", "lavori")
    assert item.is_roadworks is True
    assert item.start is None
    assert item.direction == "Courmayeur"


def test_breakdown_item_is_not_roadworks_but_has_a_start_time():
    items = parse_feed(CCISS_RSS)
    item = _by_road_and_type(items, "A16 Napoli-Canosa", "veicolo fermo o in avaria")
    assert item.is_roadworks is False
    assert item.start == datetime(2026, 8, 3, 21, 37)


def test_compound_roadworks_event_type_is_classified_correctly():
    """'personale su strada causa lavori' (personnel on road due to works)
    - a real compound clause, classified as roadworks via the 'lavori'
    substring, matching the real evidenced allowlist."""
    items = parse_feed(CCISS_RSS)
    item = _by_road_and_type(items, "A12 Genova-Rosignano", "personale su strada causa lavori")
    assert item.is_roadworks is True
    assert item.start == datetime(2026, 8, 3, 21, 36)


def test_real_multi_day_roadworks_range():
    """'dalle 21:35 del 3 alle 05:00 del 4 agosto 2026' - day 3 to day 4,
    month/year stated once, real live shape."""
    items = parse_feed(CCISS_RSS)
    item = _by_road_and_type(
        items, "R01 Ramo Verde Tangenziale Di Bologna", "tratto chiuso causa lavori"
    )
    assert item.is_roadworks is True
    assert item.start == datetime(2026, 8, 3, 21, 35)
    assert item.end == datetime(2026, 8, 4, 5, 0)
    assert item.location_from == "Allacciamento Tangenziale Di Bologna"
    assert item.location_to == "Svincolo SS 9 Via Emilia"


def test_single_location_roadworks_item():
    items = parse_feed(CCISS_RSS)
    item = _by_road_and_type(
        items, "R01 Ramo Verde Tangenziale Di Bologna", "rampa di accesso chiusa causa lavori"
    )
    assert item.is_roadworks is True
    assert item.location_at == "Svincolo S.Giovanni In Persiceto"
    assert item.location_from is None and item.location_to is None
    assert item.direction == "Bologna Borgo Panigale"


def test_demonstration_is_not_roadworks_same_day_time_range():
    items = parse_feed(CCISS_RSS)
    item = _by_road_and_type(items, "Pesaro Viale Don Giovanni Minzoni", "manifestazione")
    assert item.is_roadworks is False
    assert item.start == datetime(2026, 8, 23, 21, 30)
    assert item.end == datetime(2026, 8, 23, 22, 15)
    assert item.location_at == "Viale Marsala"


def test_weather_caused_incident_is_not_roadworks():
    items = parse_feed(CCISS_RSS)
    item = _by_road_and_type(
        items, "A1 Roma-Napoli", "veicoli scortati per maltempo causa perdita di carico"
    )
    assert item.is_roadworks is False


def test_raw_title_and_description_always_preserved():
    items = parse_feed(CCISS_RSS)
    item = items[0]
    assert item.title == "A5 Torino-Courmayeur"
    assert "pioggia" in item.description


@respx.mock
def test_client_fetches_and_parses():
    respx.get(RSS_URL).mock(return_value=httpx.Response(200, content=CCISS_RSS.encode()))
    with CcissClient() as cciss:
        items = cciss.fetch()
    assert len(items) == 8
    assert sum(1 for i in items if i.is_roadworks) == 4


def test_client_requires_no_credentials():
    CcissClient()


# --------------------------------------------------------------------------- #
# Converter
# --------------------------------------------------------------------------- #


def test_from_cciss_wraps_a_single_thin_site():
    items = parse_feed(CCISS_RSS)
    item = _by_road_and_type(items, "A12 Genova-Rosignano", "personale su strada causa lavori")
    works = from_cciss(item)
    assert len(works.sites) == 1
    assert works.territory == "Italy"
    assert works.source_grade == SourceGrade.TRAVELLER_INFO
    site = works.sites[0]
    assert site.works_type == "personale su strada causa lavori"
    assert site.date_confidence is DateConfidence.UNKNOWN
    assert site.proposed_start == datetime(2026, 8, 3, 21, 36)
    assert "A12 Genova-Rosignano" in site.location_description
    assert "Svincolo Genova Nervi" in site.location_description


def test_from_cciss_no_geometry():
    items = parse_feed(CCISS_RSS)
    works = from_cciss(items[0])
    assert works.coordinate is None
    assert works.sites[0].coordinate is None


def test_from_cciss_never_filters_by_roadworks():
    """Filtering happens at the caller's own choice via item.is_roadworks -
    from_cciss() itself converts whatever it's given, the same discipline
    from_trafficwatchni/from_trafficwales already established."""
    items = parse_feed(CCISS_RSS)
    weather_item = _by_road_and_type(items, "A5 Torino-Courmayeur", "pioggia")
    works = from_cciss(weather_item)
    assert works.sites[0].works_type == "pioggia"
