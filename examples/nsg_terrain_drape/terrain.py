"""Stated elevation, read raster-agnostically - no GDAL, no rasterio.

Two real, live, credential-free British terrain sources, plus a hand-rolled
single-band raster decoder (GeoTIFF and ESRI ASCII Grid) to read them - the
same "no heavy geospatial stack" ethos as
:mod:`streetworks.openusrn.reader`'s hand-rolled GeoPackage/WKB decoder, one
level up in difficulty (a real binary raster format, not just WKB), but
confirmed tractable by hand-decoding a real response byte-for-byte before
writing a line of the general reader (see the fixtures this module's tests
are built from - genuine WCS/OS Terrain 50 bytes, not synthesised).

**Module-boundary note (read before promoting this out of examples/).**
This lives inside ``examples/nsg_terrain_drape`` deliberately, not as a new
top-level ``streetworks`` package - the identity question ("is this SDK
street-works-only, or does it grow into a general highways-geospatial
client?") is real and not yet decided, so no public API surface is being
declared here. It is written to module standard anyway, on the chance it
does get promoted one day. If that day comes, two lines do not move:

1. **This module serves stated elevation only** - real values a named
   provider (OS, EA, ...) publishes as ground truth, with vertical datum
   labelled as first-class as CRS, never silently assumed equal across
   providers even when (as here) they turn out to agree. It never infers,
   extrapolates, or fabricates a height. Same discipline this SDK already
   applies horizontally (never-silently-reproject); this is that principle
   applied to the Z axis.
2. **Drape, viewshed, and line-of-sight are derived consumers of this
   layer and never fold into it.** This module hands back a labelled grid
   of stated Z; something downstream chooses how to sample or interpolate
   it and owns that choice (and its error). A stated-elevation client and
   an inference engine becoming the same object is exactly the failure
   mode both lines above exist to prevent. ``drape.py`` in this example is
   one such downstream consumer, not a peer inside this module.

**Raster-agnostic by design - this reader does not know what "DTM" means.**
It decodes whatever single-band grid it is handed and carries whatever
``surface_model`` label the caller supplies; it never assumes bare earth.
This was tested against real evidence, not asserted: the Environment
Agency's 2026-08-04 WCS catalogue publishes its Digital Terrain Model
(``13787b9a-...__Lidar_Composite_Elevation_DTM_1m``, bare earth) and its
Digital Surface Model (``df4e3ec3-...__Lidar_Composite_Elevation_FZ_DSM_1m``,
first-return - buildings and vegetation included) as two genuinely separate
live coverages with different dataset UUIDs, confirmed via a real
``GetCapabilities`` call to each - not a naming convention on one service, a
real difference this module has no business collapsing. A future
line-of-sight consumer wants the DSM (buildings and trees block sight, bare
earth doesn't); this example's drape wants the DTM. Neither is the
default - the caller states which :class:`WCSCoverage` it wants.

**The on-demand route beats the bulk-download route, confirmed live -
that's why EA LIDAR is the first-class adapter here and OS Terrain 50 is
the awkward fallback.** EA's LIDAR Composite exposes a real, keyless OGC
WCS 2.0.1 service (``environment.data.gov.uk/spatialdata/.../wcs``) that
serves a GeoTIFF for *any* requested bbox in one call - confirmed live by
fetching a real 300m x 300m subset over central Durham and decoding it
by hand (EPSG:27700, float32, real elevations 30.3-71.6m). OS Terrain 50
has no equivalent subsetting API (its Downloads API, the same mechanism
:mod:`streetworks.openusrn` already uses, only offers the whole ~160MB
GB-wide product) - so :class:`OSTerrain50Client` downloads that once,
caches it, and only *then* extracts the one or few 10km tiles a bbox
actually needs. Same shape as every other live adapter in this SDK
(ask, get data back) for the WCS client; a real, documented compromise for
the bulk one.

**A single small requested bbox can still come back as more than one
internal raster tile - confirmed live, not assumed.** A 39x39 pixel GeoTIFF
subset from the EA WCS came back as *four* internal 32x32 TIFF tiles (2x2),
not one - GeoServer's own internal tiling boundary fell inside the
requested area. A reader that only handled the single-tile case (like the
first real sample pulled during investigation, which happened to fit in
one tile) would have silently worked on every test and then broken on the
first real AOI large enough to cross a tile boundary. :func:`read_geotiff`
handles N tiles unconditionally - there is no single-tile special case.

**Pixel anchoring: PixelIsArea, sampled at the pixel centre.** Every real
GeoTIFF from this WCS declares ``GTRasterTypeGeoKey=1`` (PixelIsArea) -
raster index (i, j) is the pixel's upper-left corner, not its value's
location. :func:`read_geotiff` and :func:`read_ascii_grid` both resolve
``origin_x``/``origin_y`` to pixel *centres* (offsetting by half a pixel)
so :meth:`ElevationGrid.sample` never has to guess which convention a
given grid used - both readers normalise to the same one.

**Rotation/shear is refused, not silently dropped.** GeoTIFF's
``ModelTransformationTag`` is a general affine and can in principle carry
off-axis terms; every real sample seen from this WCS is axis-aligned
(cross terms exactly ``0.0``). :func:`read_geotiff` checks this and raises
``ValueError`` rather than silently ignoring a rotation it was never tested
against - an honest gap, not a guess (same posture as
:mod:`streetworks.common._wkt`'s "not a general WKT parser, extend it if a
future source needs more").

**Compression must be none.** Every real response seen is uncompressed
(``Compression=1``); a compressed TIFF raises ``NotImplementedError`` rather
than being misread as raw pixel bytes.

**Vertical datum, stated per source, never assumed equal.** OS Terrain 50's
own real tile metadata (``Metadata_NZ24.xml``, fetched live) states
``urn:ogc:def:crs:EPSG::5701`` / "Ordnance Datum Newlyn" explicitly - not
assumed from the horizontal CRS. The Environment Agency states its LIDAR
Composite heights are "referenced to Ordinance Survey Newlyn... using the
OSTN'15 transformation method" on its own dataset page. Both real answers
turn out to be the same datum (ODN) - genuinely useful to know for the
Norway comparison this feeds (NVDB's NN2000 is a *different* datum, see
``streetworks/nvdb/models.py``) - but each is carried as its own source's
stated claim, not inferred from the other or from the fact that both
providers are British.

**GDAL_NODATA is a real sentinel, not documentation** - confirmed live:
the Environment Agency's own WCS emits the ASCII tag
``-3.4028234663852886E38`` (approximately ``-FLT_MAX``, GDAL's own no-data
convention for float32 rasters), not a round number like ``-9999``. OS
Terrain 50's own ASCII Grid tiles omit the ``NODATA_value`` header line
entirely when a tile has no no-data cells (confirmed live against a real
Durham tile) - :func:`read_ascii_grid` treats that header line as optional.
"""

