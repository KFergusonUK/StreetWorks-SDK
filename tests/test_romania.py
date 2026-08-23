"""Tests for streetworks.romania - wiring only. Converter behaviour is
tested in test_common_romania.py against the same real fixture.

Fixture is real CNAIR "Dispecerat Online" HTML (tests/fixtures/
romania_dispecerat.html), trimmed from a live pull 2026-08-23 of the
genuinely keyless https://dispecerat.andnet.ro/ dispatch board - see
streetworks.romania.client's own module docstring for the full
investigation, including why this is HTML-scraped (no separate API
exists) and the real higher-failure-rate caveat that carries. Three
real records: one from section "1.1" (short-duration works, roadworks),
one from section "4" (ongoing closures - real but not roadworks-
exclusive by its own title, excluded from iter_roadworks()), one from
section "6" (rehabilitation/modernization/maintenance/repair works,
roadworks).
"""

from pathlib import Path

import httpx
import respx

from streetworks.romania import BASE_URL, RomaniaClient

FIXTURE = (Path(__file__).parent / "fixtures" / "romania_dispecerat.html").read_text(
    encoding="utf-8"
)


@respx.mock
def test_iter_events_yields_every_real_record_unfiltered():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=FIXTURE))
    with RomaniaClient() as client:
        records = list(client.iter_events())
    assert len(records) == 3
    assert {r["INDICATIV DRUM"] for r in records} == {"A1", "A7", "A2"}


@respx.mock
def test_iter_roadworks_only_includes_the_two_works_sections():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=FIXTURE))
    with RomaniaClient() as client:
        records = list(client.iter_roadworks())
    assert len(records) == 2
    assert {r["INDICATIV DRUM"] for r in records} == {"A1", "A2"}
    # The real section-4 record (A7) is excluded - not roadworks-exclusive
    # by its own section title.
    assert "A7" not in {r["INDICATIV DRUM"] for r in records}


@respx.mock
def test_parser_degrades_to_empty_on_unrecognised_markup():
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, text="<html><body>no tables here</body></html>")
    )
    with RomaniaClient() as client:
        assert list(client.iter_events()) == []
        assert list(client.iter_roadworks()) == []
