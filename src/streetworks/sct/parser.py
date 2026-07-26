"""Parser for SCT's ``incidenciesGML.xml`` - a genuine WFS 1.0-shaped
``wfs:FeatureCollection``, but flat (one ``gml:Point`` plus a dozen scalar
sibling fields per record, no nesting, no ``xlink`` associations) - a
small, contained reader for this specific shape, not a general GML
reader. See :mod:`streetworks.sct`'s own module docstring for why this is
deliberately not built on the parked general INSPIRE-GML-reader decision.

Matches elements by local name only (namespace-tolerant), the same
approach :mod:`streetworks.datex2.parser` already takes, since the real
feed's declared ``cite:``/``gml:``/``wfs:`` prefixes aren't worth binding
to rigidly for a shape this simple.
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import fromstring as _fromstring

from .models import Incident

__all__ = ["parse_incidents"]

_RECORD_LOCAL_NAME = "mct2_v_afectacions_data"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(element: Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def _parse_point(record: Element) -> tuple[float, float] | None:
    """The real feed states ``gml:coordinates`` as ``"lon,lat"`` (decimal
    point, comma-separated) under ``geom/Point`` - flipped here to this
    SDK's ``(lat, lon)`` WGS84 convention, same as every other EPSG:4326
    source (from_datex2/from_wzdx/from_autobahn)."""
    for descendant in record.iter():
        if _local(descendant.tag) == "coordinates" and descendant.text:
            parts = descendant.text.strip().split(",")
            if len(parts) != 2:
                return None
            try:
                lon, lat = float(parts[0]), float(parts[1])
            except ValueError:
                return None
            return (lat, lon)
    return None


def _parse_record(record: Element) -> Incident:
    fields: dict[str, str | None] = {}
    for child in record:
        name = _local(child.tag)
        if name == "geom":
            continue
        fields[name] = _text(child)

    return Incident(
        identificador=fields.get("identificador") or "",
        tipus=fields.get("tipus"),
        subtipus=fields.get("subtipus"),
        carretera=fields.get("carretera"),
        pk_inici=_float(fields.get("pk_inici")),
        pk_fi=_float(fields.get("pk_fi")),
        causa=fields.get("causa"),
        cap_a=fields.get("cap_a"),
        data=_parse_date(fields.get("data")),
        nivell=fields.get("nivell"),
        sentit=fields.get("sentit"),
        descripcio=fields.get("descripcio"),
        descripcio_tipus=fields.get("descripcio_tipus"),
        font=fields.get("font"),
        point=_parse_point(record),
        raw=dict(fields),
    )


def parse_incidents(payload: bytes) -> list[Incident]:
    """Parse a real ``incidenciesGML.xml`` response body into
    :class:`~.models.Incident` records - one per real
    ``mct2_v_afectacions_data`` feature member."""
    root = _fromstring(payload)
    return [
        _parse_record(element)
        for element in root.iter()
        if _local(element.tag) == _RECORD_LOCAL_NAME
    ]
