"""GML 3.2 parsing for IDEE's Spain transport-network WFS - a small,
contained reader for exactly the ``tn-ro:Road``/``tn-ro:RoadLink`` shape
this SDK uses, not a general INSPIRE GML reader (that was explicitly
parked - see ``docs/inspire-gml-investigation.md``). Matches elements by
local name only, namespace-tolerant, the same approach
:mod:`streetworks.sct.parser`/:mod:`streetworks.datex2.parser` already
take, since binding rigidly to this service's declared ``tn-ro:``/``net:``/
``gn:`` prefixes buys nothing a real response couldn't already break.

**Axis order and CRS, confirmed live, not assumed**: every real
``srsName`` seen is the OGC "http URI" form
(``http://www.opengis.net/def/crs/EPSG/0/4258``), and real coordinate
values confirm genuine lat/lon order (matching ETRS89, EPSG:4258) - see
the original investigation's own "Notes in passing" for the live
evidence. ``posList`` values are parsed straight into
``(lat, lon)`` tuples with no swap.
"""

from __future__ import annotations

from typing import Any
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import fromstring as _fromstring

__all__ = ["RawRoad", "parse_roads_page", "parse_road_links"]

_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


class RawRoad:
    """An unresolved ``tn-ro:Road`` - real fields plus the list of
    ``RoadLink`` ids it points at, not yet joined to their geometry."""

    __slots__ = (
        "id",
        "name",
        "national_road_code",
        "local_road_code",
        "inspire_local_id",
        "inspire_namespace",
        "link_ids",
        "raw",
    )

    def __init__(
        self,
        id: str,
        name: str | None,
        national_road_code: str | None,
        local_road_code: str | None,
        inspire_local_id: str | None,
        inspire_namespace: str | None,
        link_ids: list[str],
        raw: dict[str, Any],
    ) -> None:
        self.id = id
        self.name = name
        self.national_road_code = national_road_code
        self.local_road_code = local_road_code
        self.inspire_local_id = inspire_local_id
        self.inspire_namespace = inspire_namespace
        self.link_ids = link_ids
        self.raw = raw


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_local(element: Element, name: str) -> Element | None:
    for descendant in element.iter():
        if _local(descendant.tag) == name:
            return descendant
    return None


def _findall_local(element: Element, name: str) -> list[Element]:
    return [d for d in element.iter() if _local(d.tag) == name]


def _text(element: Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _href_id(element: Element | None) -> str | None:
    """The real gml:id of the referenced feature - taken from the URL
    fragment after ``#``, not parsed out of the query string, so it
    survives whichever STOREDQUERY_ID/OUTPUTFORMAT shape a future
    response uses."""
    if element is None:
        return None
    href = element.get(_XLINK_HREF)
    if not href or "#" not in href:
        return None
    return href.rsplit("#", 1)[-1] or None


def _parse_road(member: Element) -> RawRoad:
    road_el = member[0] if len(member) else member
    road_id = road_el.get("{http://www.opengis.net/gml/3.2}id", "")

    link_ids = [
        _href_id(el)
        for el in _findall_local(road_el, "link")
        if _href_id(el) is not None
    ]

    name_el = _find_local(road_el, "geographicalName")
    name = _text(_find_local(name_el, "text")) if name_el is not None else None

    inspire_id_el = _find_local(road_el, "inspireId")
    inspire_local_id = (
        _text(_find_local(inspire_id_el, "localId")) if inspire_id_el is not None else None
    )
    inspire_namespace = (
        _text(_find_local(inspire_id_el, "namespace")) if inspire_id_el is not None else None
    )

    raw: dict[str, Any] = {"id": road_id}
    for child in road_el.iter():
        local = _local(child.tag)
        if local in ("localRoadCode", "nationalRoadCode") and child.text:
            raw[local] = child.text.strip()
        elif local == "beginLifespanVersion" and child.text:
            raw[local] = child.text.strip()

    return RawRoad(
        id=road_id,
        name=name,
        national_road_code=raw.get("nationalRoadCode"),
        local_road_code=raw.get("localRoadCode"),
        inspire_local_id=inspire_local_id,
        inspire_namespace=inspire_namespace,
        link_ids=[lid for lid in link_ids if lid],
        raw=raw,
    )


def parse_roads_page(payload: bytes) -> tuple[list[RawRoad], str | None]:
    """Parse one ``GetFeature`` page of ``tn-ro:Road`` members. Returns
    the real roads on this page plus the server's own stated ``next``
    URL (WFS 2.0's own paging link), or ``None`` on the last page -
    followed directly rather than this SDK computing STARTINDEX math
    itself."""
    root = _fromstring(payload)
    next_url = root.get("next")
    members = _findall_local(root, "member")
    roads = [_parse_road(m) for m in members if _find_local(m, "Road") is not None]
    return roads, next_url


def _parse_pos_list(text: str | None) -> list[tuple[float, float]]:
    if not text:
        return []
    values = [float(v) for v in text.split()]
    return list(zip(values[0::2], values[1::2], strict=True))


def parse_road_links(payload: bytes) -> dict[str, list[tuple[float, float]]]:
    """Parse a batched (or single) ``tn-ro:RoadLink`` ``GetFeature``
    response into ``{gml:id: [(lat, lon), ...]}``. A RoadLink with no
    real ``centrelineGeometry`` (schema-legal, not observed live so far)
    is omitted rather than given empty/fabricated points."""
    root = _fromstring(payload)
    result: dict[str, list[tuple[float, float]]] = {}
    for member in _findall_local(root, "member"):
        link_el = _find_local(member, "RoadLink")
        if link_el is None:
            continue
        link_id = link_el.get("{http://www.opengis.net/gml/3.2}id", "")
        pos_list = _find_local(link_el, "posList")
        points = _parse_pos_list(_text(pos_list))
        if link_id and points:
            result[link_id] = points
    return result
