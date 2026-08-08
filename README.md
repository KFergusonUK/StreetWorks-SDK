# streetworks

[![CI](https://github.com/KFergusonUK/StreetWorks-SDK/actions/workflows/ci.yml/badge.svg)](https://github.com/KFergusonUK/StreetWorks-SDK/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/streetworks)](https://pypi.org/project/streetworks/)
[![Python](https://img.shields.io/pypi/pyversions/streetworks)](https://pypi.org/project/streetworks/)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)

An open Python SDK for street works and roadworks data — the UK's
registers, Europe's national roadworks feeds, and the US WZDx standard,
behind one consistent, typed, well-tested client.

> We do this not because it is easy, but because it is hard.

Developed and published independently, in a personal capacity — **not
on behalf of, or endorsed by, any employer.** See
[`docs/governance/attribution.md`](docs/governance/attribution.md) for
the full statement and contributor credits.

## Install

```bash
pip install streetworks            # core
pip install "streetworks[sns]"     # + SNS signature verification (cryptography)
```

Requires Python 3.10+. Early alpha, pre-1.0 — see
[`docs/getting-started/installation.md`](docs/getting-started/installation.md)
for what's verified against live systems today.

## Quickstart

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

For connectivity checks without data retrieval:
`python scripts/smoke_test.py`. Credential setup, environment variables and
what to expect from a real run are in
[`docs/getting-started/quickstart.md`](docs/getting-started/quickstart.md).

## Coverage at a glance

UK statutory registers and gazetteers (Street Manager, DataVIA, D-TRO, SRWR,
OS Open USRN), national and regional roadworks feeds and address/street
registers across Europe, the US WZDx standard plus NYC/Chicago/Paris
municipal permit registers, Australia (national + state), and New Zealand
— and growing. Every provider carries an explicit `network_scope` and a
confirmed (or honestly flagged unconfirmed) licence; nothing is silently
assumed open.

`streetworks.providers()` / `get_provider()` let you find a provider by what
it covers rather than needing to already know the module name — see
[`docs/providers/index.md`](docs/providers/index.md) for the full coverage
matrix, per-provider modules, and current Credentials-wanted scaffolds.

## Documentation

- **Getting started** — [installation](docs/getting-started/installation.md), [quickstart](docs/getting-started/quickstart.md), [development](docs/getting-started/development.md)
- **Concepts** — [architecture](docs/concepts/architecture.md), [data model](docs/concepts/data-model.md), [data integrity discipline](docs/concepts/data-integrity.md), [CRS & datums](docs/concepts/crs-and-datums.md), [write path (Section 50)](docs/concepts/write-path.md)
- **Providers** — [index / coverage matrix / credentials wanted](docs/providers/index.md), [UK & Crown Dependencies](docs/providers/uk.md), [Europe](docs/providers/europe.md), [Italy](docs/providers/italy.md), [United States](docs/providers/us.md), [Australia](docs/providers/australia.md), [New Zealand](docs/providers/new-zealand.md), [pending candidates](docs/providers/pending.md)
- **Domain notes** — [provider quirks](docs/domain-notes/provider-quirks.md), [UK permits](docs/domain-notes/uk-permits.md), [excluded territories](docs/domain-notes/excluded-territories.md)
- **Roadmap** — [`docs/roadmap.md`](docs/roadmap.md) (chronological build log)
- **Contributing** — [scaffold states](docs/contributing/scaffolds.md), [agent boundaries](docs/contributing/agent-boundaries.md), and see [CONTRIBUTING.md](CONTRIBUTING.md) for the full ground rules
- **Governance** — [licensing](docs/governance/licensing.md), [attribution and capacity](docs/governance/attribution.md)
- Full docs entry point: [`docs/index.md`](docs/index.md)

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT. Not affiliated with or endorsed by the Department for Transport or
Geoplace. Street Manager documentation is © Crown copyright, available under
the Open Government Licence v3.0. See
[`docs/governance/licensing.md`](docs/governance/licensing.md) for the full
per-provider licence index.
