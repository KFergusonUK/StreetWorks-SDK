"""Guernsey Street Gazetteer - Guernsey's real, live, keyless street
register. This SDK's second Channel Islands coverage, found by checking
whether Jersey's own real setup (see :mod:`streetworks.arcgis.jersey`)
has a Guernsey sibling - it genuinely does, on the exact same shape.

**Found by mirroring Jersey's own real service, then verifying live -
not assumed from the name alone.** ``roadworks.gov.gg`` (the real
Guernsey analogue of ``roadworks.gov.je``) hosts its own ArcGIS REST
services root: ``GSearch`` (address/street search - the one this module
uses), ``GSW`` (a real, distinct roadworks service, the Guernsey
counterpart to Jersey's ``JSWFeatureService`` - genuinely found, not
consumed here; a real future strand, the same way Jersey's own
``Projects`` layer is noted but unconsumed), ``GuernseyBasemapping``.
``GSearch``'s real layers: ``0 Roads`` (``esriGeometryPolygon`` - the one
:class:`GuernseyStreetsClient` uses), ``1 Postcodes``.

**Real field list** (``Roads``, confirmed via layer metadata and live
sampling): ``OBJECTID``, ``CADASTRE``, ``UPRN`` (a real Unique Property
Reference Number - populated on some rows, not checked as a reliable
per-street key), ``USRN`` (Guernsey's own Unique Street Reference
Number, a distinct numbering block from Jersey's - real values seen in
the ``20000``-``20500`` range), ``X_USRN``/``L_USRN`` (real but
undocumented - both esriFieldTypeDouble, in the same numeric range as
``USRN`` itself; live sampling strongly suggests these are
cross-reference/linked ``USRN`` values to neighbouring polygons, not
coordinates - kept undecoded on ``.raw``, the same discipline NWB's own
``bst_code`` gets), ``ROAD`` (the real street name - **2,591 of 2,727**
real polygon features carry one; the rest are blank), ``CLASS`` (a real,
undocumented 3-letter classification code, e.g. ``"PCP"``, ``"XDA"`` -
kept as :class:`~streetworks.common.StreetType`'s ``code``, undecoded,
the same treatment ``bst_code`` gets), ``PARISH`` (one of Guernsey's own
real parishes, e.g. ``"CASTEL"``).

**No street/pavement distinguishing field, unlike Jersey's own real
``FEATURE`` field.** Guernsey's ``Roads`` layer has no equivalent clean
type indicator - some real ``ROAD`` values are genuine street names
(``"CANDIE ROAD"``, ``"CLOS DU FALLA"``), others are the source's own
label for a car park sharing the same layer/field (``"CAR PARK"``,
observed live). Since there is no documented field to cleanly separate
these, :class:`GuernseyStreetsClient` does not attempt to - every real
non-blank ``ROAD`` value becomes a :class:`~streetworks.common.Street`,
consistent with this SDK's "never fabricate a filter the source doesn't
state" discipline.

**Genuine fractional ``USRN`` subdivisions - confirmed live, a real
numbering convention, not a data-quality issue.** Unlike Jersey's own
``USRN`` (confirmed live to be a whole integer on every real record),
Guernsey's real data includes fractional values, e.g. a real parent
``20194`` with real child polygons ``20194.02``/``20194.04``/
``20194.05``/``20194.06`` (a subdivided car park) - each carries its own
real ``ROAD``/``CLASS``. :func:`streetworks.common.from_guernsey_street`
formats these to two decimal places (masking real IEEE-754 double
encoding noise seen live, e.g. a stated ``20194.05`` arriving over the
wire as ``20194.049999999999``) rather than passing the raw float
through as a string.

**CRS: ``ESRI:102070`` "Guernsey_Grid", confirmed live via an external
projection registry, not assumed from the bare wkid.** ``GSearch``'s own
metadata states only ``"wkid": 102070, "latestWkid": 102070`` - an
Esri-specific code with no EPSG equivalent - cross-checked live against
``epsg.io``/``spatialreference.org``, both agreeing: a real, named local
Transverse Mercator grid specific to the Channel Islands' Guernsey
bailiwick (``latitude_of_origin=49.5``, ``central_meridian=
-2.41666666666667``, ``scale_factor=0.999997``, ``false_easting=47000``,
``false_northing=50000``). **Unlike that stated grid, this layer's real
``f=geojson`` polygon geometry comes back as genuine WGS84** (confirmed
live, coordinates ``-2.58, 49.44``-shaped - correct for Guernsey - with
and without an explicit ``outSR=4326``, byte-identical either way) - the
same real "search service reprojects, roadworks service doesn't" split
Jersey's own two services show; see :mod:`streetworks.arcgis.jersey`'s
module docstring. :data:`CRS` below names the stated (unused-by-geometry)
grid for completeness; it is not the CRS of anything this module's
:class:`GuernseyStreetsClient` actually returns.

**Geometry: absent on the canonical model, not fabricated.** No stated
point/line field exists anywhere on this layer (unlike Jersey's real
``USRN_XY1``/``USRN_XY2`` pair) - only the real polygon itself. Per the
same discipline :mod:`streetworks.common.from_paris` established
(``Coordinate.points`` is documented for line vertices, not polygon
rings - forcing one in would misuse that contract),
:func:`streetworks.common.from_guernsey_street` never does so:
``geometry=None``, ``GeometryGrade.ABSENT`` on every real
:class:`~streetworks.common.Street` this module produces. The real WGS84
polygon is preserved unmodified in ``Street.raw`` for any caller that
needs the full footprint.

**Licence: no explicit statement found, same open-by-design situation as
Jersey.** ``copyrightText`` is an empty string on every service/layer
checked; the public-facing site gates behind a login while the ArcGIS
REST API underneath needs none. No licence document found - genuinely
unconfirmed, not "none exists." Confirm your own reuse/redistribution
rights before redistributing data pulled through this module further
downstream.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .client import ArcGISFeatureClient

__all__ = ["BASE_URL", "STREETS_LAYER", "CRS", "GuernseyStreetsClient"]

JSON = dict[str, Any]

#: The real Guernsey street/address search service. See module docstring.
BASE_URL = "https://roadworks.gov.gg/arcgis/rest/services/GSearch/MapServer"

#: The real streets layer - esriGeometryPolygon (road extent, not a
#: centreline). See module docstring.
STREETS_LAYER = 0

#: ESRI:102070 "Guernsey_Grid" - the layer's own *stated* spatial
#: reference, confirmed live against an external projection registry.
#: **Not** the CRS of this module's real returned geometry, which is
#: WGS84 regardless (confirmed live) - see module docstring.
CRS = "ESRI:102070"


class GuernseyStreetsClient:
    """Fetch Guernsey's real street gazetteer. No credentials required -
    see module docstring for the same open-by-design, no-explicit-licence
    situation Jersey's own services have.

    >>> from streetworks.arcgis.guernsey import GuernseyStreetsClient
    >>> from streetworks.common import from_guernsey_street
    >>> with GuernseyStreetsClient() as guernsey:  # doctest: +SKIP
    ...     streets = [from_guernsey_street(f) for f in guernsey.iter_streets()]
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_streets(self, *, where: str = "ROAD<>' '") -> Iterator[JSON]:
        """Yield every real street feature (GeoJSON ``Feature`` dicts).
        Defaults to the real ``ROAD<>' '`` filter (excludes the 136 real
        rows with no stated name at all - see module docstring); pass
        ``where="1=1"`` for the raw, unfiltered layer instead."""
        yield from self._arcgis.iter_features(
            BASE_URL, STREETS_LAYER, where=where, out_fields="*"
        )

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> GuernseyStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
