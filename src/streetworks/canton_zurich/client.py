"""Kanton Zürich: "Baustellen Kantonsstrassen" - roadworks on the
canton's own cantonal-road network, over a GeoServer WFS. This SDK's
first Swiss provider, alongside the separate, non-overlapping Stadt
Zürich city-streets coverage (:mod:`streetworks.zurich`) - do not dedupe
between the two, the same discipline as every other national/regional-
vs-municipal pair in this SDK.

.. attention::
   **Confirmed live (2026-08-14)** against a real, unauthenticated pull
   (66 real feature rows at time of writing).

**Found via opendata.swiss's own CKAN catalogue** (``wfs-baustellen-
kantonsstrassen``, maintained by Geoinformation Kanton Zürich), not
guessed - the real WFS endpoint is
``https://maps.zh.ch/wfs/TbaBaustellenZHWFS`` ("Tba" = Tiefbauamt, the
canton's civil engineering office).

**Two real layers, confirmed to carry the same underlying 66 closures,
not disjoint data.** ``ms:baustellen-uebersicht`` (overview, ``Point``
geometry) and ``ms:baustellen-detailansicht`` (detail, real ``Polygon``
work-area footprints) - every sampled feature's non-geometry properties
match 1:1 across both layers by street/km-range/dates. This module uses
``baustellen-detailansicht`` (:data:`TYPE_NAME`) as the richer real
geometry source, the same "prefer the richer layer" call already made
for Oslo's own majority-``Polygon`` shape.

**CRS confirmed live: `EPSG:2056`** (Swiss LV95), stated explicitly in
the WFS's own ``GetCapabilities`` (``<DefaultCRS>urn:ogc:def:crs:EPSG::2056``)
and matching real coordinate magnitudes (``[2702540.6, 1261733.7]``,
genuine LV95 order-of-magnitude for the Zürich area) - requested
explicitly here, not reprojected, the same policy as Mallorca/Saxony/
Oslo/Helsinki.

**No unique identifier field exists anywhere in this schema - checked
every property, genuinely absent, not an extraction gap.** The real
fields are ``strassenbez``/``kmvon``/``kmbis``/``strassenname``/
``gemeindename``/``ansprechperson``/``oe``/``telefonnummer``/
``beschreibung``/``verkehrsfuehrung``/``status_baustelle``/
``datum_baubeginn``/``datum_bauende``/``lmutdat``/``link1``/
``weiteregemeinden`` - none is a stated identifier. A composite of
``strassenbez``+``kmvon``+``kmbis``+``datum_baubeginn`` is 65/66 unique
in the live data, but the one real collision is two genuinely distinct
closures (opposite directions of the same road, different times and
descriptions) sharing identical values on all four fields - proof that
fabricating a composite key here would be dishonest, not merely
imperfect. See :mod:`streetworks.common.from_canton_zurich` for how
``reference`` is left ``None`` rather than guessed.

**``ansprechperson``/``telefonnummer`` are a named individual staff
member's contact details, not an organisation** - never promoted to
``Works.promoter``, which would misrepresent a person as a company. ``oe``
("Unterhaltsbezirk N", maintenance district) is organisational but a
sub-unit, not a promoter name either. All three are preserved on
``WorksSite.raw`` only.

**``status_baustelle`` is a real, genuinely informative two-value
field** - ``"aktiv (Bauzeit)"`` (52/66 live) and
``"zukünftig (Bauzeit in Zukunft)"`` (14/66 live), the same shape as
Helsinki's ``Käynnissä``/``Tuleva`` - see the converter for how this
drives real ``VERIFIED``/``ESTIMATED`` date-confidence grading.

**Licence: opendata.swiss's "Open use" tier, confirmed live - but not
from the obvious field.** The dataset's own CKAN ``license_id`` is
empty at both the resource and parent-package level; the real licence
only surfaced via the WFS resource's separate ``rights`` field
(``https://opendata.swiss/terms-of-use#terms_open``). Checked what that
tier actually permits on opendata.swiss's own terms page: usable for
both non-commercial and commercial purposes, **no attribution
required** - the most permissive of opendata.swiss's four tiers,
comparable to CC0.

**The format gotcha - confirmed live, the same masked-failure shape
Mallorca's own module docstring documents for a different server.**
This GeoServer instance doesn't offer the shared client's own
``application/geo+json`` default; plain ``application/json`` is what
actually works, confirmed live. Every call here passes
``output_format="application/json"`` explicitly.

**No credentials required** - every claim above came from a fully
unauthenticated GetFeature request.
"""

from __future__ import annotations

from typing import Any

import httpx

from ..ogc.client import OGCFeaturesClient

__all__ = ["BASE_URL", "TYPE_NAME", "CRS", "CantonZurichClient"]

JSON = dict[str, Any]

#: Found via opendata.swiss's own CKAN catalogue entry
#: (wfs-baustellen-kantonsstrassen), confirmed live. See module docstring.
BASE_URL = "https://maps.zh.ch/wfs/TbaBaustellenZHWFS"

#: The detail-view layer (real Polygon work-area geometry) - see module
#: docstring for why this is used instead of the overview Point layer.
TYPE_NAME = "ms:baustellen-detailansicht"

#: Swiss LV95, the WFS's real native CRS - requested explicitly rather
#: than the shared client's own EPSG:4326 default. See module docstring.
CRS = "EPSG:2056"

#: This GeoServer's real working JSON output format - not the shared
#: client's own "application/geo+json" default. See module docstring.
_OUTPUT_FORMAT = "application/json"


class CantonZurichClient:
    """Fetch Kanton Zürich's real "Baustellen Kantonsstrassen" (cantonal-
    road works) from the canton's own GeoServer WFS. No credentials
    required.

    >>> from streetworks.canton_zurich import CantonZurichClient
    >>> from streetworks.common import from_canton_zurich
    >>> with CantonZurichClient() as canton_zurich:  # doctest: +SKIP
    ...     works = from_canton_zurich(canton_zurich.iter_roadworks())
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def iter_roadworks(self) -> list[JSON]:
        """Every real roadworks feature - raw, unfiltered. This dataset
        is already single-purpose, see module docstring."""
        payload = self._ogc.get_wfs_features(
            BASE_URL, type_name=TYPE_NAME, srs_name=CRS, output_format=_OUTPUT_FORMAT
        )
        return list(payload.get("features") or ())

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> CantonZurichClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
