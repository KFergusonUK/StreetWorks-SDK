# Provider quirks — index

> This is a navigational index, not a duplicate copy. Every finding
> listed here is migrated verbatim from README.md into a specific
> [`docs/providers/`](../providers/index.md) or
> [`docs/concepts/`](../concepts/architecture.md) page — follow the link
> for the full write-up. Collected here because these are the hard-won,
> easy-to-lose findings a future tidy-up is most likely to flatten or
> drop; see `docs/migration-mapping.md` for the full checklist-to-file
> mapping this index is drawn from.

## Corrections to a source brief, found live

- **DGT/Consell de Mallorca overlap** — first documented "genuinely additive, not a duplicate," later found to be real republication overlap on at least some records. [`docs/concepts/data-model.md#never-deduplicate-across-providers`](../concepts/data-model.md#never-deduplicate-across-providers), [`docs/providers/europe.md#consell-de-mallorca-island-roadworks`](../providers/europe.md#consell-de-mallorca-island-roadworks).
- **Berlin VIZ's two feeds** — officially documented as "Verkehrsredaktion is a subset of Landesmeldestelle with extra detail"; live data shows only ~50% overlap, each feed carrying real content the other lacks. [`docs/providers/europe.md#berlin-viz`](../providers/europe.md#berlin-viz).
- **Chicago CDOT's primary dataset id** — the source brief's own dataset id (`6fd2-pzze`) turned out to be dead (empty schema); the real, current dataset is `jdis-5sry`. [`docs/providers/us.md#chicago-cdot-street-closures`](../providers/us.md#chicago-cdot-street-closures).
- **NVDB's CRS** — design brief expected plain `EPSG:25833`; real data is the compound 3D `EPSG:5973`. [`docs/concepts/crs-and-datums.md`](../concepts/crs-and-datums.md).
- **Australia's road/address gazetteer** — the brief concluded no clean open national register existed (checking only Geoscape's commercial API); the Digital Atlas of Australia turned out to re-publish both, openly, under CC BY 4.0. [`docs/providers/australia.md#g-naf--national-roads-australia`](../providers/australia.md#g-naf--national-roads-australia).

## Non-WGS84 coordinate systems (full index)

See [`docs/concepts/crs-and-datums.md`](../concepts/crs-and-datums.md) —
Belgium (Lambert 72), Lithuania (LKS-94, reversed WKT axis order),
Saxony (`EPSG:25833`), Jersey (`EPSG:3109`), NYC (`EPSG:2263`), Tasmania
(GDA94/MGA55), QLDTraffic/G-NAF (GDA2020), Consell de Mallorca
(`EPSG:25831`), NVDB (compound 3D `EPSG:5973`), Statens vegvesen (mixed
CRS within one feed).

## DATEX II parser fixes surfaced by real feeds, not synthetic tests

- **`tpeglinearLocation` (lower-case)** — the Basque Country's genuine DATEX II v1.0 feed uses this spelling; the shared parser only recognised the v2/v3 PascalCase form, silently degrading a real 2-point line to a single point. [`docs/providers/europe.md#basque-country-euskadi`](../providers/europe.md#basque-country-euskadi).
- **`alert_c_location` name preference + TPEG linear from/to geometry** — both fixed on France's real feed. [`docs/providers/europe.md#datex-ii-european-roadworks`](../providers/europe.md#datex-ii-european-roadworks).
- **A discriminator gap** (DGT has zero `MaintenanceWorks`/`ConstructionWorks` records) and **a second, differently-shaped one** (Belgium's generic-value case) and **a third, distinct discriminator type** (Bulgaria's bare `Roadworks` xsi:type) — all in [`docs/providers/europe.md#datex-ii-european-roadworks`](../providers/europe.md#datex-ii-european-roadworks).

## Licence findings

See [`docs/governance/licensing.md`](../governance/licensing.md) for the
full index.

## Stated-identifier joins that genuinely exist (contrast with the
## "never a name match" discipline)

See [`docs/concepts/data-integrity.md`](../concepts/data-integrity.md) —
NWB's `bag_orl`, BD TOPO's `identifiant_voie_ban`/`id_ban_odonyme`,
Norway's NVDB↔Kartverket `adressekode`.
