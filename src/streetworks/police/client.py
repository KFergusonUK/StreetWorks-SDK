"""UK Police API (data.police.uk) - open crime and policing data for England,
Wales, and Northern Ireland.

No credentials required. This isn't street-works data itself, but crime
density near a worksite is a useful lone-working/safety signal, hence its
inclusion here. Covers the crime endpoints, force/neighbourhood lookup, and
the neighbourhood team/boundary endpoints (team details, boundary polygon -
see :meth:`PoliceClient.neighbourhood`/:meth:`PoliceClient.neighbourhood_boundary`);
stop-and-search and neighbourhood events/priorities still aren't wrapped -
see https://data.police.uk/docs/ for the full surface.

Rate limit: ~15 requests/second average, bursting to 30/second (a leaky
bucket); exceeding it returns 429 - handled by the shared retry/backoff
transport like every other provider here.
"""

from __future__ import annotations

import urllib.parse
import warnings
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport
from ..exceptions import ServerError

__all__ = ["BASE_URL", "PoliceClient"]

JSON = dict[str, Any]

BASE_URL = "https://data.police.uk/api"

#: Above this length, a GET on `crimes-street/{category}` risks exceeding
#: what the API (and intermediate infrastructure) will accept as a URL - a
#: rural neighbourhood boundary is hundreds of vertices and blows well past
#: this on GET. 2000 is a reasonable, commonly-documented safe threshold,
#: not a value the API states itself. Below it, GET is kept unchanged so
#: existing behaviour/tests for the common case (a short worksite boundary
#: or route) are untouched.
_POLY_URL_LENGTH_THRESHOLD = 2000

#: Categories that bear on personal safety - the ones relevant to a lone
#: worker or road crew's risk of confrontation, threat, or assault. Deliberately
#: excludes property/acquisitive categories (vehicle-crime, burglary,
#: shoplifting, bicycle-theft, other-theft, criminal-damage-arson, drugs) which
#: say little about that risk. See ``safety_signal()``.
SAFETY_RELEVANT_CATEGORIES = frozenset(
    {
        "violent-crime",  # "Violence and sexual offences" in crime_categories()
        "public-order",
        "anti-social-behaviour",
        "robbery",
        "possession-of-weapons",
    }
)


