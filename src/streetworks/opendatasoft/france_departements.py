"""French département roadworks - a declarative field-map registry over
:class:`~streetworks.opendatasoft.client.OpenDataSoftClient`, the same
shape :mod:`streetworks.ogc.germany` already established for German
state roadworks (a new field-map entry, not a new converter, for each
new département - :func:`streetworks.common.from_departement_roadworks`
reads the map generically).

**Why this exists alongside Bison Futé.** France's own national
roadworks feed (``streetworks.datex2.BisonFuteClient``) is scoped to
the non-concessionary national road network (the state-run RRN) only -
the majority of the French road network by length, the Routes
Départementales (RD), is each département's own responsibility and
isn't in Bison Futé at all. This is the same real gap Germany's own
state fan-out closed for its own Autobahn-GmbH/Länder split.

Three départements are live, all verified against real data, 2026-08-20:

- **Sarthe** (``227200029_chantiers_routiers``, ``data.sarthe.fr``): 9
  real features, ``LineString`` geometry, structured ISO datetimes with
  an explicit UTC offset on ``date_debut``/``date_fin``. A real, clean
  road/PR-range field (``loc_txt``, e.g. ``"RD 0316 : Du 0+100 au
  1+700"`` - a real French *Point de Repère* kilometre-marker range, the
  standard way French road authorities reference a location on a route,
  not a street address). A real, clean traffic-management status field
  (``mode_exp``, e.g. ``"Alternat"`` - alternating one-way control,
  ``"Route barrée avec déviation"`` - closed with diversion). A real
  promoter (``maitre_ouvrage``, e.g. ``"Télélec Réseaux"``, a network
  operator - not always the département itself).
- **Loire-Atlantique** (``224400028_info-route-departementale``,
  ``data.loire-atlantique.fr``, described as "temps réel"): 21 real
  features, ``Point`` geometry only (no ``geo_shape`` line field
  exists). **No structured dates at all** - ``ligne4`` states a real
  date range as French free text (e.g. ``"Du 18/08/2026 au
  20/08/2026"``), not parsed here (this SDK's "never extract structured
  data from free text" discipline) - every record on this département
  carries ``DateConfidence.UNKNOWN``, honestly, not a bug. The real
  point field is named ``localisation``, not ``geo_point_2d`` like its
  siblings - a real per-dataset naming choice, not a platform standard,
  confirmed live (Sarthe/Hauts-de-Seine both use ``geo_point_2d``).
- **Hauts-de-Seine** (``fr-229200506-travaux-et-projets-sur-voirie-
  departementale``, ``opendata.hauts-de-seine.fr``): 122 real features,
  ``LineString``/``MultiLineString`` geometry. **A genuinely different
  register from its siblings** - a capital-works/infrastructure-project
  register (tramway extensions, cycle-lane programmes), not a day-to-day
  closures feed; its own real ``avancement`` field states a project
  phase (``"Travaux en cours"``/``"Travaux programmés"``/``"Projet à
  l'étude"`` - in progress/programmed/under study), used as
  ``status_field``. **No structured dates here either** - ``date_travaux``
  is real free text, often spanning years (e.g. ``"Travaux
  d'assainissement début 2026 et travaux concessionnaires jusqu'à fin
  2029"``) or ``None`` outright - every record carries
  ``DateConfidence.UNKNOWN``, the same honest gap as Loire-Atlantique.
  ``voie`` genuinely lists several real route numbers per record
  (comma-separated, e.g. ``"RD 13, RD 97, RD 98, RD 106, RD 909,
  RD986, RD 992"``) since one capital-works project can span several
  routes - kept as one real string, never split into a fabricated list.

**A real fourth département was found and set aside, not built -
Corrèze's own WFS is genuinely GML-only** (its ``GetCapabilities``
states only GML output formats, no JSON at all, the same real shape
already handled for Schleswig-Holstein in
:mod:`streetworks.ogc.germany` - not out of scope in principle, just not
built this round; worth a real revisit with the same GML-parsing
approach). **Côtes d'Armor is real, live, and rich (5,292 real
features, a genuine REST API over the Koumoul/data-fair platform) but
doesn't fit this OpenDataSoft-specific field map at all** - a
structurally different platform, tracked separately.

**Licence: all three confirmed "Licence Ouverte / Open Licence"
(Etalab)** - France's own standard open-data licence, the same one
already confirmed for Bison Futé - directly from each dataset's own
catalogue metadata on ``data.gouv.fr``.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx

from .client import OpenDataSoftClient

__all__ = ["DepartementFieldMap", "FIELD_MAPS", "DepartementRoadworksClient"]

JSON = dict[str, Any]

_LICENCE_OUVERTE = "Licence Ouverte / Open Licence 2.0 (Etalab)"


@dataclass(frozen=True)
class DepartementFieldMap:
    """Declarative mapping from one département's own real OpenDataSoft
    record shape onto the canonical concepts
    :func:`streetworks.common.from_departement_roadworks` needs.
    Everything not mapped here still survives - the whole record is kept
    on ``Works.raw``/``WorksSite.raw``, per this SDK's "canonicalise the
    shared, preserve the specific" rule.

    ``point_field`` names the real OpenDataSoft geo-point column - not a
    platform-wide standard field name, confirmed live to vary per
    dataset (``geo_point_2d`` for Sarthe/Hauts-de-Seine,
    ``localisation`` for Loire-Atlantique). ``line_field``, when set,
    names a real ``geo_shape`` GeoJSON column whose ``geometry`` is
    genuinely a ``LineString``/``MultiLineString`` (never assumed - see
    :mod:`streetworks.common.from_paris`'s own contrasting real
    ``Polygon`` case, deliberately never read into ``Coordinate.points``).

    ``start_field``/``end_field`` are ``None`` where a département states
    no structured date at all (Loire-Atlantique, Hauts-de-Seine) - every
    ``WorksSite`` from that département then carries
    ``DateConfidence.UNKNOWN``, never a guess parsed out of free text.
    """

    departement: str
    records_url: str
    point_field: str = "geo_point_2d"
    line_field: str | None = "geo_shape"
    title_field: str | None = None
    promoter_field: str | None = None
    start_field: str | None = None
    end_field: str | None = None
    road_field: str | None = None
    status_field: str | None = None
    id_field: str | None = "objectid"
    licence: str = _LICENCE_OUVERTE
    attribution: str = ""


SARTHE = DepartementFieldMap(
    departement="Sarthe",
    records_url=(
        "https://data.sarthe.fr/api/explore/v2.1/catalog/datasets/"
        "227200029_chantiers_routiers/records"
    ),
    title_field="nature_trvx",
    promoter_field="maitre_ouvrage",
    start_field="date_debut",
    end_field="date_fin",
    road_field="loc_txt",
    status_field="mode_exp",
    attribution="Conseil départemental de la Sarthe",
)

LOIRE_ATLANTIQUE = DepartementFieldMap(
    departement="Loire-Atlantique",
    records_url=(
        "https://data.loire-atlantique.fr/api/explore/v2.1/catalog/datasets/"
        "224400028_info-route-departementale/records"
    ),
    point_field="localisation",
    line_field=None,  # no real geo_shape line field exists for this dataset
    title_field="ligne1",
    status_field="nature",
    id_field=None,  # no real per-record id field at all - see module docstring
    attribution="Département de Loire-Atlantique",
)

HAUTS_DE_SEINE = DepartementFieldMap(
    departement="Hauts-de-Seine",
    records_url=(
        "https://opendata.hauts-de-seine.fr/api/explore/v2.1/catalog/datasets/"
        "fr-229200506-travaux-et-projets-sur-voirie-departementale/records"
    ),
    title_field="description_travaux",
    promoter_field="operateur",
    road_field="voie",
    status_field="avancement",
    attribution="Département des Hauts-de-Seine",
)

FIELD_MAPS: dict[str, DepartementFieldMap] = {
    "Sarthe": SARTHE,
    "Loire-Atlantique": LOIRE_ATLANTIQUE,
    "Hauts-de-Seine": HAUTS_DE_SEINE,
}


class DepartementRoadworksClient:
    """Fetch French département roadworks via the field maps in
    :data:`FIELD_MAPS`. No credentials required.

    >>> from streetworks.opendatasoft.france_departements import DepartementRoadworksClient
    >>> from streetworks.common import from_departement_roadworks
    >>> with DepartementRoadworksClient() as france:
    ...     records = france.fetch("Sarthe")
    >>> works = from_departement_roadworks(records, SARTHE)  # doctest: +SKIP
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ods = OpenDataSoftClient(client=client)

    def fetch(self, departement: str) -> list[JSON]:
        """Fetch every current real record for ``departement`` (a key of
        :data:`FIELD_MAPS`, e.g. ``"Sarthe"``) - unconverted. Pass these
        straight to
        :func:`streetworks.common.from_departement_roadworks` with the
        same département's :class:`DepartementFieldMap`."""
        field_map = FIELD_MAPS[departement]
        return list(self._ods.iter_records(field_map.records_url))

    def iter_all(self, departements: list[str] | None = None) -> Iterator[tuple[str, JSON]]:
        """Yield ``(departement, record)`` for every record across
        ``departements`` (default: every département in
        :data:`FIELD_MAPS`)."""
        for departement in departements if departements is not None else FIELD_MAPS:
            for record in self.fetch(departement):
                yield departement, record

    def close(self) -> None:
        self._ods.close()

    def __enter__(self) -> DepartementRoadworksClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
