# Pending provider candidates

> New content, not a migration. None of Portugal, Singapore, or Canada
> appear in README.md in this "candidate for investigation" framing —
> see `docs/migration-reconciliation.md`, Case 3, for what each name
> actually does appear as (Portugal: a future-gazetteer mention already
> migrated to [`docs/providers/europe.md`](europe.md#international-gazetteers);
> Canada: the fact that a real Quebec City WZDx feed is already
> registered, migrated to [`docs/providers/us.md`](us.md#wzdx);
> Singapore doesn't appear at all). Recorded here at the project owner's
> request as named candidates for future work.

Named as worth investigating next, but **not yet scoped, and not yet
checked for a live, accessible endpoint** — unlike every other entry in
[`docs/providers/index.md`](index.md), which only lists a provider once
its API shape has been confirmed one way or another (live-verified,
Credentials-wanted, or Documented-unavailable; see
[`docs/contributing/scaffolds.md`](../contributing/scaffolds.md)).

- **Portugal — partially built, no longer fully pending.** Lisboa
  (Condicionamentos de Trânsito) is now a real, confirmed provider,
  sidestepping the still-credential-parked national IMT National Access
  Point entirely — see [`docs/providers/portugal.md`](portugal.md). Porto
  and other municipalities, and the national NAP itself, remain
  genuinely unchecked/unbuilt.
- **Singapore** — no source investigated at all.
- **Canada — partially built, no longer fully pending.** British
  Columbia (DriveBC, Open511) is now a real, confirmed provider, and
  Quebec City's WZDx feed was already covered — see
  [`docs/providers/canada.md`](canada.md). Ontario 511 was checked live
  (confirmed not to publish WZDx) but not built; other provinces and
  municipal portals (Toronto, Montreal, Vancouver) remain genuinely
  unchecked.

Following this project's own standing pattern (see
[`docs/roadmap.md`](../roadmap.md) and
[`docs/contributing/scaffolds.md`](../contributing/scaffolds.md)), any
of these moves to a real scaffold only once a genuine, checkable
endpoint has been found and its shape confirmed live — not before.
