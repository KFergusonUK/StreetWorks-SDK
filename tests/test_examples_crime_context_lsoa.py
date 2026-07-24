"""Tests for examples/crime_context_lsoa/ - the LSOA-level, worksite-keyed
successor to examples/crime_context/.

Like the neighbourhood-level example's own test file, this covers the pure
functions directly rather than the CLI end-to-end (no precedent in this
repo for driving a live worksite report in tests, and the underlying police
CSV/ONS ArcGIS calls are already covered separately - PoliceClient.bulk_download_csv()
in tests/test_police.py, ArcGISFeatureClient in tests/test_arcgis.py).

The LSOA-vintage-mixing test the brief for this example asked for is
``TestCheckLsoaMembership::test_large_missing_fraction_is_the_real_failure_mode``:
boundary and population come from the *same* ONS query row in this design
(see ons.py's own docstring), so they cannot drift from each other by
vintage - the actual seam where a vintage or source mismatch could still
bite is the join between crime-CSV LSOA codes and the ONS lookup, which is
exactly what ``check_lsoa_membership`` guards.
"""

from collections import Counter

import pytest
from shapely.geometry import Point

from examples.crime_context_lsoa import ingest, ons, report, worksite
from examples.crime_context_lsoa.stats import (
    LsoaMembershipError,
    annualised_rate_per_1000,
    check_lsoa_membership,
    compute_force_bands,
)


def _row(code: str, count: int, population: int) -> dict:
    return {
        "code": code,
        "name": code,
        "population": population,
        "count": count,
        "rings": [[(0.0, 0.0), (0.0, 0.001), (0.001, 0.001), (0.001, 0.0), (0.0, 0.0)]],
        "by_category": Counter(),
    }


# --------------------------------------------------------------------------- #
# Annualisation - a 3-month and a 12-month window over the same underlying
# rate must produce the same annual figure.
# --------------------------------------------------------------------------- #


class TestAnnualisedRate:
    def test_3_month_and_12_month_windows_agree_on_the_same_underlying_rate(self):
        population = 1500
        rate_3mo = annualised_rate_per_1000(30, population, window_months=3)
        rate_12mo = annualised_rate_per_1000(30 * 4, population, window_months=12)
        assert rate_3mo == pytest.approx(rate_12mo)

    def test_zero_population_is_none_not_zero(self):
        assert annualised_rate_per_1000(10, 0, window_months=12) is None

    def test_scales_linearly_with_count(self):
        population = 2000
        assert annualised_rate_per_1000(20, population, 12) == pytest.approx(
            2 * annualised_rate_per_1000(10, population, 12)
        )


# --------------------------------------------------------------------------- #
# LSOA membership guard - the real vintage/source-mismatch protection.
# --------------------------------------------------------------------------- #


class TestCheckLsoaMembership:
    def test_small_missing_fraction_is_tolerated(self):
        # Mirrors the real, live-checked Durham contamination rate (~0.4%
        # of rows) - this must not raise.
        row_counts = Counter({"E01000001": 996, "E01999999": 4})
        check_lsoa_membership(row_counts, known_codes={"E01000001"})

    def test_large_missing_fraction_is_the_real_failure_mode(self):
        # The scenario this guard exists for: most of the crime data's LSOA
        # codes aren't in the ONS lookup at all - e.g. 2011-vintage codes
        # joined against this module's 2021-vintage ONS table (boundary and
        # population can't drift from each other within ons.py's own design
        # - they're read from the same query row - but a caller joining
        # against a different source entirely is not protected by that).
        row_counts = Counter({"E01000001": 100, "E01999999": 900})
        with pytest.raises(LsoaMembershipError, match="90.0%"):
            check_lsoa_membership(row_counts, known_codes={"E01000001"})

    def test_empty_input_does_not_raise(self):
        check_lsoa_membership(Counter(), known_codes=set())

    def test_threshold_is_configurable(self):
        row_counts = Counter({"E01000001": 90, "E01999999": 10})
        check_lsoa_membership(row_counts, known_codes={"E01000001"}, max_missing_row_fraction=0.2)
        with pytest.raises(LsoaMembershipError):
            check_lsoa_membership(
                row_counts, known_codes={"E01000001"}, max_missing_row_fraction=0.05
            )


# --------------------------------------------------------------------------- #
# Banding - same tiered design as the neighbourhood example, population in
# place of area.
# --------------------------------------------------------------------------- #


class TestComputeForceBands:
    def test_low_count_lsoa_is_suppressed_not_falsely_low(self):
        rows = [_row(f"n{i}", 200, 1500) for i in range(20)]
        rows.append(_row("low", 1, 1500))
        rows_out, note = compute_force_bands(rows, window_months=12)

        low = next(r for r in rows_out if r["code"] == "low")
        assert low["suppressed"] is True
        assert low["band"] is None
        assert low["band_label"] == "too few crimes to band"
        assert note is None

    def test_enough_lsoas_uses_quintiles(self):
        from examples.crime_context_lsoa.stats import MIN_AREAS_FOR_QUINTILES

        rows = [_row(f"n{i}", 50 + i * 10, 1500) for i in range(MIN_AREAS_FOR_QUINTILES)]
        rows_out, note = compute_force_bands(rows, window_months=12)
        assert note is None
        assert {r["band"] for r in rows_out} == set(range(5))

    def test_below_tercile_floor_refuses_to_band(self):
        from examples.crime_context_lsoa.stats import MIN_AREAS_FOR_TERCILES

        n = MIN_AREAS_FOR_TERCILES - 1
        rows = [_row(f"n{i}", 50 + i * 10, 1500) for i in range(n)]
        rows_out, note = compute_force_bands(rows, window_months=12)
        assert note is not None
        assert all(r["band"] is None for r in rows_out)
        assert all(r["band_label"] == "too few LSOAs in this force to band" for r in rows_out)

    def test_shrinkage_pulls_small_population_lsoa_toward_force_mean(self):
        # 20 LSOAs at a steady 10% raw rate set the force mean; one tiny
        # LSOA has a much higher *raw* rate (30 crimes against a population
        # of only 150) - shrinkage should pull its adjusted rate back down
        # toward the force mean, not leave it at the raw extreme.
        rows = [_row(f"n{i}", 300, 3000) for i in range(20)]  # 10% raw rate each
        rows.append(_row("tiny", 30, 150))  # 20% raw rate, tiny population
        rows_out, _ = compute_force_bands(rows, window_months=12)
        tiny = next(r for r in rows_out if r["code"] == "tiny")
        raw = tiny["raw_rate_per_1000_per_year"]
        adjusted = tiny["adjusted_rate_per_1000_per_year"]
        force_mean = rows_out[0]["adjusted_rate_per_1000_per_year"]
        assert raw != pytest.approx(force_mean)
        assert abs(adjusted - force_mean) < abs(raw - force_mean)


