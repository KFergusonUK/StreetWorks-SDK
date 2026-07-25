"""Typed models for Via Lietuva's open roadworks data (data.gov.lt).

:class:`RoadRepair` is one row from the ``Remontas`` ("repairs") table -
the roadworks core of this source, confirmed live (2026-07, 9,762 real
rows spanning 2023-12 through 2027-08, 110 active as of the check date).
Field names here are English translations of the source's genuinely
Lithuanian CSV headers (kept on ``raw`` verbatim); each field's docstring
states its real source column.

Two of the dataset's other three tables were checked and deliberately
**not** modelled here, per this SDK's existing "don't force a non-works
source into ``Works``" rule (the same call already made for UK Police):

- ``Kliutis`` ("obstacle") - road-condition hazards (real descriptions:
  *"Silpna, nelygi kelio danga"* - weak, uneven road surface; *"Dėl
  polaidžio susilpnėjusi kelio danga"* - weakened by spring thaw), not an
  operator's planned works programme. Closer to an incident/condition
  register than roadworks.
- ``Renginys`` ("event") - real content confirmed to be traffic
  restrictions for organised events (car rally stages, closures for
  races), not roadworks at all.

**Real, scattered test data, not filtered by the source**: 25/9,762 real
rows (~0.26%) have an ``aprasymas`` that is plainly a test artefact
(literal ``"test"``/``"Test"``/``"testuojam;"`` - Lithuanian for
"testing" - or the more explicit *"Eismas nedraudžiamas, ribojimas
įvestas tik testavimui dėl maršruto planavimo"*, "traffic not restricted,
this restriction was entered only for testing route planning"), otherwise
structurally identical to a real row (real dates, real coordinates) - not
flagged by any field, not excluded here; a caller wanting to filter these
out has only free-text matching to do it with.

The fourth table, ``KelioAtkarpa`` ("road section"), is real reference
data for state road sections (``numeris``/road number, ``pavadinimas``/
name, a km range) - no restriction/date/coordinate content at all.
Confirmed live: every one of ``RoadRepair.road_id``'s 886 distinct real
values has a matching ``KelioAtkarpa`` row (886/886) - a genuine, working
join, not assumed. This is gazetteer-shaped (street/segment identity), not
roadworks, so it isn't forced into ``Works`` either - see
:func:`~streetworks.vialietuva.parser.parse_road_sections` and
:class:`RoadSection`, kept as a separate, explicitly-not-roadworks lookup
(the same role ``dir_regions``/``provinces`` play for Bison Futé/DGT).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

__all__ = ["RoadRepair", "RoadSection"]

JSON = dict[str, Any]


@dataclass
class RoadRepair:
    """One row from the ``Remontas`` table.

    Coordinates (:attr:`from_point_wkt`, :attr:`to_point_wkt`,
    :attr:`geometry_wkt`) are real WKT, stated in Lithuania's national grid,
    **LKS-94 (EPSG:3346)** - confirmed live from the value ranges (first
    number 6,000,000+, second number 300,000-700,000; genuine WGS84
    latitudes for Lithuania would read ~54-56). **The WKT axis order is
    (Northing, Easting), not the more usual (Easting, Northing)** -
    confirmed from every real sample checked (the first number is always
    in Lithuania's real northing range, the second always in its real
    easting range) - genuinely reversed from what a caller familiar with
    typical projected-CRS WKT would expect, not a formatting quirk. Carried
    through unconverted; see :mod:`streetworks.common.from_vialietuva` for
    how the ``crs`` label is attached.
    """

    work_id: str  # darbo_id
    road_id: str  # kelio_id - joins to RoadSection.road_id, confirmed live
    #: Traffic-direction code - three real values seen (``"AB"``, ``"PR"``,
    #: ``"AT"``); not decoded, same treatment as Alert-C locations elsewhere
    #: in this SDK. eismo_kryptis.
    direction: str | None = None
    km_from: float | None = None  # km_nuo
    km_to: float | None = None  # km_iki
    from_point_wkt: str | None = None  # nuo_koord_lks - always present, 9,762/9,762 live
    to_point_wkt: str | None = None  # iki_koord_lks
    #: The repair's full path, when stated - a real ``MULTILINESTRING``,
    #: present on 6,984/9,762 real rows (71.6%); the remaining rows have a
    #: point only (via :attr:`from_point_wkt`/:attr:`to_point_wkt`).
    #: geometrija.
    geometry_wkt: str | None = None
    #: Always ``True`` on every real row checked (9,762/9,762) - stated,
    #: never seen ``False`` live, so not a meaningful discriminator in
    #: practice despite being a real boolean field. koord_validacija.
    coordinates_validated: bool | None = None
    start: datetime | None = None  # data_nuo - naive, no UTC offset stated
    end: datetime | None = None  # data_iki - empty on 1/9,762 real rows (open-ended)
    #: Whether traffic is still permitted through the works. eismas_leidziamas.
    traffic_allowed: bool | None = None
    #: Severity label, Lithuanian free text (four real values: "Mažai
    #: svarbus"/minor, "Vidutiniškai svarbus"/moderate, "Svarbus"/important,
    #: "Labai svarbus"/very important) - not normalised to an enum, kept as
    #: the source states it. Empty on 124/9,762 real rows. poveikis_eismui.
    impact: str | None = None
    description: str | None = None  # aprasymas - empty on 14/9,762 real rows
    raw: JSON = field(default_factory=dict)


@dataclass
class RoadSection:
    """One row from the ``KelioAtkarpa`` table - state road reference data,
    not roadworks. See module docstring for why this isn't part of
    ``Works``."""

    road_id: str  # kelio_id
    number: str | None = None  # numeris, e.g. "1225" or "D510600800"
    name: str | None = None  # pavadinimas, e.g. "Šlavėnai–Kurkliai II–Kolonija"
    km_from: float | None = None  # km_nuo
    km_to: float | None = None  # km_iki
    raw: JSON = field(default_factory=dict)
