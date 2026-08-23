# Japan — research notes (2026-08-23)

Research only. Nothing built — no module, no client, no tests. Prompted by
"what about Japan, I bet they have a good roadworks feed" as a detour from
the Europe gaps pass (see [`docs/findings/europe-gaps.md`](europe-gaps.md)).
A real, promising, live, keyless source was found (MLIT's own
construction-schedule feed), but it's genuinely more complex than any single
provider built so far in this SDK — explicitly parked for a dedicated future
session rather than scoped down and rushed.

## Checked and ruled out — wrong category, not roadworks

**JARTIC's own "オープンデータ" (open data) page**
(`jartic.or.jp/service/opendata/`) offers four real per-prefecture ZIP
datasets (types B/C/D/M), all monthly-updated (not real-time), genuinely
keyless. The real config listing all 47-prefecture download links is at
`https://www.jartic.or.jp/d/opendata/opendata.json` (found via the page's
own `opendata.js`, not documented on the page itself).

**typeD ("交通規制情報"/traffic regulation information) — the one that
sounded most like roadworks — is confirmed the wrong category.** Downloaded
and inspected the real Tottori prefecture file (25,136 real rows, 170
columns, Shift-JIS-encoded CSV, `csv.reader` after `.decode('shift_jis')`).
The real `県別規制種別名称` (regulation-type name) distribution:

```
一時停止 (stop sign)                    9,967
横断歩道 (pedestrian crossing)           5,513
指定方向外進行禁止 (no-entry-except-dir) 1,726
最高速度（区間） (speed limit, section)  1,304
信号機の設置場所 (signal light location) 1,301
駐車禁止 (no parking)                      967
車両通行帯 (vehicle lane designation)      831
...
```

This is Japan's national **police-issued permanent traffic-sign register**
(built for a SIP — Strategic Innovation Promotion program — autonomous-
driving-support research effort), not a temporary works/closures feed. No
"工事" (construction) or "通行止め" (road closed) value appeared anywhere in
the real type list for this prefecture. A genuine, confirmed wrong-category
finding — the same class of miss as Georgia's ArcGIS Hub or NRW's
road-network data in earlier sessions of this SDK.

**NEXCO East's own real, keyless `TrafficAPI`**
(`driveplaza.com/dp/TrafficAPI`, found by reading the site's own
`roadinfo.js`, which states `url: '/dp/TrafficAPI'`) is real and live, but
only returns coarse per-region summary counts:

```json
{"area": "九州", "url": "https://www.drivetraffic.jp/realtime-area?...", "count": "7", "status": "通行止あり"}
```

Too coarse to build a `Works`-per-record provider from — no individual
record locations, dates, or descriptions.

**`drivetraffic.jp`** (NEXCO/JARTIC's joint real-time map, linked from the
TrafficAPI response) is a complex proprietary Angular app built on a
commercial Japanese map-tile vendor's API (`its-mo.com`, key
`JSZcaedc53a858b|uIdAD` embedded in the page, apparently already public).
Checked its own runtime config endpoint (`/config_app`) for a data API —
found only branding/session config, no direct data URL. Not fully resolved;
the real point-level data likely lives inside the compiled `main-*.js`
bundle or behind the its-mo.com map layer itself. Not traced further once
the MLIT lead below was found.

## The real, promising lead — not built, parked for a dedicated session

**MLIT's own "道路情報提供システム" (Road Information Provision System)**,
`road-info-prvs.mlit.go.jp` — run by JARTIC on MLIT's behalf (confirmed via
an `Access-Control-Allow-Origin: https://www.jartic-ri2maps.org` CORS header
on the root page). Genuinely separate from JARTIC's own wrong-category
opendata above — this is MLIT's road-administrator side, not the police-
regulation side.

Traced through the map app's own JS the same way Brussels/Romania were
found:

1. The page (`roadinfo/pc/pcTukokisei_81_1.html`) loads `Tukokisei.js`, a
   Leaflet-based map controller.
2. `Tukokisei.js` builds data URLs as
   `{CREATE_JSON_PATH}{dataset}/{meshCode}.json`, where `dataset` is one of:
   - `TukoKisei` — current traffic regulations
   - `TokiTuko` — winter-season regulations
   - **`KojiYotei`** — "工事・行事予定実施" (construction/event schedule
     execution) — the real roadworks-relevant one
