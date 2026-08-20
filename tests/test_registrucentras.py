"""Tests for streetworks.registrucentras - wiring only. See
streetworks.registrucentras.client's own module docstring for the live
evidence behind each real behaviour covered here (the stable
version-less URL, and why no pagination is needed)."""

from __future__ import annotations

import httpx
import respx

from streetworks.registrucentras import BASE_URL, RegistruCentrasStreetsClient


@respx.mock
def test_iter_streets_needs_no_credentials():
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200, json={"_data": [{"gat_kodas": 1, "pavadinimas": "Test g."}]}
        )
    )
    with RegistruCentrasStreetsClient() as rc:
        rows = list(rc.iter_streets())
    assert len(rows) == 1


@respx.mock
def test_iter_streets_yields_every_real_row_in_one_request():
    route = respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "_data": [
                    {"gat_kodas": 1, "pavadinimas": "Pirma g."},
                    {"gat_kodas": 2, "pavadinimas": "Antra g."},
                ]
            },
        )
    )
    with RegistruCentrasStreetsClient() as rc:
        rows = list(rc.iter_streets())
    assert [r["pavadinimas"] for r in rows] == ["Pirma g.", "Antra g."]
    assert route.call_count == 1
