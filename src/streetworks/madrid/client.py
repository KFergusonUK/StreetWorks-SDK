"""Madrid: INFORMO ("Tráfico. Incidencias en vía pública") - the
Ayuntamiento de Madrid's own municipal traffic-incidents feed, this SDK's
first Madrid-city (as opposed to national/DGT) source and the fourth
Spanish provider alongside :mod:`streetworks.datex2.dgt` (national),
:mod:`streetworks.sct` (Catalonia) and :mod:`streetworks.ogc.mallorca`
(the Balearics).

.. attention::
   **Confirmed live (2026-08-08)** against a real, unauthenticated pull
   (217 real incidents at time of writing).

**The source brief's URL is dead - Madrid relaunched its whole open-data
portal in February 2026.** ``informo.munimadrid.es`` (the brief's stated
host, and the domain still named in the portal's own October-2023 PDF
schema doc) no longer resolves at all (confirmed via two independent
resolvers, including a public DNS-over-HTTPS lookup, to rule out a local
network quirk - genuine ``NXDOMAIN``, not a sandbox restriction). The
CKAN-based portal that replaced it (``datos.madrid.es``) now serves this
dataset's own "download" link as a redirect to the real current host,
**``informo.madrid.es``** (``munimadrid.es`` → ``madrid.es`` - not just a
path change). This client targets that confirmed-live URL directly rather
than the CKAN redirect hop, to avoid depending on a redirect chain that
could itself move again.

**The live wire format also differs from the portal's own PDF
documentation** (dated October 2023, three years stale relative to this
investigation): the documented ``fh_inicio``/``fh_final`` format is
``yyyy-mm-ddTHH:mm:ss+dd:00`` (with a UTC offset); every one of 217 real
records checked live instead uses ``yyyy-mm-ddTHH:mm:ss.fffffff`` - no
offset, and **seven** fractional-second digits (not the six
``datetime.strptime``'s ``%f`` accepts) - see
:func:`streetworks.common.from_madrid._parse_date` for the real parser
this needed, not the documented one.

**Roadworks filter: the source's own ``es_obras`` boolean, not the
brief's assumed free-text type filter.** The brief planned to filter on
``cod_tipo_incidencia``/``nom_tipo_incidencia`` text values ("obras en la
vía", "obras de mantenimiento", ...) - real data has an explicit
``es_obras`` flag (``'S'``/``'N'``) that settles this more reliably, the
same "trust the explicit flag over free-text type" discipline
:mod:`streetworks.chicagodot.client`'s ``worktype`` filter and
:mod:`streetworks.berlin.client`'s ``subtype`` filter already use. Two
real, evidenced findings this settles that the brief left open:

- **``cortes de carriles`` (lane closures, type code ``LCS``) are real
  and common (7/217 in this pull) but are *not* flagged ``es_obras`` -
  Madrid's own system treats a lane closure as a consequence worth
  reporting separately, not a worksite itself. Excluded.
- **``operación asfalto`` (asphalt resurfacing, type code ``RWR``) is
  *also* not flagged ``es_obras``** (2/217, both ``'N'``) - a genuine
  surprise (asphalt work reads like roadworks to a human), but the
  source's own classification is the evidenced signal trusted here, not
  overridden on the strength of what the label sounds like. Excluded.

Confirmed live and *not* seen in this pull at all: ``es_accidente``
(accidents) and ``es_contaminacion`` (pollution-episode mobility
protocols) were both ``'N'`` on all 217 real records - the "mixed feed
full of noise" the brief anticipated didn't show up in practice at
investigation time, though the fields exist and this client still checks
them explicitly rather than assuming they'll always be empty.

**Coordinates: both UTM and geographic given directly, no KML needed.**
The brief wasn't sure whether the XML itself carried coordinates or only
its KML sibling dataset - it does, directly: ``utm_x``/``utm_y``
(**EPSG:25830, ETRS89 / UTM Zone 30N - confirmed from the portal's own
field dictionary**, not assumed WGS84) and ``longitud``/``latitud``
(geographic, same reference frame). This client's converter uses the
geographic pair directly and labels it **EPSG:4258** (ETRS89 geographic),
matching this SDK's standing policy of never relabelling a native
ETRS89 source as WGS84/EPSG:4326 - see
:mod:`streetworks.ogc.mallorca`'s and :mod:`streetworks.arcgis.jersey`'s
own CRS notes for the same discipline applied elsewhere.

**``id_incidencia`` is the reliable reference, not ``codigo``.** ``codigo``
(the documented "año/número" field) is unique on 212/217 real records but
6 genuinely share the literal placeholder value ``"2025/0"`` - a real
data-quality gap, not a fixture artefact. ``id_incidencia`` is unique on
all 217.

**No grouping** - each ``Incidencia`` already stands alone; there is no
umbrella/application field anywhere in the schema, the same shape
:mod:`streetworks.berlin.client` found. See
:func:`streetworks.common.from_madrid` for how this becomes ``Works``.

**Licence: CC BY**, confirmed via the DGT national NAP's own catalogue
(Ayuntamiento de Madrid entries filtered to ``license_id=cc-by``) -
consistent with the dataset also being mirrored there (see the module's
own ``scope_note`` in ``registry.py`` for the never-dedupe note against
``dgt``, which already reaches some ``M-`` Madrid-area roads on its own
national/interurban network, though never municipal streets).

**No app key required** - the real pull behind every claim above
succeeded fully unauthenticated.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["INCIDENCIAS_URL", "MadridClient", "parse_incidencias"]

JSON = dict[str, Any]

#: Confirmed live 2026-08-08. Not the source brief's/portal PDF's stated
#: ``informo.munimadrid.es`` host - see module docstring.
INCIDENCIAS_URL = "https://informo.madrid.es/informo/tmadrid/incid_aytomadrid.xml"

#: Every real field on one ``<Incidencia>`` element - flat, no nesting
#: beyond the (always-blank outside pollution episodes) escenario fields.
_FIELDS = (
    "id_incidencia",
    "codigo",
    "cod_tipo_incidencia",
    "nom_tipo_incidencia",
    "fh_inicio",
    "fh_final",
    "incid_prevista",
    "incid_planificada",
    "incid_estado",
    "descripcion",
    "utm_x",
    "utm_y",
    "longitud",
    "latitud",
    "tipoincid",
    "es_obras",
    "es_accidente",
    "es_contaminacion",
    "escenario_contaminacion",
    "fecha_escenario_contaminacion",
    "descripcion_escenario",
    "medidas_escenario",
    "excepciones_escenario",
)


def _to_dict(element: ET.Element) -> JSON:
    record: JSON = {}
    for field in _FIELDS:
        child = element.find(field)
        record[field] = child.text if child is not None else None
    return record


def parse_incidencias(content: bytes) -> list[JSON]:
    """Parse a raw INFORMO XML response body into plain dicts, one per
    ``<Incidencia>``, unfiltered. Public so a fixture or a file already on
    disk can be parsed without an HTTP round-trip - see
    :mod:`tests.test_madrid`."""
    root = ET.fromstring(content)
    return [_to_dict(el) for el in root.findall("Incidencia")]


class MadridClient:
    """Fetch Madrid's INFORMO traffic-incidents feed. No credentials
    required.

    >>> from streetworks.madrid import MadridClient
    >>> from streetworks.common import from_madrid
    >>> with MadridClient() as madrid:  # doctest: +SKIP
    ...     works = from_madrid(list(madrid.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_incidencias(self) -> Iterator[JSON]:
        """Every real incident, unfiltered - includes accidents, lane
        closures, pollution-episode scenarios, everything ``es_obras``
        excludes. See module docstring."""
        response = self._transport.request("GET", INCIDENCIAS_URL)
        yield from parse_incidencias(response.content)

    def iter_roadworks(self) -> Iterator[JSON]:
        """Real roadworks records only (``es_obras == 'S'``) - see module
        docstring for why this beats a free-text type filter."""
        for record in self.iter_incidencias():
            if record.get("es_obras") == "S":
                yield record

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> MadridClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
