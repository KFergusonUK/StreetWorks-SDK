# streetworks documentation

> Migrated verbatim from README.md's opening (title/intro paragraph and
> the "We do this..." quote), plus a map to the rest of this docs tree
> (phase one, lossless restructure — see `docs/migration-mapping.md` for
> the full checklist-to-file mapping, and `docs/migration-reconciliation.md`
> for what was found while reconciling the seed checklist against the
> actual README).

An open Python SDK for street works and roadworks data — the UK's
registers, Europe's national roadworks feeds, and the US WZDx standard,
behind one consistent, typed, well-tested client.

> We do this not because it is easy, but because it is hard.

```python
from streetworks.streetmanager import StreetManagerClient, Environment

with StreetManagerClient("api-user@example.com", password, environment=Environment.SANDBOX) as sm:
    sm.authenticate()                                  # verify credentials
    submitted = sm.reporting.permits(status="submitted")
```

## Map

- **Getting started** — [installation](getting-started/installation.md), [quickstart](getting-started/quickstart.md), [development](getting-started/development.md)
- **Concepts** — [architecture](concepts/architecture.md), [data model](concepts/data-model.md), [data integrity discipline](concepts/data-integrity.md), [CRS & datums](concepts/crs-and-datums.md), [write path (Section 50)](concepts/write-path.md)
- **Providers** — [index / coverage matrix / credentials wanted](providers/index.md), [UK & Crown Dependencies](providers/uk.md), [Europe](providers/europe.md), [Italy](providers/italy.md), [United States](providers/us.md), [Australia](providers/australia.md), [New Zealand](providers/new-zealand.md)
- **Roadmap** — [`roadmap.md`](roadmap.md) (chronological build log)
- **Domain notes** — [provider quirks (index)](domain-notes/provider-quirks.md)
- **Contributing** — [scaffold states](contributing/scaffolds.md), and see [CONTRIBUTING.md](../CONTRIBUTING.md) for the full ground rules
- **Governance** — [licensing](governance/licensing.md)
- Existing investigation/reference docs (untouched by this migration): [INTEGRATION.md](INTEGRATION.md), [DTRO_SCHEMAS.md](DTRO_SCHEMAS.md), [network-scope-audit.md](network-scope-audit.md), [credentials-wanted-issues.md](credentials-wanted-issues.md), [idemallorca-investigation.md](idemallorca-investigation.md), [catalonia-sct-investigation.md](catalonia-sct-investigation.md), [inspire-gml-investigation.md](inspire-gml-investigation.md), [gazetteer-field-dump.md](gazetteer-field-dump.md), [nap-survey.md](nap-survey.md), [RELEASING.md](RELEASING.md)

## Status of this migration

**Phase one only — extract and relocate, not editorial.** The README
itself is untouched and remains the reference copy for this phase; see
`docs/migration-mapping.md` for the full checklist-to-file mapping and
`docs/migration-reconciliation.md` for what changed between the seed
checklist and the real README once it was read in full. Phase two
(slimming the README to a front door + links into this tree) is a
separate, not-yet-started task.
