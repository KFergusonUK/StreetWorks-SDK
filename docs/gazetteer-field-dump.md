# Gazetteer field dump

Input to the canonical-gazetteer model design session. Reporting only — nothing
here changed any code. Per the brief: where something is genuinely unknown,
this document says so rather than inferring it.

Sources for this document: the adapters' real model files (`models.py`/
`reader.py`, read fresh, not from memory of having built them), their module
docstrings (which record extensive live verification done earlier in this
project — cited here as background, not re-derived), and existing test
fixtures in `tests/fixtures/`. No new large-scale analyses were run. One
adapter (the bonus Street Manager Lookup API) still has **no** fixture or
live-credential coverage in this environment — flagged explicitly below
rather than guessed at. `datavia` originally had the same gap, but real
credentials became available mid-session (see below) and were used for a
small number of targeted, low-volume live queries — not a large-scale
analysis, just enough to answer this brief's own open questions honestly.

---

## Part A — adapters as built

For each adapter: the real public model class(es), every field, one real
example value, how often it's populated in practice, and whether the source
states it or this SDK derives it.

### `datavia` — NSG (England & Wales, streets)

**No typed model exists.** `src/streetworks/datavia/` has `client.py`,
`filters.py`, `__init__.py` — no `models.py`. Every method
(`get_features`, `get_feature_info`, `get_map`) returns the WFS/WMS response
essentially unmodified: parsed GeoJSON `dict` for `geojson` output, raw
`bytes` for binary formats, `str` otherwise. The only structure this SDK
defines is the `Layer` enum (WFS `typeNames`: `ms:StreetLines`,
`ms:ESUStreets`, `ms:ESUOneWayExemptions`, `ms:StreetInterestLines/Points/
Polygons`, `ms:StreetConstructionLines/Points/Polygons`,
`ms:StreetSpecialDesignationLines/Points/Polygons`) and filter-builder
functions in `filters.py` (`property_equals`, `usrn_equals`,
`intersects_polygon`, `dwithin_point`, `bbox`).

| | |
|---|---|
| Public model classes | **None.** Raw `dict`/`bytes`/`str` pass-through. |
| Field names | See the real, live `StreetLines`/`ESUStreets` schemas below — pulled via WFS `DescribeFeatureType`, not previously captured anywhere in this repo. |
| Real example value | Now available for `StreetLines` — see below. Still unavailable for every other layer (`ESUOneWayExemptions`, `StreetInterestLines/Points/Polygons`, `StreetConstructionLines/Points/Polygons`, `StreetSpecialDesignationLines/Points/Polygons`) — not queried this session. |
| Population | Only assessable for the two fields actually queried live (`StreetLines`, `ESUStreets`) — see below. Unknown for every other layer. |
| Stated vs. derived | N/A — nothing is derived; the response is passed through unmodified. |

This is itself a reportable finding, not just a gap: of the 8 adapters, this
is the only one with **no typed model layer at all**.

**Live verification, added mid-session once credentials became available.**
Both this SDK's own `DataViaClient.street_by_usrn()` and the generic
`get_features()`/`filters.property_equals()` path were run against the real
API (Basic auth, Durham-scoped credentials) and confirmed working
end-to-end — auth, WFS `GetFeature` XML construction, and JSON parsing all
correct. Real `StreetLines` example (USRN `11713561`, Church Street, Durham
City):

```json
{
  "usrn": 11713561,
  "provider_id": "1355",
  "provider": "Durham",
  "record_type": "1",
  "record_type_text": "Designated Street Name",
  "street_descriptor_eng": "CHURCH STREET",
  "street_descriptor_cym": "",
  "locality_name_eng": "",
  "locality_name_cym": "",
  "town_name_eng": "DURHAM CITY",
  "administrative_area": "DURHAM",
  "language": "ENG",
  "state_code": "2",
  "state": "Open",
  "surface_code": "1",
  "surface": "Metalled",
  "street_status": "Maintainable at public expense",
  "street_status_id": "1",
  "maintaining_authority": "Durham",
  "street_start_date": "2014/07/10 00:00:00",
  "record_entry_date": "2008/04/21 00:00:00",
  "last_update_date": "2015/07/07 00:00:00",
  "reinstatement_record": "Carriageway type 2 (2.5 to 10 MSA)",
  "special_surface_record": 0,
  "special_construction_record": 0,
  "protected_street_record": 0,
  "pedestrian_crossings_record": 0,
  "traffic_sensitive_record": 0,
  "special_engineering_difficulty_record": 0,
  "esuids": "4276210541888;4276710542051;4276410541965"
}
```

A second real example (USRN `33909869`, Carr Street, Spennymoor) confirmed
the same field shape with different values — `reinstatement_record`,
`esuids` count, dates, and geometry all vary per street as expected; every
other field name is stable across both.

**Complete real `StreetLines` schema** (27 fields, via `DescribeFeatureType`
— the two examples above populate all but `locality_name_eng`/`_cym`,
which were empty on both real streets checked): `usrn` (int), `provider_id`,
`provider`, `record_type`, `record_type_text`, `street_descriptor_eng`,
`street_descriptor_cym`, `locality_name_eng`, `locality_name_cym`,
`town_name_eng`, `town_name_cym`, `administrative_area`, `language`,
`state_code`, `state`, `surface_code`, `surface`, `street_status`,
`street_status_id`, `maintaining_authority`, `street_start_date`,
`record_entry_date`, `last_update_date` (all three real dates —
directly answers B3 for DataVIA), `reinstatement_record`,
`special_surface_record`/`special_construction_record`/
`protected_street_record`/`pedestrian_crossings_record`/
`traffic_sensitive_record`/`special_engineering_difficulty_record`
(booleans), `esuids` (a semicolon-delimited string of ESU ids belonging to
this USRN — confirms a USRN aggregates multiple ESUs, e.g. 14 on Carr
Street, 3 on Church Street).

