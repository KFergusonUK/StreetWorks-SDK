"""Consell de Mallorca - island road incidents/roadworks, via IDEmallorca's
GeoServer WFS.

The *insular* layer beneath DGT: DGT's national DATEX feed only carries
roads it owns, not Consell-managed island roads (confirmed live - an
Alcúdia-area query against DGT returned ~5 works island-wide). This is
genuinely additive coverage, not a duplicate - see
``docs/idemallorca-investigation.md`` for the full recon this build is
based on.

**Only HTTP works, not HTTPS - confirmed live, contrary to the original
brief's assumed base URL.** ``https://www.conselldemallorca.info/...``
fails to connect at all; every real link on the Consell's own site
(``/geoserveis``) also uses plain ``http://``. :data:`BASE_URL` reflects
what's actually reachable, not what looked more likely.

**Two layers, joined by a shared ``codi`` (int) - confirmed live, not
assumed 1:1.** ``incidencies_icon`` is the spine: one point per incident,
carrying every real attribute (type, dates, description, road, direction).
``incidencies_tram`` supplies the affected road segment(s) as a real
``MultiLineString`` (one real record, ``codi=19528``, genuinely has 2
parts - not always a single-part wrapper) - geometry only, no other
attributes (``codi``/``color``/``shape``, confirmed via
``DescribeFeatureType``). The join is **not total**: 16/17 real icons in
one live pull had a matching tram record; one (``codi=19612``, a lane
closure on Ma-13) is icon-only - handled honestly by
:func:`streetworks.common.from_mallorca`, never fabricating a line for it.

**The format gotcha - a real, masked failure, not a documentation gap.**
This GeoServer instance genuinely rejects
:attr:`~streetworks.ogc.client.OGCFeaturesClient.get_wfs_features`'s own
default ``output_format="application/geo+json"`` - but not with an error
status. It returns **HTTP 200** wrapping an XML
``InvalidParameterValue`` exception body
(``"Failed to find response for output format application/geo json"``),
which is why every call in this module passes
``output_format="application/json"`` explicitly rather than relying on
the client's default - **do not "fix" this back to the SDK default**, it
will silently break this source, not the client. :func:`_validate_feature_collection`
additionally checks the decoded payload is really a ``FeatureCollection``
before returning it, as a second, explicit guard against exactly this
kind of masked failure - belt and braces, since a bad ``output_format``
here fails quietly rather than loudly.

**CRS: ETRS89 / UTM zone 31N, EPSG:25831 - confirmed live, not
reprojected.** Stated explicitly in the WFS capabilities
(``<DefaultCRS>urn:ogc:def:crs:EPSG::25831</DefaultCRS>``) and confirmed
from real coordinate magnitudes (``[529082.6, 4380729.7]`` - the right
order of magnitude for Mallorca in UTM31N; genuine WGS84 values would
read ~3.3/~39.6). The server *can* reproject to WGS84 server-side on
request (tested live, genuinely correct) - not used here, per this SDK's
standing CRS policy (native CRS, labelled, never silently reprojected -
the same choice already made for Belgium's Lambert 72 and Lithuania's
LKS-94).

**Discriminator: ``tipoinc``, clean and explicit - not the Cyprus
free-text problem.** Three real values seen live (one snapshot, 17
incidents): ``"Obres"`` (works, 6), ``"Manteniment"`` (maintenance, 10),
``"Altres"`` (other, 1). :data:`ROADWORKS_TIPOINC` covers the first two
only - the one real ``Altres`` record checked
(``observacions: "Restriccions de la DGT, cada dia de 10 a 22h"``) reads
as a DGT-imposed restriction on a Consell road, not Consell's own
works/maintenance programme, so it's deliberately excluded rather than
assumed roadworks.

**Licence: unconfirmed.** Checked the WFS capabilities
(``Fees: NONE``/``AccessConstraints: NONE`` - GeoServer's own
unconfigured defaults, not a deliberate statement), the IDEmallorca
geoportal, and the Consell's general legal notice - no explicit
reuse/licence text found anywhere. Per the Autobahn GmbH/Belgium/Bulgaria
precedent, the test fixture is synthetic (real confirmed shape, invented
values), and this stays flagged, not assumed open.

**Scope: Mallorca only, not a Balearic cluster.** The investigation
checked Menorca (has its own separate IDE, ``ide.cime.es`` - no incidents
layer located) and Eivissa (a differently-shaped open-data portal, broken
TLS certificate, nothing roadworks-related found on a first pass) - the
pattern doesn't uniformly generalise, so this ships as a single provider,
not the head of a committed cluster.
"""

