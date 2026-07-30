"""Shared, honest per-point CRS resolution for the DATEX/GML provider
family - extracted after a real, serious finding in Norway's vegvesen feed
(see :mod:`streetworks.datex2.vegvesen`'s own module docstring): real
coordinates split across two genuinely different CRSes *within the same
feed* (confirmed live, 2026-07-30: ~76% ETRS89/UTM zone 33N via a real
``srsName="...25833"`` attribute, ~24% genuine WGS84 via DATEX
``pointCoordinates``, which never carries ``srsName`` at all - the DATEX
spec's own implicit-WGS84 default). A single ``crs=`` override per call
(the Belgium/Saxony shape) cannot express this; per-point resolution can.

**Governing constraint (deliberate): no CRS-provenance field on
``Coordinate``.** Whether a given point's CRS was *declared* (a
consistent ``srsName``), *inferred* (no declaration, but the value fits a
known band), or *corrected* (a declaration that the values themselves
contradict) is real, useful information - but it's build/ingest-time
telemetry, not something worth persisting on the canonical model forever.
:class:`CrsResolution.status` carries it back to the caller for logging/
counting (see :mod:`streetworks.datex2.vegvesen`'s own smoke-test
surfacing); it never reaches :class:`~streetworks.common.models.Coordinate`.
Accepted trade-off, not an oversight: a downstream consumer can't later
ask "which of these points had a contradicted declaration" - that
visibility exists only at build time, in logs and counts.

**Never reprojects - labels only.** Resolving *which* CRS a point is
already in is not the same as converting it to a different one; per this
SDK's standing CRS policy (state honestly, let the consumer choose),
:func:`resolve_coordinate_crs` only ever picks an EPSG code and, where the
two raw values are ambiguous, the correct ``(a, b)`` assignment - the
numbers themselves are never transformed.

**Axis order is resolved by magnitude, not declared position.** Both
WGS84 and UTM have real axis-order traps (formal WGS84 is lat-first;
``CRS:84`` is lon-first; a feed's own posList order isn't guaranteed
either way - confirmed live: Norway's real UTM ``posList`` states
easting-then-northing, the opposite of the pointCoordinates path's
explicit lat-then-lon). Trusting declared/positional order is exactly the
kind of assumption this module exists to stop making - each
:class:`CrsProfile` states which value band is which, and the two raw
numbers are assigned to whichever band they actually fit, however they
arrived.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "CrsProfile",
    "CrsResolution",
    "resolve_coordinate_crs",
    "WGS84",
    "WGS84_NORWAY",
    "UTM33N_NORWAY",
    "LAMBERT72_BELGIUM",
]

_logger = logging.getLogger(__name__)

Status = Literal["declared", "inferred", "corrected", "unresolved"]

#: Matches urn:ogc:def:crs:EPSG::25833, http://www.opengis.net/def/crs/EPSG/0/25833,
#: EPSG:25833, or a bare 25833 - every real srsName shape seen across this
#: SDK's DATEX/GML fixtures. Compound CRSes (horizontal + vertical, seen
#: before on Norway's own NVDB product) are handled by taking the last
#: (innermost/horizontal) numeric component - see _parse_srs_name.
_EPSG_CODE = re.compile(r"(\d{4,5})(?!.*\d)")
_CRS84 = re.compile(r"CRS:?84", re.IGNORECASE)


def _parse_srs_name(srs_name: str | None) -> str | None:
    """``"urn:ogc:def:crs:EPSG::25833"``/``"EPSG:25833"``/``"25833"`` ->
    ``"EPSG:25833"``; ``"CRS:84"`` -> ``"EPSG:4326"`` (CRS:84 is WGS84,
    lon-first, the OGC web-services alias); ``None``/unparseable ->
    ``None``. Never guesses - an srsName this can't parse is treated the
    same as one that's absent, not silently assumed to be any particular
    CRS."""
    if not srs_name:
        return None
    if _CRS84.fullmatch(srs_name.strip()):
        return "EPSG:4326"
    match = _EPSG_CODE.search(srs_name)
    return f"EPSG:{match.group(1)}" if match else None


@dataclass(frozen=True)
class CrsProfile:
    """One known CRS's identity plus the real value-range band its
    coordinates fall into - used to recognise/arbitrate, never to
    reproject. ``band_a``/``band_b`` are ``(min, max)`` inclusive ranges
    for the two raw components, in this SDK's established ``(lat-like,
    lon-like)`` / ``(northing-like, easting-like)`` order - i.e. ``band_a``
    is whichever component is largest-northward, matching the ``(lat,
    lon)`` convention already used throughout :mod:`streetworks.datex2`.
    """

    epsg: str
    band_a: tuple[float, float]
    band_b: tuple[float, float]

    def order(self, raw_a: float, raw_b: float) -> tuple[float, float] | None:
        """If the two raw values fit this profile's bands in *either*
        order, return them correctly assigned to ``(band_a, band_b)`` -
        the axis-order-by-magnitude resolution. ``None`` if neither
        order fits."""
        if self.band_a[0] <= raw_a <= self.band_a[1] and self.band_b[0] <= raw_b <= self.band_b[1]:
            return (raw_a, raw_b)
        if self.band_a[0] <= raw_b <= self.band_a[1] and self.band_b[0] <= raw_a <= self.band_b[1]:
            return (raw_b, raw_a)
        return None


@dataclass(frozen=True)
class CrsResolution:
    """The result of resolving one point's real CRS. ``status`` is for the
    caller's own logging/counting only - see module docstring for why it
    never reaches :class:`~streetworks.common.models.Coordinate`."""

    epsg: str
    ordered: tuple[float, float]
    status: Status


#: General WGS84 - the full legitimate global range, deliberately not
#: narrowed to any one country, so this profile stays reusable across the
#: whole DATEX/GML family rather than accidentally Norway-specific.
#: **Not axis-order-disambiguating on its own** where both raw values are
#: under 90 in magnitude (e.g. a real Nordic lat/lon pair can fit either
#: assignment within -90..90/-180..180) - use a narrower, country-specific
#: profile like :data:`WGS84_NORWAY` wherever axis order actually needs
#: resolving, not just CRS identity.
WGS84 = CrsProfile(epsg="EPSG:4326", band_a=(-90.0, 90.0), band_b=(-180.0, 180.0))

#: WGS84, narrowed to real Norway-mainland latitude/longitude - confirmed
#: live (2026-07-30) against 503 real DATEX pointCoordinates elements in
#: one Statens vegvesen pull, 100% within these bands. Unlike the general
#: :data:`WGS84` profile above, these bands don't overlap each other, so
#: they genuinely disambiguate axis order rather than just confirming
#: "this is WGS84-shaped." Svalbard would push latitude to 74-81 degrees
#: (not expected in the mainland roadworks feed) - a point that lands
#: there resolves as "unresolved" rather than silently mishandled.
WGS84_NORWAY = CrsProfile(epsg="EPSG:4326", band_a=(57.0, 72.0), band_b=(4.0, 32.0))

#: ETRS89 / UTM zone 33N, Norway-mainland real value bands - confirmed
#: live (2026-07-30) against 2,133 real gmlLineString/posList elements in
#: one Statens vegvesen pull, 100% within these bands, 0 contradictions.
#: Svalbard would push latitude/northing outside this band (not expected
#: in the roadworks feed) - a point that lands there resolves as
#: "unresolved" rather than silently mishandled, see resolve_coordinate_crs.
UTM33N_NORWAY = CrsProfile(
    epsg="EPSG:25833", band_a=(6_400_000.0, 7_950_000.0), band_b=(100_000.0, 1_100_000.0)
)

#: Belgian Lambert 72 - the CRS's own documented extent for Belgian
#: territory (EPSG:31370's registered bounds). Unlike UTM33N_NORWAY above,
#: **not independently re-verified live this session** - Belgium's own
#: real mixed-CRS finding (see streetworks.datex2.belgium) predates this
#: module and was confirmed by other means; this profile exists so the
#: shared helper can recognise it too, not because Belgium's own adapter
#: has been migrated onto this helper yet (tracked as follow-up).
LAMBERT72_BELGIUM = CrsProfile(epsg="EPSG:31370", band_a=(0.0, 300_000.0), band_b=(0.0, 300_000.0))


def resolve_coordinate_crs(
    *,
    srs_name: str | None,
    raw_a: float,
    raw_b: float,
    encoding_default: str,
    candidates: tuple[CrsProfile, ...],
) -> CrsResolution:
    """Resolve one point's real CRS and correctly-ordered value, honestly.

    ``srs_name`` is the raw declared value (if any) from the source
    document. ``raw_a``/``raw_b`` are the two components exactly as
    received, in whatever order the source states them - this function
    resolves the order, the caller doesn't need to guess it first.
    ``encoding_default`` is the CRS to assume when nothing else is known
    (e.g. ``"EPSG:4326"`` for DATEX ``pointCoordinates``, which never
    carries ``srsName`` - see module docstring). ``candidates`` are the
    known :class:`CrsProfile`\\ s this call site can recognise by value
    range (only used to *arbitrate*, never to override a consistent
    declaration).

    Decision order, matching the real Norway/Belgium findings this was
    built from:

    1. ``srs_name`` declares a known EPSG whose profile is in
       ``candidates``, and the values fit that profile's band ->
       ``status="declared"``.
    2. ``srs_name`` declares a known EPSG but the values *don't* fit its
       profile's band -> the value range decides instead (checked against
       every candidate); logged loudly, ``status="corrected"`` - a
       declaration is never trusted over what the numbers themselves say.
    3. ``srs_name`` is absent or unparseable, and the values fit
       ``encoding_default``'s own profile (if it's one of ``candidates``)
       -> ``status="inferred"``.
    4. ``srs_name`` is absent, and the values *don't* fit
       ``encoding_default``'s band but *do* fit a different candidate ->
       that candidate wins, logged loudly, ``status="corrected"`` - this
       is exactly Belgium's original shape (real Lambert 72 values,
       tagged ``<latitude>``/``<longitude>``, no override stated at all;
       silently trusting the field name would have been wrong).
    5. Nothing matches anything -> ``status="unresolved"``, values passed
       through unordered (raw_a, raw_b) rather than a silent guess -
       flagged for the caller to surface, not hidden.
    """
    declared_epsg = _parse_srs_name(srs_name)
    declared_profile = next((c for c in candidates if c.epsg == declared_epsg), None)
    default_profile = next((c for c in candidates if c.epsg == encoding_default), None)

    def _best_range_match() -> tuple[CrsProfile, tuple[float, float]] | None:
        for profile in candidates:
            ordered = profile.order(raw_a, raw_b)
            if ordered is not None:
                return profile, ordered
        return None

    if declared_epsg is not None:
        if declared_profile is not None:
            ordered = declared_profile.order(raw_a, raw_b)
            if ordered is not None:
                return CrsResolution(epsg=declared_epsg, ordered=ordered, status="declared")
            match = _best_range_match()
            if match is not None:
                winner, ordered = match
                _logger.warning(
                    "CRS declaration contradicted by real values: srsName declared %s "
                    "but (%r, %r) doesn't fit that profile's band - using value-range-"
                    "inferred %s instead. Never reprojected, only relabelled.",
                    declared_epsg,
                    raw_a,
                    raw_b,
                    winner.epsg,
                )
                return CrsResolution(epsg=winner.epsg, ordered=ordered, status="corrected")
            return CrsResolution(epsg=declared_epsg, ordered=(raw_a, raw_b), status="unresolved")
        # Declared to a CRS this call site has no profile for - trust the
        # declaration (nothing to cross-check it against), but there's no
        # band to resolve axis order from either.
        return CrsResolution(epsg=declared_epsg, ordered=(raw_a, raw_b), status="declared")

    if default_profile is not None:
        ordered = default_profile.order(raw_a, raw_b)
        if ordered is not None:
            return CrsResolution(epsg=encoding_default, ordered=ordered, status="inferred")

    match = _best_range_match()
    if match is not None:
        winner, ordered = match
        _logger.warning(
            "No CRS declared and values don't fit the assumed default %s: "
            "(%r, %r) - using value-range-inferred %s instead. Never "
            "reprojected, only relabelled.",
            encoding_default,
            raw_a,
            raw_b,
            winner.epsg,
        )
        return CrsResolution(epsg=winner.epsg, ordered=ordered, status="corrected")

    return CrsResolution(epsg=encoding_default, ordered=(raw_a, raw_b), status="unresolved")