from __future__ import annotations

import io
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

__all__ = [
    "ElevationGrid",
    "read_geotiff",
    "read_ascii_grid",
    "WCSCoverage",
    "EA_LIDAR_DTM_1M",
    "EA_LIDAR_DSM_1M",
    "EALidarWCSClient",
    "OSTerrain50Client",
]

# ---------------------------------------------------------------------------
# The grid model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ElevationGrid:
    """One real, stated elevation surface - a regular grid of Z values with
    its own CRS, vertical datum, and surface-model declaration, all carried
    as first-class fields (see module docstring's module-boundary note).
    Every value is provider-stated; this type never carries an inferred one.

    ``values`` is row-major, ``values[row][col]``, row 0 = the *northernmost*
    row (both readers in this module normalise to this regardless of the
    source format's own on-disk row order). ``origin_x``/``origin_y`` is the
    real-world position of the *centre* of ``values[0][0]`` (see the
    module docstring's PixelIsArea note) in ``crs``. ``pixel_size_x`` is
    positive (x increases with column); ``pixel_size_y`` is negative (y
    decreases with row) - both in the same units as ``crs``.
    """

    values: tuple[tuple[float, ...], ...]
    origin_x: float
    origin_y: float
    pixel_size_x: float
    pixel_size_y: float
    width: int
    height: int
    crs: str
    vertical_datum: str
    surface_model: str
    nodata: float | None = None

    def sample(self, x: float, y: float) -> float | None:
        """Bilinear-interpolated elevation at real-world ``(x, y)`` in this
        grid's own ``crs`` - ``None`` if ``(x, y)`` falls outside the grid,
        or any of the four neighbours it would blend is no-data (never
        fabricate a value by blending across a real gap)."""
        col_f = (x - self.origin_x) / self.pixel_size_x
        row_f = (y - self.origin_y) / self.pixel_size_y
        if not (0.0 <= col_f <= self.width - 1 and 0.0 <= row_f <= self.height - 1):
            return None
        col0, row0 = int(col_f), int(row_f)
        col1, row1 = min(col0 + 1, self.width - 1), min(row0 + 1, self.height - 1)
        fx, fy = col_f - col0, row_f - row0

        def _at(r: int, c: int) -> float | None:
            v = self.values[r][c]
            return None if self.nodata is not None and v == self.nodata else v

        v00, v01, v10, v11 = _at(row0, col0), _at(row0, col1), _at(row1, col0), _at(row1, col1)
        if v00 is None or v01 is None or v10 is None or v11 is None:
            return None
        top = v00 * (1 - fx) + v01 * fx
        bottom = v10 * (1 - fx) + v11 * fx
        return top * (1 - fy) + bottom * fy


