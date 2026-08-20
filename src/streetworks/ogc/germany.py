"""German state (Bundesland) roadworks - a declarative field-map registry
over :class:`~streetworks.ogc.client.OGCFeaturesClient`.

Adding a new state is writing a new :class:`StateFieldMap` entry, not a new
converter - :func:`streetworks.common.from_ogc_features` reads the map
generically. Five states are live, all verified against real data - the
first three 2026-07, Baden-Württemberg and Schleswig-Holstein 2026-08-20:

- **Hamburg** (``de.hh.up:baustelle``, WFS 2.0.0/1.1.0): 130 real features,
  ``Point`` geometry, dates ``DD.MM.YYYY`` (``baubeginn``/``bauende``).
  **Access mode resolved, not assumed**: the state's open-data catalogue
  also lists a "direct GeoJSON download" - confirmed live to be a ZIP
  wrapper around this same WFS (containing
  ``de_hh_up_baustelle_EPSG_4326.json``), not a separate source. The direct
  WFS ``GetFeature`` call is the canonical path here - one HTTP request,
  no archive to unpack, identical data. No road number/name field exists
  anywhere in the real data (checked all 130 features, 0 road-like keys) -
  left unmapped rather than extracted from ``titel`` text, which would be
  inference. No clean single status field either (six independent boolean
  flags instead - ``iststoerung``, ``istfreigegeben``,
  ``istoepnveingeschraenkt``, ... - all preserved in ``.raw``, none forced
  into ``WorksSite.status``).
- **Brandenburg** (``app:baustelleninfo``, WFS 2.0.0): 487 real features,
  ``LineString`` geometry (2 vertices per segment in the live sample),
  dates ISO (``Baustellen_Beginn``/``Baustellen_Ende``, bare dates, no
  time component - always 10 characters, checked across the whole feed).
  The OGC API Features URL from the original design notes 404s live; the
  WFS is the confirmed-working path. One real field name differs from
  what was documented before checking: it's ``Straßenummner`` (double
  "n") - a typo baked into the source schema itself, not
  ``Straßennummer``. The WFS's own capabilities document states its data
  ultimately originates from a Mobilithek DATEX II feed, republished as
  WFS/GeoJSON server-side - convenient for this client (no DATEX parsing
  needed) but noted here since it explains the schema's shape.
  **Grouping deliberately not attempted**: the ``ID`` field has real
  prefix/suffix structure (``"267201193_1"``, ``"_2"``, ``"_3"``, ...) -
  140 of 164 distinct prefixes are multi-record - but agreement within a
  group is only ~81-88% (dates, type, road), nowhere near Autobahn's
  clean 100%, and there's no independent field corroborating it the way
  Autobahn's "Gesamtmaßnahme" date does. Per the project's record-identity
  discipline (raise a grouping signal, don't act on it unilaterally
  without stronger evidence), this ships 1:1 like every other state.
- **Saxony (Sachsen)**: 1,531 real closures (``Sperrungen``) + 813 real
  diversion routes (``Umleitungen``), ``LineString`` geometry, dates
  ``DD.MM.YYYY`` (``Sperrung_von``/``Sperrung_bis``). **No queryable
  service exists at all** - the "GDI-Baustellen-WFS" a news item once
  referenced doesn't exist as a live endpoint (checked exhaustively via
  the GDI-DE catalogue's own CSW search - 5 real metadata records for
  Saxony's SPERRINFOSYS, none link a working WFS); what's actually there
  is a WMS (renders images, out of scope) and a **direct GeoJSON ZIP
  download** (confirmed working -
  ``Baustelleninfo_Sachsen_geojson.zip``, containing separate closures
  and diversions files). Retains historical records (90/1,531 real
  closures were already past-dated at fetch time - not filtered out, the
  Brandenburg/Hamburg convention of "map with real dates" applies here
  too). Richest source in the cluster - district and municipal roadworks
  aggregated alongside state roads, not state-roads-only like Hamburg/
  Brandenburg.

  **CRS is EPSG:25833 (UTM33N), not WGS84 - genuinely, not by omission.**
  Checked the WMS capabilities, the direct download itself (``"crs":
  {"type": "name", "properties": {"name": "EPSG:25833"}}`` on the
  FeatureCollection), and even the separate "planned works" dataset's own
  ISO metadata (``EPSG/0/25833``) - no WGS84 variant exists anywhere for
  this data. Rather than park a source this rich over an axis-order
  technicality, or silently reproject (which this SDK never does), Saxony
  ships with its real CRS carried through and labelled explicitly on
  ``Coordinate.crs`` - the same policy already used for this SDK's
  British National Grid providers (OS Open USRN, DataVIA, Street
  Manager). GeoJSON ``coordinates`` are ``[easting, northing]`` in this
  feed (confirmed against real values, e.g. ``400720.257, 5667893.864``
  in the Meißen area) - taken as-is, no axis flip, matching exactly how
  ``from_streetmanager`` handles BNG. The Germany-wide lon/lat bounds
  check doesn't apply to this state; :data:`SAXONY_EASTING_RANGE`/
  :data:`SAXONY_NORTHING_RANGE` are the equivalent sanity guard, verified
  against the real 1,531-feature feed (easting 281,960-500,138, northing
  5,566,743-5,721,829), not assumed.

  **Another grouping signal, raised not acted on, same as Brandenburg's.**
  Saxony's ``ID`` property isn't unique - 1,531 real features, only 1,133
  distinct ``ID`` values (398 duplicated). Spot-checked: a duplicated ID
  is one closure whose geometry is split across several ``LineString``
  features (same dates, same location text, different road segments) -
  the same shape of thing as Brandenburg's prefix groups, just via a
  different field and not yet checked across the full 398 for agreement
  strength. Ships 1:1 like every other state in this cluster, for the
  same reason: a real pattern worth knowing about, not evidence strong
  enough (or checked thoroughly enough here) to build grouping logic on.

- **Baden-Württemberg**: 928 real features, ``LineString`` geometry, a
  real direct GeoJSON download - no WFS query needed at all (MobiData BW,
  ``api.mobidata-bw.de``, the state's own real transport-data platform,
  run by Verkehrsministerium Baden-Württemberg - confirmed via the
  platform's own CKAN API, ``dl-de/by-2-0``). Covers Bundesstraßen,
  Landesstraßen and Kreisstraßen (federal/state/county roads) - never
  municipal streets, a real ``MULTI_AUTHORITY_INTERURBAN`` scope, not
  comprehensive. **The one state in this cluster with a genuine
  time-of-day, not just a date** - ``starttime``/``endtime`` state a full
  ISO 8601 datetime with an explicit UTC offset (e.g.
  ``"2015-06-01T00:00:00.000+02:00"``), parsed via
  ``datetime.fromisoformat`` (the new ``"iso_datetime"``
  :class:`DateField` format) rather than the date-only path every other
  state uses. **A third real per-feature-identifier shape**: neither a
  meaningful ``ID`` property (Brandenburg's shape) nor the GeoJSON
  feature's own ``id`` (Hamburg's shape) - the real identifier lives in a
  lowercase ``id`` *property* instead, handled via the new
  :attr:`StateFieldMap.id_field` override. ``type``/``subtype`` split
  cleanly into a real binary (``"ROAD_CLOSED"``, 505; ``"CONSTRUCTION"``,
  423) - used as ``status_field``.
- **Schleswig-Holstein**: 1,116 real features, genuinely GML-only -
  confirmed live via a real ``OUTPUTFORMAT=application/json`` request
  rejected outright (the same shape Mecklenburg-Vorpommern's and
  Saxony-Anhalt's own dedicated WFS already reject), parsed client-side
  via the standard library's own ``xml.etree.ElementTree`` (see
  :func:`_fetch_lbv_sh_gml`/:func:`_parse_lbv_sh_gml`) rather than routed
  around - the real host is LBV.SH's own ``dienste.gdi-sh.de``
  deployment, licence ``CC BY 4.0``, confirmed directly on Schleswig-
  Holstein's own open-data portal (``opendata.schleswig-holstein.de``),
  not just the aggregator ``govdata.de``, which had lost the field
  entirely. Geometry is real ``gml:MultiCurve``/``curveMember``/
  ``LineString`` in the service's own stated native EPSG:25832
  (ETRS89/UTM32N) - reprojected client-side via
  :mod:`streetworks.common._utm32n`, the same standard (not
  country-specific) transform already verified for Denmark. **Every real
  MultiCurve wraps exactly one curveMember** (1,114/1,116 real features
  carry one; the other 2 carry none at all - none has ever carried more
  than one), so only the first is read, unwrapped to a plain
  ``LineString``. **One real combined start/end field, not two separate
  ones** - ``Dauer_der_Bauphase`` states e.g. ``"2026-08-03 23:00:00 bis
  2026-09-11 22:59:00"`` (German "bis" = "until") - split client-side
  into synthetic ``_start_iso``/``_end_iso`` properties (see
  :func:`_split_dauer_der_bauphase`) so :func:`streetworks.common.from_ogc_features`
  can read them like any other state's real separate fields, with the
  original field left untouched for raw fidelity. Real road-class
  prefixes span ``B``/``L``/``K`` (Bundesstraße/Landesstraße/Kreisstraße)
  and a bare ``"G"`` (Gemeindestraße/municipal - **466/1,116 real
  records, the single largest group** - a real but low-information
  value, since the field states only the class letter, not an actual
  road name/number, for these rows) - genuinely comprehensive, reaching
  down to municipal roads by classification, unlike Baden-Württemberg's
  interurban-only scope.

  **This same WFS deployment also carries Niedersachsen and
  Mecklenburg-Vorpommern feature types - found, checked, deliberately not
  built.** ``Baustellen_Niedersachsen`` (142 real features) and
  ``Baustellen_MV`` (77 real features) are both genuinely reachable,
  unauthenticated, off the identical endpoint. Neither has its own
  confirmed open licence, though: Niedersachsen's own real AlD
  (Arbeitsstellen längerer Dauer) dataset traces to a Mobilithek
  marketplace "offer" URL with no stated licence and no separate open
  republish found on any Niedersachsen state portal - the same gated-at-
  origin shape already parked for NRW's own roadworks route elsewhere in
  this SDK; reachability via a neighbouring state's operational mirror
  doesn't establish a licence the origin state itself hasn't granted.
  Mecklenburg-Vorpommern's inclusion here doesn't resolve its own
  pre-existing parking reason below either, for the same reason. **Not
  routed around** - Schleswig-Holstein's own real, separately-confirmed
  CC BY 4.0 licence covers only its own state's layer.

**Parked, not built:**

- **Mecklenburg-Vorpommern** - confirmed live GML-only on its own
  dedicated WFS (``application/geo+json`` explicitly rejected with an
  ``InvalidParameterValue`` exception) and its licence is only vaguely
  stated ("Urheberrecht", no specific Datenlizenz Deutschland citation
  unlike Hamburg/Brandenburg/Saxony's explicit CC BY/dl-de/by-2-0). Two
  independent reasons to park, not one - also reachable (same two
  problems, effectively) via Schleswig-Holstein's shared WFS, see above.
- **Niedersachsen** - reachable, unauthenticated, via Schleswig-
  Holstein's own shared WFS (142 real features) - but its own real AlD
  dataset traces to a Mobilithek marketplace offer with no stated
  licence and no independent open republish found on any Niedersachsen
  state portal. The same gated-at-origin shape already parked for NRW;
  see above for the full reasoning.
- **Saxony-Anhalt** - confirmed live GML-only (tested
  ``OUTPUTFORMAT=application/json`` directly against the real WFS; it
  raises an ``msPostGISLayer`` exception - no JSON output exists) *and*
  its ``GetCapabilities`` states ``AccessConstraints: "This service is
  for non-commercial use only."`` - an explicit restriction, not merely
  an unconfirmed licence, and one that conflicts with this SDK's own MIT
  licence (usable commercially by anyone downstream). Worth flagging for
  whoever revisits this: the state's own web page separately describes
  the service as "free of charge," which reads as open but isn't the
  same claim as a commercial-use permission - the two aren't
  contradictory once you notice "free" is about cost, not rights, but
  it's an easy trap for a future reader to fall into. GML-only is also
  unresolved and would need addressing on its own even if the licence
  question were settled.
- **NRW** - publishes road *network* geodata (sections, nodes, lanes,
  bridges, count sites), not roadworks - a gazetteer source, not this
  cluster's concern. NRW's actual roadworks route is MOBIDROM/Mobilithek,
  the gated DATEX path already parked elsewhere in this SDK. Some cities
  (e.g. Aachen) publish their own municipal Baustellen WFS - a different,
  unaddressed cluster, out of scope here.
- **Bavaria** - BAYSIS publishes WMS/WFS under CC BY 4.0, but its themes
  are network, inventory, structures, traffic counts, expansion plans and
  diversion routes - **no Baustellen (roadworks) layer at all**. Bavarian
  roadworks route to Bayerninfo, then to Mobilithek and, in border
  regions only, into Saxony's own system.

The states that ship publish under **Creative Commons Attribution 4.0**
(Saxony) or **Datenlizenz Deutschland - Namensnennung - Version 2.0**
(dl-de/by-2-0; Hamburg, Brandenburg) - both confirmed directly from each
service's own ``GetCapabilities``/catalogue metadata, free reuse,
redistribution, and commercial exploitation permitted with attribution.
Exact attribution text is on each :class:`StateFieldMap` entry below.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

import httpx

from .client import OGCFeaturesClient

__all__ = ["DateField", "StateFieldMap", "FIELD_MAPS", "GermanRoadworksClient"]

JSON = dict[str, Any]

#: Germany's real bounds, with a small margin - used to sanity-check that a
#: state's WFS genuinely returned lon/lat (GeoJSON order), not lat/lon (the
#: WFS 1.3.0/2.0 EPSG:4326 axis order some servers hand back regardless of
#: the requested output format). See the module-level bounds check the
#: tests run against every fixture, and run again yourself against any new
#: state's first live fetch before trusting it.
GERMANY_LON_RANGE = (5.6, 15.3)
GERMANY_LAT_RANGE = (47.0, 55.3)

#: Saxony's real UTM33N (EPSG:25833) bounds, with a small margin - verified
#: against the real 1,531-feature closures feed (easting 281,960-500,138,
#: northing 5,566,743-5,721,829), not guessed. The lon/lat bounds above
#: don't apply to Saxony - these are its equivalent sanity guard.
SAXONY_EASTING_RANGE = (270_000, 510_000)
SAXONY_NORTHING_RANGE = (5_555_000, 5_735_000)


@dataclass(frozen=True)
class DateField:
    """One date-bearing property: which field, and which format it's in.
    Both formats seen live are date-only (no time component) - represented
    as midnight Europe/Berlin, not naive, so every datetime in this SDK
    stays comparable."""

    field: str
    #: "iso" = YYYY-MM-DD, "de" = DD.MM.YYYY, "iso_datetime" = a full ISO
    #: 8601 datetime with UTC offset (Baden-Württemberg's real
    #: starttime/endtime - the one state in this cluster with a genuine
    #: time-of-day component, not just a date).
    format: Literal["iso", "de", "iso_datetime"] = "iso"


@dataclass(frozen=True)
class StateFieldMap:
    """Declarative mapping from one German state's WFS feature properties
    onto the canonical concepts :func:`streetworks.common.from_ogc_features`
    needs. Everything not mapped here still survives - the whole feature is
    kept on ``WorksSite.raw``, per the project's "canonicalise the shared,
    preserve the specific" rule.

    ``administrative_area`` for every feature this map produces is
    ``state`` - **endpoint provenance, not a record field**. There is no
    ``bundesland`` property on these features; the state is known because
    this map is bound to one state's own endpoint, the same mechanism by
    which National Highways' DATEX adapter states
    ``administrative_area="National Highways"`` explicitly rather than
    reading it off a field. Different from Spain's ``provinces()``, which
    reads a real per-record field - don't go looking for one here.

    ``crs`` is almost always ``"EPSG:4326"`` - Saxony is the one
    exception (``"EPSG:25833"``, UTM33N), since no WGS84 source exists
    for it at all. :func:`streetworks.common.from_ogc_features` reads
    this to decide whether to flip GeoJSON's native ``(lon, lat)`` to
    this SDK's ``(lat, lon)`` convention (only for EPSG:4326) or carry
    coordinates through unchanged (everything else, matching how British
    National Grid providers elsewhere in this SDK are handled) - see that
    module's docstring.

    ``access_mode`` picks how :class:`GermanRoadworksClient` fetches this
    state: ``"wfs"`` (the default - a WFS ``GetFeature`` request),
    ``"zipped_geojson"`` (a direct-download ZIP archive containing a
    GeoJSON file - Saxony's only option, since it has no queryable
    service at all), ``"direct_geojson"`` (a plain unauthenticated GET
    that already returns a full GeoJSON ``FeatureCollection`` - no query
    params, no archive; Baden-Württemberg's own MobiData BW platform)
    or ``"gml_wfs"`` (a GML-only WFS, parsed client-side via
    :func:`_fetch_lbv_sh_gml` - Schleswig-Holstein's own real shape,
    genuinely GML-only, confirmed live to reject
    ``application/geo+json`` outright). ``zip_member`` is the filename
    inside the archive to read, required only for ``"zipped_geojson"``.
    """

    state: str
    base_url: str
    type_name: str = ""
    access_mode: Literal["wfs", "zipped_geojson", "direct_geojson", "gml_wfs"] = "wfs"
    zip_member: str | None = None
    crs: str = "EPSG:4326"
    title_field: str | None = None
    promoter_field: str | None = None
    start: DateField | None = None
    end: DateField | None = None
    road_field: str | None = None
    status_field: str | None = None
    #: Overrides the default reference resolution (a real `ID` property,
    #: then the GeoJSON feature's own `id`) - needed for Baden-Württemberg,
    #: whose real per-feature identifier lives in a lowercase `id`
    #: *property* (`"1487640-...-sperrung.001"`), a third real shape none
    #: of Hamburg/Brandenburg/Saxony's own identifiers use. See
    #: :func:`streetworks.common.from_ogc_features._to_works`.
    id_field: str | None = None
    licence: str = ""
    attribution: str = ""
    version: str = "2.0.0"


HAMBURG = StateFieldMap(
    state="Hamburg",
    base_url="https://geodienste.hamburg.de/hh_wfs_baustellen",
    type_name="de.hh.up:baustelle",
    title_field="titel",
    promoter_field="organisation",
    start=DateField("baubeginn", "de"),
    end=DateField("bauende", "de"),
    road_field=None,  # genuinely absent - see module docstring
    status_field=None,  # six independent booleans instead - see module docstring
    licence="Datenlizenz Deutschland - Namensnennung - Version 2.0 (dl-de/by-2-0)",
    attribution="Freie und Hansestadt Hamburg, Behörde für Verkehr und Mobilitätswende",
)

BRANDENBURG = StateFieldMap(
    state="Brandenburg",
    base_url="https://isk.geobasis-bb.de/ows/baustelleninfo_wfs",
    type_name="app:baustelleninfo",
    title_field="Art",
    promoter_field=None,
    start=DateField("Baustellen_Beginn", "iso"),
    end=DateField("Baustellen_Ende", "iso"),
    road_field="Straßenummner",  # sic - the real field name, not "Straßennummer"
    status_field="Status_Fahrstreifen",
    licence="Datenlizenz Deutschland - Namensnennung - Version 2.0 (dl-de/by-2-0)",
    attribution="© Landesbetrieb Straßenwesen Brandenburg, dl-de/by-2-0, (Daten geändert)",
)

SAXONY = StateFieldMap(
    state="Sachsen",
    base_url="http://www.list.smwa.sachsen.de/gdi/download/baustelleninfo/"
    "Baustelleninfo_Sachsen_geojson.zip",
    access_mode="zipped_geojson",
    zip_member="Baustelleninfo_Sperrungen_Sachsen.geojson",
    crs="EPSG:25833",  # UTM33N - no WGS84 source exists, see module docstring
    title_field="Sperrung_Art_Klartext",
    promoter_field="Behörde",
    start=DateField("Sperrung_von", "de"),
    end=DateField("Sperrung_bis", "de"),
    road_field="Strasse",
    status_field="Sperrung_Typ_Klartext",
    licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
    attribution="Baustelleninformationssystem Sachsen",
)

BADEN_WUERTTEMBERG = StateFieldMap(
    state="Baden-Württemberg",
    base_url="https://api.mobidata-bw.de/datasets/traffic/roadworks/roadworks_geojson.json",
    access_mode="direct_geojson",
    title_field="description",
    # "reference" is a static "MobiData BW" platform label, not a real promoter
    promoter_field=None,
    start=DateField("starttime", "iso_datetime"),
    end=DateField("endtime", "iso_datetime"),
    road_field="street",
    status_field="type",  # real, clean binary: "ROAD_CLOSED" (505) / "CONSTRUCTION" (423)
    id_field="id",  # a real lowercase "id" property - see StateFieldMap.id_field
    licence="Datenlizenz Deutschland - Namensnennung - Version 2.0 (dl-de/by-2-0)",
    attribution="MobiData BW, Verkehrsministerium Baden-Württemberg, dl-de/by-2-0",
)

#: LBV.SH's own real ArcGIS-backed WFS namespace and feature-element
#: namespaces - confirmed live off its own GetCapabilities/GetFeature
#: responses, not guessed.
_LBV_SH_NS = "http://watkipw023.dpaorinp.de:6080/arcgis/admin/services/Baustelleninformationen/MapServer/WFSServer"
_WFS_NS = "http://www.opengis.net/wfs/2.0"
_GML_NS = "http://www.opengis.net/gml/3.2"

_BERLIN_TZ = ZoneInfo("Europe/Berlin")

#: Baustellen_SH's own real "Dauer_der_Bauphase" field states one
#: combined start/end string ("2026-08-03 23:00:00 bis 2026-09-11
#: 22:59:00"), not two separate fields like every other state in this
#: cluster - split here into synthetic `_start_iso`/`_end_iso`
#: properties so :class:`StateFieldMap` can read them the same way as
#: any other state's real separate fields. The original field is left
#: untouched in the parsed properties dict, for raw fidelity.
_DAUER_SEPARATOR = " bis "


def _split_dauer_der_bauphase(properties: JSON) -> None:
    value = properties.get("Dauer_der_Bauphase")
    if not value or _DAUER_SEPARATOR not in value:
        return
    start_text, end_text = value.split(_DAUER_SEPARATOR, 1)
    for key, text in (("_start_iso", start_text), ("_end_iso", end_text)):
        try:
            naive = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        properties[key] = naive.replace(tzinfo=_BERLIN_TZ).isoformat()


def _gml_point_to_geojson(point: ET.Element) -> JSON | None:
    from ..common._utm32n import utm32n_to_wgs84  # deferred: see module docstring

    pos = point.find(f"{{{_GML_NS}}}pos")
    if pos is None or not pos.text:
        return None
    easting, northing = (float(v) for v in pos.text.split())
    lon, lat = utm32n_to_wgs84(easting, northing)
    return {"type": "Point", "coordinates": [lon, lat]}


def _gml_multicurve_to_geojson(multicurve: ET.Element) -> JSON | None:
    from ..common._utm32n import utm32n_to_wgs84  # deferred: see module docstring

    # Confirmed live (2026-08-20): every real Baustellen_SH MultiCurve
    # wraps exactly one curveMember/LineString (1,114/1,116 real
    # features carry one, the other 2 carry none at all - none has ever
    # carried more than one). Only the first curveMember is read; a
    # genuine second one would be silently dropped, but none has been
    # observed - see module docstring.
    pos_list = multicurve.find(
        f"{{{_GML_NS}}}curveMember/{{{_GML_NS}}}LineString/{{{_GML_NS}}}posList"
    )
    if pos_list is None or not pos_list.text:
        return None
    values = [float(v) for v in pos_list.text.split()]
    pairs = list(zip(values[0::2], values[1::2], strict=True))
    coordinates = [list(utm32n_to_wgs84(easting, northing)) for easting, northing in pairs]
    if not coordinates:
        return None
    return {"type": "LineString", "coordinates": coordinates}


def _gml_geometry_to_geojson(shape: ET.Element | None) -> JSON | None:
    if shape is None:
        return None
    point = shape.find(f"{{{_GML_NS}}}Point")
    if point is not None:
        return _gml_point_to_geojson(point)
    multicurve = shape.find(f"{{{_GML_NS}}}MultiCurve")
    if multicurve is not None:
        return _gml_multicurve_to_geojson(multicurve)
    return None


def _fetch_lbv_sh_gml(ogc: OGCFeaturesClient, base_url: str, type_name: str) -> list[JSON]:
    """Fetch and parse one real feature type off LBV.SH's shared
    ArcGIS-backed WFS (``dienste.gdi-sh.de``) - genuinely GML-only,
    confirmed live to reject ``OUTPUTFORMAT=application/json`` outright
    (a real ``InvalidParameterValue`` exception, the same shape
    Mecklenburg-Vorpommern's and Saxony-Anhalt's own dedicated WFS
    already rule out for :meth:`OGCFeaturesClient.get_wfs_features`).
    Returns GeoJSON-shaped ``Feature`` dicts, geometry already
    reprojected client-side from the service's real native EPSG:25832
    (ETRS89/UTM32N) to WGS84 via :mod:`streetworks.common._utm32n` - the
    same closed-form transform already verified for Denmark, a standard
    UTM zone, not a country-specific one.

    1,116 real ``Baustellen_SH`` features confirmed to fit one
    un-paginated request (``COUNT=2000``, live-confirmed
    ``numberMatched == numberReturned``) at investigation time - revisit
    with real WFS 2.0 paging (``STARTINDEX``/``COUNT``) if the feed ever
    grows past that."""
    xml_bytes = ogc.get_xml(
        base_url,
        params={
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAMES": type_name,
            "COUNT": "2000",
        },
    )
    return _parse_lbv_sh_gml(xml_bytes, type_name)


def _parse_lbv_sh_gml(xml_bytes: bytes, type_name: str) -> list[JSON]:
    """The pure parsing half of :func:`_fetch_lbv_sh_gml`, split out so
    it can run against a real captured fixture with no HTTP involved -
    see ``tests/test_common_ogc_features.py``."""
    root = ET.fromstring(xml_bytes)  # noqa: S314 - a trusted government WFS endpoint
    local_type = type_name.split(":", 1)[-1]
    features: list[JSON] = []
    for member in root.findall(f"{{{_WFS_NS}}}member"):
        element = member.find(f"{{{_LBV_SH_NS}}}{local_type}")
        if element is None:
            continue
        properties: JSON = {}
        geometry: JSON | None = None
        for child in element:
            local_name = child.tag.split("}", 1)[-1]
            if local_name == "SHAPE":
                geometry = _gml_geometry_to_geojson(child)
            else:
                properties[local_name] = child.text
        _split_dauer_der_bauphase(properties)
        features.append(
            {
                "type": "Feature",
                "id": element.get(f"{{{_GML_NS}}}id"),
                "properties": properties,
                "geometry": geometry,
            }
        )
    return features


SCHLESWIG_HOLSTEIN = StateFieldMap(
    state="Schleswig-Holstein",
    base_url="https://dienste.gdi-sh.de/WFS_SH_Baustelleninformationen",
    type_name="Baustelleninformationen:Baustellen_SH",
    access_mode="gml_wfs",
    title_field="Art_der_Maßnahme",
    promoter_field=None,
    # Baustellen_SH states one real combined field, not separate
    # start/end - _fetch_lbv_sh_gml splits it into these two synthetic
    # properties before this map ever sees it. See module docstring.
    start=DateField("_start_iso", "iso_datetime"),
    end=DateField("_end_iso", "iso_datetime"),
    road_field="Straßenname",
    status_field="Verkehrseinschränkung",
    licence="Creative Commons Namensnennung - 4.0 International (CC BY 4.0)",
    attribution="Landesbetrieb Straßenbau und Verkehr Schleswig-Holstein (LBV.SH)",
)

FIELD_MAPS: dict[str, StateFieldMap] = {
    "Hamburg": HAMBURG,
    "Brandenburg": BRANDENBURG,
    "Sachsen": SAXONY,
    "Baden-Württemberg": BADEN_WUERTTEMBERG,
    "Schleswig-Holstein": SCHLESWIG_HOLSTEIN,
}


class GermanRoadworksClient:
    """Fetch German state roadworks via the field maps in :data:`FIELD_MAPS`.
    No credentials required.

    >>> from streetworks.ogc.germany import GermanRoadworksClient
    >>> from streetworks.common import from_ogc_features
    >>> with GermanRoadworksClient() as germany:
    ...     features = germany.fetch("Hamburg")
    >>> works = from_ogc_features(features, HAMBURG)
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def fetch(self, state: str) -> list[JSON]:
        """Fetch every current feature for ``state`` (a key of
        :data:`FIELD_MAPS`, e.g. ``"Hamburg"``) - the raw GeoJSON Feature
        dicts, unconverted. Pass these straight to
        :func:`streetworks.common.from_ogc_features` with the same state's
        :class:`StateFieldMap`."""
        field_map = FIELD_MAPS[state]
        if field_map.access_mode == "zipped_geojson":
            assert field_map.zip_member is not None  # required for this access mode
            payload = self._ogc.get_zipped_geojson(field_map.base_url, member=field_map.zip_member)
            return list(payload.get("features") or ())
        if field_map.access_mode == "direct_geojson":
            payload = self._ogc.get(field_map.base_url)
            return list(payload.get("features") or ())
        if field_map.access_mode == "gml_wfs":
            return _fetch_lbv_sh_gml(self._ogc, field_map.base_url, field_map.type_name)
        payload = self._ogc.get_wfs_features(
            field_map.base_url,
            type_name=field_map.type_name,
            version=field_map.version,
            srs_name=field_map.crs,
        )
        return list(payload.get("features") or ())

    def iter_all(self, states: list[str] | None = None) -> Iterator[tuple[str, JSON]]:
        """Yield ``(state, feature)`` for every feature across ``states``
        (default: every state in :data:`FIELD_MAPS`)."""
        for state in states if states is not None else FIELD_MAPS:
            for feature in self.fetch(state):
                yield state, feature

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> GermanRoadworksClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
