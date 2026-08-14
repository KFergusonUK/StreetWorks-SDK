"""Vienna: "verkehrswirksame Baustellen" (traffic-relevant roadworks) -
this SDK's second Austria roadworks coverage, alongside the separate,
non-overlapping national ASFINAG motorway feed
(:mod:`streetworks.datex2.austria`) - do not dedupe between the two,
the same discipline as every other national-vs-municipal pair in this
SDK.

.. attention::
   **Confirmed live (2026-08-14)** against a real, unauthenticated pull
   (111 real feature rows at time of writing).

**The brief's own candidate URL (`data.gv.at`) is a JS-rendered SPA -
the real data lives directly on Vienna's own GeoServer WFS instead.**
A plain unauthenticated fetch of any `data.gv.at` catalogue page,
including the CKAN-style API path the brief's own naming implied,
returns an identical empty shell - not real content. The real endpoint,
found via web search: `https://data.wien.gv.at/daten/geo` (a real,
live, 377-layer WFS).

**Two real layers, genuinely disjoint - not the same data in two
formats.** :data:`POINT_TYPE_NAME` (``ogdwien:BAUSTELLENPKTOGD``, 39
real features) and :data:`LINE_TYPE_NAME` (``ogdwien:BAUSTELLENLINOGD``,
72 real features) - confirmed live: **zero real `OBJECTID` overlap and
zero location-name overlap** between the two. Each real worksite is
recorded once, as either a point or a line, not both -
:meth:`ViennaClient.iter_roadworks` fetches and yields both, genuinely
needed for the complete picture (111 real works total), unlike Kanton
Zürich's own two layers (which really do carry the same data twice).

**CRS confirmed live, cross-verified two ways.** The WFS's own
``GetCapabilities`` states ``<DefaultSRS>urn:x-ogc:def:crs:EPSG:31256``
and the real ``GetFeature`` response's own ``crs`` field agrees - and a
same-feature request reprojected to `EPSG:4326` landed on real Vienna
coordinates (`[16.36, 48.17]`, in the 10th district, matching that same
feature's own stated `BEZIRK: 10`) - confirming the native small-number
GK East values (`[2174.3, 336902.7]`) are genuinely correct, not a
mislabelled CRS. Requested natively here, not reprojected, the same
policy as Mallorca/Saxony/Oslo/Helsinki/Kanton Zürich.

**Two real server quirks, confirmed live, both masked-failure risks -
the same shapes Mallorca's and Stadt Zürich's own module docstrings
already document for different servers.**

- This GeoServer genuinely rejects the shared client's own
  ``application/geo+json`` default - **but not with an error status**.
  It returns **HTTP 200** wrapping an XML ``InvalidParameterValue``
  exception (*"Failed to find response for output format application/
  geo+json"*), which looks like success until the body is actually
  parsed. Confirmed by reading the real response body, not just the
  status code - an earlier check that only checked status codes wrongly
  concluded this format worked. ``OUTPUTFORMAT="application/json"`` is
  what actually returns real GeoJSON, used explicitly here.
- It also rejects both WFS 2.0.0's plural ``TYPENAMES`` alone (a real
  `400`) and WFS 1.1.0's plural ``TYPENAMES`` alone (a real structured
  `ExceptionReport`) - it needs 1.1.0's singular ``TYPENAME`` sent
  alongside the shared client's own ``TYPENAMES``, confirmed live that
  having both present (one recognised, one ignored) succeeds.

**A real, checked-and-correctly-excluded false lead.**
``ogdwien:BAUSPERRE82OGD``/``BAUSPERRE86OGD`` ("Bausperre § 8 (2)/(6)")
sound roadworks-adjacent but are real Vienna Bauordnung (building code)
construction-freeze zoning restrictions - an urban-planning concept, not
a road closure. Checked and ruled out, not assumed related from the
name alone.

**Licence: Stadt Wien's stated general open-data policy is CC BY 4.0**,
confirmed live from ``digitales.wien.gv.at``'s own open-data page
(*"Die Publikation erfolgt in der Regel unter der Lizenz CC BY 4.0"* -
"Publication generally occurs under the CC BY 4.0 licence"). This is a
**general stated practice, not this specific dataset's own confirmed
per-record licence field** - the catalogue page that would carry that
field is the JS-rendered SPA shell noted above, unreachable for
automated per-dataset confirmation.

**No credentials required** - every claim above came from a fully
unauthenticated GetFeature request.
"""

from __future__ import annotations

from typing import Any

import httpx

from ..ogc.client import OGCFeaturesClient

__all__ = ["BASE_URL", "POINT_TYPE_NAME", "LINE_TYPE_NAME", "CRS", "ViennaClient"]

JSON = dict[str, Any]

#: Vienna's own GeoServer WFS - found via web search (the data.gv.at
#: catalogue frontend is a JS-rendered SPA, no data reachable from a
#: plain fetch). See module docstring.
BASE_URL = "https://data.wien.gv.at/daten/geo"

#: verkehrswirksame Baustellen Punkte - real Point geometry.
POINT_TYPE_NAME = "ogdwien:BAUSTELLENPKTOGD"

#: verkehrswirksame Baustellen Linien - real LineString geometry.
#: Genuinely disjoint from the point layer, see module docstring.
LINE_TYPE_NAME = "ogdwien:BAUSTELLENLINOGD"

#: MGI / Austria GK East, the WFS's real native CRS - requested
#: explicitly rather than the shared client's own EPSG:4326 default.
#: See module docstring.
CRS = "EPSG:31256"

#: This GeoServer's real working JSON output format - not the shared
#: client's own "application/geo+json" default, which it masks as a
#: real HTTP 200 wrapping an XML error. See module docstring.
_OUTPUT_FORMAT = "application/json"


class ViennaClient:
    """Fetch Vienna's real "verkehrswirksame Baustellen" (traffic-
    relevant roadworks and closures) from the city's own GeoServer WFS.
    No credentials required.

    >>> from streetworks.vienna import ViennaClient
    >>> from streetworks.common import from_vienna
    >>> with ViennaClient() as vienna:  # doctest: +SKIP
    ...     works = from_vienna(vienna.iter_roadworks())
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def iter_roadworks(self) -> list[JSON]:
        """Every real feature from both the point and line layers,
        combined - genuinely disjoint real data, not a redundant
        duplicate representation, see module docstring."""
        features: list[JSON] = []
        for type_name in (POINT_TYPE_NAME, LINE_TYPE_NAME):
            payload = self._ogc.get_wfs_features(
                BASE_URL,
                type_name=type_name,
                version="1.1.0",
                srs_name=CRS,
                output_format=_OUTPUT_FORMAT,
                extra_params={"TYPENAME": type_name},
            )
            features.extend(payload.get("features") or ())
        return features

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> ViennaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
