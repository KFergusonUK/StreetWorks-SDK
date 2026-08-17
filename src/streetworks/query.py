"""UK-first "works near here" join layer.

One call: a WGS84 point and/or a UK USRN, plus a radius, in; a mixed list
of canonical :class:`~streetworks.common.Works` out. This composes existing
clients and ``from_<provider>`` converters - it is not a new data model,
and it is not the uniform ``search()`` facade the registry deliberately
refused to grow (a method that looked like a spatial query but was
actually a 170 MB download or 113 sequential HTTP calls would make the
SDK untrustworthy; see :mod:`streetworks.registry`).

The starting hypothesis of ``works_near(lat, lon)`` / ``works_near_usrn``
is kept, but v1 is a **documented subset**, not "every registered
roadworks provider". Providers are chosen from the registry (verified,
credentials actually supplied, geometry or a USRN the converter
populates) rather than guessed from names.

**v1 distance path** (WGS84 ``EPSG:4326`` only, haversine, mean Earth
radius 6 371 000 m - the same constant
:mod:`examples.compare_active_works` already uses):

* ``trafficwales`` - always, keyless. Traffic Wales RSS roadworks
  (motorway/trunk only). Live-verified ``georss:point``.
* ``nationalhighways`` - only when the caller passes a
  :class:`~streetworks.datex2.NationalHighwaysClient` or a subscription
  key. Planned SRN closures, DATEX ``posList`` in WGS84. v1 pulls
  ``closureType=planned`` only.

Distance is to :attr:`~streetworks.common.Coordinate.value` (the
representative point; first vertex of a line), not a geodesic-to-
linestring. Records whose only geometry is in another CRS are **skipped
for the distance path, never reprojected**. This SDK has no tested
WGS84→BNG transform, so Street Manager's ``EPSG:27700`` coordinates
cannot honestly participate in a lat/lon filter.

**v1 USRN path** (exact street match on populated USRN fields; radius is
unused unless a WGS84 point is also given):

* ``streetmanager`` - only when the caller passes a
  :class:`~streetworks.streetmanager.StreetManagerClient`. Queries
  ``reporting.iter_permits(usrn=...)`` (the same query-param passthrough
  other reporting filters use) and also filters converted records by
  ``Works.location_usrn`` / ``WorksSite.location_usrn`` /
  ``WorksSite.street_ref``. This is the caller's organisation's permits,
  not an England-wide public spatial search. Whether ``/permits`` honours
  ``usrn`` server-side is not independently re-verified in this module;
  the client-side filter is what keeps unmatched USRNs out of the result.
* ``srwr`` - only when the caller passes a local extract
  (``srwr_source``). Matches ``Works.location_usrn``. Will **not**
  download the national daily zip - that is the bulk-extract cost the
  registry design brief refused to hide behind a "near" call. The
  converter does not populate coordinates (phase WKT exists natively but
  is not mapped), so SRWR cannot join the distance path.

**Explicitly not in v1, and why:**

* TrafficWatchNI - verified RSS, no geometry, cannot distance-filter.
* OS Open USRN - a street gazetteer, not works; ~300 MB bulk GeoPackage,
  not a live spatial API. Resolve a USRN to a point yourself (or pass
  ``usrn=`` against SM/SRWR).
* TfL - no provider in this SDK.
* DataVIA, D-TRO - credentialed; streets / legal orders, not
  works-progress.
* Street Manager Open Data - receive-only SNS.
* Every non-UK roadworks feed (DGT, NDW, Autobahn, …) - a global sweep
  would hide mixed-CRS traps and large downloads.
* Credentials-wanted / unverified / :class:`~streetworks.exceptions.ProviderUnavailableError`
  scaffolds (Trafikverket, Vejdirektoratet, SA, NT, LINZ Roads, MapRoad)
  - never queried, even if a caller later grows this module's allowlist
  by mistake: :func:`v1_providers` consults ``ProviderEntry.verified``
  and ``credentials``.

**Never deduplicates across providers.** Two feeds can both correctly
report what looks like the same physical worksite. Every record is kept,
with ``provider``, ``territory``, ``administrative_area``, and ``.raw``
intact. See the README's "Never deduplicate across providers" note.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import IO, TYPE_CHECKING, Literal

from .registry import _REGISTRY, ProviderEntry

if TYPE_CHECKING:
    from .common.models import Coordinate, Works
    from .datex2 import NationalHighwaysClient
    from .streetmanager import StreetManagerClient

__all__ = [
    "EARTH_RADIUS_M",
    "V1_DISTANCE_PROVIDERS",
    "V1_USRN_PROVIDERS",
    "NearbyWorks",
    "haversine_m",
    "v1_providers",
    "works_near",
    "works_near_usrn",
]

#: Mean Earth radius in metres - same 6 371 km
#: :mod:`examples.compare_active_works` already uses for its haversine.
EARTH_RADIUS_M = 6_371_000.0

#: Registry keys that can join the WGS84 distance path in v1.
V1_DISTANCE_PROVIDERS = frozenset({"trafficwales", "nationalhighways"})

#: Registry keys that can join the USRN path in v1.
V1_USRN_PROVIDERS = frozenset({"streetmanager", "srwr"})

_WGS84_CRS = frozenset({"EPSG:4326", "CRS:84"})

Match = Literal["distance", "usrn"]


@dataclass(frozen=True)
class NearbyWorks:
    """One hit from :func:`works_near`.

    ``works`` is the canonical record. ``provider`` is the registry key.
    ``distance_m`` is the haversine distance in metres from the query
    point to the representative WGS84 coordinate, or ``None`` for a
    USRN-only match that has no WGS84 geometry. ``match`` says which
    path included it.
    """

    works: Works
    provider: str
    distance_m: float | None = None
    match: Match = "distance"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres on a sphere of radius
    :data:`EARTH_RADIUS_M`. Inputs are WGS84 latitude/longitude in
    degrees. This is a distance *comparison*, not a reprojection - the
    source coordinates are never transformed."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(min(1.0, a)))


def _entry(key: str) -> ProviderEntry:
    return next(e for e in _REGISTRY if e.key == key)


def _live_enough(entry: ProviderEntry, *, credentials_supplied: bool) -> bool:
    """Registry gate: verified, not a ProviderUnavailable scaffold, and
    credentials actually in hand when the entry needs them."""
    if not entry.verified:
        return False
    if entry.credentials is not None and not credentials_supplied:
        return False
    return True


def _has_nh_credentials(
    national_highways: NationalHighwaysClient | None,
    national_highways_key: str | None,
) -> bool:
    key = (national_highways_key or "").strip()
    return national_highways is not None or bool(key)


def v1_providers(
    *,
    lat: float | None = None,
    lon: float | None = None,
    usrn: int | str | None = None,
    street_manager: StreetManagerClient | None = None,
    national_highways: NationalHighwaysClient | None = None,
    national_highways_key: str | None = None,
    srwr_source: str | Path | IO[str] | None = None,
) -> tuple[str, ...]:
    """Which v1 providers :func:`works_near` will actually query for this
    call - derived from the registry plus what the caller supplied, never
    a hand-maintained "query these" list that can drift from
    ``verified`` / ``credentials``.

    Unverified and credential-gated-without-credentials entries are
    absent even if their key is in :data:`V1_DISTANCE_PROVIDERS` /
    :data:`V1_USRN_PROVIDERS`.
    """
    has_point = lat is not None and lon is not None
    has_usrn = usrn is not None
    planned: list[str] = []

    if has_point:
        tw = _entry("trafficwales")
        if tw.key in V1_DISTANCE_PROVIDERS and _live_enough(tw, credentials_supplied=True):
            planned.append(tw.key)
        nh = _entry("nationalhighways")
        if (
            nh.key in V1_DISTANCE_PROVIDERS
            and _live_enough(
                nh,
                credentials_supplied=_has_nh_credentials(
                    national_highways, national_highways_key
                ),
            )
        ):
            planned.append(nh.key)

    if has_usrn:
        sm = _entry("streetmanager")
        if (
            sm.key in V1_USRN_PROVIDERS
            and street_manager is not None
            and _live_enough(sm, credentials_supplied=True)
        ):
            planned.append(sm.key)
        srwr = _entry("srwr")
        if (
            srwr.key in V1_USRN_PROVIDERS
            and srwr_source is not None
            and _live_enough(srwr, credentials_supplied=True)
        ):
            planned.append(srwr.key)

    return tuple(planned)


def _is_wgs84(coordinate: Coordinate) -> bool:
    return coordinate.crs in _WGS84_CRS


def _wgs84_points(works: Works) -> list[tuple[float, float]]:
    """Representative WGS84 points on a Works - the umbrella coordinate
    and each site's, de-duplicated. Non-WGS84 coordinates are ignored,
    not converted."""
    found: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for coordinate in (works.coordinate, *(site.coordinate for site in works.sites)):
        if coordinate is None or not _is_wgs84(coordinate):
            continue
        point = (float(coordinate.value[0]), float(coordinate.value[1]))
        if point not in seen:
            seen.add(point)
            found.append(point)
    return found


def nearest_wgs84_distance_m(works: Works, lat: float, lon: float) -> float | None:
    """Haversine distance to the nearest representative WGS84 point on
    ``works``, or ``None`` if it has no WGS84 geometry."""
    points = _wgs84_points(works)
    if not points:
        return None
    return min(haversine_m(lat, lon, plat, plon) for plat, plon in points)


def _normalise_usrn(usrn: int | str) -> str:
    text = str(usrn).strip()
    return str(int(text)) if text.isdigit() else text


def _usrn_matches(works: Works, usrn: str) -> bool:
    if works.location_usrn == usrn:
        return True
    for site in works.sites:
        if site.location_usrn == usrn:
            return True
        ref = site.street_ref
        if ref is not None and ref.scheme == "usrn" and ref.value == usrn:
            return True
    return False


def _fetch_traffic_wales() -> list[Works]:
    from .common import from_trafficwales
    from .trafficwales import Feed, TrafficWalesClient

    with TrafficWalesClient() as client:
        items = client.fetch(Feed.ROADWORKS)
    return [from_trafficwales(item) for item in items]


def _fetch_national_highways(
    client: NationalHighwaysClient | None, key: str | None
) -> list[Works]:
    from .common import from_datex2
    from .datex2 import ClosureType, NationalHighwaysClient

    own = client is None
    nh = client or NationalHighwaysClient((key or "").strip())
    try:
        situations = list(nh.iter_roadworks(ClosureType.PLANNED))
    finally:
        if own:
            nh.close()
    return [
        from_datex2(situation, territory="England", administrative_area="National Highways")
        for situation in situations
    ]


def _fetch_street_manager(client: StreetManagerClient, usrn: str) -> list[Works]:
    from .common import from_streetmanager

    rows = list(client.reporting.iter_permits(usrn=usrn))
    return [works for works in from_streetmanager(rows) if _usrn_matches(works, usrn)]


def _fetch_srwr(source: str | Path | IO[str], usrn: str) -> list[Works]:
    from .common import from_srwr
    from .srwr import iter_activities

    matches: list[Works] = []
    for activity in iter_activities(source):
        works = from_srwr(activity)
        if _usrn_matches(works, usrn):
            matches.append(works)
    return matches


def _append_distance_hits(
    hits: list[NearbyWorks],
    provider: str,
    works_list: Iterable[Works],
    lat: float,
    lon: float,
    radius_m: float,
) -> None:
    for works in works_list:
        distance_m = nearest_wgs84_distance_m(works, lat, lon)
        if distance_m is not None and distance_m <= radius_m:
            hits.append(
                NearbyWorks(
                    works=works, provider=provider, distance_m=distance_m, match="distance"
                )
            )


def works_near(
    lat: float | None = None,
    lon: float | None = None,
    *,
    usrn: int | str | None = None,
    radius_m: float = 500.0,
    street_manager: StreetManagerClient | None = None,
    national_highways: NationalHighwaysClient | None = None,
    national_highways_key: str | None = None,
    srwr_source: str | Path | IO[str] | None = None,
) -> list[NearbyWorks]:
    """Works near a WGS84 point and/or on a UK USRN.

    Pass ``lat`` and ``lon`` together for the distance path, ``usrn`` for
    the USRN path, or both. See the module docstring for who is queried
    in v1, who is not, and the CRS rule.

    Returns :class:`NearbyWorks` rows (each wrapping a canonical
    ``Works``), one per source record, **not** deduplicated across
    providers. Sorted by distance (USRN-only hits, ``distance_m is
    None``, last), then provider key, then works reference.
    """
    if (lat is None) ^ (lon is None):
        raise ValueError("lat and lon must be passed together")
    if lat is None and usrn is None:
        raise ValueError("works_near requires lat/lon and/or usrn")
    if radius_m < 0:
        raise ValueError("radius_m must be >= 0")

    planned = v1_providers(
        lat=lat,
        lon=lon,
        usrn=usrn,
        street_manager=street_manager,
        national_highways=national_highways,
        national_highways_key=national_highways_key,
        srwr_source=srwr_source,
    )
    usrn_s = _normalise_usrn(usrn) if usrn is not None else None
    hits: list[NearbyWorks] = []

    if "trafficwales" in planned:
        assert lat is not None and lon is not None
        _append_distance_hits(hits, "trafficwales", _fetch_traffic_wales(), lat, lon, radius_m)

    if "nationalhighways" in planned:
        assert lat is not None and lon is not None
        _append_distance_hits(
            hits,
            "nationalhighways",
            _fetch_national_highways(national_highways, national_highways_key),
            lat,
            lon,
            radius_m,
        )

    if "streetmanager" in planned:
        assert street_manager is not None and usrn_s is not None
        for works in _fetch_street_manager(street_manager, usrn_s):
            hits.append(
                NearbyWorks(works=works, provider="streetmanager", distance_m=None, match="usrn")
            )

    if "srwr" in planned:
        assert srwr_source is not None and usrn_s is not None
        for works in _fetch_srwr(srwr_source, usrn_s):
            hits.append(NearbyWorks(works=works, provider="srwr", distance_m=None, match="usrn"))

    hits.sort(
        key=lambda hit: (
            hit.distance_m is None,
            hit.distance_m if hit.distance_m is not None else 0.0,
            hit.provider,
            hit.works.reference or "",
        )
    )
    return hits


def works_near_usrn(
    usrn: int | str,
    *,
    lat: float | None = None,
    lon: float | None = None,
    radius_m: float = 500.0,
    street_manager: StreetManagerClient | None = None,
    national_highways: NationalHighwaysClient | None = None,
    national_highways_key: str | None = None,
    srwr_source: str | Path | IO[str] | None = None,
) -> list[NearbyWorks]:
    """USRN-first form of :func:`works_near`.

    Without ``lat``/``lon``, only USRN-bearing v1 providers run (Street
    Manager and/or a local SRWR extract) and ``radius_m`` is unused -
    this SDK has no tested USRN→WGS84 path that would let Traffic Wales
    or National Highways join from a USRN alone. Pass a point as well if
    you have already resolved the street.
    """
    return works_near(
        lat,
        lon,
        usrn=usrn,
        radius_m=radius_m,
        street_manager=street_manager,
        national_highways=national_highways,
        national_highways_key=national_highways_key,
        srwr_source=srwr_source,
    )


def _unverified_registry_keys() -> frozenset[str]:
    """Registry keys with ``verified=False`` - used by tests to pin the
    skip-unverified rule to the live registry, not a copied list."""
    return frozenset(entry.key for entry in _REGISTRY if not entry.verified)
