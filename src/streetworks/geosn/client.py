"""Germany (Saxony/Sachsen) - GeoSN's (Staatsbetrieb Geobasisinformation
und Vermessung Sachsen) statewide "Hauskoordinaten" (house coordinates)
bulk export. This SDK's third German state-level streets/gazetteer
provider, completing the "state fan-out" fallback path Germany's
national streets investigation named (Hamburg, Brandenburg, Saxony,
Berlin) - see `docs/germany-streets-investigation.md`.

**Not the shared Deutschland-Online-Gazetteer (DOG) WFS Hamburg and
Brandenburg both use - checked and confirmed Saxony genuinely doesn't
participate in it.** The DOG service's own real member states are
Brandenburg and Berlin only (confirmed live via
`isk.geobasis-bb.de/ows/gazetteer_wfs`'s own abstract); Saxony's own
ALKIS WFS (`geodienste.sachsen.de/aaa/public_alkis/vereinf/wfs`,
confirmed live) publishes only cadastral parcels, buildings, land use
and administrative boundaries - no street or address feature type at
all. Saxony instead publishes its own address-point data as a real
statewide bulk CSV/text export, found via its own open-geodata portal
page (`geodaten.sachsen.de/downloadbereich-hauskoordinaten-4172.html`).

**Real, live, keyless bulk download - a genuinely large real file
(~206 MB uncompressed, ~51 MB zipped), the largest single download this
SDK's German-state cluster has needed.** 990,090 real address-point
rows, confirmed live, 100% carrying a real street name (`str`). This is
address-point data, not a dedicated street register - one row per real
address, not per street - so :mod:`streetworks.common.from_geosn`
deduplicates by `(gmdschl, strschl)` (municipality code + street code),
keeping the first real row's own coordinate as a representative point
for the whole street - the same "one real, arbitrarily-chosen-but-
genuinely-stated point stands for the whole entity" discipline
`from_oslo`/`from_canton_zurich`/`from_brandenburg_street` already
apply to their own polygon-first-vertex case, applied here to a
real address point instead of a ring vertex. 42,824 real distinct
(municipality, street) combinations, confirmed live.

**CRS: real ETRS89 / UTM zone 33N (`EPSG:25833`), confirmed live -
zone 33, not 32 (unlike Denmark's DAR).** The file's own `zone` column
reads `33` on every row checked; reprojected client-side via
:mod:`streetworks.common._utm33n`, a closed-form Transverse Mercator
inverse (no `pyproj`), cross-checked against a real address in
Dolsenhain (Frohburg, near Leipzig) before shipping - the axis order is
the standard `(Easting, Northing)`, confirmed by the same bounds check,
unlike Lithuania's own UTM-family source, which needed a swap.

**No credentials.** Licence: **Datenlizenz Deutschland - Namensnennung -
2.0**, confirmed live from GeoSN's own open-geodata FAQ page
(`geodaten.sachsen.de`) - explicitly stated to permit commercial reuse.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "GeoSNStreetsClient"]

JSON = dict[str, Any]

#: The real, live, keyless statewide bulk-download route - see module
#: docstring.
BASE_URL = (
    "https://geocloud.landesvermessung.sachsen.de/public.php/dav/files/"
    "B3HnXbDDgAkw69a/hk_sn_ascii.zip"
)


class GeoSNStreetsClient:
    """Fetch Saxony's real statewide address export (Hauskoordinaten).
    No credentials required.

    >>> from streetworks.geosn import GeoSNStreetsClient
    >>> from streetworks.common import from_geosn_street
    >>> with GeoSNStreetsClient() as geosn:  # doctest: +SKIP
    ...     streets = [from_geosn_street(r) for r in geosn.iter_streets()]
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
        """Every real Saxony address row, deduplicated to one per real
        `(gmdschl, strschl)` street - not the full 990,090-row address
        table. See module docstring."""
        response = self._transport.request("GET", BASE_URL)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            inner_name = archive.namelist()[0]
            with archive.open(inner_name) as raw_file:
                text = io.TextIOWrapper(raw_file, encoding="utf-8", newline="")
                reader: Any = csv.DictReader(text, delimiter=";")
                seen: set[tuple[str, str]] = set()
                for row in reader:
                    key = (row.get("gmdschl", ""), row.get("strschl", ""))
                    if key in seen:
                        continue
                    seen.add(key)
                    yield row

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> GeoSNStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
