# UK permit domain notes

> New content, not a migration — neither item below was in README.md
> (see `docs/migration-reconciliation.md`, Case 3: "UK per-USRN/terraces
> claim" and "S50 fee-suppression/deem-clock detail", both explicitly
> listed as not present in the source). The two items carry different
> levels of grounding in this repository — see each section.

## Permits are issued per-USRN; terraces share a parent USRN

Street Manager permits are issued against a USRN (Unique Street
Reference Number), not against individual properties. A row of
terraced properties, or a named sub-section of a street, is commonly
addressed separately in everyday use but is not necessarily a distinct
USRN — it can share its parent street's USRN.

**Stated here on the project owner's own domain knowledge as a council
employee, not independently re-derived from this codebase.** The
closest grounded finding in this repository is narrower and specific to
one data source: DataVIA's `ESUStreets` layer carries no name field at
all, so a real named sub-part of a street sharing a USRN — e.g.
"Anchorage Terrace", a real local name for part of Church Street,
Durham, USRN `11713561` — is not recoverable from that source at any
level (confirmed live via `DescribeFeatureType`; see the module
docstring of
[`src/streetworks/common/from_datavia.py`](../../src/streetworks/common/from_datavia.py)
and [`docs/gazetteer-field-dump.md`](../gazetteer-field-dump.md)). That
finding is about gazetteer naming coverage for one provider, not a
general statement of Street Manager's permitting statute — the two are
related (both turn on USRNs being the unit of reference) but shouldn't
be read as the same claim.

## S50 fee suppression

The only Section 50-specific behaviour anywhere in the Street Manager
system is that no charge is raised in reporting. Mechanically, an S50
work is submitted, started, and stopped identically to a statutory
permit; the fee is suppressed at the reporting/billing layer rather
than anywhere the connector touches. This reconciles the statute (a
Section 50 licence can't carry scheme fees) with the observed
"planned/standard" permit behaviour in Street Manager — Street Manager
keeps the ordinary permit mechanics and zeroes the charge, rather than
modelling S50 as a distinct record type.

This is invisible to
[`examples/streetmanager_section_50.py`](../../examples/streetmanager_section_50.py)
itself — the connector never touches charging — but is worth stating
here precisely because a later reader of that adapter can't see it from
the code: the connector treats an S50 as a permit in every respect;
Street Manager alone decides not to bill it. Sourced from
`s50-streetworks-connector-brief.md` (the investigation document this
connector was built from — see [`docs/concepts/write-path.md`](../concepts/write-path.md)
for the connector itself and its sandbox-verification status), which
states this finding as empirically verified against a live sandbox
submission, not assumed from the spec alone.
