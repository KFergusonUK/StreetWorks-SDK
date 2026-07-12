"""Shared plumbing for DATEX II snapshotPull services (SOAP POST variant).

Multiple national road authorities expose roadworks over the identical
DATEX II ``snapshotPull/2020`` WSDL interface - a SOAP ``pullSnapshotData``
operation with an empty request body. Confirmed so far: Iceland (IRCA, see
:mod:`streetworks.datex2.irca` - built against this module) and, per its own
WSDL, Norway (Statens vegvesen). This module builds and POSTs that one SOAP
envelope, returning the raw XML response body for the shared
:func:`~streetworks.datex2.parser.iter_situations` /
:func:`~streetworks.datex2.parser.iter_roadworks` to consume unchanged - the
same wrapper-agnostic reuse already proven for both providers (the parser
matches on local element names, so the SOAP envelope is transparent to it).

The ``SOAPAction`` header value is mandatory, not optional: a request
without it (or with an empty value) gets a ``500`` fault ("No operation
found for specified action") from Iceland's server - confirmed live. Its
value is read straight from the WSDL's ``soapbind:operation`` element
(``http://datex2.eu/wsdl/snapshotPull/2020/pullData``), not guessed.

:mod:`streetworks.datex2.vegvesen` (Norway) currently uses a *different*,
REST-style ``GET .../pullsnapshotdata`` path instead of this module, since
that was what a live 401 probe against Statens vegvesen's server confirmed
- not this SOAP form. If Norway's Phase 2 credentials turn out to expect
SOAP POST instead, migrate ``VegvesenClient`` onto this shared plumbing
then; duplicating the two request styles for now, rather than forcing one
provider onto an unverified transport, keeps each client honest about what
was actually confirmed against its own live service.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from .._transport import SyncTransport

__all__ = ["SOAP_ACTION", "pull_snapshot"]

#: Confirmed against Iceland's live WSDL (``GetSituation``-equivalent
#: ``SituationService?wsdl``, ``soapbind:operation soapAction=...``).
SOAP_ACTION = "http://datex2.eu/wsdl/snapshotPull/2020/pullData"

_REQUEST_BODY = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
    b'xmlns:pull="http://datex2.eu/wsdl/snapshotPull/2020">'
    b"<soapenv:Header/>"
    b"<soapenv:Body><pull:pullSnapshotData></pull:pullSnapshotData></soapenv:Body>"
    b"</soapenv:Envelope>"
)


def pull_snapshot(
    transport: SyncTransport,
    endpoint_url: str,
    *,
    header_provider: Callable[[], Mapping[str, str]] | None = None,
) -> bytes:
    """POST the empty ``pullSnapshotData`` SOAP request to ``endpoint_url``
    and return the raw XML response body."""
    headers = {"Content-Type": "text/xml; charset=UTF-8", "SOAPAction": f'"{SOAP_ACTION}"'}
    response = transport.request(
        "POST",
        endpoint_url,
        content=_REQUEST_BODY,
        headers=headers,
        header_provider=header_provider,
    )
    return response.content
