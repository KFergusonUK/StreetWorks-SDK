"""Tests for streetworks.common.from_datavia.

``datavia_streetlines_durham.json`` and ``datavia_esustreets_durham.json``
are real DataVIA responses (Basic-auth, Durham-scoped credentials, captured
live this session - see docs/gazetteer-field-dump.md). Real fixture values
are local to Durham; field *shapes* are national (confirmed via WFS
``DescribeFeatureType``, not authority-specific).
``datavia_streetlines_bilingual_synthetic.json`` is hand-constructed
(Durham has no Welsh street names) purely to exercise the bilingual path -
its own ``_fixture_note`` field says so.
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, Identifier, from_datavia

FIXTURES = Path(__file__).parent / "fixtures"


def _features(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["features"]


def test_real_streetlines_feature_becomes_a_street_with_esu_segment_refs():
    features = {f["properties"]["usrn"]: f for f in _features("datavia_streetlines_durham.json")}
    church_street = from_datavia(features[11713561])

    assert church_street.identifiers == (Identifier(scheme="usrn", value="11713561"),)
    assert church_street.name == "CHURCH STREET"
    assert church_street.names[0].language == "eng"
    assert church_street.geometry_grade is GeometryGrade.PUBLISHED
    assert len(church_street.geometry.parts) == 3  # matches the 3 real esuids
    assert len(church_street.segment_refs) == 3
    assert Identifier(scheme="esu", value="4276210541888") in church_street.segment_refs
    assert church_street.as_at is not None  # from real last_update_date


def test_real_esustreets_feature_proves_many_to_many_street_segment():
    # esuid=4276210541888 is real: one physical ESU serving two distinct
    # designated streets, Church Street (11713561) and Church Street
    # Villas (11713562) - confirmed live, the exact evidence this design
    # brief cites for why Segment is independent of Street.
    features = {f["properties"]["esuid"]: f for f in _features("datavia_esustreets_durham.json")}
    segment = from_datavia(features[4276210541888])

    assert segment.identifiers == (Identifier(scheme="esu", value="4276210541888"),)
    assert set(segment.street_refs) == {
        Identifier(scheme="usrn", value="11713561"),
        Identifier(scheme="usrn", value="11713562"),
    }
    assert segment.street_type.code == "C98"
    assert segment.names == ()  # ESUStreets carries no name field at all


def test_esustreets_single_usrn_segment_has_one_street_ref():
    features = {f["properties"]["esuid"]: f for f in _features("datavia_esustreets_durham.json")}
    segment = from_datavia(features[4276410541965])
    assert segment.street_refs == (Identifier(scheme="usrn", value="11713561"),)


def test_bilingual_synthetic_fixture_produces_two_names():
    # Durham has no Welsh street names for real - this fixture is
    # constructed, per its own _fixture_note, to exercise this path.
    feature = _features("datavia_streetlines_bilingual_synthetic.json")[0]
    street = from_datavia(feature)
    assert len(street.names) == 2
    assert street.names[0].value == "HIGH STREET"
    assert street.names[0].language == "eng"
    assert street.names[1].value == "STRYD FAWR"
    assert street.names[1].language == "cym"


def test_bilingual_synthetic_fixture_multilinestring_geometry_has_two_parts():
    feature = _features("datavia_streetlines_bilingual_synthetic.json")[0]
    street = from_datavia(feature)
    assert len(street.geometry.parts) == 2
    assert street.geometry.crs  # stated, not silently dropped
