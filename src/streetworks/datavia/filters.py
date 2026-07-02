"""OGC WFS filter and request builders for Geoplace DataVIA.

These deliberately mirror the request shapes in the DataVIA documentation:
POST bodies are WFS 1.1.0 ``GetFeature`` documents with ``ogc:Filter``
elements; GET requests are WFS 2.0.0 KVP with ``startIndex``/``count``
paging. POST is recommended by Geoplace for anything with a filter, to avoid
URL encoding/length issues.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from xml.sax.saxutils import escape

Coordinate = tuple[float, float]

_WFS_NAMESPACES = (
    'xmlns:wfs="http://www.opengis.net/wfs"\n'
    '  xmlns:gml="http://www.opengis.net/gml"\n'
    '  xmlns:ogc="http://www.opengis.net/ogc"\n'
    '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
    '  xsi:schemaLocation="http://www.opengis.net/wfs\n'
    '                      http://schemas.opengis.net/wfs/1.0.0/WFS-basic.xsd"'
)


def _coords(points: Iterable[Coordinate]) -> str:
    return ",".join(f"{x} {y}" for x, y in points)


# --------------------------------------------------------------------------- #
# Filter fragments (combine with and_/or_)
# --------------------------------------------------------------------------- #


def property_equals(name: str, value: object) -> str:
    """``ogc:PropertyIsEqualTo`` - e.g. ``property_equals("usrn", 4401245)``."""
    return (
        "<ogc:PropertyIsEqualTo>"
        f"<ogc:PropertyName>{escape(name)}</ogc:PropertyName>"
        f"<ogc:Literal>{escape(str(value))}</ogc:Literal>"
        "</ogc:PropertyIsEqualTo>"
    )


def usrn_equals(usrn: int | str) -> str:
    """Filter on a single USRN."""
    return property_equals("usrn", usrn)


def intersects_polygon(ring: Sequence[Coordinate], *, geometry_property: str = "geom") -> str:
    """``ogc:Intersects`` with a ``gml:Polygon`` outer ring.

    ``ring`` is a sequence of (x, y) pairs - lon/lat for EPSG:4326 or
    easting/northing for EPSG:27700 - and should be closed (first == last);
    if not, it is closed automatically.
    """
    pts = list(ring)
    if pts and pts[0] != pts[-1]:
        pts.append(pts[0])
    return (
        "<ogc:Intersects>"
        f"<ogc:PropertyName>{escape(geometry_property)}</ogc:PropertyName>"
        "<gml:Polygon><gml:outerBoundaryIs><gml:LinearRing>"
        f"<gml:coordinates>{_coords(pts)}</gml:coordinates>"
        "</gml:LinearRing></gml:outerBoundaryIs></gml:Polygon>"
        "</ogc:Intersects>"
    )


def dwithin_point(
    x: float, y: float, distance_m: float, *, geometry_property: str = "geom"
) -> str:
    """``ogc:DWithin`` - features within ``distance_m`` metres of a point."""
    return (
        "<ogc:DWithin>"
        f"<ogc:PropertyName>{escape(geometry_property)}</ogc:PropertyName>"
        f"<gml:Point><gml:coordinates>{x},{y}</gml:coordinates></gml:Point>"
        f"<ogc:Distance units='m'>{distance_m:g}</ogc:Distance>"
        "</ogc:DWithin>"
    )


def bbox(
    lower: Coordinate, upper: Coordinate, *, geometry_property: str = "geom"
) -> str:
    """``ogc:BBOX`` with a ``gml:Envelope``."""
    return (
        "<ogc:BBOX>"
        f"<ogc:PropertyName>{escape(geometry_property)}</ogc:PropertyName>"
        "<gml:Envelope>"
        f"<gml:lowerCorner>{lower[0]} {lower[1]}</gml:lowerCorner>"
        f"<gml:upperCorner>{upper[0]} {upper[1]}</gml:upperCorner>"
        "</gml:Envelope>"
        "</ogc:BBOX>"
    )


def and_(*fragments: str) -> str:
    """Combine filter fragments with ``ogc:AND``."""
    if len(fragments) == 1:
        return fragments[0]
    return f"<ogc:AND>{''.join(fragments)}</ogc:AND>"


def or_(*fragments: str) -> str:
    """Combine filter fragments with ``ogc:OR``."""
    if len(fragments) == 1:
        return fragments[0]
    return f"<ogc:OR>{''.join(fragments)}</ogc:OR>"


# --------------------------------------------------------------------------- #
# GetFeature document
# --------------------------------------------------------------------------- #


def getfeature_xml(
    type_name: str,
    *,
    filter_fragment: str | None = None,
    srs: str = "EPSG:4326",
    output_format: str = "geojson",
    start_index: int | None = None,
    count: int | None = None,
) -> str:
    """Build a WFS 1.1.0 ``GetFeature`` POST body as used by DataVIA."""
    filter_xml = f"<ogc:Filter>{filter_fragment}</ogc:Filter>" if filter_fragment else ""
    paging = ""
    if start_index is not None:
        paging += f"<wfs:StartIndex>{int(start_index)}</wfs:StartIndex>"
    if count is not None:
        paging += f"<wfs:Count>{int(count)}</wfs:Count>"
    return (
        '<wfs:GetFeature service="WFS" version="1.1.0" '
        f'outputFormat="{escape(output_format)}"\n  {_WFS_NAMESPACES}>\n'
        f'  <wfs:Query typeName="{escape(type_name)}" srsName="{escape(srs)}">'
        f"{filter_xml}</wfs:Query>\n"
        f"{paging}"
        "</wfs:GetFeature>"
    )
