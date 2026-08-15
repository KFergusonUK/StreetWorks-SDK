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
promoter-account/council-policy considerations noted in that module's docstring.

**Also sandbox-verified, 2026-08-12:** the evidence-attachment addition to
the same `apply()` flow - two placeholder files uploaded via
`WorkAPI.upload_file` (`POST /files`, already a generic wrapper, no new
`client.py` method needed), the real returned `file_id`s included on
`WorkCreateRequest.file_ids`, and `create_work` still succeeding with that
field present. A real run produced real ids (`file_ids=[80475, 80476]`)
against a real created work (`UG05046633203`) - not a mocked assertion.

## Field disposition (S50/01 vs `WorkCreateRequest`)

The real Durham S50/01 paper form (*Application for Licence to Place,
Retain and Maintain Apparatus Within the Highway*) carries more than a
works record can hold. Checked field-by-field, not assumed:

- **Structured** (a real home on `WorkCreateRequest`): licensee identity
  (`secondary_contact`/number/email), apparatus description/excavation
  method (`description_of_work`), whether excavation is required
  (`excavation`), the drawn location (`works_coordinates`, reprojected to
  BNG), road/USRN, traffic management and duration.
- **Free-text** (no dedicated field, but not lost): trench counts,
  development context, other supporting information - fits in
  `additional_info`/`project_reference_number`.
- **Out of scope, genuinely, not a gap to close**: contractor identity
  distinct from the licensee, street-works accreditation, public liability
  insurance, Land Registry references, adoption agreements, and the
  applicant's signed declarations. These are the evidence, accreditation,
  land title, and legal undertakings a licensing authority needs to *grant
  a licence* - none of it has a shape in a works-coordination permit. This
  is the boundary the connector was always drawn around: Street Manager
  records the **works**; it does not process the **licence**. The
  evidence-attachment addition above narrows this bucket a little (insurance
  and accreditation *copies* can now be filed as attachments, not lost) but
  doesn't remove it - filing a document is not the same as it being
  assessed, and the licence decision still sits with the Highway Authority.

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

**Two additions layered onto the script, both example-layer only - no
`section_50_utils` or `client.py` change was needed for either:**
evidence attachment (upload placeholder files via the already-existing
`WorkAPI.upload_file`, fold the real returned `file_id`s into
`applicant_fields["file_ids"]`, which `build_work_create_request` already
passes through untouched) and an illustrative bond estimate
(`calculate_bond`, a pure function computing itemised per-surface costs
from the drawn extent's own real BNG area via a shoelace formula, times
council rates - folded into `additional_info` as a labelled note, never a
structured field). What's real in both: the upload calls, the returned
ids, and the area arithmetic. What's illustrative: the placeholder
documents and the bond rates, exactly like `HA_SWA_CODE` above - replace
with your own evidence and your own council's current schedule.

See [`docs/domain-notes/uk-permits.md`](../domain-notes/uk-permits.md#s50-fee-suppression)
for the fee-suppression behaviour this connector's own docstring can't
show — Street Manager, not the connector, decides not to bill an S50.
