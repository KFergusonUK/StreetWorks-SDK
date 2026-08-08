# Quickstart

> Migrated verbatim from README.md's `## Quickstart`, `## Prerequisites:
> credentials`, and `## Verify your setup` sections (phase one, lossless
> restructure — see `docs/migration-mapping.md`).

```python
from streetworks.streetmanager import StreetManagerClient, Environment

with StreetManagerClient("api-user@example.com", password, environment=Environment.SANDBOX) as sm:
    sm.authenticate()                                  # verify credentials
    submitted = sm.reporting.permits(status="submitted")
```

The fastest way to see everything working: copy the credential template, fill
in what you have, and run the one-file tour — it logs in to each configured
provider and retrieves a little real data (read-only). Providers you leave
blank are skipped, and SRWR / OS Open USRN need no credentials at all.

```bash
cp .env.example .env      # then edit .env
python examples/quickstart.py
```

For connectivity checks without data retrieval, use the smoke test instead:
`python scripts/smoke_test.py`.

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
| National Highways | Free account at the [developer portal](https://developer.data.nationalhighways.co.uk/) — create a "Subscription" for an API key | `NH_SUBSCRIPTION_KEY` |
| Statens vegvesen (Norway, DATEX II) — confirmed 2026-07-30, see [Recently confirmed](../providers/index.md#recently-confirmed) | Free; [request access](https://www.vegvesen.no/en/fag/technology/open-data/a-selection-of-open-data/what-is-datex/get-access/) to the "Road traffic information" publication — registration issues a username/password, not an API key | `VEGVESEN_USERNAME` + `VEGVESEN_PASSWORD`, or `VEGVESEN_TOKEN` (Bearer) |
| Trafikverket (Sweden, DATEX-adjacent) — **[Credentials wanted](../providers/index.md#credentials-wanted)** | Free, self-service: [data.trafikverket.se](https://data.trafikverket.se/) or [Trafiklab](https://www.trafiklab.se/api/other-apis/trafikverket/) | `TRAFIKVERKET_API_KEY` |
| Vejdirektoratet (Denmark, DATEX II 3.2) — **[Credentials wanted](../providers/index.md#credentials-wanted)** | Free; register via [Dataudveksleren](https://du-portal-ui.dataudveksler.app.vd.dk/) — issues Basic Auth + a per-dataset pull URL | `VEJDIREKTORATET_URL`, `VEJDIREKTORATET_USERNAME` + `VEJDIREKTORATET_PASSWORD` |
| TfNSW Live Traffic (New South Wales, Australia) — confirmed 2026-07-30, see [Recently confirmed](../providers/index.md#recently-confirmed) | Free, self-service via the [TfNSW API Gateway](https://opendata.transport.nsw.gov.au/) | `NSW_LIVETRAFFIC_API_KEY` |
| DTP Planned Disruptions (Victoria, Australia) — confirmed 2026-07-30, see [Recently confirmed](../providers/index.md#recently-confirmed) | Free via the [Transport Victoria Open Data Hub](https://opendata.transport.vic.gov.au/dataset/planned-disruptions-road) | `VIC_DISRUPTIONS_API_KEY` |

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
obvious immediately. See [docs/INTEGRATION.md](../INTEGRATION.md) for the
full variable list and how to (deliberately) target production.
