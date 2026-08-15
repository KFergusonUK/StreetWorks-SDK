# Scaffold states

> Cross-reference summary — the full content this summarises is migrated
> verbatim into [`docs/providers/index.md`](../providers/index.md)'s
> `### Credentials wanted` section (phase one, lossless restructure — see
> `docs/migration-mapping.md`). Not duplicated here in full since it's a
> large pair of tables; this page exists so "how do scaffolds work in
> this project" has a findable home under `contributing/`.

Two distinct scaffold states, per README.md's `### Credentials wanted`
section:

1. **Credentials wanted** — built to the service's own documented/
   confirmed API shape, covered by mocked tests, but never run against a
   real authenticated response, because the project genuinely doesn't
   have the access to try. Six providers currently in this state:
   Trafikverket (Sweden), Vejdirektoratet (Denmark), ASFINAG (Austria),
   Traffic SA (South Australia), LINZ NZ Addresses: Roads/Road Sections,
   and Stockholm (Sweden). See
   [`docs/providers/index.md#credentials-wanted`](../providers/index.md#credentials-wanted)
   for the full per-provider table (what's confirmed, what's pending,
   which credential, how to get it).

2. **Documented, unavailable** — genuinely no working interface exists at
   all, not a credential gate: Road Report NT (Northern Territory — a
   reverse-engineered SignalR hub, not a REST/GeoJSON API), MapRoad
   Roadworks Licensing (Ireland — a real API, but gated behind a formal
   GDPR data-sharing arrangement, not a self-service key), and Greece (no
   roadworks dataset exists on the national NAP at all, and the portal is
   currently down). See
   [`docs/providers/index.md#credentials-wanted`](../providers/index.md#credentials-wanted)
   for the second table covering these three.

**The standing contribution pattern**: if you have access to any
Credentials-wanted provider, running `python scripts/smoke_test.py` and
reporting back — ideally with one real trimmed record — is a genuinely
valuable contribution, the same way a tester's real credentials confirmed
Norway/NSW/Victoria on 2026-07-30 (see
[`docs/providers/index.md#recently-confirmed`](../providers/index.md#recently-confirmed)
for the record of what changed when that happened). Every roadworks
module also warns at import time (`UserWarning`) with the same pointer.
Drafted issue text for each scaffold lives in
[docs/credentials-wanted-issues.md](../credentials-wanted-issues.md).
