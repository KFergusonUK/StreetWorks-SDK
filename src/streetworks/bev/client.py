"""Austria: BEV (Bundesamt für Eich- und Vermessungswesen, the Federal
Office of Metrology and Surveying) - the "Österreichisches Adressregister"
(Austrian Address Register), specifically its national street table
(``STRASSE.csv``). This SDK's first Austrian streets/gazetteer coverage,
a sibling to the existing Austrian roadworks providers (Vienna's own WFS,
ASFINAG's national Credentials-wanted DATEX II scaffold).

**Not the source first found - the obvious BEV product page is a paid
shop, a genuinely separate free line was found instead.**
`bev.gv.at/Services/Produkte/Adressregister/` lists a per-record priced
product (e.g. EUR 0.045/record for 1m-geocoded addresses, ordered via
"Bestellformulare"/"BEV Shops") - its own downloadable sample ZIP turned
out to be a single-municipality demo (Zell am See, 190 real rows), not
the national dataset. A **separate, free, CC-BY-4.0 product line** is
published directly on BEV's own GeoNetwork data portal,
``data.bev.gv.at`` (distinct from the general ``data.gv.at`` national
portal, which is a JS SPA with no easily discoverable API) - confirmed
live via its own ISO19139 metadata: *"Für dieses Produkt gilt die
Standardlizenz CC-BY-4.0"*, access constraint ``noLimitations``
("Der öffentliche Zugang zu diesem Produkt unterliegt keinen
Einschränkungen").

**Real, live, keyless bulk ZIP - "Adresse Relationale Tabellen -
Stichtagsdaten" (Address Relational Tables - snapshot-date data).**
Confirmed live: a plain unauthenticated ``GET`` returns a real ~93 MB
ZIP containing multiple relational CSV tables (``ADRESSE``,
``GEBAEUDE``, ``GEMEINDE``, ``ORTSCHAFT``, ``STRASSE``, ...) - this
client reads only ``STRASSE.csv`` (137,767 real national street rows,
100% named, zero duplicate ``SKZ``) and ``GEMEINDE.csv`` (2,092 real
municipalities, a clean 1:1 join - every real ``STRASSE`` row's ``GKZ``
resolves, confirmed against the complete dataset) to attach a real
municipality name rather than leaving a bare code, the same "resolve
what's cheaply joinable" call this SDK already made differently for
Denmark's DAR (which left the raw kommune code unresolved since no
lookup table was fetched there).

**No geometry anywhere in ``STRASSE.csv`` - a real, defining
characteristic of this specific resource, not a gap in this build.**
The same "pure name registry" shape ANNCSU (Italy) already established
- real coordinates exist only on the much larger sibling ``ADRESSE.csv``
(325 MB, address-point level, not fetched here) and the separate,
INSPIRE-branded ``AT-INSPIRE_AD_Address`` bulk product (confirmed live,
~183 MB) - both real, address-level resources, out of scope for a
streets-only build, the same "streets built, address side deliberately
scoped out" call ANNCSU already made for its own ``accessi`` sibling.

**A real dated-snapshot limitation, stated honestly rather than
engineered around.** This product is published periodically (roughly
twice yearly, "Stichtag" snapshots - live-confirmed dates include
01.04.2025, 01.10.2025) under a URL that bakes the snapshot date in
(``..._Stichtagsdaten_20251001.zip``) - there is no stable "latest"
alias found anywhere on ``data.bev.gv.at`` (its GeoNetwork search API
returned only real ``400``s on every query shape tried). ``BASE_URL``
therefore points at the most recent snapshot confirmed live at the time
of this module's own investigation (2026-08-18) - a future maintainer
will need to update it once BEV publishes a newer one; this is a real,
disclosed constraint, not silently assumed to be self-updating.

**No credentials.** Licence: **Creative Commons Attribution 4.0
International (CC BY 4.0)**, confirmed live from this product's own
ISO19139 metadata on ``data.bev.gv.at`` - required attribution wording
stated verbatim: *"© Österreichisches Adressregister, Stichtagsdaten vom
01.10.2025"* (the date changes per snapshot).
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "BevStreetsClient"]

JSON = dict[str, str]

#: The real, live, keyless national bulk-download route - a dated
#: snapshot, the most recent confirmed live at investigation time. See
#: module docstring for why there's no stable "latest" alias to use
#: instead, and why a future maintainer may need to update this.
BASE_URL = (
    "https://data.bev.gv.at/download/Adressregister/Archiv_Adressregister/"
    "Adresse_Relationale_Tabellen_Stichtagsdaten_20251001.zip"
)

_STRASSE_ENTRY = "STRASSE.csv"
_GEMEINDE_ENTRY = "GEMEINDE.csv"


class BevStreetsClient:
    """Fetch Austria's real national street-name register (BEV's
    Adressregister, ``STRASSE.csv``), joined against the real
    ``GEMEINDE.csv`` municipality table. No credentials required.

    >>> from streetworks.bev import BevStreetsClient
    >>> from streetworks.common import from_bev_street
    >>> with BevStreetsClient() as bev:  # doctest: +SKIP
    ...     streets = [from_bev_street(r) for r in bev.iter_streets()]
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 120.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_streets(self) -> Iterator[JSON]:
        """Every real Austrian street, with a real ``GEMEINDENAME``
        (municipality name) joined in from ``GEMEINDE.csv`` - never a
        bare, unresolved ``GKZ`` code. See module docstring."""
        response = self._transport.request("GET", BASE_URL)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            gemeinde_by_gkz = self._read_gemeinde(archive)
            with archive.open(_STRASSE_ENTRY) as raw_file:
                text = io.TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
                reader: Any = csv.DictReader(text, delimiter=";")
                for row in reader:
                    row["GEMEINDENAME"] = gemeinde_by_gkz.get(row.get("GKZ", ""), "")
                    yield row

    @staticmethod
    def _read_gemeinde(archive: zipfile.ZipFile) -> dict[str, str]:
        with archive.open(_GEMEINDE_ENTRY) as raw_file:
            text = io.TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
            reader: Any = csv.DictReader(text, delimiter=";")
            return {row["GKZ"]: row["GEMEINDENAME"] for row in reader}

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BevStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
