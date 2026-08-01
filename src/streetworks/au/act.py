"""Australian Capital Territory: Temporary Traffic Management (TTM) -
Planned Road Closures, the sixth :mod:`streetworks.au` member and the
first with genuine **municipal/local-street coverage** - every other
provider in this cluster (including the "big five") is state-network only.
Permit-derived: Roads ACT's real TTM application workflow (an ESRI
Survey123 form) feeds this feed directly.

.. attention::
   **Confirmed live (2026-08-01)** against a real, unauthenticated pull
   (98 real records). Credential-free, shipped live-verified with a real
   fixture from day one - never a Credentials-wanted scaffold.

**A real correction to the source investigation brief: this is ArcGIS, not
Socrata.** dataACT (`data.act.gov.au`, a genuine Socrata portal) catalogues
this dataset, but the catalogue entry itself is a plain **link/pointer**
(confirmed live: the Socrata item's own `viewType`/`displayType` are both
``"href"``, and its `/resource/{id}.json` SODA endpoint returns a real
HTTP 400, *"Non-tabular datasets do not support rows requests"*) - the
real data lives on a separate **ArcGIS Online-hosted FeatureServer**
(`services1.arcgis.com/E5n4f1VY84i0xSjy/.../FeatureServer/0`), reachable
directly via the Socrata item's own ``additionalAccessPoints`` metadata.
So this module reuses the same
:class:`~streetworks.arcgis.client.ArcGISFeatureClient` WA/QLD-adjacent
providers already do, **not** a new Socrata SODA client - the brief's
"fourth AU client shape" claim doesn't hold; this is still ArcGIS.

**The "live vs. historical" gating question - resolved live, genuinely
live.** dataACT actually catalogues *two* related datasets: "...(Historical
Data)" and "...(Live Stream)" - this module targets the latter
(``gcdw-wgd8``). Confusingly, the *underlying* ArcGIS service URL itself is
still named ``Road_Closures_public_view_HISTORICAL`` (a real, if
misleading, service name) - but its own catalogue description states
"provides a live stream of planned road closures within the ACT" and
"Update Frequency: Real time", and a real live pull confirms this: real
project codes reference 2026 works (e.g. ``TTE26-ACT-4139``, a real
September-2026-dated closure, fetched the same day this module was built)
- genuinely current, not stale historical rows. The service name is not
evidence of what the data actually is; the real query result is.

**Real total, small - the "tail" framing holds.** Confirmed live: **98**
real total records (``returnCountOnly=true``) - genuinely small,
consistent with this being a city-state's whole TTM programme, not a
national dataset. ``maxRecordCount`` 1000, so a single unpaged query
already returns everything - still paged properly via the shared
:class:`~streetworks.arcgis.client.ArcGISFeatureClient`, not assumed to
stay that way.

**Real ``type`` values, confirmed live, not guessed** - all seven of the
catalogue's own documented enum values were seen in a 98-record pull:
``roadWorks`` (34, the largest single value, ~35%), ``buildingConstruction``
(25), ``lightRail`` (22), ``specialEvent`` (8), ``other`` (5),
``utilities`` (3), ``telecommunications`` (1). Since ``roadWorks`` is
directly, positively confirmed (unlike South Australia's still-unverified
``REC_TYPE``), :meth:`ActTtmClient.iter_roadworks` filters server-side via
``where="type='roadWorks'"`` by default - a real, evidenced filter, not a
guess. ``describeActivity`` is confirmed to be populated on exactly the 5
``other``-typed records and empty everywhere else - matching the
catalogue's own documented rule ("required if 'other' type selected")
precisely.

**Geometry: native EPSG:4326 - no reprojection guard needed at all**,
unlike WA/SA's Web Mercator services. Confirmed from the live layer
definition (``spatialReference: {"wkid": 4326}``) and from real query
results (genuine Canberra-range coordinates, e.g.
``[149.159294347216, -35.2303907095075]``, returned with no ``outSR``
special-casing required) - the simplest AU geometry story so far.

**A real, confirmed text-formatting quirk**: ``roadsClosed`` (the primary
location-description field) genuinely embeds literal HTML ``<br>`` line
breaks in real data (e.g. ``"...Aspinall Street and Mabel Miller
Lane.<br>\\n\\n"``) - carried through exactly as stated, never silently
stripped or reformatted, per this SDK's standing "never silently correct
the source" discipline. A real ``suburb1`` value was also seen as the
literal string ``"OTHER"`` (Whitlam Display Village, a genuine outer-
suburb/greenfield development site) - not a sentinel needing special
handling the way WA's ``"LOCAL ROAD"`` was, just an unusually-named real
suburb value, carried through as-is.

**``tccsCommsClosure``/``roadsDelegateClosure`` - real approval-status
fields, confirmed always ``"yes"`` in the current live feed (98/98).**
Plausible explanation: this is the *public* view of the TTM system, so
only comms-cleared, delegate-approved closures are exposed here at all -
unapproved plans presumably never reach this feed. Since the fields never
actually vary, they add no real discriminating signal today, so
:mod:`streetworks.common.from_au_act_ttm` does not use them to promote
``DateConfidence`` past ``ESTIMATED`` - the same "a real field, but
currently constant, so it can't discriminate anything" reasoning WA's
always-empty ``WorkStatus`` got.

**Licence: Creative Commons Attribution-ShareAlike 4.0 International
(CC BY-SA), confirmed live from the Socrata item's own ``license``
metadata** (``licenseId: "CC_40_BY_SA"``) - **distinct from every other
AU provider in this cluster**, which are plain CC-BY (no Share-Alike
clause). Real attribution: ``"Transport Canberra and City Services -
Roads ACT"``. ``administrative_area`` uses ``"Roads ACT"`` (the specific
operating unit that owns TTM approvals, per the catalogue's own
``custom_fields``), matching the operator-as-authority rule already
applied to Autobahn GmbH/TfNSW/Main Roads WA; the broader directorate
("Transport Canberra and City Services") is the real attribution string
and should also be credited wherever this data is displayed or
redistributed, per Share-Alike's own terms.

**Credentials**: none. Confirmed live - every query above succeeded with
no authentication.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..arcgis.client import ArcGISFeatureClient

__all__ = ["BASE_URL", "ROADWORKS_LAYER", "ActTtmClient"]

JSON = dict[str, Any]

BASE_URL = "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/Road_Closures_public_view_HISTORICAL/FeatureServer"

#: The (only) real layer - esriGeometryPoint, confirmed live. Despite the
#: service's own name, this is the live-stream catalogue entry - see
#: module docstring.
ROADWORKS_LAYER = 0

#: The real, confirmed-live value meaning roadworks specifically - see
#: module docstring for the full 98-record enum split.
_ROADWORKS_WHERE = "type='roadWorks'"


class ActTtmClient:
    """Fetch ACT Temporary Traffic Management closures from Roads ACT's
    ArcGIS-hosted live feed. No credentials required - see module
    docstring.

    >>> from streetworks.au.act import ActTtmClient
    >>> from streetworks.common import from_au_act_ttm
    >>> with ActTtmClient() as act:  # doctest: +SKIP
    ...     works_list = from_au_act_ttm(list(act.iter_roadworks()))
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_closures(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Every real TTM closure feature (GeoJSON ``Feature`` dicts),
        every ``type`` - roadworks, building construction, light rail,
        special events, utilities, telecommunications, and other - paged
        correctly via the shared
        :class:`~streetworks.arcgis.client.ArcGISFeatureClient`. See
        :meth:`iter_roadworks` for the roadworks-only convenience."""
        yield from self._arcgis.iter_features(
            BASE_URL, ROADWORKS_LAYER, where=where, out_fields="*", out_sr=4326
        )

    def iter_roadworks(self, *, where: str = _ROADWORKS_WHERE) -> Iterator[JSON]:
        """``type='roadWorks'`` only - a real, confirmed-live filter value
        (34/98 real records in one pull), not a guess. See module
        docstring."""
        yield from self.iter_closures(where=where)

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> ActTtmClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
