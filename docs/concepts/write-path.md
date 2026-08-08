# Write path (Section 50 connector)

> Migrated verbatim from README.md's `## Street Manager` section (the S50
> paragraphs) and the `## Status` section (the sandbox-verification
> paragraph) (phase one, lossless restructure — see
> `docs/migration-mapping.md`).

## Verification status

Not yet exercised against live systems — implemented to the published specs
and covered by mocked tests: **most write/publish paths** (general Street
Manager work submission and assessment; D-TRO create/update and
provisions). These are publisher-scoped and deliberately excluded from the
read-only smoke test.

**Exception, sandbox-verified 2026-08-06, production unexercised:** the
Section 50 apply/start/stop path
([`examples/streetmanager_section_50.py`](../../examples/streetmanager_section_50.py))
has been run end-to-end against the Street Manager sandbox - `create_work`,
`start_work`, and `stop_work` all succeeded against a real sandbox record.
Note this needed a Promoter-role sandbox account specifically; an HA-role
login (which the read-only Street Manager examples use) got 400s and would
likely 403 on `create_work` regardless of payload correctness - see that
script's own docstring. Sandbox success says nothing about production,
which remains untouched and shouldn't be exercised casually here given the
promoter-account/council-policy considerations noted in that module's brief.

## The connector itself

See [`examples/streetmanager_section_50.py`](../../examples/streetmanager_section_50.py)
for applying for, starting, and stopping a Section 50 licence works record
under a highway authority's own promoter account - transport and identity
injection only (reprojects the applicant's WGS84 extent to BNG, stamps the
SWA codes and `activity_type`/`work_type`, passes everything else through
unchanged). The reusable request-assembly logic lives in
`streetworks.streetmanager.utils.section_50_utils`; the WGS84↔BNG transform
it depends on (no `pyproj` - a pure-Python implementation of Ordnance
Survey's own published Helmert + Transverse Mercator formulas) lives in
`streetworks.common._bng`. **Needs Promoter-role sandbox credentials, not
Highway Authority** - a Street Manager login can't hold both, and this is a
different account from the HA-role one the other Street Manager examples
use for reads (live-confirmed - see the script's own docstring).

Open [`examples/streetmanager_section_50_form.html`](../../examples/streetmanager_section_50_form.html)
directly in a browser for a visual mockup of the applicant-facing flow -
static and disconnected (no server, nothing calls Street Manager), but its
"Build request" buttons run a real, faithful port of both
`streetworks.common._bng`'s reprojection and
`section_50_utils.build_work_create_request`'s assembly logic in-page, so
the JSON shown is genuinely what the Python connector would send, not a
mockup of it.

See [`docs/domain-notes/uk-permits.md`](../domain-notes/uk-permits.md#s50-fee-suppression)
for the fee-suppression behaviour this connector's own docstring can't
show — Street Manager, not the connector, decides not to bill an S50.
