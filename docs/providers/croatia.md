# Croatia

> This SDK's first Croatia coverage — confirmed live 2026-08-26. Found
> while checking whether Croatia had a real roadworks feed after Albania
> turned out a genuine dead end (see
> [`docs/findings/europe-gaps.md`](../findings/europe-gaps.md)). Full
> working notes for both, plus everything else found in this survey, in
> that same file.

## Hrvatske ceste (National Access Point) — Confirmed live

Croatia's national state-road roadworks source — genuine DATEX II v3,
published on Croatia's own National Access Point (NPT — Nacionalna
pristupna točka, a Realis ITS NAP platform deployment at
`promet-info.hr`), run for Hrvatske ceste (the state-road authority).
**Confirmed live 2026-08-26**: a real developer login (HTTP Basic)
round-tripped 85 real situations, all real `MaintenanceWorks` records,
through the shared DATEX II parser with zero code changes.

```python
from streetworks.datex2.croatia import CroatiaClient
from streetworks.common import from_datex2

# HTTP Basic (username/password) is confirmed correct; bearer_token
# remains a real, unconfirmed-for-this-dataset alternative
with CroatiaClient(username=username, password=password) as croatia:
    for situation in croatia.iter_roadworks():
        works = from_datex2(situation, territory="Croatia")
```

**Two real, sibling datasets found on the NAP, not one.** "HC Radovi
DatexII" (legacy, published since 22.05.2023,
`https://b2b.promet-info.hr/dc/b2b.hc.roadworks.datex`) and "HC Radovi
DatexII v3" (published since 11.03.2024,
`https://b2b.promet-info.hr/dc/b2b.hc.roadworks.datex3`) — this SDK
targets the v3 endpoint, the same "prefer the newer schema version when
both exist" choice already made for D-TRO. Both confirmed live to return
a real `401` for an unauthenticated request.

**The real pull URL was public before any registration** — found by
reading the NAP's own dataset-metadata pages
(`promet-info.hr/hr/datasets_details?id=...`, reached via
`promet-info.hr/hr/dataproviders?search=HC%20radovi`), which state the
access URL directly, alongside real format/auth/quality metadata:
encoding UTF-8, syntax XML, grammar XSD, data model "DATEX II Profile",
georeferencing method **Geocoordinates WGS84** (no reprojection needed,
unlike Belgium's own real Lambert 72 finding), update frequency **up to
1 minute**.

**Auth: the NAP's own metadata states both Basic and Bearer
authentication as real, documented security mechanisms** for this exact
dataset (`osnovna autentifikacija, bearer autentifikacija`) — which one
is actually required (or whether either works) isn't stated beyond that.
`CroatiaClient` accepts either shape (`username`/`password` for Basic,
or `bearer_token` for Bearer) and lets the caller's own registration
outcome decide.

**A real, live self-service registration form was found and inspected**
— unlike Vejdirektoratet (registration portal reached but not walked
through) or ASFINAG (auth mechanism completely unknown).
`promet-info.hr/hr/registration` is a plain sign-up form: email, name,
organisation, address, phone, language, password — no visible
approval/contract gate before submission (what happens *after*
submitting is itself unconfirmed, since no real submission was made on
the caller's behalf).

**Licence: Croatia's own national "Otvorena dozvola" (Open Licence)** —
confirmed by fetching and reading the real PDF
(`promet-info.hr/_resources/doc/Otvorena%20dozvola.pdf`), not just the
NAP's own summary label. Explicitly permits commercial and
non-commercial use, reproduction, distribution, adaptation, and
integration into products — CC BY/OGL-tier permissiveness, with the same
shape of requirement: cite the real source (name + last-modified date,
or a stated fallback attribution sentence when the source gives none)
and the dataset's own URI, and mark any modifications as such. No
comparable restriction to ASFINAG's own supplementary
downstream-disclosure clause was found.

**Confirmed 2026-08-26, against a real authenticated pull**: HTTP Basic
(`username`/`password`) is the correct auth for this account (Bearer
remains a real, unconfirmed-for-this-dataset platform-wide alternative);
the real DATEX II v3 response is a bare `SituationPublication` — this
SDK's own shared streaming parser handled it with zero code changes; and
every one of the 85 real situations checked was `MaintenanceWorks` (no
`ConstructionWorks` seen in this pull, though the NAP's own metadata
still names it as real). See
[`docs/providers/index.md`](index.md) for the module table entry.
