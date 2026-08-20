"""Lyon (Métropole de Lyon) roadworks - a real, live, keyless WFS 2.0.0
feed found while surveying French cities for a `streetworks` roadworks
example write-up, over the same generic
:class:`~streetworks.ogc.client.OGCFeaturesClient` this SDK's German
state cluster already uses (:mod:`streetworks.ogc.germany`) - built
bespoke rather than folded into either that module or
:mod:`streetworks.opendatasoft.france_departements`, since Lyon's own
real platform (a plain GeoServer WFS) matches neither's shape closely
enough to be worth stretching.

**"Chantier perturbant" (disruptive worksite) - 351 real features at
investigation time (2026-08-20), confirmed via WFS's own
``numberMatched``.** Real fields: ``nom`` (the real road name, 100%
populated), ``nomchantier`` (a real, varied works description, e.g.
``"Travaux de canalisations"``, ``"Réalisation de branchements"`` -
not a fixed enum), ``commune1``/``insee`` (a real municipality name and
INSEE code within the métropole - this genuinely spans several real
communes, e.g. ``"Francheville"``, not Lyon city alone),
``debutchantier``/``finchantier`` (clean date-only ``YYYY-MM-DD``
strings, 0/351 missing), ``typeperturbation`` (a real, clean 4-value
restriction-type field: ``"Circulation interdite"``/``"Circulation
réduite"``/``"Circulation alternée"``/``"Circulation interdite de
jour"``), ``gid`` (a real stable per-feature integer id).

**``avancement`` (progress/status) is real but constant -
``"Chantier en cours"`` on all 351 real records at investigation time**,
confirmed live, not filtered here - this endpoint only ever states
currently-active works, the same real "current only, no separate
planned tier" shape several other providers in this SDK's German/
French clusters share.

**``intervenant`` (a real promoter-shaped field) is genuinely
uninformative on the overwhelming majority of records** - 347/351 real
records state the literal value ``"Autre"`` ("other"); only 4 carry a
real specific value (``"Grand Lyon"`` x2, ``"Concessionnaire"`` x1,
``None`` x1) - mapped anyway (it is what the source states), not
suppressed, but documented honestly rather than presented as a rich
promoter field.

**Geometry is real ``MultiPolygon`` only - no point or line field
exists on this layer.** Per this SDK's "never force a polygon into
``Coordinate.points``/``.parts``" rule (already established for
Guernsey/Paris's own real polygon cases) and its "never a computed
centroid" rule, the real first ring's first vertex is used as
``Coordinate.value`` - a genuine, stated coordinate, not a fabricated
one, the same "one real, arbitrarily-chosen-but-genuinely-stated point"
precedent this SDK's own gazetteer converters (Oslo, Kantone Zürich,
GeoSN) already established for their own polygon-only sources, applied
here to a roadworks record rather than a street. The full real polygon
is preserved unmodified in ``Works.raw``/``WorksSite.raw``.

**Licence: Licence Ouverte / Open Licence 2.0 (Etalab), confirmed**
directly from this dataset's own catalogue metadata on
``data.gouv.fr`` - the same licence already confirmed for Bison Futé
and most of this SDK's other French providers.

**No credentials required** - every read in this investigation
succeeded unauthenticated.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..ogc.client import OGCFeaturesClient

__all__ = ["BASE_URL", "TYPE_NAME", "LyonClient"]

JSON = dict[str, Any]

#: Métropole de Lyon's own real GeoServer WFS - confirmed live, no key
#: required. See module docstring for how this was found.
BASE_URL = "https://data.grandlyon.com/geoserver/metropole-de-lyon/ows"

#: The real "disruptive worksite" feature type - confirmed live, the
#: only roadworks-shaped layer among ~30 real feature types this WFS
#: serves.
TYPE_NAME = "metropole-de-lyon:pvo_patrimoine_voirie.pvochantierperturbant"


class LyonClient:
    """Fetch Métropole de Lyon's real roadworks feed. No credentials
    required.

    >>> from streetworks.lyon import LyonClient
    >>> from streetworks.common import from_lyon
    >>> with LyonClient() as lyon:  # doctest: +SKIP
    ...     works = from_lyon(lyon.iter_roadworks())
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def iter_roadworks(self) -> Iterator[JSON]:
        """Every real feature (GeoJSON ``Feature`` dicts) - a single
        request, confirmed live to return the whole real 351-feature
        layer in one response (well under this WFS's own page-size
        limit), unlike this SDK's larger German WFS sources."""
        payload = self._ogc.get_wfs_features(BASE_URL, type_name=TYPE_NAME, version="2.0.0")
        yield from payload.get("features") or []

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> LyonClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
