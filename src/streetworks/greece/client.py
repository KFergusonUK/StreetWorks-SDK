"""Greece: investigated, and **deliberately not built as a functional
adapter** - no roadworks source exists, open or otherwise.

.. attention::
   **This is a documented, honest scaffold, not a working client.**
   Constructing :class:`GreeceClient` raises
   :class:`~streetworks.exceptions.ProviderUnavailableError` immediately -
   there is no network call, no parser, no fixture, because there is
   nothing to build against. See "Why scaffold, not build" below.

**Greece's real National Access Point (`www.nap.gov.gr`, confirmed as
the official MMTIS/RTTI/SRTI/SSTP NAP for Greece per the European
Commission's own October 2025 National Access Points list) is a
decentralised metadata catalogue (CKAN, run by CERTH/HIT), not a
centralised DATEX II feed** - the reason Greece is absent from the
pan-EU DATEX aggregators that carry ~24 other live NAPs (Italy among
them - see :mod:`streetworks.cciss`).

**What the catalogue actually contains, confirmed via its own real
dataset titles** (not a guess): POI and sensor data - truck parking,
refuelling points, KTEL bus and ferry timetables, Motorist Service
Stations, Thessaloniki floating-car-data (speed/congestion/travel-time
estimates), and toll-operator sensor feeds - real Vehicle Detection
Sensor data from Attiki Odos, Road Weather Information System locations
for Egnatia Odos, and real-time Variable Message Sign data from the
Hellastron network (Aegean Motorway, Attiki Odos, Gefyra, Egnatia Odos,
Kentriki Odos, Moreas Motorway, Ionia Odos, Nea Odos, Olympia Odos).
**No roadworks or DATEX II Situation Publication dataset anywhere.**
The real DATEX contributors (the motorway companies, the toll-road
association Hellastron, CERTH/HIT) publish traffic-*flow* and sensor
data, not roadworks - the same "NAP exists, roadworks absent" shape
this SDK already found for Ireland's TII feed (see
:mod:`streetworks.maproad`), settled here by real dataset-title
inspection, not assumption.

**A second, independent reason nothing can be built right now: the
portal itself is genuinely down.** Confirmed live (2026-08-03) via
direct probing, not a single fluke: ``data.nap.gov.gr`` returns a real
``502 Bad Gateway`` from its own CKAN backend (nginx front, broken
backend - reproduced on both the dataset-list page and the
``/api/3/action/package_list`` API endpoint); its mirror,
``data.nap.imet.gr``, hangs at the TLS handshake stage and never
completes a connection. Even if a roadworks dataset existed, the portal
serving it is not currently reachable.

**Even a best-case future (a toll operator publishing its own roadworks
feed) would only ever be motorway-concession-only, fragmented per
operator** - not a genuine national source, unlike MapRoad's real
national+local Irish coverage (see :mod:`streetworks.maproad`) or
CCISS's real Italy-wide one (see :mod:`streetworks.cciss`).

**Licence**: not applicable - there is no dataset to license.

**Credentials**: none apply - there is no API to authenticate to.
"""

from __future__ import annotations

import warnings
from typing import Any

from ..exceptions import ProviderUnavailableError

__all__ = ["GreeceClient"]

warnings.warn(
    "streetworks.greece is a documented-but-unavailable scaffold: Greece's "
    "real National Access Point (nap.gov.gr) is a decentralised metadata "
    "catalogue of POI/sensor data (truck parking, VMS/VDS, weather, "
    "floating car data) with no roadworks or DATEX II Situation dataset at "
    "all - confirmed via its own real dataset titles, not assumed. The "
    "portal itself is also currently unreachable (a real 502 on its CKAN "
    "backend). GreeceClient() always raises ProviderUnavailableError - see "
    "the module docstring for the full investigation, and the 'help "
    "wanted' issues at https://github.com/KFergusonUK/StreetWorks-SDK/issues "
    "if a documented roadworks source (national or toll-operator) ever "
    "surfaces.",
    UserWarning,
    stacklevel=2,
)

_UNAVAILABLE_MESSAGE = (
    "streetworks.greece: Greece's real National Access Point (nap.gov.gr) "
    "carries POI/sensor data (truck parking, refuelling points, KTEL bus/"
    "ferry timetables, floating car data, toll-operator VMS/VDS/weather) "
    "but no roadworks or DATEX II Situation Publication dataset at all - "
    "confirmed by direct inspection of its real dataset titles, not "
    "assumed. The portal is also currently unreachable (a real 502 Bad "
    "Gateway on its own CKAN backend, confirmed live). There is nothing "
    "here to build a client against - see this module's own docstring for "
    "the full reasoning."
)


class GreeceClient:
    """Greece has no roadworks source, open or otherwise - construction
    itself raises :class:`~streetworks.exceptions.ProviderUnavailableError`
    immediately, making no network call and offering no other entry
    point to work around it. See module docstring for the full
    investigation and why this is a documented scaffold, not a
    functional client.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ProviderUnavailableError(_UNAVAILABLE_MESSAGE)
