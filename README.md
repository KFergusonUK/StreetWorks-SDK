# streetworks

[![CI](https://github.com/KFergusonUK/StreetWorks-SDK/actions/workflows/ci.yml/badge.svg)](https://github.com/KFergusonUK/StreetWorks-SDK/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/streetworks)](https://pypi.org/project/streetworks/)
[![Python](https://img.shields.io/pypi/pyversions/streetworks)](https://pypi.org/project/streetworks/)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)

An open Python SDK for UK street works APIs — one consistent, typed,
well-tested client for the services the sector actually uses.

> We do this not because it is easy, but because it is hard.

```python
from streetworks.streetmanager import StreetManagerClient, Environment

with StreetManagerClient("api-user@example.com", password, environment=Environment.SANDBOX) as sm:
    sm.authenticate()                                  # verify credentials
    submitted = sm.reporting.permits(status="submitted")
```

| Module | Service | Direction |
|---|---|---|
| `streetworks.streetmanager` | [DfT Street Manager](https://department-for-transport-streetmanager.github.io/street-manager-docs/api-documentation/) — all nine APIs (Work, Reporting, Street Lookup, GeoJSON, Party, Data Export, Event, Sampling, Worklist), V6 & V7, sandbox & production | read + write |
| `streetworks.opendata` | [Street Manager Open Data](https://department-for-transport-streetmanager.github.io/street-manager-docs/open-data/) — AWS SNS push notifications | receive |
| `streetworks.datavia` | [Geoplace DataVIA](https://datavia.geoplace.co.uk/documentation) — full NSG layer catalogue over OGC WFS (Basic + OAuth2) | read |
| `streetworks.dtro` | [DfT Digital Traffic Regulation Orders](https://d-tro.dft.gov.uk/api-documentation/) — integration & production | read + write |

Shared across all modules: automatic retries with exponential backoff and
jitter, `Retry-After`-aware 429 handling, a single exception hierarchy, and
both **sync and async** clients built on [httpx](https://www.python-httpx.org/).

## What this is (and isn't)

**It is** a typed client library: it handles authentication, token lifecycles,
retries, rate limiting, pagination, and request/response plumbing for each of
these APIs, so you call Python methods instead of hand-rolling HTTP. Auth and
connectivity are verified against the real systems (see **Status** below).

**It isn't** a replacement for the APIs' own documentation. You still bring
your own credentials (issued by the service operators, not by this SDK) and
you still need each API's domain concepts — what a permit payload contains,
what makes a valid USRN filter, which DataVIA layer holds which data. The SDK
gets you connected and typed; the linked docs tell you what to send.

## Status

Early alpha (`0.1.0`). Street Manager authentication and connectivity are
**verified working against SANDBOX** with a real account. The DataVIA and
D-TRO clients are built to the published documentation and pass a full mocked
test suite, but some endpoint details are awaiting first confirmation against a
live account — see the "Values to confirm" list in
[docs/INTEGRATION.md](docs/INTEGRATION.md). The `streetworks.exceptions` API
and the client method surface may change before `1.0`. Feedback and
first-contact reports very welcome.

## Install

```bash
pip install streetworks            # core
pip install "streetworks[sns]"     # + SNS signature verification (cryptography)
```

Requires Python 3.10+.

## Prerequisites: credentials

Credentials are issued by the service operators. You only need the ones for the
service(s) you'll use. Keep them in environment variables or a secret manager —
never in code.

| Service | How to get access | Environment variables |
|---|---|---|
| Street Manager | Your organisation's Street Manager admin issues API accounts; [start in sandbox](https://department-for-transport-streetmanager.github.io/street-manager-docs/articles/testing-with-street-manager-sandbox-environment.html) | `SM_EMAIL`, `SM_PASSWORD` |
| Street Manager Open Data | Register an HTTPS endpoint with DfT to receive the SNS subscription | *(none — you host the receiver)* |
| DataVIA | A [Geoplace DataVIA](https://datavia.geoplace.co.uk/) account (username/password) or issued OAuth2 client credentials | `DATAVIA_USER` + `DATAVIA_PASSWORD`, or `DATAVIA_CLIENT_ID` + `DATAVIA_CLIENT_SECRET` |
| D-TRO | Register an application via the [D-TRO service](https://d-tro.dft.gov.uk/) for an app id and OAuth2 client credentials (integration first, then production) | `DTRO_CLIENT_ID`, `DTRO_CLIENT_SECRET`, `DTRO_APP_ID` |

Credentials are **per-environment** — sandbox/integration credentials do not
work against production, and vice versa.

## Verify your setup

Before writing any code, confirm your credentials and connectivity with the
included smoke test. It targets the **test** environments by default, is
read-only, and skips any service you haven't configured:

```bash
SM_EMAIL='api-user@example.com' SM_PASSWORD='...' python scripts/smoke_test.py
```

```
================================================================
streetworks connectivity smoke test
TARGET  Street Manager: sandbox
All checks are READ-ONLY.
================================================================

  [PASS] Street Manager - authenticated (sandbox/v6), organisation 1355
  ...
```

A `FAIL` prints the exact exception, so a wrong credential or environment is
obvious immediately. See [docs/INTEGRATION.md](docs/INTEGRATION.md) for the
full variable list and how to (deliberately) target production.

## Street Manager

Authentication, token caching, and refresh (via the Party API, with automatic
fall-back to re-authentication) are handled for you — following the DfT
integration guidance: one token, reused, never re-authenticating per call.

```python
from streetworks.streetmanager import StreetManagerClient, Environment, ApiVersion

with StreetManagerClient(
    "api-user@example.com",
    "password",                      # store securely, e.g. environment variable
    environment=Environment.SANDBOX, # or Environment.PRODUCTION
    version=ApiVersion.V6,           # or ApiVersion.V7 / ApiVersion.LATEST
) as sm:
    # Typed convenience methods for common workflows...
    work = sm.work.get_work("TSR1591199404915")
    submitted = sm.reporting.permits(status="submitted")
    sm.work.assess_permit("TSR1591199404915", "TSR1591199404915-01",
                          {"assessment_status": "granted", ...})

    # ...and a generic escape hatch for every endpoint we haven't wrapped yet:
    s58 = sm.work.post("section-58s", json={...})
    updates = sm.event.works_updates()
```

Async is a mirror image:

```python
from streetworks.streetmanager import AsyncStreetManagerClient

async with AsyncStreetManagerClient("api-user@example.com", "password") as sm:
    permits = await sm.reporting.permits(status="submitted")
```

> **Environments.** `Environment.SANDBOX` and `Environment.PRODUCTION` are
> isolated systems with separate credentials. Develop and test against
> SANDBOX; only point at PRODUCTION once your workflows are proven. The smoke
> test and integration suite refuse to touch production without an explicit
> opt-in, so a stray setting can't send you at live data by accident.

### Typed models

Pydantic v2 models generated from the official DfT swagger specifications
live under `streetworks.streetmanager.models.<version>` and validate any
client payload:

```python
from streetworks.streetmanager.models.v6.work import WorkResponse

work = WorkResponse.model_validate(sm.work.get_work("TSR1591199404915"))
```

To regenerate after a DfT release, run the **Regenerate Street Manager
models** workflow from the Actions tab (it opens a PR), or locally:

```bash
pip install -e ".[gen]"
python scripts/generate_models.py --version v6 --from-dir specs/streetmanager/v6
```

## Street Manager Open Data (SNS push)

Open Data is a *push* model: Street Manager POSTs event notifications to an
HTTPS endpoint you host. `streetworks.opendata` handles envelope parsing,
signature verification, subscription auto-confirmation, and payload
extraction — framework-agnostic:

```python
from streetworks.opendata import handle

# inside your web handler, with the raw request body:
event = handle(request_body, expected_topic_arn="arn:aws:sns:eu-west-2:...:...")
if event is not None:               # None => subscription handshake, auto-confirmed
    print(event["event_type"], event["object_reference"])
```

See [`examples/opendata_fastapi.py`](examples/opendata_fastapi.py) for a
complete FastAPI receiver.

## Geoplace DataVIA

Basic auth or OAuth2 client credentials (server-to-server), the full NSG layer
catalogue (`Layer.STREET_LINES`, `ESU_STREETS`, `ESU_ONE_WAY_EXEMPTIONS`, and
the Interest / Construction / Special Designation layers in all three geometry
flavours), composable OGC filters, and transparent paging:

```python
from streetworks.datavia import DataViaClient, Layer, filters

with DataViaClient(username="user", password="pass") as dv:      # or client_id=/client_secret=
    street = dv.street_by_usrn(4401245)
    nearby = dv.streets_near_point(-0.138405, 50.825181, 100)    # within 100m

    sed = dv.get_features(
        Layer.SPECIAL_DESIGNATION_LINES,
        filter_fragment=filters.and_(
            filters.intersects_polygon(ring),
            filters.property_equals("special_designation_code", 3),
        ),
    )

    for feature in dv.iter_features(Layer.ESU_STREETS, page_size=500):
        ...
```

POST `GetFeature` bodies match the shapes in the DataVIA documentation
(WFS 1.1.0 + `ogc:Filter`); GET KVP with `startIndex`/`count` is also
available via `get_features_kvp()`. Output formats: GeoJSON (default),
OGRGML, SHAPEZIP, CSV, SPATIALITEZIP.

## DfT D-TRO

OAuth2 client credentials (30-minute tokens, cached and renewed
automatically), `x-app-id` and per-request `X-Correlation-ID` headers handled
for you:

```python
from streetworks.dtro import DTROClient, Environment

with DTROClient(client_id, client_secret, app_id=app_id,
                environment=Environment.INTEGRATION) as dtro:
    events = dtro.search_events(since="2026-06-01T00:00:00", pageSize=50)
    record = dtro.get_dtro(events["events"][0]["id"])

    dtro.create_dtro(payload)                          # publisher scope
    dtro.create_dtro_from_file(big_json, gzip=True)    # large D-TROs
    signed = dtro.get_all_dtros_url()                  # full CSV extract
```

## Design principles

1. **Never block the user.** Typed methods for confirmed, common endpoints;
   generic `get/post/put/delete` on every API group for everything else.
2. **Be a good API citizen.** Token reuse, refresh-then-reauth, exponential
   backoff, honoured `Retry-After` — per the DfT integration guidance.
3. **Test without credentials, verify with them.** The whole unit suite runs
   against mocked transports (`respx`) so CI needs no secrets; a separate
   smoke test and skip-guarded integration suite verify against the real
   systems when you supply credentials.
4. **Room to grow.** Each provider is a self-contained module over a shared
   transport/exception core — adding a new API is additive.

## Roadmap

- [x] Pydantic model generation pipeline for the Street Manager swagger specs
- [ ] Auto-pagination helpers for the Reporting API
- [ ] DataVIA WMS support
- [ ] D-TRO data-model helpers (schema validation against DfT releases)
- [ ] Scottish Road Works Register (SRWR)?
- [ ] Ordnance Survey NGD / Linked Identifiers?

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Development

```bash
pip install -e ".[dev]"
pytest                    # 35 mocked unit tests - no credentials needed
ruff check .
```

The unit tests mock the network so they run offline and without credentials.
To verify the SDK against the **real** test/sandbox systems with your own
credentials, use the smoke test or the integration suite — see
[docs/INTEGRATION.md](docs/INTEGRATION.md):

```bash
python scripts/smoke_test.py     # one read-only call per configured service
pytest -m integration -v         # same checks, in the test suite
```

## Licence

MIT. Not affiliated with or endorsed by the Department for Transport or
Geoplace. Street Manager documentation is © Crown copyright, available under
the Open Government Licence v3.0.
