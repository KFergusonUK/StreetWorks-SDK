# Asia

This SDK's first Asian territory. See [`docs/providers/index.md`](index.md)
for the authoritative live/verified status table.

## LTA DataMall (Singapore) — Credentials wanted

Singapore's Land Transport Authority runs a real, well-documented national
open-data platform, LTA DataMall. Found while asking whether any more
country-level roadworks gaps existed beyond Europe — see
[`docs/roadmap.md`](../roadmap.md) and
[`docs/findings/europe-gaps.md`](../findings/europe-gaps.md) for the wider
survey this sits alongside.

```python
from streetworks.singapore import SingaporeClient
from streetworks.common import from_singapore

with SingaporeClient(account_key=account_key) as client:  # doctest: +SKIP
    works_list = from_singapore(list(client.iter_roadworks()))
```

**Better-confirmed than most Credentials-wanted scaffolds in this SDK.**
Built entirely from LTA's own current, official documentation — the "LTA
DataMall API User Guide & Documentation", Version 6.9 (3 Aug 2026), fetched
live — and the auth mechanism itself was confirmed live, not just
documented: a `GET` with a placeholder `AccountKey` header returns a real
`401` on both real endpoints (`RoadWorks`, `TrafficIncidents`), not a `404`
— confirming the real paths and the real header name, short of a real
authenticated response.

**Three real, genuinely different-shaped datasets, not one:**

- **`RoadWorks`** ("Approved Road Works") — road works currently
  approved/being carried out. Real fields: `EventID`, `StartDate`,
  `EndDate` (`YYYY-MM-DD`), `SvcDept` (the department or company performing
  the work — a real applicant-style field, the same role Vienna's/NYC
  DOT's own applicant fields already play in this SDK, mapped to
  `Works.promoter`), `RoadName`, `Other` (free text). **No coordinates at
  all** — a real, documented gap. Updated every 24 hours.
- **`RoadOpenings`** ("Planned Road Openings") — the identical real field
  shape, a genuinely separate dataset (new-road-opening events, not
  works-in-progress). Also no coordinates, also 24-hour updates.
- **`TrafficIncidents`** — a live, 2-minute-update feed of current road
  incidents, a genuinely different shape again: `Type` (a real, explicit
  13-value enum — `Accident`, **`Roadwork`**, `Vehicle breakdown`,
  `Weather`, `Obstacle`, `Road Block`, `Heavy Traffic`, `Miscellaneous`,
  `Diversion`, `Unattended Vehicle`, `Fire`, `Plant Failure`, `Reverse
  Flow`), `Latitude`/`Longitude` (real point coordinates, unlike the other
  two datasets), and `Message` (free text). **No id field and no dates at
  all** — a real gap in the opposite direction from `RoadWorks`/
  `RoadOpenings`. `Type == "Roadwork"` is the real, spec-stated roadworks
  filter for this dataset.

`SingaporeClient.iter_roadworks()` combines all three: every real
`RoadWorks`/`RoadOpenings` record, plus `TrafficIncidents` filtered to
`Type == "Roadwork"`.

**Pagination**: real OData envelope, `{"odata.metadata": ..., "value":
[...]}`, capped at 500 records per call — documented explicitly: append
`?$skip=500`/`$skip=1000`/... for subsequent pages. The client loops until
a page comes back short of 500 records.

**Licence: Singapore Open Data Licence v1.0** — confirmed via LTA's own
published licence page: worldwide, perpetual, royalty-free, non-exclusive,
commercial use explicitly permitted. Rate limit 10,000,000 calls/day (LTA's
own stated API Terms of Service figure).

**Credentials**: free self-service registration ("Request for API Access"
on [datamall.lta.gov.sg](https://datamall.lta.gov.sg/content/datamall/en.html))
issues a single `AccountKey` header value — not a formal contract, but not
obtained on the user's behalf either. Env var: `SINGAPORE_LTA_ACCOUNT_KEY`.

**What's still open until a real key is used**: whether the
empty/short-page pagination end-condition is correct in practice; whether
`SvcDept`/`Other`/`Message` ever carry structured data beyond free text;
real record volumes for `RoadWorks`/`RoadOpenings`. Have a key? Running
`scripts/smoke_test.py` and reporting back one real trimmed record from
each dataset would confirm this adapter — see the "help wanted" issues at
<https://github.com/KFergusonUK/StreetWorks-SDK/issues>.
