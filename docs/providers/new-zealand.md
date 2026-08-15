# New Zealand

> Migrated verbatim from README.md's `## NZTA & LINZ (New Zealand)`
> section (phase one, lossless restructure — see
> `docs/migration-mapping.md`).

This SDK's first New Zealand coverage — two separate top-level packages,
not one combined `nz` package, matching how `streetworks.kartverket`/
`streetworks.nvdb` split Norway by publisher rather than lumping the
country together: `streetworks.nzta` (works) and `streetworks.linz`
(gazetteer) are different agencies, different technologies, and (as
detailed below) do **not** join to each other.

```python
from streetworks.nzta import NztaClient
from streetworks.common import from_nzta

with NztaClient() as nzta:
    works_list = from_nzta(list(nzta.iter_roadworks()))

from streetworks.linz import LinzClient
from streetworks.common import from_linz_address

with LinzClient() as linz:
    addresses = [from_linz_address(f) for f in linz.iter_addresses(where="1=1")]
```

**NZTA (Waka Kotahi) Highway Information — Road Events, confirmed live
2026-08-02 (104 real records), credential-free.** A real correction to
the source investigation: this is the ArcGIS open-data portal service
(`opendata-nzta.opendata.arcgis.com`), not the bespoke `trafficnz.info`
REST/SOAP API also considered early on — reuses the same
`ArcGISFeatureClient` every AU ArcGIS provider does. Two real layers share
an identical field schema but never overlap: layer 0 ("Road Events",
point, 104 real records) is roadworks-relevant; layer 1 ("Road Area
Events", polyline, 53 real records) is **always** `eventType=="Area
Warning"` — a weather/hazard concept, not roadworks — so this client stays
point-only, no Victoria/QLD-style corridor trap. **The richest real
status→confidence signal confirmed anywhere in this SDK**: real `status`
(`Scheduled`/`Active`/`Resolved`) correlates perfectly with `eventType` in
a full live pull, giving a genuinely evidenced VERIFIED/ESTIMATED split —
every AU provider built so far lacked a signal this clean. National state
highways only, licensed **NZTA 4.0 BY CC** (a CC BY 4.0 variant).

**No structured road/route identifier anywhere in NZTA's real schema —
settles the works-to-LINZ join question directly.** The real fields
(`locationArea`, `directLineDistance1`–`3`, `alternativeRoute`) are free
text only (e.g. `"SH 80 Pukaki to Mt Cook (Aoraki Mt Cook Highway)"`), so
`from_nzta` never populates `WorksSite.street_ref` — a name-match
crosswalk would be inferred, not stated, the same SA-`ROAD_NO` discipline
this SDK holds everywhere. LINZ stands on its own as this cluster's
gazetteer.

**LINZ (Toitū Te Whenua) NZ Addresses, confirmed live 2026-08-02
(2,421,642 real addresses, per the layer's own `feature_count`),
credential-free.** A public ArcGIS Online mirror of the current NZ
Addresses family (layer 123113) needs no LINZ Data Service key at all —
licensed **CC BY 4.0**, confirmed from both the Koordinates layer metadata
and the ArcGIS item's own `licenseInfo` independently. A real,
newly-discovered `unit`/flat-number concept is present (e.g. `"2"` in
`"2/49 Pigeon Mountain Road"`) that this SDK's own `Address` model
docstring already flagged as absent from every source built so far — no
canonical field exists for it yet, so it stays on `.raw` only, alongside
`is_land` (a real boolean concept the live layer definition states as
`esriFieldTypeString` length 2, so real values are the truncated `"tr"`/
`"fa"`, not `true`/`false`).

**NZ Addresses: Roads/Road Sections (the `streets` counterpart) is a
Phase 1 scaffold — the sibling `iter_addresses()` above is already
verified, this is a narrower gap.** Schema and a real attribute sample
(not geometry) are both confirmed live from LINZ's own public Koordinates
metadata API, but the actual WFS pull has never been exercised: it needs a
genuine LINZ Data Service (LDS) API key this build doesn't have. The real
URL shape is documented and implemented — Koordinates embeds the key in
the URL **path** (`services;key={api_key}/wfs/`), confirmed live from the
layer's own `/services/` listing — see
[Credentials wanted](index.md#credentials-wanted) for the fuller writeup,
including the single most interesting open question in this cluster:
whether `road_id` genuinely cross-references between NZ Addresses and
Roads/Road Sections (the field name is identical across all three layers'
schemas; the real samples pulled so far just happen not to overlap).
