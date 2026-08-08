# Data model

> Migrated verbatim from README.md's `## Common models` and `## Canonical
> gazetteer model` sections (phase one, lossless restructure — see
> `docs/migration-mapping.md`).

## Works model (`Works`, `WorksSite`, `WorksPlanning`, `Coordinate`)

Every provider has its own native, full-fidelity shape — that's
deliberate, and it never goes away. `streetworks.common` adds canonical
types *alongside* those native interfaces, for code that wants to handle
works data from several providers the same way without caring which one it
came from:

```python
from streetworks.common import from_srwr
from streetworks.srwr import SRWRClient, iter_activities

with SRWRClient() as srwr:
    archive = srwr.download_daily("srwr-daily.zip")
    for activity in iter_activities(archive):
        works = from_srwr(activity)
        for site in works.sites:
            print(site.reference, site.works_type, site.date_confidence, site.raw)
```

A DATEX source needs two more keyword arguments, since a `Situation` can't
state them itself — see below:

```python
from streetworks.common import from_datex2
from streetworks.datex2.dgt import DGTClient, provinces

with DGTClient() as dgt:
    situations = list(dgt.iter_roadworks())
spanish_provinces = provinces(situations)  # {situation.id: "province name", ...}
for situation in situations:
    works = from_datex2(
        situation, territory="Spain",
        administrative_area=spanish_provinces.get(situation.id),
    )