# ---------------------------------------------------------------------------
# GeoTIFF - stdlib struct only, tiled or stripped, single band
# ---------------------------------------------------------------------------

_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 11: 4, 12: 8}
_SAMPLE_FORMAT_CODE = {
    (8, 1): "B", (8, 2): "b",
    (16, 1): "H", (16, 2): "h",
    (32, 1): "I", (32, 2): "i", (32, 3): "f",
    (64, 3): "d",
}
_TAG_IMAGE_WIDTH = 256
_TAG_IMAGE_LENGTH = 257
_TAG_BITS_PER_SAMPLE = 258
_TAG_COMPRESSION = 259
_TAG_SAMPLES_PER_PIXEL = 277
_TAG_STRIP_OFFSETS = 273
_TAG_STRIP_BYTE_COUNTS = 279
_TAG_TILE_WIDTH = 322
_TAG_TILE_LENGTH = 323
_TAG_TILE_OFFSETS = 324
_TAG_TILE_BYTE_COUNTS = 325
_TAG_SAMPLE_FORMAT = 339
_TAG_MODEL_PIXEL_SCALE = 33550
_TAG_MODEL_TIEPOINT = 33922
_TAG_MODEL_TRANSFORMATION = 34264
_TAG_GEO_KEY_DIRECTORY = 34735
_TAG_GDAL_NODATA = 42113
_GEOKEY_PROJECTED_CS = 3072
_GEOKEY_GEOGRAPHIC_CS = 2048


class _TiffIFD:
    """One decoded IFD: tag id -> raw values tuple, byte order kept for
    re-reading offset-referenced blocks (tile bytes, ASCII tags)."""

    def __init__(self, data: bytes, endian: str, entries: dict[int, tuple]):
        self.data = data
        self.endian = endian
        self.entries = entries

    def get(self, tag: int, default=None):
        return self.entries.get(tag, default)

    def require(self, tag: int):
        if tag not in self.entries:
            raise ValueError(f"GeoTIFF missing required tag {tag}")
        return self.entries[tag]


def _read_ifd(data: bytes) -> _TiffIFD:
    if data[:2] == b"II":
        endian = "<"
    elif data[:2] == b"MM":
        endian = ">"
    else:
        raise ValueError("not a TIFF (bad byte-order mark)")
    magic = struct.unpack(endian + "H", data[2:4])[0]
    if magic != 42:
        raise ValueError(f"not a TIFF (bad magic number {magic})")
    ifd_offset = struct.unpack(endian + "I", data[4:8])[0]
    n_entries = struct.unpack(endian + "H", data[ifd_offset : ifd_offset + 2])[0]
    entries: dict[int, tuple] = {}
    for i in range(n_entries):
        entry_off = ifd_offset + 2 + i * 12
        tag, field_type, count = struct.unpack(endian + "HHI", data[entry_off : entry_off + 8])
        raw = data[entry_off + 8 : entry_off + 12]
        size = _TYPE_SIZES.get(field_type, 4) * count
        block = raw if size <= 4 else data[struct.unpack(endian + "I", raw)[0] :]
        if field_type == 2:  # ASCII
            entries[tag] = (block[:count].split(b"\x00", 1)[0].decode("ascii"),)
        elif field_type == 3:  # SHORT
            entries[tag] = struct.unpack(endian + f"{count}H", block[: count * 2])
        elif field_type == 4:  # LONG
            entries[tag] = struct.unpack(endian + f"{count}I", block[: count * 4])
        elif field_type == 5:  # RATIONAL (num, den) pairs
            entries[tag] = struct.unpack(endian + f"{count * 2}I", block[: count * 8])
        elif field_type == 12:  # DOUBLE
            entries[tag] = struct.unpack(endian + f"{count}d", block[: count * 8])
        # other field types (BYTE, SBYTE, FLOAT, ...) aren't needed by any
        # tag this reader consults - not decoded, left out of entries.
    return _TiffIFD(data, endian, entries)


