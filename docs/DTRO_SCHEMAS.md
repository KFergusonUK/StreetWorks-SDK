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
| `v5.0.0` | In development | Not yet built. Confirmed contents so far: refactored speed-limit regulation modelling, a new attribute distinguishing diversion-route geometry styles, additional `vehicleType`/`regulationType` values, and new validation rules (`pointGeometry` no longer usable for speed limits; `directedLinear` mandatory for some `regulationType`s) |
| `v4.0.0` | **Current production schema** (confirmed at a DfT technical webinar, July 2026) | This SDK still ships `v3.5.1` models — pending regeneration, not yet done |
| `v3.5.1` | Shipped by this SDK today | Generated publish models target this version; no longer matches production, see `v4.0.0` above |
| `v3.5.0` | Supported | |
| `v3.4.1` | Deprecating | The version the current SDK examples were first written against |
| `v3.4.0` | Deprecating | |

The SDK's D-TRO **client** (endpoints, auth, headers) is independent of these
data-model versions and is verified against the OpenAPI spec. What tracks the
schema version is only the **publish payload** you send to `create_dtro` /
`update_dtro` / `create_provisions`.

## What the SDK does today

The client accepts publish payloads as plain dicts and forwards them as-is, so
you can publish against **any** schema version by constructing the payload
yourself (the DfT examples in the repo above are the reference). For the
shipped schema version(s), generated Pydantic models let you validate a
payload locally before sending — see below.

## Generated publish models (v3.5.1 shipped)

Version-namespaced Pydantic models are generated from the DfT JSON schema
into `streetworks.dtro.models.<version>` — `v3_5_1` ships today. **This no
longer matches production**, which moved to `v4.0.0` in July 2026 (confirmed
at a DfT technical webinar) — regeneration against `v4.0.0` is pending, not
yet done. Validate a payload before publishing:

```python
from streetworks.dtro import DTROClient

DTROClient.validate_payload(payload)                    # v3_5_1 default
DTROClient.validate_payload(payload, version="v3_5_1")  # explicit
```

This raises `pydantic.ValidationError` on structural, type, enum, or
required-field errors, and returns the payload unchanged on success. Two
honest limits: the schema's cross-field `if/then/else` rules (e.g. "if
regulation X then condition Y required") are enforced by the D-TRO service
on submission, not locally; and formatted strings (email/uri/date) validate
leniently as plain strings. A payload that passes here can still be rejected
by the service — but the common mistakes are caught first.

To add a new version (e.g. `v4_0_0`, now the production schema, not yet regenerated here):

1. Download its JSON schema from the repo's version folder into
   `specs/dtro/<version>/`.
2. Run `python scripts/generate_dtro_models.py --version v4_0_0
   --schema specs/dtro/v4_0_0/<schema>.json`.
3. Commit the generated models so they ship on PyPI.
