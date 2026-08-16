"""Tests for streetworks.common.from_anncsu - built directly against
:class:`~streetworks.anncsu.models.Odonimo` objects, no HTTP mocking
needed here."""

from __future__ import annotations

from streetworks.anncsu.models import Odonimo
from streetworks.common import from_anncsu
from streetworks.common.gazetteer import GeometryGrade
from streetworks.common.models import Identifier, SourceGrade

_REAL_ODONIMO = Odonimo(
    progressivo_nazionale=375741,
    codice_comune="A008",
    codice_istat="068001",
    codice_comunale="27",
    odonimo="CONTRADA COLLE COLUCCI",
    localita=None,
    totale_accessi=1,
    denominazione_lingua1=None,
    denominazione_lingua2=None,
    raw={"ODONIMO": "CONTRADA COLLE COLUCCI"},
)


def test_from_anncsu_converts_to_a_street_with_no_geometry():
    street = from_anncsu(_REAL_ODONIMO)

    assert street.names[0].value == "CONTRADA COLLE COLUCCI"
    assert street.geometry is None
    assert street.geometry_grade == GeometryGrade.ABSENT  # a real, documented state
    assert street.territory == "Italy"
    assert street.source_grade == SourceGrade.REGISTER
    assert street.raw is _REAL_ODONIMO


def test_from_anncsu_carries_both_real_municipality_identifiers():
    street = from_anncsu(_REAL_ODONIMO)

    by_scheme = {i.scheme: i for i in street.identifiers}
    assert by_scheme["progressivo_nazionale"] == Identifier(
        scheme="progressivo_nazionale", value="375741"
    )
    assert by_scheme["codice_comune_belfiore"] == Identifier(
        scheme="codice_comune_belfiore", value="A008", scope="ANNCSU"
    )
    assert by_scheme["codice_istat"] == Identifier(
        scheme="codice_istat", value="068001", scope="ANNCSU"
    )
    assert by_scheme["codice_comunale"] == Identifier(
        scheme="codice_comunale", value="27", scope="068001"
    )


def test_from_anncsu_omits_codice_comunale_identifier_when_genuinely_absent():
    gap = Odonimo(
        progressivo_nazionale=375692,
        codice_comune="A008",
        codice_istat="068001",
        codice_comunale=None,  # a real, genuine gap
        odonimo="LOCALITA' COLLE COCILIERI",
        localita=None,
        totale_accessi=0,
        denominazione_lingua1=None,
        denominazione_lingua2=None,
        raw={},
    )
    street = from_anncsu(gap)
    schemes = {i.scheme for i in street.identifiers}
    assert "codice_comunale" not in schemes


def test_from_anncsu_never_emits_segment_refs():
    # A pure name registry - no street geometry beyond nothing at all,
    # so there is nothing to reference as a segment.
    street = from_anncsu(_REAL_ODONIMO)
    assert street.segment_refs == ()
