# Provider coverage matrix

A compact, per-territory view of SDK coverage — complementary to the detailed
[module table](index.md), not a replacement for it. Every cell was checked
directly against the live registry (`streetworks.providers()`) on 2026-08-26,
not transcribed from an earlier snapshot — see "How this was built" at the
bottom for the exact method, including the judgement calls that needed more
than a flat registry lookup (WZDx's per-feed `needapikey` flag, the North
American 511 platform's per-jurisdiction verification tier, and Germany's/
France's own national-motorway-network baseline).

## Legend

| Symbol | Meaning |
|---|---|
| `X` | Complete, or as complete as the available APIs allow |
| `~` | Partial coverage, or a real source exists but is waiting on credentials |
| `o` | No real coverage found |

`TTRO`/`NUAR`/`Other` are effectively UK-only today (D-TRO, the NUAR
reference model, UK Police/DataVIA) — `o` elsewhere reflects that, not a
gap in the search.

## Territory-level matrix

| Territory | Roadworks | Street Gazetteer | TTRO | NUAR | Other | Notes |
|---|---|---|---|---|---|---|
| **United Kingdom** | | | | | | |
| England | X | X | X | ~ | X | Street Manager + TfL; OS Open USRN + DataVIA NSG; D-TRO; NUAR (model only, not a live connector); UK Police |
| Scotland | X | X | o | o | **o** | SRWR (national register) + OS Open USRN. UK Police's own real coverage is `{England, Northern Ireland, Wales}` — Scotland genuinely isn't in it |
| Wales | ~ | X | **X** | ~ | X | Traffic Wales (trunk/motorway feed, not a full register) + OS Open USRN. D-TRO's own real territories are `{England, Wales}` — Wales is genuinely covered, not just England |
| Northern Ireland | ~ | X | o | o | X | TrafficWatchNI (traffic feed, not a full register); OSNI streetnames + DfI Roads centreline; UK Police covers NI |
| **Crown Dependencies** | | | | | | |
| Jersey | X | X | o | o | o | RoadWorkx (national register) + Jersey Street Gazetteer |
| Guernsey | o | X | o | o | o | Guernsey Street Gazetteer only — no roadworks feed found |
| Isle of Man | o | **o** | o | o | o | No Isle of Man provider of any kind exists in the SDK today — not even a street gazetteer |
| **Europe** | | | | | | |
| Ireland | o | ~ | o | o | o | MapRoad exists as a real statutory register but has no accessible technical read path anywhere (gated data-sharing arrangement, `ProviderUnavailableError` always raised) — genuinely `o`, not merely credentials-wanted. Monaghan is one county only → partial gazetteer |
| Germany | ~ | ~ | o | o | o | Autobahn (national motorways) complete; state-level roadworks is a growing patchwork — see the [state-by-state table](#germany-state-by-state) below |
| France | X | X | o | o | o | Bison Futé national DATEX + several département/métropole feeds; BAN + BD TOPO national gazetteers — see the [région-by-région table](#france-région-by-région) below |
| Spain | X | X | o | o | o | DGT national (Catalonia/Basque Country gaps filled via SCT/Euskadi) + Mallorca + Madrid; IDEE Transportes national road network |
| Portugal | X | ~ | o | o | o | Infraestruturas de Portugal national Condicionamentos; gazetteer is Lisbon only |
| Netherlands | X | X | o | o | o | NDW national DATEX + Amsterdam; BAG + NWB national gazetteers |
| Austria | ~ | X | o | o | o | Vienna only live; national ASFINAG still credentials-wanted; BEV national address register |
| Switzerland | ~ | X | o | o | o | Canton + City of Zürich only; swisstopo federal street register |
| Denmark | ~ | X | o | o | o | Copenhagen only live; national Vejdirektoratet still credentials-wanted; DAR national register |
| Sweden | ~ | o | o | o | o | Trafikverket + Stockholm both credentials-wanted, no live feed yet |
| Finland | X | X | o | o | o | Digitraffic national DATEX; Digiroad national network |
| Norway | X | X | o | o | o | Statens vegvesen national (verified); Kartverket addresses + NVDB national network |
| Bulgaria | X | o | o | o | o | LIMA/Road Infrastructure Agency national DATEX |
| Romania | X | o | o | o | o | CNAIR national dispatch board (HTML-scraped) |
| Belgium | ~ | ~ | o | o | o | Flanders DATEX + Brussels only (Wallonia credential-gated); Straatnamenregister is Flanders only |
| Luxembourg | X | X | o | o | o | Ponts et Chaussées national DATEX; CACLR national street register |
| Italy | X | X | o | o | o | CCISS national RSS + Roma + Milano; ANNCSU national street register |
| Poland | X | o | o | o | o | GDDKiA national roads/motorways |
| Lithuania | X | X | o | o | o | Via Lietuva national roadworks; Registrų centras national centrelines |
| Iceland | X | X | o | o | o | IRCA/Vegagerðin national DATEX; Landmælingar Íslands national network |
| Greece | o | ~ | o | o | o | National roadworks confirmed unavailable (no Situation dataset exists at all); gazetteer is one of 580 municipalities |
| Gibraltar | o | X | o | o | o | Street gazetteer covers the whole territory; no roadworks feed found |
| Croatia | **X** | o | o | o | o | Hrvatske ceste DATEX v3 — graduated to verified 2026-08-26 (85 real `MaintenanceWorks` situations round-tripped through the shared parser) |
| **Oceania** | | | | | | |
| Australia | X | X | o | o | o | No national register exists; 7 of 8 states/territories live, SA still credentials-wanted; G-NAF + National Roads national gazetteers |
| New Zealand | X | **~** | o | o | o | NZTA national state highways (verified); LINZ Addresses is verified, but the separate LINZ Roads/Road Sections register is still credentials-wanted (a real LDS API key) |
| **North America** | | | | | | |
| USA | X | X | o | o | o | Federated, not national — see the [state-by-state table](#united-states-state-by-state) below |
| Canada | ~ | X | o | o | o | No national register; several provinces live, several still credentials-wanted — see the [province-by-province table](#canada-province-by-province) below |
| **Asia** | | | | | | |
| Hong Kong | X | o | o | o | o | Highways Department strategic-network roadworks, genuinely keyless — everything Transport Department publishes |
| South Korea | ~ | o | o | o | o | Korea Expressway Corporation — credentials-wanted scaffold, least-confirmed in the SDK (real pull URL unknown until registration) |
| Singapore | ~ | o | o | o | o | LTA DataMall — credentials-wanted scaffold |

## United States, state-by-state

Street Gazetteer is `X` for every state via TIGERweb's national coverage
(US Census Bureau) and isn't repeated per row. Roadworks coverage comes from
three independent mechanisms that can overlap: the generic **WZDx** registry
(41 cataloged feeds, each separately flagged keyless or key-gated), the
**North American 511 platform** (na511 — one shared client, verified
per-jurisdiction), and standalone **city/state permit registers** (NYC DOT,
Chicago CDOT, DC DDOT).

A state is `X` if *any* of those mechanisms gives it real keyless (or
already-verified) coverage — a 511 deployment sitting unverified doesn't
drag a state down to `~` if a keyless WZDx feed independently covers it, and
vice versa. This is the real correction this table makes to an earlier
draft: several states were marked `X` on the strength of a WZDx feed alone
without checking that feed's own `needapikey` flag — Colorado, Massachusetts,
Michigan, Oregon, Pennsylvania and Virginia all have real *cataloged* WZDx
feeds, but every one of them needs a developer key this SDK doesn't hold, and
no alternate keyless source exists for any of the six — so they're `~`, not
`X`. Conversely, Delaware, Kansas and Mississippi each have a real, genuinely
keyless WZDx feed that an earlier pass missed entirely — corrected to `X`.

| State | Roadworks | Notes |
|---|---|---|
| Alabama | ~ | Investigated, genuinely unresolved rather than ruled out |
| Alaska | X | Alaska 511 — verified live |
| Arizona | X | Arizona 511 — verified live |
| Arkansas | o | No source found |
| California | ~ | Regional WZDx only (Bay Area MTC, key-gated); no statewide coverage |
| Colorado | **~** | WZDx feed cataloged but key-gated; no key held |
| Connecticut | X | Connecticut 511 — verified live |
| Delaware | **X** | Real keyless WZDx feed (Delaware DOT) |
| Florida | X | Florida DOT WZDx (keyless) |
| Georgia | X | Georgia 511 — verified live |
| Hawaii | X | Hawaii DOT WZDx (keyless) |
| Idaho | X | Idaho 511 — verified live |
| Illinois | X | Chicago CDOT permit register (verified, keyless) — the state DOT's own WZDx feed is key-gated |
| Indiana | X | Indiana DOT WZDx (keyless) |
| Iowa | X | Iowa DOT WZDx (keyless) |
| Kansas | **X** | Real keyless WZDx feed (Kansas DOT) |
| Kentucky | X | Kentucky Transportation Cabinet WZDx (keyless) |
| Louisiana | X | Louisiana DOTD WZDx (keyless) — the separate Louisiana 511 is still credentials-wanted |
| Maine | X | New England 511 platform WZDx feed (keyless) + New England Compass |
| Maryland | X | Maryland DOT WZDx (keyless) |
| Massachusetts | **~** | CWZ 1.0 support was built for MassDOT's feed, but it still needs a real key nobody's obtained yet |
| Michigan | **~** | WZDx feed cataloged but key-gated; no key held |
| Minnesota | X | Minnesota DOT WZDx (keyless) |
| Mississippi | **X** | Real keyless WZDx feed (Mississippi DOT) |
| Missouri | X | Two real keyless WZDx feeds (Missouri DOT + St. Charles County) |
| Montana | o | No source found |
| Nebraska | o | No source found |
| Nevada | X | Nevada 511 — verified live |
| New Hampshire | X | New England 511 platform WZDx feed (keyless) + New England Compass |
| New Jersey | ~ | Real WZDx feed cataloged (keyless); na511 separately WAF-blocked from this build environment |
| New Mexico | X | New Mexico DOT WZDx (keyless) |
| New York | X | New York DOT WZDx (keyless) + NYC DOT permit register (verified) — the separate New York 511 is still credentials-wanted |
| North Carolina | X | North Carolina DOT WZDx (keyless) — the separate North Carolina 511 is still credentials-wanted |
| North Dakota | o | A real lead found, not yet built |
| Ohio | **~** | Real WZDx feed cataloged (Ohio DOT), but key-gated |
| Oklahoma | X | Oklahoma DOT WZDx (keyless) |
| Oregon | **~** | WZDx feed cataloged but key-gated; no key held |
| Pennsylvania | **~** | Both the Turnpike's WZDx feed and Pennsylvania 511 are key-gated; no alternate keyless source found |
| Rhode Island | o | No source found |
| South Carolina | o | A real lead found, not yet built |
| South Dakota | o | No source found |
| Tennessee | o | A real lead found, not yet built |
| Texas | X | City of Austin WZDx (keyless) — TxDOT's own statewide feed is key-gated |
| Utah | X | Utah DOT WZDx (keyless) |
| Vermont | X | New England 511 platform WZDx feed (keyless) + New England Compass |
| Virginia | **~** | WZDx feed cataloged but key-gated; no key held |
| Washington | X | Washington State DOT WZDx (keyless) — this SDK's canonical WZDx example feed |
| West Virginia | o | No source found |
| Wisconsin | ~ | Real WZDx feed cataloged (keyless — confirmed against the raw catalog); na511 separately blocked by a firewall |
| Wyoming | o | No source found |

## Canada, province-by-province

Street Gazetteer is `X` everywhere via the National Road Network's
countrywide coverage and isn't repeated per row.

| Province/Territory | Roadworks | Notes |
|---|---|---|
| Alberta | X | 511 Alberta — verified live |
| British Columbia | X | DriveBC + Vancouver Road Ahead — both verified live |
| Manitoba | o | No source found |
| New Brunswick | **~** | New Brunswick 511 — still credentials-wanted, not yet verified |
| Newfoundland and Labrador | X | Newfoundland and Labrador 511 — verified live |
| Nova Scotia | **~** | Nova Scotia 511 — still credentials-wanted; its own developer signup page has been taken down, no known self-service route to a key |
| Ontario | X | Ontario 511 (keyless) + Toronto Road Restrictions/Closures |
| Prince Edward Island | o | No source found |
| Quebec | X | MTQ Travaux routiers — verified live |
| Saskatchewan | **~** | Saskatchewan Highway Hotline — still credentials-wanted; its own developer signup page has also been taken down |
| Northwest Territories | o | No source found |
| Nunavut | o | No source found |
| Yukon | X | 511 Yukon — graduated to verified 2026-08-26 (16 real events round-tripped through the shared parser) |

## Germany, state-by-state

Autobahn GmbH gives genuine national coverage of the federal motorway
network — every state's real Autobahn mileage is covered by it, regardless
of whether that state also has its own feed. That's the floor (`~`) for
every one of Germany's 16 *Bundesländer* below; `X` means a state or city
authority's own dedicated feed sits on top of it too. Street Gazetteer is
only shown where a dedicated register exists — no national German street
register was found (see `docs/findings/germany-streets-investigation.md`),
so most states have none.

| State (Bundesland) | Roadworks | Street Gazetteer | Notes |
|---|---|---|---|
| Baden-Württemberg | X | o | Autobahn (national) + Verkehrsministerium state feed |
| Bavaria (Bayern) | ~ | o | Autobahn (national) only |
| Berlin | X | o | Autobahn (national) + VIZ state feed |
| Brandenburg | X | X | Autobahn (national) + state feed + WFS BB-BE street gazetteer |
| Bremen | ~ | o | Autobahn (national) only |
| Hamburg | X | X | Autobahn (national) + state feed + GAGES street gazetteer |
| Hesse (Hessen) | ~ | o | Autobahn (national) only |
| Mecklenburg-Vorpommern | ~ | o | Autobahn (national) only |
| Lower Saxony (Niedersachsen) | ~ | o | Autobahn (national) only |
| North Rhine-Westphalia (Nordrhein-Westfalen) | ~ | o | Autobahn (national) + Dortmund (city only, not statewide) |
| Rhineland-Palatinate (Rheinland-Pfalz) | X | o | Autobahn (national) + MWVLW state feed |
| Saarland | X | o | Autobahn (national) + LfS state feed |
| Saxony (Sachsen) | X | X | Autobahn (national) + state feed + GeoSN street gazetteer |
| Saxony-Anhalt (Sachsen-Anhalt) | ~ | o | Autobahn (national) only |
| Schleswig-Holstein | X | o | Autobahn (national) + LBV.SH state feed |
| Thuringia (Thüringen) | ~ | o | Autobahn (national) only |

## France, région-by-région

Bison Futé (the DIRs — Directions Interdépartementales des Routes) gives
genuine national coverage of France's major road network, the same
"reaches everywhere, major roads only" role Autobahn plays for Germany —
the floor (`~`) for every région below. `X` means a real département or
métropole feed sits on top of it too. BAN and BD TOPO are both genuinely
national gazetteers (IGN), so Street Gazetteer is `X` everywhere and isn't
repeated per row. Scoped to Metropolitan France's 13 régions — the five
overseas régions (Guadeloupe, Martinique, Guyane, La Réunion, Mayotte)
haven't been investigated, not confirmed absent.

| Région | Roadworks | Notes |
|---|---|---|
| Auvergne-Rhône-Alpes | X | Bison Futé (national) + Métropole de Lyon |
| Bourgogne-Franche-Comté | ~ | Bison Futé (national) only |
| Brittany (Bretagne) | X | Bison Futé (national) + Rennes Métropole |
| Centre-Val de Loire | ~ | Bison Futé (national) only |
| Corsica (Corse) | ~ | Bison Futé (national) only |
| Grand Est | ~ | Bison Futé (national) only |
| Hauts-de-France | ~ | Bison Futé (national) only |
| Île-de-France | X | Bison Futé (national) + Hauts-de-Seine (département) + Ville de Paris |
| Normandy (Normandie) | ~ | Bison Futé (national) only |
| Nouvelle-Aquitaine | ~ | Bison Futé (national) only |
| Occitanie | X | Bison Futé (national) + Toulouse Métropole |
| Pays de la Loire | X | Bison Futé (national) + Sarthe and Loire-Atlantique (départements) |
| Provence-Alpes-Côte d'Azur | ~ | Bison Futé (national) only |

## How this was built

Every territory-level cell above was checked directly against
`streetworks.providers(territory=...)` and each entry's own `.verified`
flag — not transcribed from a prior snapshot of this page or of
`docs/providers/index.md`. Several mechanisms needed more than a flat
registry lookup:

- **The North American 511 platform (na511)** registers every jurisdiction
  under the single territory string `"USA"` or `"Canada"`, not per-state —
  so state/province-level status came from each jurisdiction's own provider
  *key* (`id511`, `ga511`, `nl511`, ...) and its individual `.verified` flag,
  not a territory-filtered query.
- **The generic WZDx registry** (`streetworks.wzdx.registry.list_feeds()`)
  catalogs 41 real feeds with their own `state` and `needapikey` fields —
  a feed being cataloged and `active` doesn't mean it's actually reachable
  without credentials this SDK doesn't hold. Six states (Colorado,
  Massachusetts, Michigan, Oregon, Pennsylvania, Virginia) were previously
  marked complete on the strength of a WZDx feed that's real but key-gated;
  three (Delaware, Kansas, Mississippi) had a real keyless feed that an
  earlier pass missed entirely.
- **Germany and France both register every sub-national provider under the
  bare country territory** too (`"Germany"`/`"France"`), so state/région
  assignment came from each entry's own `administrative_area` field
  (e.g. `"Sachsen"`, `"Département des Hauts-de-Seine"`), matched by hand
  against each country's real administrative map. Both countries also have
  a genuine national road-authority feed (Autobahn GmbH; Bison Futé/the
  DIRs) that reaches every state/région for the major-road network alone —
  treated as the floor (`~`) for every row, with `X` reserved for a state
  or région that also has its own dedicated feed on top.

See [`docs/providers/index.md`](index.md) for the authoritative per-module
detail behind every cell, and [`docs/providers/us.md`](us.md) /
[`docs/providers/canada.md`](canada.md) for the full investigation writeups
behind the state/province tables.