from __future__ import annotations

from typing import Any

import httpx

from .client import OGCFeaturesClient

__all__ = [
    "BASE_URL",
    "ICON_TYPE_NAME",
    "TRAM_TYPE_NAME",
    "CRS",
    "ROADWORKS_TIPOINC",
    "MallorcaClient",
]

JSON = dict[str, Any]

#: Plain HTTP only - HTTPS doesn't connect at all, confirmed live. See
#: module docstring.
BASE_URL = "http://www.conselldemallorca.info/geoserver/SIT/wfs"

ICON_TYPE_NAME = "SIT:incidencies_icon"
TRAM_TYPE_NAME = "SIT:incidencies_tram"

#: ETRS89 / UTM zone 31N - the source's real native CRS. See module
#: docstring for why this is requested explicitly rather than the
#: client's own EPSG:4326 default, and why it isn't reprojected.
CRS = "EPSG:25831"

#: ``tipoinc`` values that count as roadworks. Deliberately excludes
#: ``"Altres"`` - see module docstring.
ROADWORKS_TIPOINC = frozenset({"Obres", "Manteniment"})


def _validate_feature_collection(payload: JSON, *, layer: str) -> None:
    if payload.get("type") != "FeatureCollection":
        raise ValueError(
            f"Mallorca: {layer} did not return a GeoJSON FeatureCollection "
            f"(got {payload.get('type')!r}) - this GeoServer masks a bad "
            f"output_format as HTTP 200 with an XML error body, see module "
            f"docstring"
        )


class MallorcaClient:
    """Fetch Consell de Mallorca road incidents (IDEmallorca GeoServer
    WFS). No credentials required.

    >>> from streetworks.ogc.mallorca import MallorcaClient
    >>> from streetworks.common import from_mallorca
    >>> with MallorcaClient() as mallorca:
    ...     icons = mallorca.fetch_roadworks_icons()
    ...     trams = mallorca.fetch_trams()
    >>> works = from_mallorca(icons, trams)
    """

    def __init__(self, *, base_url: str = BASE_URL, client: httpx.Client | None = None) -> None:
        self.base_url = base_url
        self._ogc = OGCFeaturesClient(client=client)

    def fetch_icons(self) -> list[JSON]:
        """Every real incident (all ``tipoinc`` values, not filtered) from
        ``incidencies_icon`` - the raw GeoJSON Feature dicts."""
        payload = self._ogc.get_wfs_features(
            self.base_url,
            type_name=ICON_TYPE_NAME,
            # Not the client's own "application/geo+json" default - this
            # server masks that as HTTP 200 + an XML error body. See
            # module docstring. Do not remove this override.
            output_format="application/json",
            srs_name=CRS,
        )
        _validate_feature_collection(payload, layer="incidencies_icon")
        return list(payload.get("features") or ())

    def fetch_roadworks_icons(self) -> list[JSON]:
        """Like :meth:`fetch_icons`, filtered to ``tipoinc`` in
        :data:`ROADWORKS_TIPOINC` (``"Obres"``/``"Manteniment"`` -
        excludes ``"Altres"``, see module docstring)."""
        return [
            feature
            for feature in self.fetch_icons()
            if (feature.get("properties") or {}).get("tipoinc") in ROADWORKS_TIPOINC
        ]

    def fetch_trams(self) -> list[JSON]:
        """Every affected-segment line from ``incidencies_tram`` - the raw
        GeoJSON Feature dicts, each carrying a ``codi`` that joins back to
        an icon's own ``codi`` (not total - see module docstring)."""
        payload = self._ogc.get_wfs_features(
            self.base_url,
            type_name=TRAM_TYPE_NAME,
            output_format="application/json",  # see fetch_icons
            srs_name=CRS,
        )
        _validate_feature_collection(payload, layer="incidencies_tram")
        return list(payload.get("features") or ())

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> MallorcaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