```

`from_datex2` (and `from_wzdx`) take `territory`/`administrative_area` as
keywords rather than deriving them, because neither can be read off a
DATEX `Situation` (or a WZDx `RoadEvent`) alone — the provider sections
in [`docs/providers/`](../providers/index.md) show what each source natively
states — a province, a DIR region, or nothing at all — that you'd pass in.

Two levels, deliberately not three: `Works` is the umbrella (reference,
location, promoter — no committed dates of its own); `WorksSite` is the
dated, actionable unit under it (Street Manager's `-01`/`-02` permits,
SRWR's phases joined to their Undertaker-Phase, DATEX roadworks records all
map here). `WorksPlanning` is a separate type for planning *artifacts* —
PAAs and Street Manager Forward Plans — with indicative rather than
committed dates: a record that is *born* as a planning artifact maps here;
a record that only *transitions* through a planning-ish status (SRWR's
"Advance Planning", DATEX's `validityStatus = planned`) stays a `WorksSite`
with that status exposed, so the same source record never migrates between
canonical types as its lifecycle progresses.

Every canonical object carries a `source_grade` (`register` / `operator` /
`traveller_info`) and `WorksSite` carries a computed `date_confidence`
(`verified` / `estimated` / `unknown`), so consumers can filter by
trustworthiness without provider-specific knowledge — and every one keeps
`.raw` pointing back at its exact source record(s), so converting never
loses anything.

`Coordinate.value` is always one representative point, so every point-only
consumer keeps working unchanged; `Coordinate.points` holds every vertex
when the source geometry is a real line (a WZDx/Street Manager `LineString`,
a DATEX `LinearLocation`/TPEG segment) — `points[0] == value` always. This
used to just collapse to `value` across every converter that had line
geometry available; now it survives.

`Works` also carries location *provenance*, not location *geography*:
`territory` (country-level — UK nations count as countries: `"Scotland"`,
`"England"`, ..., plus `"USA"`, `"Netherlands"`) and `administrative_area`
(the sub-national body that *owns* the data one level down — a UK highway
authority, a US state DOT, a Dutch province, or a national operator's own
name where the operator IS the authority). `administrative_area` is
populated only where a provider genuinely states it, never inferred from a
coordinate, and is consistent *within* one territory but not
size-comparable *across* them — filter by `territory` before aggregating.
`WorksSite.territory`/`.administrative_area` delegate to the parent `Works`,
so a site in hand doesn't need the umbrella held separately. Some
converters (`from_datex2`, `from_wzdx`) can't derive these from the source
record alone — see their docstrings for why — and take them as keyword
arguments instead of guessing.

Converters currently cover SRWR, Street Manager, DATEX II (NDW, National
Highways, Digitraffic/Finland, IRCA/Iceland, Bison Futé/France, DGT/Spain,
Belgium/Flanders, Luxembourg, Bulgaria, and Euskadi/Basque Country (DATEX
II v1.0 — the oldest schema version this converter handles) via the one
shared converter — Belgium's own real, non-WGS84 CRS is passed through
its `crs` parameter, see [DATEX II (European roadworks)](../providers/europe.md#datex-ii-european-roadworks)),
Autobahn GmbH/Germany, Via Lietuva/Lithuania (own real, non-WGS84 CRS —
LKS-94, `EPSG:3346` — and reversed WKT axis order, see
[Via Lietuva (Lithuania)](../providers/europe.md#via-lietuva-lithuania)), German
state roadworks (Hamburg, Brandenburg, Saxony, via the one shared
`from_ogc_features` converter), Consell de Mallorca (its own `from_mallorca`
converter, for the two-layer icon/tram join — see
[Consell de Mallorca (island roadworks)](../providers/europe.md#consell-de-mallorca-island-roadworks)),
Servei Català de Trànsit (its own `from_sct` converter, for the
flat WFS/GML shape — no dates populated, see
[Servei Català de Trànsit (Catalonia)](../providers/europe.md#servei-català-de-trànsit-catalonia)),
WZDx, TrafficWatchNI and Traffic Wales. UK Police stays outside
the works hierarchy entirely — it's a *context* provider (area-level crime as a
safety signal), not a works
provider, and forcing it into a `WorksSite` would misrepresent what it
actually is.

See [`examples/compare_active_works.py`](../../examples/compare_active_works.py)
for this normalisation in practice — active works in a Street Manager
area (default: Durham City) and across Paris's own Chantiers register,
side by side, printed with one shared bit of code working unmodified
across both, despite Street Manager stating an explicit lifecycle status
field and Paris stating none at all (its own "active" is inferred from
the date_debut/date_fin window instead). Honestly not a fair work-count
comparison — a small English city against a major world capital — the
point is the shared canonical shape, not the numbers.

## Never deduplicate across providers

A live-verified real case, not a hypothetical: DGT and Consell de
Mallorca were first documented as "genuinely additive, not a duplicate"
(`docs/idemallorca-investigation.md`'s original framing) — a later audit
(`docs/network-scope-audit.md`) found this wrong. 2 of DGT's Balearic
records match Consell de Mallorca's own records almost exactly on road,
km-range and end-date — the same real works republished in both feeds,
confirmed by checking the actual geometry and dates, not assumed from
either provider's stated remit. DGT itself turned out to reach several
other Spanish regional/provincial/insular road authorities' works too,
not just its own state network (see [DGT](../providers/europe.md#datex-ii-european-roadworks))
— so a territory carrying both a `strategic`/`multi_authority
_interurban` provider and a `regional`/`comprehensive` one for the same
area (Spain: DGT + Consell de Mallorca; England: National Highways +
Street Manager) should be expected to overlap at the edges, not treated
as two disjoint slices that sum to the whole.

**This SDK never deduplicates near-identical works across providers, and
never will without a shared, verified reference id.** The same lesson
already learned one level down, inside a single provider —
[`examples/collaboration_finder.py`](../../examples/collaboration_finder.py)
deliberately excludes pairs sharing one Street Manager
`work_reference_number`, because matching on place-and-date alone would
wrongly treat a permit and its own amendment as two separate works — the
cross-provider case is the same risk, one level up: matching two
providers' records on place-and-date alone would just as wrongly merge
two authorities' legitimate, independently-issued permits into one,
losing whichever provider's record didn't win the merge. A permit is
issued *per authority*, not per physical worksite, so two records for
what looks like the same location can both be correct — collapsing them
on a look-alike heuristic is a bug users would only find months later,
which is worse than showing an occasional duplicate plainly. If
aggregation across providers is ever built, it must preserve every
source record with its own provenance, never dedupe, and flag likely
duplicates for a human to judge rather than resolving automatically.

## Canonical gazetteer model (`Street`, `Segment`, `Address`)

The gazetteer equivalent of the works model above — canonical types for the
eight street/address providers (`datavia`, `openusrn`, `bdtopo`, `nvdb`,
`nwb`, `ban`, `bag`, `kartverket`), designed *after* those native adapters,
from their real shapes, the same way `Works`/`WorksSite` was at 0.5.0. Same
rule: additive only, never replacing the native interfaces, `.raw` always
points back at the source.

```python
from streetworks.common import from_bdtopo
from streetworks.bdtopo.models import troncon_from_feature

