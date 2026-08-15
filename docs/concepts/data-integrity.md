# Data integrity discipline

> Assembled from README.md (phase one, lossless restructure — see
> `docs/migration-mapping.md`). Unlike `data-model.md` (one contiguous
> source section), this page collects a *recurring, real* discipline that
> the README states explicitly dozens of times across individual provider
> write-ups, rather than once in a single consolidated section. Every
> quotation below is verbatim from its named source section in
> [`docs/providers/`](../providers/index.md); nothing here is new prose
> synthesised for this migration.

## Verify live, never trust documentation alone

The recurring, load-bearing discipline behind nearly every provider
write-up in this SDK: build to the *documented* shape, then check it
against a real live pull before shipping, and correct the record when
reality disagrees. Representative, verbatim instances (see the full
per-provider detail in [`docs/providers/`](../providers/index.md)):

- NWB: *"Corrected an earlier WFS paging warning (an unencoded `+` in `outputFormat`, not a paging bug) but found a real one of its own: PDOK's WFS silently ignores `CQL_FILTER` entirely."*
- QLDTraffic: *"Two real doc-vs-reality mismatches, confirmed live... not implemented mechanically from the spec's own text."*
- Chicago CDOT: *"The obvious primary dataset id turned out to be dead — found live, not guessed."*
- Berlin (VIZ): *"The dataset's own official description says Verkehrsredaktion is 'a subset of Landesmeldestelle with extra detail.' Live data disagrees."*
- NVDB: *"CRS is EPSG:5973, not the initially expected EPSG:25833 — confirmed live on every real geometry checked."*
- G-NAF/National Roads: *"A real correction to the initial research. Australia was first thought to have 'no clean national open road-centreline register with identifiers.'... A separate, genuinely open publication route was missed at first."*
- BAG: *"Licence: CC0 1.0 Universal — confirmed from the Atom feed's own `<rights>` element, a correction to what was originally documented (Public Domain Mark 1.0 — a different, if similarly permissive, legal instrument)."*

This is not a one-off habit on hard cases — see
[`docs/providers/index.md`](../providers/index.md) for the "Status" section's
own full list of exactly which providers' authentication and read/consume
access has been verified against the real systems, and
[Recently confirmed](../providers/index.md#recently-confirmed) for the
standing record of what a tester's own real credentials changed when a
scaffold got promoted.

## Never silently reproject; state the CRS

See [`docs/concepts/crs-and-datums.md`](crs-and-datums.md) for the full,
provider-by-provider evidence. The recurring statement of the rule itself,
verbatim from where it appears:

- German state roadworks (Saxony): *"Rather than park a source this rich... over an axis-order technicality, Saxony ships with its real CRS carried through and labelled explicitly on `Coordinate.crs` — the same policy this SDK already uses for its British National Grid providers... a non-4326 CRS is never silently reprojected, just stated."*
- Consell de Mallorca: *"the server can reproject to WGS84 server-side on request (tested, genuinely correct), but per this SDK's standing CRS policy the native CRS is requested and labelled instead."*
- Belgium (DATEX II): *"`from_datex2()` gained a `crs` parameter (default `EPSG:4326`, true for every DATEX source checked before this one) so Belgium's real CRS can be stated explicitly rather than assumed — coordinates are carried through unconverted, per this SDK's standing CRS policy."*
- NYC DOT: *"Coordinates are NAD83 / New York Long Island, EPSG:2263 — inferred from real coordinate-value-range evidence... and never silently reprojected to WGS84, the same 'label honestly' discipline Tasmania's own real GDA94/MGA zone 55 geometry established for this SDK."*

## Stated-identifier joins only — never a name match

- TIGERweb: real identifiers are dataset-scoped; segments never aggregate under a synthesised named-street entity — *"checked, not assumed: no layer anywhere in the service aggregates segments under a named-street entity, so per the no-synthetic-streets rule this is the same shape as the Netherlands."*
- NWB: *"`Wegvak.toponyme_id()` returns `bag_orl` where present and `None` otherwise — it never falls back to the name, which would silently over-merge in exactly these real cases"* (7 of 385 real name-grouped street groups genuinely span two different real `bag_orl` values).
- Traffic SA (South Australia): *"Until confirmed, `WorksSite.street_ref` deliberately stays unpopulated from either field [`ROAD_NO`/`GIS_LINK_ID`] — this SDK doesn't wire unverified candidates into a gazetteer join, the same discipline as a name-match."*
- NZTA: *"free text only... so `from_nzta` never populates `WorksSite.street_ref` — a name-match crosswalk would be inferred, not stated, the same SA-`ROAD_NO` discipline this SDK holds everywhere."*
- NYC DOT: *"there is no LION `segmentid` (or any other street-register identifier) anywhere on this dataset — only free-text cross-street names, so `WorksSite.street_ref` is never populated, the same SA-`ROAD_NO`/NZTA discipline this SDK holds everywhere."*
- G-NAF & National Roads: *"the only possible link is a name match... forbidden by this SDK's stated-identifiers-only rule."*
- SRWR: states street identity at the *activity* level with no field joining a given street to a given phase, so `from_srwr` "deliberately leaves `street_ref` `None` rather than guessing which of possibly several real streets a phase belongs to" (see `docs/concepts/data-model.md`).

Contrast — where a **stated** (not inferred) join genuinely exists, it is
used: NWB's `bag_orl` (BAG's own `openbare_ruimte_identificatie`), BD
TOPO's `identifiant_voie_ban`/`id_ban_odonyme` (BAN's own compact
toponyme-id format and a street-level BAN UUID), Norway's NVDB `adressekode`
(the same identifier `streetworks.kartverket` already models). See
[`docs/providers/europe.md`](../providers/europe.md) for the full detail
behind each.

## No synthetic streets; Z coordinates preserved; no cross-provider dedup

These three are documented in full in
[`docs/concepts/data-model.md`](data-model.md) (the "No synthetic streets",
"Two additions to `Coordinate`", and "Never deduplicate across providers"
sections respectively) — not repeated here to avoid two homes for the same
text.
