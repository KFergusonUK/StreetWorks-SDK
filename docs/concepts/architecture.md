# Architecture

> Migrated from README.md's `## What this is (and isn't)` and
> `## Design principles` sections (verbatim), plus a real, recurring
> "build bespoke, extract shared code only on the second real consumer"
> pattern collected from several provider write-ups (phase one, lossless
> restructure — see `docs/migration-mapping.md`).

## What this is (and isn't)

**It is** a typed client library: it handles authentication, token lifecycles,
retries, rate limiting, pagination, and request/response plumbing for each of
these APIs, so you call Python methods instead of hand-rolling HTTP. Auth and
connectivity are verified against the real systems (see
[`docs/providers/index.md`](../providers/index.md) — Status).

**It isn't** a replacement for the APIs' own documentation. You still bring
your own credentials (issued by the service operators, not by this SDK) and
you still need each API's domain concepts — what a permit payload contains,
what makes a valid USRN filter, which DataVIA layer holds which data. The SDK
gets you connected and typed; the linked docs tell you what to send.

Shared across all modules: automatic retries with exponential backoff and
jitter, `Retry-After`-aware 429 handling, and a single exception hierarchy,
all built on [httpx](https://www.python-httpx.org/). **Async is per-module,
not universal** — checked directly against the source, not assumed: Street
Manager, DataVIA, D-TRO, SRWR, OS Open USRN, BAN, Kartverket, NVDB, NWB and
BD TOPO each ship an `Async<Name>Client` mirror; BAG, DATEX II (all of NDW/
National Highways/Digitraffic/IRCA/Bison Futé/DGT/Belgium/Luxembourg/Bulgaria/
Euskadi/Vegvesen/Trafikverket/Vejdirektoratet),
Autobahn GmbH, Via Lietuva, Consell de Mallorca, Servei Català de Trànsit,
the German state roadworks client, WZDx, TrafficWatchNI, Traffic Wales, UK
Police, and the ArcGIS-based providers (Jersey, TIGERweb) are sync-only
today. Check a given module for an `Async*Client` before assuming one
exists.

## Design principles

1. **Never block the user.** Typed methods for confirmed, common endpoints;
   generic `get/post/put/delete` on every API group for everything else.
2. **Be a good API citizen.** Token reuse, refresh-then-reauth, exponential
   backoff, honoured `Retry-After` — per the DfT integration guidance.
3. **Test without credentials, verify with them.** The whole unit suite runs
   against mocked transports (`respx`) so CI needs no secrets; a separate
   smoke test and skip-guarded integration suite verify against the real
   systems when you supply credentials.
4. **Room to grow.** Each provider is a self-contained module over a shared
   transport/exception core — adding a new API is additive.

## Shared clients: built bespoke, extracted on the second real consumer

A recurring, real pattern across this codebase's history, not a stated
abstract rule but a demonstrated one — collected here from several
provider write-ups (full context in [`docs/providers/`](../providers/index.md)):

- **`streetworks.socrata`** (`SodaClient`) — *"a new shared Socrata (SODA) client, factored out of `streetworks.wzdx.registry` when [NYC DOT] needed the identical GET-with-query-params-and-paginate shape — the same role `streetworks.arcgis`/`streetworks.ogc` play for their own technologies."* Chicago CDOT and Paris Chantiers were each evaluated against it in turn: Chicago *"reuses `streetworks.socrata`... directly"*; Paris, on a genuinely different platform (OpenDataSoft, not Socrata), was built bespoke instead — *"No shared `streetworks.opendatasoft` client was extracted for it: built bespoke inside `streetworks.paris`, the same sequence that produced `streetworks.socrata`'s `SodaClient` (bespoke first, shared only once a second same-platform provider needs the identical shape)."*
- **`streetworks.ogc`** (`OGCFeaturesClient`) — a generic OGC-features GeoJSON client, first built for the German state roadworks cluster (`streetworks.ogc.germany`, a declarative per-state field-map registry reading it), then reused unchanged for Consell de Mallorca — *"reusing the same `OGCFeaturesClient` the German states use."* Declared **new infrastructure in 0.7.0** and its interface **provisional** — built deliberately generic so the future gazetteer work can reuse it, which may reshape it in 0.8.0.
- **`streetworks.arcgis`** (`ArcGISFeatureClient`) — the third client shape in the SDK, after the DATEX/JSON adapters and `OGCFeaturesClient`. *"Built fresh for this protocol, not a generalisation of `OGCFeaturesClient` or `DataViaClient` — they share almost nothing but 'fetches geodata over HTTP.'"* First proven against Jersey RoadWorkx and TIGERweb (where it had to solve a real pagination-truncation trap, not just a quick fetch — see [`docs/providers/uk.md`](../providers/uk.md)), then reused unchanged by Main Roads WA, QLDTraffic, Traffic SA, ACT, Tasmania, NZTA, and G-NAF/National Roads (see [`docs/providers/australia.md`](../providers/australia.md) and [`docs/providers/new-zealand.md`](../providers/new-zealand.md)).

## Provider discovery layer

See [`docs/providers/index.md`](../providers/index.md) for
`streetworks.providers()`/`get_provider()` — the "what covers X" /
"give me Y's client" discovery API, and the full per-module coverage
table.
