# Excluded territories

> New content, not a migration — not in README.md (see
> `docs/migration-reconciliation.md`, Case 3: "China exclusion" and
> "Russia exclusion", both explicitly listed as not present in the
> source). **Stated here on the project owner's own authority as a
> design decision, not independently investigated or verified within
> this codebase or session** — no scaffold, client, or registry entry
> for either territory exists to check this claim against, unlike the
> rest of this project's provider documentation, which is grounded in
> live-verified findings.

China and Russia are deliberately excluded from this SDK's provider
scope:

- **China**: public Chinese mapping/geodata is legally required to be
  obfuscated under the GCJ-02 coordinate system before publication,
  rather than using unmodified WGS84. Any coordinates from a Chinese
  source would need a further, separately-verified correction step this
  project doesn't implement, and mixing obfuscated and true coordinates
  silently would be exactly the kind of unstated CRS handling this
  project's own data-integrity discipline rules out (see
  [`docs/concepts/data-integrity.md`](../concepts/data-integrity.md)).
- **Russia**: excluded on sanctions/export-control grounds.

Neither exclusion has a corresponding scaffold, client, or fixture in
this repository to point to — they're recorded here as a stated
boundary on future scope, not as a finding this project verified
itself.
