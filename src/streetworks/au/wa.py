"""Western Australia: Main Roads WA's WebEOC Roadworks - real-time roadwork
data feeding the Main Roads Travel Map (``travelmap.mainroads.wa.gov.au``),
over a public ArcGIS REST Feature Service. The third
:mod:`streetworks.au` member, and the third genuinely distinct AU shape:
NSW is one feed, many layers, sharing a schema; Victoria is two
independent, differently-shaped systems; WA is a single ArcGIS
``FeatureServer`` layer - a new client *protocol*, not just a new schema.
**Credential-free, live-verified and shipped with a real fixture from day
one** - unlike NSW/Victoria, this module never went through a
Credentials-wanted phase.

**Architecture: a thin wrapper over the existing, generic**
:class:`~streetworks.arcgis.client.ArcGISFeatureClient` - **not a new
pagination implementation.** That client was already built and live-hardened
against two real ArcGIS deployments with opposite pagination behaviour
(Jersey's broken ``resultOffset``, TIGERweb's genuine one - see
:mod:`streetworks.arcgis.client`'s own docstring) before this module
existed; :class:`WaMainRoadsClient` just supplies this service's own
``base_url``/``layer_id``, the same shape :mod:`streetworks.arcgis.jersey`
already established. WA's own layer states genuine
``advancedQueryCapabilities.supportsPagination: true`` (confirmed live) and
its real total (227 records, one live pull) sits well under its own
``maxRecordCount`` (2000) - so a single unpaged query already returns
everything today - but :meth:`WaMainRoadsClient.iter_roadworks` still pages
properly through the shared client rather than assuming that stays true as
the dataset grows.

**Gating check 1 - is ``outSR=4326`` honoured? Verified live, not assumed
- yes, for this service, but the runtime guard is built anyway.** Layer 2's
native spatial reference is Web Mercator (``wkid: 102100``/``latestWkid:
3857``), and a sibling ArcGIS deployment in this same SDK (Jersey's
``roadworks.gov.je``) has been confirmed to silently *ignore* ``outSR``
entirely - so this could not be assumed correct without checking. A live
``outSR=4326`` query against real WA data returned genuine WGS84-range
values (e.g. ``[116.410315549036, -32.8307254877164]``, real Boddington
territory) - honoured correctly. Because GeoJSON's own output strips any
per-feature CRS statement (only a *service-level* ``crs`` member is
present, discarded once :meth:`~streetworks.arcgis.client.ArcGISFeatureClient.iter_features`
yields individual features), a caller downstream of that call has no way
to re-derive what CRS a given feature came back in - so this module builds
a **runtime coordinate guard** in
:func:`streetworks.common.from_au_wa_mainroads._coordinate` regardless of
today's confirmed-good result: any point outside plausible WGS84 degree
range (``abs(lon) > 180`` or ``abs(lat) > 90``) is treated as unreprojected
Web Mercator metres and converted explicitly, never silently trusted
either way. This makes the adapter correct whether or not ``outSR`` stays
honoured on any given day, matching this SDK's standing "verify, don't
assume" CRS discipline.

**A deliberate deviation from the source brief's suggested implementation,
worth recording**: the brief suggested ``pyproj.Transformer`` for the
Web-Mercator-to-WGS84 fallback path. This module uses a small closed-form
spherical-Mercator inverse formula instead (see
:func:`streetworks.common.from_au_wa_mainroads._web_mercator_to_wgs84`) -
**not** an approximation layered on top of ``pyproj``'s geodetic engine,
but the *exact* algebraic inverse of how EPSG:3857 itself is defined
(Web Mercator is already a spherical, not ellipsoidal, projection by
specification - there is no additional accuracy ``pyproj`` would add for
this specific pair). Chosen to preserve this SDK's explicit,
repeatedly-stated design constraint of no GDAL/heavy geospatial
dependencies - the same reasoning
:class:`~streetworks.arcgis.client.ArcGISFeatureClient`'s own module
docstring states for why it exists in the first place ("no GDAL and no
geospatial dependency - this SDK's standard-library-plus-httpx property is
preserved"). Adding ``pyproj`` as a new hard dependency for one adapter's
defensive fallback (unexercised against real data today, since ``outSR``
is confirmed honoured) would have been a real regression of that property.

**Gating check 2 - date-string format, pinned from real data, not
guessed.** ``DateStarte``/``EstimatedC``/``EntryDate`` are all
``esriFieldTypeString`` (confirmed from live layer metadata), not native
date fields. A full live pull (227 real records, 681 date-field values)
confirms the format is **``DD/MM/YYYY HH:MM:SS``** unambiguously: 397 of
those values have a first component greater than 12 (e.g.
``"28/01/2025 15:29:14"``), which can only be a day, never a month; zero
values have a second component greater than 12. Locked via
:data:`streetworks.common.from_au_wa_mainroads._DATE_FORMAT`, never a
locale-guessing parser. Real value ranges confirm the item catalogue's own
description ("Please refer to the attributes 'DateStarte' and
'EstimatedC' for roadwork start date and estimated date of completion") -
``DateStarte`` is the real/planned start, ``EstimatedC`` is explicitly an
*estimate* of completion, graded :attr:`~streetworks.common.DateConfidence.ESTIMATED`
accordingly, never upgraded to ``VERIFIED``. **No timezone is stated in
any real value** - Western Australia is AWST (UTC+8) year-round with no
daylight saving, so unlike Victoria's genuinely ambiguous AEST/AEDT case, a
caller *could* safely attach a fixed ``+08:00`` - but this module still
parses to a timezone-**naive** ``datetime``, per this SDK's standing "never
state what the source doesn't" discipline; a caller who wants an aware
timestamp can attach ``+08:00`` themselves, safely, given the fixed offset
noted here.

**``WorkStatus`` is a real field, confirmed always empty** in a full live
pull (0/227 populated - every real value was ``""``). Passed through
honestly as ``None`` when empty (see :mod:`streetworks.common.from_au_wa_mainroads`)
rather than fabricating a status - **there is currently no live signal in
this feed distinguishing "confirmed active" from "planned," which is why
every :class:`~streetworks.common.WorksSite` this module builds grades
:attr:`~streetworks.common.DateConfidence.ESTIMATED`, never ``VERIFIED``**,
regardless of dates - a stronger version of NSW's own "never promote past
ESTIMATED" choice, since WA has no status field populated at all to
consider promoting from.

**``Road`` carries a real, undocumented sentinel value, confirmed live and
handled explicitly, not by accident**: 28 of 227 real records (~12.3%)
state ``Road`` as the **literal string ``"LOCAL ROAD"``** (all-caps, not a
real road name) rather than a named/numbered state road - and in every one
of those 28 records, and *only* those, ``LocalRoadName`` carries the real
local road name instead (confirmed live: the two fields are perfectly
mutually exclusive across all 227 records - never both empty, never both
populated). :func:`streetworks.common.from_au_wa_mainroads._road_name`
resolves this: use ``LocalRoadName`` when ``Road == "LOCAL ROAD"``, else
``Road`` itself - never surfaces the literal sentinel string to a caller as
if it were a real road name.

**``network_scope`` - default ``UNKNOWN``, not promoted, per the brief's own
instruction to check real data before promoting.** Main Roads WA's remit is
the state road network, but the real ``Road == "LOCAL ROAD"`` minority
above is genuinely local-road-only - and, unlike NSW's real minority
(6/363, ~1.7% - small enough that :attr:`~streetworks.registry.NetworkScope.STRATEGIC`
with the minority noted was judged reasonable there), WA's real local-road
minority is **~12.3%** - over one in eight real records - a large enough
genuine local-road component that promoting past ``UNKNOWN`` would
overstate this feed's real state-network purity. Honest-unknown over
confident-guess, exactly as the brief asked.

**``WorkType`` real values, confirmed live - one real value beyond the
source's own documented list.** The ArcGIS item's own catalogue
description states four work types: Maintenance, Resurfacing, Upgrades,
Utility works. A full live pull confirms all four *plus a fifth,
undocumented real value*: ``"PTA Works"`` (3/227 real records, e.g. "Great
Eastern Hwy at Helena St, Midland - PTA Works") - plausibly Public
Transport Authority-coordinated works, not confirmed from any document,
carried through as-is like every other real ``WorkType`` value, not
filtered out.

**``SeeMoreName``/``SeeMoreUrl`` - confirmed live, not as documented in the
brief's field map.** ``SeeMoreName`` is **always ``null``** in every real
record checked (0/227 populated) - genuinely dead in this data, despite
existing as a field. ``SeeMoreUrl`` is populated on 35/227 (~15%) and is a
genuine reference link (a project page or, sometimes, a detour-map image
URL directly) - but **not always a well-formed absolute URL**: one real
value observed live is a bare domain-and-path string with no ``https://``
scheme at all (``"www.mainroads.wa.gov.au/projects-initiatives/..."``),
carried through exactly as stated, never silently prefixed with a scheme
that wasn't there.

**``Id``/``FID``/``GlobalID`` - three real identifiers, one real key.**
``GlobalID`` is a genuine GUID, confirmed unique across all 227 real
records - this is what :func:`streetworks.common.from_au_wa_mainroads.from_au_wa_mainroads`
keys ``Works.reference`` on. ``FID`` is the layer's real ``objectIdField``
(confirmed from live layer metadata) - **never used for identity**: this is
an ``isView: true`` layer (confirmed live), so its own OIDs are reassignable
view artefacts, the same caution this SDK already applies to other ArcGIS
view layers. ``Id`` (a real, always-integer WebEOC identifier, unlike
NSW's real float-id quirk) is retained on ``.raw`` only, not built into any
composite reference - WA has exactly one layer, unlike NSW's multi-layer
collision risk, so no compositing is needed.

**``EntryDate`` has no home on the canonical model** - a real, populated
field (record-creation timestamp in WebEOC), but neither
:class:`~streetworks.common.Works` nor :class:`~streetworks.common.WorksSite`
models a "record created" concept the way this SDK's ``raw`` fields do for
other providers' unmodelled real fields (e.g. Jersey's unlabelled ``A``-``E``
integers) - kept in ``.raw`` only, not force-mapped onto ``proposed_start``
or anything else.

**Licence: Creative Commons Attribution 4.0, confirmed live from the
ArcGIS item's own catalogue metadata** (``licenseInfo``), not merely
inferred from the layer's own empty ``copyrightText`` (confirmed live to be
``""`` - attribution genuinely does *not* ride on the layer itself, exactly
as the brief expected). The catalogue's real ``accessInformation`` states
``"Main Roads WA"``; the licence's own required attribution notice (its
real text, quoted from the catalogue) is: *"The Commissioner of Main Roads
is the creator and owner of the data and Licenced Material, which is
accessed pursuant to a Creative Commons (Attribution) Licence, which has a
disclaimer of warranties and limitation of liability."* This module's
``administrative_area`` uses **"Main Roads Western Australia"** (matching
the brief's instruction and this SDK's operator-as-authority convention
already applied to Autobahn GmbH/TfNSW/DTP) - the real catalogue metadata's
own short form (``"Main Roads WA"``) and the licence notice's own legal
name (``"the Commissioner of Main Roads"``) are recorded here for anyone
who needs the exact real strings.

**Geometry**: real coordinates are GeoJSON-native ``[lon, lat]`` (WGS84
after the coordinate guard above), the same axis order NSW/Victoria use -
never flipped to DATEX's ``(lat, lon)`` convention. Point geometry only -
confirmed from live layer metadata (``esriGeometryPoint``) - a centroid
marker, no extent published, nothing further to decode.

**Credentials: none** - confirmed live, every real query above succeeded
with no authentication of any kind, matching the brief and this service's
public ``isView: true`` Feature Service design.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..arcgis.client import ArcGISFeatureClient

__all__ = ["BASE_URL", "ROADWORKS_LAYER", "WaMainRoadsClient"]

JSON = dict[str, Any]

BASE_URL = "https://services2.arcgis.com/cHGEnmsJ165IBJRM/arcgis/rest/services/WebEoc_Roadworks/FeatureServer"

#: The real (and only) roadworks layer - esriGeometryPoint, confirmed live.
#: See module docstring.
ROADWORKS_LAYER = 2


class WaMainRoadsClient:
    """Fetch WA roadworks from Main Roads WA's WebEOC Roadworks ArcGIS
    Feature Service. No credentials required - see module docstring.

    >>> from streetworks.au.wa import WaMainRoadsClient
    >>> from streetworks.common import from_au_wa_mainroads
    >>> with WaMainRoadsClient() as wa:  # doctest: +SKIP
    ...     works_list = from_au_wa_mainroads(list(wa.iter_roadworks()))
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_roadworks(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Yield every real roadworks feature (GeoJSON ``Feature`` dicts),
        paged correctly via the shared
        :class:`~streetworks.arcgis.client.ArcGISFeatureClient` - see
        module docstring for why this layer doesn't need its own bespoke
        pagination logic. Requests ``outSR=4326`` (confirmed honoured live
        - see module docstring for the runtime guard that makes this safe
        either way)."""
        yield from self._arcgis.iter_features(
            BASE_URL, ROADWORKS_LAYER, where=where, out_fields="*", out_sr=4326
        )

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> WaMainRoadsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