def _geokey_epsg(ifd: _TiffIFD) -> str | None:
    directory = ifd.get(_TAG_GEO_KEY_DIRECTORY)
    if not directory or len(directory) < 4:
        return None
    n_keys = directory[3]
    for i in range(n_keys):
        base = 4 + i * 4
        if base + 4 > len(directory):
            break
        key_id, tag_location, _count, value = directory[base : base + 4]
        if tag_location != 0:
            continue  # value lives in GeoDoubleParams/GeoAsciiParams - not handled, honest gap
        if key_id in (_GEOKEY_PROJECTED_CS, _GEOKEY_GEOGRAPHIC_CS) and value not in (0, 32767):
            return f"EPSG:{value}"
    return None


def _geotransform(ifd: _TiffIFD) -> tuple[float, float, float, float]:
    """Returns (origin_x, origin_y, pixel_size_x, pixel_size_y) for pixel
    *centres*, normalising both GeoTIFF georeferencing conventions this
    module supports to the same PixelIsArea-corrected anchor (see module
    docstring)."""
    matrix = ifd.get(_TAG_MODEL_TRANSFORMATION)
    if matrix:
        a0, a1, _a2, a3, a4, a5, _a6, a7 = matrix[:8]
        if a1 != 0.0 or a4 != 0.0:
            raise ValueError("rotated/sheared GeoTIFF (non-zero ModelTransformationTag cross "
                              "terms) is not supported - refusing rather than misreading it")
        # (0, 0) is the upper-left *corner* of pixel (0,0) under PixelIsArea;
        # its centre is (0.5, 0.5) in raster space.
        return (a0 * 0.5 + a3, a5 * 0.5 + a7, a0, a5)
    scale = ifd.get(_TAG_MODEL_PIXEL_SCALE)
    tiepoint = ifd.get(_TAG_MODEL_TIEPOINT)
    if scale and tiepoint and len(tiepoint) >= 6:
        i0, j0, _k0, x0, y0, _z0 = tiepoint[:6]
        if i0 != 0.0 or j0 != 0.0:
            raise ValueError("ModelTiepointTag with a non-origin tiepoint is not supported")
        sx, sy, _sz = scale[:3]
        return (x0 + sx * 0.5, y0 - sy * 0.5, sx, -sy)
    raise ValueError("GeoTIFF has neither ModelTransformationTag nor "
                      "ModelPixelScaleTag+ModelTiepointTag - can't georeference it")


def _sample_struct_code(bits: int, sample_format: int) -> str:
    code = _SAMPLE_FORMAT_CODE.get((bits, sample_format))
    if code is None:
        raise NotImplementedError(f"unsupported BitsPerSample={bits}/SampleFormat={sample_format}")
    return code


def _decode_samples(endian: str, code: str, raw: bytes) -> tuple[float, ...]:
    n = len(raw) // struct.calcsize(code)
    return struct.unpack(f"{endian}{n}{code}", raw)


