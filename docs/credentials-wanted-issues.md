# "Credentials wanted" GitHub issues — drafted text

Draft text for two `help wanted` issues, one per provider in the
[README's Credentials wanted section](../README.md#credentials-wanted).
Norway/NSW/Victoria were confirmed on 2026-07-30 by a real credentialed
pull and no longer need this - their drafted issue text has been removed.
None of these have been opened yet — this file is the text to paste in when
opening them (or to point someone at ahead of time). Both modules'
import-time `UserWarning` and the README table link to
`https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22`,
which will surface these once opened with the `help wanted` label.

Suggested labels for both: `help wanted`, `credentials-wanted`.

---

## Issue: Trafikverket (Sweden) — confirm the adapter against real data

**Title:** `Credentials wanted: verify streetworks.datex2.trafikverket against real Swedish data`

**Body:**

`streetworks.datex2.trafikverket` is a Phase 1 scaffold: built against
Trafikverket's own confirmed-live API shape (not vanilla DATEX II — its own
XML-request/JSON-response envelope) — but no real authenticated response
has ever been seen.

**Confirmed, live, credential-free:** a deliberate invalid-key probe
against the real endpoint returns a genuine structured `401` — this
confirms the endpoint, the request envelope shape, the `Situation` object
name, and schema version `1.5`, independent of any documentation page's own
claims.

**Pending:**
1. Whether the response JSON nests exactly as the dotted `INCLUDE` field
   paths suggest.
2. **The real value of `MessageType`/`MessageCode` that means roadworks
   specifically** — searched several third-party sources, none state it.
   Until this is confirmed, `iter_roadworks()` deliberately returns nothing
   rather than guess — see the module docstring.
3. Whether `Deviation` carries a genuine unique `Id` field.
4. Real coordinate coverage for `Geometry.WGS84`.

**Credential needed:** an API key (not Basic Auth). Free, self-service:
[data.trafikverket.se](https://data.trafikverket.se/) or via
[Trafiklab](https://www.trafiklab.se/api/other-apis/trafikverket/) — fill a
form, accept the licence, verify email, key issued immediately. The
lightest-weight registration of any Credentials-wanted provider here.

**What to report back:** run `python scripts/smoke_test.py` with
`TRAFIKVERKET_API_KEY` set, paste the result line (it lists the real
`MessageType` values seen), and — most usefully — **the real
`MessageType`/`MessageCode` value on a deviation you know to be
roadworks**, so `ROADWORKS_MESSAGE_TYPES`-equivalent filtering can finally
be implemented correctly. One real trimmed `Situation`/`Deviation` record
(anything sensitive stripped) would also let the synthetic fixture be
replaced.

See `src/streetworks/datex2/trafikverket.py`'s module docstring for the
full detail behind each claim above.

---

## Issue: Vejdirektoratet (Denmark) — confirm the adapter against real data

**Title:** `Credentials wanted: verify streetworks.datex2.vejdirektoratet against real Danish data`

**Body:**

`streetworks.datex2.vejdirektoratet` is a Phase 1 scaffold: built against
genuine DATEX II 3.2, confirmed directly from Vejdirektoratet's own
protocol specification — but the credential-gated data pull itself has
never been exercised.

**Confirmed:**
- `sit:ConstructionWorks`/`sit:MaintenanceWorks` record types and their
  full `constructionWorkType`/`roadMaintenanceType` enumerations, stated
  explicitly in Vejdirektoratet's own protocol PDF (not inferred).
- The open metadata catalogue, live (196 datasets, no auth) — the specific
  roadworks dataset ("OOV2 Trafikmeldinger", id 222) confirmed
  road-work-themed, DATEX-II-standard, and CC BY 4.0-licensed.
- HTTP Basic Auth as the documented scheme (quoted verbatim from the
  protocol doc).

**Pending:**
1. Whether `trafikmeldinger` really is a list of independent DATEX XML
   strings, as documented, or a single wrapping document.
2. Whether the REST response is unmodified DATEX II 3.2 or carries a
   Vejdirektoratet-specific profile the shared parser doesn't expect.
3. Real location-referencing coverage.

**Credential needed:** HTTP Basic Auth username/password **and** the
actual per-dataset pull URL — both issued together at registration; there
is no public data URL to hardcode. Free; register via
[Dataudveksleren](https://du-portal-ui.dataudveksler.app.vd.dk/).

**What to report back:** run `python scripts/smoke_test.py` with
`VEJDIREKTORATET_URL`/`VEJDIREKTORATET_USERNAME`/`VEJDIREKTORATET_PASSWORD`
set, paste the result line, and — ideally — one real trimmed
`sit:situation` (with anything sensitive stripped) so the synthetic fixture
can be swapped for real data and the open questions above closed out.

See `src/streetworks/datex2/vejdirektoratet.py`'s module docstring for the
full detail behind each claim above.
