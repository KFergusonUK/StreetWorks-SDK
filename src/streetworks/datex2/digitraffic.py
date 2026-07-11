"""Finland (Fintraffic Digitraffic) roadworks - Simple-JSON, as GeoJSON.

Digitraffic publishes Finnish national roadworks credential-free at
https://www.digitraffic.fi/en/road-traffic/. There are three roadworks
endpoints; this module targets the JSON/GeoJSON one deliberately:

* ``/api/traffic-message/v2/roadworks`` (**this one**) - carries real
  coordinate geometry directly, so it needs no Alert-C location-code
  decoding.
* ``/api/traffic-message/v2/roadworks/datex2-3.5.xml`` - DATEX II 3.5 XML,
  but uses Alert-C location referencing (codes, not coordinates), which
  this SDK doesn't decode yet. Avoided for now.
* ``/api/traffic-message/v2/roadworks/datex2-2.2.3.xml`` - being removed
  after 2026-10-20. Not used.

**Digitraffic's Simple-JSON is its own schema, not a JSON serialisation of
DATEX II** (verified live, 574 real features, 2026-07) - unlike National
Highways, where the JSON mirrors the XML field-for-field. It needs its own
parsing path, the same shape of solution as :mod:`.nationalhighways`,
targeting the same shared :class:`~streetworks.datex2.models.Situation`/
:class:`~streetworks.datex2.models.SituationRecord` models. Field-by-field,
against real data:

* One :class:`~streetworks.datex2.models.SituationRecord` per
  ``roadWorkPhase`` (a situation's one announcement can carry several -
  observed 1-5 live, each genuinely at a different road/location).
* ``record_type`` is hardcoded to ``"MaintenanceWorks"`` - **a compromise,
  not a field mapping**. Digitraffic has no field that says "maintenance
  work"; this endpoint is contextually roadworks-only
  (``situationType`` is always ``"road work"``), so every derived record
  needs a value `Situation.roadworks` recognises, but nothing here is
  actually read off a discriminator field the way NDW/NH's ``record_type``
  genuinely is one.
* ``road_maintenance_type`` takes the single most specific ``workTypes[]``
  entry (first non-``"other"``, else ``"other"``) - not a joined composite;
  no other DATEX adapter synthesises this field from multiple values. The
  full ``workTypes[]`` list (and everything else this mapping leaves out -
  ``severity``, ``workingHours[]``, ``restrictions[]``...) stays reachable
  via ``SituationRecord.raw`` (the phase dict) and ``Situation.raw`` (the
  whole feature) - nothing is dropped, just not promoted to a typed field.
* ``Location.points`` is the **situation's** geometry (GeoJSON
  ``Point``/``MultiLineString``, axis-flipped from ``[lon, lat]`` to this
  SDK's ``(lat, lon)`` convention), reused across every phase-derived
  record - Digitraffic doesn't publish geometry per phase. This is
  genuinely coarser than ``road_number``/``alert_c_location`` (below),
  which are precise per phase, verified live on a 3-phase situation with
  three different road numbers under one shared geometry. Read the
  coordinate as "this situation's affected area", not that record's exact
  spot.
* ``Location.road_number`` / ``alert_c_location`` come from the phase's own
  ``roadAddress.road`` / ``alertCLocation.name`` - preserving the
  human-readable Alert-C name, not decoding a location code into geometry,
  which is exactly what ``alert_c_location`` is documented for elsewhere in
  this SDK.
* ``Validity.status`` stays ``None`` always - there is no
  active/planned/suspended equivalent anywhere in this feed (checked every
  key across all 574 features). A phase-level ``severity``
  (``high``/``highest``/``low``) exists but is an impact label, not a
  lifecycle state, and isn't force-fit into ``impact_delay_band`` (a
  different unit - a time-band vocabulary). Consequence: `from_datex2`'s
  ``date_confidence`` honestly computes ``UNKNOWN`` throughout for Finland,
  the same honest non-verification the RSS converters already do.
* ``Validity.periods`` stays ``()`` always. Digitraffic's ``workingHours[]``
  (e.g. ``{"weekday": "Saturday", "startTime": "10:00", "endTime": "16:00"}``)
  is the closest concept to DATEX's ``Period`` list, but it's a *recurring
  weekly pattern*, not discrete ``(datetime, datetime)`` windows - mapping
  it in would mean inventing a calendar date it doesn't have.
* ``Situation.overall_severity`` stays ``None`` - severity is per-phase
  only, and promoting one phase's value to situation level would be
  inferring a fact the source never stated there.

``territory``/``administrative_area`` (see :mod:`streetworks.common.from_datex2`)
can't be derived from a ``Situation`` alone here either: pass
``territory="Finland"`` (no field states a feed's own country, same
documented convention as NDW's ``"Netherlands"``/NH's ``"England"``), and
:func:`provinces` for ``administrative_area`` - **not** an ELY-centre
(Finland's actual regional road authority): checked exhaustively, no
ELY-centre field exists anywhere in this feed. ``province`` (e.g.
``"Pirkanmaa"``) is the closest genuinely-stated field, a general
geographic region rather than a precise road-authority equivalent to a UK
highway authority or US state DOT - stated plainly, not oversold. Verified
stable, not an approximation: checked all 610 phases in the live feed, and
every phase's own copy of ``province`` matched its announcement's value
with zero exceptions, so reusing one value per situation loses nothing.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._dt import parse_iso8601 as _dt
from .._transport import RetryConfig, SyncTransport
from .models import Location, Situation, SituationRecord, Validity

__all__ = ["BASE_URL", "DigitrafficClient", "parse_situations", "provinces"]

JSON = dict[str, Any]

BASE_URL = "https://tie.digitraffic.fi"
_ROADWORKS_PATH = "api/traffic-message/v2/roadworks"


def _primary_point(location_details: JSON | None) -> JSON:
    road_address_location = (location_details or {}).get("roadAddressLocation") or {}
    return road_address_location.get("primaryPoint") or {}


def _work_type(work_types: list[JSON] | None) -> str | None:
    """The single most specific type - first non-"other" entry, else
    "other" if that's all there is. Not a joined composite; see module
    docstring."""
    entries = [t.get("type") for t in (work_types or []) if t.get("type")]
    specific = next((t for t in entries if t != "other"), None)
    return specific or (entries[0] if entries else None)


def _parse_geometry_points(geometry: JSON | None) -> tuple[tuple[float, float], ...]:
    """GeoJSON ``Point``/``MultiLineString`` coordinates, flattened and
    axis-flipped from native ``[lon, lat]`` to this SDK's ``(lat, lon)``."""
    if not geometry:
        return ()
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return ()
    try:
        if kind == "Point":
            lon, lat = coordinates
            return ((float(lat), float(lon)),)
        if kind == "MultiLineString":
            points: list[tuple[float, float]] = []
            for line in coordinates:
                points.extend((float(lat), float(lon)) for lon, lat in line)
            return tuple(points)
    except (TypeError, ValueError):
        return ()
    return ()


