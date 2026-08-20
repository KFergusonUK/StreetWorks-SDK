"""Ireland: MapRoad Roadworks Licensing (MRL) - investigated, and
**deliberately not built as a functional adapter**.

.. attention::
   **This is a documented, honest scaffold, not a working client.**
   Constructing :class:`MapRoadClient` raises
   :class:`~streetworks.exceptions.ProviderUnavailableError` immediately -
   there is no network call, no parser, no fixture, because there is
   nothing publicly documented to build against. See "Why scaffold, not
   build" below.

**What MapRoad actually is.** MapRoad Licensing (`maproadroadworkslicensing.ie
<https://maproadroadworkslicensing.ie/MRL/>`_) is Ireland's real national
system for managing road opening licence applications - run by the Road
Management Office (RMO) under the Local Government Management Agency
(LGMA). It genuinely covers **both national and local roads** (TII's own
consents for national-road works route through it; regional/local works
are the local authorities', also via MapRoad) - the richest real
coverage of any Irish roadworks source investigated, if it were
reachable.

**This is a genuinely different case from TII's own DATEX II feed
(`data.tii.ie`), already checked and ruled out** - that feed's real,
published dataset catalogue (verified directly, all real dataset titles
enumerated) carries travel times, weather, VMS/VDS, collision rates, and
traffic counts, but no roadworks/Situation publication at all. MapRoad
is the real roadworks source; the question this module answers is
whether it can be *read* by a data consumer, not just written to by a
licence applicant.

**Why scaffold, not build - confirmed from Ireland's own official
catalogue metadata (`datacatalogue.gov.ie
<https://datacatalogue.gov.ie/dataset/maproad-roadworks-licensing-system>`_),
not a guess.** The listing states, together: ``API Available: Yes``,
``Open Data: No``, ``Data Sharing: Yes``, and ``Personal Data: Yes``.
Read together, not selectively, this describes a real API that exists
for a **formal, gated data-sharing arrangement** - not a self-service
developer key, and not an open, anonymous feed. ``Personal Data: Yes``
is the real reason: licence applications carry applicant/company
contact details, a genuine GDPR concern an open feed wouldn't have (a
real, material difference from NYC DOT's own permit register, which is
open precisely because its records don't carry that same personal-data
weight). Registration for MapRoad itself is a real, formal applicant
process (download a registration pack, complete it, email it to
``contact@rmo.ie``) aimed at utilities/contractors *submitting*
applications - not a self-service consumer sign-up. **No technical
shape for a read path - endpoint, schema, authentication mechanism -
was found published anywhere**, unlike Trafikverket/Vejdirektoratet/
Traffic SA, all of which have a real, live-probed or documented contract
this SDK could describe even while blocked from using it. There is
nothing here to build a client against without guessing a private
contract, the same documented-unavailable-scaffold discipline this SDK
already uses for Greece - see :mod:`streetworks.greece`.

**The cleaner alternative for anyone who actually needs Irish roadworks
data**: contact the RMO (``contact@rmo.ie``) directly to ask about a
formal data-sharing agreement for MapRoad - the real, stated access
route for a party with a genuine need, not a self-service one this SDK
can automate.

**Licence**: not specified on the catalogue listing (the "Licenses"
field is empty).

**Credentials**: none apply in the way this SDK usually means it - no
API key or token would unlock read access; the stated route is a
data-sharing agreement, a relationship, not a credential.
"""

from __future__ import annotations

import warnings
from typing import Any

from ..exceptions import ProviderUnavailableError

__all__ = ["MapRoadClient"]

warnings.warn(
    "streetworks.maproad is a documented-but-unavailable scaffold: MapRoad "
    "Roadworks Licensing has a real, government-catalogued API, but "
    "Ireland's own catalogue metadata (API Available: Yes, Open Data: No, "
    "Data Sharing: Yes, Personal Data: Yes) describes a formal, gated "
    "data-sharing arrangement, not a self-service developer key - no "
    "technical shape for a read path is published anywhere found. "
    "MapRoadClient() always raises ProviderUnavailableError - see the "
    "module docstring for the full investigation, and the 'help wanted' "
    "issues at https://github.com/KFergusonUK/StreetWorks-SDK/issues if a "
    "documented read API ever surfaces.",
    UserWarning,
    stacklevel=2,
)

_UNAVAILABLE_MESSAGE = (
    "streetworks.maproad: MapRoad Roadworks Licensing has a real, "
    "government-catalogued API (datacatalogue.gov.ie confirms 'API "
    "Available: Yes'), but it is a formal, gated data-sharing arrangement "
    "('Open Data: No', 'Data Sharing: Yes', 'Personal Data: Yes'), not a "
    "self-service developer key - no published endpoint, schema, or "
    "authentication mechanism was found for a read path. Building a "
    "client against an unpublished private contract is out of scope - "
    "see this module's own docstring for the full reasoning, and contact "
    "contact@rmo.ie directly for a formal data-sharing agreement if you "
    "have a genuine need."
)


class MapRoadClient:
    """MapRoad Roadworks Licensing has no publicly documented read API -
    construction itself raises
    :class:`~streetworks.exceptions.ProviderUnavailableError` immediately,
    making no network call and offering no other entry point to work
    around it. See module docstring for the full investigation and why
    this is a documented scaffold, not a functional client.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ProviderUnavailableError(_UNAVAILABLE_MESSAGE)
