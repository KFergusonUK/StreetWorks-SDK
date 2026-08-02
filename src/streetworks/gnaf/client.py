"""Australia: G-NAF (Geocoded National Address File) + the national road
network - this SDK's first Australian gazetteer coverage, over the
**Digital Atlas of Australia** (``digital.atlas.gov.au``), a whole-of-
government ArcGIS Online platform, not Geoscape's own commercial API.

.. attention::
   **Confirmed live (2026-08-02)** against real, unauthenticated pulls -
   both :meth:`GnafClient.iter_addresses` (15,901,249 real addresses) and
   :meth:`GnafClient.iter_roads` (4,346,217 real road segments). Neither
   is a Credentials-wanted scaffold.

**A real correction to the source investigation.** The brief that started
this build concluded Australia has "no clean national *open* road-
centreline register with identifiers" because Geoscape's own **Roads**
product is commercial. That's true of Geoscape's direct API - but the
Digital Atlas of Australia publishes an open derivative anyway: real
national **address points** (from G-NAF) and a real national **road
network** (from Geoscape Roads), both re-published under CC BY 4.0 as
ArcGIS Feature Services, confirmed live by resolving each dataset's
Digital Atlas item to its underlying ``services-ap1.arcgis.com``
``FeatureServer`` URL - not documented anywhere on the dataset landing
pages themselves, which are JS-rendered and don't state it. This
supersedes the brief's own fallback plan (SA's CRRS / Tasmania's State
Roads as state-scoped consolation prizes) - AU now has a genuine
*national* road register, live-verified, the same tier as NZ's LINZ.

**National Address Points (G-NAF derivative), confirmed live.** Real
total **15,901,249** addresses (``returnCountOnly`` on the live layer),
point geometry, native SR **EPSG:7844 (GDA2020)** - ``outSR=4326``
confirmed honoured live (real coordinates, e.g. a real ACT address at
``(149.13066859, -35.16709003)``). The real stated identifier is
``ADDRESS_DETAIL_PID`` (G-NAF's own PID, e.g. ``"GAACT714958506"``) - the
nearest AU equivalent to a USRN, but address-scoped, not street-scoped:
there is **no separate street/locality PID** on this derivative (the full
multi-table G-NAF product has one, ``STREET_LOCALITY_PID``, but this
ArcGIS derivative flattens it away, the same "no street table of its
own" shape already seen in this SDK's BAG route - see
:mod:`streetworks.common.from_bag`). Street identity here is text only:
``STREET_NAME``/``STREET_TYPE``, no persistent id to key a
:class:`~streetworks.common.gazetteer.Street` on. Licence: **CC BY 4.0**,
plus a genuine, mandatory extra restriction - open G-NAF must not be used
to generate an address or address list for **sending mail** unless each
address is independently verified against a secondary source (confirmed
verbatim from the item's own ``licenseInfo``) - irrelevant to gazetteer
use, but binding on any vendored fixture bytes, so it's stated here
rather than silently dropped.

**National Roads (Geoscape Roads derivative), confirmed live - genuinely
comprehensive, not a highways-only skim.** Real total **4,346,217**
segments, polyline geometry, same native SR/``outSR`` behaviour as
addresses. Real ``hierarchy`` values span the *entire* network, from
``NATIONAL OR STATE HIGHWAY`` (120,293) down through ``LOCAL ROAD``
(1,918,246, the largest single value), ``ACCESS ROAD``, ``FOOTPATH``,
``CYCLEPATH`` and ``VEHICLE TRACK`` - real local-road reach beyond
anything else this SDK has queried live, TIGERweb's own local layer
included. The real stated identifier is ``road_id`` ("Persistent
identifier for a roads feature", per the layer's own field description) -
segment-scoped, not an aggregated named-street id (no separate
named-street layer was found alongside this one), so
:mod:`streetworks.common.from_gnaf` emits
:class:`~streetworks.common.gazetteer.Segment` only, never
:class:`~streetworks.common.gazetteer.Street` - the same "no synthetic
streets" discipline :mod:`streetworks.common.from_nwb` already
established. Real per-segment attributes: ``jurisdiction_control`` (a
genuine per-record authority, e.g. ``"Transport for New South Wales
(controlled roads)"``, richer than a hardcoded value), ``national_route``/
``state_route``, decomposed ``street_name``/``street_type``/
``street_suffix`` (separate from ``full_street_name``, the LINZ-style
split), ``surface``, ``speed``, ``one_way``. A filtered sibling, **Major
Roads** (highways/arterial/sub-arterial only, 535,072 records), also
exists on the same platform but is a strict subset of this layer - not
built separately. Licence: **CC BY 4.0**, no extra restriction.

**No stated join between the two layers - resolves the brief's join
question, on better evidence than it had.** Addresses carry no
``road_id`` reference; roads carry no address reference. The only
possible link is ``STREET_NAME``/``STREET_TYPE`` against
``full_street_name`` - a name match, forbidden by this SDK's
stated-identifiers-only rule (see :mod:`streetworks.common.gazetteer`'s
own module docstring). So :class:`~streetworks.common.gazetteer.Address`
and :class:`~streetworks.common.gazetteer.Segment` here stand alone from
each other, same conclusion the brief reached about the *works* cluster
(no AU roadworks feed states a G-NAF/road identifier either), now settled
for the gazetteer side too - on the real open register, not the
commercial one the brief assumed was the only option.

**Credentials**: none for either method.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..arcgis.client import ArcGISFeatureClient

__all__ = [
    "ADDRESSES_BASE_URL",
    "ADDRESSES_LAYER",
    "ROADS_BASE_URL",
    "ROADS_LAYER",
    "GnafClient",
]

JSON = dict[str, Any]

#: National Address Points (G-NAF derivative) - confirmed live, no
#: credentials. See module docstring.
ADDRESSES_BASE_URL = (
    "https://services-ap1.arcgis.com/ypkPEy1AmwPKGNNv/arcgis/rest/services/"
    "national_address_points/FeatureServer"
)
ADDRESSES_LAYER = 0

#: National Roads (Geoscape Roads derivative) - the full network, not the
#: filtered "Major Roads" subset. Confirmed live, no credentials. See
#: module docstring.
ROADS_BASE_URL = (
    "https://services-ap1.arcgis.com/ypkPEy1AmwPKGNNv/arcgis/rest/services/"
    "National_Roads/FeatureServer"
)
ROADS_LAYER = 0


class GnafClient:
    """Fetch Australian address and road gazetteer data from the Digital
    Atlas of Australia. No credentials for either method - see module
    docstring for why this is a genuinely different, better route than
    Geoscape's own commercial G-NAF/Roads APIs.

    >>> from streetworks.gnaf import GnafClient
    >>> from streetworks.common import from_gnaf_address
    >>> with GnafClient() as gnaf:  # doctest: +SKIP
    ...     addresses = [from_gnaf_address(a) for a in gnaf.iter_addresses(where="STATE='ACT'")]
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_addresses(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Every real National Address Points feature (GeoJSON ``Feature``
        dicts) matching ``where`` - confirmed live, no credentials. Real
        total 15,901,249 - always scope ``where`` (e.g. ``"STATE='ACT'"``)
        rather than pulling the whole layer. See module docstring."""
        yield from self._arcgis.iter_features(
            ADDRESSES_BASE_URL, ADDRESSES_LAYER, where=where, out_fields="*", out_sr=4326
        )

    def iter_roads(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Every real National Roads feature (GeoJSON ``Feature`` dicts)
        matching ``where`` - confirmed live, no credentials. Real total
        4,346,217 - always scope ``where`` (e.g. ``"state='ACT'"``) rather
        than pulling the whole layer. See module docstring."""
        yield from self._arcgis.iter_features(
            ROADS_BASE_URL, ROADS_LAYER, where=where, out_fields="*", out_sr=4326
        )

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> GnafClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
