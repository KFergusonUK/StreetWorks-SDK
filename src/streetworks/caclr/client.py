"""Luxembourg - CACLR (Registre national des localités et des rues,
"national register of localities and streets"), run by ACT
(Administration du Cadastre et de la Topographie), the Grand Duchy's
official address/street reference under the law of 25 July 2002. This
SDK's first Luxembourgish streets/gazetteer coverage, a sibling to the
existing Luxembourg roadworks provider (Ponts et Chaussées,
``streetworks.datex2.luxembourg``).

**A real fixed-width legacy export, not a modern WFS/REST feed - the
government's own live geoportal WFS was checked first and ruled out.**
``ws.geoportail.lu`` (Luxembourg's national geoportal WFS/WMS host) is
real and live, but is MapServer-based with per-theme "map" identifiers
this module never found a working one for; the geocatalogue's own
search API (GeoNetwork) only returned real ``400``s on every query
shape tried. The real, live, keyless route instead is CACLR's own bulk
export on ``data.public.lu`` (Luxembourg's national open-data portal, a
udata instance, the same software family as France's data.gouv.fr).

**A real, stable "current resource" API - found and used instead of the
dataset page's own promoted (dated-snapshot) download link.** The
dataset page's UI links directly to
``download.data.public.lu/resources/.../20260817-023002/caclr.zip`` - a
real, working, but dated URL (the same no-stable-latest-alias shape
Austria's BEV and Lithuania's Registrų centras registers both have, in
their own bulk exports). udata's own REST API
(``data.public.lu/api/1/datasets/registre-national-des-localites-et-des-rues/``,
confirmed live) always reflects the *current* resource list, so this
client resolves the real ``caclr.zip`` URL from there first, then
downloads it - genuinely self-updating, unlike the workaround used for
BEV (a hardcoded snapshot date needing future maintenance).

**A real, fixed-width flat-file format inside the ZIP, confirmed field-
by-field from ACT's own published PostgreSQL import script**
(``import-caclr.sql``, bundled as a sibling resource on the same
dataset page) rather than guessed from column alignment. Three of the
13 real tables in the ZIP are used: ``RUE`` (9,946 real streets, this
resource's own subject), ``LOCALITE`` (590 real localities), and
``COMMUALL`` (132 real communes). Encoding is genuine ISO-8859-1
(Latin-1), confirmed live: 1,613/9,946 real street names contain a real
accented character (French and Luxembourgish, e.g. "Rue Siggy vu
Lëtzebuerg"), and UTF-8 decoding fails outright on this file.

**A real join trap found and worked around before shipping, not
reproduced.** ``LOCALITE.FK_COMMU_CODE`` and ``COMMUALL.CODE`` are
*not* globally unique on their own - Luxembourg's real commune codes
are only unique **within their own canton**, confirmed live: joining on
``FK_COMMU_CODE`` alone resolves a real Luxembourg-City street to
"Burmerange" (a different, real, but wrong commune roughly 30 km away).
The correct join uses the composite ``(FK_CANTO_CODE, FK_COMMU_CODE)``
key both tables actually carry - confirmed live against the same
street, correctly resolving to "Luxembourg". See
:mod:`streetworks.common.from_caclr`'s own docstring for how the
converter uses this.

**No geometry anywhere in the ``RUE`` table - a real, defining
characteristic of this specific resource, not a gap in this build.**
The same pure name-registry shape ANNCSU (Italy) and BEV (Austria)
already established. Real coordinates would need a join to a separate
address-point-level resource (the much larger ``IMMEUBLE`` table, ~14.6
MB, buildings/addresses) this build doesn't fetch.

**Real per-row lifecycle flags kept, never used to filter.**
``DATE_FIN_VALID`` (a real end-validity date, populated on 573/9,946
rows) and ``INDIC_PROVISOIRE`` (a real provisional-street flag, ``O`` on
145/9,946 rows) are both genuine, live-confirmed states this client
passes through rather than silently dropping.

**No credentials.** Licence: **Creative Commons Zero (CC0)**, confirmed
live from the dataset's own page on data.public.lu - the most
permissive licence any provider in this SDK carries, no attribution
required at all.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["DATASET_API_URL", "CaclrStreetsClient"]

JSON = dict[str, Any]

#: The real, stable udata dataset metadata API - always reflects the
#: current resource list, confirmed live. See module docstring for why
#: this is used instead of the dataset page's own dated download link.
DATASET_API_URL = (
    "https://data.public.lu/api/1/datasets/registre-national-des-localites-et-des-rues/"
)

_ZIP_RESOURCE_TITLE = "caclr.zip"

# Real fixed-width field layouts, confirmed from ACT's own published
# import-caclr.sql (1-indexed start position, length) - see module
# docstring.
_RUE_FIELDS = {
    "NUMERO": (1, 5),
    "NOM": (6, 40),
    "NOM_MAJUSCULE": (46, 40),
    "MOT_TRI": (86, 10),
    "CODE_NOMENCLATURE": (96, 5),
    "INDIC_LIEU_DIT": (102, 1),
    "DATE_FIN_VALID": (103, 10),
    "DS_TIMESTAMP_MODIF": (114, 10),
    "FK_CPTCH_TYPERUE": (124, 2),
    "FK_CPTCH_NUMERORUE": (127, 2),
    "FK_LOCAL_NUMERO": (132, 5),
    "INDIC_PROVISOIRE": (138, 1),
    "NOM_ABREGE": (139, 30),
}

_LOCALITE_FIELDS = {
    "NUMERO": (1, 5),
    "NOM": (6, 40),
    "FK_CANTO_CODE": (110, 2),
    "FK_COMMU_CODE": (113, 2),
}

_COMMUNE_FIELDS = {
    "CODE": (1, 2),
    "NOM": (3, 40),
    "FK_CANTO_CODE": (93, 2),
}


def _parse_fixed_width(line: str, fields: dict[str, tuple[int, int]]) -> dict[str, str]:
    return {
        name: line[start - 1 : start - 1 + length].strip()
        for name, (start, length) in fields.items()
    }


def _read_table(
    archive: zipfile.ZipFile, member: str, fields: dict[str, tuple[int, int]]
) -> list[dict[str, str]]:
    with archive.open(member) as raw_file:
        text = io.TextIOWrapper(raw_file, encoding="latin-1", newline="")
        return [_parse_fixed_width(line.rstrip("\r\n"), fields) for line in text if line.strip()]


class CaclrStreetsClient:
    """Fetch Luxembourg's real national street register (CACLR). No
    credentials required.

    >>> from streetworks.caclr import CaclrStreetsClient
    >>> from streetworks.common import from_caclr_street
    >>> with CaclrStreetsClient() as caclr:  # doctest: +SKIP
    ...     streets = [from_caclr_street(r) for r in caclr.iter_streets()]
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

    def _resolve_zip_url(self) -> str:
        payload = self._transport.request("GET", DATASET_API_URL).json()
        for resource in payload.get("resources", []):
            if resource.get("title") == _ZIP_RESOURCE_TITLE:
                url: str = resource["url"]
                return url
        raise LookupError(f"{_ZIP_RESOURCE_TITLE!r} not found in CACLR's real resource list")

    def iter_streets(self) -> Iterator[JSON]:
        """Every real Luxembourg street, with a real commune name joined
        in via the real ``LOCALITE``/``COMMUALL`` composite-key chain -
        never a bare, unresolved code. See module docstring."""
        zip_url = self._resolve_zip_url()
        response = self._transport.request("GET", zip_url)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            localites = {
                row["NUMERO"]: row for row in _read_table(archive, "LOCALITE", _LOCALITE_FIELDS)
            }
            communes = {
                (row["FK_CANTO_CODE"], row["CODE"]): row
                for row in _read_table(archive, "COMMUALL", _COMMUNE_FIELDS)
            }
            for row in _read_table(archive, "RUE", _RUE_FIELDS):
                locality = localites.get(row["FK_LOCAL_NUMERO"])
                commune_nom = ""
                if locality is not None:
                    commune = communes.get(
                        (locality["FK_CANTO_CODE"], locality["FK_COMMU_CODE"])
                    )
                    if commune is not None:
                        commune_nom = commune["NOM"]
                row["COMMUNE_NOM"] = commune_nom
                yield row

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> CaclrStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
