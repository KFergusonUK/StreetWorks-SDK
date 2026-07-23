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
| `v4.0.0` | **Current production schema** — live in Integration 2026-04-30, Production 2026-06-01 (confirmed directly from the DfT repo's own release announcements, and separately at a DfT technical webinar, July 2026) | Models generated and shipped by this SDK — see below |
| `v3.5.1` | Also shipped by this SDK, also still accepted by production | DfT's own announcement: "v3.5.0 and v3.5.1 remain live at present" alongside v4.0.0 — this is not a hard cut-over, both are genuinely valid production payload shapes right now |
| `v3.5.0` | Supported | |
| `v3.4.1` | **Deprecated** 2026-06-01, alongside the v4.0.0 production release | The version the current SDK examples were first written against |
| `v3.4.0` | **Deprecated** 2026-06-01 | |

The SDK's D-TRO **client** (endpoints, auth, headers) is independent of these
data-model versions and is verified against the OpenAPI spec/Postman
collections. What tracks the schema version is only the **publish payload**
you send to `create_dtro` / `update_dtro` / `create_provisions`, and the
local `validate_payload()` helper.

**No other client-behaviour change was found for v4.0.0** — endpoints,
headers, auth, and payload-size limits are all unchanged from what
`streetworks/dtro/client.py`'s own module docstring already documents. Two
real, separate things *did* change alongside v4.0.0 that are not schema
concerns and are not implemented here, reported rather than silently
skipped:

- **A new spatial search capability** was added to `POST /search` (DfT
  announcement, 2026-07-13): an input polygon returns `INTERSECT` results —
  any record whose geometry lies within or intersects the supplied polygon.
  Confirmed live in the Integration environment only as of that
  announcement. `DTROClient.search()` already forwards an arbitrary
  `DtroSearch` body as-is, so a caller can already use this by constructing
  the right query dict — no client change is *required* — but there's no
  typed/documented helper for the polygon shape here.
- **New service-generated response metadata**: DfT's v4.0.0 announcement
  states the service now auto-generates `Creation date/time`, `Last update
  date/time`, and `Last Up-version date/time` on each record. These are
  response-side fields the service adds, not part of the publish JSON
  schema `Model` validates against — they were not found anywhere in the
  v4.0.0 schema fetched from the DfT repo (which is the *submission* schema
  only), so they aren't in the generated models either. If DfT publishes a
  separate response/record schema for `get_dtro`/`search`, it hasn't been
  found or verified this session.

## What the SDK does today

The client accepts publish payloads as plain dicts and forwards them as-is, so
you can publish against **any** schema version by constructing the payload
yourself (the DfT examples in the repo above are the reference). For the
shipped schema version(s), generated Pydantic models let you validate a
payload locally before sending — see below.

## Generated publish models (v3.5.1 and v4.0.0 shipped)

Version-namespaced Pydantic models are generated from the DfT JSON schema
into `streetworks.dtro.models.<version>` — `v3_5_1` and `v4_0_0` both ship
today, additively (`v3_5_1` was not touched or regenerated). Validate a
payload before publishing:

```python
from streetworks.dtro import DTROClient

DTROClient.validate_payload(payload)                    # v4_0_0 default
DTROClient.validate_payload(payload, version="v3_5_1")  # explicit
DTROClient.validate_payload(payload, version="v4_0_0")  # explicit, same as no version
```

**Behaviour change: the default is now `v4_0_0`** (was `v3_5_1`) — matching
DfT's production schema since 2026-06-01. Production genuinely still
accepts v3.5.1 payloads too (see the version map above), so pass
`version="v3_5_1"` explicitly if that's what you're actually validating —
calling `validate_payload()` with no `version` on a v3.5.1-shaped payload
now fails, the mirror image of the previous default's trap. The raised
`pydantic.ValidationError` names the schema version directly in its
message (`"...for v4_0_0 Model"`/`"...for v3_5_1 Model"`) precisely because
both versions' generated classes share the name `Model` and a bare
traceback couldn't otherwise tell you which schema rejected a payload. See
`DTROClient.validate_payload`'s own docstring.

This raises `pydantic.ValidationError` on structural, type, enum, or
required-field errors, and returns the payload unchanged on success. Two
honest limits: the schema's cross-field `if/then/else` rules (e.g. "if
regulation X then condition Y required") are enforced by the D-TRO service
on submission, not locally; and formatted strings (email/uri/date) validate
leniently as plain strings. A payload that passes here can still be rejected
by the service — but the common mistakes are caught first.

### v3.5.1 → v4.0.0, in human terms

Real, schema-verified differences (cross-checked against DfT's own written
release notes on
[Issue #1](https://github.com/department-for-transport-public/D-TRO/issues/1),
2026-03-31, and against the two schemas' real `$defs` directly — not just
copied from the announcement):

- **Breaking: `regulation` changed from a 1-item array to a plain object.**
  v3.5.1: `"regulation": [{...}]` (`minItems: 1, maxItems: 1`). v4.0.0:
  `"regulation": {...}`. Every existing v3.5.1 payload/caller needs this
  restructured, not just re-validated.
- **Breaking: `condition`/`conditions`/`conditionSet` were restructured.**
  v3.5.1's `conditions` was an awkward `oneOf` (a bare `condition`, or an
  object with `operator`+`condition[]`+`conditionSet`); v4.0.0's is simply
  `{"type": "array", "items": {"$ref": "condition"}}`. `conditionSet` went
  from an *array* of `{operator, conditionSet, conditions, condition[]}`
  objects to a single object requiring `operator`, referencing `conditions`
  only (no more nested `condition`/`conditionSet` properties directly on
  it). `condition` itself gained a new direct `conditionSet` property it
  didn't have in v3.5.1 (nesting a condition set inside a single condition
  is now possible). A **new `permitCondition` type** exists in v4.0.0 with
  no v3.5.1 equivalent found (`locationRelatedPermit`,
  `maxDurationOfPermit`, `maximumAccessDuration`, `minimumTimeToNextEntry`,
  `permitIdentifier`, `schemeIdentifier`, and more) — not mentioned by name
  in DfT's own release notes, found directly in the schema diff.
