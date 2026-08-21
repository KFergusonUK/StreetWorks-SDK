"""Québec (province) roadworks - the Ministère des Transports et de la
Mobilité durable's (MTQ) real "Travaux routiers" feed, over its own plain
WFS 2.0.0 (MapServer) deployment, found via Données Québec (the
provincial open-data portal). Found while surveying the Canadian
provinces for roadworks coverage beyond British Columbia (see
:mod:`streetworks.drivebc`) - this SDK's first Canadian *provincial*
roadworks provider (as distinct from Quebec **City**'s own separate,
already-covered WZDx feed - see :mod:`streetworks.wzdx.registry`'s own
module docstring; the two are genuinely different real authorities/
platforms, never deduplicated against each other).

**Real layer, confirmed live via the dataset's own Données Québec
catalogue entry (``travaux-routiers``, CC BY 4.0, MTQ-published).** 526
real features at investigation time (2026-08-21), confirmed via the WFS's
own ``numberMatched``. Real fields: ``identifiant`` (per-record id),
``identifiantChantier`` (a real project-level grouping key - 391 distinct
chantiers across 526 records, 71 with 2-5 real entraves each, the same
grouping shape :mod:`streetworks.arcgis.jersey`'s own ``PROJID`` gives),
``routeAutoroute`` (a real route number, empty string on some records -
not always populated), ``entraveType`` (a real, clean 6-value enum:
``"Mineure (semaine)"``/``"Majeure (semaine et fin de semaine)"``/
``"Mineure (semaine et fin de semaine)"``/``"Majeure (semaine)"``/
``"Mineure (fin de semaine)"``/``"Majeure (fin de semaine)"``),
``debut``/``fin``/``miseAJour`` (real dates, ``"YYYY/MM/DD HH:MM:SS"`` -
not ISO 8601, 0/526 missing on either ``debut`` or ``fin``),
``identificationDesTravaux`` (a real work title), ``localisation``
(a real free-text location description), ``direction``, ``entrave`` (the
real closure/restriction prose), ``entravesLieesAuxChargesEtDimensions``
(load/dimension restrictions), ``detoursEtItinerairesFacultatifs``
(detour text), ``descriptionFrancais``/``descriptionAnglais`` - **a
genuinely bilingual official pair, both real, not one derived from the
other** (MTQ publishes both languages itself) - and ``couleurLigne``
(a display hex colour, cosmetic, kept in ``.raw`` only) plus a constant
``source`` field (``"https://www.quebec511.info"``, confirming this feed
is the real data behind Québec 511's own public map).

**No separate ``status``/verified flag exists** - unlike Jersey's
``STATUS`` or DC's ``STATUS`` - so this is treated the same as
:mod:`streetworks.drivebc`'s own uniformly-``ESTIMATED`` case: a live
"currently causing disruption" feed, not independent confirmation the
work is physically happening right now.

**Geometry is real ``LineString``, genuine WGS84** (``srsName=EPSG:4326``
requested and honoured, confirmed live against real Québec coordinates),
via the exact same generic
:class:`~streetworks.ogc.client.OGCFeaturesClient` this SDK's German
state cluster and :mod:`streetworks.lyon` already use - no new fetch
code needed. The real service accepts this client's default WFS 2.0.0
``TYPENAMES``/``OUTPUTFORMAT=application/geo+json`` request shape
unchanged (confirmed live), even though the dataset's own published
example URL uses the older ``outputformat=geojson`` (bare format name,
not the MIME type) - both work.

**Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)**,
confirmed live via Données Québec's own dataset metadata
(``license_id: cc-by``).

**No credentials required** - every read in this investigation succeeded
unauthenticated.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..ogc.client import OGCFeaturesClient

__all__ = ["BASE_URL", "TYPE_NAME", "QuebecClient"]

JSON = dict[str, Any]

#: MTQ's own real WFS (MapServer) deployment - confirmed live, no key
#: required. See module docstring for how this was found.
BASE_URL = "https://ws.mapserver.transports.gouv.qc.ca/swtq"

#: The real "chantiers" (worksites) feature type - confirmed live, the
#: one roadworks-shaped layer this dataset's own Données Québec entry
#: names.
TYPE_NAME = "ms:chantiers_mtmdet"


class QuebecClient:
    """Fetch Québec province's real MTQ roadworks feed. No credentials
    required.

    >>> from streetworks.quebec import QuebecClient
    >>> from streetworks.common import from_quebec
    >>> with QuebecClient() as quebec:  # doctest: +SKIP
    ...     works_list = from_quebec(list(quebec.iter_roadworks()))
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def iter_roadworks(self) -> Iterator[JSON]:
        """Every real feature (GeoJSON ``Feature`` dicts) - a single
        request, confirmed live to return the whole real 526-feature
        layer in one response."""
        payload = self._ogc.get_wfs_features(BASE_URL, type_name=TYPE_NAME, version="2.0.0")
        yield from payload.get("features") or []

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> QuebecClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
