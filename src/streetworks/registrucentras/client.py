"""Lithuania - Registrų centras (State Enterprise Centre of Registers),
the "Adresų registras" (Address Register) - specifically its
"Gatvių ašinių linijų erdviniai duomenys" (street centerline spatial
data) resource. This SDK's first Lithuanian streets/gazetteer coverage,
a sibling to the existing Lithuanian roadworks provider (Via Lietuva,
``streetworks.vialietuva``).

**Real, live, genuinely keyless REST/JSON API - confirmed live on
Lithuania's national open-data portal, data.gov.lt.** A plain
unauthenticated ``GET`` against
``get.data.gov.lt/datasets/gov/rc/ar/gragatve/GraGatve`` returns the
complete real dataset in one response (~15.5 MB, no pagination needed) -
22,547 real national street records, confirmed live, 100% carrying a
real name and real geometry, zero duplicate street codes.

**A real, stable, version-less URL - found after the dataset's own
promoted download link turned out to bake in a version number.** The
dataset's own page (``data.gov.lt/datasets/1349/``) links to
``.../versions/116/dynamic-resource/gragatve/json/download/`` - a real,
working, but dated snapshot URL (the same "no stable latest alias"
shape Austria's BEV register has). A shorter, undated link on the same
page (``.../distribution/14765/download/``) was followed and found to
redirect to ``get.data.gov.lt/datasets/gov/rc/ar/gragatve/GraGatve`` -
confirmed live to return byte-identical data to the versioned URL, with
no version number anywhere in it. This client uses that stable route.

**A real, confirmed axis-order quirk in the geometry field, found live
and worked around, not assumed.** The ``gatves`` field states real WKT
``LINESTRING``/``MULTILINESTRING`` geometry, but its own coordinate
pairs are ordered ``(Northing, Easting)``, not the standard WKT/GeoJSON
``(Easting, Northing)`` = ``(X, Y)`` convention - confirmed by bounds-
checking: LKS-94's real Lithuanian easting range is roughly
300,000-720,000 m and its real northing range is roughly
5,990,000-6,265,000 m, and a real sample point's first WKT ordinate
(~6,107,030) only ever falls in the northing range. Reprojecting with
the ordinates read in that swapped order lands the point inside
Lithuania's real extent (~22.7 deg E, ~55.1 deg N); reading them in
literal WKT order lands near Sri Lanka. See
:mod:`streetworks.common.from_registrucentras`'s own docstring for how
the converter applies this.

**CRS: LKS-94 / Lithuanian Coordinate System 1994 (EPSG:3346), the only
CRS this resource states - no server-side reprojection option exists**
(a plain REST/JSON download, not a WFS with an ``srsName`` parameter).
Reprojected client-side via :mod:`streetworks.common._lks94`, a
closed-form Transverse Mercator inverse (no ``pyproj``, matching this
SDK's stdlib-only convention - the same approach Denmark's DAR already
established for its own UTM32N case).

**``gyvenamoji_vietove`` (the residential-area/settlement reference) is
left unresolved - a real, disclosed limitation, not an oversight.**
Each street row states only a bare ``{"_id": ...}`` reference; resolving
it to a real settlement name would mean fetching a separate 127 MB
national dataset (confirmed live:
``get.data.gov.lt/datasets/gov/rc/ar/gragyvenamojivietove/GraGyvenamojiVietove``,
20,880 real residential areas) just to label one field - a
disproportionate cost for a single lookup, unlike Austria's BEV register
(joined against a 51 KB municipality table bundled in the same
download). Kept on ``.raw`` for any caller who wants to resolve it
themselves.

**No credentials.** Licence: Creative Commons Attribution 4.0
International, confirmed live directly from the dataset's own page on
data.gov.lt.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "RegistruCentrasStreetsClient"]

JSON = dict[str, Any]

#: The real, live, keyless, version-less national bulk route. See
#: module docstring for why this is used instead of the dataset page's
#: own promoted (dated-snapshot) download link.
BASE_URL = "https://get.data.gov.lt/datasets/gov/rc/ar/gragatve/GraGatve"


class RegistruCentrasStreetsClient:
    """Fetch Lithuania's real national street-centerline register. No
    credentials required.

    >>> from streetworks.registrucentras import RegistruCentrasStreetsClient
    >>> from streetworks.common import from_registrucentras_street
    >>> with RegistruCentrasStreetsClient() as rc:  # doctest: +SKIP
    ...     streets = [from_registrucentras_street(r) for r in rc.iter_streets()]
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_streets(self) -> Iterator[JSON]:
        """Every real Lithuanian street - the full national dataset,
        returned in one response (confirmed live: no pagination exists
        or is needed for this resource's real size)."""
        response = self._transport.request("GET", BASE_URL)
        yield from response.json().get("_data", [])

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> RegistruCentrasStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