**Complete real `ESUStreets` schema** (20 fields, same route): `esuid`
(long), `esuidstring`, `provider_id`, `provider_name`, `one_way`,
`national_cycle_route`, `national_cycle_route_number`, `prow`,
`prow_number`, `highway_dedication_code`, `highway_dedication_code_text`,
`one_way_exemption`, `road_classification` (e.g. `"B6277"`, or empty on
minor roads/footpaths), `works_prohibited`, `planning_order`,
`obstruction`, `quiet_route`, `usrns` (string, back-reference to its parent
USRN(s)), `last_update_date`, `record_entry_date`.

**Directly answers this brief's B2 sub-question for DataVIA (investigated
live, not inferred)**: a real DataVIA street with a named sub-part sharing
a parent USRN — Church Street (USRN 11713561), whose ESUs on the ground
correspond to the locally-known "Anchorage Terrace" — was investigated.
**No field anywhere in either schema carries that name.** `StreetLines`
gives exactly one name per USRN (`street_descriptor_eng`); `ESUStreets`
carries *no name field at all* — not empty, structurally absent from the
schema (`esuid`/`usrns`/`road_classification`/dedication flags/dates only).
So DataVIA states neither *where* a sub-name applies nor whether any such
extent is directional, because the sub-name itself isn't represented in
this data model at any granularity — a real, structural answer, not a
missing-data gap.

### OS Open USRN (`openusrn`) — GB, streets

No `models.py`; the native shape is a dataclass in `reader.py`.

| Field | Type | Real example | Population | Stated/derived |
|---|---|---|---|---|
| `usrn` | `int` | `33909869` — a real Durham street, per `tests/test_openusrn.py`'s own comment, "verified live against DataVIA" | Always (primary key) | Stated |
| `geometry` | `str \| None` (WKT) | A `MULTILINESTRING` decoded from GeoPackage WKB to WKT by this SDK's own minimal decoder | Usually — but not always: the test fixture deliberately models a second real-shaped row (`usrn=84202034`) with `NULL` geometry as an expected, not hypothetical, case | Stated (reformatted, not altered, by this SDK) |

That's the entire model — two fields. No street name, no classification, no
authority. USRN is a pure key + geometry register; naming/classification for
the same USRN space lives in DataVIA (unverifiable this session, see above)
or Street Manager's Lookup API (see the bonus section below).

### `ban` — France, addresses

Class: `BANAddress` (`src/streetworks/ban/models.py`). Built from three real
access routes (geocoding API, `csv-bal` bulk, plain `csv` bulk) into one
shape; per-route absence noted below rather than treated as missing data.