# --------------------------------------------------------------------------- #
# Worksite geometry
# --------------------------------------------------------------------------- #


class TestWorksiteFromPoint:
    def test_returns_a_polygon_containing_the_origin_point(self):
        polygon = worksite.worksite_from_point(54.61, -1.56, 300)
        assert polygon.contains(Point(-1.56, 54.61))

    def test_larger_radius_gives_larger_area(self):
        small = worksite.worksite_from_point(54.61, -1.56, 100)
        large = worksite.worksite_from_point(54.61, -1.56, 500)
        assert large.area > small.area


class TestFindIntersectingLsoas:
    def test_finds_the_lsoa_the_worksite_overlaps(self):
        # A worksite buffer centred inside a real-shaped LSOA square.
        square = [(-1.60, 54.60), (-1.60, 54.62), (-1.58, 54.62), (-1.58, 54.60), (-1.60, 54.60)]
        lsoa_stats = {"E01000001": {"rings": [square]}}
        site = worksite.worksite_from_point(54.61, -1.59, 50)
        assert worksite.find_intersecting_lsoas(site, lsoa_stats) == ["E01000001"]

    def test_finds_nothing_when_worksite_is_far_away(self):
        square = [(-1.60, 54.60), (-1.60, 54.62), (-1.58, 54.62), (-1.58, 54.60), (-1.60, 54.60)]
        lsoa_stats = {"E01000001": {"rings": [square]}}
        site = worksite.worksite_from_point(0.0, 0.0, 50)
        assert worksite.find_intersecting_lsoas(site, lsoa_stats) == []


# --------------------------------------------------------------------------- #
# Cross-force contamination filter
# --------------------------------------------------------------------------- #


class TestInForceRows:
    def test_drops_rows_far_from_the_median_point(self):
        near_rows = [
            {"Latitude": str(54.6 + i * 0.001), "Longitude": str(-1.55 + i * 0.001)}
            for i in range(20)
        ]
        far_row = {"Latitude": "52.46", "Longitude": "-1.93"}  # ~190km away - real, from Durham
        rows = near_rows + [far_row]
        kept = ingest._in_force_rows(rows)
        assert far_row not in kept
        assert len(kept) == len(near_rows)

    def test_keeps_everything_when_all_rows_are_close_together(self):
        rows = [
            {"Latitude": str(54.6 + i * 0.001), "Longitude": str(-1.55 + i * 0.001)}
            for i in range(10)
        ]
        assert ingest._in_force_rows(rows) == rows


class TestHaversine:
    def test_zero_distance_for_the_same_point(self):
        assert ingest._haversine_km(54.6, -1.5, 54.6, -1.5) == pytest.approx(0.0, abs=1e-9)

    def test_known_distance_is_plausible(self):
        # Durham city to Darlington - real towns, ~20km apart by road, so
        # straight-line should be a bit less than that.
        km = ingest._haversine_km(54.7761, -1.5733, 54.5250, -1.5561)
        assert 20 < km < 30


# --------------------------------------------------------------------------- #
# ONS geometry unwrapping
# --------------------------------------------------------------------------- #


class TestPolygonRings:
    def test_polygon_returns_its_single_ring(self):
        geometry = {"type": "Polygon", "coordinates": [[[0.0, 0.0], [0.0, 1.0], [1.0, 0.0]]]}
        rings = ons._polygon_rings(geometry)
        assert rings == [[(0.0, 0.0), (0.0, 1.0), (1.0, 0.0)]]

    def test_multipolygon_returns_all_rings_flattened(self):
        geometry = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0.0, 0.0], [0.0, 1.0], [1.0, 0.0]]],
                [[[5.0, 5.0], [5.0, 6.0], [6.0, 5.0]]],
            ],
        }
        rings = ons._polygon_rings(geometry)
        assert len(rings) == 2

    def test_unknown_geometry_type_returns_no_rings(self):
        assert ons._polygon_rings({"type": "Point", "coordinates": [0.0, 0.0]}) == []


# --------------------------------------------------------------------------- #
# Month range (mirrors the neighbourhood example's own availability-based fix)
# --------------------------------------------------------------------------- #


class TestMonthRange:
    def test_ends_at_the_given_latest_month(self):
        date_from, date_to = report.month_range("2026-05", window_months=12)
        assert date_to == "2026-05"
        assert date_from == "2025-06"

    def test_crosses_a_year_boundary(self):
        date_from, date_to = report.month_range("2026-01", window_months=3)
        assert (date_from, date_to) == ("2025-11", "2026-01")