troncon = troncon_from_feature(feature)  # one WFS feature
segment = from_bdtopo(troncon)
print(segment.names[0].value, segment.street_refs, segment.geometry.crs)
```

**Three types, not two.** `Segment` is independent, not a child list of
`Street` — real data proves the relationship is many-to-many, not
one-to-many: a real DataVIA ESU (`esuid` `4276210541888`, Durham) belongs to
*two* distinct designated streets at once (`usrns="11713562;11713561"` —
Church Street and Church Street Villas), and NVDB's real "Dalveien" address
spans two topologically-unrelated `veglenkesekvenser`. Containment would
misstate both, so `Segment.street_refs` and `Street.segment_refs` are both
plural lists of `Identifier`, resolved by the caller, never nested.

**The trim test.** This model serves exactly three use cases — plotting
streets on a map, linking streets to roadworks, and pulling street names
from address gazetteers — and no more; anything more complex is expected to
use the native interfaces directly (see [`docs/providers/`](../providers/index.md)).
A field only exists here if it serves one of those three, *or* a source states it
and dropping it would lose real data (this project's evidence discipline
never drops stated data) — where those conflict, the field stays and is
marked optional.

**No synthetic streets.** A `Street` is only ever emitted by a provider
that publishes a street entity — never derived by grouping addresses or
segments. Consequence, stated plainly: `from_nwb` emits **no `Street` at
all** — NWB publishes segments with a `bag_orl` reference, and this SDK's
only built BAG route (the light GeoPackage) has no street row of its own to
be a `Street` (only the not-built full XML extract does). So Dutch street
names reach this model only via `Address.street_name`, never a Dutch
`Street` — a real gap with a real fix waiting, not a design flaw.

`Identifier.scope` matters because most European street/address
identifiers are *municipality-scoped*, not nationally unique — BAN's
derived `toponyme_id` splits at commune boundaries, and Kartverket's real
`adressekode` reuses the same numeric code for unrelated streets in
different kommuner (confirmed live: "Karl Johans gate 1" resolves to three
different real addresses across three municipalities, each its own
`adressekode` — 15100/13630/3620). An unscoped identifier is a trap;
`scope` is what makes comparing two `Identifier`s safe.

Some fields are stated by only one provider so far — `Segment.names` (NWB's
`stt_naam` too, in practice, despite this being written up during design as
a BD-TOPO-only field — see `from_nwb`'s docstring) and
`Segment.address_ranges` (NWB's six real house-number-range fields) are the
weakest, single-source points in this model; kept because stated data is
never dropped, not because they're load-bearing everywhere.

`WorksSite.street_ref` (an `Identifier`, singular) is this model's
connection back to the works side: Street Manager states a USRN per permit
row, so `from_streetmanager` populates it directly. SRWR was checked, not
assumed — it states street identity too (record type `004`), but at the
*activity* level, with no field joining a given street to a given phase, so
`from_srwr` deliberately leaves `street_ref` `None` rather than
guessing which of possibly several real streets a phase belongs to.

Two additions to `Coordinate`, both additive: every point may be a 2-tuple
or a 3-tuple (`(x, y)` or `(x, y, z)`) — Z survives where a source states it
(NVDB's real `LINESTRING Z` under EPSG:5973, a compound 3D CRS), never
defaulted to 0 where it's absent — and a new `parts` field holds a real
`MultiLineString`'s other lines (DataVIA's `StreetLines`: one street
aggregating several ESUs' geometry) — `value`/`points` still describe the
first part alone, so every existing point/line consumer keeps working
unchanged.

Out of scope, deliberately: linear referencing/extents (NVDB's fractional
`startposisjon`/`sluttposisjon` is the only real candidate, and even it
isn't modelled here), sub-name street extents (investigated and closed —
DataVIA's own ESU schema has no name field at all, so a real local name
like "Anchorage Terrace" for part of Church Street, Durham, isn't
recoverable from this source at any level), a `unit`/flat concept (no
built source has one — addresses use `housenumber`+`suffix`, e.g. BAN's
real `numero`+`suffixe` decomposition, `4`+`"bis"`), and reprojection
(CRS is always labelled as given, varying by *route* as well as provider —
BD TOPO's WFS states WGS84, its bulk GeoPackage is documented, not
independently confirmed, as Lambert-93).
