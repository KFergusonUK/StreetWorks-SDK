"""Police bulk CSV ingestion and per-LSOA aggregation.

Everything here goes through :meth:`streetworks.police.PoliceClient.bulk_download_csv`
and :meth:`streetworks.police.PoliceClient.crime_categories` - both real
API/download methods, not something reached around the SDK for. See
``PoliceClient.bulk_download_csv``'s own docstring for the live-verified
facts about the CSV route (scriptable CSRF form + async job, real column
names, the small amount of cross-force contamination in a per-force
export) that this module's design already accounts for.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from typing import Any

from streetworks.police import SAFETY_RELEVANT_CATEGORIES, PoliceClient

JSON = dict[str, Any]

#: A row further than this from the force's own median crime location is
#: treated as cross-force contamination, not this force's own data - see
#: _in_force_rows()'s docstring for the live check this threshold is based
#: on. Comfortably above Durham's real p99 distance (~32km) and comfortably
#: below where the real contamination in one live check actually sat
#: (Birmingham, Braintree, Dudley... all 100km+ away).
_MAX_DISTANCE_FROM_MEDIAN_KM = 50.0


def category_slug_by_name(police: PoliceClient) -> dict[str, str]:
    """``{CSV "Crime type" string: JSON API slug}`` - confirmed live,
    character-for-character, from :meth:`PoliceClient.crime_categories`'s
    own ``name``/``url`` fields. The brief for this example expected a
    separate mapping file (``police-uk-category-mappings.csv``) would be
    needed; live-checked and it isn't - that file maps granular Home
    Office offence codes to a *different* category scheme, not the CSV's
    ``Crime type`` column, which already matches ``crime_categories()``
    exactly."""
    return {entry["name"]: entry["url"] for entry in police.crime_categories()}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _in_force_rows(rows: list[JSON]) -> list[JSON]:
    """Drops rows geographically far from the force's own median crime
    location - the actual, general fix for the cross-force contamination
    ``bulk_download_csv`` documents (``Falls within`` cannot be used for
    this: confirmed live, every row in a force's own export - including the
    contaminating ones - carries that force's own name in that column, so
    it isn't a geographic signal at all).

    Live-verified against a real Durham May-2026 download (7,401 rows):
    99% of rows sit within 31.6km of the force's own median point; the
    0.34% that don't jump straight to 100km+ (Birmingham, Braintree,
    Dudley, Folkestone, Havant, Leicester - all real, all in that one
    check). There is no ambiguous middle ground in the real data between
    "clearly this force" and "clearly not" for that kind of contamination -
    a single distance threshold cleanly separates them, which is not
    something a per-LSOA row-count threshold could do without risking
    excluding genuinely quiet rural LSOAs that are still really part of the
    force.

    This does *not* catch a smaller, different, and more defensible effect
    left in deliberately: a Durham-recorded crime whose snapped location
    lands just over the border in a neighbouring force's LSOA still passes
    this filter (it's genuinely close by), so a thin real fringe of
    low-count neighbouring-force LSOAs remains in the candidate set -
    almost always caught by MIN_COUNT_TO_BAND suppression downstream rather
    than shown as a real band, and small enough in row volume that
    ``stats.check_lsoa_membership`` doesn't flag it either.
    """
    points = [
        (float(r["Latitude"]), float(r["Longitude"]))
        for r in rows
        if r.get("Latitude") and r.get("Longitude")
    ]
    if not points:
        return rows
    median_lat = statistics.median(p[0] for p in points)
    median_lng = statistics.median(p[1] for p in points)
    return [
        r
        for r in rows
        if r.get("Latitude")
        and r.get("Longitude")
        and _haversine_km(median_lat, median_lng, float(r["Latitude"]), float(r["Longitude"]))
        <= _MAX_DISTANCE_FROM_MEDIAN_KM
    ]


def fetch_lsoa_crime_counts(
    police: PoliceClient, force: str, *, date_from: str, date_to: str
) -> tuple[dict[str, JSON], Counter[str]]:
    """Downloads ``force``'s street-level crime CSVs for the given month
    range, drops geographic cross-force contamination (see
    :func:`_in_force_rows`), and aggregates safety-relevant crime by LSOA
    code.

    Returns ``(per_lsoa, all_lsoa_row_counts)``:

    - ``per_lsoa``: ``{lsoa_code: {"count": int, "by_category": Counter}}``
      for :data:`~streetworks.police.SAFETY_RELEVANT_CATEGORIES` crimes only
      (the same category set the neighbourhood-level example uses, for the
      same reason - see that constant's own comment in
      ``streetworks/police/client.py``).
    - ``all_lsoa_row_counts``: every LSOA code seen in the (already
      geographically filtered) download, **all** categories, with its row
      count - the candidate LSOA universe asked of ONS. Some residual
      mismatch against ONS's table is still expected and checked for by
      ``stats.check_lsoa_membership`` (a real address can still snap to a
      neighbouring force's LSOA right at a boundary) - this function
      removes the *bulk* of the contamination, not a guarantee of none.
    """
    rows = _in_force_rows(police.bulk_download_csv(force, date_from=date_from, date_to=date_to))
    slug_by_name = category_slug_by_name(police)

    per_lsoa: dict[str, JSON] = defaultdict(lambda: {"count": 0, "by_category": Counter()})
    all_lsoa_row_counts: Counter[str] = Counter()

    for row in rows:
        code = row.get("LSOA code")
        if not code:
            continue  # a real minority of rows have no LSOA at all (crime type dependent)
        all_lsoa_row_counts[code] += 1

        slug = slug_by_name.get(row["Crime type"])
        if slug in SAFETY_RELEVANT_CATEGORIES:
            entry = per_lsoa[code]
            entry["count"] += 1
            entry["by_category"][row["Crime type"]] += 1

    return dict(per_lsoa), all_lsoa_row_counts
