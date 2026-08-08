# Italy

> Migrated verbatim from README.md's `## Italy — CCISS (traffic bulletin
> RSS)` section (phase one, lossless restructure — see
> `docs/migration-mapping.md`).

## CCISS (traffic bulletin RSS)

Confirmed as Italy's own official RTTI/SRTI National Access Point (per
the European Commission's own October 2025 National Access Points
list), reached here via the real, public, **keyless** RSS route rather
than the registration-gated DATEX II one:

```python
from streetworks.cciss import CcissClient
from streetworks.common import from_cciss

with CcissClient() as cciss:
    roadworks = [i for i in cciss.fetch() if i.is_roadworks]
    works_list = [from_cciss(i) for i in roadworks]
```

**Genuinely different shape from TrafficWatchNI/Traffic Wales, despite
looking similar** — those two already serve roadworks-only feeds (see
[`docs/providers/uk.md`](uk.md)); CCISS
publishes one real, mixed stream (roadworks, weather, breakdowns,
accidents, demonstrations, debris/spill incidents), confirmed live 100
real items at a time, 78 of them real roadworks. Filtering happens via
`item.is_roadworks` — a real, evidenced classification (contains
`lavori`/`personale su strada`/`pulizia del manto stradale`), not a
closed enum, since the real event-type text is free Italian prose with
too much genuine variety to force into one (`manifestazione`, `veicolo
fermo o in avaria`, `tratto chiuso causa lavori`, `perdita di carico`,
...).

**No geometry** — the real feed carries only `title`/`description`/
`pubDate`/`dc:date`, confirmed directly against the live XML (an
earlier AI-summarised read of the CCISS homepage wrongly suggested items
were georeferenced; the real RSS feed isn't).

The registration-gated DATEX II route (same `cciss.it` domain, richer
structured data under RTTI) remains available as a separate, later
option if you register — not pursued here. **Licence unconfirmed** — no
reuse licence was found stated for this feed.
