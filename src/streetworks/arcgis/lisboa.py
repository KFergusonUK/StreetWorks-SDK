"""Lisboa (Toponímia de Lisboa) - Portugal's capital's own official street
naming register, run by Câmara Municipal de Lisboa (CML). This SDK's first
Portuguese streets/gazetteer coverage - streets was previously ruled out at
the national level (Infraestruturas de Portugal's own road-network service
carries route-classification codes, no name field at all - see
``docs/portugal-streets-investigation.md``); found instead the same way
Germany's state fan-out works, by checking whether the capital itself
publishes its own open register.

**Found by walking CML's real Geodados ArcGIS Online organisation
(``geodados_CML``), not from documentation alone.** Two other real
candidates were checked and set aside first: the ``Topónimos`` layer on
CML's own ``Cartografia_Base`` service is only 40 point features - real,
but neighbourhood/district labels ("Belém", "Baixa", "Alvalade"), not
streets; the ``Rede Viária`` layer on that same service (3,763 real named
segments) turned out to be only the city's *structuring* road network - a
live check found just 375 distinct street names across those 3,763
segments, plainly not exhaustive for a city Lisbon's size. **This
service's own ``Toponímia de Lisboa`` layer is the real, official
register instead** - 3,671 real records, 100% carrying a real name
(``DESIGNACAO``), each already one row per street (confirmed live: a
single ``Avenida da Liberdade`` record, not several segments sharing that
name). Unlike the structuring-network layer, this one carries real
municipal-decree provenance per record - ``DATA_DELIBERACAO_CAMARARIA``/
``DATA_EDITAL``/``DATA_PUBLICACAO``/``DATA_EDITAL_GOVERNO_CIVIL`` (the
real dates the municipal chamber deliberated, published its edict, and
so on), ``DENOMINACOES_ANTERIORES`` (real former names, e.g. "Rua do
Possolo" was previously "Rua da Boa-Morte"), and a real prose
``HISTORIAL`` essay on the name's origin - the genuine civic-register
shape this SDK's other "streets" providers aim for, not a cartographic
backbone.

**Geometry is real, and genuinely WGS84 - confirmed live, not assumed
from the service's stated native CRS.** The service's own
``spatialReference`` states Web Mercator (``wkid: 102100`` / ``3857``),
but a live ``f=geojson`` request (with no ``outSR`` at all) returns
genuine WGS84 coordinates (a real ``Avenida da Liberdade`` vertex:
``[-9.142..., 38.716...]``, correct for Lisbon) - the same "GeoJSON
output reprojects even though the layer's own stated CRS doesn't change"
behaviour :mod:`streetworks.arcgis.tigerweb` already documents for a
different real service. :class:`ArcGISFeatureClient` always requests
``f=geojson``, so this module never needs to reproject anything itself.

**A genuine MultiLineString on some records - not a fabricated
shape.** A real street's decree can cover a name that was later applied
to a physically discontinuous set of segments (confirmed live: a real
"Avenida Ucrânia" spans 7 separate ``paths`` in one record). See
:mod:`streetworks.common.from_lisboa_streets` for how this is carried
through to :class:`~streetworks.common.models.Coordinate`'s own
``parts``.

**Licence: real, explicit, and permissive - CC0, per the service's own
``licenseInfo``**: *"Aplica-se a licença Creative Commons CCZero"*
(Creative Commons CC Zero applies), alongside a real non-legal-use
caveat also stated there (*"Cartografia não homologada, não podendo ser
utilizada para fins legais"* - uncertified cartography, not for legal
use) - a caution worth carrying forward, not a licence restriction.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .client import ArcGISFeatureClient

__all__ = ["BASE_URL", "STREETS_LAYER", "CRS", "LisboaStreetsClient"]

JSON = dict[str, Any]

#: CML's real Geodados ArcGIS Online-hosted feature service. See module
#: docstring for how this was found among ~130 other real CML datasets.
BASE_URL = "https://services.arcgis.com/1dSrzEWVQn5kHHyK/arcgis/rest/services/Cultura_Toponimia/FeatureServer"

#: "Toponímia de Lisboa" - esriGeometryPolyline, one real record per
#: street. See module docstring.
STREETS_LAYER = 0

#: The layer's own stated native spatial reference is Web Mercator
#: (EPSG:3857), but this module's real returned geometry is genuine
#: WGS84 regardless (confirmed live) - see module docstring.
CRS = "EPSG:4326"


class LisboaStreetsClient:
    """Fetch Lisboa's real official street naming register. No
    credentials required - confirmed live, public, keyless.

    >>> from streetworks.arcgis.lisboa import LisboaStreetsClient
    >>> from streetworks.common import from_lisboa_street
    >>> with LisboaStreetsClient() as lisboa:  # doctest: +SKIP
    ...     streets = [from_lisboa_street(f) for f in lisboa.iter_streets()]
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_streets(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Yield every real street feature (GeoJSON ``Feature`` dicts).
        No blank-name filter is applied by default - confirmed live,
        every one of the 3,671 real records carries a non-null
        ``DESIGNACAO``, unlike Guernsey's own equivalent layer."""
        yield from self._arcgis.iter_features(
            BASE_URL, STREETS_LAYER, where=where, out_fields="*"
        )

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> LisboaStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
