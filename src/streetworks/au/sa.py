"""South Australia: Traffic SA / DIT Roadworks - the fifth
:mod:`streetworks.au` member, over a public ArcGIS **MapServer** (not
WA's FeatureServer). The most architecturally interesting AU provider so
far - the first whose works feed states numeric road identifiers
(``ROAD_NO``, ``GIS_LINK_ID``), not names only - and the least verified.

.. attention::
   **PHASE 1 SCAFFOLD - genuinely blocked on TWO access gates, not
   credential-free.** An earlier draft of the investigation this module is
   built from called SA credential-free, going only from the fact that the
   layer *definition* (``?f=json``) is public - that was wrong, corrected
   the same day. The layer **metadata** is public; the **query operation
   is token-gated**: four clean attempts (three ``where`` clauses across
   two response formats, including ArcGIS's own form-built request UI)
   all returned a genuine HTTP 400 ("Failed to execute query"), and the
   service directory page itself carries ``Login | Get Token`` links.
   Separately, and independently, ``maps.sa.gov.au`` **CloudFront-blocks
   some countries' network egress entirely** (confirmed live from this
   SDK's own build environment, and separately from a UK egress - a
   403 with the literal body *"The Amazon CloudFront distribution is
   configured to block access from your country"* - while a Poland VPN
   egress reached the layer *metadata*, though every query attempt from
   that same egress still 400'd on the token gate). Whether an ArcGIS
   token is genuinely **self-service** (obtainable at
   ``location.sa.gov.au/arcgis/tokens/``) or requires a data agreement
   with DIT is **unresolved** - that token host itself returned a
   CloudFront 403 from the one egress that could reach the layer metadata,
   so it has never been reached to check. **No real feature has been
   retrieved by anyone working on this module.** The schema below is
   ground truth (a real live layer-definition pull, not documentation),
   but the join-key question this provider exists to answer, and every
   other real-data question, stays open until someone with a working
   token *and* an allowed-region egress runs ``scripts/smoke_test.py``.

**Why build this now, half-blocked, rather than wait**: the schema itself
is already ground truth (the layer definition is public and was
successfully pulled), the shared :class:`~streetworks.arcgis.client.ArcGISFeatureClient`
already supports the one real extension this needed (token passthrough via
``extra_params`` - added alongside this module, see that client's own
module docstring), and shipping the wiring now means graduation only needs
a token and a working egress, not a from-scratch build - the same
Credentials-wanted shape as :mod:`streetworks.datex2.trafikverket`/
:mod:`streetworks.datex2.vejdirektoratet`, except with an extra
geographic dimension neither of those has.

**Service** (from the live layer-0 definition, real ground truth):
``https://maps.sa.gov.au/arcgis/rest/services/DPTIExtTransport/TrafficSAOpenData2/MapServer``.
**Endpoint name drift, unresolved**: data.sa.gov.au's own catalogue links
to ``TrafficSAOpenData`` (no ``2``); the live service resolves under
``TrafficSAOpenData2``. Whether the un-suffixed name is a working alias, a
redirect, or simply stale catalogue text has not been checked (the same
catalogued-URL-vs-live-URL drift NSW's own Developer Guide had - see
:mod:`streetworks.au.nsw`) - ``...OpenData2`` is used here as the name the
live service itself resolves under.

**Layer 0 = Roadworks *and* Incidents, genuinely mixed** - ``REC_TYPE``
is the real, confirmed-live discriminator field, but **its actual
roadworks-meaning value has never been seen** (no query has ever
succeeded). Rather than fabricate a filter string with zero evidence
behind it - a real ``where="REC_TYPE='...'"`` guess could silently match
nothing, or worse, silently match the wrong records, and nobody would
know either way - :meth:`TrafficSaClient.iter_roadworks` defaults to
**no** ``REC_TYPE`` filter at all, returning layer 0's honest, full mix.
Once a real pull confirms the value, pass it explicitly via
``where="REC_TYPE='<real value>'"`` yourself, or wait for this module to
be updated. **Layer 1 = road closures and detours** - a sibling, real
layer, not consumed by :meth:`~TrafficSaClient.iter_roadworks` at all;
:meth:`~TrafficSaClient.iter_closures` reaches it directly, opt-in, with
the same "no confirmed record has ever been seen" caveat.

**The headline open question, unresolved**: is ``ROAD_NO`` South
Australia's **Common Road Referencing System (CRRS)** number - a real,
live-stated field on every DPTI-maintained road - and does it, if
populated, key to a State Maintained Roads / CRRS road register? Every
other AU works feed built so far (NSW, Victoria, WA, QLD) is name-only,
leaving the stated-identifier-join gap open per this SDK's own
name-is-not-a-join rule; SA is the first candidate to close it, *if*
``ROAD_NO`` turns out to be real, populated, and genuinely joinable - none
of which is confirmed. Until it is, this module does **not** populate
``WorksSite.street_ref`` from ``ROAD_NO``/``GIS_LINK_ID`` - both values
are preserved on ``.raw`` only, never promoted to a join key this SDK
can't verify. See :mod:`streetworks.common.from_au_sa_trafficsa`.

**Schema** (real field list, from the live layer-0 ``?f=json`` definition -
ground truth, not documentation):

- ``ROADWORKS_AND_INCIDENTS_ID`` (string, 40) - the real display field.
  ``Works.reference`` is keyed on this, never ``ESRI_OID`` (an internal
  Esri row id, not this layer's own stated identifier).
- ``REC_TYPE`` (string, 200) - the roadworks-vs-incident discriminator
  (see above); real value unconfirmed.
- ``INCIDENT_ID`` (double) - populated on incident records, per the field
  name; unconfirmed whether it's ever populated on roadworks records too.
- ``DESCRIPTION`` (string, 200).
- ``START_DATE``/``END_DATE`` - real ``esriFieldTypeDate`` fields (epoch
  milliseconds UTC, the standard ArcGIS REST convention for this field
  type - not this feed's own peculiarity, so this part is confidently
  documented even without a real response). **No DD/MM-vs-MM/DD ambiguity
  here** - unlike WA's plain-string dates, these are typed, unlike
  anything else built in this cluster so far.
  ``START_DATE_STRING``/``END_DATE_STRING`` (string, 24) are real human
  display copies, not parsed here.
- ``ROAD_NO`` (double) - the headline candidate join key, see above.
- ``GIS_LINK_ID`` (double) - a second candidate identifier; what it
  references is unconfirmed.
- ``LOCAL_ROAD`` (string, 50) - a road name, likely populated where
  ``ROAD_NO`` is absent (a WA ``Road``/``LocalRoadName``-shaped split,
  unconfirmed whether it's actually structured that cleanly here).
- ``SIDE_STREET`` (string, 50), ``SUBURB`` (string, 50).
- ``LATITUDE``/``LONGITUDE`` (double) - explicit lat/lon attributes
  alongside the geometry's own ``SHAPE``. **Not used for this module's
  geometry** - whether they're genuinely WGS84 and agree with the
  reprojected ``SHAPE`` is unconfirmed (a feed has mislabelled lat/lon
  fields before - Belgium's Lambert-72-in-``<latitude>``/``<longitude>``-
  named-fields, see :mod:`streetworks.common.from_datex2`), so this
  module reprojects ``SHAPE`` itself via the same guard WA uses rather
  than trust two unverified attribute fields. Kept on ``.raw`` for anyone
  who wants to cross-check once real data exists.
- ``ACTIVE`` (string, 1) - an active flag; real encoding (``Y``/``N``,
  ``1``/``0``, something else) unconfirmed, so not used to grade
  ``DateConfidence`` - see :mod:`streetworks.common.from_au_sa_trafficsa`.
- ``TRAFFIC_DIR``/``NO_LANES_CLOSED``/``SPEED_LIMIT`` (string, 25 each) -
  semi-structured impact fields (discrete concepts, but stringly-typed) -
  a fourth distinct impact shape in this cluster, after Victoria's enum,
  QLD's richer enum, and WA's free prose.
- ``SHAPE`` (geometry) - native SR **102100/EPSG:3857** (Web Mercator),
  confirmed from the live layer definition, the same native CRS as WA's
  layer. ``ESRI_OID`` - the real ``objectIdField``; **never used for
  identity**, same caution as WA's ``FID``.

**Geometry**: point only (``esriGeometryPoint``, confirmed from the live
layer definition) - no linework, so no corridor-as-worksite trap here.
Reuses :mod:`streetworks.common._web_mercator` (the same closed-form
EPSG:3857 inverse WA's module introduced) - see that module's own
docstring for why a closed-form formula is used instead of ``pyproj``.

**Coverage - conflicting claims, unresolved.** The dataset's own
description says "metropolitan Adelaide area"; its "Geospatial Coverage"
metadata field says "South Australia." Until real coordinates settle
which is true, treat this as the narrowest-coverage AU provider so far and
grade :attr:`~streetworks.registry.NetworkScope` conservatively - see
:mod:`streetworks.common.from_au_sa_trafficsa`.

**Pagination**: this is a **MapServer**, not WA's FeatureServer - the
``/query?f=geojson`` interface is identical, and the shared
:class:`~streetworks.arcgis.client.ArcGISFeatureClient` is reused
unchanged (real layer metadata states genuine
``advancedQueryCapabilities.supportsPagination: true``, ``maxRecordCount``
1000), but whether a MapServer layer's ``resultOffset`` behaves like a
FeatureServer's in practice has never been checked against a real
response - :meth:`ArcGISFeatureClient.iter_features`'s own live-verification
strategy (never trusting the metadata claim alone) covers this the same
way it already covers Jersey's broken case, so no MapServer-specific
handling was added here on top of it - but this is unexercised, not
proven, for a MapServer specifically.

**Licence**: **CC BY 4.0**, confirmed on the data.sa.gov.au resource page
and portal-wide. DIT (Department for Infrastructure and Transport) as
publisher. No real fixture exists - the query gate means no real record
has ever been retrieved - so the test fixture here is synthetic, the same
"nothing to trim from" position :mod:`streetworks.datex2.trafikverket`/
:mod:`streetworks.datex2.vejdirektoratet` are in.

**Credentials**: an ArcGIS token from
``location.sa.gov.au/arcgis/tokens/`` - whether generating one is
self-service or requires contacting DIT is **unresolved** (see above). Env
var: ``SA_TRAFFICSA_TOKEN`` (see ``.env.example``,
``scripts/smoke_test.py``).

**What's still open** (all of it, until a token + working egress exist):

1. **Whether a query token is obtainable at all without a data agreement**
   - this gates every question below; if it turns out to be gated/by
   request, SA may not be publicly consumable the way Trafikverket/
   Vejdirektoratet are, a materially worse story than either.
2. **``ROAD_NO``/``GIS_LINK_ID`` population and real join semantics** -
   the single most important question once access exists.
3. Whether ``LATITUDE``/``LONGITUDE`` are genuinely WGS84 and agree with
   the reprojected ``SHAPE``.
4. Real coverage - metro-Adelaide vs the "South Australia" metadata claim.
5. The real ``REC_TYPE`` value(s) meaning roadworks (vs incidents).
6. The canonical endpoint - ``TrafficSAOpenData2`` vs the un-suffixed
   ``TrafficSAOpenData`` data.sa.gov.au links to.
7. Whether MapServer ``resultOffset`` paging genuinely works the way
   WA's FeatureServer does.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from typing import Any

import httpx

from ..arcgis.client import ArcGISFeatureClient

__all__ = ["BASE_URL", "ROADWORKS_AND_INCIDENTS_LAYER", "CLOSURES_LAYER", "TrafficSaClient"]

warnings.warn(
    "streetworks.au.sa is a Credentials-wanted scaffold: built against a "
    "real live layer definition (see module docstring), but genuinely "
    "blocked on two access gates - a token-gated query endpoint and a "
    "geo-restricted host - so no real feature has ever been retrieved. Can "
    "you reach an ArcGIS token from an allowed region? Running the smoke "
    "test and reporting back one real trimmed record would confirm this "
    "adapter - see the 'help wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues for exactly "
    "what's needed.",
    UserWarning,
    stacklevel=2,
)

JSON = dict[str, Any]

BASE_URL = "https://maps.sa.gov.au/arcgis/rest/services/DPTIExtTransport/TrafficSAOpenData2/MapServer"

#: Roadworks and Incidents, genuinely mixed - filter REC_TYPE once its
#: real roadworks value is confirmed. See module docstring.
ROADWORKS_AND_INCIDENTS_LAYER = 0

#: Road closures and detours - a sibling layer, opt-in, not consumed by
#: iter_roadworks(). See module docstring.
CLOSURES_LAYER = 1


class TrafficSaClient:
    """Fetch South Australian roadworks/incidents from Traffic SA's DPTI
    ArcGIS MapServer. **Phase 1 scaffold, genuinely blocked on two access
    gates - see module docstring.** No real feature has been retrieved by
    this module yet.

    Requires an ArcGIS query token (``location.sa.gov.au/arcgis/tokens/``
    - whether self-service is unconfirmed, see module docstring).

    >>> from streetworks.au.sa import TrafficSaClient
    >>> from streetworks.common import from_au_sa_trafficsa
    >>> with TrafficSaClient(token=token) as sa:  # doctest: +SKIP
    ...     works_list = from_au_sa_trafficsa(list(sa.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        token: str,
        base_url: str = BASE_URL,
        client: httpx.Client | None = None,
    ) -> None:
        if not token:
            raise ValueError("token is required - see module docstring")
        self.token = token
        self.base_url = base_url.rstrip("/")
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_events(self, layer_id: int, *, where: str = "1=1") -> Iterator[JSON]:
        """The shared primitive both :meth:`iter_roadworks` and
        :meth:`iter_closures` build on - every real GeoJSON feature from
        ``layer_id`` matching ``where``, with the query token attached to
        every page request (never to the layer-metadata call, which stays
        public - see :class:`~streetworks.arcgis.client.ArcGISFeatureClient`'s
        own module docstring)."""
        yield from self._arcgis.iter_features(
            self.base_url,
            layer_id,
            where=where,
            out_fields="*",
            out_sr=4326,
            extra_params={"token": self.token},
        )

    def iter_roadworks(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Layer 0's full ``ROADWORKS_AND_INCIDENTS`` mix - **not filtered
        to roadworks-only**, since the real ``REC_TYPE`` value meaning
        roadworks has never been confirmed (no query has ever succeeded -
        see module docstring). Inspect ``properties["REC_TYPE"]`` yourself,
        or pass ``where="REC_TYPE='<real value>'"`` once you've confirmed
        it against real data."""
        yield from self.iter_events(ROADWORKS_AND_INCIDENTS_LAYER, where=where)

    def iter_closures(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Layer 1, road closures and detours - opt-in, a sibling of
        :meth:`iter_roadworks`, not consumed by it. Same "never verified
        against real data" caveat, see module docstring."""
        yield from self.iter_events(CLOSURES_LAYER, where=where)

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> TrafficSaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
