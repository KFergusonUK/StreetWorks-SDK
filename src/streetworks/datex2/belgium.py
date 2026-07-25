"""Belgium (Flanders / Verkeerscentrum) roadworks - DATEX II v3,
credential-free.

Verkeerscentrum Vlaanderen (the Flemish traffic centre, part of Agentschap
Wegen en Verkeer) publishes real-time traffic situations, including
roadworks, as open DATEX II v3 - no registration, no API key.

**Confirmed live, 2026-07**: a single ``GET`` on ``datex2v3full`` (~390 KB)
returns around 100 real situations. Standard DATEX II v3 envelope
(``d2Payload``/``sit:``/``loc:``), parsed through the same shared
:func:`~streetworks.datex2.parser.iter_situations_full` /
:func:`~streetworks.datex2.parser.iter_roadworks_full` every other DATEX
adapter uses - no bespoke parse path, but this feed did surface two real,
significant findings that changed the *shared* parser/model, not just this
client (see below) - the brief's own "verify-first" instruction paid for
itself twice over here.

**Coverage is Flanders only, not all of Belgium** - confirmed, not
assumed. Every real situation states
``supplierIdentification/nationalIdentifier`` as ``"BETICV"`` (Belgium
Traffic Information Centre Vlaanderen), and the dataset itself is named
"DATEX2 feed Verkeerscentrum Vlaanderen" on transportdata.be (Belgium's
federal NAP, a CKAN catalogue). Belgium's traffic data is genuinely
regionally fragmented - Wallonia publishes its own, separate "Événements
routiers en Wallonie" dataset on the same NAP, not wrapped here; Brussels
wasn't checked. Same discipline as France (non-concessionary network only)
and Spain (excl. Catalonia/Basque Country): partial coverage, stated
honestly, not implied to be national.

**The discriminator gap this feed surfaced (a second one, different in
shape from Spain's)**: of ~195 roadworks-relevant records in one live
pull, only 19 used the dedicated ``MaintenanceWorks`` xsi:type (zero used
``ConstructionWorks``). The other 67 were the generic
``RoadOrCarriagewayOrLaneManagement`` record, discriminated only by
``roadOrCarriagewayOrLaneManagementType=newRoadworksLayout`` - a real
DATEX II v3 standard enum value, unambiguous by name (not Belgium-specific
- other profiles could use it too). Sitting alongside those 67 in the same
xsi:type were 61 other records with genuinely different values
(``narrowLanes``, ``roadClosed``, ``contraflow``,
``singleAlternateLineTraffic``) that can arise from accidents or events,
not just works - so they're deliberately **not** matched. Fixed additively
in :attr:`~streetworks.datex2.models.SituationRecord.is_roadworks` (see
that property's own comment) - confirmed this doesn't change any other
adapter's real fixture, including DGT's own 7 real
``RoadOrCarriagewayOrLaneManagement`` records, which use entirely
different type values.

**The CRS finding - the more significant one.** Every real coordinate in
this feed is stated in **Belgian Lambert 72 (EPSG:31370)**, not WGS84 -
confirmed from the ``srsName="EPSG:31370"`` attribute on every real
``gmlLineString``, and from the values themselves (hundred-thousands, the
right order of magnitude for Lambert 72 eastings/northings; genuine
Belgian WGS84 latitudes would read ~49-52). The source XML still uses the
tag names ``<latitude>``/``<longitude>`` for point coordinates even though
the values are Lambert 72, not degrees - genuinely misleading if trusted
at face value rather than checked against the stated ``srsName``. Per this
SDK's standing CRS policy (never silently reproject - the same choice
already made for Saxony's UTM33N and the UK's British National Grid
providers), coordinates are carried through **unconverted**, and
:func:`~streetworks.common.from_datex2` gained a ``crs`` parameter so
callers can state this explicitly rather than the converter assuming
WGS84 for every DATEX source, which was true of every adapter checked
before this one but isn't universal.

**Location, verified across all real roadworks-relevant records (86/86 in
one live pull)**: 100% coordinate coverage, no Alert-C-only records -
resolving the brief's own open question about this feed. Alert-C
references are present *alongside* the coordinates (not instead of them)
on many records, preserved in ``alert_c_location`` as usual, never
decoded.

**Other honest gaps, confirmed against the real feed**: no
``generalPublicComment`` on any record checked, so ``traffic_management``
comes out ``None`` throughout; ``roadNumber``/``roadName`` were both
absent on every roadworks record checked, so ``location_description``
comes out ``None`` too - this feed identifies *where* precisely (via
coordinates) but not *which road* by name/number.

**Licence - genuinely not a permissive open licence, unlike Bison
Futé/DGT/Luxembourg.** No per-dataset licence badge exists on the CKAN
catalogue entry itself. The NAP's own site-wide Terms of Use
(https://www.transportdata.be/pages/terms-of-use,
https://www.transportdata.be/fr/pages/terms-of-use) state, in French
(original) and English (the site's own translation, matching):

    FR: "les informations publiées sur ce site web ne peuvent en aucun
    cas : être copiées et reproduites de manière excessive… être
    diffusées ou communiquées à des tiers à des fins commerciales… être
    utilisées à des fins illégales"

    EN: "The data listed on this website... may not be in any event:
    copied or reproduced in an excessive manner... distributed or shared
    with third parties with a view to commercial purposes... used for
    illegal purposes."

Free to use, but **commercial redistribution to third parties is
explicitly prohibited** - a real, binding restriction, not a formality.
Because this SDK is itself redistributed openly, real fixture data was
judged too close to that restriction to include here; the test fixture is
synthetic, built to the real, confirmed shape (Lambert 72 coordinates,
the ``newRoadworksLayout``/``MaintenanceWorks`` split) rather than trimmed
from a live pull - the same choice already made for Autobahn GmbH's
unconfirmed licence.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Situation
from .parser import iter_roadworks_full as _iter_roadworks_full
from .parser import iter_situations_full as _iter_situations_full

__all__ = ["BASE_URL", "DATEX_PATH", "CRS", "BelgiumClient"]

BASE_URL = "https://www.verkeerscentrum.be"
DATEX_PATH = "uitwisseling/datex2v3full"

#: Belgian Lambert 72 - confirmed live, not WGS84. See module docstring.
#: Pass this to :func:`streetworks.common.from_datex2`'s ``crs`` parameter.
CRS = "EPSG:31370"


class BelgiumClient:
    """Fetch Flemish (not all-Belgium - see module docstring) roadworks
    from Verkeerscentrum Vlaanderen. No credentials required.

    >>> from streetworks.datex2.belgium import BelgiumClient, CRS
    >>> from streetworks.common import from_datex2
    >>> with BelgiumClient() as be:
    ...     situations = list(be.iter_roadworks())
    >>> for situation in situations:
    ...     works = from_datex2(
    ...         situation, territory="Belgium",
    ...         administrative_area="Flanders", crs=CRS,
    ...     )
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_situations(self) -> bytes:
        """``GET datex2v3full`` - the raw DATEX II XML response body (all
        current traffic situations on the Flemish network, including
        roadworks)."""
        response = self._transport.request("GET", f"{self.base_url}/{DATEX_PATH}")
        return response.content

    def iter_situations(self) -> Iterator[Situation]:
        yield from _iter_situations_full(io.BytesIO(self.get_situations()), provider="Belgium")

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record - see module docstring for why that isn't a
        simple ``MaintenanceWorks``/``ConstructionWorks``-only check for
        this feed."""
        yield from _iter_roadworks_full(io.BytesIO(self.get_situations()), provider="Belgium")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BelgiumClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