class PoliceClient:
    """UK Police API (data.police.uk) - open crime data, no credentials required.

    >>> from streetworks.police import PoliceClient
    >>> with PoliceClient() as police:
    ...     crimes = police.street_level_crimes(51.500617, -0.124629)
    ...     print(len(crimes), "crimes reported near this point last month")
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def _get(self, path: str, **params: Any) -> Any:
        response = self._transport.request(
            "GET",
            f"{self.base_url}/{path}",
            params={k: v for k, v in params.items() if v is not None},
        )
        return response.json()

    # --- crime ------------------------------------------------------------ #

    def street_level_crimes(
        self, lat: float, lng: float, *, category: str = "all-crime", date: str | None = None
    ) -> list[JSON]:
        """``GET /crimes-street/{category}`` - crimes within roughly a 1 mile
        radius of a point. ``date`` is ``YYYY-MM``; omit for the latest
        available month. Capped at 10,000 results, per the API's own limit."""
        return self._get(f"crimes-street/{category}", lat=lat, lng=lng, date=date)

    def street_level_crimes_in_area(
        self,
        points: list[tuple[float, float]],
        *,
        category: str = "all-crime",
        date: str | None = None,
    ) -> list[JSON]:
        """``GET`` (or ``POST``, for a large polygon) ``/crimes-street/{category}``
        for a custom polygon - a list of ``(lat, lng)`` points describing a
        worksite boundary, route, or (via :meth:`neighbourhood_boundary`) a
        whole neighbourhood policing area, rather than a single point with an
        implicit radius.

        Coordinates are formatted to 5 decimal places (~1m precision - far
        finer than the source data's own anonymisation) when building the
        ``poly`` string, which also cuts its length substantially for free.
        If the resulting request would still exceed a safe URL length
        (``crimes-street`` accepts the same parameters as a form-encoded
        ``POST`` to the same path), this sends a ``POST`` instead of a
        ``GET`` automatically - a rural neighbourhood ring is commonly
        hundreds of vertices and would otherwise fail as an oversized URL.
        The public signature is unchanged either way.

        Raises :class:`~streetworks.exceptions.ServerError` (never silently
        returns ``[]``) if the API responds ``503`` - which it does for a
        polygon too complex for it to process, even over ``POST``. Silently
        returning an empty list here would render an area as low-crime when
        the query never actually ran - the distinction matters.

        Emits a :class:`UserWarning` if the response comes back at exactly
        10,000 results (the API's own cap, shared with
        :meth:`street_level_crimes`) - that count may be a truncation, not
        the true total.
        """
        poly = ":".join(f"{lat:.5f},{lng:.5f}" for lat, lng in points)
        params = {k: v for k, v in {"poly": poly, "date": date}.items() if v is not None}
        path = f"crimes-street/{category}"
        url = f"{self.base_url}/{path}"

        query_length = len(urllib.parse.urlencode(params))
        try:
            if len(url) + 1 + query_length <= _POLY_URL_LENGTH_THRESHOLD:
                response = self._transport.request("GET", url, params=params)
            else:
                response = self._transport.request("POST", url, data=params)
        except ServerError as exc:
            if exc.status_code == 503:
                raise ServerError(
                    "The Police API returned 503 for this polygon - it was too "
                    f"complex for it to process ({len(points)} points, even over "
                    "POST). Try simplifying/decimating the ring rather than "
                    "retrying as-is.",
                    status_code=exc.status_code,
                    body=exc.body,
                    request_url=exc.request_url,
                ) from exc
            raise

        results: list[JSON] = response.json()
        if len(results) == 10_000:
            warnings.warn(
                "street_level_crimes_in_area returned exactly 10,000 results, "
                "the API's own cap - this may be a truncation, not the true count.",
                stacklevel=2,
            )
        return results

    def safety_signal(self, lat: float, lng: float, *, date: str | None = None) -> JSON:
        """Aggregate street-level crime near a point into a worker-safety
        signal, restricted to :data:`SAFETY_RELEVANT_CATEGORIES` - the
        categories that actually bear on the risk of confrontation, threat,
        or assault to a lone worker or road crew. Property crime (vehicle
        crime, burglary, shoplifting, ...) is fetched but excluded from the
        safety count, since it says little about that risk.

        Read this as **contextual awareness, not prediction** - three things
        that would otherwise mislead:

        1. **Historical, not live.** The API publishes street-level crime
           roughly a month or two in arrears, aggregated per calendar month.
           It describes an area's recent past, not what's happening at the
           site today.
        2. **Area-level, not site-level.** Police deliberately anonymise
           each crime's location to a snapped map point (often the middle of
           the street, sometimes 100m+ from the true spot) to protect victim
           privacy. Treat this as a signal about the surrounding area, never
           about the exact worksite.
        3. **A one-mile radius**, matching the underlying
           ``crimes-street/{category}`` endpoint's own search area.

        Returns ``{"date": ..., "total_crimes": N, "safety_relevant_count": M,
        "by_category": {category: count, ...}}``.
        """
        crimes = self.street_level_crimes(lat, lng, category="all-crime", date=date)
        by_category: dict[str, int] = {}
        for crime in crimes:
            category = crime.get("category")
            if category in SAFETY_RELEVANT_CATEGORIES:
                by_category[category] = by_category.get(category, 0) + 1
        return {
            "date": date,
            "total_crimes": len(crimes),
            "safety_relevant_count": sum(by_category.values()),
            "by_category": by_category,
        }

    def crimes_at_location(
        self,
        *,
        date: str,
        lat: float | None = None,
        lng: float | None = None,
        location_id: int | None = None,
    ) -> list[JSON]:
        """``GET /crimes-at-location`` - crimes at one specific street-level
        location (not a radius search). Pass either ``lat``/``lng`` or
        ``location_id``."""
        return self._get(
            "crimes-at-location", date=date, lat=lat, lng=lng, location_id=location_id
        )

    def crimes_no_location(
        self, *, category: str, force: str, date: str | None = None
    ) -> list[JSON]:
        """``GET /crimes-no-location`` - crimes reported by ``force`` that
        couldn't be mapped to a location."""
        return self._get("crimes-no-location", category=category, force=force, date=date)

    def crime_categories(self, *, date: str | None = None) -> list[JSON]:
        """``GET /crime-categories`` - valid category codes for a given
        month (defaults to the latest)."""
        return self._get("crime-categories", date=date)

    def last_updated(self) -> str:
        """``GET /crime-last-updated`` - the month of the latest available
        street-level crime data (``YYYY-MM-DD``; only the month is meaningful)."""
        return self._get("crime-last-updated")["date"]

    def street_level_availability(self) -> list[JSON]:
        """``GET /crimes-street-dates`` - months with data available, and
        which forces submitted stop-and-search data for each."""
        return self._get("crimes-street-dates")

    # --- forces & neighbourhoods -------------------------------------------- #

    def forces(self) -> list[JSON]:
        """``GET /forces`` - every force except British Transport Police."""
        return self._get("forces")

    def locate_neighbourhood(self, lat: float, lng: float) -> JSON:
        """``GET /locate-neighbourhood`` - the force and neighbourhood team
        ID covering a point."""
        return self._get("locate-neighbourhood", q=f"{lat},{lng}")

    def neighbourhoods(self, force: str) -> list[JSON]:
        """``GET /{force}/neighbourhoods`` - every neighbourhood policing
        team in a force, as ``{"id": ..., "name": ...}``."""
        return self._get(f"{force}/neighbourhoods")

    def neighbourhood(self, force: str, neighbourhood_id: str) -> JSON:
        """``GET /{force}/{neighbourhood_id}`` - team details: name, centre
        point, contact details, links, description. Real response fields
        vary in how populated they are - ``contact_details``/``locations``
        are commonly empty (``{}``/``[]``), confirmed live - and ``centre``
        is itself ``{"latitude": ..., "longitude": ...}`` with **string**
        values, the same as :meth:`neighbourhood_boundary`."""
        return self._get(f"{force}/{neighbourhood_id}")

    def neighbourhood_boundary(
        self, force: str, neighbourhood_id: str
    ) -> list[tuple[float, float]]:
        """``GET /{force}/{neighbourhood_id}/boundary`` - the boundary as
        ``(lat, lng)`` pairs, ready to pass straight to
        :meth:`street_level_crimes_in_area` as ``points`` - same order, no
        reordering needed.

        Real, verified facts about this endpoint, from live calls (not the
        docs) - all preserved as-is, never repaired, by this method:

        - The API states each coordinate as a **string**
          (``{"latitude": "52.6394052587", ...}``); this method coerces to
          ``float`` so callers never see that.
        - It is always a **single ring** - no multipolygon, no holes, no
          nesting. A neighbourhood that is physically two disjoint parts
          cannot be represented by this endpoint at all; that's a real
          limitation of the source data, not something this method works
          around.
        - The ring is **closed** (the last point repeats the first),
          confirmed live.
        - Rings are **not guaranteed to be simple**: a real ring (
          Leicestershire's ``NC04``, "City Centre") contains near-duplicate
          consecutive vertices (confirmed live, sub-metre apart) and, per
          the same live investigation, at least one spike where the ring
          steps out and immediately returns along nearly the same line.
          This method returns the ring exactly as received - simplification
          or repair is the caller's decision, not this SDK's.
        """
        raw = self._get(f"{force}/{neighbourhood_id}/boundary")
        return [(float(point["latitude"]), float(point["longitude"])) for point in raw]

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> PoliceClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
