"""Northern Territory: Road Report NT (Department of Infrastructure,
Planning and Logistics - DIPL, since renamed Department of Logistics and
Infrastructure - DLI; the agency name is itself in flux) - investigated,
and **deliberately not built as a functional adapter**.

.. attention::
   **This is a documented, honest scaffold, not a working client.**
   Constructing :class:`RoadReportNtClient` raises
   :class:`~streetworks.exceptions.ProviderUnavailableError` immediately -
   there is no network call, no parser, no fixture, because there is
   nothing real to build against. See "Why scaffold, not build" below.

**Coverage** (from ``roadreport.nt.gov.au``'s own public description):
all NT-Government-managed roads statewide, including remote/unsealed and
Aboriginal-land access roads - **council roads excluded** (the site
directs those inquiries to the relevant local council instead).

**Nature - a road-*condition* system, not a roadworks/permit system.**
Real page content is dominated by closures, impassable-road reports,
weight/vehicle-type restrictions, and flooding; roadworks is, at best, a
minor subset of what this service actually publishes - the weakest real
works-fit of any provider this SDK has looked at.

**Why scaffold, not build.** Every other credential-blocked provider in
this SDK (Trafikverket, Vejdirektoratet, Traffic SA) is blocked on
*access* to a real, published interface - a key or a token away from
working, with a documented (or at least self-describing, live-probed)
contract to build against. NT is different in kind: it has **no
published REST/GeoJSON API at all**. The real frontend
(``roadreport.nt.gov.au/road-map``, a minified Angular single-page app)
was inspected directly - its bundled JavaScript references the Microsoft
SignalR client library (``aka.ms/signalr-core-differences`` appears
verbatim in the bundle) and a real hub connection named
``"roadsReportingHub"``, invoking hub methods by name over that
persistent connection - a real one, ``"GetAllMajorRoadObstructions"``, was
found as a literal string in the bundle. **This is inferred from a
minified JS bundle, not a published specification** - stated explicitly
here so no future contributor mistakes reverse-engineered hub method
names for a documented contract, the same distinction this SDK draws
everywhere else between "confirmed live" and "guessed."

Building a working client against that inference would mean: (1)
encoding hub method names / the SignalR negotiate handshake / message
framing as if they were a stable public contract, when they're a private
app's internal implementation detail that could change without notice;
(2) committing this SDK to an entirely new persistent-connection
transport (WebSocket/long-polling via SignalR) for its single weakest
real works-fit provider - every other client in this SDK is a plain
request/response HTTP call; (3) consuming what is, functionally, a
private mobile-app backend rather than an offered open data feed. None of
that is worth doing for a source whose own real content is mostly road
*conditions*, not roadworks. So: documented, not implemented.

**The cleaner alternative for anyone who actually needs NT roadworks
data**: the National Freight Data Hub's harmonised aggregate feed is,
for once, plausibly the *right* source rather than the usual
lossier-re-serve - precisely because no direct NT API exists to prefer
over it. **Unverified whether it actually carries real NT records** (as
opposed to a catalogue pointer back to this same unreachable interface) -
worth checking before relying on it.

**Licence**: not specified on any catalogue listing found.

**Credentials**: none apply - there is no API to authenticate to.
"""

from __future__ import annotations

import warnings
from typing import Any

from ..exceptions import ProviderUnavailableError

__all__ = ["RoadReportNtClient"]

warnings.warn(
    "streetworks.au.nt is a documented-but-unavailable scaffold: Road "
    "Report NT has no published REST/GeoJSON API - its real backend is an "
    "undocumented SignalR hub, reverse-engineered from a minified JS "
    "bundle, not a contract this SDK builds clients against. "
    "RoadReportNtClient() always raises ProviderUnavailableError - see "
    "the module docstring for the full investigation, and the 'help "
    "wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues if a "
    "documented REST equivalent ever surfaces.",
    UserWarning,
    stacklevel=2,
)

_UNAVAILABLE_MESSAGE = (
    "streetworks.au.nt: Road Report NT has no published REST/GeoJSON API. "
    "Its real backend is an undocumented SignalR real-time hub "
    "('roadsReportingHub', confirmed live by inspecting the site's own "
    "minified Angular bundle - a hub method literally named "
    "'GetAllMajorRoadObstructions' was found there), not a published "
    "contract this SDK can build a stable client against. Consuming a "
    "private app backend inferred from minified JS is out of scope - see "
    "this module's own docstring for the full reasoning, and the National "
    "Freight Data Hub for a possible alternative route (unverified whether "
    "it carries real NT records)."
)


class RoadReportNtClient:
    """Road Report NT has **no published REST/GeoJSON API** - construction
    itself raises :class:`~streetworks.exceptions.ProviderUnavailableError`
    immediately, making no network call and offering no other entry point
    to work around it. See module docstring for the full investigation
    and why this is a documented scaffold, not a functional client.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ProviderUnavailableError(_UNAVAILABLE_MESSAGE)
