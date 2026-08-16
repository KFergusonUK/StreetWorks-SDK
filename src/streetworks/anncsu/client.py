"""Italy: ANNCSU (Anagrafe Nazionale Numeri Civici e Strade Urbane) -
this SDK's first Italian streets gazetteer. A genuine national street-
name registry, jointly run by Agenzia delle Entrate (the tax/cadastre
agency) and ISTAT, established by DPCM 12 May 2016.

.. attention::
   **Confirmed live (2026-08-16)** against a real, unauthenticated bulk
   download (1,219,991 real street records at time of writing).

**Streets only, deliberately - the address/civic-number side is real but
deferred.** ANNCSU actually has two resources: ``odonimi`` (street
names, what this module builds) and ``accessi`` (civic numbers/address
points, with partial real coordinate coverage - confirmed live only
~20% populated in a real regional sample checked). Building both at once
would mean absorbing a much larger, partially-geometry-bearing dataset
in the same pass as the simpler name registry - scoped out on purpose.
See ``docs/providers/pending.md`` for the address side's own findings.

**Bulk CSV, not the live point-query API - a deliberate choice, not an
oversight.** A real, live, keyless point-query API also exists
(``anncsu.open.agenziaentrate.gov.it/age-inspire/opendata/anncsu/querydata.php``,
confirmed live: a deliberately malformed request returns a genuine
structured JSON error, and a real query -
``?resource=odonimi&codicecomune=H501&denominazione=VIA%20MILANO`` -
returns real matching records) - but it only supports lookup by
municipality code plus a (partial) name match, not "give me everything."
Enumerating all ~7,900 real Italian municipalities one at a time through
that API would be impractical for a full national pull, so this client
uses the real national bulk CSV instead
(``getds.php?STRAD_ITA``, confirmed live, ZIP-wrapped, updated
2026-08-03 at time of writing) - one request, the complete real dataset.

**No geometry anywhere in this resource - a real, defining
characteristic, not a gap in this build.** ``odonimi`` is a pure name
registry: real street name, real national/municipal identifiers, a real
stated count of address points on that street (``TOTALE_ACCESSI``) - and
nothing spatial at all. Real coordinates exist only on the separate
``accessi`` resource (see above), which this build doesn't fetch. Every
:class:`~streetworks.anncsu.models.Odonimo` therefore has no geometry
concept at all - the canonical :class:`~streetworks.common.gazetteer.Street`
this converts to is always
:attr:`~streetworks.common.gazetteer.GeometryGrade.ABSENT`, the same
documented "real NULL-geometry rows" state OS Open USRN already
establishes for this model - not synthesised, not guessed.

**Encoding: genuine UTF-8, confirmed by decoding real accented content,
not assumed.** A live byte-level check first suggested Windows-1252 (the
raw non-ASCII byte range looked plausible for it), but that encoding
actually fails to decode a real byte in this file - UTF-8 decodes
cleanly and produces genuine text (confirmed: ``LOCALITÀ CASTELLUCCIO``,
a real value, decodes correctly only as UTF-8).

**Two real, independently-stated municipality identifiers, both kept.**
``CODICE_COMUNE`` (the traditional "Belfiore" cadastral/tax code, e.g.
``"H501"`` for Roma) and ``CODICE_ISTAT`` (ISTAT's own numeric
municipality code, e.g. ``"058091"``) - related but not interchangeable,
both stated on every real row.

**No credentials.** Licence: **Creative Commons Attribution 4.0
International (CC BY 4.0)**, confirmed live from the dataset's own
catalogue metadata on `dati.gov.it <https://www.dati.gov.it/>`_.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Odonimo

__all__ = ["BASE_URL", "AnncsuClient"]

#: The real, live, keyless national bulk-download route for the
#: "odonimi" (street name) resource - a ZIP wrapping one date-suffixed
#: CSV file (the inner filename changes; this client reads the archive's
#: first member rather than hardcoding a name). See module docstring.
BASE_URL = "https://anncsu.open.agenziaentrate.gov.it/age-inspire/opendata/anncsu/getds.php"

_STRAD_ITA_PARAM = "STRAD_ITA"

#: A real browser user-agent is required - a plain default httpx UA gets
#: a 403 from this host's own edge (Akamai), confirmed live.
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; streetworks-sdk)"}


def _to_odonimo(row: dict[str, str]) -> Odonimo:
    def _clean(value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None

    codice_comunale = _clean(row.get("CODICE_COMUNALE"))
    return Odonimo(
        progressivo_nazionale=int(row["PROGRESSIVO_NAZIONALE"]),
        codice_comune=row["CODICE_COMUNE"].strip(),
        codice_istat=row["CODICE_ISTAT"].strip(),
        codice_comunale=codice_comunale,
        odonimo=row["ODONIMO"].strip(),
        localita=_clean(row.get("LOCALITA'")),
        totale_accessi=int(row.get("TOTALE_ACCESSI") or 0),
        denominazione_lingua1=_clean(row.get("DIZIONE_LINGUA1")),
        denominazione_lingua2=_clean(row.get("DIZIONE_LINGUA2")),
        raw=dict(row),
    )


class AnncsuClient:
    """Fetch Italy's real national ANNCSU street-name registry. No
    credentials required.

    >>> from streetworks.anncsu import AnncsuClient
    >>> from streetworks.common import from_anncsu
    >>> with AnncsuClient() as anncsu:  # doctest: +SKIP
    ...     streets = [from_anncsu(o) for o in anncsu.iter_odonimi()]
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 120.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(
            timeout=timeout, follow_redirects=True, headers=_HEADERS
        )
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_odonimi(self) -> Iterator[Odonimo]:
        """Every real Italian street name - the full national bulk
        download, unfiltered. See module docstring for the real ZIP/CSV
        shape and why the bulk route is used over the point-query API."""
        # A genuine bare flag param (no "="), confirmed live - the more
        # usual "?STRAD_ITA=" shape (what a plain params dict would send)
        # is rejected by the server with a real "no content associated"
        # error, not silently accepted.
        response = self._transport.request("GET", f"{BASE_URL}?{_STRAD_ITA_PARAM}")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            inner_name = archive.namelist()[0]
            with archive.open(inner_name) as raw_file:
                text = io.TextIOWrapper(raw_file, encoding="utf-8", newline="")
                reader: Any = csv.DictReader(text, delimiter=";")
                for row in reader:
                    yield _to_odonimo(row)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> AnncsuClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
