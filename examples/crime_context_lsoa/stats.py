"""Rate, shrinkage, annualisation, and banding for LSOA-level crime context.

Mirrors the tiered banding design in
``examples/crime_context/generate_map.py`` (quintile / tercile / refuse-to-
band, suppression for too-few-crimes areas) deliberately duplicated rather
than imported across examples, so each stays independently runnable and
copy-pasteable - see that module's own comment on the same tradeoff for the
neighbourhood-level version this one succeeds.
"""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

JSON = dict[str, Any]

#: Same judgement call as the neighbourhood example, same reasoning: a
#: handful of crimes against a small population is Poisson noise, not
#: signal, even after shrinkage.
MIN_COUNT_TO_BAND = 5

#: At least 3 areas per bin, rounded down - see generate_map.py's own
#: comment on this reasoning, which applies identically here.
MIN_AREAS_FOR_TERCILES = 6
MIN_AREAS_FOR_QUINTILES = 15

BAND_LABELS_5 = [
    "well below force typical",
    "below force typical",
    "around force typical",
    "above force typical",
    "well above force typical",
]
BAND_COLORS_5 = ["#e3f3f1", "#a8dad4", "#69b8ae", "#2f8577", "#0b4f45"]
BAND_LABELS_3 = ["below force typical", "around force typical", "above force typical"]
BAND_COLORS_3 = ["#a8dad4", "#69b8ae", "#0b4f45"]
SUPPRESSED_COLOR = "#d9d9d9"


class LsoaMembershipError(ValueError):
    """Raised by :func:`check_lsoa_membership` - see its docstring."""


def annualised_rate_per_1000(
    count: int, population: int, window_months: int
) -> float | None:
    """Crimes per 1,000 residents **per year**, scaled up from whatever
    window the count actually covers, so a 3-month and a 12-month window
    over the same underlying rate give the same annual figure - see
    ``tests/test_examples_crime_context_lsoa.py``'s annualisation test.
    ``None`` for a zero/negative population (can't be computed, not zero)."""
    if population <= 0:
        return None
    return (count / population * 1000) * (12 / window_months)


def check_lsoa_membership(
    row_counts_by_code: Counter[str],
    known_codes: set[str],
    *,
    max_missing_row_fraction: float = 0.05,
) -> None:
    """Raise :class:`LsoaMembershipError` if too large a fraction of crime
    CSV rows reference an LSOA code ``known_codes`` (from ONS's own 2021
    table) doesn't have.

    A *small* missing fraction is expected and healthy: a per-force CSV
    export carries a small amount of genuine cross-force contamination
    (confirmed live for Durham - ~0.4% of rows, geographically outside the
    force, presumably shared custody or joint operations - see
    ``PoliceClient.bulk_download_csv``'s docstring). Because each stray row
    usually lands in a different LSOA, that same ~0.4% of rows touched
    around 15% of *distinct* codes in the real check - which is why this
    guard measures row volume, not distinct-code count: distinct-code
    fraction would flag the normal case as if it were a problem.

    A *large* missing fraction is the real failure this guards against:
    2011-vintage LSOA codes joined against this module's 2021-vintage ONS
    lookup, crime data for the wrong force, or any other source/vintage
    mismatch - which would otherwise silently render as "most areas have no
    data" rather than a loud, diagnosable error. The default 5% threshold
    sits comfortably above the real 0.4% baseline and comfortably below
    what a genuine mismatch would produce.
    """
    total_rows = sum(row_counts_by_code.values())
    if total_rows == 0:
        return
    missing_rows = sum(n for code, n in row_counts_by_code.items() if code not in known_codes)
    missing_fraction = missing_rows / total_rows
    if missing_fraction > max_missing_row_fraction:
        raise LsoaMembershipError(
            f"{missing_fraction:.1%} of crime rows reference an LSOA code not in "
            f"the ONS 2021 lookup (threshold {max_missing_row_fraction:.0%}) - this "
            "is far more than the small amount of real cross-force contamination "
            "a per-force export normally carries, and suggests a vintage or source "
            "mismatch (e.g. 2011 LSOA codes against a 2021 lookup) rather than "
            "something safe to ignore."
        )


