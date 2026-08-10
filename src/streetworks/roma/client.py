"""Roma: "Roma si trasforma" - Roma Capitale's own civic-interventions
tracker, this SDK's second Italy provider alongside the national
:mod:`streetworks.cciss` traffic bulletin, and its first Rome-municipal
source.

.. attention::
   **Confirmed live (2026-08-09)** against a real, unauthenticated pull
   (1215 real records at time of writing).

**Not the source the investigation brief named - checked live before
building, and the brief's premise didn't hold.** The brief proposed
Roma Servizi per la Mobilità's (RSM) ArcGIS Hub
(``data-rsm.opendata.arcgis.com``), reasoning RSM "explicitly tracks
cantieri" so a roadworks layer was "very likely" present. Checked
directly: RSM's real DCAT feed lists 81 real datasets - ZTL zones, bike
infrastructure, metro/tram lines, bus lanes, traffic signals, parking,
mobility managers - and not one is roadworks/cantieri-related. Roma
Capitale's own CKAN portal (``dati.comune.roma.it``) was checked next
(the brief's own named fallback) - zero results for "cantieri", "lavori",
"viabilità" or "opere" via its real search API. **The real source is a
third, different site the brief never named**: ``romasitrasforma.it``
("Roma si trasforma" - "Rome is transforming"), a Drupal-based civic-
projects portal. Found by reading its custom Drupal module's own bundled
JS (``modules/custom/roma_api_mappa/assets/main.js``) - the same
technique that found Lisboa's and Road Report NT's real backends.

**A genuinely broader scope than "roadworks" - this is Rome's general
capital-projects tracker, not a dedicated roadworks feed.** Real records
span four macro-themes (``field_tema``): Sostenibilità (sustainability -
624 real records), Inclusione (schools, housing - 285), Cultura
(restorations, museums - 239), Innovazione (digital infrastructure -
67). Street/road maintenance is one sub-tag among many, not the feed's
own subject.

**Roadworks filter: ``field_tag_temi`` contains ``"Strade e
infrastrutture"``, AND ``field_stato_lavori == "Cantiere"``** (a closed
project-lifecycle taxonomy - ``Progettazione`` → ``Gara`` → ``Cantiere``
→ ``Fine lavori`` - confirmed via the portal's own ``/api/filtri``
endpoint, not guessed). 252/1215 real records carry the
"Strade e infrastrutture" tag; of those, only 69 are currently
``Cantiere`` (in progress) rather than already finished, in design, or
out to tender. **This is the thinnest real roadworks signal of any
municipal provider this SDK has built** - 69/1215 (5.7%) of the source
feed, not a dedicated register.

**A real bug in the source, found and corrected, not reproduced.** The
``field_posizione`` object's own key names are swapped relative to true
geography: what the source calls ``"lon"`` holds latitude-range values
(~41.7-42.1, Rome's real latitude band) and what it calls ``"lat"``
holds longitude-range values (~12.2-12.8, Rome's real longitude band) -
confirmed against every real coordinate in this pull, not a one-off.
:func:`streetworks.common.from_roma` reads them swapped back to their
true meaning; see that module's own docstring.

**No date fields exist anywhere in this schema** - a first for a
municipal provider in this SDK. ``field_stato_lavori`` is a project-
lifecycle *state*, not a calendar date; there is no ``field_data_inizio``/
``field_data_fine`` or equivalent. ``date_confidence`` is always
``UNKNOWN`` and no ``proposed_start``/``proposed_end`` are populated -
never inferred from the lifecycle state, which would misrepresent a
category as a date.

**Geolocation is genuinely partial even within the filtered subset**:
35/69 real "Cantiere" + "Strade e infrastrutture" records carry a real
``field_posizione``; the other 34 have only a district-level
``field_municipio`` (Roman numeral, I-XV) and sometimes a free-text
``field_indirizzo``, no coordinate.

**Licence: genuinely unconfirmed, not carried over from any assumption.**
Checked the page text, footer, and common Italian open-data licence
terms (licenza, IODL, riutilizzo, copyright, note legali) - none found
stated anywhere on the live site.

**No app key required** - every claim above came from a fully
unauthenticated pull.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["INTERVENTI_URL", "RomaClient"]

JSON = dict[str, Any]

#: Found in "Roma si trasforma"'s own Drupal module JS
#: (roma_api_mappa/assets/main.js), not documented anywhere public.
#: Confirmed live 2026-08-09.
INTERVENTI_URL = "https://romasitrasforma.it/api/interventi"

#: Confirmed via the portal's own /api/filtri taxonomy - the real
#: sub-tag for street/road-infrastructure work, one of several under the
#: "Sostenibilità" macro-theme. See module docstring.
_ROADWORKS_TAG = "Strade e infrastrutture"

#: Confirmed via /api/filtri: the closed field_stato_lavori lifecycle -
#: only "Cantiere" means currently in progress.
_IN_PROGRESS_STATUS = "Cantiere"


def _is_roadworks(record: JSON) -> bool:
    tags = record.get("field_tag_temi") or []
    return _ROADWORKS_TAG in tags and record.get("field_stato_lavori") == _IN_PROGRESS_STATUS


class RomaClient:
    """Fetch Roma Capitale's "Roma si trasforma" interventions feed. No
    credentials required.

    >>> from streetworks.roma import RomaClient
    >>> from streetworks.common import from_roma
    >>> with RomaClient() as roma:  # doctest: +SKIP
    ...     works = from_roma(list(roma.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_interventi(self) -> Iterator[JSON]:
        """Every real intervention, unfiltered - schools, libraries,
        parks and digital infrastructure alongside real roadworks. See
        module docstring."""
        response = self._transport.request("GET", INTERVENTI_URL)
        yield from response.json() or []

    def iter_roadworks(self) -> Iterator[JSON]:
        """Real, currently in-progress street/infrastructure works only
        - see module docstring for why this is a thin (5.7%) slice of
        the full feed, not a dedicated roadworks register."""
        for record in self.iter_interventi():
            if _is_roadworks(record):
                yield record

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> RomaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
