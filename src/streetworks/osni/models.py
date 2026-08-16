"""OSNI (Ordnance Survey Northern Ireland) Open Data - Gazetteer -
Streetnames: this SDK's own native model. See
:mod:`streetworks.osni.client` for the full investigation and
provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Streetname"]


@dataclass(frozen=True)
class Streetname:
    """One real OSNI Streetnames feature - a street name plus a single
    representative point, nothing more. A genuinely thinner shape than a
    full address/street gazetteer (no ASD-style attribute richness, no
    address points) - see :mod:`streetworks.osni.client`'s own module
    docstring for why this is graded honestly as a name+point gazetteer,
    not a street-geometry or address register.

    ``usrn`` is real, live-confirmed 100% populated and 100% unique
    across all 25,643 real features sampled - but it is **OSNI's own
    field, not confirmed to cross-reference GB's national USRN/NSG
    registry** (Northern Ireland is outside that GB-wide scheme). Kept
    and promoted, scoped to say so, rather than dropped or silently
    treated as a national USRN.

    ``easting``/``northing`` are the real, separately-stated
    ``X_Coord``/``Y_Coord`` properties - genuine Irish Grid values,
    confirmed by their own plausible magnitude (consistent with the old
    Irish Grid, TM65/TM75, not the modern Irish Transverse Mercator).
    **Not** the GeoJSON download's own ``geometry`` field, which this
    particular route reprojects to WGS84 - see the module docstring for
    why the two disagree and which one this SDK trusts.
    """

    streetname: str
    usrn: int
    objectid: int
    easting: float
    northing: float
    raw: dict[str, Any] = field(default_factory=dict)
