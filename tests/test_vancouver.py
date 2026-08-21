"""Tests for streetworks.vancouver - wiring only. Converter behaviour is
tested in test_common_vancouver.py against the same real fixtures.
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.vancouver import (
    CURRENT_CLOSURES_DATASET,
    UNDER_CONSTRUCTION_DATASET,
    UPCOMING_DATASET,
    VancouverClient,
)


def _fixture(name: str) -> dict:
    return json.loads(
        (Path(__file__).parent / "fixtures" / f"vancouver_{name}.json").read_text(encoding="utf-8")
    )


@respx.mock
def test_iter_current_closures_yields_real_records():
    respx.get(url__regex=rf".*/{CURRENT_CLOSURES_DATASET}/records").mock(
        return_value=httpx.Response(200, json=_fixture("current_closures"))
    )
    with VancouverClient() as vancouver:
        records = list(vancouver.iter_current_closures())
    assert len(records) == 3


@respx.mock
def test_iter_under_construction_yields_real_records():
    respx.get(url__regex=rf".*/{UNDER_CONSTRUCTION_DATASET}/records").mock(
        return_value=httpx.Response(200, json=_fixture("under_construction"))
    )
    with VancouverClient() as vancouver:
        records = list(vancouver.iter_under_construction())
    assert len(records) == 2


@respx.mock
def test_iter_upcoming_yields_real_records():
    respx.get(url__regex=rf".*/{UPCOMING_DATASET}/records").mock(
        return_value=httpx.Response(200, json=_fixture("upcoming"))
    )
    with VancouverClient() as vancouver:
        records = list(vancouver.iter_upcoming())
    assert len(records) == 2