| Field | Real example (API: 8 Rue des Halles, Paris) | Population | Stated/derived |
|---|---|---|---|
| `id` | `"75101_4461_00008"` | Always | Stated (`id`/`cle_interop`) |
| `toponyme_id` | `"75101_4461"` | Always | **Derived by this SDK** — stripped from `id` (see below) |
| `commune_insee` | `"75101"` | Always | Stated |
| `commune_nom` | `"Paris"` | Usually | Stated |
| `housenumber` | `"8"` | Present on housenumber-type results; absent on street-type results (e.g. lieu-dit/street-only entries) | Stated |
| `suffix` | `"bis"` — real example, `29001_0015_00004_bis` (Argol), csv-bal row: `numero=4, suffixe=bis` | Sometimes — only where French housenumber suffixing (bis/ter/quater or a letter) applies | Stated. **API note:** the geocoding API folds any suffix into `housenumber` itself and never populates this field (`suffix=None` always via `address_from_api_feature`) — only the two bulk CSV routes expose it separately |
| `street` | `"Rue des Halles"` | Usually | Stated |
| `postcode` | `"75001"` | Usually — **not present at all** via `csv-bal` (not a column in that format) | Stated |
| `lon`/`lat` | `3.657425` / `44.54242` (WGS84) | Always where geocoded | Stated |
| `ban_id` | `"17755936-2d91-4f2d-9ceb-9c77bce57eda"` | Always via API/`csv-bal`; **always `None`** via plain `csv` (that format doesn't carry the UUID) | Stated |
| `locality` | e.g. a `lieudit_complement_nom` value | Rarely (only lieu-dit addresses) | Stated |
| `position` | `"entrée"` | Usually (bulk formats) | Stated |
| `source` | `"commune"` | Usually (bulk formats) | Stated |
| `raw` | full original record, incl. `x`/`y` (Lambert-93/local, not modelled as coordinates — see module docstring) | Always | N/A |

**`toponyme_id` is the brief's own worked example of a derived field**: it is
*not* a literal BAN column. It's the address `id` with the numero/suffix
tail stripped off, on the confirmed-live observation that every address on
the same street within one commune shares that prefix (verified: 6/6 real
addresses on Impasse des Chênes, Argol). There is no `id_ban_toponyme`
field in real BAL 1.4 data under any format currently served — checked
across two départements.

### `bdtopo` — France, streets

Two classes, a genuine two-level spine: `VoieNommee` (named street) above
`Troncon` (road segment), joined by `liens_vers_supports`/
`liens_vers_route_nommee`.

**`Troncon`** — real example (`Rue Jean Monnet`, INSEE 01004):

| Field | Real example | Population | Stated/derived |
|---|---|---|---|
| `cleabs` | `"TRONROUT0000002001926152"` | Always | Stated |
| `nature` | `"Route à 1 chaussée"` | Always | Stated |
| `importance` | `"5"` | Always | Stated |
| `nom_collaboratif_gauche`/`_droite` | `"R JEAN MONNET"` (both sides, same here) | Usually | Stated |
| `nom_voie_ban_gauche`/`_droite` | `"Rue Jean Monnet"` (both sides) | Usually — real, common case: not every segment is a formally addressed street | Stated |
| `identifiant_voie_ban_gauche`/`_droite` | `"01004_0398"` (both sides) | Sometimes (same caveat) | Stated |
| `id_ban_odonyme_gauche`/`_droite` | `"d3f1c104-0186-42c5-acda-b6ee2defb09c"` | Sometimes | Stated |
| `insee_commune_gauche`/`_droite` | `"01004"` (both) | Usually | Stated |
| `sens_de_circulation` | `"Double sens"` | Usually | Stated |
| `vitesse_moyenne_vl` | `25` | Usually | Stated |
| `cpx_numero`, `cpx_gestionnaire`, `cpx_classement_administratif` | `null` in this example | Sometimes | Stated |
| `liens_vers_route_nommee` | `null` in this example (see `VoieNommee.liens_vers_supports` instead, the confirmed-working direction) | Sometimes | Stated |
| `etat_de_l_objet` | `"En service"` | Always | Stated |
| `geometry` | `LINESTRING` with real 3D coordinates, e.g. `(-0.12052741 46.43903041 173.7)` | Always | Stated |
| `raw` | ~90 real columns preserved, incl. `date_creation`/`date_modification` | Always | N/A |

**`VoieNommee`** — real example (`Impasse de Mollon`, INSEE 01004):

| Field | Real example | Population | Stated/derived |
|---|---|---|---|
| `cleabs` | `"VOIE_NOM0000002336861171"` | Always | Stated |
| `nom_voie_ban` | `"Impasse de Mollon"` | Usually | Stated |
| `nom_collaboratif` | `"IMP DE MOLLON"` | Usually | Stated |
| `nom_normalise` | `"IMP DE MOLLON"` | Usually | Stated |
| `type_voie` | `"impasse"` | Usually | Stated |
| `identifiant_voie_ban` | `"01004_0668"` | Sometimes | Stated |
| `id_ban_odonyme` | `"24e7b6f4-dfe3-4ad9-b8b6-60f922289243"` | Sometimes | Stated |
| `insee_commune`/`nom_commune` | `"01004"` / `"Ambérieu-en-Bugey"` | Usually | Stated |
| `liens_vers_supports` | `"TRONROUT0000002005899987"` | Usually — this is the confirmed-live-resolving link direction | Stated |
| `geometry` | `MULTILINESTRING` (aggregated segment extent) | Always | Stated |

Both `Troncon.toponyme_id_gauche()`/`_droite()` and `VoieNommee.toponyme_id()`
are thin accessor methods returning `identifiant_voie_ban*` or `None` —
**not derived values**, just a naming convention matching BAN's own
`toponyme_id` for cross-adapter consistency.

### `bag` — Netherlands, addresses

Class: `BAGLocation` (Locatieserver results — covers `adres`, `weg`,
`woonplaats`, `gemeente`, `postcode` types in one flat shape).

Real example (`adres`, "Dam 1, 1012JS Amsterdam"):

| Field | Real example | Population | Stated/derived |
|---|---|---|---|
| `id` | `"adr-2a8dc1af055da20b8bcdc8e4dbda1eaa"` | Always | Stated (Locatieserver's own composite key) |
| `type` | `"adres"` | Always | Stated |
| `weergavenaam` | `"Dam 1, 1012JS Amsterdam"` | Always | Stated |
| `identificatie` | `"0363010003761571-0363200003761447"` (adres) or e.g. `"0363300000003186"` (weg) | Usually | Stated |
| `openbareruimte_id` | `"0363300000003186"` | Usually — real BAG street object id, confirmed live identical to `identificatie` on a `weg` result | Stated |
| `nummeraanduiding_id` | `"0363200003761447"` | On address results | Stated |
| `straatnaam` | `"Dam"` | Usually | Stated |
| `huisnummer` | `1` (int) | On address results | Stated |
| `postcode` | `"1012JS"` | On address results | Stated |
| `woonplaatsnaam`/`gemeentenaam`/`provincienaam` | `"Amsterdam"` / `"Amsterdam"` / `"Noord-Holland"` | Usually | Stated |
| `lon`/`lat` | from `centroide_ll` WKT `POINT(4.8937175 52.37329259)` | Usually | Stated (reformatted from WKT) |
| `rd_x`/`rd_y` | from `centroide_rd` | Usually | Stated (reformatted from WKT) |
| `score` | `7.219551` | Usually | Stated |
| `afstand` | — | Only on `reverse()` results | Stated |

**House-number decomposition finding (relevant to B1)**: the real fixtures
checked (`bag_lookup_response.json`, `bag_free_response.json`,
`bag_search_diacritics.json`, `bag_suggest_response.json`) carry `huisnummer`
(int) and a combined display field `huis_nlt` (e.g. `"1"`) — **no
`huisletter` or `toevoeging` field appears in any of them**, and neither is
modelled on `BAGLocation`. Either the Locatieserver only emits them on
addresses that actually have a letter/addition (none of the sampled real
addresses did), or they aren't part of this `fl=` field list — not
resolved without a live query against an address known to carry one, which
this session couldn't run. Reported as unknown rather than guessed.

### `nwb` — Netherlands, streets

Class: `Wegvak` (one road segment / "wegvak" — a street is a *set* of these,
grouped via `bag_orl`, not one feature).

Real example (Alexiastraat, Harlingen):

| Field | Real example | Population | Stated/derived |
|---|---|---|---|
| `wvk_id` | `314551046` | Always (primary key) | Stated |
| `stt_naam` | `"Alexiastraat"` | Usually — even purely-numbered roads carry a name value (confirmed: a real A79 motorway segment has `stt_naam="A79"`) | Stated |
| `gme_id`/`gme_naam` | `72` / `"Harlingen"` | Usually | Stated |
| `wpsnaam` | `"Harlingen"` | Usually | Stated |
| `wegbehsrt`/`wegbehcode`/`wegbehnaam` | `"G"` / `"72"` / `"Harlingen"` (Gemeente) | Usually | Stated |
| `bst_code` | `"VP"` (voetpad/footpath) — other real values: `"FP"` (fietspad), `"RB"` (ordinary carriageway) | Always | Stated |
| `frc`/`fow` | `"7"` / `"7"` | Usually | Stated |
| `wegnummer`/`routeltr`/`routenr` | empty / empty / `null` in this example (populated on numbered routes) | Sometimes | Stated |
| `bag_orl` | `"0072300000319612"` | Usually — **not universal**: confirmed live, ~5% of Harlingen's wegvakken (96 of 1,886) carry none | Stated |
| `jte_id_beg`/`jte_id_end` | `314551086` / `314550058` | Always | Stated |
| `rijrichtng` | `"B"` (both directions) | Always | Stated |
| `geometry` | `LINESTRING`/`MULTILINESTRING` depending on route (WFS vs. bulk GeoPackage — a serialisation difference, not a data difference, per the module docstring) | Always | Stated |
| `raw` | ~55 real columns preserved | Always | N/A |

**Not promoted to the model but real and present in `.raw`**: `wvk_begdat`
(a per-feature effective/begin date — relevant to B3),
`hnrstrlnks`/`hnrstrrhts` (even/odd/neither house-number-parity flag per
side) and `e_hnr_lnks`/`e_hnr_rhts`/`l_hnr_lnks`/`l_hnr_rhts` (first/last
house number per side) — a real, segment-level house-number-range encoding
NWB carries that this SDK doesn't currently surface as first-class fields.
Worth flagging to the design session for B6/B1: this is a second, coarser
street↔address linkage beyond `bag_orl`, expressed as a number range rather
than an identifier.

`Wegvak.toponyme_id()` returns `bag_orl or None` — never falls back to name
matching (confirmed measurably less reliable: 7 of 385 real
(municipality, name) groups span more than one distinct `bag_orl`).

### `kartverket` — Norway, addresses (Matrikkelen; SSR reported separately below)

Class: `Address` (Vegadresse/Matrikkeladresse — REST API and bulk CSV, same
shape).

Real example (Ávjovárgeaidnu 3, Karasjok, bulk CSV):

| Field | Real example | Population | Stated/derived |
|---|---|---|---|
| `lokalid` | `"128065463"` | Bulk CSV only (`None` from the REST API — not present on that shape) | Stated |
| `kommunenummer`/`kommunenavn` | `"5610"` / `"KARASJOK"` | Always | Stated |
| `adressetype` | `"vegadresse"` | Always | Stated |
| `adressenavn` | `"Ávjovárgeaidnu"` | Usually | Stated |
| `adressekode` | `"1300"` | Always — confirmed clean at real scale (Karasjok 1,896 addresses/139 codes, Oslo 106,154/2,535, zero one-to-many) | Stated |
| `nummer` | `3` (int) | Usually | Stated |
| `bokstav` | `""` (empty) in every real bulk row sampled this session | **Unknown how often populated** — no populated real example found in the fixtures checked; the field exists and is real (Norwegian addressing does use letter suffixes), just not observed populated in this session's sample | Stated |
| `adressetilleggsnavn` | — | Rarely (a supplementary name, e.g. a farm name) | Stated |
| `adressetekst` | `"Ávjovárgeaidnu 3"` | Usually | Stated |
| `postnummer`/`poststed` | `"9730"` / `"KARASJOK"` | Usually | Stated |
| `epsg` | `"EPSG:4258"` (REST, always) or per-row `EPSG-kode` (bulk — same municipality published in multiple CRS variants as separate files) | Always | Stated |
| `nord`/`ost` | `69.472335` / `25.509034` | Always | Stated |
| `uuid_adresse` | `"56b864d3-d9e8-5098-8a76-a64a05ac7a0c"` | Bulk CSV only | Stated |
| `oppdateringsdato` | `"01.01.2024 00:00:00"` | Bulk CSV; also present on REST results | Stated |

**SSR (`PlaceName`/`NamedForm`) — a genuinely different register, reported
separately per the brief.** `PlaceName.names` is a list because a real
place can carry several parallel official names: a real SSR place
(Karasjok/Kárášjohka/Kaarasjoki, `stedsnummer` 868181) has three, in
Norwegian, Northern Sámi and Kven, each independently statused
(`navnestatus`, `skrivemåtestatus`). Fields: `stedsnummer` (int, always),
`stedstatus`, `navneobjekttype` (e.g. `"Adressenavn"` — SSR does have a
dedicated address-name object type), `kommuner`/`fylker` (tuples of
(code, name)), `nord`/`ost` (point only — no line geometry in any SSR
product checked), `names` (tuple of `NamedForm`: `skrivemate`, `sprak`,
`navnestatus`, `skrivematestatus`, `stedsnavnnummer`). All stated by the
source; nothing derived.

### `nvdb` — Norway, streets

Three classes, and — unlike BD TOPO — **not** a nested two-level spine:
`Veglenkesekvens`/`Veglenke` (pure network topology, no name) and
`VegAdresse` (naming/addressing, on a separate object type, NVDB type 538)
are two independent organising principles that only share the
`adressekode`/`veglenkesekvens_ids` link.

**`Veglenkesekvens`**/**`Veglenke`** — real example (`veglenkesekvensid=1`):

| Field | Real example | Population | Stated/derived |
|---|---|---|---|
| `veglenkesekvensid` | `1` | Always | Stated |
| `lengde` | `228.048` | Always | Stated |
| `veglenker[].veglenkenummer` | `1` | Always | Stated |
| `veglenker[].type` | `"HOVED"` (main) | Always | Stated |
| `veglenker[].startposisjon`/`sluttposisjon` | `0.0` / `0.45729325` | Always | Stated |
| `veglenker[].lengde` | `106.313` | Always | Stated |
| `veglenker[].kommune` | `4201` | Always | Stated |
| `veglenker[].geometry`/`srid` | `LINESTRING Z (...)` / `5973` | Always | Stated |

**Not promoted to `Veglenke` but real and present in `.raw`**: `typeVeg`
(e.g. `"Enkel bilveg"` — "simple car road") and `typeVeg_sosi` (e.g.
`"enkelBilveg"`) — the real road-type/classification field (relevant to
B5) — plus `detaljnivå`, `målemetode`, `måledato`, and the geometry-level
`datafangstdato`/`oppdateringsdato` (relevant to B3).

**`VegAdresse`** — real example (`id=646`, "Dalveien"):

| Field | Real example | Population | Stated/derived |
|---|---|---|---|
| `id` | `646` | Always | Stated |
| `adressekode` | `"1140"` | Always | Stated — confirmed the *same* identifier space as `kartverket.Address.adressekode` |
| `adressenavn` | `"Dalveien"` | Usually | Stated |
| `kommune` | `"4202"` | Usually | Stated |
| `veglenkesekvens_ids` | `(384, 2399262)` | Always — confirmed live: can be **more than one**, the key structural finding for B2/B4 | Stated |
| `geometry`/`srid` | present | Usually | Stated |

`metadata.startdato`/`sist_modifisert` (e.g. `"2020-05-24"` /
`"2025-05-01T08:05:41Z"`) is the real per-object temporal field (B3), not
currently promoted onto `VegAdresse` — preserved in `.raw`.

`VegAdresse.toponyme_id()` returns `adressekode or None` — a naming
convention, not a derived value.

---

### Bonus: Street Manager Street Lookup API (NSG/ASD proxy, not a gazetteer)

Per your request to include this — this is Street Manager's own
**Lookup API** (`api = Api.LOOKUP`, distinct from the Work/Reporting APIs
covered elsewhere), which proxies NSG street and ASD (Additional Special
Designation) data by USRN. Generated pydantic models,
`src/streetworks/streetmanager/models/v6/lookup.py`, from Street Manager's
live swagger spec.

**No real captured example exists anywhere in this repo for this endpoint.**
No fixtures (`find tests -iname "*lookup*" -o -iname "*nsg*"` → nothing
dedicated), and no `SM_*` credentials are present in this session's
environment, so no live call was possible. `tests/test_traffic_sensitive.py`
exercises the reducer logic against explicitly synthetic data (its own
comments call it "made-up": `usrn=11700550`, `street_descriptor="EXAMPLE
ROAD"`, `authority="EXAMPLE COUNCIL"`) — real-shaped but not a real
response, not used as an example value below.

`StreetResponse` fields (schema is real/authoritative — from the live
swagger spec — even though no live *instance* was captured):

| Field | Type | Notes |
|---|---|---|
| `usrn` | `float` | Same identifier space as `datavia`/`openusrn` |
| `street_descriptor` | `str` | Street name |
| `area`/`town` | `str` | |
| `authority`/`authority_swa_code` | `str` | Street authority |
| `road_category` | `float` | **Marked `DEPRECATED` in the spec itself** — see bugs/gaps below |
| `reinstatement_types` | `list[ReinstatementTypeDetails]` | Coded reinstatement type (1–10, 999) + free-text location |
| `traffic_sensitive` | `bool` | Blanket flag |
| `primary_notice_authorities`/`interest_authorities` | `list[...]` | Each with `swa_code`, `name`, `location_description`, `record_end_date` |
| `additional_special_designations_response` | `list[AdditionalSpecialDesignationsResponse]` | See below — the real sub-extent mechanism |
| `street_line` | `GeoJSONMultiLineString \| None` | Full street geometry |
| `street_centre_point` | `GeoJSONCentrePoint \| None` | |

`AdditionalSpecialDesignationsResponse` (the ASD sub-extent shape, directly
relevant to B2/B4):

| Field | Type | Notes |
|---|---|---|
| `street_special_desig_code` | Enum (1,2,3,6,8,9,10,12,13,16–30,999) | Coded designation type |
| `special_desig_location_text` | `str \| None` | **Free text**, not a structured extent |
| `special_desig_description` | `str \| None` | |
| `special_desig_start_time`/`end_time` | `float \| None` | Time-of-day window |
| `special_desig_periodicity_code` | Enum | e.g. recurring designations |
| `asd_coordinate_geometry` | `GeoJSONGeometry \| None` | Optional — a designation need not carry its own geometry |
| `whole_road` | `bool \| None` | The only structured extent signal — binary, not a range |
| `special_desig_start_date`/`end_date` | `AwareDatetime \| None` | Date-range validity |

`is_traffic_sensitive(usrn)` (`LookupAPI`/`AsyncLookupAPI`) is an
**explicitly derived, client-side view** — validates `street_by_usrn(usrn)`
against `StreetResponse` and reduces it to
`{"is_traffic_sensitive": bool, "designations": [...]}`. It is the one
clearly-labelled derived field in this whole survey outside BAN's
`toponyme_id`/BD TOPO's `toponyme_id_gauche`.

---

## Part B — open questions

### B1. House-number decomposition

The working sketch `street_name, number, unit` does not match any of the
three sources. Real shapes:

| Source | Fields | Real example |
|---|---|---|
| `ban` | `housenumber` (str) + `suffix` (str, separate) | `numero=4, suffixe=bis` (Argol) — bis/ter/quater or a bare letter go in `suffix`. **API-only caveat**: the geocoding API folds any suffix into `housenumber` and never populates `suffix` separately — only the two bulk CSV routes decompose it |
| `bag` | `huisnummer` (int) only, on this model | No real example with a letter/addition found in this session's fixtures. The raw Locatieserver `doc` carries a combined `huis_nlt` display string; separate `huisletter`/`toevoeging` fields were not observed in any sampled real response and are not modelled. **Unknown** whether the Locatieserver ever emits them separately — not resolved without a live query against a known letter-bearing address |
| `kartverket` | `nummer` (int) + `bokstav` (str, separate) | Field exists and is real (confirmed in the model/CSV schema); no populated real example was found in this session's samples — every real `bokstav` value checked was empty |

No-number addresses: not specifically re-verified this session for any of
the three (BAN's `nom_ld`/lieu-dit fields exist for lieu-dit-only entries;
not re-checked live here) — **unknown**, flagged rather than guessed.

None of the three uses anything resembling a single `unit`/flat field —
that concept doesn't appear in any of the three real schemas checked.

### B2. Street naming: segment level or street level?

| Source | Level | Evidence |
|---|---|---|
| `bdtopo` | **Both**, genuinely two-level. `voie_nommee` (street) aggregates `troncon_de_route` (segment) rows via a confirmed-live-resolving link; segments also carry their own (possibly different) left/right names directly | Confirmed live, see Part A |
| `nwb` | **Segment level only.** `stt_naam` is a `Wegvak` (segment) field; there is no separate named-street object. Grouping into a "street" is done by joining on `bag_orl`, not by a street-level name record NWB itself provides | Confirmed live at Harlingen scale |
| `nvdb` | **Neither, cleanly.** `Veglenkesekvens`/`Veglenke` (the segment/topology layer) carries *no name at all*. Naming lives on a separate `Adresse` object (type 538) that can span **multiple** `veglenkesekvenser** — not nested under one, and not itself a segment property | Confirmed live: the real "Dalveien" object spans two link sequences |
| `datavia` | **Resolved live, mid-session, once credentials became available.** `StreetLines` gives exactly one name (`street_descriptor_eng`) per USRN. `ESUStreets` (the ESU/sub-street-unit level) carries **no name field of any kind** — confirmed via the real `DescribeFeatureType` schema (20 fields: `esuid`, `usrns`, `road_classification`, dedication/PROW/cycle flags, dates — nothing name-like). Tested directly against Church Street, Durham (USRN 11713561), whose ESUs correspond on the ground to the locally-known "Anchorage Terrace": that name is not retrievable anywhere in DataVIA's data model, at either level. So the answer to "where does it apply / is it directional" is moot — there's no field for the sub-name to occupy in the first place |
| `openusrn` | **Unknown — not resolvable this session.** No live credentials for this specific product (it's a separate OS download route, not queried). Its own model has no name field at all (`usrn`+`geometry` only) |
| `streetmanager` (bonus) | ASD sub-designations are **effectively segment/extent-level within a street**, not separate named streets: `special_desig_location_text` is free text (no structured start/end), `asd_coordinate_geometry` is optional, and `whole_road` is the only structured signal, binary rather than a range. No stated directional convention |

### B3. "As at" / temporal validity

| Source | Mechanism | Real field(s) |
|---|---|---|
| `bag` | **Bitemporal in the full XML extract** (validity period + registration period), confirmed live on a real `OpenbareRuimte` history (two `Voorkomen` entries, one ending exactly where the next begins). **Not present at all in the GeoPackage this SDK reads** — `bag-light.gpkg` is current-status only, no history. `status` vocabularies do survive into the GeoPackage per table (e.g. `pand`: `"Pand in gebruik"`, `"Sloopvergunning verleend"`) | `beginGeldigheid`/`eindGeldigheid`, `tijdstipRegistratie`/`eindRegistratie` (XML extract only, not built) |
| `nvdb` | Per-object `metadata.startdato`/`sist_modifisert`; per-geometry `datafangstdato`/`oppdateringsdato`. A real changelog/version mechanism was referenced in earlier verification (`versjon` on `metadata`) but not deeply investigated this session | `metadata.startdato="2020-05-24"`, `sist_modifisert="2025-05-01T08:05:41Z"` (real, `VegAdresse` id 646) |
| `nwb` | Monthly republication (bulk file), **and** a real per-feature field: `wvk_begdat` (confirmed present in both real fixtures sampled, e.g. `"2019-01-01T00:00:00+01:00"`). Whether there's a companion end-date field wasn't checked this session — **unknown** | `wvk_begdat` |
| `bdtopo` | Real, confirmed-present per-feature fields: `date_creation`/`date_modification` (both `troncon_de_route` and `voie_nommee` carry them, e.g. `"2023-12-07T12:27:26.605Z"` / `"2024-03-08T14:53:45.791Z"`). Whether `cleabs` is stable across releases: **unknown** — not verified across two releases in this or any prior session | `date_creation`, `date_modification` |
| `datavia` | **Resolved live**: `StreetLines` carries three real per-feature dates — `street_start_date` (e.g. `"2014/07/10 00:00:00"`), `record_entry_date`, `last_update_date`. `ESUStreets` carries two: `last_update_date`, `record_entry_date` | `street_start_date`, `record_entry_date`, `last_update_date` |
| `openusrn` | **Unknown.** Its own model (`usrn`+`geometry`) carries no temporal field at all — the bulk file is simply republished periodically with no per-feature date modelled | — |
| `ban` | `date_der_maj` present in the real `csv-bal` fixture header/rows (e.g. `"2022-11-02"`) — not currently promoted onto `BANAddress`, preserved in `.raw` | `date_der_maj` |
| `kartverket` | `oppdateringsdato` (real, both REST and bulk CSV, e.g. `"01.01.2024 00:00:00"`), plus a separate `datauttaksdato` (bulk-file extraction date) seen in the real CSV header | `oppdateringsdato` (modelled), `datauttaksdato` (not modelled) |

### B4. Linear referencing

| Source | Real field(s) | Measure type | Measured along | Direction stated? |
|---|---|---|---|---|
| `nvdb` | `veglenke.startposisjon`/`sluttposisjon` (link's own sub-range on its parent sequence); `stedfesting.startposisjon`/`sluttposisjon` (an `Adresse`'s placement on a sequence) | Fractional, `0.0`–`1.0` | Its parent `veglenkesekvens` | Not independently re-verified this session — the fractional range itself doesn't encode direction beyond start<end along the sequence's own topology |
| Street Lookup (NSG/ASD, bonus) | `asd_coordinate_geometry` (optional GeoJSON) + `whole_road` (bool) + `special_desig_location_text` (free text) | **None structured** — either "whole road" or free text; no point-to-point ESU referencing, no fraction, no distance | N/A | No |
| `streetmanager` works extents (Work/Reporting API, not Lookup) | `works_coordinates` (raw GeoJSON `LineString`/`Polygon`, British National Grid easting/northing) + `usrn`/`street_name`. `Section58Extent` enum (`whole_road`/`part_of_the_road`) is the only structured extent-type signal | Raw geometry, not a linear-referencing scheme at all | N/A (absolute coordinates) | No |
| `datavia`/`openusrn` | ESU point-to-point extents are the NSG's documented mechanism in principle, but **not verifiable this session** — no live access | — | — | Unknown |
| `nwb`/`bdtopo`/`bag`/`ban`/`kartverket` | None — these are whole-feature (segment/point) registers, not linear-referencing systems | N/A | N/A | N/A |

### B5. Street type / classification

| Source | Real field | Domain | Code or plain string? |
|---|---|---|---|
| `bdtopo` | `Troncon.nature` | e.g. `"Route à 1 chaussée"` | Plain string (French label, not a short code) |
| `bdtopo` | `Troncon.importance` | e.g. `"5"` | Numeric-string code, scale/meaning not independently re-verified this session |
| `nwb` | `Wegvak.bst_code` | `"VP"` (voetpad/footpath), `"FP"` (fietspad/cycle path), `"RB"` (ordinary carriageway) — three real values confirmed at Harlingen scale | Short code, needs a lookup table (not bundled in this SDK) |
| `nwb` | `frc`/`fow` | e.g. `"7"`/`"7"` | Numeric codes (functional road class / form of way — standard NWB/INSPIRE-style codes, not independently decoded here) |
| `nvdb` | `typeVeg`/`typeVeg_sosi` (real, **not promoted** to `Veglenke` — `.raw` only) | e.g. `"Enkel bilveg"` / `"enkelBilveg"` | Plain string + a parallel SOSI code string |
| Street Lookup (bonus) | `reinstatement_types[].reinstatement_type_code` | Enum 1–10, 999 | Coded, needs lookup (`reinstatement_type_code_string` gives the label alongside it) |
| Street Lookup (bonus) | `additional_special_designations_response[].street_special_desig_code` | Enum (1,2,3,6,8,9,10,12,13,16–30,999) | Coded |
| Street Lookup (bonus) | `road_category` | `float` | **Marked `DEPRECATED`** in the live spec itself — see bugs below |
| `ban`/`bag`/`kartverket` | None — these are address registers with no street-classification field on the address itself | N/A | N/A |
| `datavia`/`openusrn` | Unknown — not verifiable this session | — | — |

### B6. Cross-references between addresses and streets

| Link | Direction stated | Real field | Coverage | Name-match only? |
|---|---|---|---|---|
| `nwb` → `bag` | street → address | `Wegvak.bag_orl` = `bag.openbare_ruimte_identificatie` | ~95% (96/1,886 Harlingen wegvakken missing it) | **No — real stated identifier.** Confirmed clean at scale (378 groups, zero one-to-many) |
| `bdtopo` → `ban` | street → address, **both directions available**: `identifiant_voie_ban_gauche`/`_droite` (compact toponyme-id, matches BAN's own format) *and* `id_ban_odonyme_gauche`/`_droite` (a second, independent UUID BAN's own API never exposes directly) | Present on both `Troncon` (per side) and `VoieNommee` | Sometimes (not every segment is formally addressed) | **No.** Verified at full-commune scale on two communes, zero over-merged groups against `nom_voie_ban` |
| `nvdb` → `kartverket` | street → address | `VegAdresse.adressekode` = `kartverket.Address.adressekode` (same identifier space, confirmed live) | Always where an `Adresse` object exists; **an `Adresse` can span multiple `veglenkesekvenser`**, breaking the simple 1:1 assumption | **No — real stated identifier** |
| `datavia`/`openusrn` → USRN/UPRN references | Unknown | USRN is the shared key across `datavia`, `openusrn`, and Street Manager Lookup (all three key on the same USRN space — confirmed for `openusrn`'s `usrn=33909869`, "verified live against DataVIA") | Unknown — not independently re-verified this session which of `datavia`'s layers carry a UPRN reference, if any | Unknown |
| `ban`/`bag`/`kartverket` — what each address states about its street | `ban`: `toponyme_id` (derived from `id`, not a literal field — see B1/Part A). `bag`: `openbare_ruimte_id`/`straatnaam` (`openbare_ruimte_naam` flattened onto every addressable object — no separate street row in the GeoPackage this SDK reads, though the full XML extract does have one). `kartverket`: `adressekode`/`adressenavn` on every `Address` | All three state an identifier or code, not just a name, for their own street concept | Always (every address in these registers carries the field) | **No**, for all three — each carries a real identifier (`toponyme_id`-shaped prefix, `openbare_ruimte_id`, `adressekode`), not merely a name string |
| Street Lookup (bonus) | USRN-keyed `StreetResponse`, same key space as `datavia`/`openusrn` | `usrn` | N/A (it's the primary key of the endpoint) | No — a real, shared identifier |
| NWB name-based fallback (flagged explicitly per the brief's standard) | — | grouping by `(gme_naam, stt_naam)` alone | Measurably less reliable: 7 of 385 real groups span more than one distinct `bag_orl` | **Yes — this specific fallback path is a name match, and this SDK's own `toponyme_id()` deliberately does not use it** |

---

## Part C — trim-test judgement (advisory only)

Judged against the three stated canonical-model use cases only: (1) plot
streets on a map, (2) link streets to roadworks, (3) pull street names from
address gazetteers. Fields below are ones that look like they would **not**
be needed to serve those three — not a coverage assessment, and not a
recommendation to delete anything from the native adapters, which stay as
built. This is a judgement call; final call is yours.

| Adapter | Likely trimmable for the 3 use cases | Reasoning |
|---|---|---|
| `ban` | `locality`, `position`, `source`, most of `raw` (e.g. cadastral parcel refs) | Address-provenance/positioning metadata, not needed to plot a street or join to roadworks |
| `bdtopo` | `Troncon`: `cpx_*` fields, `sens_de_circulation`, `vitesse_moyenne_vl`, `etat_de_l_objet`; `VoieNommee`: `nom_normalise` (duplicate of `nom_voie_ban`/`nom_collaboratif` in practice) | Traffic-engineering detail beyond the three use cases; `nature`/`importance`/geometry/BAN links are the load-bearing fields |
| `bag` | `score`, `afstand`, `woonplaatsnaam`/`provincienaam` (once `gemeentenaam` is kept), `type` variants beyond `adres`/`weg` | Search-ranking and administrative-hierarchy fields not needed for street-name lookup |
| `nwb` | `wegbehsrt`/`wegbehcode`/`wegbehnaam` (road-authority detail), `frc`/`fow`, `routeltr*`/`routenr*` beyond the primary route number, `jte_id_beg`/`jte_id_end` | Authority/route-numbering detail beyond plotting + roadworks-linking; `bag_orl` and `stt_naam` are load-bearing |
| `kartverket` | `NamedForm.stedsnavnnummer`, `fylker` (once `kommuner` is kept), `poststed`/`postnummer` if postal lookup isn't in scope | Postal/administrative detail; `adressekode`/`adressenavn`/point are load-bearing |
| `nvdb` | `vegsystemreferanser` (a real third identifier axis, confirmed but explicitly out of this brief's scope already), `målemetode`/`måledato`/`detaljnivå` | Survey-methodology metadata, not needed for the three use cases; `adressekode`/`veglenkesekvens_ids`/geometry are load-bearing |
| Street Lookup (bonus) | `primary_notice_authorities`/`interest_authorities` (relevant to use case 2 only if roadworks-notice routing is explicitly in scope — arguably keep), `reinstatement_types` (relevant to use case 2 in a different, more detailed sense than "link to roadworks") | Borderline — flagged rather than confidently trimmed, since use case (2) is stated broadly enough that these could matter |
| `datavia` | Cannot judge — no known field list this session | — |

---

## Bugs / gaps spotted while doing this (not fixed, per the brief)

1. **`StreetResponse.road_category`** (Street Manager Lookup API) is typed
   `float` but the field's own `description` in the generated model says
   `"DEPRECATED"`. If the canonical model is tempted to use it as a
   street-classification source (B5), it shouldn't — it's dead in the
   upstream API.
2. **No DataVIA fixture exists anywhere in the test suite**, and
   `test_datavia.py` only ever mocks an empty `FeatureCollection`. This was
   partially closed this session by live queries (see Part A/DataVIA), which
   confirmed `DataViaClient.street_by_usrn()` and `get_features()` both work
   correctly end-to-end against the real API — but those real responses
   still aren't captured as committed fixtures, so none of this adapter's
   parsing/field-shape behaviour is exercised in CI against anything
   resembling real WFS output. Worth turning the two real `StreetLines`
   payloads captured this session into committed fixtures.
3. **`ESUStreets`' `usrns` field is not filterable via WFS**, confirmed
   live: `get_features(Layer.ESU_STREETS, filter_fragment=f.property_equals
   ("usrns", <usrn>))` returns HTTP 200 with an `ows:ExceptionReport`
   (`FLTApplyFilterToLayer() failed` / `msPostGISLayerWhichShapes(): Query
   error`) rather than an empty result or a clean 4xx — even though the
   same field is returned fine in unfiltered/`esuid`-filtered queries. Not
   a bug in this SDK (the XML this SDK builds is correct — `usrn` filtering
   on `StreetLines` itself works fine), but a real, live-confirmed
   limitation of the upstream service worth knowing before anyone designs a
   "find all ESUs for this USRN" query path through `ESUStreets` directly
   rather than reading `StreetLines.esuids`.
4. **No fixture or test exists for Street Manager's Lookup API at all**
   (`streets`/`street_by_usrn`) — only the derived `is_traffic_sensitive`
   reducer is tested, and only against synthetic, self-labelled "made-up"
   data. The real `StreetResponse`/ASD shape has never been exercised
   against anything resembling a real payload.
5. **`nwb.Wegvak` doesn't promote `wvk_begdat` or the house-number-range
   fields** (`hnrstrlnks`/`hnrstrrhts`/`e_hnr_lnks`/`e_hnr_rhts`/
   `l_hnr_lnks`/`l_hnr_rhts`) even though they're real, present in every
   sampled fixture, and directly relevant to two of this brief's own
   questions (B3, B6/B1) — not a defect exactly, since they're preserved in
   `.raw`, but worth a second look given how directly they answer open
   questions this design session is asking.
6. **`nvdb.Veglenke` doesn't promote `typeVeg`/`typeVeg_sosi`** — the real
   road-type/classification field (B5) — even though `Veglenkesekvens`/
   `Veglenke` is otherwise fairly complete. Same "preserved in `.raw`, not
   a defect" caveat as above.
