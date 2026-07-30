"""Tests for the shared per-point CRS resolver.

Built after a real, serious finding in Norway's vegvesen feed: coordinates
split across two genuinely different CRSes within the same feed (~76%
UTM zone 33N, ~24% WGS84), which a single per-call ``crs=`` override
cannot express. See ``streetworks/common/_crs.py``'s own module docstring.
"""

from streetworks.common._crs import (
    LAMBERT72_BELGIUM,
    UTM33N_NORWAY,
    WGS84,
    WGS84_NORWAY,
    resolve_coordinate_crs,
)

_NORWAY_CANDIDATES = (WGS84_NORWAY, UTM33N_NORWAY)


def test_declared_utm33n_consistent_with_values():
    # Real Kristiansund bridge point (posList order: easting, northing).
    result = resolve_coordinate_crs(
        srs_name="25833",
        raw_a=133396.39,
        raw_b=7018386.84,
        encoding_default="EPSG:4326",
        candidates=_NORWAY_CANDIDATES,
    )
    assert result.epsg == "EPSG:25833"
    assert result.status == "declared"
    # axis order resolved by magnitude: northing (millions) first, easting second
    assert result.ordered == (7018386.84, 133396.39)


def test_inferred_wgs84_no_srs_name():
    # Real Oslo point, pointCoordinates path (lat, lon), no srsName ever present.
    result = resolve_coordinate_crs(
        srs_name=None,
        raw_a=59.946438,
        raw_b=10.712339,
        encoding_default="EPSG:4326",
        candidates=_NORWAY_CANDIDATES,
    )
    assert result.epsg == "EPSG:4326"
    assert result.status == "inferred"
    assert 57 <= result.ordered[0] <= 72  # a real Norwegian latitude band
    assert result.ordered == (59.946438, 10.712339)


def test_contradiction_declared_utm_but_wgs84_values():
    """A declared srsName the values themselves contradict - value-range
    wins, never the declaration. Never observed live for Norway (0/2,636
    real elements), but the resolver must handle it, not assume it can't
    happen."""
    result = resolve_coordinate_crs(
        srs_name="25833",
        raw_a=59.9,
        raw_b=10.7,
        encoding_default="EPSG:4326",
        candidates=_NORWAY_CANDIDATES,
    )
    assert result.epsg == "EPSG:4326"
    assert result.status == "corrected"


def test_no_declaration_and_values_dont_fit_default_belgium_shape():
    """The real Belgium shape: no srsName override stated, but the values
    are clearly Lambert 72, not the assumed WGS84 default - this is
    exactly the case that would have been silently wrong before this
    module existed."""
    result = resolve_coordinate_crs(
        srs_name=None,
        raw_a=150_000.0,
        raw_b=170_000.0,
        encoding_default="EPSG:4326",
        candidates=(WGS84, LAMBERT72_BELGIUM),
    )
    assert result.epsg == "EPSG:31370"
    assert result.status == "corrected"


def test_belgium_lambert72_declared_and_consistent():
    result = resolve_coordinate_crs(
        srs_name="EPSG:31370",
        raw_a=150_000.0,
        raw_b=170_000.0,
        encoding_default="EPSG:4326",
        candidates=(WGS84, LAMBERT72_BELGIUM),
    )
    assert result.epsg == "EPSG:31370"
    assert result.status == "declared"


def test_axis_order_swapped_inputs_resolve_identically():
    """Whichever raw order the source emits, the resolver must land on
    the same correctly-ordered output - resolution is by magnitude, never
    declared/positional order."""
    utm_normal = resolve_coordinate_crs(
        srs_name="25833", raw_a=7018386.84, raw_b=133396.39,
        encoding_default="EPSG:4326", candidates=_NORWAY_CANDIDATES,
    )
    utm_swapped = resolve_coordinate_crs(
        srs_name="25833", raw_a=133396.39, raw_b=7018386.84,
        encoding_default="EPSG:4326", candidates=_NORWAY_CANDIDATES,
    )
    assert utm_normal.ordered == utm_swapped.ordered == (7018386.84, 133396.39)

    wgs84_normal = resolve_coordinate_crs(
        srs_name=None, raw_a=59.946438, raw_b=10.712339,
        encoding_default="EPSG:4326", candidates=_NORWAY_CANDIDATES,
    )
    wgs84_swapped = resolve_coordinate_crs(
        srs_name=None, raw_a=10.712339, raw_b=59.946438,
        encoding_default="EPSG:4326", candidates=_NORWAY_CANDIDATES,
    )
    assert wgs84_normal.ordered == wgs84_swapped.ordered == (59.946438, 10.712339)


def test_srs_name_parses_urn_and_opengis_and_bare_forms():
    for srs_name in (
        "urn:ogc:def:crs:EPSG::25833",
        "http://www.opengis.net/def/crs/EPSG/0/25833",
        "EPSG:25833",
        "25833",
    ):
        result = resolve_coordinate_crs(
            srs_name=srs_name, raw_a=7018386.84, raw_b=133396.39,
            encoding_default="EPSG:4326", candidates=_NORWAY_CANDIDATES,
        )
        assert result.epsg == "EPSG:25833", srs_name
        assert result.status == "declared", srs_name


def test_crs84_alias_resolves_to_wgs84():
    result = resolve_coordinate_crs(
        srs_name="CRS:84", raw_a=59.946438, raw_b=10.712339,
        encoding_default="EPSG:4326", candidates=_NORWAY_CANDIDATES,
    )
    assert result.epsg == "EPSG:4326"
    assert result.status == "declared"


def test_out_of_all_bands_is_unresolved_not_a_silent_guess():
    result = resolve_coordinate_crs(
        srs_name=None, raw_a=99999999.0, raw_b=-99999999.0,
        encoding_default="EPSG:4326", candidates=_NORWAY_CANDIDATES,
    )
    assert result.status == "unresolved"
    assert result.epsg == "EPSG:4326"  # falls back to the stated default, not a guess
    assert result.ordered == (99999999.0, -99999999.0)  # unordered, passed through as-is


def test_declared_to_a_crs_with_no_known_profile_is_trusted_but_unordered():
    """A real EPSG we simply don't have a CrsProfile for - trust the
    declaration (nothing to cross-check it against), but can't resolve
    axis order without a band to check against."""
    result = resolve_coordinate_crs(
        srs_name="EPSG:27700", raw_a=1.0, raw_b=2.0,
        encoding_default="EPSG:4326", candidates=_NORWAY_CANDIDATES,
    )
    assert result.epsg == "EPSG:27700"
    assert result.status == "declared"
    assert result.ordered == (1.0, 2.0)


def test_crs_profile_order_returns_none_when_neither_assignment_fits():
    assert WGS84.order(500_000.0, 6_000_000.0) is None
