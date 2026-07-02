# Testing against the real systems

The SDK makes real calls to the live services. The **unit tests** (`pytest`)
mock the network so they run fast, offline, and without credentials — that's
by design. To verify the SDK actually connects and behaves against the real
test/sandbox systems, use the tools below with your own credentials.

Everything here is **read-only** and targets **non-production** environments
by default (Street Manager SANDBOX, D-TRO integration). Nothing is created,
updated, or deleted.

Both the smoke test and the integration suite print the target environment
prominently and **refuse to touch production unless you explicitly opt in**
(`--allow-production` for the smoke test, `STREETWORKS_ALLOW_PRODUCTION=1` for
the integration tests). A stray `*_ENV=production` variable can't quietly send
you at live data.

## Quickest check: the smoke test

```bash
export SM_EMAIL="api-user@example.com"
export SM_PASSWORD="..."
python scripts/smoke_test.py
```

It prints a banner naming the target environment for each service, then runs
one minimal read per service you've supplied credentials for and prints
`PASS` / `FAIL` / `SKIP`. Run `python scripts/smoke_test.py --help` for the
full variable list.

To deliberately check a **production** service (still read-only), set its
`*_ENV=production` variable and add `--allow-production`:

```bash
SM_EMAIL=... SM_PASSWORD=... SM_ENV=production \
  python scripts/smoke_test.py --allow-production
```

## As part of the test suite

The same checks exist as skip-guarded integration tests:

```bash
pytest -m integration -v      # needs credentials in the environment; skips what isn't set
```

These are excluded from the default `pytest` run, so they never interfere
with normal development or CI. To run them in CI, use the **Integration tests
(live systems)** workflow (Actions tab, manual trigger). It reads credentials
from repository secrets — add whichever you need under
Settings → Secrets and variables → Actions:

`SM_EMAIL`, `SM_PASSWORD`, `DATAVIA_USER`, `DATAVIA_PASSWORD`,
`DATAVIA_CLIENT_ID`, `DATAVIA_CLIENT_SECRET`, `DATAVIA_USRN`,
`DTRO_CLIENT_ID`, `DTRO_CLIENT_SECRET`, `DTRO_APP_ID`.

## Environment variables

| Variable | Service | Notes |
|---|---|---|
| `SM_EMAIL`, `SM_PASSWORD` | Street Manager | API user credentials |
| `SM_ENV` | Street Manager | `sandbox` (default) or `production` |
| `SM_VERSION` | Street Manager | `v6` (default) or `v7` |
| `DATAVIA_USER`, `DATAVIA_PASSWORD` | DataVIA | Basic auth |
| `DATAVIA_CLIENT_ID`, `DATAVIA_CLIENT_SECRET` | DataVIA | OAuth2 (used in preference to Basic if set) |
| `DATAVIA_USRN` | DataVIA | optional USRN to fetch as an extra probe |
| `DTRO_CLIENT_ID`, `DTRO_CLIENT_SECRET` | D-TRO | OAuth2 client credentials |
| `DTRO_APP_ID` | D-TRO | your application UUID |
| `DTRO_ENV` | D-TRO | `integration` (default) or `production` |

## Open Data is different

Open Data is a **push** model — there's no endpoint to poll. A true
end-to-end test needs a publicly reachable HTTPS endpoint that Street Manager
can POST to. For local development, expose the example FastAPI receiver
(`examples/opendata_fastapi.py`) with a tunnel such as ngrok, then register
that URL as your subscription and confirm the handshake. The smoke test
verifies the parsing/verification pipeline locally, which is the part you can
check without deploying.

## Values to confirm on first contact

A few endpoint details were taken from the published documentation but not
yet exercised against a live account. The smoke test is the fastest way to
confirm them; if any is wrong for your account it's a one-line change (all are
overridable without touching library internals):

- **Street Manager `/authenticate` field names.** The SDK sends
  `{"emailAddress": ..., "password": ...}`. If your account expects different
  keys, that's the first thing a failed `authenticate()` will reveal.
- **Street Manager base URLs / version paths.** `Environment` and
  `ApiVersion` accept plain strings, so you can pass an exact base URL or
  version segment if the host or path differs.
- **DataVIA service URL.** Defaults to the documented Basic/OIDC service
  URLs (note the significant `www.` prefix). Override with the `service_url`
  argument if your subscription uses a different path.
- **D-TRO token and endpoint paths.** Token is obtained from
  `{base}/oauth-generator`; the newest *provisions* endpoints aren't wrapped
  yet — reach them via `dtro.request(...)` until they're added.

When you've confirmed the real shapes, please open a PR or an issue noting
what you verified and against which environment — that turns these inferences
into documented certainties for everyone.
