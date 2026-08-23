"""Tests for streetworks.poland - wiring only. Converter behaviour is
tested in test_common_poland.py against the same real fixture.

Fixture is real GDDKiA disruption XML (tests/fixtures/
poland_utrudnienia.xml), trimmed from a live pull 2026-08-23 of the
genuinely keyless https://www.archiwum.gddkia.gov.pl/dane/zima_html/
utrdane.xml feed - see streetworks.poland.client's own module
docstring for the full investigation. Four real records: two
typ="U" (roadworks - one with coordinates, one without), one typ="I"
(incident, not roadworks), one typ="W" (accident, not roadworks).
"""

from pathlib import Path

import httpx
import respx

from streetworks.poland import BASE_URL, PolandClient

FIXTURE = (Path(__file__).parent / "fixtures" / "poland_utrudnienia.xml").read_bytes()


@respx.mock
def test_iter_events_yields_every_real_record_unfiltered():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE))
    with PolandClient() as client:
        records = list(client.iter_events())
    assert len(records) == 4
    assert {r["typ"] for r in records} == {"U", "I", "W"}


@respx.mock
def test_iter_roadworks_filters_to_typ_u():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE))
    with PolandClient() as client:
        records = list(client.iter_roadworks())
    assert len(records) == 2
    assert all(r["typ"] == "U" for r in records)
    assert {r["nr_drogi"] for r in records} == {"A1", "A18"}