def _parse_location(feature: JSON, phase: JSON) -> Location:
    primary_point = _primary_point(phase.get("locationDetails"))
    road = (primary_point.get("roadAddress") or {}).get("road")
    alert_c = (primary_point.get("alertCLocation") or {}).get("name")
    geometry = feature.get("geometry")
    return Location(
        kind=(geometry or {}).get("type"),
        points=_parse_geometry_points(geometry),
        road_number=str(road) if road is not None else None,
        alert_c_location=alert_c,
    )


def _parse_record(feature: JSON, announcement: JSON, phase: JSON) -> SituationRecord:
    duration = phase.get("timeAndDuration") or {}
    comment = phase.get("comment")
    return SituationRecord(
        id=phase.get("id") or "",
        record_type="MaintenanceWorks",  # endpoint-derived, not a field - see module docstring
        source_name=announcement.get("sender"),
        validity=Validity(
            overall_start=_dt(duration.get("startTime")),
            overall_end=_dt(duration.get("endTime")),
        ),
        location=_parse_location(feature, phase),
        comments=(comment,) if comment else (),
        road_maintenance_type=_work_type(phase.get("workTypes")),
        raw=phase,
    )


def _parse_situation(feature: JSON) -> Situation:
    props = feature.get("properties") or {}
    situation = Situation(
        id=props.get("situationId") or "",
        version_time=_dt(props.get("versionTime")),
        raw=feature,
    )
    for announcement in props.get("announcements") or []:
        for phase in announcement.get("roadWorkPhases") or []:
            situation.records.append(_parse_record(feature, announcement, phase))
    return situation


def parse_situations(payload: JSON) -> list[Situation]:
    """Parse one Digitraffic roadworks ``FeatureCollection`` into
    :class:`~streetworks.datex2.models.Situation` objects - one per
    feature, each with one :class:`~streetworks.datex2.models.SituationRecord`
    per ``roadWorkPhase``."""
    features = payload.get("features") or []
    return [_parse_situation(f) for f in features if isinstance(f, dict)]


def provinces(payload: JSON) -> dict[str, str]:
    """Map ``situationId -> province`` (e.g. ``"Pirkanmaa"``) for every
    feature that states one - pass the result to
    ``streetworks.common.from_datex2(situation, administrative_area=...)``,
    since a ``Situation`` alone doesn't carry it. See module docstring for
    why this is province, not an ELY-centre, and why reusing one value per
    situation is safe (verified against every phase in the live feed)."""
    result: dict[str, str] = {}
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        situation_id = props.get("situationId")
        if not situation_id:
            continue
        for announcement in props.get("announcements") or []:
            province = _primary_point(announcement.get("locationDetails")).get("province")
            if province:
                result[situation_id] = province
                break
    return result


class DigitrafficClient:
    """Fetch Finnish roadworks from Digitraffic. No credentials required.

    >>> from streetworks.datex2.digitraffic import DigitrafficClient, provinces
    >>> from streetworks.common import from_datex2
    >>> with DigitrafficClient() as digitraffic:
    ...     payload = digitraffic.get_roadworks()
    ...     situation_provinces = provinces(payload)
    ...     for situation in digitraffic.parse(payload):
    ...         works = from_datex2(
    ...             situation, territory="Finland",
    ...             administrative_area=situation_provinces.get(situation.id),
    ...         )
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_roadworks(self) -> JSON:
        """``GET /api/traffic-message/v2/roadworks`` - the raw GeoJSON
        FeatureCollection. Not paginated - one response is the whole feed."""
        response = self._transport.request("GET", f"{self.base_url}/{_ROADWORKS_PATH}")
        return response.json()

    @staticmethod
    def parse(payload: JSON) -> list[Situation]:
        return parse_situations(payload)

    def iter_situations(self) -> Iterator[Situation]:
        yield from parse_situations(self.get_roadworks())

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record - close to a no-op filter here, since this
        endpoint is already roadworks-only, but kept for API consistency
        with :class:`~streetworks.datex2.NationalHighwaysClient`."""
        for situation in self.iter_situations():
            if situation.roadworks:
                yield situation

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> DigitrafficClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
