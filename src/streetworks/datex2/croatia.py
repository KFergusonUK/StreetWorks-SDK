"""Croatia (Hrvatske ceste / NPT - Nacionalna pristupna točka) roadworks -
genuine DATEX II v3, credential-gated at the data-pull layer only.

.. attention::
   **PENDING LIVE VERIFICATION.** This module is built against Croatia's
   own National Access Point (NPT, a Realis ITS NAP platform deployment
   at ``promet-info.hr``) - its public dataset-metadata pages, not a
   secondhand description - and a real, live, unauthenticated request
   confirming the auth mechanism and endpoint shape (a plain ``GET`` on
   the real, publicly-documented pull URL returns a genuine ``401``, not
   a ``404``). No real authenticated response has been seen.
   **Better-confirmed than Vejdirektoratet at the same stage**: Croatia's
   own NAP states the real pull URL directly in its public metadata
   (Vejdirektoratet's own protocol doc only says the URL is "configured
   at registration," never published) - the URL itself needed no
   registration to discover, only the credential to use it does.

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
issues login credentials (the real form doesn't state up front whether
that's a Basic Auth username/password pair, a Bearer token, or both -
see the auth note above). Env vars:
``CROATIA_USERNAME``/``CROATIA_PASSWORD`` or ``CROATIA_BEARER_TOKEN``
(see ``.env.example``, ``scripts/smoke_test.py``).

**What's still open until a real credentialed pull**:

1. Which of Basic/Bearer auth this specific dataset actually accepts (the
   NAP states both are real mechanisms on the platform, not necessarily
   both for this one dataset).
2. Whether the real DATEX II v3 response is a bare
   ``SituationPublication`` this SDK's own shared streaming parser
   handles unchanged, or a Croatia-specific profile with fields the
   parser doesn't expect.
3. Real roadworks-record-type coverage - whether
   ``ConstructionWorks``/``MaintenanceWorks`` appear as the dedicated
   xsi:type, or via the same kind of generic-record discriminator gap
   Belgium's/Spain's own real feeds needed (see
   :mod:`streetworks.datex2.belgium`/:mod:`streetworks.datex2.dgt`).
"""

from __future__ import annotations

import io
import warnings
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Situation
from .parser import iter_roadworks as _iter_roadworks
from .parser import iter_situations as _iter_situations

__all__ = ["BASE_URL", "LEGACY_BASE_URL", "CroatiaClient"]

warnings.warn(
    "streetworks.datex2.croatia is a Credentials-wanted scaffold: built to "
    "Croatia's own National Access Point metadata (see module docstring), "
    "not yet verified against a real authenticated response. Have "
    "promet-info.hr registration credentials for the 'HC Radovi DatexII "
    "v3' dataset? Running the smoke test and reporting back one real "
    "trimmed record, and which auth scheme (Basic or Bearer) actually "
    "worked, would be the single most useful contribution - see the "
    "'help wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues for exactly "
    "what's needed.",
    UserWarning,
    stacklevel=2,
)

#: HC Radovi DatexII v3 - confirmed live (a real 401 on an unauthenticated
#: request). See module docstring.
BASE_URL = "https://b2b.promet-info.hr/dc/b2b.hc.roadworks.datex3"

#: The sibling legacy (non-v3) dataset, same NAP, published since
#: 22.05.2023 - see module docstring. Not fetched by default.
LEGACY_BASE_URL = "https://b2b.promet-info.hr/dc/b2b.hc.roadworks.datex"


class CroatiaClient:
    """Fetch Croatian state-road roadworks from Hrvatske ceste's real
    NAP dataset. **Pending live verification - see module docstring.**

    Requires either ``username``/``password`` (HTTP Basic) or
    ``bearer_token`` - which one this dataset actually accepts is
    unconfirmed, see module docstring.

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
