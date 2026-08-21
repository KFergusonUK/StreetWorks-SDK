"""USDOT WZDx Feed Registry - discover feed URLs.

The registry (`datahub.transportation.gov <https://datahub.transportation.gov/Roadways-and-Bridges/Work-Zone-Data-Feed-Registry/69qe-yiui/about_data>`_,
a Socrata dataset) lists every agency-published WZDx feed: URL, format,
version, auth requirement, and whether it's currently active. No
credentials required to read the registry itself. Confirmed live
2026-08-02: 41 rows total.

**The real WZDx/CWZ discriminator is ``version``, not ``format``.**
``format`` is only ever the literal string ``"geojson"`` or ``"json"`` on
every real row checked - it never distinguishes spec family, despite
being the field an earlier design assumed would. CWZ (Connected Work
Zone, a joint AASHTO/ITE/NEMA/SAE schema built on WZDx v4.2 as its own
base) rows instead state the real, exact value ``version == "CWZ 1.0"``
(4/41 real rows). :mod:`streetworks.wzdx.parser` parses CWZ 1.0 too (see
its own module docstring for how the camelCase variant one real vendor
emits is handled) - so :attr:`RegistryEntry.is_supported_wzdx` now
includes it, and ``wzdx_only`` no longer drops it. Check
``entry.needapikey`` regardless: 3 of the 4 real CWZ rows found live
(Massachusetts DOT, Colorado DOT, Illinois DOT) require a credential this
SDK does not obtain on a caller's behalf - only PurposeBuilt Systems'
real CWZ feed is genuinely keyless.

**Real WZDx version strings are inconsistently formatted** - ``"4"``
appears alongside ``"4.1"``/``"4.2"`` (not ``"4.0"``), so version parsing
treats a bare integer as an implicit ``.0``. No sub-3.1 real version was
found live, but the floor is still enforced defensively, since the
registry is explicitly the thing that tracks churn (feed additions,
removals, version bumps - see its own changelog). One real row
(Michigan DOT, also the one inactive entry live) has no ``version`` at
all - treated the same as an unparseable one, a documented skip, never a
crash.

**``needapikey`` is absent, not ``false``, on most rows that need no
key** - confirmed live: 13/41 real rows state ``needapikey: true``, 1
states it explicitly ``false``, and the other 27 simply omit the field.
:func:`_parse_entry` treats absence as ``False`` (no key needed), the
same "missing means not required" convention this SDK already uses
elsewhere. ``apikeyurl`` is a real nested ``{"url": ..., "description":
...}`` dict, the identical shape ``url`` already has - both unwrapped the
same way.

**The registry is not purely US** - a real Quebec City, Canada row
(``state: "n/a"``) is live and active, confirmed - callers wanting
US-only coverage should filter on ``state``/``organization`` themselves;
this module does not assume "US" is the only real value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .._transport import RetryConfig
from ..socrata import SodaClient

__all__ = ["RegistryEntry", "list_feeds", "REGISTRY_URL"]

JSON = dict[str, Any]

REGISTRY_URL = "https://datahub.transportation.gov/resource/69qe-yiui.json"

#: The lowest WZDx spec version this SDK's parser is confirmed against -
#: see :mod:`streetworks.wzdx.client`'s own module docstring for the
#: version-tolerant field handling. A real version below this, or an
#: unparseable one, is excluded by :attr:`RegistryEntry.is_supported_wzdx`.
_MIN_WZDX_VERSION = (3, 1)

#: Real, exact CWZ ``version`` values this SDK's parser handles (see
#: :mod:`streetworks.wzdx.parser`'s own module docstring) - checked
#: separately from :data:`_MIN_WZDX_VERSION` since ``"CWZ 1.0"`` fails the
#: plain numeric parse :func:`_parse_version` does for WZDx versions.
_SUPPORTED_CWZ_VERSIONS = frozenset({"CWZ 1.0"})


@dataclass(frozen=True)
class RegistryEntry:
    """One registered feed."""

    state: str | None
    organization: str | None
    feed_name: str | None
    url: str | None
    format: str | None
    version: str | None
    active: bool | None
    needapikey: bool
    apikeyurl: str | None
    raw: JSON

    @property
    def is_supported_wzdx(self) -> bool:
        """Whether ``version`` is a real WZDx or CWZ spec version this
        SDK's parser handles - ``False`` for a missing version or anything
        below :data:`_MIN_WZDX_VERSION` that isn't a recognised CWZ
        version. See module docstring."""
        if self.version in _SUPPORTED_CWZ_VERSIONS:
            return True
        parsed = _parse_version(self.version)
        return parsed is not None and parsed >= _MIN_WZDX_VERSION


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return None


def _url_field(value: Any) -> str | None:
    """Unwraps a Socrata ``url``-type column - a real ``{"url": ...}``
    dict on every row checked, never a bare string, but handled either
    way. Shared by ``url`` and ``apikeyurl``, the identical real shape."""
    if isinstance(value, dict):
        url = value.get("url")
        return url if isinstance(url, str) else None
    if isinstance(value, str):
        return value
    return None


def _parse_version(value: str | None) -> tuple[int, int] | None:
    """``None`` for anything that isn't a plain ``major[.minor]`` numeric
    version - real CWZ rows state ``"CWZ 1.0"`` (fails the digit check on
    the first component), and a real Michigan DOT row states no version
    at all. A bare ``"4"`` (a real, confirmed-live formatting quirk, not
    hypothetical) is treated as ``(4, 0)``."""
    if not value:
        return None
    parts = value.strip().split(".")
    if len(parts) == 1:
        parts.append("0")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return None
    return (int(parts[0]), int(parts[1]))


def _parse_entry(row: JSON) -> RegistryEntry:
    return RegistryEntry(
        state=row.get("state"),
        organization=row.get("issuingorganization"),
        feed_name=row.get("feedname"),
        url=_url_field(row.get("url")),
        format=row.get("format"),
        version=row.get("version"),
        active=_as_bool(row.get("active")),
        needapikey=bool(_as_bool(row.get("needapikey"))),
        apikeyurl=_url_field(row.get("apikeyurl")),
        raw=row,
    )


def list_feeds(
    *,
    active_only: bool = True,
    wzdx_only: bool = True,
    registry_url: str = REGISTRY_URL,
    retry: RetryConfig | None = None,
    timeout: float = 30.0,
    client: httpx.Client | None = None,
) -> list[RegistryEntry]:
    """Fetch and parse the WZDx feed registry. ``active_only`` (default)
    drops entries the registry itself has flagged inactive - it does not
    verify the feed is actually reachable right now. ``wzdx_only``
    (default) drops any entry whose version this SDK's parser can't
    handle (see :attr:`RegistryEntry.is_supported_wzdx`) - a documented
    skip, never a crash. This now includes real CWZ 1.0 feeds (the
    parser handles those too - see :mod:`streetworks.wzdx.parser`); the
    name is kept for compatibility rather than renamed to something like
    ``supported_only``. Check ``entry.needapikey`` before
    calling :meth:`~streetworks.wzdx.WZDxClient.fetch` on a returned
    entry's ``url`` - about a third of real feeds need a key the caller
    must supply themselves (``entry.apikeyurl`` points at signup). Reads
    via :class:`~streetworks.socrata.SodaClient`, the shared Socrata
    transport this SDK's Socrata providers build on."""
    with SodaClient(retry=retry, timeout=timeout, client=client) as soda:
        entries = [_parse_entry(row) for row in soda.iter_records(registry_url)]
    if active_only:
        entries = [e for e in entries if e.active]
    if wzdx_only:
        entries = [e for e in entries if e.is_supported_wzdx]
    return entries
