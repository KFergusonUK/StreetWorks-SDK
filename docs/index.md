# streetworks documentation

**Coverage** — ✓ live · ~ in progress · ✗ ruled out (quoted from
[`docs/providers/index.md`](providers/index.md#coverage), the canonical
roster — update there first, not here)

**Europe**  ✓ Belgium · Bulgaria · Finland · France · Germany · Iceland · Italy · Jersey · Lithuania · Luxembourg · Netherlands · Norway · Spain · UK   ~ Denmark · Greece · Ireland · Portugal · Sweden
**Americas**  ✓ Canada · United States
**Oceania**  ✓ Australia · New Zealand
**Asia**  ~ Singapore
**Ruled out**  ✗ China · Russia

*Several territories carry multiple data-owning authorities (Catalonia, Basque Country, Mallorca, Madrid; the four UK nations) — and "in progress" collapses two genuinely different states (credentials-wanted vs. documented-but-unavailable) for scannability — see the [full matrix](providers/index.md) for both.*

> Migrated verbatim from README.md's opening (title/intro paragraph and
> the "We do this..." quote), plus a map to the rest of this docs tree
> (phase one, lossless restructure — see `docs/migration-mapping.md` for
> the full checklist-to-file mapping, and `docs/migration-reconciliation.md`
> for what was found while reconciling the seed checklist against the
> actual README).

An open Python SDK for street works and roadworks data — the UK's
registers, Europe's national feeds, the US WZDx standard, and providers
across Australia and New Zealand, behind one consistent, typed,
verification-first client.

> We do this not because it is easy, but because it is hard.

Developed and published independently, in a personal capacity — not on
behalf of, or endorsed by, any employer. See
[`docs/governance/attribution.md`](governance/attribution.md) for the
full statement and contributor credits.

## Why?

Roadworks data is published through wildly different systems —
statutory registers, DATEX II, WZDx, ArcGIS, WFS, bespoke REST APIs and
regional platforms. Almost every provider also has its own
authentication, pagination, geometry, date formats and quirks.

`streetworks` solves that integration problem so you can get on with
building applications instead of learning how every individual road
authority happens to publish its data.

It provides one common model without pretending those sources are
equivalent — preserving the differences, limitations and provenance
that matter.

And, honestly, part of the fun is discovering how different
organisations have chosen to put their data together.

```python
from streetworks.streetmanager import StreetManagerClient, Environment

with StreetManagerClient("api-user@example.com", password, environment=Environment.SANDBOX) as sm:
    sm.authenticate()                                  # verify credentials
    submitted = sm.reporting.permits(status="submitted")
```

## Map

- **Getting started** — [installation](getting-started/installation.md), [quickstart](getting-started/quickstart.md), [development](getting-started/development.md)
- **Concepts** — [architecture](concepts/architecture.md), [data model](concepts/data-model.md), [data integrity discipline](concepts/data-integrity.md), [CRS & datums](concepts/crs-and-datums.md), [write path (Section 50)](concepts/write-path.md)
- **Providers** — [index / coverage matrix / credentials wanted](providers/index.md), [UK & Crown Dependencies](providers/uk.md), [Europe](providers/europe.md), [Italy](providers/italy.md), [United States](providers/us.md), [Canada](providers/canada.md), [Australia](providers/australia.md), [New Zealand](providers/new-zealand.md), [pending candidates](providers/pending.md)
- **Examples** — [`examples.md`](examples.md) (curated, one line per example in `examples/`)
- **Roadmap** — [`roadmap.md`](roadmap.md) (chronological build log)
- **Domain notes** — [provider quirks (index)](domain-notes/provider-quirks.md), [UK permits](domain-notes/uk-permits.md), [excluded territories](domain-notes/excluded-territories.md)
- **Contributing** — [scaffold states](contributing/scaffolds.md), [agent boundaries](contributing/agent-boundaries.md), and see [CONTRIBUTING.md](../CONTRIBUTING.md) for the full ground rules
- **Governance** — [licensing](governance/licensing.md), [attribution and capacity](governance/attribution.md)
- Existing investigation/reference docs (untouched by this migration): [INTEGRATION.md](INTEGRATION.md), [DTRO_SCHEMAS.md](DTRO_SCHEMAS.md), [network-scope-audit.md](network-scope-audit.md), [credentials-wanted-issues.md](credentials-wanted-issues.md), [idemallorca-investigation.md](idemallorca-investigation.md), [catalonia-sct-investigation.md](catalonia-sct-investigation.md), [inspire-gml-investigation.md](inspire-gml-investigation.md), [gazetteer-field-dump.md](gazetteer-field-dump.md), [nap-survey.md](nap-survey.md), [RELEASING.md](RELEASING.md)

## Status of this migration

**Phases one and two both complete.** Phase one (extract and relocate,
not editorial) produced this tree — see `docs/migration-mapping.md` for
the full checklist-to-file mapping and `docs/migration-reconciliation.md`
for what changed between the seed checklist and the real README once it
was read in full. Phase two slimmed the README itself down to a front
door (badges, install, a working quickstart, and links into this tree)
now that every removed block had a confirmed docs home — see
`docs/phase-two-removal-map.md` for the section-by-section removal
mapping. The pre-slim README is preserved in git history, not archived
separately.
