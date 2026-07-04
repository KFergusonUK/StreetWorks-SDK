# D-TRO schema versions

The D-TRO **data model** (the shape of a traffic order you publish) is
versioned and evolves independently of the API surface. Multiple versions are
supported concurrently, so publishing code must target the version the
receiving environment expects.

Authoritative source — the DfT publishes every version's JSON schema, data
model, examples, and validation rules here:
**https://github.com/department-for-transport-public/D-TRO**

## Version map

Confirm the current mapping and any cut-over dates against the repository and
its release notes before relying on them — deprecation timelines can move.

| Schema version | Role | Notes |
|---|---|---|
| `v4.0.0` | Latest / upcoming | Target to have publish models ready for ahead of its production cut-over |
| `v3.5.1` | **Supported — matches production today** | The version to generate publish models against first |
| `v3.5.0` | Supported | |
| `v3.4.1` | Deprecating | The version the current SDK examples were first written against |
| `v3.4.0` | Deprecating | |

The SDK's D-TRO **client** (endpoints, auth, headers) is independent of these
data-model versions and is verified against the OpenAPI spec. What tracks the
schema version is only the **publish payload** you send to `create_dtro` /
`update_dtro` / `create_provisions`.

## What the SDK does today

The client accepts publish payloads as plain dicts and forwards them as-is, so
you can already publish against **any** schema version by constructing the
payload yourself (the DfT examples in the repo above are the reference). There
is not yet a set of generated, version-namespaced Pydantic models to validate
those payloads before sending — that's the planned enhancement below.

## Planned: generated publish models

Mirroring the Street Manager model pipeline, the intent is to generate
version-namespaced Pydantic models from the DfT JSON schemas, e.g.
`streetworks.dtro.models.v3_5_1` and `streetworks.dtro.models.v4_0_0`, so a
publisher can validate a payload against the exact version their authority
targets.

To do this when picking the work up:

1. Download the JSON schema for the desired version from the repo's version
   folder into `specs/dtro/<version>/`.
2. Extend `scripts/generate_models.py` (or add a sibling script) to emit
   `src/streetworks/dtro/models/<version>/` from that schema.
3. Commit the generated models so they ship on PyPI, and add a manual
   regeneration workflow like the Street Manager one.

Until then, publishing works with hand-constructed dicts validated by the
service on submission.
