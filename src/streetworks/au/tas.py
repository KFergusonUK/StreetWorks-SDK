"""Tasmania: Department of State Growth (Transport Services) Roadworks -
State Roads, the seventh :mod:`streetworks.au` member, over its own
ArcGIS FeatureServer. Planned works on the state road network only - no
incidents mixed in, the cleanest single-type feed in this AU cluster.

.. attention::
   **Confirmed live (2026-08-01)** against a real, unauthenticated pull
   (10 real records - genuinely this small; a real ``returnCountOnly``
   check, not an artefact of paging). **Licence genuinely unconfirmed -
   see below** - real, working data, shipped the same way
   :mod:`streetworks.arcgis.jersey` was (an openly, unauthenticatedly
   queryable service with no explicit licence statement found), not
   blocked the way South Australia is.

**Service** (confirmed live): ``STATE_RDS/Roadworks_State_Roads`` on
``data.stategrowth.tas.gov.au``'s ArcGIS Server - found by walking every
real folder in the service root (the investigation brief's own guess, a
``PUBLIC`` folder alongside a ``STATEROADS`` road-centreline layer, turned
out to be the *wrong* folder; the real service lives under ``STATE_RDS``
instead, alongside the real ``STATEROADS`` centreline layer's own sibling,
confirming the road-register connection the brief hoped for exists, just
in a different folder than guessed).

**Real total: 10.** The smallest AU provider in this SDK by a wide margin
- genuinely this size (``returnCountOnly=true`` confirms it directly, not
an artefact of a truncated page). ``maxRecordCount`` 2000, genuine
``advancedQueryCapabilities.supportsPagination: true`` - still paged
properly via the shared
:class:`~streetworks.arcgis.client.ArcGISFeatureClient`, not assumed to
stay this small.

**Geometry: real ``esriGeometryPolyline`` - not point-only**, unlike every
other AU provider built so far (NSW/VIC/WA/QLD/SA/ACT are all points).
Real line lengths vary from 5 to 152 vertices in one live pull; every real
``LOCATION_DESC`` checked describes a short, specific segment ("Between
View Road overpass and North Terrace", "Near Proctors Road Roundabout") -
**not** the Victoria/QLD corridor-extent trap (a real span check on all 10
records found the longest real line still resolves to a single named
road's own stated segment, not a multi-road/multi-suburb sprawl) - so
:mod:`streetworks.common.from_au_tas_roadworks` keeps the full line via
``Coordinate.points``, the same trusted-precise-linework treatment
Bison Futé's real TPEG segments get.

**CRS - genuinely different from WA/SA, and this matters for how the
runtime guard is built.** The layer's real native spatial reference is
**EPSG:28355 (GDA94 / MGA zone 55)**, confirmed from the live layer
definition - **not** Web Mercator, despite the investigation brief's own
guess. ``outSR=4326`` is confirmed honoured live (real Tasmanian-range
WGS84 coordinates returned, e.g. ``[147.049..., -41.538...]``). **This
module deliberately does not reuse**
:mod:`streetworks.common._web_mercator` **the way WA/SA do** - that
module's closed-form inverse is specific to EPSG:3857 (a spherical
projection with a cheap, exact algebraic inverse); GDA94/MGA zone 55 is a
real ellipsoidal Transverse Mercator projection, whose correct inverse
needs genuine UTM-family ellipsoid math, not a one-line formula - applying
the Web Mercator formula to MGA55 easting/northing values, if ``outSR``
ever stopped being honoured, would silently produce **wrong, not just
imprecise**, coordinates, which is worse than not guarding at all. So
this module trusts the confirmed-live ``outSR=4326`` request without a
reprojection fallback, and instead relies on
``scripts/smoke_test.py``'s own plausible-range check (the same "fail
loudly if a coordinate looks wrong" discipline WA's own smoke check
uses) to catch it if that ever stops being true - a real, load-bearing
distinction from WA/SA worth understanding before extending this module.

**Real field list** (from the live layer definition - ground truth):
``ID`` (the real ``objectIdField``, ``esriFieldTypeOID`` - **no separate
GUID/GlobalID field exists on this layer at all**, a real gap compared to
WA/SA/ACT, all of which have one; ``Works.reference`` is keyed on ``ID``
anyway since nothing better is stated, with this caveat recorded
honestly rather than silently treating it as a stable identifier the way
a real GlobalID would be), ``EVENT_TYPE`` (confirmed live to be the
literal string ``"Roadworks"`` on all 10/10 real records - a single-value
feed, no incident-filtering needed, unlike NSW/SA), ``START_TIME``/
``END_TIME`` (real ``esriFieldTypeDate`` fields, epoch milliseconds UTC -
proper typed dates, no WA-style ``DD/MM`` string ambiguity here),
``LOCATION_DESC``, ``ROAD_NAME``, ``TRAFFIC_MANAGEMENT`` (real free-text
prose, e.g. "Reduced Speed limit with frequent lane closures during
working hours 9.30 am to 2.30 pm"), ``WEB_LINK`` (confirmed always
``null`` on every real record checked - a real field, currently unused,
the same "field exists but is currently dead" finding as WA's
``SeeMoreName``), ``SITE_CONTACT``/``SITE_CONTACT_PHONE`` (real, always
populated - a genuinely new kind of field in this AU cluster: a named
contractor plus phone number, e.g. ``"BridgePro"``/``"0460 933 483"`` -
no canonical model field fits this, so it's folded into
``traffic_management`` alongside the impact text rather than dropped, see
:mod:`streetworks.common.from_au_tas_roadworks`).

**Licence - genuinely unconfirmed, checked directly, not inferred from
portal norms.** The investigation brief flagged this as "not specified on
the NFDH harvest listing... likely CC-BY (Tasmanian LISTdata is CC-BY
4.0), but must be confirmed on the actual resource, not assumed." Checked
directly: the ArcGIS item's own portal metadata
(``/portal/sharing/rest/content/items/{id}``) states both
``"licenseInfo": null`` **and** ``"accessInformation": null`` - genuinely
no licence statement anywhere on the real resource itself. Tasmania's own
open-data guidance is explicit that not all LIST-family data shares one
blanket policy ("you must refer to the Licence Terms and Conditions...
to confirm the terms") - and this service isn't even hosted on the LIST
portal (``thelist.tas.gov.au``) at all, it's a separate Department of
State Growth deployment, so LIST's own CC-BY 4.0 statement doesn't
obviously extend here either. Shipped anyway, the same
:mod:`streetworks.arcgis.jersey` basis: openly, unauthenticatedly
queryable by design, real data committed as a real fixture - but
``licence=None``/``licence_confirmed=False`` in the registry, and this
should weigh into any redistribution decision downstream.

**Credentials**: none. Confirmed live - every query above succeeded with
no authentication.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..arcgis.client import ArcGISFeatureClient

__all__ = ["BASE_URL", "ROADWORKS_LAYER", "TasRoadworksClient"]

JSON = dict[str, Any]

BASE_URL = "https://data.stategrowth.tas.gov.au/arcgis/rest/services/STATE_RDS/Roadworks_State_Roads/FeatureServer"

#: The (only) real layer - esriGeometryPolyline, confirmed live.
ROADWORKS_LAYER = 0


class TasRoadworksClient:
    """Fetch Tasmanian state-road roadworks from the Department of State
    Growth's ArcGIS FeatureServer. No credentials required - see module
    docstring for the genuinely unconfirmed licence, distinct from
    "blocked."

    >>> from streetworks.au.tas import TasRoadworksClient
    >>> from streetworks.common import from_au_tas_roadworks
    >>> with TasRoadworksClient() as tas:  # doctest: +SKIP
    ...     works_list = from_au_tas_roadworks(list(tas.iter_roadworks()))
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_roadworks(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Every real roadworks feature (GeoJSON ``Feature`` dicts) -
        already roadworks-only by construction (confirmed live:
        ``EVENT_TYPE`` is the literal ``"Roadworks"`` on every real record,
        no incidents mixed in, see module docstring), paged correctly via
        the shared :class:`~streetworks.arcgis.client.ArcGISFeatureClient`.
        """
        yield from self._arcgis.iter_features(
            BASE_URL, ROADWORKS_LAYER, where=where, out_fields="*", out_sr=4326
        )

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> TasRoadworksClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
