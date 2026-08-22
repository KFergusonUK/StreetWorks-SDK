"""Infraestruturas de Portugal (IP) - Condicionamentos (real-time national
road restrictions/roadworks), over IP's own public ArcGIS REST deployment.
This SDK's first Portugal *national* roadworks provider -
:mod:`streetworks.arcgis.lisboa` is municipal (Lisbon only).

**Found by tracing IP's own live public "Trânsito em Tempo Real" page**
(``servicos.infraestruturasdeportugal.pt/pt-pt/viajar-na-estrada/transito-em-tempo-real``),
the same technique that found Lisboa's and Road Report NT's real
backends: the page embeds a real ArcGIS Instant App
(``infraestruturas.maps.arcgis.com/apps/instant/basic/...``), resolved
via the sharing REST API to its real webmap
(``webmap_viajar_na_estrada_sem_cameras_featurelayer``), which names four
real operational layers on one shared ``utility.arcgis.com`` MapServer
(``webapps/viajar_na_estrada2024``): Condicionamentos (this module),
Outras Ocorrências, Acidentes, and a Serra da Estrela driving-conditions
layer - none of the other three consumed here, see below.

This directly supersedes the earlier NAP-survey finding
(``docs/nap-survey.md``) that the national NAP itself
(``nap-portugal.imt-ip.pt``) carries no roadworks content - genuinely
true (confirmed again this session by reading its own JS bundle end to
end: zero roadworks vocabulary anywhere), but IP publishes its own live
feed entirely separately from the NAP registration/catalogue system,
which turned out to be an access-management portal (users, suppliers,
access requests, contracts), not a data host.

**93 real active records, confirmed live 2026-08-22.** ``tipo ==
"MaintenanceWorks"`` (86) or ``"ConstructionWorks"`` (2) are genuine
roadworks - 88/93. The other two real values are confirmed, not assumed,
to be something else: ``PoorRoadInfrastructure`` (4, a real defect
*report* - a damaged guardrail, a fallen sign - not active repair work)
and ``GenericIncident`` (1, a real event-driven closure). The two
sibling layers on the same service, checked live rather than trusted by
name, are genuinely not roadworks either - Outras Ocorrências (77 real
records: ``EnvironmentalObstruction``/``VehicleObstruction``/
``GeneralObstruction``/``EquipmentDamageObstruction``/
``AnimalPresenceObstruction``) and Acidentes - so ``Condicionamentos``
alone is the right, sufficient layer.

**Real fields**: ``objectid``, ``tipo``, ``estado`` (real but uniformly
``"ativo"`` on every record checked - the same "real field, currently
uninformative" honesty this SDK already gives Alberta's ``Severity``),
``datainicio``/``dataobservacao``/``datafim`` (Esri epoch
**milliseconds**), ``commentsummary`` (real free-text description of the
restriction/work), ``description`` (the real road identifier, e.g.
``"EN211"``), ``pkbegin`` (kilometre marker), ``direction``,
``distrito``/``concelho`` (district/municipality), plain ``latitude``/
``longitude`` attribute fields (see geometry note below).

**A real "no defined end" placeholder in ``datafim``, confirmed live -
not assumed.** 3 of 34 real non-null ``datafim`` values are the exact
same sentinel, ``2556143999000`` (2050-12-31 23:59:59 UTC) - a fabricated
far-future date meaning "no end stated," the same class of finding
WZDx's own placeholder-date handling already documents for this SDK.
Never surfaced as a real date - see
:func:`streetworks.common.from_ip._epoch_ms_to_end`.

**Geometry: real ``f=geojson`` output is genuine WGS84**, confirmed live
by comparing a real decoded point against that same record's own
separately-stated ``latitude``/``longitude`` attribute fields (identical
to six decimal places) - despite the layer's native ``shape`` geometry
being Web Mercator (``wkid 102100``/``3857``), the same "check
per-service, don't assume" discipline TIGERweb's and DC's own module
docstrings establish.

**Licence: unconfirmed** - no ``licenseInfo``/``accessInformation`` on
the real ArcGIS item, and no terms found specific to this dataset. Ships
anyway, flagged prominently, the same honest-gap tier as Autobahn
GmbH/Jersey/NYC DOT in this SDK.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .client import ArcGISFeatureClient

__all__ = ["BASE_URL", "CONDICIONAMENTOS_LAYER", "IPRoadworksClient"]

JSON = dict[str, Any]

BASE_URL = (
    "https://utility.arcgis.com/usrsvcs/servers/"
    "98bffc4ef35b4e18a03641918c5d07dd/rest/services/webapps/"
    "viajar_na_estrada2024/MapServer"
)

#: "Condicionamentos" - the real roadworks/restrictions layer. See module docstring.
CONDICIONAMENTOS_LAYER = 2

#: Confirmed live, not a guess - the real filter separating roadworks from
#: the layer's two other real ``tipo`` values. See module docstring.
_ROADWORKS_TYPES = ("MaintenanceWorks", "ConstructionWorks")


class IPRoadworksClient:
    """Fetch Infraestruturas de Portugal's real Condicionamentos records.
    No credentials required.

    >>> from streetworks.arcgis.ip import IPRoadworksClient
    >>> from streetworks.common import from_ip
    >>> with IPRoadworksClient() as ip:  # doctest: +SKIP
    ...     works_list = from_ip(list(ip.iter_roadworks()))
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_condicionamentos(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Yield every real Condicionamentos feature (GeoJSON ``Feature``
        dicts), unfiltered - includes real non-roadworks records
        (``PoorRoadInfrastructure``/``GenericIncident``). See module
        docstring."""
        yield from self._arcgis.iter_features(
            BASE_URL, CONDICIONAMENTOS_LAYER, where=where, out_fields="*"
        )

    def iter_roadworks(self) -> Iterator[JSON]:
        """Yield only real roadworks features - ``tipo`` filtered
        server-side to ``MaintenanceWorks``/``ConstructionWorks``. See
        module docstring."""
        where = "tipo IN ({})".format(",".join(f"'{t}'" for t in _ROADWORKS_TYPES))
        yield from self.iter_condicionamentos(where=where)

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> IPRoadworksClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
