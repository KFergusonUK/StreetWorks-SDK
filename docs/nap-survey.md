# NAP survey — European National Access Points for roadworks feeds

Research only. Nothing in either batch was built — no module, no client, no
tests. Source list:
[NAPCORE's National Access Point registry](https://napcore.eu/description-naps/national-access-point/),
RTTI column (Delegated Regulation (EU) 2022/670). Each country was checked
against the live site, not just the registry's own description; NAPCORE's
listed URL is noted separately from what was actually found wherever they
diverge.

## Tier 1 — batch 1 (Slovakia, Slovenia, Malta, Lithuania, Denmark, Sweden)

Every country here shows *some* real roadworks signal — this batch has no
Ireland-style "no roadworks at all" case. What varies enormously is how
much of that signal sits behind a JS app, an agreement, or a login this
survey couldn't get past — recorded as `unknown`, not guessed.

### Summary table

| Country | Roadworks? | Format | Access | Licence (short) | Confidence |
|---|---|---|---|---|---|
| Slovakia | Yes | DATEX II (version disclosed only after registration), Pull/HTTPS | Written agreement + X.509 mTLS certificate | Free, commercial use OK, attribution required | Documented, untested |
| Slovenia | Yes | DATEX II v3.3 **and** v2.3, plus GeoJSON/JSON/RSS/GeoRSS/TPEG/RDS-TMC | Account registration + per-dataset approval + OAuth2 | CC BY-SA 4.0 (per dataset) | Documented, untested |
| Malta (listed NAP) | Unknown | Unknown | Unknown — portal is a JS app; public ArcGIS services found carry no roadworks layer | Not found | Unknown |
| Malta (GeoHub, unlisted) | Yes | ArcGIS Feature Service | Item listed "public"; live query returned a permissions error | "View-only… not allowed to download, copy, modify or redistribute in any form" | Verified live (access denial), documented (content) |
| Lithuania (listed NAP) | Reported yes (secondary source only) | DATEX II 2.0RC2 (per third-party description) | Data-provision agreement (per third-party description) | Unknown | Unknown — portal 403s on every path tried |
| Lithuania (data.gov.lt, unlisted) | Yes | CSV/JSON/JSONL/RDF | Open, no registration | CC BY 4.0 | Verified live |
| Denmark | Yes | DATEX II v3.2 XML, AMQP push **or** REST pull | Registration; per-dataset Basic Auth credentials. Catalogue itself is open, no auth | CC BY 4.0 (catalogue-stated) | Documented (schema is authoritative and detailed), untested (no credentialed pull) |
| Sweden | Yes | DATEX II (XML dataset via Trafikverket agreement) **and** a separate "Situation" object on Trafikverket's open API | Free self-service registration (open API) **or** signed agreement (DATEX XML) | CC0 1.0 (open API); CC0 ("CCZero") on the DATEX catalogue entry too | Verified live (endpoint + auth behaviour), documented (content) |

---

### Slovakia — cdb.sk

**RTTI NAP:** https://www.cdb.sk/en/traffic-information-rds-tmc/data-service-in-the-DATEX-II.alej (matches NAPCORE's listing)

**Roadworks?** Yes. The terms document defines the feed's content directly:
> "The digital data of situational traffic information (hereinafter referred to as 'SDI') represent information on situation on roads (**usually closures and longer-term restrictions of operation**)."

**Format:** DATEX II, per STN CEN/TS 16157 (the Slovak national adoption of
the DATEX II CEN/TS). The **specific interface version is not published** —
it's disclosed only in a "data contract specification" sent after a request
is accepted. Delivery is Pull over TLS (https).

**Access:** Written agreement + **X.509 client certificate (mTLS)**. Real
process, confirmed from the linked terms/request PDF:
1. Applicant fills a form (company name, ID/VAT number, legal form, contact
   details) and sends it signed, by post or email, to Slovenská správa ciest
   (SSC).
2. On acceptance, SSC sends a "data contract specification" naming the
   DATEX II interface version, addresses, message range, and localisation
   method.
3. SSC issues an **X.509 access certificate** ("without which access to the
   DATEX II data service is not possible"), normally valid 2 years.

This looks obtainable — a standard company-details form, no unusual
prerequisites — but it is a real registration-plus-PKI step, not "open."

**Licence:** Captured in full, both languages (they match exactly — no
Saxony-Anhalt-style contradiction found here). Original Slovak (point 5,
`ssc_cdb_terms_of_use_traffic_information_v1.0.0_sk_norecstriction.pdf`):

> "5. Používanie SDI je:
> 5.1. bezodplatné,
> 5.2. nevýhradné,
> 5.3. pre komerčné alebo nekomerčné účely, pre poskytovanie služieb s pridanou hodnotou, pokiaľ toto nie je v rozpore s platnými legislatívnymi predpismi,
> 5.4. na dobu neurčitú, pričom platí, že SSC je oprávnená ho kedykoľvek aj bez udania dôvodu zrušiť…"

Official English translation (same document, `_en_` variant), matches:

> "5. Use of SDI is: 5.1. free of charge 5.2. non-exclusive, 5.3. for
> commercial or non-commercial purposes, for the provision of value-added
> services, unless this is in conflict with applicable legislative
> regulations, 5.4. for an indefinite period, while SSC is entitled to
> cancel it at any time and without giving a reason…"

Redistribution is restricted, not blanket-permitted: raw-form redistribution
needs SSC's written consent (point 7); redistribution as part of a real
product/service is fine but a specific attribution string is mandatory
(point 8) — Slovak: *"Zdrojom digitálnych údajov situačných dopravných
informácií je Slovenská správa ciest"*; English: *"The source of digital
data of situational traffic information is Slovak Road Administration."*

**Endpoint:** None public — issued per-applicant in the post-acceptance data
contract. Portal: https://www.cdb.sk/en/traffic-information-rds-tmc/data-service-in-the-DATEX-II.alej.
Request form: https://www.cdb.sk/files/documents/cestna-databanka/situacne-di/ssc_cdb_terms_of_use_traffic_information_v1.0.0_en_norecstriction.pdf

**Confidence:** Documented but untested. Full terms and request form read
in both languages; no live pull attempted (would need a real company
identity and a 2-year certificate-issuance wait).

---

### Slovenia — nap.si

**RTTI NAP:** https://nap.si/en/dataset_list?group=97706fee-e9b0-6d18-d4f1-4232b58b721d
(matches NAPCORE's listing). This is a catalogue, not a single feed — per
the brief's own instruction, queried via the dataset detail pages rather
than guessed from the group listing alone.

**Roadworks?** Yes, and unusually well-served: the group lists **eleven**
separate roadworks resources, same content in parallel formats — DATEX II
v3.3, DATEX II v2.3, GeoJSON (English and Slovene), JSON (English and
Slovene), RSS/GeoRSS (English and Slovene), RDS-TMC, and TPEG.

**Format:** DATEX II v3.3 is the primary/newest ("Roadworks - location,
type, description and status, in DATEX II v3.3 format"), XML, XSD-validated,
UTF-8. Update frequency stated as "Up to 1 min." Georeferencing: OpenLR,
Alert C, and plain WGS84 geocoordinates — so unlike some DATEX feeds, this
one doesn't require Alert-C-only location decoding.

**Access:** Registration required, **not** open despite the CC BY-SA
licence badge — this is the real, load-bearing distinction the brief asked
this survey to make precisely. Confirmed from NAP's own B2B instructions
PDF (`nap_B2B_en.pdf`):
1. Create an account (email confirmation).
2. Log in, browse the dataset list, check a "request" box per dataset, fill
   a form (**purpose of access, a ≥100-character description of use, a time
   period**), tick "I agree to the terms of use," submit.
3. NAP staff approve/deny per dataset (statuses shown: granted / requested
   / denied).
4. Once granted, pull data via OAuth2 **password grant** (`POST
   https://b2b.nap.si/uc/user/token` with username+password → bearer
   access/refresh token; then `GET https://b2b.nap.si/data/b2b.roadworks`
   with `Authorization: bearer <token>`).

**A real, unreconciled discrepancy worth flagging:** the dataset metadata
page states the DATEX II v3.3 access URL as
`https://b2b.ncup.si/data/b2b.roadworks.datexii33` (confirmed identically
on both the English and Slovene versions of the same dataset page), while
the B2B instructions document's own worked examples use a **different
host**, `https://b2b.nap.si/data/b2b.roadworks`. Both could be real (a
provider-hosted endpoint vs. a NAP-gateway alias), but this wasn't
reconciled — noted rather than guessed.

**Licence:** Dataset page states plainly (English): *"licence provided,
free of charge"* under **Creative Commons Attribution-ShareAlike 4.0**
(linked to `creativecommons.org/licenses/by-sa/4.0/deed.sl`). Original
Slovene wording, same page: *"Pogodba ali licenca: zagotovljena licenca,
brezplačno."* The two match — no contradiction found. Note this is the
per-dataset licence; the site-wide account "terms of use" (ticked at
registration) is a separate document this survey didn't independently
fetch.

**Endpoint:** `https://b2b.ncup.si/data/b2b.roadworks.datexii33` (per
dataset metadata) — see discrepancy note above.

**Confidence:** Documented but untested. Full B2B access flow read from
NAP's own PDF; no account was created, so the token exchange and the actual
feed response were not exercised live.

---

### Malta

**RTTI NAP (as listed):** https://geoservices.transport.gov.mt/egis

**Roadworks?** Unknown, honestly. The front-end is a JavaScript single-page
app (Transport Malta's "eGIS") whose visible menu includes a "Roadworks"
item, but that couldn't be read without executing the app. The underlying
public ArcGIS REST services **were** reachable and checked directly:

- The REST services root directory (`/arcgis/rest/services`) 403s.
- The main map service (`TM_Maps/eGIS_Malta`) lists 15 layers — tourist
  sites, transport stands, bus stops — **no roadworks layer**.
- `TM_Maps/eGIS_RoadandCoastalInfrastructure` lists traffic lights, lane
  control signals, CCTV, and VMS — traffic *management* infrastructure, not
  works or closures.
- Checked every service folder under `TM_Maps` (10 services); none is named
  or shaped like a roadworks/closures layer.

So: the UI advertises roadworks, but no publicly reachable service behind
*this specific* NAP was found to carry it. That's a real "unknown," not a
"no" — the layer could exist behind the login the app itself may present,
or the menu item could link out to a different system entirely.

**A quick win, noted and not pursued further:** a completely different
Maltese government body — the NSDI/"Malta GeoHub" (`geohub.gov.mt`, not the
NAP URL NAPCORE lists) — publishes a live ArcGIS item literally named
**"Full Road Closure"**
(`https://geohub.gov.mt/maps/102a9e17511b43f2be2b73baaeac61b9`), backing
service `main_road_works_NoEdits`. Worth a look in a future batch if Malta
comes up again, but it is not the listed RTTI NAP and wasn't chased beyond
the checks below.

- **Format:** ArcGIS Feature Service. Item metadata (via the AGOL
  `sharing/rest/content/items` API): `"access": "public"`.
- **Access — the real finding:** despite the item being catalogued as
  "public," a live, unauthenticated query against the FeatureServer itself
  (`utility.arcgis.com/usrsvcs/servers/.../FeatureServer?f=json`) returned:
  `"You do not have permissions to access this resource or perform this
  operation."` Item-level "public" ≠ queryable without a token, at least
  for this ArcGIS Enterprise-hosted service.
- **Licence — captured verbatim, and it directly contradicts the "public"
  access label**, the exact kind of gap this survey was told to watch for.
  From the linked Terms of Use PDF, under "RELIANCE OF INFORMATION POSTED":
  > "The Dataset is made available for view-only purposes. You may view and
  > interact with the spatial data contained within the Dataset but you are
  > not allowed to download, copy, modify or redistribute in any form."

  The same document's general IP section adds: *"The Government of Malta
  is the owner or the licensee of all intellectual property rights in the
  website… All such rights are reserved."*

**Confidence:** Unknown for the listed NAP itself (roadworks presence not
confirmed one way or the other). For the GeoHub aside: verified live that
the catalogue entry exists and that a direct query is refused; the licence
text is a direct document read, not inferred.

---

### Lithuania

**RTTI NAP (as listed by the task):** https://maps.eismoinfo.lt/portal/apps/sites/#/npp/pages/restrictions
**RTTI NAP (as listed by NAPCORE itself):** …/pages/counters — the two
disagree on which sub-page NAPCORE's own table points to; noted, not
resolved, since neither loaded.

**Roadworks?** Reported yes, but **only from secondary sources** — every
path on `eismoinfo.lt` and `maps.eismoinfo.lt` tried returned **HTTP 403**
to this tool, including the bare domain root. This may be a genuine bot/WAF
block rather than anything about the data itself, but it means the listed
NAP could not be read directly at all, at any URL, by this survey.

What a web search surfaced (not independently verified against the source):
road maintenance/repairs, obstacles, and event-related restrictions on
state roads, provided in **DATEX II 2.0RC2** format by AB "Via Lietuva"
(data since 1 June 2020), described as free of charge but gated by **a data
provision agreement**. That description could not be cross-checked against
the actual portal.

**A quick win, verified live and worth flagging strongly:** Lithuania's
open-data portal, **data.gov.lt**, publishes what looks like the same
underlying dataset under a completely different, fully open route:
*"Eismo ribojimai valstybinės reikšmės keliuose"* (Traffic restrictions on
state roads), https://data.gov.lt/datasets/1250/, provider **Via Lietuva** —
the same organisation named for the DATEX II feed above.

- **Format:** JSON, JSONL, RDF, and per-table **CSV** (four tables: road
  repairs `Remontas`, obstacles, event restrictions `Renginys`, and state
  road sections `KelioAtkarpa`), plus a "Saugyklos API" (storage API).
- **Access:** Open, no registration. **Verified live** — fetched the
  `Remontas` (repairs) CSV directly:
  `https://get.data.gov.lt/datasets/gov/via_lietuva/eismo_ribojimai/Remontas/:format/csv`
  → HTTP 200, real, current rows with genuine Lithuanian roadworks
  descriptions (*"Kelio remontas"* — road repair; *"Darbai kelkraštyje.
  Eismas per viaduką draudžiamas…"* — works on the road shoulder/verge,
  traffic across the viaduct prohibited), real date ranges, and geometry in
  the Lithuanian national grid (LKS-94, not WGS84 — coordinates in the
  6,000,000+/400,000+ range confirm this).
- **Licence:** **Creative Commons Attribution 4.0**
  (`creativecommons.org/licenses/by/4.0/deed.lt`).

This is a real, live, open, no-registration route to substantively the same
data the listed NAP is gated behind an agreement for — genuinely worth
building against instead of the NAP URL, if/when Lithuania is picked up for
implementation. Not pursued further here per the "note it and stop" rule.

**Confidence:** Unknown for the listed NAP (inaccessible, description
unverified). Verified live for the data.gov.lt alternative.

---

### Denmark — Dataudveksleren (du.vd.dk / nap.vd.dk)

**RTTI NAP:** both URLs redirect to the same portal,
`https://du-portal-ui.dataudveksler.app.vd.dk/` — matches NAPCORE's listing
of both names as one thing.

**Roadworks?** Yes, confirmed directly and in detail from Vejdirektoratet's
own DATEX II 3.2 schema documentation (the "Fælles TRACÉ
Protokolbeskrivelse," a 500KB technical spec, not marketing copy). The
`sit:SituationRecord` type list is stated explicitly and includes
`sit:ConstructionWorks` and `sit:MaintenanceWorks` (both roll up to a
`Roadworks` class in the document's own class diagram). Enumerated values
go well beyond a bare presence check —
`constructionWorkType`: `constructionWork, demolitionWork,
roadImprovementOrUpgrading, roadWideningWork`; `roadMaintenanceType`:
`clearanceWork, installationWork, maintenanceWork, overheadWorks,
repairWork, resurfacingWork, roadsideWork, roadworks, saltingInProgress,
snowploughsInUse, treeAndVegetationCuttingWork`.

**Format:** DATEX II v3.2, XML, and — unusually for this batch — **two
parallel transports**, both documented in their own protocol PDFs:
- **AMQP push**: each `sit:Situation` sent individually on
  creation/update, DATEX II XML carried in the AMQP `application-data`
  field of a `Bare Message`.
- **REST pull**: `HTTP GET`, response body a `trafikmeldinger` list of
  DATEX II XML strings.

**Access:** Registration required for the actual data. The REST protocol
document states this in full:
> "En request skal bruge HTTP Basic Authentication for at godkendes og må
> kun sendes over HTTPS… TOKEN er en base64-encoding af username:password.
> username og password konfigureres i DU ved opsætning af datasæt."
> ("A request must use HTTP Basic Authentication to be authorised and may
> only be sent over HTTPS… username and password are configured in DU
> [Dataudveksleren] when the dataset is set up.")

Notably, the **catalogue/metadata layer itself is open with no
authentication** — confirmed live by querying the DCAT endpoint directly
(`https://businessservice.dataudveksler.app.vd.dk/api/Metadata?format=dcat`),
which returned all 196 registered datasets without any credential.
opendata.dk's own description of the portal matches this framing: *"Her kan
du få adgang til offentligt tilgængelige datasæt relateret til vej og
trafik"* ("Here you can access publicly available datasets related to
roads and traffic") — true for the catalogue, not for the data pull itself.

**Licence:** The DCAT entry for the traffic-messages dataset states
**CC BY 4.0** (`CC_BY_4_0`) directly as a coded field rather than as
prose — there is no separate licence paragraph to quote verbatim beyond
that code, so none is invented here.

**Endpoint:** Catalogue (open, live-queried):
`https://businessservice.dataudveksler.app.vd.dk/api/Metadata?format=dcat`.
The actual per-dataset REST/AMQP pull address is issued during registration
per dataset, not a single public constant.

**Confidence:** The schema/format claims are documented at a level of
detail this survey would call authoritative (Vejdirektoratet's own protocol
PDFs, not a summary page). The catalogue's openness is verified live. The
actual credentialed data pull was not exercised — no account was
registered.

---

### Sweden — trafficdata.se

**RTTI NAP:** https://www.trafficdata.se (matches NAPCORE's listing). This,
like Slovenia's, is a catalogue over individually-hosted sources — mostly
Trafikverket (38 of 49 listed datasets), plus Trafiklab, TomTom,
Transportstyrelsen, and the Swedish Energy Agency.

**Roadworks?** Yes, both directly and via a second, independently-checked
route:
1. A dedicated catalogue entry, **"Road work Information, Road works"**
   (https://trafficdata.se/dataset/roadworks): *"This dataset includes road
   works elaborated by Swedish Transport Administration. DATEX."* Format
   `application/xml`, provider Trafikverket, coverage "motorways, regional
   roads, state/federal roads," quality stated as "Best effort," update
   frequency "Annual" (this last figure reads more like a metadata-review
   cadence than the feed's actual refresh rate, and wasn't independently
   confirmed either way).
2. Trafikverket's separate, better-known **open API**
   (`api.trafikinfo.trafikverket.se`) exposes a `Situation` query object
   covering road events/disruptions, road work included per Trafikverket's
   own documentation. **Verified live**, without a real key:
   ```
   POST https://api.trafikinfo.trafikverket.se/v2/data.json
     <REQUEST><LOGIN authenticationkey="test"/>
       <QUERY objecttype="Situation" schemaversion="1.5"/></REQUEST>
   → HTTP 401
   {"RESPONSE":{"RESULT":[{"ERROR":{"SOURCE":"Security","MESSAGE":"Invalid authentication"}}]}}
   ```
   A real, structured rejection — confirms the endpoint, the `Situation`
   object name, and the schema version live, independent of the catalogue
   page's own claims.

Trafikverket also publishes a DATEX II **profile specification** (v3.0,
dated June 2024) for how third parties — named explicitly as including
municipalities — should *publish* roadworks-with-traffic-impact data back
*to* Trafikverket as open data, suggesting a partly decentralised,
crowd-sourced-from-municipalities picture behind the single national feed.
Noted, not chased further.

**Access:** Two tiers, genuinely different in weight:
- The **open API** (`Situation` and friends): free **self-service**
  registration — fill a form, "Acceptera den licens som är knuten till
  API:t" (accept the licence tied to the API), verify email, get a key
  immediately. Lightest-weight access model in this whole batch.
- The **DATEX XML dataset** specifically (per a secondary source, not
  independently confirmed against a primary Trafikverket document): free of
  charge, but requires a **signed agreement** with Trafikverket before
  access is granted — closer to Slovakia's or Denmark's model than the open
  API's.

**Licence:** trafficdata.se's own licence facet for the catalogue shows
**43 of 49 datasets** under "Creative Commons CCZero," including the
roadworks entry itself ("Creative Commons CCZero" shown directly on the
dataset page). The open API's registration flow separately links a
**CC0 1.0 Universal / Public Domain Dedication**. Both routes land on CC0 —
consistent with each other, no contradiction found.

**Endpoint:** Open API, verified live: `https://api.trafikinfo.trafikverket.se/v2/data.json`.
DATEX dataset: catalogue page only (`https://trafficdata.se/dataset/roadworks`)
links to documentation (`data.trafikverket.se/documentation/datex/datamodel`),
not a bare data URL — the real pull address is presumably issued as part of
the agreement, same pattern as Denmark and Slovakia.

**Confidence:** Verified live for the open API's endpoint, object name, and
auth behaviour. Documented (catalogue page, cross-referenced against a
second Trafikverket source) for roadworks content and the DATEX access
model; not live-tested (no key obtained, no agreement signed).

---

### Cross-cutting notes

- **Three real "licence-says-one-thing, access-gate-says-another" cases**
  turned up in six countries: Slovenia (CC BY-SA badge, but OAuth2 +
  per-dataset approval to actually pull), Denmark (CC BY 4.0 on the
  catalogue entry, but Basic Auth credentials issued per dataset), and
  Malta's GeoHub aside (AGOL "public" access label, but an explicit
  view-only/no-redistribution clause and a live permission denial). None of
  these are contradictions in the Saxony-Anhalt sense (nothing here says
  "free" in one place and "non-commercial only" in another) — they're a
  different, equally real gap: an open **licence** doesn't imply open
  **access**, and a catalogue's access label doesn't always match what the
  underlying service actually does when queried.
- **Two listed NAPs were simply unreachable** to this tool — Malta's
  `geoservices.transport.gov.mt/egis` (JS app, ArcGIS root 403s) and all of
  `eismoinfo.lt`/`maps.eismoinfo.lt` for Lithuania (403 on every path,
  including the bare domain). Both are recorded as `unknown`, not `no`.
- **Two unlisted alternates were found to be strictly better** than the
  listed NAP for the same country's data: Lithuania's data.gov.lt (open,
  CC BY 4.0, live-verified, versus the listed NAP's agreement-gated DATEX
  II) and, more narrowly, Malta's GeoHub (a real roadworks layer exists
  somewhere in Maltese government GIS, even though the listed NAP doesn't
  appear to expose one). Both are flagged as quick wins for a future batch,
  not pursued into implementation here.
- **DATEX II version fragmentation is real and worth carrying into the
  roadmap**: v2.0RC2 (Lithuania, per secondary source), v2.3 and v3.3 in
  parallel (Slovenia), v3.2 (Denmark), an unspecified/undisclosed version
  gated behind registration (Slovakia), and v3.0 (Sweden, for the
  municipal-publishing profile specifically). A future implementation batch
  for any of these needs its DATEX II version confirmed again at build
  time, not assumed from this survey.

---

## Tier 2 — standard national portals (Austria, Belgium, Czech Republic, Poland, Portugal, Hungary, Estonia, Latvia, Luxembourg, Switzerland, Italy, Greece, Croatia, Romania)

Fourteen countries. Two produced fully live-verified, no-auth, open DATEX II
pulls with real roadworks records counted directly out of the payload
(Belgium, Luxembourg) — the strongest possible result this survey can
produce. A third (Estonia) went further still: the *documented* access
model says registration-plus-API-key, and the *actual* live endpoint needed
neither. Two NAPs were simply broken at the infrastructure level when
checked (Czech Republic: connection timeout on every path; Greece: expired
TLS certificate and a 502 from the backend). Both are recorded as
`unknown`, not `no` — a dead server says nothing about the data behind it.

### Summary table

| Country | Roadworks? | Format | Access | Licence (short) | Confidence |
|---|---|---|---|---|---|
| Austria | Yes | DATEX II Profile, XML, Pull | Unclear — catalogue page says open, a secondary source says registration; not reconciled | CC BY 4.0 **+ four ASFINAG supplementary conditions** (not vanilla CC BY) | Documented, untested |
| Belgium | Yes | DATEX II **v3**, XML | Open, no auth for the Flanders feed; site-wide terms ban commercial redistribution | No per-dataset licence found; site terms prohibit commercial third-party distribution | **Verified live** (70 Roadworks + 14 MaintenanceWorks records counted directly) |
| Czech Republic | Unknown (secondary source only) | DATEX II (version unstated) | Unknown | Unknown | Unknown — **host unreachable, connection times out on every path** |
| Poland | Yes | DATEX II v3.4, explicit ConstructionWorks/MaintenanceWorks | Registration + test/production certificate after message-exchange testing | Not found | Documented, untested |
| Portugal (listed NAP) | Unknown | Unknown | Unknown | Unknown | Unknown — Angular SPA, no backend API discoverable |
| Portugal (Lisbon municipal, unlisted) | Yes (city-scoped only) | CSV | Open, no registration | CC BY 4.0 | Verified live (resource URL confirmed) |
| Hungary | Yes | DATEX II v2.3/v3.2/v3.3 (in transition) | Registration + accept ÁSZF (T&Cs) | Free of charge (provider side confirmed; user-side reuse terms not found) | Documented, untested |
| Estonia | Yes | DATEX II v2.0, XML | **Documented as registration + API key; actual live endpoint needs neither** | CC BY-**NC** 4.0 (contradicts a secondary source claiming commercial use is fine) | **Verified live** (316 real MaintenanceWorks records) |
| Latvia | Yes | Unstated (catalogue says "Multiple") | Unknown — React SPA, no API found | CC0 1.0 | Documented, untested |
| Luxembourg | Yes | DATEX II v2.3, XML | Open, no auth | CC0 ("cc-zero") | **Verified live** (178 real MaintenanceWorks records) |
| Switzerland | Yes | DATEX II, SOAP-wrapped pull | Free self-service registration, API key | Reciprocal data-exchange model — **not** a standard open licence, see below | Documented (live endpoint identified, not credentialed) |
| Italy | Yes | DATEX II v2.3 (shared industry profile) | **SPID** (Italian national digital identity) required for portal login | Not found | Documented, untested |
| Greece | Unknown | Unknown | Unknown | Unknown | Unknown — **TLS certificate expired; backend API returns 502** |
| Croatia | Likely (not itemised) | DATEX II v2.3 (B2B) and v3.0 | Unknown | Not found | Documented, untested |
| Romania | Yes | GeoJSON / Esri FeatureServer | Account registration | Metadata record literally states "Not relevant"; site terms are default-closed (permission required) | Documented; the one real endpoint found currently 500s |

---

### Austria — mobilitaetsdaten.gv.at

**RTTI NAP:** https://mobilitaetsdaten.gv.at (matches NAPCORE's listing). A
catalogue (106 datasets, 32 providers at time of check), not a single feed.

**Roadworks?** Yes — "Verkehrsmeldungen zu geplanten Ereignissen (ASFINAG)"
(Traffic reports on planned events): *"Das Datenpaket stellt die Daten des
ASFINAG Baustellenmanagements zur Verfügung"* (The data package provides
ASFINAG's construction-site management data), covering roadworks,
maintenance, renovations, and pre-planned events, modelled as DATEX II
`Situation`s with lane-level and speed-funnel detail.

**Format:** "DATEX II Profile," XML, HTTP/HTTPS pull, 1-minute update rate,
"24/7 operation... quality-assured by specialised personnel." Specific
DATEX II version number not stated on the dataset page itself.

**Access:** Genuinely unreconciled. The dataset's own catalogue page states
plainly: "Access Requirements: Open access; no registration, API key, or
formal agreement mentioned as mandatory." A separate web search summary
states the opposite — "accessing it requires registration." The portal
itself (`contentportal.asfinag.at/data`) is a JS app this tool couldn't
read past its title. Recorded honestly as unresolved rather than picking
the more convenient answer.

**Licence — the real finding here.** Not vanilla CC BY 4.0: ASFINAG
publishes its own variant at
`contentportal.asfinag.at/assets/licenses/cc-by-40-asf/de/cc-by-40-asf.html`,
described as "the standard CC-BY 4.0 modified by four supplementary
conditions," captured verbatim (German):

1. *"Im Rundfunk (Radio, TV, gesprochene und bildliche Streaming-Dienste)
   sind die Quellen analog der Information zu nennen oder es ist eine
   gesonderte Vereinbarung zu treffen."* — broadcast media must attribute
   or reach a separate agreement.
2. *"Sie müssen uns die eigenen Services und Dienste nennen, in denen Sie
   unsere Informationen oder darauf aufbauende Informationen nutzen."* — an
   active obligation to disclose to ASFINAG which of your own
   products/services use the data.
3. *"Sie räumen uns das Recht ein, auf Basis der Namensnennung durch Sie,
   die Datenbereitstellung an Sie öffentlich zu kommunicieren."* — you
   grant ASFINAG the right to publicly name you as a data recipient.
4. *"Sie müssen digital bereitgestellte Verordnungen... übernehmen und
   angemessene Anstrengungen unternehmen, um diese... unverändert in Ihren
   eigenen Diensten darzustellen."* — a real operational obligation to
   implement and display official digital traffic regulations unchanged in
   your own service.

None of these are disqualifying, but "CC BY 4.0" alone, unquoted, would
have missed all four.

**Endpoint:** `https://contentportal.asfinag.at/data` (portal, JS app — no
bare endpoint URL found without registering).

**Confidence:** Documented, untested. Licence text is a direct document
read; the access-requirement contradiction is reported, not resolved.

---

### Belgium — transportdata.be

**RTTI NAP:** https://www.transportdata.be (matches NAPCORE's listing).
CKAN-powered — queried via search, per the brief's own instruction for
catalogue-shaped NAPs.

**Roadworks?** Yes, and **verified live, directly out of the payload**, not
inferred from a description. Two regional candidates surfaced in the
catalogue: "DATEX2 feed Verkeerscentrum Vlaanderen (full version)"
(Flanders) and "Événements routiers en Wallonie" (Wallonia, not chased
further given time). The Flanders dataset's own description: *"traffic
flow, incidents, current road works and special events that effect
traffic."*

**Format:** DATEX II **v3** — confirmed directly from the live XML's own
namespace declarations (`modelBaseVersion="3"`,
`http://datex2.eu/schema/3/...`).

**Access — fully open, no authentication.** Live-fetched the endpoint with
a plain unauthenticated GET:
```
GET https://www.verkeerscentrum.be/uitwisseling/datex2v3full
→ HTTP 200, 411,819 bytes, real current data (publication time matched
  the actual fetch time)
```
Counted `xsi:type` occurrences directly in the payload:
**70 `Roadworks`, 14 `MaintenanceWorks`** — genuine roadworks content, not
a guess from the description.

**Licence:** No per-dataset licence field found on the CKAN entry itself.
The portal's site-wide Terms of Use, however, carry a real, binding
restriction — captured in both French (native) and English (site's own
translation), and they match:

> French: *"les informations publiées sur ce site web ne peuvent en aucun
> cas : être copiées et reproduites de manière excessive… être diffusées
> ou communiquées à des tiers à des fins commerciales… être utilisées à
> des fins illégales"*
>
> English: *"The data listed on this website... may not be in any event:
> copied or reproduced in an excessive manner... distributed or shared
> with third parties with a view to commercial purposes... used for
> illegal purposes."*

So: fully open technical access, but a real, site-wide, non-commercial
restriction — an important pairing to keep straight, and the opposite
combination from Slovenia/Denmark (open-looking licence, gated access)
found in Tier 1.

**Endpoint:** `https://www.verkeerscentrum.be/uitwisseling/datex2v3full`
— live-verified, open.

**Confidence:** Verified live. This is the strongest possible result this
survey can produce for a country.

---

### Czech Republic — registr.dopravniinfo.cz

**RTTI NAP:** https://registr.dopravniinfo.cz (matches NAPCORE's listing).

**Roadworks?** Unknown — could not be checked against the primary source
at all. **The host is unreachable**: DNS resolves cleanly
(`185.240.221.50`), but every connection attempt — from this tool and from
a direct `curl` with an 8-second timeout — times out with no response,
across both `registr.dopravniinfo.cz` and a second related domain,
`dopravniinfo.gov.cz` (same IP). Not a 403/WAF pattern like some other
sites in this survey; the server simply doesn't answer.

What search-engine caches show (**not independently verified against the
source, since the source can't be reached**): DATEX II sources named
"Hustota provozu" (traffic density), "Běžné dopravní informace" (common
traffic information, described as covering accidents), and variable
message sign configuration data, all provided by NDIC (National Data and
Information Centre). No dataset explicitly named for roadworks/uzavírky
surfaced in the cached titles found — so even secondhand, roadworks
presence here is not confirmed.

**Format, access, licence, endpoint:** Unknown — no primary-source page
was reachable to check any of these.

**Confidence:** Unknown. This is the cleanest "the tool couldn't get past
the front door" case in this batch — recorded as such, not guessed at from
a general DATEX II description.

---

### Poland — kpd.gddkia.gov.pl

**RTTI NAP:** https://kpd.gddkia.gov.pl (matches NAPCORE's listing), run by
GDDKiA (General Directorate for National Roads and Motorways) as part of
the CROCODILE/CROCODILE 2 programme. Includes a public "Mapa utrudnień"
(disruption map) JS app, named directly in the brief, whose content
couldn't be read past its shell.

**Roadworks?** Yes, confirmed directly from the platform's own "Profil
DATEX 2" page: explicit `Construction works` (types: construction work,
road improvement/upgrading, road widening work) and `Maintenance works`
(types: maintenance work, **roadworks**, snowploughs in use) situation
categories.

**Format:** DATEX II **v3.4** — a real, dated migration: "Migration of
DATEX II in KPD to version 3.4," September 2024. Earlier profile work
(motorway concessionaires' sector, later shared with KPD/GDDKiA) was based
on DATEX II v2.3, per the industry-wide "Gruppo Tecnico DATEX" coordination
— i.e. Poland's ecosystem has been through at least one real version
migration, worth confirming again at build time rather than assumed fixed.

**Access:** Registration, heavier than a simple form. Per the platform's
own FAQ: submit a (downloadable) application by email or post to GDDKiA's
Warsaw office; for API access specifically, a **test-environment
certificate** is issued first, with a defined testing deadline, and only
after successful message-exchange testing is a **production certificate**
issued. Structurally similar to Slovakia's model (agreement + certificate),
though the certificate mechanics weren't independently confirmed as X.509
specifically.

**Licence:** Not found, despite searching the FAQ, the DATEX profile page,
and the technical-specification references surfaced by search.

**Endpoint:** None public — the "Profil DATEX 2" page offers downloadable
sample XML files, not a bare pull URL; the disruption map itself is a JS
app with no endpoint visible without executing it.

**Confidence:** Documented, untested. Roadworks content and DATEX II
version are both confirmed directly from primary-source pages; access and
licence are not fully resolved.

---

### Portugal — nap-portugal.imt-ip.pt

**RTTI NAP:** https://nap-portugal.imt-ip.pt (matches NAPCORE's listing,
after a same-origin redirect to `/nap/`), operated by IMT (Instituto da
Mobilidade e dos Transportes).

**Roadworks?** Unknown for the listed NAP itself. The site is an Angular
single-page app (`<app-root>`, no server-rendered content at all — even the
raw HTML has nothing but script tags). A search for the app's backend API
didn't surface one; the only concretely findable route was a client-side
path, `/nap/multimodalsupply`, which per its own description covers
**MMTIS** (Regulation (EU) 2017/1926 — schedules, network topology,
cycling/park-and-ride/bike-share, NeTEx/SIRI) — a **different** EU
regulation from the RTTI one this survey is scoped to, and not
roadworks-shaped at all.

**A quick win, noted and not pursued further:** IP (Infraestruturas de
Portugal, the actual national road authority) publishes real geometry
datasets — national road network, national rail network, motorway network
as WFS — openly (**CC BY 4.0**) on Portugal's general open-data portal,
`dados.gov.pt`, confirmed via that portal's own API
(`/api/1/organizations/infraestruturas-de-portugal-s-a-1/datasets/`). None
of IP's own open datasets there are roadworks/disruptions, though. A
**separate, city-scoped** dataset from the Lisbon municipality,
"Condicionamentos de Trânsito" (Traffic restrictions), is genuinely
roadworks-adjacent, open, CC BY 4.0, and live: a real CSV resource URL
(`https://coiapp2.cm-lisboa.pt/file/datahub/...`) was confirmed to exist
via the portal's API. It covers Lisbon only, not the national NAP.

**Format, access, endpoint (listed NAP):** Unknown — no backend API found.

**Confidence:** Unknown for the listed NAP. Verified (via API metadata, not
a direct pull) for the Lisbon municipal aside.

---

### Hungary — napportal.kozut.hu

**RTTI NAP:** https://napportal.kozut.hu (matches NAPCORE's listing), run
by Magyar Közút (national roads) with Budapest Közút (the capital's own
network) as a second data provider. JS app; primary confirmation came from
an official PDF brochure (`2023_nap_hu_brosura`) rather than the live
portal.

**Roadworks?** Yes, explicitly — the brochure's own data-category table
("Elérhető adatkörök") lists, under "MK ÚTINFORM": **"Úton végzett munkák"**
("Works carried out on the road"), national coverage, format DATEX,
alongside dynamic road-condition data, traffic management measures,
temporary traffic organisation measures, and real-time traffic data.

**Format:** DATEX II, but **fragmented across a real version transition**:
Budapest Közút's original static data used v2.3; the service added a
bidirectional v3.2 interface; Magyar Közút's newest implementation, in
progress as of the brochure's writing (CROCODILE III phase), is **v3.3**
— "a legújabb" (the newest). A build against this NAP needs the version
reconfirmed at the time, not assumed from this survey.

**Access:** Registration. Per the brochure's own terms summary (excerpted
from the ÁSZF — Általános Szerződési Feltételek, General Terms and
Conditions): *"A NAP-ot adatszolgáltatóként való regisztráció után lehet
adatszolgáltatásra használni... Az Adatszolgáltató az oldalra történő
regisztrációjával kijelenti, hogy az ÁSZF-et megismerte és elfogadja az
abban foglalt feltételeket."* (The NAP may be used for data provision only
after registering as a data provider... by registering, the Data Provider
declares that they have read the ÁSZF and accept its terms.) Metadata is
stated to be reachable without any registration at all; broader data
packages need it.

**Licence:** The brochure confirms the **provider**-side service is free:
*"Az Üzemeltető (Magyar Közút Nonprofit Zrt.) a Szolgáltatást térítésmentesen,
ellenérték követelése nélkül nyújtja."* (The Operator provides the Service
free of charge, without demanding consideration.) This is the
provider-onboarding section specifically (`ADATSZOLGÁLTATÓK CSATLAKOZÁSA`)
— the **data user's own reuse/redistribution terms were not found** in the
pages read, so "free of charge" shouldn't be assumed to extend to
downstream redistribution rights without checking the user-side ÁSZF
directly.

**Endpoint:** None public — behind registration.

**Confidence:** Documented, untested. Roadworks content and the multi-version
DATEX II transition are both confirmed directly from an official PDF, not
inferred.

---

### Estonia — andmed.eesti.ee

**RTTI NAP:** https://andmed.eesti.ee (matches NAPCORE's listing) —
Estonia's general national open-data portal ("Teabevärav"/Information
Gateway), not transport-specific; the RTTI-relevant entry was found by
searching within it.

**Roadworks?** Yes — confirmed twice over, once from documentation and once
directly from live data. The dataset itself,
**"Transpordiameti Tark Tee DATEX II andmevärav"** (Transport
Administration Smart Road DATEX II Data Gateway), is explicitly tagged in
the portal's own structured metadata against
`RTTI_LEGAL_ACT` = *"Reaalaja liiklusteabe delegeeritud määrus (EL)
2022/670"* — literally the regulation this whole survey is scoped to —
plus the Open Data Directive. A related dataset,
"Liikluspiirangute andmed" (Data on traffic restrictions), is linked
alongside it.

**Format:** DATEX II — the live payload declares `modelBaseVersion="2"`
(`http://datex2.eu/schema/2/2_0`), i.e. **v2.0/v2.x**, not the v3 this
metadata record's own "DATEX II" label alone wouldn't have told us; XML,
`SituationPublication`, `feedType: Traffic restrictions`.

**Access — a real, load-bearing discrepancy between documented process and
live behaviour.** The portal's own structured "rights" field, read in full
(Estonian, verbatim):

> *"Teenusele ligipääsuks on vajalik registreeruda ja pärast edukat
> registreerumist saadetakse Kasutajale unikaalne API-võti, mida tuleb
> kasutada DATEX II teenuste poole pöördumisel. API-võti muutub kehtivaks
> alles siis, kui Haldaja on Kasutaja registreerumise üle vaadanud."*
> ("To access the Service, registration is required, and after successful
> registration the User is sent a unique API key... The API key only
> becomes valid once the Administrator has reviewed the User's
> registration.")

The registration form's own required fields are listed too: institution
name, first/last name, email, and **purpose of registration**, all
mandatory.

**But the actual live endpoint needed none of this.** The metadata
record's own `serviceEndpoints` field named
`https://tarktee.mnt.ee/api/v1/datex/restrictions`, which 301-redirects to
`https://tarktee.transpordiamet.ee/api/v1/datex/restrictions` (a real
domain migration, mnt.ee → transpordiamet.ee). A plain, unauthenticated
`GET` against the new domain returned **HTTP 200 with 8.5MB of real,
current DATEX II XML — no API key, no login, nothing.** Counted directly:
**316 real `MaintenanceWorks` situation records.** Whether this is an
intentional "the catalogue's documented process is stricter than the
service actually enforces" situation, or a real access-control gap, isn't
something this survey can determine — reported as observed, not
interpreted.

**Licence — also a real discrepancy, the Saxony-Anhalt kind this survey
was told to watch for.** The dataset's own structured licence field:
`"code": "CC_BY_NC_4.0"`, `"name": "CC BY-NC 4.0 - Creative Commons
Autorile viitamine–Mitteäriline eesmärk 4.0 Rahvusvaheline"` — **explicitly
non-commercial**. A general web search summary about the same "ITS-NAP
catalogue" claimed the opposite: "everyone has access to the data along
with rights to reuse and share it for both commercial and non-commercial
purposes." The dataset's own structured field is the authoritative one
here — captured directly, not summarised — and it says NC.

**Endpoint:** `https://tarktee.transpordiamet.ee/api/v1/datex/restrictions`
— **verified live, fully open in practice**.

**Confidence:** Verified live — the strongest result in this batch,
alongside Belgium and Luxembourg, and the only one of the three where the
documented access model and the actual live behaviour visibly disagree.

---

### Latvia — transportdata.gov.lv

**RTTI NAP:** https://transportdata.gov.lv (matches NAPCORE's listing,
titled "Transports. Mobilitāte" | "Latvijas Nacionālais piekļuves punkts").
A React single-page app (`<div id="root">`); no CKAN-style API found at
the usual paths, and several guessed API routes all returned the SPA shell
unchanged.

**Roadworks?** Yes — confirmed via Latvia's general open-data portal,
`data.gov.lv`, whose own catalogue aggregates the NAP's datasets under
"Nacionālā piekļuves punkta datu kopas" (National access point dataset
collection), published by VSIA "Latvijas Valsts ceļi" (Latvian State
Roads). Two directly-named resources: **"Ilgtermiņa un īstermiņa ceļa
darbi"** (Long-term and short-term road works) and **"Īstermiņa ceļa
darbi"** (Short-term road works), alongside "Valsts autoceļu tīkls" (State
road network).

**Format:** Listed only as "Multiple" on the aggregator entry; the
individual `transportdata.gov.lv/lv/card/...` pages for each resource are
part of the same unreadable SPA, so the specific DATEX II version (if any)
wasn't confirmed.

**Access:** Unknown for the live portal. The aggregator dataset itself
carries **CC0 1.0 (Public Domain)**.

**Endpoint:** Not found — every specific-resource URL discovered
(`transportdata.gov.lv/lv/card/<uuid>`) rendered as the same empty SPA
shell; no working data pull was identified.

**Confidence:** Documented, untested. Roadworks presence and licence are
confirmed from the aggregating open-data catalogue entry, not the NAP
itself, which stayed opaque throughout.

---

### Luxembourg — data.public.lu

**RTTI NAP:** https://data.public.lu (matches NAPCORE's listing, "Ponts et
Chaussées" as named in the brief) — a udata-platform instance, queried
directly via its API.

**Roadworks?** Yes — confirmed immediately from the catalogue's own API
(`/api/1/datasets/?q=chantier`): **"PCH : Les chantiers actuels"** (PCH:
Current construction sites) and **"PCH : Les futurs chantiers"** (Future
construction sites), both from Administration des Ponts et Chaussées,
Luxembourg's actual road authority, plus separate cycle-path variants and
a municipal one (Esch-sur-Alzette).

**Format:** DATEX II — confirmed directly from the live payload's schema
location, `DATEXIISchema_2_2_3.xsd`, i.e. **v2.3**.

**Access — fully open, no authentication.** Live-fetched with a plain
unauthenticated GET:
```
GET https://www.cita.lu/info_trafic/datex/chantierActuelDatex.xml
→ HTTP 200, real, current publicationTime matching the fetch time
```
Counted `xsi:type` occurrences directly: **178 real `MaintenanceWorks`**
records, plus `SpeedManagement`, `GeneralNetworkManagement`, and location
data. A KML alternative of the same dataset is also published
(`https://www.cita.lu/kml/chantiers_actuel.kml`).

**Licence:** **CC0** (`cc-zero`), stated directly on the dataset's own API
record — genuinely the simplest, most unambiguous licence found in either
tier of this survey.

**Endpoint:** `https://www.cita.lu/info_trafic/datex/chantierActuelDatex.xml`
— verified live, open, no auth.

**Confidence:** Verified live. Alongside Belgium, the cleanest possible
result this survey can produce.

---

### Switzerland — opentransportdata.swiss

**RTTI NAP:** https://opentransportdata.swiss/en/road-traffic/ (matches
NAPCORE's listing). Switzerland isn't an EU member, so Delegated
Regulation 2022/670 doesn't bind it legally, but the platform (run by
FEDRO/ASTRA, the Federal Roads Office) is included in this batch as
instructed and turned out to be one of the most precisely documented
entries here.

**Roadworks?** Yes, explicit: the "Traffic information (road traffic)"
dataset's own description: *"real-time information on road traffic
conditions, including traffic flow, accidents and short- or long-term
roadworks."*

**Format:** DATEX II (no version number stated on the dataset page itself)
— delivered over a **SOAP-wrapped pull interface**, an unusual combination
for this survey (most DATEX II access here is plain REST or AMQP):
`https://api.opentransportdata.swiss/TDP/Soap_Datex2/TrafficSituations/Pull`.

**Access:** API key required. Tiered: a free, self-service initial
registration grants 260,000 requests per 6 months at up to 1 request/minute;
extended/unlimited access requires either contributing your own traffic
data (becoming a data partner) or a written justification request.

**Licence — genuinely unusual, and worth reading in full rather than
labelling "open."** Not a standard permissive licence at all but a
**reciprocal data-exchange model** ("TAC FEDRO"), captured verbatim
(German):

- *"Werden die VDP-Daten allerdings im Zuge eines Geschäftsmodells genutzt,
  wird von den Nutzerinnen und Nutzern im Rahmen des gegenseitigen
  Datenaustauschs eine gleichwertige Datenlieferung gefordert."* (§6.1) —
  if the data is used as part of a business model, the user is required to
  provide an **equivalent data delivery back**, as part of a mutual
  exchange — not a one-way open licence at all once money is involved.
- *"Den Nutzern ist es untersagt, die Daten im Rohformat über eine
  maschinenlesbare Schnittstelle an Dritte weiterzugeben."* (§8.1) — raw
  redistribution to third parties via a machine-readable interface is
  prohibited.
- *"Sofern nicht gesetzlich anders geregelt, dürfen die Datennutzer die
  Daten nicht in einer Weise kombinieren, die die Erstellung von
  Verhaltensprofilen oder die Re-Identifizierung von Personen auf
  öffentlichen Strassen möglich macht."* (§7.3) — no combining the data in
  ways that would allow behavioural profiling or re-identification of
  people on public roads.
- Mandatory attribution string (§13): *"Datenquelle: Verkehrsdaten-Plattform
  (VDP) ASTRA."*

**Endpoint:** `https://api.opentransportdata.swiss/TDP/Soap_Datex2/TrafficSituations/Pull`
— identified and documented; not called with a real key.

**Confidence:** Documented in real depth (the terms document is precise
and was read in full); not live-tested, since that needs a registered key.

---

### Italy — cciss.it

**RTTI NAP:** https://www.cciss.it (matches NAPCORE's listing) — CCISS
(Centro Coordinamento Informazioni Sulla Sicurezza Stradale), under the
Ministry of Infrastructure and Transport.

**Roadworks?** Yes — the public real-time feed on the site itself displays
event types including *"riduzione di carreggiata causa lavori"* (lane
reduction due to works), and Italy has a real, shared industry DATEX II
profile — coordinated by the "Gruppo Tecnico DATEX Italia" (motorway
concessionaires, under the aegis of the Ministry/CCISS and AISCAT) —
covering CCISS, ANAS, and urban network managers together.

**Format:** DATEX II **v2.3**, per the shared national/motorway-sector
profile (`Profilo-DATEX-IT---DATEX-II-v2.3`, published by the technical
group on GitHub).

**Access — the standout finding for Italy.** The CCISS portal's own login
page states that, since 1 October 2021, citizens can no longer authenticate
with ordinary credentials and must use **SPID** (Sistema Pubblico di
Identità Digitale — Italy's national digital identity system). This is a
categorically heavier access barrier than a registration form or even an
mTLS certificate: it presumes an Italian (or otherwise SPID-eligible)
digital identity, which a non-Italian organisation would need to establish
separately before ever reaching a data-access step. There is a **separate**
NAP for MMTIS data (`cciss.it/nap/mmtis/...`, Regulation 1926/2017, NeTEx/
SIRI, 18 regional contributors) — a different EU regulation from RTTI, not
chased further for roadworks purposes. Participation in the DATEX II
technical group itself is by email (`gruppotecnico@retedatex.it`), which
reads as more informal/bespoke than any of the self-service or form-based
registrations found elsewhere in this survey.

**Licence:** Not found.

**Endpoint:** Not found — the technical group's GitHub profile documents
the DATEX II *schema*, not a live pull address.

**Confidence:** Documented, untested. The SPID requirement is a direct
read of the login page, not an inference.

---

### Greece — nap.gov.gr

**RTTI NAP:** http://www.nap.gov.gr (matches NAPCORE's listing), catalogue
at `data.nap.gov.gr`, part of the CROCODILE 2 programme.

**Roadworks?** Unknown — **the catalogue is genuinely broken** at the time
of this check, on two independent signals:
1. `https://data.nap.gov.gr` — **TLS certificate has expired** (WebFetch
   refused the connection outright on this basis).
2. Bypassing that (`curl -k`) to test the CKAN API and the dataset-listing
   page directly both returned **`502 Bad Gateway`** from the backend
   (`nginx/1.10.3`), not just a slow response.

The landing page (before the catalogue) describes only general categories
— "traffic congestion levels and vehicle speeds," "travel time data,"
weather measurements — with no explicit roadworks mention, but this is not
being treated as a confirmed "no": the actual dataset catalogue, where a
roadworks-specific entry would live, could not be reached to check.

**Checked for an alternate, found none:** Greece's general open-data
portal, `data.gov.gr` (a real, working CKAN 2.11.3 instance, confirmed
live), was searched directly via its API for "έργα" (works) — every result
was an administrative/construction-project dataset (regional development
works, building-permit registers, hospital tenders) with no traffic or
roadworks relevance.

**Format, access, licence, endpoint:** Unknown.

**Confidence:** Unknown. Alongside the Czech Republic, this is a case where
the survey's honest output is "the infrastructure itself is down," not a
finding about the data.

---

### Croatia — promet-info.hr

**RTTI NAP:** https://www.promet-info.hr (matches NAPCORE's listing), run
by HAK (Hrvatski autoklub).

**Roadworks?** Likely, but **not explicitly itemised** the way several
other countries in this survey were — a real distinction worth keeping,
not glossed over. The site's own DATEX II page lists real profiles
directly: DATEX II **v2** — `Cameras 1.0, Counters 1.0, Events 1.2,
Traveltimes 1.0, VMS Status 1.0, VMS Table 1.0, Weather 1.0, Wind 1.0,
Truck parking Status, Truck parking Table`; DATEX II **v3** — `Cameras 3.0,
Counters 3.0, Events 3.0, IDACS 3.0, Truck parking 3.0, SRTI 3.0, Traffic
management plans 3.0, Traffic regulation 3.0, Traveltime 3.0, VMS 3.0,
Weather 3.0, Wind 3.0`. The generic "Events" profile is exactly the DATEX
II category that carried roadworks as a `SituationRecord` subtype
everywhere else this was checked directly in this survey (Denmark,
Belgium, Estonia, Luxembourg, Poland, Hungary all showed this explicitly)
— but Croatia's own page doesn't itemise "roadworks"/"radovi" as a named
type the way those did, so this is recorded as a reasoned "likely," not a
confirmed "yes."

**Format:** DATEX II v2.3 (B2B, stated directly: *"compatible with DATEXII
standard, version 2.3"*) and v3 profiles as listed above.

**Access, licence, endpoint:** Not found. The providers-list page names
three road-infrastructure operators (Hrvatske autoceste, Autocesta Zagreb
- Macelj, Hrvatske ceste) and HAK itself as the traffic-info service
provider, but gives no registration process, terms, or endpoint.

**Confidence:** Documented, untested — and the "likely, not confirmed"
roadworks verdict is itself the honest output here, not a rounding-up to
"yes" the way DATEX II's generic reputation might invite.

---

### Romania — pna.cestrin.ro

**RTTI NAP:** https://pna.cestrin.ro (matches NAPCORE's listing), CESTRIN
(part of C.N.A.I.R., Romania's national road authority). An Umbraco/ASP.NET
site with an embedded Esri map; TLS chain is real but incomplete (a missing
intermediate certificate, not an expired one — a lesser version of Greece's
problem).

**Roadworks?** Yes, confirmed two ways:
1. A dedicated tool, **"drumuri-cu-lucrari"** (roads with works): *"The
   application provides you with search tools and dynamic tools for
   displaying and centralizing data on roads with works."*
2. A structured NAP metadata record (EU EIP SA46 Coordinated Metadata
   Catalogue format) for a dataset named **"Drumuri închise"** (Closed
   roads).

**Format:** GeoJSON via an Esri **FeatureServer**, per the metadata
record's own `Data Format - Syntax: Other` / `Data Format - Data Model:
other`, `Access Interface: HTTP/HTTPS`, `Communication Method: Pull`. Not
DATEX II for this specific dataset, despite the platform's general DATEX
branding elsewhere on the site (page CSS is full of `datex-*` class names).

**Access:** Registration — a "creati-cont-utilizator" (create user
account) page exists site-wide; the specific "Drumuri închise" record
itself didn't state an authentication requirement beyond the general site
account.

**Licence — a real, if unhelpful, structured answer.** The metadata
record's own `Contract or Licence` field literally reads: **"Not
relevant."** The site-wide Terms and Conditions, separately, take a real
default-closed stance (Romanian, verbatim):

> *"Nu puteți utiliza conținutul din cadrul Serviciilor noastre, cu
> excepția cazului în care obțineți permisiunea noastra sau a
> proprietarului conținutului sau dacă legea permite acest lucru."*
> ("You may not use the content within our Services, except when you
> obtain our permission or that of the content owner, or if the law
> permits it.")

So: a metadata field that shrugs off the question, sitting next to a site
policy that defaults to "ask first" — worth flagging as a real gap between
what a machine-readable catalogue states and what the human terms actually
require.

**Endpoint:** `https://pna.cestrin.ro/file-geojson/rest/services/roads_closed/featureserver`
— found in the metadata record, live-tested, and currently returns
**HTTP 500** (server error, not an auth rejection).

**Confidence:** Documented; the one concrete endpoint found is currently
broken, so nothing here reached "verified live."

---

## Tier 2 cross-cutting notes

- **Two fully live-verified, zero-friction results**: Belgium (Flanders
  DATEX II v3, 70+14 real roadworks records) and Luxembourg (DATEX II v2.3,
  178 real MaintenanceWorks records) — both completely open, no
  registration, no key, real current data confirmed by counting situation
  types directly out of the payload rather than trusting a description.
- **Estonia is the most important single finding in this batch**: the
  *documented* access process (register, wait for admin approval, get an
  API key) and the *actual* live endpoint (fully open, zero auth, 316 real
  roadworks records) flatly disagree. This survey reports the discrepancy
  rather than picking whichever answer looks better — a future
  implementation would need to decide deliberately whether to rely on
  behaviour that contradicts the platform's own stated policy.
- **A second real licence discrepancy, same shape as Saxony-Anhalt's**:
  Estonia's dataset states CC BY-**NC** 4.0 in its own structured metadata,
  while a general description of the same catalogue claims commercial use
  is fine. The structured, dataset-level field is the one trusted here.
- **Two access models genuinely outside the registration/agreement/mTLS
  spectrum seen in Tier 1**: Switzerland's reciprocal "give data back if
  you monetise it" model, and Italy's requirement for SPID (a national
  digital identity, not just an account). Neither is a simple "open" or
  "closed" — both need their own real evaluation before building against.
- **Two NAPs were infrastructurally broken, not just hard to parse**: the
  Czech Republic (connection timeout, every path, both related domains)
  and Greece (expired TLS certificate *and* a 502 from the backend API).
  Both are `unknown`, and both are worth a quick re-check before writing
  either off — a dead server today doesn't mean a dead server at
  implementation time.
- **A quiet pattern worth naming**: general national open-data portals
  (Portugal's dados.gov.pt, Latvia's data.gov.lv) kept surfacing real,
  CC-licensed, sometimes live-pullable *catalogue entries* for a NAP's own
  data even when the NAP's own dedicated portal was an unreadable SPA.
  This mirrors Tier 1's Lithuania/Malta pattern closely enough that it's
  worth stating as a general heuristic for future batches: when a
  country's dedicated NAP is a JS wall, check that country's *general*
  open-data portal for the same organisation's datasets before concluding
  "unknown."
- **DATEX II version spread continues**: v2.0 (Estonia), v2.3 (Luxembourg,
  Italy, Croatia's B2B profile, Poland's earlier profile), v3.0 (Croatia),
  v3.2 (Hungary, mid-transition), v3.3 (Hungary's newest), v3.4 (Poland,
  migrated Sept 2024), and Belgium's confirmed-live v3 (exact minor version
  not checked). As in Tier 1: reconfirm at build time, never assume from
  this survey.

---

## Tier 3 — batch 3 (Bulgaria, Cyprus)

Two countries, and — like Belgium, Luxembourg, and Estonia in Tiers 1–2 —
both produced fully live-verified, open, no-authentication DATEX II feeds
with real current data pulled directly. Bulgaria is a clean confirmation;
Cyprus surfaced a genuinely important nuance about *how* roadworks content
is (or isn't) machine-typed, worth reading past the "yes, roadworks" verdict.

### Summary table

| Country | Roadworks? | Format | Access | Licence (short) | Confidence |
|---|---|---|---|---|---|
| Bulgaria | Yes | DATEX II v2.3, XML | Open, no auth (`datasheet.api.bg`) | Not stated on-site; secondhand-only text from an unreachable subdomain | **Verified live** (14 real `Roadworks` records, file regenerated same-day) |
| Cyprus | Content present, **not type-confirmed** | DATEX II v3, XML | Open, no auth | CC BY 4.0 | **Verified live** (real construction/maintenance content in free text; all 97 records typed as generic, not `Roadworks`) |

---

### Bulgaria — lima.api.bg, datasheet.api.bg

**RTTI NAP:** `lima.api.bg` (as listed) is **unreachable** — connection
refused on both HTTP and HTTPS, consistently, across multiple attempts.
`datasheet.api.bg`, the second URL given, resolves and works fully; it
appears to be the actual public-facing catalogue/download front for the
same LIMA platform (Road Infrastructure Agency, "Агенция „Пътна
инфраструктура""), with `lima.api.bg` reserved for the dashboard/login
side (a `/dashboard` and `/privacy/index` path were found by search but
not reached directly).

**Roadworks?** Yes — confirmed **live, directly out of the payload**, not
inferred. The catalogue lists a dedicated "roadworks" category with three
real entries: **"Closed Roads"** (`r01`), **"Closed Roadways"** (`r02`),
and **"Short-term Road Construction"** (`r03`). The "Closed Roads" dataset
page states its own purpose plainly (English and Bulgarian both read):

> English: *"This document contains information on the closed roads in
> the Republican Road Network of the country, as well as detailed
> information on the reasons for their closing."*
>
> Bulgarian: *"Този документ съдържа информация за затворени пътища по
> републиканската пътна мрежа в страната, както и подробна информация за
> причината за затваряне."*

**Format:** DATEX II **v2.3** — confirmed directly from the live file's own
schema location, `DATEXIISchema_2_2_3.xsd`. XML, UTF-16 encoded (unusual —
most DATEX II feeds seen in this survey are UTF-8).

**Access — fully open, no authentication.** The dataset page links a
concretely-dated download file
(`/files/20260725_roadworks_r01.xml`, timestamped the same day as this
check), not a generic "call an API" instruction. Fetched directly:
```
GET https://datasheet.api.bg/files/20260725_roadworks_r01.xml
→ HTTP 200, real current data, publicationTime matched the fetch time
```
Counted `xsi:type` occurrences directly in the payload: **14 real
`Roadworks` situation records** (plus matching `Point` location records —
one per situation). Stated update frequency on the catalogue page:
**"15 minutes."**

**Licence:** Genuinely thin. No CC badge, licence name, or terms text
anywhere on `datasheet.api.bg` itself — only a bare copyright line, *"©
2020 Road Infrastructure Agency"*, linking to `http://api.bg`. A real
terms-of-use page was located by search
(`https://lima.api.bg/privacy/index`), and a search-result summary of its
cached content mentions liability disclaimers ("excluding responsibility
for losses and damages of any kind arising from or connected with using
the provision") — but since `lima.api.bg` itself could not be reached
directly by this tool, **this text is reported as secondhand, not
independently verified**, consistent with how this survey has treated
every other unreachable-primary-source case.

**Endpoint:** `https://datasheet.api.bg/files/20260725_roadworks_r01.xml`
— live-verified, open. Note the filename is date-stamped, so the exact URL
changes; the stable entry point is the catalogue page
(`https://datasheet.api.bg/?lang=en&g=roadworks&c=r01`), not the file URL
itself.

**Confidence:** Verified live for content and format. Licence is the one
open question, and honestly so — the page that would answer it definitively
is unreachable, not merely un-checked.

---

### Cyprus — traffic4cyprus.org.cy

**RTTI NAP:** https://traffic4cyprus.org.cy (matches the brief's listing),
branded "CyNAP." A CKAN-shaped catalogue (42 datasets across three pages at
time of check), all from a small set of real providers (Public Works
Department dominant, plus Waze, Nextbike Cyprus, and Bolt as private
data-sharing partners).

**Roadworks?** Content-level yes, **type-level no** — a real, precise
distinction worth keeping, not rounding up. The relevant dataset,
**"Traffic Events"**, describes itself simply: *"Export live traffic
events, as they have been inserted into the platform."* Live-fetched
directly:
```
GET https://www.traffic4cyprus.org.cy/swarco3/api/Data/SituationPublication
→ 200, real current data (publicationTime matched the fetch time),
  124,331 bytes, 97 situation records
```
Every one of those 97 records is typed **`GenericSituationRecord`** — none
use DATEX II's specific `Roadworks`/`ConstructionWorks`/`MaintenanceWorks`
subclasses the way Belgium, Bulgaria, Denmark, Luxembourg, Poland, and
Estonia's feeds all did elsewhere in this survey. Searching the free-text
`description` fields inside those generic records, however, turns up real
roadworks content: **23 mentions of "construction," 7 of "maintenance,"**
including a genuine example — *"Pipeline construction works will be
carried out by the Water Development Department..."* So the data is
there; a consumer would need to parse free text (or a category/subtype
field not surfaced in this check) to isolate roadworks specifically,
rather than filtering cleanly on `situationRecord` type the way most of
this survey's other DATEX II feeds allow.

**Format:** DATEX II **v3**, confirmed both from the catalogue page's own
stated field and from the live payload's namespace
(`http://datex2.eu/schema/3/situation`, `d2Payload`).

**Access:** Fully open, no authentication — the endpoint above answered a
plain unauthenticated `GET` immediately.

**Licence:** **CC BY 4.0**, stated uniformly across every one of the 20+
datasets checked on the catalogue listing (Public Works Department's own
feeds, and the third-party Waze/Nextbike/Bolt ones alike) — the most
consistent, unambiguous licence picture of any NAP checked in this survey
so far; no per-dataset variation found.

**Endpoint:** `https://www.traffic4cyprus.org.cy/swarco3/api/Data/SituationPublication`
— live-verified, open, no auth. ("swarco3" in the path names Swarco, a
real ITS vendor — the platform is presumably a vendor-operated system
behind the government's own branding, consistent with how several other
NAPs in this survey turned out to be run by a named integrator rather than
built in-house.)

**Confidence:** Verified live for access, format, and licence. Roadworks
*content* is verified live too — but the *type-safety* of isolating it
programmatically is not, and that distinction is the real finding here,
not a footnote to it.

---

## Tier 3 cross-cutting notes

- **Both countries produced fully open, live-verified DATEX II pulls** —
  no registration, no key, real current data confirmed directly out of the
  payload. That makes five NAPs across this whole survey (Belgium,
  Luxembourg, Estonia, Bulgaria, Cyprus) where the actual live behaviour,
  not just the documentation, was confirmed open.
- **Cyprus is the survey's clearest example of a distinction worth
  carrying forward**: "does the feed carry roadworks content" and "can a
  consumer cleanly filter for roadworks by type" are two different
  questions, and this batch is the first time they came apart this
  visibly. Every other confirmed-yes DATEX II feed in this survey (Belgium,
  Bulgaria, Denmark, Luxembourg, Poland, Estonia) used the specific
  `Roadworks`/`ConstructionWorks`/`MaintenanceWorks` subtypes; Cyprus uses
  the generic record for everything and relies on free text. A future
  implementation against Cyprus specifically would need a text-matching
  strategy, not just a type filter — flagged here so that isn't discovered
  the hard way during a build.
- **`lima.api.bg` vs `datasheet.api.bg` is the same "which subdomain
  actually serves the public" pattern already seen twice in this survey**
  (Slovenia's `b2b.ncup.si` vs `b2b.nap.si`; Estonia's `tarktee.mnt.ee` vs
  `tarktee.transpordiamet.ee`). Worth a standing reminder for future
  batches: when a listed NAP domain doesn't answer, try the sibling domains
  search turns up before concluding `unknown` — one of the two often does.
