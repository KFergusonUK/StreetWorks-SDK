"""South Korea (Korea Expressway Corporation / 한국도로공사) roadworks -
"고속도로 공사현황" ("Expressway Construction Status"), credential-gated
at the data-pull layer only, published on Korea's national Public Data
Portal (data.go.kr, dataset id ``15076874``).

.. attention::
   **PENDING LIVE VERIFICATION - and less confirmed than most
   Credentials-wanted scaffolds in this SDK.** This module is built
   against the dataset's own public listing page
   (``data.go.kr/data/15076874/openapi.do``, and its own embedded
   schema.org JSON-LD metadata block) - not against a real authenticated
   pull, and **not even against a real endpoint URL**. Unlike Croatia
   (see :mod:`streetworks.datex2.croatia`), where the real pull URL is
   stated publicly, data.go.kr's own convention only reveals a dataset's
   real request URL once a service key has actually been applied for and
   approved - the public listing page states the *existence* of the
   OpenAPI service, its real field descriptions, its licence, and its
   registration process, but not the URL itself. **Field key names are
   also unconfirmed** - the dataset's own description names its real
   fields only in human-readable Korean (see below), not the actual
   JSON/XML parameter keys a real response would use - so, unlike
   Singapore (:mod:`streetworks.singapore`), **no converter
   (``from_korea``) is built yet either**; this client only gets a
   caller as far as raw response items.

**What's confirmed, from the dataset's own public listing (both the
Korean and English-mirror pages, and its embedded schema.org JSON-LD)**:

- **Real fields, named in Korean, not yet mapped to real API keys**:
  노선명 (route name), 구간명 (section name), 사업 명칭 (project name),
  공사연장 (construction extension/length), 공사기간 (construction
  period), 준공날짜 (completion date), 공사 시작·종점 주소 (construction
  start/end point address), 준공 및 시공 구분 (completion/construction
  classification), 사업단 정보 (project team/business-unit information).
- **Format**: ``JSON+XML`` (both stated as supported) - this client
  requests JSON by default.
- **Licence**: ``이용허락범위 제한 없음`` ("no restriction on scope of
  use") - confirmed identically on both the public page and the
  embedded schema.org ``license`` field. Free of charge.
- **Registration**: free self-service via data.go.kr's own "Apply for
  Use" flow (Project Service Key / Personal Service Key) - real review-
  type metadata states *"Development Stage: Auto Approval / Production
  Stage: Manual Review"*, i.e. a development-tier key is expected to be
  near-instant, production-scale traffic needs manual review. The exact
  pull URL and the caller's real ``serviceKey`` are expected to be
  issued together once approved - neither was obtained on the caller's
  behalf.
- **Contact**: Korea Expressway Corporation's AI Data Division
  (AI데이터처), ``+82-54-811-4418`` - stated on the dataset's own listing.
- **Auth query parameter**: ``serviceKey`` - not confirmed for this
  specific dataset, but this is data.go.kr's own platform-wide standard
  parameter name for every OpenAPI service on the portal (confirmed live
  against the real gateway host, ``apis.data.go.kr``, which returns a
  real structured XML error - ``NO_OPENAPI_SERVICE_ERROR`` - for a
  request bearing an unrecognised path plus ``?serviceKey=...``,
  confirming the parameter name and the gateway's own real error-response
  shape, though not this dataset's own real path).

**The standard data.go.kr response envelope is assumed, not confirmed
for this specific dataset.** Nearly every OpenAPI service on this portal
wraps its real items as ``{"response": {"header": {...}, "body":
{"items": {"item": [...]}, "numOfRows": ..., "pageNo": ...,
"totalCount": ...}}}`` (JSON) or the XML equivalent -
:meth:`KoreaClient.iter_items` reads this shape defensively (never
raises if it doesn't match, yields nothing instead) since this specific
dataset's own real response has never been seen.

**Credentials**: free self-service registration via
`data.go.kr <https://www.data.go.kr/data/15076874/openapi.do>`_'s own
"Apply for Use" button. Env vars: ``KOREA_BASE_URL``/
``KOREA_SERVICE_KEY`` (see ``.env.example``, ``scripts/smoke_test.py``).

**What's still open until a real credentialed pull**:

1. The real pull URL itself - genuinely unknown until registration, the
   same gap ASFINAG has (see :mod:`streetworks.datex2.austria`).
2. The real JSON/XML field key names behind each of the nine human-
   described fields above - needed before ``from_korea`` can be written
   at all.
3. Whether the standard data.go.kr envelope assumed above is actually
   this dataset's own real response shape.
4. Whether any coordinate/location field exists beyond the described
   "construction start/end point address" free text, and if so, its
   real format.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["KoreaClient"]

warnings.warn(
    "streetworks.korea is a Credentials-wanted scaffold: built to the "
    "dataset's own public listing on data.go.kr (see module docstring), "
    "not yet verified against a real authenticated response - genuinely "
    "less confirmed than most scaffolds in this SDK, since neither the "
    "real pull URL nor the real field key names are known yet, only the "
    "human-readable field descriptions. Have a data.go.kr service key for "
    "dataset 15076874 ('한국도로공사_고속도로 공사현황')? Running the smoke "
    "test and reporting back the real pull URL, one real trimmed record, "
    "and the real field key names would be the single most useful "
    "contribution - see the 'help wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues for exactly "
    "what's needed.",
    UserWarning,
    stacklevel=2,
)

JSON = dict[str, Any]

_PAGE_SIZE = 100


class KoreaClient:
    """Fetch Korea Expressway Corporation's real-time expressway
    construction status. **Pending live verification - see module
    docstring, especially the real pull URL being genuinely unconfirmed.**

    Requires ``base_url`` (issued at registration - there is no public
    default, see module docstring) and ``service_key``.

    >>> from streetworks.korea import KoreaClient
    >>> with KoreaClient(  # doctest: +SKIP
    ...     base_url=base_url, service_key=service_key,
    ... ) as client:
    ...     records = list(client.iter_items())
    """

    def __init__(
        self,
        *,
        base_url: str,
        service_key: str,
        response_format: str = "json",
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url:
            raise ValueError(
                "base_url is required - data.go.kr issues the real pull "
                "address once a service key is approved, see module "
                "docstring"
            )
        if not service_key:
            raise ValueError("service_key is required, see module docstring")
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key
        self.response_format = response_format
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def _fetch_page(self, page_no: int) -> JSON:
        response = self._transport.request(
            "GET",
            self.base_url,
            params={
                "serviceKey": self.service_key,
                "type": self.response_format,
                "numOfRows": _PAGE_SIZE,
                "pageNo": page_no,
            },
        )
        return response.json()

    def iter_items(self) -> Iterator[JSON]:
        """Real construction-status records - reads the standard
        data.go.kr response envelope defensively (see module docstring
        for why this is assumed, not confirmed, for this specific
        dataset). Yields nothing rather than raising if the real
        response doesn't match."""
        page_no = 1
        while True:
            payload = self._fetch_page(page_no)
            body = (payload.get("response") or {}).get("body") or {}
            items = (body.get("items") or {}).get("item")
            if items is None:
                return
            page = items if isinstance(items, list) else [items]
            yield from page
            if len(page) < _PAGE_SIZE:
                return
            page_no += 1

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> KoreaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
