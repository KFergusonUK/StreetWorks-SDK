"""New Zealand: NZTA (Waka Kotahi, NZ Transport Agency) Highway
Information - "Road Events", the works strand of this SDK's first New
Zealand coverage. National state-highway roadworks/hazards, real-time.

.. attention::
   **Confirmed live (2026-08-02)** against a real, unauthenticated pull
   (104 real point events). Credential-free, shipped live-verified with a
   real fixture from day one - never a Credentials-wanted scaffold.

**A real correction to the source investigation: this is the ArcGIS
open-data portal service, not the bespoke** ``trafficnz.info`` **REST/SOAP
API the brief also flagged.** ``opendata-nzta.opendata.arcgis.com``
catalogues "Road Events" against a real ArcGIS Online-hosted
``NZTA_Highway_Information`` ``FeatureServer`` - confirmed live, and this
module reuses the same :class:`~streetworks.arcgis.client.ArcGISFeatureClient`
every AU ArcGIS provider does, rather than building a second, bespoke
REST/SOAP client for the same underlying data. **Licence confirmed live
from the ArcGIS item's own metadata**: ``"NZTA 4.0 BY CC"`` - a CC-BY 4.0
variant, resolving the brief's own "verify this isn't a bespoke
restrictive licence" caution in CC-BY's favour.

**Two real layers, genuinely different content - not a Point/LineString
pairing for the same events.** Layer 0 ("Road Events", point, 104 real
records) and layer 1 ("Road Area Events", polyline, 53 real records)
share an identical field schema, but **their real ``eventId`` values never
overlap** (confirmed live: zero intersection across all real records
pulled) and layer 1's real ``eventType`` is **always** ``"Area Warning"``
(53/53) - a weather/hazard-area concept, not roadworks at all. So this is
not the Victoria/QLD "coarse line, precise point, same event" shape -
these are two independent feeds, and roadworks stays **point-only**, no
corridor-extent trap to guard against here. Layer 1 is not built - out of
scope for a works SDK, the same treatment NSW's non-works hazard layers
get.

**Real ``eventType`` values, confirmed live - the roadworks filter is
evidenced, not guessed**: ``"Scheduled Road Work"`` (68/104, the largest
single value), ``"Road Work"`` (28/104), ``"Road Hazard"`` (8/104 - real
crashes reported by Fire Service/Police, *not* roadworks, confirmed
excluded from the filter). :meth:`NztaClient.iter_roadworks` filters
server-side on ``eventType IN ('Road Work', 'Scheduled Road Work')``.

**The richest real status signal confirmed anywhere in this SDK.** Real
``status`` (``Scheduled``/``Active``/``Resolved``) and ``planned``
(``"True"``/``"False"``, a stringly-typed boolean) correlate perfectly
with ``eventType`` in a full live pull: every ``"Scheduled Road Work"``
record is ``status=='Scheduled'``/``planned=='True'``; every real
``"Road Work"`` record is ``planned=='True'`` with
``status`` almost always ``'Active'`` (27/28), one real ``'Resolved'``.
This gives a genuine, evidenced VERIFIED/ESTIMATED split for
:attr:`~streetworks.common.DateConfidence` - every AU roadworks provider
built so far lacked a signal this clean (WA's own ``WorkStatus`` was
confirmed always empty, 0/227) - see
:mod:`streetworks.common.from_nzta` for how this is used.

**No structured road/route identifier anywhere in the real schema -
settles the works-to-LINZ join question directly.** The real field list
(``locationArea``, ``directLineDistance1``-``3``, ``alternativeRoute``) is
free text only (e.g. ``"SH 80 Pukaki to Mt Cook (Aoraki Mt Cook
Highway)"``) - NZTA's own state-highway Location Referencing (route +
displacement) lives in a genuinely separate API this layer doesn't carry
at all. So :mod:`streetworks.common.from_nzta` does not populate
``WorksSite.street_ref`` - there is no stated identifier to join LINZ's
``road_id`` against, only free text, and a name-match crosswalk would be
inferred, not stated, the same SA-``ROAD_NO`` discipline. LINZ (see
:mod:`streetworks.linz`) stands on its own as this cluster's gazetteer,
not linked to NZTA's works.

**Geometry**: point only (confirmed ``esriGeometryPoint`` from the live
layer definition). Native spatial reference is **EPSG:2193 (NZGD2000 / New
Zealand Transverse Mercator 2000)** - confirmed from the live layer
definition - but ``outSR=4326`` is confirmed honoured live (real New
Zealand-range WGS84 coordinates returned, e.g.
``[174.773985779427, -36.8728584510707]``, genuine Auckland-area
territory), so no reprojection guard is needed.

**Real identifiers**: ``eventId`` (a real, genuinely unique integer
business identifier, confirmed unique across all 104 real records) is
what :mod:`streetworks.common.from_nzta` keys ``Works.reference`` on -
never ``OBJECTID`` (the layer's internal Esri row id). A real ``GlobalID``
GUID is also present but ``eventId`` is the source's own stated business
key, the more natural analogue to WA's ``GlobalID``/TAS's ``ID``.

**A real, currently-dead field**: ``restrictions`` is confirmed always
``null`` in every real record checked (0/104 populated) - a real field,
just currently unused, the same "field exists but nothing has ever
populated it" finding as WA's ``SeeMoreName``.

**Data-quality note from the portal's own description, dated 3 Oct
2024**: ``eventComments``/``alternativeRoute``/``eventModified`` were
previously null-only fields, repaired as of that date - so an "these
fields are always empty" assumption sourced from before then would be
stale; confirmed live (2026-08-02) that all three are genuinely populated
on real records now.

**Credentials**: none. Confirmed live - every query above succeeded with
no authentication.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..arcgis.client import ArcGISFeatureClient

__all__ = ["BASE_URL", "ROAD_EVENTS_LAYER", "ROAD_AREA_EVENTS_LAYER", "NztaClient"]

JSON = dict[str, Any]

BASE_URL = "https://services.arcgis.com/CXBb7LAjgIIdcsPt/arcgis/rest/services/NZTA_Highway_Information/FeatureServer"

#: Point events - roadworks live here. See module docstring.
ROAD_EVENTS_LAYER = 0

#: Polyline "Area Warning" events - confirmed live to be entirely
#: non-roadworks (53/53 real records). Not built - see module docstring.
ROAD_AREA_EVENTS_LAYER = 1

#: Real, confirmed-live values meaning roadworks specifically - see module
#: docstring for the full eventType/status/planned correlation.
_ROADWORKS_WHERE = "eventType IN ('Road Work', 'Scheduled Road Work')"


class NztaClient:
    """Fetch New Zealand state-highway road events from Waka Kotahi NZTA's
    ArcGIS-hosted feed. No credentials required - see module docstring.

    >>> from streetworks.nzta import NztaClient
    >>> from streetworks.common import from_nzta
    >>> with NztaClient() as nzta:  # doctest: +SKIP
    ...     works_list = from_nzta(list(nzta.iter_roadworks()))
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_road_events(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Every real point event (GeoJSON ``Feature`` dicts) from layer 0
        - every ``eventType``, not just roadworks. See
        :meth:`iter_roadworks` for the roadworks-only convenience."""
        yield from self._arcgis.iter_features(
            BASE_URL, ROAD_EVENTS_LAYER, where=where, out_fields="*", out_sr=4326
        )

    def iter_roadworks(self, *, where: str = _ROADWORKS_WHERE) -> Iterator[JSON]:
        """``eventType IN ('Road Work', 'Scheduled Road Work')`` - a real,
        confirmed-live filter (96/104 real records in one pull), not a
        guess. See module docstring."""
        yield from self.iter_road_events(where=where)

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> NztaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
