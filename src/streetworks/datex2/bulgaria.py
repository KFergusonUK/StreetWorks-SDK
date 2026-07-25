"""Bulgaria (Road Infrastructure Agency / LIMA) roadworks - DATEX II v2.3,
credential-free.

Агенция "Пътна инфраструктура" (the Road Infrastructure Agency) publishes
current roadworks on the republican road network as open DATEX II v2.3 via
its LIMA platform's public-facing download site, ``datasheet.api.bg`` - no
registration, no API key.

**The NAP-listed endpoint is wrong - confirmed live.** NAPCORE lists
``lima.api.bg`` as the RTTI NAP; it's unreachable (connection refused,
consistently, on both HTTP and HTTPS). The working host is
``datasheet.api.bg``, a separate public download front for the same LIMA
platform. This is now a recurring pattern across this survey (see
``docs/nap-survey.md``) - the listed NAP is not always the real door.

**The file URL is date-stamped, not fixed - so this adapter is a two-step
fetch.** ``datasheet.api.bg`` doesn't serve roadworks at a stable URL; each
dataset's catalogue page links a same-day file
(``/files/YYYYMMDD_roadworks_r03.xml``) that changes daily. :meth:`get_situations`
therefore fetches the catalogue page first, extracts today's real file link,
then fetches that file - confirmed live (2026-07): the linked file's own
``publicationTime`` matches the fetch time.

**Three category datasets exist; only one is needed - confirmed live, not
assumed.** LIMA's roadworks catalogue splits into three separately
downloadable datasets: "Closed Roads" (``r01``, 14 records), "Closed
Roadways" (``r02``, 46 records), and "Short-term Road Construction"
(``r03``, 150 records) in one live pull. Checking the real record IDs
across all three showed ``r03`` is a strict superset of ``r01`` and ``r02``
combined (every ``r01``/``r02`` record ID also appears in ``r03``; the
union of all three equals ``r03`` alone) - so fetching ``r03`` alone gives
the complete picture, and this adapter does exactly that rather than
fetching and de-duplicating three files.

**Encoding is mislabeled - confirmed live, worked around here, not in the
shared parser.** The real file's XML declaration states
``encoding="UTF-16"``, but the actual bytes are UTF-8 (verified from the
raw byte sequence - no null-byte padding, no BOM, plain UTF-8 throughout).
A strict XML parser (Python's ``xml.etree.ElementTree`` included) rejects
this outright (``ParseError: encoding specified in XML declaration is
incorrect``). :meth:`get_situations` rewrites the declared encoding to
``UTF-8`` (matching the real bytes) before handing the document to the
shared parser - a source-specific fix kept local to this adapter, since no
other feed checked in this SDK has shown the same mislabelling.

**Discriminator - a third dedicated type, distinct from both existing
ones.** Every real roadworks record checked (150/150 in one live pull, all
three category files) uses the bare xsi:type ``Roadworks`` directly, not
``MaintenanceWorks``/``ConstructionWorks`` - not schema-typical (``Roadworks``
is normally an abstract base type in the DATEX II model, not something fed
directly to ``xsi:type``), but real, live data. Added to
:data:`~streetworks.datex2.models.ROADWORKS_TYPES` (see that module's own
comment for the live-regression check confirming zero drift across every
other adapter's real fixture data).

**Location, verified across all 150 real records**: every record states
**three** ``pointByCoordinates`` under one ``groupOfLocations`` (xsi:type
``Point``) rather than a single point or a proper linear location - real
WGS84 values throughout (roughly 41.7-44.2 latitude, 22.4-28.6 longitude,
correct for Bulgaria; no ``srsName`` override anywhere, unlike Belgium).
The shared parser's point-location handling
(:func:`~streetworks.datex2.parser._parse_location`) captures only the
*first* of the three points, same as its existing behaviour for every
other point-kind location in this SDK - so coordinate coverage is 100%,
but each site's stated path/extent (the other two points) isn't captured.
Documented here rather than changed in the shared parser, which would mean
inventing a new location kind for a pattern seen in exactly one feed so
far.

**Other honest gaps, confirmed against the real feed**: neither
``roadNumber`` nor an Alert-C location name is present on any record
checked - locations are identified by coordinates and free-text comments
only (e.g. road numbers appear inside ``generalPublicComment`` text, e.g.
``"III-5509"``, but aren't parsed out of prose). ``cause`` is absent on
every record; ``roadworks/maintenanceWorks/roadMaintenanceType`` is always
``"roadworks"`` but sits three levels deep (inside
``roadworks``/``maintenanceWorks``), one level past what the shared
parser's ``road_maintenance_type`` direct-child lookup reaches - so that
field comes out ``None`` for Bulgaria, and :func:`~streetworks.common.from_datex2`
falls back to ``record_type`` (``"Roadworks"``) for ``works_type``, which
is accurate.

**Licence - genuinely unconfirmed, not just unchecked.** No licence badge,
name, or terms text exists anywhere on ``datasheet.api.bg`` itself - only a
bare copyright line ("© 2020 Road Infrastructure Agency"). A terms page was
located at ``lima.api.bg/privacy/index``, but since ``lima.api.bg`` is
itself unreachable, that text could only be checked secondhand (a
search-result cache), not read directly - so it's **not** treated as
confirmed. Per the Autobahn GmbH/Belgium precedent, the test fixture here
is **synthetic**, built to the real, confirmed shape (three points per
location, the bare ``Roadworks`` xsi:type, the mislabelled UTF-16
declaration) rather than trimmed from a live pull.

**Scope**: the "Republican Road Network" (the national road network under
the Road Infrastructure Agency's own administration) - stated on the
dataset's own description, not independently cross-checked against a
region-by-region breakdown the way Belgium's was, since Bulgaria's single
national road authority doesn't raise the same fragmentation question
Belgium/Germany/Spain do.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Situation
from .parser import iter_roadworks_full as _iter_roadworks_full
from .parser import iter_situations_full as _iter_situations_full

__all__ = ["BASE_URL", "CATALOGUE_PATH", "BulgariaClient"]

BASE_URL = "https://datasheet.api.bg"
CATALOGUE_PATH = "?lang=en&g=roadworks&c=r03"

#: "Short-term Road Construction" - confirmed live to be a strict superset
#: of the other two roadworks categories ("Closed Roads"/r01, "Closed
#: Roadways"/r02). See module docstring.
_FILE_HREF_RE = re.compile(r'href="(/files/\d{8}_roadworks_r03\.xml)"')

#: The real feed's XML declaration claims UTF-16; the actual bytes are
#: UTF-8. See module docstring.
_MISLABELLED_ENCODING = b'encoding="UTF-16"'
_CORRECTED_ENCODING = b'encoding="UTF-8"'


class BulgariaClient:
    """Fetch Bulgaria's national roadworks ("Short-term Road Construction",
    LIMA/datasheet.api.bg). No credentials required.

    >>> from streetworks.datex2.bulgaria import BulgariaClient
    >>> from streetworks.common import from_datex2
    >>> with BulgariaClient() as bg:
    ...     situations = list(bg.iter_roadworks())
    >>> for situation in situations:
    ...     works = from_datex2(situation, territory="Bulgaria")
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
        """Resolve today's real roadworks file from the catalogue page, fetch
        it, and correct its mislabelled encoding declaration (see module
        docstring) - the raw, corrected DATEX II XML response body."""
        catalogue = self._transport.request("GET", f"{self.base_url}/{CATALOGUE_PATH}")
        match = _FILE_HREF_RE.search(catalogue.text)
        if match is None:
            raise ValueError(
                f"Bulgaria: no roadworks file link found on the catalogue page "
                f"({self.base_url}/{CATALOGUE_PATH}) - the page structure may "
                f"have changed"
            )
        file_response = self._transport.request("GET", f"{self.base_url}{match.group(1)}")
        return file_response.content.replace(_MISLABELLED_ENCODING, _CORRECTED_ENCODING, 1)

    def iter_situations(self) -> Iterator[Situation]:
        yield from _iter_situations_full(io.BytesIO(self.get_situations()), provider="Bulgaria")

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record (``Roadworks`` - see module docstring)."""
        yield from _iter_roadworks_full(io.BytesIO(self.get_situations()), provider="Bulgaria")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BulgariaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
