# Network-scope audit — every roadworks provider

Report only, per the brief — no build. Every classification below is
checked against the adapter's own module docstring (itself already
live-verified during that provider's build, in most cases) or a fresh
live pull done for this audit specifically. Confidence is stated
per-provider; nothing is asserted from memory alone.

## Headline findings — read these first

**1. DGT (Spain) is not "strategic" the way it looks — it's a
multi-authority aggregator, and it genuinely overlaps with Consell de
Mallorca.** A fresh live pull shows DGT's road-number prefixes are
**not** limited to the state network (`A-`/`N-`/`AP-`, 205 of 391 real
records) — real regional/provincial/insular prefixes appear too: `CV-`
(Comunidad Valenciana's own regional network, 16 records across
València/Castelló/Alacant), `M-` (Madrid's regional network, 15),
`RM-`/`EX-`/`TF-` (Murcia/Extremadura/Tenerife regional, 8 each), and —
the important one — **`Ma-`/`Me-` (Consell de Mallorca's and Consell
Insular de Menorca's own island road numbering, 5 records)**. DGT is
Spain's national *driver-information* aggregator across ~15
autonomous-community/provincial/insular road authorities (everyone
except Catalonia and the Basque Country, which run fully independent
systems), not simply "the roads DGT itself owns."

Two of DGT's five real `Illes Balears` records were cross-checked
directly against a fresh Consell de Mallorca pull and matched almost
exactly on road, kilometre range, and validity dates:

| DGT (situation id) | Road | DGT end date | Consell de Mallorca (codi) | Consell end date |
|---|---|---|---|---|
| `17500114` | Ma-1 | 2026-08-30 12:00 | `19128` | 2026-08-30 12:00 |
| `18801036` | Ma-15 | 2027-02-22 18:00 | `19528` | 2027-02-22 23:59 |

This is the **same real-world incident published in both feeds** —
genuine duplication for at least these two, not the "genuinely additive,
not a duplicate" picture `docs/idemallorca-investigation.md` and the
Mallorca README section currently state. That framing needs revising: DGT
and Consell de Mallorca are *mostly* complementary (DGT: state + most
other Spanish road authorities' works; Consell: Mallorca's own island
network, in far more detail — 16-17 current records vs. DGT's ~5 for the
whole island) but a small, real subset of significant Mallorca works get
mirrored into DGT's feed too, presumably because they're judged
driver-information-relevant nationally. **Recommended follow-up (not done
here — this is a report): update the "genuinely additive, not a
duplicate" language in the investigation doc and README to "mostly
additive, with confirmed partial overlap for higher-impact works."**

**2. TrafficWatchNI has an explicit two-tier scope in one feed.** Already
documented in the client's own docstring, not newly discovered: "trunk
roads and motorways NI-wide, plus all roads in Greater Belfast." This is
genuinely two different scopes bundled into one provider depending on
which of its two feed variants (`NORTHERN_IRELAND`/`BELFAST`) is queried
— strategic NI-wide, comprehensive within Belfast specifically.

**3. Saxony is not like its Hamburg/Brandenburg siblings.** Already
documented in `streetworks/ogc/germany.py`'s own docstring: Saxony
"aggregat[es] district and municipal roadworks alongside state roads, not
state-roads-only like Hamburg/Brandenburg." Same `kind`/`_module`
grouping in the registry today, genuinely different scope underneath.

## Summary table

| Provider | Territory | Kind (current) | Network scope (proposed) | Narrower than territory implies? | Confidence |
|---|---|---|---|---|---|
| `streetmanager` | England | roadworks | `comprehensive` | No | Documented (statutory NRSWA 1991 register; real sandbox data shows utility/Section 50/58 activity types alongside the highway authority's own, though the sandbox itself only contains one real authority) |
| `opendata` | England | roadworks | `comprehensive` (inherited) | No | Documented — explicitly "same coverage as Street Manager itself" |
| `dtro` | England, Wales | roadworks | `not_applicable` | N/A | A legal-orders register, not a works-progress feed — "network scope" doesn't map the same way; noted, not classified |
| `srwr` | Scotland | roadworks | `comprehensive` | No | Live-confirmed: 95 distinct `promoter_district_id` values across 845 real current activities (one day's extract) — genuine multi-organisation diversity, consistent with its statutory design (Scotland's equivalent of Street Manager under the Roads (Scotland) Act 1984) |
| `trafficwatchni` | Northern Ireland | roadworks | `strategic` **+** `comprehensive` (area-dependent) | **Yes, if only the NI-wide feed is used** | Documented in the client's own docstring — see Headline Finding 2 |
| `trafficwales` | Wales | roadworks | `strategic` | **Yes** | Documented: "motorway and trunk roads only" |
| `nationalhighways` | England | roadworks | `strategic` | **Yes** | Documented: "The Strategic Road Network (SRN) only - not local roads" |
| `jersey` | Jersey | roadworks | `comprehensive` | No | Live-confirmed: 293 distinct promoters (utilities — Jersey Electricity/Telecom/Water — plus government road/drainage teams plus non-utility promoters like a cycling club and a hospice charity) across all 12 parishes (`Authority` values `GHA` + `PSH`/`PSS`/`PSB`/... parish codes), 22,205 real records |
| `ndw` | Netherlands | roadworks | `comprehensive` | No | Live-confirmed: real `source_name` values span `Gemeente` (municipality — Utrecht, Eindhoven, Leiden, The Hague, ...), `Provincie` (province), and `RWS` (national) district offices in one 3,000-record sample — genuine three-tier aggregation |
| `dgt` | Spain | roadworks | `multi_authority_interurban` (new category) | **Yes, but not the way expected** — see Headline Finding 1 | Live-confirmed: state (`A-`/`N-`/`AP-`) + ~10 regional/provincial/insular prefixes; zero municipal-street-style entries in any real record checked |
| `mallorca` | Spain | roadworks | `regional` (insular) | No (its own network is the point) | Live-confirmed: 205 island roads, `Ma-`/numbered network; not independently confirmed whether Palma's own municipal streets are included or excluded (no per-record authority-tier field to check) |
| `bisonfute` | France | roadworks | `strategic` | **Yes** | Documented: "the non-concessionary national road network (the state-run RRN) only - private autoroute concessionaires publish separately" (and by extension, departmental/communal roads are also out of scope) |
| `belgium` | Belgium | roadworks | `regional` | **Yes** | Documented (Flanders only, confirmed via `nationalIdentifier="BETICV"`); not independently confirmed whether Flemish municipal streets are included (no source/road-authority field on any real record — a documented "honest gap") |
| `luxembourg` | Luxembourg | roadworks | `strategic` | **Yes** | Documented: "the national road network only, as published by Ponts et Chaussées" |
| `bulgaria` | Bulgaria | roadworks | `strategic` | **Yes** | Documented: "the 'Republican Road Network' (the national road network under the Road Infrastructure Agency's own administration)" |
| `vialietuva` | Lithuania | roadworks | `strategic` | **Yes** | Documented: dataset name itself is "Eismo ribojimai valstybinės reikšmės keliuose" - "traffic restrictions on **state-significance** roads" |
| `autobahn` | Germany | roadworks | `motorway` | **Yes** | Documented: "National motorways only - state/regional roads are separate" |
| `hamburg` | Germany | roadworks | `strategic` (regional) | **Yes** | Documented: Hamburg's own state road authority (BWVM), not confirmed to include Hamburg's municipal streets |
| `brandenburg` | Germany | roadworks | `strategic` (regional) | **Yes** | Documented: Brandenburg's own state road agency (Landesbetrieb Straßenwesen) |
| `saxony` | Germany | roadworks | `comprehensive` (regional) | No (broadest of the three German states) | Documented — see Headline Finding 3; genuinely aggregates state+district+municipal, but only within Saxony |
| `digitraffic` | Finland | roadworks | `strategic` | **Yes** | Live-confirmed: every real road identifier checked is a numbered national route (`79`, `661`, `8`, `9`, `74`, `12248`, ...), no municipal street names seen |
| `irca` | Iceland | roadworks | `strategic` | **Yes** | Live-confirmed: real comments reference only numbered national routes (Hringvegur/Route 1, Snæfellsnesvegur/54, Stykkishólmursvegur/58); Reykjavík's own municipal streets are a separate authority, not seen in any real record |
| `wzdx` | USA | roadworks | `varies_by_feed` (new category) | N/A - not one provider | Documented: "not one provider's coverage - a schema ~40+ agencies publish independently" - individual feeds range from a single city DOT (comprehensive-locally) to a state DOT (strategic); no single value applies |
| `vegvesen` | Norway | roadworks | `unknown` | Unknown | Explicitly flagged in its own module docstring as "PENDING LIVE VERIFICATION" - never run against real Norwegian data, Phase 1 scaffold only |

## Multi-provider territories — the relationships the registry should show

- **Spain**: `dgt` (multi-authority interurban, excl. Catalonia/Basque
  Country) + `mallorca` (Mallorca's own island network, richer detail,
  confirmed partial overlap with `dgt` for higher-impact works — see
  Headline Finding 1). Not a clean layering the way England's pair is;
  more like "DGT is broad-and-shallow across most of Spain's road
  authorities, Mallorca is narrow-and-deep for one of them."
- **England**: `streetmanager` (comprehensive, all promoters/roads,
  statutory) + `nationalhighways` (strategic, SRN only) — genuinely
  complementary, National Highways' own works should also appear in
  Street Manager (SRN promoters are notifiable authorities too), so this
  is closer to "one is a subset view of the other" than two disjoint
  networks. Not independently confirmed here (would need a live
  cross-reference by road/reference number, out of scope for this pass).
- **Northern Ireland**: `trafficwatchni` alone, but internally two-tier
  (see Headline Finding 2) — worth the registry showing this as one
  provider with an area-dependent scope, not two providers.
- **Germany**: `autobahn` (motorway only, national) + `hamburg`/
  `brandenburg`/`saxony` (regional, each a different sub-tier) — a clean
  national/regional layering, already documented as such in
  `streetworks/ogc/germany.py`.
- **Wales**: `trafficwales` (strategic, motorway/trunk only) - no
  comprehensive Welsh equivalent to Street Manager/SRWR in this SDK
  currently (D-TRO covers Wales too, but it's a legal-orders register,
  not a works-progress feed - not the same thing).

## Proposed registry field

```python
class NetworkScope(str, Enum):
    """What tier of the road network a roadworks provider's real data
    actually reaches - checked against real records, never assumed from
    a provider's stated remit alone (DGT's real data reaches several
    regional/insular networks beyond its own, not just the state network
    its name implies - see docs/network-scope-audit.md)."""

    COMPREHENSIVE = "comprehensive"                  #: all roads, all promoters (Street Manager, SRWR, Jersey)
    MULTI_AUTHORITY_INTERURBAN = "multi_authority_interurban"  #: several road authorities' interurban networks aggregated, no municipal streets (DGT)
    STRATEGIC = "strategic"                           #: one national/state road authority's own network only (National Highways, Bison Futé, Autobahn's siblings)
    MOTORWAY = "motorway"                             #: motorways only, a stricter subset of strategic (Autobahn)
    REGIONAL = "regional"                             #: one sub-national authority's own network (Belgium/Flanders, Consell de Mallorca)
    VARIES_BY_FEED = "varies_by_feed"                 #: a multi-agency schema, not one provider's coverage (WZDx)
    NOT_APPLICABLE = "not_applicable"                 #: not a works-progress register at all (D-TRO)
    UNKNOWN = "unknown"                               #: never verified against real data (Vegvesen)
```

Kept deliberately smaller than the full nine-way split the table above
implies — `TrafficWatchNI`'s and Saxony's genuine two-tier/hybrid scopes
don't need their own enum values; they're exactly what the existing
`scope_note` free-text field is for (already present on `ProviderEntry`,
already carrying comparable nuance for several providers). Proposed
addition to `ProviderEntry`:

```python
network_scope: NetworkScope = NetworkScope.UNKNOWN
```

Defaulting to `UNKNOWN` rather than a guessed value means a provider
nobody has audited yet reads as genuinely unaudited, not silently
"comprehensive" — the same "unknown is a valid, honest answer" discipline
this SDK already applies to the NAP survey and the IDEmallorca licence
question.

## Recommendation

**All three done as a follow-up wiring pass** (see the CHANGELOG's
`[Unreleased]` entry and the README's
[Never deduplicate across providers](#never-deduplicate-across-providers)
section - this file is left as the original audit record, not updated in
place):

1. ~~Wire `network_scope` into the registry~~ - done: a `NetworkScope`
   enum plus a `network_scope` field on every `ProviderEntry`.
2. ~~Fix the DGT/Mallorca "genuinely additive, not a duplicate" claim~~ -
   done, and sharpened first: characterising the overlap directly (not
   just re-measuring it) found it's **republication** of the same real
   works (matched geometry sits within, not beside, the same work-zone
   span; no independent reference field exists on DGT's side to attribute
   it otherwise), not a jurisdiction-boundary case, and Consell de
   Mallorca is **not** a confirmed strict superset of DGT's Balearic
   entries either (2 of 4 distinct DGT Mallorca-area situations had no
   live match at check time - likely data lag, not conclusively
   resolved). Corrected everywhere the original claim shipped, stated
   plainly rather than quietly edited.
3. ~~Surface `network_scope` in `providers()`'s own rendering~~ - done,
   shown as a `Network scope:` line alongside the existing `Scope:` text.