def compute_force_bands(
    lsoa_rows: list[JSON], *, window_months: int, min_count: int = MIN_COUNT_TO_BAND
) -> tuple[list[JSON], str | None]:
    """Shrinks each LSOA's rate toward the force-wide mean, then bands into
    quintiles (or terciles, or refuses to band at all - see the module's
    tier constants) exactly mirroring
    ``examples/crime_context/generate_map.py``'s ``compute_bands``, with
    population in place of area.

    Each item in ``lsoa_rows`` needs ``"count"`` and ``"population"`` and
    is mutated in place with ``raw_rate_per_1000_per_year``,
    ``adjusted_rate_per_1000_per_year``, ``suppressed``, ``band``,
    ``band_label``, ``band_color``. Returns ``(lsoa_rows, banding_note)``.
    """
    for s in lsoa_rows:
        s["raw_rate_per_1000_per_year"] = annualised_rate_per_1000(
            s["count"], s["population"], window_months
        )

    populations = [s["population"] for s in lsoa_rows if s["population"] > 0]
    k = statistics.median(populations) if populations else 1.0
    total_count = sum(s["count"] for s in lsoa_rows)
    total_population = sum(populations)
    # Bayes-flavoured shrinkage toward the force-wide mean rate (fraction of
    # residents, not yet annualised/per-1000), weighted by k (the median
    # LSOA population) - a fast, readable approximation of a proper
    # Poisson-gamma model, not that model itself. See generate_map.py's
    # identical-in-spirit comment on the area-denominator version.
    force_rate_per_person = total_count / total_population if total_population else 0.0

    for s in lsoa_rows:
        population = s["population"]
        if population > 0:
            adjusted_per_person = (s["count"] + force_rate_per_person * k) / (
                population + k
            )
            s["adjusted_rate_per_1000_per_year"] = (
                adjusted_per_person * 1000 * (12 / window_months)
            )
        else:
            s["adjusted_rate_per_1000_per_year"] = None
        # Safety-critical branch, same as the neighbourhood example: a
        # suppressed LSOA renders unshaded/grey, never folded into the
        # lightest real band.
        s["suppressed"] = (
            s["count"] < min_count or s["adjusted_rate_per_1000_per_year"] is None
        )

    bandable = sorted(
        (s for s in lsoa_rows if not s["suppressed"]),
        key=lambda s: s["adjusted_rate_per_1000_per_year"],
    )
    n = len(bandable)

    labels: list[str] | None
    colors: list[str] | None
    if n >= MIN_AREAS_FOR_QUINTILES:
        labels, colors, num_bands = BAND_LABELS_5, BAND_COLORS_5, 5
    elif n >= MIN_AREAS_FOR_TERCILES:
        labels, colors, num_bands = BAND_LABELS_3, BAND_COLORS_3, 3
    else:
        labels = colors = None
        num_bands = 0

    banding_note = None
    if num_bands and labels is not None and colors is not None:
        for i, s in enumerate(bandable):
            band_index = min(num_bands - 1, (i * num_bands) // n)
            s["band"] = band_index
            s["band_label"] = labels[band_index]
            s["band_color"] = colors[band_index]
    elif n > 0:
        banding_note = (
            f"This force has only {n} LSOA(s) with enough recorded crime to "
            f"compare (minimum {MIN_AREAS_FOR_TERCILES} needed for even a "
            "three-band split) - too few for a meaningful relative comparison, "
            "so no areas are banded or coloured."
        )
        for s in bandable:
            s["band"] = None
            s["band_label"] = "too few LSOAs in this force to band"
            s["band_color"] = SUPPRESSED_COLOR

    for s in lsoa_rows:
        if s["suppressed"]:
            s["band"] = None
            s["band_label"] = "too few crimes to band"
            s["band_color"] = SUPPRESSED_COLOR

    return lsoa_rows, banding_note
