# Installation

> Migrated verbatim from README.md's `## Install` section (phase one, lossless restructure — see `docs/migration-mapping.md`).

```bash
pip install streetworks            # core
pip install "streetworks[sns]"     # + SNS signature verification (cryptography)
```

Requires Python 3.10+.

## Status

Early alpha. See [`docs/providers/index.md`](../providers/index.md) for the
full, per-provider verified/pending breakdown (which providers are
authentication-and-read verified against the real systems, which are
[Credentials wanted](../providers/index.md#credentials-wanted), and the
[Recently confirmed](../providers/index.md#recently-confirmed) log of what
real data changed when a tester's credentials confirmed a scaffold).

Known reconciliation items: D-TRO `v4.0.0` is the production schema (live
since 2026-06-01, confirmed directly from DfT's own repo and separately at
a DfT technical webinar, July 2026) — this SDK now generates and ships
`v4.0.0` models alongside `v3.5.1` (production still accepts both; see
[docs/DTRO_SCHEMAS.md](../DTRO_SCHEMAS.md) for the full payload-shape
diff — it's a real migration, not a drop-in swap); the `streetworks.exceptions`
API and client method surface may change before `1.0`. See
[docs/INTEGRATION.md](../INTEGRATION.md) for how to verify against the
real systems yourself. First-contact reports welcome.
