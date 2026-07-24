"""ONS 2021 LSOA boundaries and population, example-local by design.

Deliberately not part of ``streetworks`` itself - this SDK is a street works
and roadworks client library, and demographics/census geography is out of
its scope even though this one example needs a population denominator. See
this package's README for the fuller architectural note.

One live-verified discovery worth recording: boundary geometry and
population both come from the **same** ArcGIS FeatureServer layer -
ONS's Census 2021 "Number of Usual Residents" (TS001) table, LSOA layer -
queried once per batch of LSOA codes. That means there is no separate
boundary-source/population-source pair that could drift to different LSOA
vintages; both are read from the same rows, keyed by the same
``LSOA2021Code`` field, in the same request. The 2021 vintage is therefore
structural, not just a convention this code happens to follow - see
:func:`fetch_lsoa_stats`'s docstring and ``tests/test_examples_crime_context_lsoa.py``
for the guard this still leaves in place at the join with crime data.

Confirmed live (Durham Constabulary, 2026-05): the "Total" field
(ONS's internal code ``I36759D0`` - aliased here, never trusted by name
alone since Esri field names are arbitrary and only the alias is stable)
gives real per-LSOA population; a real spot check (Darlington 015B) matched
a plausible 1,938 residents, consistent with the ONS's own "roughly 1,500"
LSOA sizing target.
"""

from __future__ import annotations

from typing import Any

from streetworks.arcgis import ArcGISFeatureClient

JSON = dict[str, Any]

#: ONS Census 2021 "Number of Usual Residents" (TS001), LSOA layer. Found by
#: searching ArcGIS Online for the real, ONS-owned service - not guessed -
#: and confirmed live to carry both geometry and the "Total" population
#: field together. https://services.arcgis.com/qHLhLQrcvEnxjtPr/arcgis/rest/services/Pop_Census21_EW_DemographyMigration_TS001_NumberOfUsualResidents/FeatureServer
_TS001_BASE_URL = (
    "https://services.arcgis.com/qHLhLQrcvEnxjtPr/arcgis/rest/services/"
    "Pop_Census21_EW_DemographyMigration_TS001_NumberOfUsualResidents/FeatureServer"
)
_LSOA_LAYER_ID = 6

#: The layer's field for total usual residents is a raw Esri code
#: (``I36759D0``) whose only documented meaning is its alias, "Total" -
#: confirmed live against layer metadata, not guessed from the name.
_POPULATION_FIELD = "I36759D0"

#: Keeps each `where LSOA2021Code IN (...)` query well under this SDK's own
#: documented safe-URL-length convention (see streetworks/police/client.py's
#: _POLY_URL_LENGTH_THRESHOLD) - this layer's query() only supports GET, so
#: batching, not a GET/POST switch, is the way to stay under it.
_BATCH_SIZE = 50


def fetch_lsoa_stats(
    codes: list[str],
    *,
    out_sr: int = 4326,
    client: ArcGISFeatureClient | None = None,
) -> dict[str, JSON]:
    """Fetch boundary geometry (WGS84 lon/lat rings) and 2021 Census
    population for each ``LSOA2021Code`` in ``codes``, batched to stay
    under a safe GET URL length.

    Returns ``{code: {"name", "population", "utla", "rings"}}`` - only for
    codes ONS's own table actually has (an unknown/mistyped code is simply
    absent from the result, not an error; see this package's
    ``lsoa_membership`` guard for turning "many codes missing" into a loud
    failure instead of a quiet one, which is the real risk this data mixing
    - not vintage skew, since geometry and population share one row and
    thus one vintage by construction).

    ``out_sr`` defaults to 4326 (WGS84 lon/lat), matching the point+radius
    worksite path's own coordinate system (see ``worksite.py``). The USRN
    worksite path uses ``out_sr=27700`` (British National Grid) instead, to
    match the OS Open USRN GeoPackage's native CRS without needing a real
    OSGB36 reprojection - see ``worksite.worksite_from_usrn``'s docstring.
    """
    owns_client = client is None
    client = client or ArcGISFeatureClient()
    try:
        stats: dict[str, JSON] = {}
        for start in range(0, len(codes), _BATCH_SIZE):
            batch = codes[start : start + _BATCH_SIZE]
            in_clause = ",".join(f"'{code}'" for code in batch)
            result = client.query(
                _TS001_BASE_URL,
                _LSOA_LAYER_ID,
                where=f"LSOA2021Code IN ({in_clause})",
                out_fields=f"LSOA2021Code,NAME,UTLAName,{_POPULATION_FIELD}",
                out_sr=out_sr,
            )
            for feature in result.get("features", []):
                props = feature["properties"]
                code = props["LSOA2021Code"]
                geometry = feature.get("geometry") or {}
                rings = _polygon_rings(geometry)
                stats[code] = {
                    "name": props["NAME"],
                    "utla": props["UTLAName"],
                    "population": props[_POPULATION_FIELD],
                    "rings": rings,
                }
        return stats
    finally:
        if owns_client:
            client.close()


def _polygon_rings(geometry: JSON) -> list[list[tuple[float, float]]]:
    """A GeoJSON Polygon or MultiPolygon's rings as ``(x, y)`` coordinate
    tuples - ``(lon, lat)`` degrees or ``(easting, northing)`` metres
    depending on the ``out_sr`` this geometry was requested with; this
    function itself is CRS-agnostic and just unwraps the GeoJSON shape.
    LSOA boundaries are occasionally MultiPolygon (a small number of real
    LSOAs are split by a river or a motorway), so this does not assume
    Polygon the way a single neighbourhood-team boundary safely could."""
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if geom_type == "Polygon":
        return [[(x, y) for x, y in ring] for ring in coords]
    if geom_type == "MultiPolygon":
        return [[(x, y) for x, y in ring] for polygon in coords for ring in polygon]
    return []
