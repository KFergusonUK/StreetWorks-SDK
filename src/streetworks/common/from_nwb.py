"""NWB -> streetworks.common gazetteer converter.

**Emits no ``Street`` at all** - only :class:`~streetworks.common.gazetteer.Segment`,
one per real :class:`~streetworks.nwb.models.Wegvak`. Per the module
docstring's "no synthetic streets" rule: NWB publishes segments with a
``bag_orl`` reference, and this SDK's only built BAG route (the light
GeoPackage) has no street row of its own to be a ``Street`` - so Dutch
street names reach this canonical model only via ``Address.street_name``
(see :mod:`.from_bag`), never via a Dutch ``Street``.

**Contradicts one assumption in the design brief, flagged rather than
silently worked around**: the brief's own field listing noted
``Segment.names`` as "optional; BD TOPO only, so far." Real data shows
otherwise - ``Wegvak.stt_naam`` is a genuine, live-confirmed per-segment
name (even purely-numbered roads carry one; a real A79 motorway segment
has ``stt_naam="A79"``), so this converter populates ``Segment.names`` for
NWB too, per the evidence-discipline rule that stated data is never
dropped. The brief's note was accurate when written; it's now one
provider out of date.

``street_refs`` comes from ``Wegvak.toponyme_id()`` (the real, stated
``bag_orl`` join - never NWB's own less-reliable name-based grouping, see
the native module's docstring for the measured over-merge counts).
``address_ranges`` comes from the six real ``hnrstrlnks``/``hnrstrrhts``/
``e_hnr_lnks``/``e_hnr_rhts``/``l_hnr_lnks``/``l_hnr_rhts`` fields,
promoted onto :class:`~streetworks.nwb.models.Wegvak` for this model (see
its own docstring) - a third, coarser address-street linking mechanism
alongside identifier and name.
"""

from __future__ import annotations

from datetime import date, datetime

from ..nwb.models import Wegvak
from ._wkt import coordinate_from_wkt
from .gazetteer import AddressRange, Name, Segment, StreetType
from .models import Identifier

__all__ = ["from_nwb"]


def _date(value: str | None) -> date | None:
    """``wvk_begdat`` is a real ISO-8601 string with timezone offset, e.g.
    ``"2019-01-01T00:00:00+01:00"``."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _address_ranges(wegvak: Wegvak) -> tuple[AddressRange, ...]:
    ranges = []
    if any((wegvak.hnrstrlnks, wegvak.e_hnr_lnks, wegvak.l_hnr_lnks)):
        ranges.append(
            AddressRange(
                side="links",
                first=wegvak.e_hnr_lnks,
                last=wegvak.l_hnr_lnks,
                structure=wegvak.hnrstrlnks,
            )
        )
    if any((wegvak.hnrstrrhts, wegvak.e_hnr_rhts, wegvak.l_hnr_rhts)):
        ranges.append(
            AddressRange(
                side="rechts",
                first=wegvak.e_hnr_rhts,
                last=wegvak.l_hnr_rhts,
                structure=wegvak.hnrstrrhts,
            )
        )
    return tuple(ranges)


def from_nwb(wegvak: Wegvak, *, crs: str = "EPSG:28992") -> Segment:
    """Convert one real :class:`~streetworks.nwb.models.Wegvak` into a
    :class:`~streetworks.common.gazetteer.Segment`. ``crs`` defaults to
    ``EPSG:28992`` (Amersfoort / RD New), confirmed live on every real
    geometry regardless of access route."""
    geometry = coordinate_from_wkt(wegvak.geometry, crs=crs)
    if geometry is None:
        raise ValueError(f"Wegvak {wegvak.wvk_id} has no geometry to convert")
    bag_orl = wegvak.toponyme_id()
    return Segment(
        geometry=geometry,
        identifiers=(Identifier(scheme="wvk_id", value=str(wegvak.wvk_id)),),
        names=(Name(value=wegvak.stt_naam),) if wegvak.stt_naam else (),
        street_refs=(Identifier(scheme="bag_orl", value=bag_orl),) if bag_orl else (),
        street_type=StreetType(code=wegvak.bst_code) if wegvak.bst_code else None,
        address_ranges=_address_ranges(wegvak),
        administrative_area=wegvak.gme_naam,
        as_at=_date(wegvak.wvk_begdat),
        raw=wegvak,
    )
