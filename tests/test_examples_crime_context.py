"""Tests for examples/crime_context/generate_map.py.

Not part of the installed ``streetworks`` package (``examples/`` is a
worked example, not library code) so there's no precedent elsewhere in
this repo for testing one directly - it's loaded here by file path via
``importlib`` rather than a normal import.

Coverage is aimed at the banding tiers (quintile / tercile / refuse-to-band)
and, especially, the suppression path: a neighbourhood with too few
recorded crimes must render unshaded/grey, never folded into the lightest
real colour band just because a tiny denominator makes its rate come out
low. Nothing in a real live run (Leicestershire, City of London, Durham)
has had few enough crimes to hit that branch, so it's exercised here with
synthetic stats instead - see the module docstring's own comment on this in
``compute_bands()``.

The 503-raises-a-typed-exception-not-an-empty-list behaviour lives in
``tests/test_police.py`` (``test_503_raises_server_error_not_empty_list``)
and is, deliberately, mocked-only: forcing a genuine 503 out of the real
data.police.uk service would be an inappropriate way to get that coverage
against a public government API, so respx is the right tool here, not a
live run.
"""

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = (
    Path(__file__).parent.parent / "examples" / "crime_context" / "generate_map.py"
)


def _load_generate_map():
    spec = importlib.util.spec_from_file_location("generate_map", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_map"] = module
    spec.loader.exec_module(module)
    return module


gm = _load_generate_map()


def _stat(id_: str, count: int, area_km2: float) -> dict:
    return {"id": id_, "name": id_, "count": count, "area_km2": area_km2, "boundary": []}


# --------------------------------------------------------------------------- #
# Suppression - the safety-critical branch
# --------------------------------------------------------------------------- #


class TestSuppression:
    def test_low_count_area_is_suppressed_not_falsely_low(self):
        stats = [_stat(f"n{i}", 200, 1.0) for i in range(20)]
        stats.append(_stat("low", 1, 1.0))
        stats_out, note = gm.compute_bands(stats)

        low = next(s for s in stats_out if s["id"] == "low")
        assert low["suppressed"] is True
        assert low["band"] is None
        assert low["band_label"] == "too few crimes to band"
        assert low["band_color"] == gm.SUPPRESSED_COLOR
        # The whole point: suppressed grey must not be reachable via the
        # real colour scale, so a viewer can't mistake it for a real band.
        assert low["band_color"] not in gm.BAND_COLORS_5
        assert low["band_color"] not in gm.BAND_COLORS_3
        assert note is None  # the rest of the force still banded fine

    def test_zero_area_is_suppressed(self):
        stats = [_stat(f"n{i}", 200, 1.0) for i in range(20)]
        stats.append(_stat("degenerate", 50, 0.0))
        stats_out, _note = gm.compute_bands(stats)

        degenerate = next(s for s in stats_out if s["id"] == "degenerate")
        assert degenerate["suppressed"] is True
        assert degenerate["band"] is None
        assert degenerate["band_color"] == gm.SUPPRESSED_COLOR

    def test_suppressed_area_excluded_from_bandable_ranking(self):
        stats = [_stat(f"n{i}", 200, 1.0) for i in range(20)]
        stats.append(_stat("low", 0, 1.0))
        stats_out, _note = gm.compute_bands(stats)

        banded = [s for s in stats_out if s["band"] is not None]
        assert len(banded) == 20
        assert all(s["id"] != "low" for s in banded)

    def test_count_exactly_at_min_is_not_suppressed(self):
        stats = [_stat(f"n{i}", 200, 1.0) for i in range(20)]
        stats.append(_stat("edge", gm.MIN_COUNT_TO_BAND, 1.0))
        stats_out, _note = gm.compute_bands(stats)

        edge = next(s for s in stats_out if s["id"] == "edge")
        assert edge["suppressed"] is False
        assert edge["band"] is not None


# --------------------------------------------------------------------------- #
# Banding tiers
# --------------------------------------------------------------------------- #


class TestBandingTiers:
    def test_enough_areas_uses_quintiles(self):
        n = gm.MIN_AREAS_FOR_QUINTILES
        stats = [_stat(f"n{i}", 50 + i * 10, 1.0) for i in range(n)]
        stats_out, note = gm.compute_bands(stats)

        assert note is None
        assert {s["band"] for s in stats_out} == set(range(5))
        assert all(s["band_label"] in gm.BAND_LABELS_5 for s in stats_out)
        assert all(s["band_color"] in gm.BAND_COLORS_5 for s in stats_out)

    def test_between_floors_falls_back_to_terciles(self):
        n = gm.MIN_AREAS_FOR_QUINTILES - 1
        assert n >= gm.MIN_AREAS_FOR_TERCILES, "test assumes a real gap between the two floors"
        stats = [_stat(f"n{i}", 50 + i * 10, 1.0) for i in range(n)]
        stats_out, note = gm.compute_bands(stats)

        assert note is None
        assert {s["band"] for s in stats_out} == set(range(3))
        assert all(s["band_label"] in gm.BAND_LABELS_3 for s in stats_out)
        assert all(s["band_color"] in gm.BAND_COLORS_3 for s in stats_out)

    def test_below_tercile_floor_refuses_to_band(self):
        n = gm.MIN_AREAS_FOR_TERCILES - 1
        stats = [_stat(f"n{i}", 50 + i * 10, 1.0) for i in range(n)]
        stats_out, note = gm.compute_bands(stats)

        assert note is not None
        assert str(n) in note
        assert all(s["band"] is None for s in stats_out)
        assert all(
            s["band_label"] == "too few neighbourhoods in this force to band" for s in stats_out
        )
        assert all(s["band_color"] == gm.SUPPRESSED_COLOR for s in stats_out)

    def test_city_of_london_sized_force_clears_tercile_floor_exactly(self):
        # The real case this tier structure targets: a force the size of
        # the City of London (6 real neighbourhoods) must clear the new
        # floor, not silently fall through it the way the prototype's old
        # floor of 5 would have left it right on the edge.
        assert gm.MIN_AREAS_FOR_TERCILES == 6
        stats = [_stat(f"n{i}", 50 + i * 10, 1.0) for i in range(6)]
        stats_out, note = gm.compute_bands(stats)

        assert note is None
        assert {s["band"] for s in stats_out} == set(range(3))

    def test_refuse_to_band_and_per_area_suppression_can_coexist(self):
        # Below the tercile floor *and* one area individually suppressed -
        # both real reasons for band=None should appear, distinctly.
        n = gm.MIN_AREAS_FOR_TERCILES - 1
        stats = [_stat(f"n{i}", 50 + i * 10, 1.0) for i in range(n)]
        stats.append(_stat("also_low", 1, 1.0))
        stats_out, note = gm.compute_bands(stats)

        assert note is not None
        labels = {s["band_label"] for s in stats_out}
        assert "too few neighbourhoods in this force to band" in labels
        assert "too few crimes to band" in labels
        assert all(s["band"] is None for s in stats_out)


# --------------------------------------------------------------------------- #
# Pure geometry / date helpers
# --------------------------------------------------------------------------- #


class TestLatestAvailableMonth:
    def test_returns_the_max_reported_date(self):
        availability = [{"date": "2026-03"}, {"date": "2026-05"}, {"date": "2026-04"}]
        assert gm.latest_available_month(availability) == "2026-05"

    def test_ignores_list_order(self):
        availability = [{"date": "2023-06"}, {"date": "2026-05"}, {"date": "2024-01"}]
        assert gm.latest_available_month(availability) == "2026-05"


class TestMonthWindow:
    def test_returns_requested_number_of_months_oldest_first(self):
        months = gm.month_window("2026-07", window_months=12)
        assert len(months) == 12
        assert months == sorted(months)

    def test_ends_at_the_given_latest_month_with_no_extra_offset(self):
        # No hidden skip - the caller passes the real latest available
        # month (from latest_available_month()) and the window ends there.
        months = gm.month_window("2026-05", window_months=3)
        assert months[-1] == "2026-05"

    def test_crosses_a_year_boundary_correctly(self):
        months = gm.month_window("2026-01", window_months=3)
        assert months == ["2025-11", "2025-12", "2026-01"]


class TestRingAreaKm2:
    def test_degenerate_ring_is_zero(self):
        assert gm.ring_area_km2([(0.0, 0.0), (0.0, 0.01)]) == 0.0

    def test_small_square_has_plausible_positive_area(self):
        # ~1.1km x 1.1km square at the equator -> roughly 1.2 km^2.
        ring = [(0.0, 0.0), (0.0, 0.01), (0.01, 0.01), (0.01, 0.0), (0.0, 0.0)]
        area = gm.ring_area_km2(ring)
        assert 1.0 < area < 1.5

    def test_area_is_orientation_independent(self):
        ring = [(0.0, 0.0), (0.0, 0.01), (0.01, 0.01), (0.01, 0.0), (0.0, 0.0)]
        reversed_ring = list(reversed(ring))
        assert gm.ring_area_km2(ring) == gm.ring_area_km2(reversed_ring)


class TestDecimateRing:
    def test_ring_at_or_below_target_is_returned_unchanged(self):
        ring = [(float(i), float(i)) for i in range(10)]
        assert gm.decimate_ring(ring, target_vertices=150) == ring

    def test_long_ring_is_reduced_but_stays_closed(self):
        ring = [(float(i) * 0.001, float(i) * 0.001) for i in range(500)]
        ring[-1] = ring[0]  # close it, like a real boundary ring
        decimated = gm.decimate_ring(ring, target_vertices=50)

        assert len(decimated) < len(ring)
        assert len(decimated) >= 3
        assert decimated[-1] == ring[-1]