- **`regulation.timeZone` is now a fixed value.** v3.5.1: any non-empty
  string. v4.0.0: `"const": "Europe/London"` — any other value now fails
  validation (confirmed by testing, see `tests/test_dtro_models_v4_0_0.py`).
- **`vehicleType` lost exactly 8 values, all moved to `vehicleUsageType`**
  (confirmed live, byte-for-byte matching DfT's own list): `coastguard
  Vehicle`, `diplomaticVehicle`, `emergencyAndIncidentSupportVehicle`,
  `emergencyServicesVehicle`, `fireServiceVehicle`, `policeVehicle`,
  `publicServiceVehicle`, `schoolBus`. A payload stating one of these as a
  `vehicleType` under v4.0.0 will now fail; it needs restating as a
  `vehicleUsageType`.
- **`sourceActionType` gained `"fullRevoke"`** (confirmed live) — for full
  revocations of a TRO; partial revocations (revoking only some contained
  provisions) still use `"amendment"`, per DfT's own note.
- **New validation, per DfT's release notes** (not independently
  re-derived from the raw schema this session, but real and worth carrying
  here): `externalReference.lastUpdateDate` must not be in the future;
  `rateLine.durationStart` must be before `rateLine.durationEnd`; and
  `heaviestAxleWeight`/`grossVehicleWeight`/`vehicleHeight`/
  `vehicleLength`/`vehicleWidth` gained minimum/maximum/`multipleOf`
  constraints.
- **`maxStayNoReturn` moved to be a child of `period`**, rather than sitting
  where it was since v3.4.1 (per DfT's release notes).
- Not schema changes, but real v4.0.0-era additions worth knowing: the new
  search-polygon capability and new service-generated response metadata —
  see the callout above.

None of this is a small diff. Treat v4.0.0 as a genuine payload-shape
migration, not a drop-in schema swap — the generated models will catch the
structural breaks (wrong `regulation` shape, wrong `vehicleType` value,
wrong `timeZone`) immediately and locally, which is exactly what
`validate_payload(payload, version="v4_0_0")` is for.

### Does the `v3_5_1`/`v4_0_0` namespacing scale to a third version?

Yes, mechanically — nothing here is hardcoded to two versions.
`scripts/generate_dtro_models.py` and `streetworks/dtro/models/__init__.py`
are both purely parametrised on the `--version`/`<version>` string; adding
`v5_0_0` when it lands is the same three steps as adding `v4_0_0` was (see
below). The one place that does *not* auto-scale is `DTROClient
.validate_payload`'s own error message, which hardcodes the list of
available versions (`"Available today: 'v3_5_1', 'v4_0_0'"`) — a one-line
edit each time a version is added, not a structural limitation, but real
maintenance a future version add must remember to do.

To add a new version (e.g. `v5_0_0`, in development, not yet released - see
the version map above):

1. Download its JSON schema from the repo's version folder into
   `specs/dtro/<version>/`.
2. Run `python scripts/generate_dtro_models.py --version v5_0_0
   --schema specs/dtro/v5_0_0/<schema>.json`.
3. Commit the generated models so they ship on PyPI.
4. Update `DTROClient.validate_payload`'s "Available today" error message
   (see above — this step is easy to forget, since nothing enforces it).
