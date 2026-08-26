"""Croatia (Hrvatske ceste / NPT - Nacionalna pristupna točka) roadworks -
genuine DATEX II v3, credential-gated at the data-pull layer only.

.. attention::
   **CONFIRMED LIVE (2026-08-26).** Verified against a real authenticated
   pull with real HTTP Basic credentials: 85 real situations, all real
   ``MaintenanceWorks`` records (no ``ConstructionWorks`` seen in this
   pull - a real snapshot property, not a schema limitation; the legacy
   dataset's own metadata still names both as real possibilities). The
   shared streaming parser handles the real response with **zero code
   changes** - a bare ``<SituationPublication>`` root, exactly as
   assumed, resolving the "bare vs. profile-wrapped" open question below.
   **Auth resolved: HTTP Basic (``username``/``password``) is confirmed
   correct** - real registration issued a plain username/password pair,
   not a bearer token; ``bearer_token`` support is kept (the NAP's own
   metadata still states it as a real platform-wide mechanism) but is
   now unconfirmed-for-this-account rather than unconfirmed-for-this-
   dataset. Real coordinates are genuine WGS84 - both a
   ``coordinatesForDisplay`` point and a full ``gmlLineString`` with
   explicit ``srsName="EPSG:4326"`` are present on every real record
   checked; the shared parser reads the LineString's first point. Real
   ``generalPublicComment`` text is genuinely bilingual (``hr``/``en``
   ``values``) on some but not all comments - only Croatian was seen
   guaranteed present, English only sometimes.

**Two real, sibling datasets found on the NAP, not one** - "HC Radovi
DatexII" (legacy, published since 22.05.2023,
``https://b2b.promet-info.hr/dc/b2b.hc.roadworks.datex``) and "HC Radovi
DatexII v3" (published since 11.03.2024,
``https://b2b.promet-info.hr/dc/b2b.hc.roadworks.datex3``) - this module
targets the v3 endpoint, the same "prefer the newer schema version when
both exist" choice this SDK already makes for D-TRO. Both are confirmed
live to return a real ``401`` for an unauthenticated request.

**Auth: the NAP's own metadata states both Basic and Bearer authentication
as real, documented security mechanisms** (``osnovna autentifikacija,
bearer autentifikacija``) for this exact dataset - which one is actually
required (or whether either works) is not stated beyond that, and hasn't
been exercised against a real credentialed pull. This client accepts
either shape - ``username``/``password`` (HTTP Basic) or a
``bearer_token`` - and lets the caller's real registration outcome decide
which one to use.

**Real, live self-service registration confirmed** - unlike Vejdirektoratet
(registration portal reached but not walked through) or ASFINAG (auth
mechanism unknown), this NAP's own real registration form
(``promet-info.hr/hr/registration``) was found and inspected live: email,
name, organisation, address, phone, language, password - a plain
self-service sign-up form, no visible approval/contract gate before
submission (though what happens after submitting - immediate access vs.
a manual approval step - is itself unconfirmed, since no real submission
was made on the caller's behalf).

**Format**: genuine DATEX II, UTF-8 XML, XSD grammar, "DATEX II Profile"
data model, real georeferencing method stated as **WGS84** geocoordinates
(no reprojection needed, unlike Belgium's own Lambert 72 finding) -
confirmed from the NAP's own public dataset-metadata page, not assumed.
Real update frequency stated: **up to 1 minute**.

**Licence: Croatia's own national "Otvorena dozvola" (Open Licence)** -
confirmed by fetching and reading the real PDF
(``promet-info.hr/_resources/doc/Otvorena%20dozvola.pdf``), not just the
NAP's own summary label. Explicitly permits commercial and
non-commercial use, reproduction, distribution, adaptation, and
integration into products - the same permissiveness tier as CC BY/OGL,
with the same shape of requirement: cite the real source (name + last-
modified date, or a stated fallback attribution sentence when the source
gives none) and the dataset's own URI, and mark any modifications as
such. No comparable restriction to ASFINAG's own supplementary
downstream-disclosure clause was found.

**Credentials**: free self-service registration at
`promet-info.hr/hr/registration <https://www.promet-info.hr/hr/registration>`_
issues login credentials - confirmed to be a Basic Auth username/password
pair for this account (see the auth note above). Env vars:
``CROATIA_USERNAME``/``CROATIA_PASSWORD`` or ``CROATIA_BEARER_TOKEN``
(see ``.env.example``, ``scripts/smoke_test.py``).

**What's still open**: whether Bearer auth also works for this dataset
(only Basic has been exercised); real record-type coverage beyond
``MaintenanceWorks`` - no ``ConstructionWorks`` has been seen live yet,
though the NAP's own metadata still names it as real.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Situation
from .parser import iter_roadworks as _iter_roadworks
from .parser import iter_situations as _iter_situations

__all__ = ["BASE_URL", "LEGACY_BASE_URL", "CroatiaClient"]

#: HC Radovi DatexII v3 - confirmed live (2026-08-26, real authenticated
#: pull, 85 real situations). See module docstring.
BASE_URL = "https://b2b.promet-info.hr/dc/b2b.hc.roadworks.datex3"

#: The sibling legacy (non-v3) dataset, same NAP, published since
#: 22.05.2023 - see module docstring. Not fetched by default.
LEGACY_BASE_URL = "https://b2b.promet-info.hr/dc/b2b.hc.roadworks.datex"


class CroatiaClient:
    """Fetch Croatian state-road roadworks from Hrvatske ceste's real
    NAP dataset. **Confirmed live (2026-08-26) - see module docstring.**

    Requires either ``username``/``password`` (HTTP Basic, confirmed
    correct) or ``bearer_token`` (real platform-wide mechanism, unconfirmed
    for this account) - see module docstring.

    >>> from streetworks.datex2.croatia import CroatiaClient
    >>> from streetworks.common import from_datex2
    >>> with CroatiaClient(  # doctest: +SKIP
    ...     username=username, password=password,
    ... ) as croatia:
    ...     for situation in croatia.iter_roadworks():
    ...         works = from_datex2(situation, territory="Croatia")
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        username: str | None = None,
        password: str | None = None,
        bearer_token: str | None = None,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        if bearer_token and (username or password):
            raise ValueError(
                "pass either username+password (Basic) or bearer_token "
                "(Bearer), not both - see module docstring"
            )
        if not bearer_token and not (username and password):
            raise ValueError(
                "credentials required - username+password or bearer_token, "
                "see module docstring"
            )
        self.base_url = base_url.rstrip("/")
        if client is None:
            if bearer_token:
                client = httpx.Client(
                    timeout=timeout,
                    follow_redirects=True,
                    headers={"Authorization": f"Bearer {bearer_token}"},
                )
            else:
                assert username is not None and password is not None
                client = httpx.Client(
                    timeout=timeout,
                    follow_redirects=True,
                    auth=httpx.BasicAuth(username, password),
                )
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_situations(self) -> bytes:
        """``GET`` the configured endpoint - the raw DATEX II XML response
        body."""
        response = self._transport.request("GET", self.base_url)
        return response.content

    def iter_situations(self) -> Iterator[Situation]:
        yield from _iter_situations(io.BytesIO(self.get_situations()), provider="Croatia")

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record (``MaintenanceWorks``/``ConstructionWorks``)."""
        yield from _iter_roadworks(io.BytesIO(self.get_situations()), provider="Croatia")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> CroatiaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
