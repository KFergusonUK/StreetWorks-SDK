"""Norway (Statens vegvesen) -> streetworks.common converter.

Thin wrapper over :func:`~streetworks.common.from_datex2.from_datex2` that
pre-supplies Norway's real per-record mixed-CRS candidate list
(:data:`~streetworks.common._crs.WGS84_NORWAY`,
:data:`~streetworks.common._crs.UTM33N_NORWAY`), so a caller doesn't have
to remember to pass ``crs_candidates`` manually - a real, confirmed-live
finding (~76% UTM zone 33N, ~24% WGS84 within the same feed, across 844
real roadworks records) that a single ``crs=`` override can't express; see
:mod:`streetworks.datex2.vegvesen` for the finding and
:mod:`streetworks.common._crs` for the resolution rule (declared/inferred/
corrected by real value range, axis order resolved by magnitude, never
declared/positional order - resolution status is telemetry only, never
stored on :class:`~streetworks.common.Coordinate`).

``territory="Norway"`` is always passed - no DATEX feed states its own
country, the same convention every other DATEX adapter follows (see
:mod:`streetworks.common.from_datex2`). ``administrative_area`` has no
confirmed regional-subdivision field for Norway (real ``source/sourceName``
is the national operator, ``"NPRA"``, on every record - see
:mod:`streetworks.datex2.vegvesen`), so it stays ``None`` unless a caller
states one explicitly.
"""

from __future__ import annotations

from ..datex2.models import Situation
from ._crs import UTM33N_NORWAY, WGS84_NORWAY
from .from_datex2 import from_datex2
from .models import Works

__all__ = ["from_vegvesen"]

_NORWAY_CANDIDATES = (WGS84_NORWAY, UTM33N_NORWAY)


def from_vegvesen(situation: Situation, *, administrative_area: str | None = None) -> Works:
    """Convert one DATEX II :class:`~streetworks.datex2.Situation` (from
    :class:`~streetworks.datex2.vegvesen.VegvesenClient`) into a
    :class:`~streetworks.common.Works`, with Norway's real per-record
    mixed-CRS split resolved honestly (see module docstring) rather than
    guessed at with a single ``crs=`` value."""
    return from_datex2(
        situation,
        territory="Norway",
        administrative_area=administrative_area,
        crs_candidates=_NORWAY_CANDIDATES,
    )