def read_geotiff(
    data: bytes, *, surface_model: str, vertical_datum: str, crs: str | None = None
) -> ElevationGrid:
    """Decode a single-band GeoTIFF into an :class:`ElevationGrid`. Handles
    both tiled and stripped layouts, any real ``BitsPerSample``/
    ``SampleFormat`` combination this module has seen live (8/16/32-bit
    int or unsigned, 32/64-bit float), and mosaics an arbitrary number of
    internal tiles - see the module docstring for why that last part isn't
    optional. ``surface_model``/``vertical_datum`` are the caller's own
    stated labels (this reader has no opinion on what the pixels mean);
    ``crs`` overrides the EPSG code this function would otherwise read from
    the file's own ``GeoKeyDirectoryTag``, for the (unencountered so far)
    case where a source's GeoTIFF doesn't carry one."""
    ifd = _read_ifd(data)
    width = ifd.require(_TAG_IMAGE_WIDTH)[0]
    height = ifd.require(_TAG_IMAGE_LENGTH)[0]
    if ifd.get(_TAG_SAMPLES_PER_PIXEL, (1,))[0] != 1:
        raise NotImplementedError("only single-band GeoTIFFs are supported")
    if ifd.get(_TAG_COMPRESSION, (1,))[0] != 1:
        raise NotImplementedError("only uncompressed GeoTIFFs are supported")
    bits = ifd.require(_TAG_BITS_PER_SAMPLE)[0]
    sample_format = ifd.get(_TAG_SAMPLE_FORMAT, (1,))[0]
    code = _sample_struct_code(bits, sample_format)
    endian = ifd.endian

    rows: list[list[float]] = [[0.0] * width for _ in range(height)]

    tile_width = ifd.get(_TAG_TILE_WIDTH)
    if tile_width:
        tile_height = ifd.get(_TAG_TILE_LENGTH)[0]
        tile_width = tile_width[0]
        offsets = ifd.require(_TAG_TILE_OFFSETS)
        byte_counts = ifd.require(_TAG_TILE_BYTE_COUNTS)
        tiles_across = -(-width // tile_width)  # ceil
        for idx, (offset, count) in enumerate(zip(offsets, byte_counts, strict=True)):
            tile_row, tile_col = divmod(idx, tiles_across)
            values = _decode_samples(endian, code, data[offset : offset + count])
            row0, col0 = tile_row * tile_height, tile_col * tile_width
            for r in range(min(tile_height, height - row0)):
                src = r * tile_width
                rows[row0 + r][col0 : col0 + min(tile_width, width - col0)] = (
                    values[src : src + min(tile_width, width - col0)]
                )
    else:
        offsets = ifd.require(_TAG_STRIP_OFFSETS)
        byte_counts = ifd.require(_TAG_STRIP_BYTE_COUNTS)
        row = 0
        for offset, count in zip(offsets, byte_counts, strict=True):
            values = _decode_samples(endian, code, data[offset : offset + count])
            n_rows = len(values) // width
            for r in range(n_rows):
                rows[row + r] = list(values[r * width : (r + 1) * width])
            row += n_rows
        if row != height:
            raise ValueError(f"strip decode produced {row} rows, expected {height}")

    origin_x, origin_y, pixel_size_x, pixel_size_y = _geotransform(ifd)
    resolved_crs = crs or _geokey_epsg(ifd)
    if resolved_crs is None:
        raise ValueError(
            "no CRS declared (GeoKeyDirectoryTag) and none supplied - refusing to guess"
        )
    nodata_raw = ifd.get(_TAG_GDAL_NODATA)
    nodata = float(nodata_raw[0]) if nodata_raw else None

    return ElevationGrid(
        values=tuple(tuple(r) for r in rows),
        origin_x=origin_x, origin_y=origin_y,
        pixel_size_x=pixel_size_x, pixel_size_y=pixel_size_y,
        width=width, height=height,
        crs=resolved_crs, vertical_datum=vertical_datum, surface_model=surface_model,
        nodata=nodata,
    )


# ---------------------------------------------------------------------------
# ESRI ASCII Grid - plain text, stdlib only
# ---------------------------------------------------------------------------

_ASCII_HEADER_KEYS = {
    "ncols", "nrows", "xllcorner", "xllcenter", "yllcorner", "yllcenter",
    "cellsize", "nodata_value",
}


def read_ascii_grid(
    text: str, *, surface_model: str, vertical_datum: str, crs: str = "EPSG:27700"
) -> ElevationGrid:
    """Decode an ESRI ASCII Grid (``.asc``) into an :class:`ElevationGrid`.
    The ``NODATA_value`` header line is optional (OS Terrain 50 omits it on
    tiles with no no-data cells - confirmed live, see module docstring);
    ``xllcorner``/``yllcorner`` (cell corner) and ``xllcenter``/
    ``yllcenter`` (cell centre) are both accepted, since the ESRI format
    permits either."""
    lines = text.splitlines()
    header: dict[str, float] = {}
    body_start = 0
    for i, line in enumerate(lines):
        parts = line.split()
        if len(parts) != 2 or parts[0].lower() not in _ASCII_HEADER_KEYS:
            body_start = i
            break
        header[parts[0].lower()] = float(parts[1])
    else:
        raise ValueError("ASCII Grid has no data rows after its header")

    ncols, nrows = int(header["ncols"]), int(header["nrows"])
    cellsize = header["cellsize"]
    if "xllcenter" in header:
        x_center0 = header["xllcenter"]
    else:
        x_center0 = header["xllcorner"] + cellsize / 2
    if "yllcenter" in header:
        y_center0 = header["yllcenter"]
    else:
        y_center0 = header["yllcorner"] + cellsize / 2

    data_rows = [line.split() for line in lines[body_start : body_start + nrows]]
    if len(data_rows) != nrows or any(len(r) != ncols for r in data_rows):
        raise ValueError(f"ASCII Grid body doesn't match declared {ncols}x{nrows}")
    # File rows are north-to-south already (row 0 = top = north) - matches
    # this module's ElevationGrid convention directly, no flip needed.
    values = tuple(tuple(float(v) for v in row) for row in data_rows)

    return ElevationGrid(
        values=values,
        origin_x=x_center0,
        origin_y=y_center0 + (nrows - 1) * cellsize,
        pixel_size_x=cellsize, pixel_size_y=-cellsize,
        width=ncols, height=nrows,
        crs=crs, vertical_datum=vertical_datum, surface_model=surface_model,
        nodata=header.get("nodata_value"),
    )


# ---------------------------------------------------------------------------
# EA LIDAR Composite - on-demand WCS, the first-class adapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WCSCoverage:
    """One real, live-confirmed EA LIDAR Composite WCS coverage - a
    dataset's own stated identity (URL, coverage id, surface model,
    vertical datum), never something this module infers from a naming
    convention. See :data:`EA_LIDAR_DTM_1M`/:data:`EA_LIDAR_DSM_1M`."""

    wcs_url: str
    coverage_id: str
    surface_model: str
    vertical_datum: str = "Ordnance Survey Newlyn (ODN) via OSTN'15"


#: Bare earth. Confirmed live 2026-08-04 (GetCapabilities against
#: environment.data.gov.uk's own WCS).
EA_LIDAR_DTM_1M = WCSCoverage(
    wcs_url="https://environment.data.gov.uk/spatialdata/"
    "lidar-composite-digital-terrain-model-dtm-1m/wcs",
    coverage_id="13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m",
    surface_model="DTM",
)

#: First-return surface (buildings, vegetation included) - the layer a
#: future line-of-sight consumer would want, DTM would not. Confirmed live
#: 2026-08-04, a genuinely separate coverage (different dataset UUID) from
#: the DTM above, not a parameter on the same one.
EA_LIDAR_DSM_1M = WCSCoverage(
    wcs_url="https://environment.data.gov.uk/spatialdata/"
    "lidar-composite-digital-surface-model-first-return-dsm-1m/wcs",
    coverage_id="df4e3ec3-315e-48aa-aaaf-b5ae74d7b2bb__Lidar_Composite_Elevation_FZ_DSM_1m",
    surface_model="DSM",
)


class EALidarWCSClient:
    """Ask a bbox, get a real elevation grid back - the Environment
    Agency's keyless OGC WCS 2.0.1 service, confirmed live (see module
    docstring). Same request/response shape as every other live adapter in
    this SDK; no bulk download, no tile bookkeeping.

    >>> from examples.nsg_terrain_drape.terrain import EALidarWCSClient, EA_LIDAR_DTM_1M
    >>> with EALidarWCSClient(EA_LIDAR_DTM_1M) as ea:
    ...     grid = ea.fetch(min_e=427000, min_n=542000, max_e=427300, max_n=542300)
    ...     grid.sample(427150, 542150)
    """

    def __init__(
        self,
        coverage: WCSCoverage = EA_LIDAR_DTM_1M,
        *,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ):
        self.coverage = coverage
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)

    def fetch(self, *, min_e: float, min_n: float, max_e: float, max_n: float) -> ElevationGrid:
        """Fetch the real elevation grid covering ``[min_e, max_e]`` x
        ``[min_n, max_n]`` (EPSG:27700 metres). One HTTP call; the response
        may internally be one or many GeoTIFF tiles (see module docstring),
        handled transparently by :func:`read_geotiff`."""
        params = {
            "request": "GetCoverage",
            "service": "WCS",
            "version": "2.0.1",
            "coverageId": self.coverage.coverage_id,
            "subset": [f"E({min_e},{max_e})", f"N({min_n},{max_n})"],
            "format": "image/tiff",
        }
        response = self._client.get(self.coverage.wcs_url, params=params)
        response.raise_for_status()
        return read_geotiff(
            response.content,
            surface_model=self.coverage.surface_model,
            vertical_datum=self.coverage.vertical_datum,
            crs="EPSG:27700",
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> EALidarWCSClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# OS Terrain 50 - bulk download + cache, the awkward fallback
# ---------------------------------------------------------------------------

_PRODUCT_URL = "https://api.os.uk/downloads/v1/products/Terrain50"
_ARCHIVE_FORMAT = "ASCII Grid and GML (Grid)"
_ARCHIVE_FILENAME = "terr50_gagg_gb.zip"
#: Confirmed live in a real tile's own metadata (Metadata_NZ24.xml,
#: 2026-08-04): urn:ogc:def:crs:EPSG::5701, "Ordnance Datum Newlyn".
_VERTICAL_DATUM = "Ordnance Datum Newlyn (EPSG:5701)"

# The standard OS National Grid two-letter 100km-square algorithm - cross-
# checked live against a known real square (Durham, E427000/N542000 ->
# "NZ", confirmed against OS Terrain 50's own tile naming).
_GRID_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"  # 25 letters, I omitted


def _os_grid_square(easting: float, northing: float) -> str:
    e100k, n100k = int(easting // 100_000), int(northing // 100_000)
    if not (0 <= e100k <= 6 and 0 <= n100k <= 12):
        raise ValueError(
            f"({easting}, {northing}) is outside the OS National Grid's lettered range"
        )
    l1 = (19 - n100k) - (19 - n100k) % 5 + (e100k + 10) // 5
    l2 = (19 - n100k) * 5 % 25 + e100k % 5
    return _GRID_LETTERS[l1] + _GRID_LETTERS[l2]


def _os_grid_tile_ref(easting: float, northing: float) -> str:
    """The 4-character 10km tile reference (e.g. ``"NZ24"``) OS Terrain 50's
    own tile filenames use."""
    square = _os_grid_square(easting, northing)
    e10k, n10k = int(easting // 10_000) % 10, int(northing // 10_000) % 10
    return f"{square}{e10k}{n10k}"


def _mosaic(grids: list[ElevationGrid]) -> ElevationGrid:
    """Combine same-resolution, grid-aligned tiles into one
    :class:`ElevationGrid`. Only used for OS Terrain 50, whose 10km tiles
    are always exactly grid-aligned (a real property of the OS National
    Grid, not assumed) - not a general-purpose raster mosaicker."""
    if len(grids) == 1:
        return grids[0]
    first = grids[0]
    for g in grids[1:]:
        this = (g.pixel_size_x, g.pixel_size_y, g.crs, g.vertical_datum, g.surface_model)
        that = (
            first.pixel_size_x, first.pixel_size_y, first.crs,
            first.vertical_datum, first.surface_model,
        )
        if this != that:
            raise ValueError("can't mosaic tiles with different resolution, CRS, or labelling")

    min_x = min(g.origin_x for g in grids)
    max_y = max(g.origin_y for g in grids)
    max_x = max(g.origin_x + (g.width - 1) * g.pixel_size_x for g in grids)
    min_y = min(g.origin_y + (g.height - 1) * g.pixel_size_y for g in grids)
    width = round((max_x - min_x) / first.pixel_size_x) + 1
    height = round((min_y - max_y) / first.pixel_size_y) + 1
    nodata = first.nodata if first.nodata is not None else float("nan")
    rows = [[nodata] * width for _ in range(height)]
    for g in grids:
        col_off = round((g.origin_x - min_x) / first.pixel_size_x)
        row_off = round((g.origin_y - max_y) / first.pixel_size_y)
        for r in range(g.height):
            rows[row_off + r][col_off : col_off + g.width] = g.values[r]

    return ElevationGrid(
        values=tuple(tuple(r) for r in rows),
        origin_x=min_x, origin_y=max_y,
        pixel_size_x=first.pixel_size_x, pixel_size_y=first.pixel_size_y,
        width=width, height=height,
        crs=first.crs, vertical_datum=first.vertical_datum, surface_model=first.surface_model,
        nodata=first.nodata,
    )


class OSTerrain50Client:
    """Bulk-download-then-cache access to OS Terrain 50 (50m-post DTM,
    ASCII Grid format) - the awkward fallback next to
    :class:`EALidarWCSClient`'s on-demand subsetting (see module
    docstring). The whole GB product is one ~160MB zip of 10km-tile zips
    (confirmed live: ``data/{sq}/{sq}{e}{n}_OST50GRID_{date}.zip`` ->
    ``{TILE}.asc``) - downloaded once via the same OS Data Hub Downloads
    API :mod:`streetworks.openusrn` already uses, cached to disk, and only
    the tile(s) a requested bbox actually needs are ever extracted.

    >>> from examples.nsg_terrain_drape.terrain import OSTerrain50Client
    >>> with OSTerrain50Client(cache_dir="./cache") as os50:
    ...     grid = os50.fetch(min_e=427000, min_n=542000, max_e=430000, max_n=545000)
    """

    def __init__(
        self,
        *,
        cache_dir: str | Path = ".",
        timeout: float = 600.0,
        client: httpx.Client | None = None,
    ):
        self.cache_dir = Path(cache_dir)
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._archive_path = self.cache_dir / _ARCHIVE_FILENAME

    def _ensure_archive(self) -> Path:
        if self._archive_path.exists():
            return self._archive_path
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        response = self._client.get(f"{_PRODUCT_URL}/downloads", params={"format": _ARCHIVE_FORMAT})
        response.raise_for_status()
        entries = response.json()
        if not entries:
            raise ValueError(f"no {_ARCHIVE_FORMAT!r} download available for OS Terrain 50")
        with self._client.stream("GET", entries[0]["url"]) as stream:
            stream.raise_for_status()
            tmp = self._archive_path.with_suffix(".part")
            with open(tmp, "wb") as f:
                for chunk in stream.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
            tmp.rename(self._archive_path)
        return self._archive_path

    def _read_tile(self, outer: zipfile.ZipFile, tile_ref: str) -> ElevationGrid:
        square = tile_ref[:2].lower()
        prefix = f"data/{square}/{tile_ref.lower()}_"
        candidates = [n for n in outer.namelist() if n.lower().startswith(prefix)]
        if not candidates:
            raise ValueError(
                f"no OS Terrain 50 tile for grid square {tile_ref!r} "
                "(outside Great Britain, or a wholly-sea 10km square)"
            )
        inner_bytes = outer.read(candidates[0])
        with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
            text = inner.read(f"{tile_ref.upper()}.asc").decode("ascii")
        return read_ascii_grid(text, surface_model="DTM", vertical_datum=_VERTICAL_DATUM)

    def fetch(self, *, min_e: float, min_n: float, max_e: float, max_n: float) -> ElevationGrid:
        """Fetch (downloading/caching the archive on first use) and mosaic
        every 10km tile overlapping the bbox (EPSG:27700 metres) into one
        :class:`ElevationGrid`."""
        archive = self._ensure_archive()
        tile_refs = sorted(
            {
                _os_grid_tile_ref(e, n)
                for e in (min_e, max_e)
                for n in (min_n, max_n)
            }
            | {
                _os_grid_tile_ref(e, n)
                for e in range(int(min_e // 10_000 * 10_000), int(max_e) + 1, 10_000)
                for n in range(int(min_n // 10_000 * 10_000), int(max_n) + 1, 10_000)
            }
        )
        with zipfile.ZipFile(archive) as outer:
            grids = [self._read_tile(outer, ref) for ref in tile_refs]
        return _mosaic(grids)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OSTerrain50Client:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
