# Street Manager Open Data archive — live probe record (2026-10-28)

What was checked against `https://opendata.manage-roadworks.service.gov.uk`
before `streetworks.opendata.archive` was built, and what each result decided.
Everything here was observed live on 2026-10-28; nothing is inferred from
documentation alone.

## The host

S3 (bucket `prod-sm-archived-notifications-48575862-eu-west-2`) behind
CloudFront. The DfT [Archived notifications](https://department-for-transport-streetmanager.github.io/street-manager-docs/archived-notifications)
page is a small Vue app that reads the bucket listing directly.

| Probe | Result | Decided |
|---|---|---|
| `HEAD permit/2026/09.zip` | `200`, `Content-Type: application/zip`, `Content-Length: 1044935949`, `Accept-Ranges: bytes`, `ETag`, `Last-Modified` | Downloads stream and can resume |
| `HEAD` on a missing month (`permit/2026/12.zip`, `permit/2019/12.zip`, unknown topic) | `404` (not `403`) | `available()` treats 404 as "not published"; any other error raises |
| `GET /` and `GET /?list-type=2&prefix=...` | Public `ListBucketResult` (V1 and V2, with continuation tokens) | `files()` lists what's published rather than probing URLs |
| `Range: bytes=N-` | `206` | Resume works |
| `Range` + matching `If-Range: <etag>` | `206`; with a stale `If-Range`, `200` and the whole file | Resume is guarded against the file changing mid-download |
| MD5 of the downloaded `activity/2026/09.zip` and `section_58/2026/09.zip` | Equal to their `ETag`s; no `ETag` in the listing has a multipart `-N` suffix | `download()` verifies against the `ETag` |

## Coverage and publication

The full listing is 203 keys, all `{topic}/{yyyy}/{mm}.zip`:

| Topic | Months | Range | Gaps | Total |
|---|---|---|---|---|
| `permit` | 75 | 2020/07–2026/09 | none | 70.98 GB |
| `activity` | 73 | 2020/09–2026/09 | none | 0.48 GB |
| `section_58` | 55 | 2022/03–2026/09 | none | 0.11 GB |

Each month normally appears on the 1st of the following month, 08:00–09:45
UTC (2026/07, /08 and /09 all did); 2026/06 appeared on 21 July. All 34
files for 2020–2021 months carry 2022 `LastModified` dates, so the archive
only began in 2022 and its first years were uploaded then.

Months are cut at **UK local midnight**: the 2026/08 `section_58` file holds
one event at `2026-07-31T23:19:59Z` (00:19 BST on 1 August).

## Contents

- **One event per member, the live feed's envelope.** Every member in the
  2026/09 `activity` (16,531) and `section_58` (3,764) files, and in 183
  members sampled across the 2026/09 `permit` file, is a JSON object with
  exactly `event_reference`, `event_type`, `event_time`, `object_type`,
  `object_reference`, `version` and `object_data`. No unparseable members, no
  folders.
- **Matches DfT's schema.** Every `object_data` key seen is in DfT's
  [Event Notifier Message JSON Schema](https://department-for-transport-streetmanager.github.io/street-manager-docs/api-documentation/json/event-notifier-message.json),
  and the event types seen are exactly the schema's 18 (11 permit/work, 3
  activity, 4 section 58).
- **Member names** follow
  `{object_reference}_{event_type lowercased}_event_{yyyy-mm-dd}_{HH-MM-SS}-{n}.json`.
  Two reasons the SDK doesn't parse them: permit references can contain
  underscores (e.g. `..._1-01_permit_submitted_event_...`), so splitting is
  ambiguous; and the trailing `{n}` isn't milliseconds but the minute and
  second run together unpadded (`12-40-33-4033`, `11-15-09-159`).
- **Filter fields are strings.** `usrn`, `highway_authority_swa_code`,
  `promoter_swa_code`, `area_name` and `activity_type` are strings in every
  topic. Activity and section 58 events have no promoter fields; section 58
  events have no `activity_type`.
- **No personal data fields.** None of the `object_data` keys hold contact
  details, so real members can be committed as fixtures.

## Duplicates

None found: no repeated `(object_reference, event_type, event_time)` and no
repeated `event_reference` within any of the 2026/08 and 2026/09 `activity`
and `section_58` files, and no overlap between the two months on either key.
The guard in `KFergusonUK/RemedialWorksVisits`'s `remedial_works.py` reads
loose `.json` files alongside zips in the same folder, so it protects against
an extracted member being counted twice - not against anything in DfT's
files. So the SDK doesn't de-duplicate; `event_reference` is unique if a
caller mixes sources. Not checked for `permit` across months (it would need
two 1 GB downloads).

## The permit file, read over HTTP ranges

`permit/2026/09.zip` was opened with `zipfile` through a range-backed file
object, fetching about 137 MB rather than 1 GB:

- **ZIP64**, 1,081,996 members, a 125 MB central directory.
- **Memory:** `zipfile.ZipFile` held 723 MB after opening (865 MB peak),
  measured with `tracemalloc`. This is the cost `iter_events()` documents for
  a permit month.
- **Every member uses a data descriptor** (general-purpose flag bit 3), all
  deflate. A constant-memory reader that walks local headers instead of the
  central directory is possible, but it has to find each member's end by
  decompressing it, since the local headers carry no sizes. Not built.

## SNS filter attributes

The live feed's `MessageAttributes` are `area`, `ha_org`, `activity_type`,
`promoter_org` and `usrn`. DfT's sample notification shows `ha_org` and
`promoter_org` carry SWA codes (`5990`, `STPR`), so `iter_events()`'s filters
of the same names match `highway_authority_swa_code` and `promoter_swa_code`,
not the organisation names.

## Licence

The archive host states none. The DfT docs page that hosts the archive browser
carries the site footer "All content is available under the Open Government
Licence v3.0, except where otherwise stated", and nothing on the page states
otherwise. The archive needs no registration, unlike the live SNS feed, whose
sign-up includes accepting terms of use.