3. `meshCode` is a real **JIS X0410 "1次メッシュ" (primary mesh)** code — an
   ~80km grid covering Japan. Derived from the app's own real
   `getPrimaryMeshCd(lat, lon)` formula:
   `floor(lat * 1.5)` concatenated with `floor(lon - 100)`. Tokyo
   (35.68°N, 139.76°E) → mesh code `5339`.
4. `CREATE_JSON_PATH` itself is **a rotating, timestamped, randomly-named
   directory** — e.g. `backup/20260823163500/6cod3rp1i7P9gLjf/` — regenerated
   periodically. It's only discoverable by first fetching a small dedicated
   JS file that defines the constant:
   `{page-dir}/../backup/{timestamp}/{random}/A7bsTtYx.js` (the exact
   filename `A7bsTtYx.js` is itself embedded in the page's own `<script src>`
   tag — it changes too, so it has to be read fresh from the HTML each time,
   not hardcoded). This reads as a real anti-scraping/cache-busting
   mechanism, not a stable path a client could hardcode.

**Confirmed live 2026-08-23** for Tokyo's mesh (`5339`): `KojiYotei` returned
213KB / 200 real records with genuine `LineString` geometry (embedded as a
`geo_json` string property per record, real WGS84 coordinates) and real
per-record unique ids (`same_tukokisei_info_id`, e.g.
`"2432441e3b0aa701"`). Real fields on one sample record:

```json
{
  "kisei_kaishi_nichiji": "2026-08-22 20:25:00",
  "kisei_naiyo_cd": "05",
  "kisei_naiyo_shosai_cd": "001",
  "genin_jisho_cd": "05",
  "kisei_jishi_jyokyo": "1",
  "doro_cd": "3",
  "same_tukokisei_info_id": "2432441e3b0aa701",
  "is_country": 1,
  "iconData": {"kisei_genin_syubetsu_cd": 5, "point": ["139.768702...", "35.684044..."]},
  "geo_json": "{\"type\": \"Feature\", ..., \"geometry\":{\"type\":\"LineString\",\"coordinates\":[...]}}"
}
```

**No free-text description field exists anywhere** — every field is a
numeric code (`kisei_naiyo_cd` regulation-content code, `genin_jisho_cd`
cause code, `kisei_jishi_jyokyo` implementation-status code,
`kisei_genin_syubetsu_cd` cause-type code). No official published code
legend was found. Partial meanings were reverse-engineered by reading the
app's own conditional rendering logic in `Tukokisei.js` — e.g.:

```js
} else if (kiseiType == 4) {
    // 車線規制 (lane regulation)
} else if (kiseiType == 5) {
    // 片側交互通 (one-side alternating traffic)
} else if (kiseiType == 6) {
    // チェーン規制 (winter tire chain regulation)
} else if ((kiseiType == 1 || kiseiType == 8) && (geninJishoType == 5 || 6 || 7)) {
    // 工事通行止(国道) - construction road closure (national road)
}
```

— i.e. `genin_jisho_cd` values `5`/`6`/`7` collectively render as
"construction-caused closure" when combined with certain `kisei_naiyo_cd`
values. This is real evidence, not a guess, but it's **not a complete or
authoritative mapping** — it only proves the values seen (`05`, `06`) fall
inside a set the app itself treats as construction-related, not what each
individual code specifically means on its own.

**Full national coverage means querying potentially hundreds of real mesh
tiles**, not one pull — Japan's populated land area spans many primary-mesh
cells. An actual tile-index/list wasn't found or fetched during this pass
(would need to be enumerated, or derived from the JIS mesh standard's own
published boundaries).

## Next steps, if picked back up

1. Find or derive the real list of populated mesh codes (rather than
   guessing coordinates tile-by-tile).
2. Look harder for an official 原因事象 (cause)/規制内容 (regulation-content)
   code legend — a PDF spec document, matching the pattern GDDKiA's own
   schema PDF and NEC's own C2C schema ZIP already provided for other
   providers in this SDK. Don't write field-mapping code against
   reverse-engineered partial meanings alone if an authoritative source
   exists.
3. Confirm the `CREATE_JSON_PATH` rotation cadence (how often does the
   directory change? does the old one 404 immediately, or stay valid for a
   grace period?) before designing the client's own fetch-then-fetch
   two-step flow.
4. Decide whether `TukoKisei` (current regulations, mixed causes) is worth
   pulling alongside `KojiYotei` (construction schedule) for the same reason
   NEC's `laneClosureData`/`incidentData` both got consumed — check whether
   ids overlap or are genuinely additive first.
