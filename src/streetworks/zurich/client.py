"""Stadt Zürich: "Aktuelle Tiefbauprojekte im öffentlichen Grund" -
current civil-engineering projects on public ground, over the city's own
GeoServer WFS. This SDK's second Swiss coverage, alongside the separate,
non-overlapping cantonal-road coverage (:mod:`streetworks.canton_zurich`)
- do not dedupe between the two.

.. attention::
   **Confirmed live (2026-08-14)** against a real, unauthenticated pull
   (140 real feature rows at time of writing).

**Found via opendata.swiss's own CKAN catalogue** (``aktuelle-
tiefbauprojekte-im-offentlichen-grund``, maintained by the City of
Zürich) - the real WFS endpoint is
``https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Aktuelle_Tiefbauprojekte_im_oeffentlichen_Grund``,
one real layer, :data:`TYPE_NAME`.

**The format gotcha - a real masked-failure risk, the same shape
Mallorca's own module docstring already documents.** This GeoServer
instance's real ``GetCapabilities`` lists ``application/vnd.geo+json``
as its only JSON output format - plain ``application/json`` (the shared
client's own default) is **not** in that list. Every call here passes
``output_format="application/vnd.geo+json"`` explicitly rather than
relying on the client's default - do not "fix" this back to the SDK
default, it will silently break this source.

**A second real quirk: this server only accepts WFS 1.1.0's singular
``TYPENAME`` parameter, not 2.0.0's plural ``TYPENAMES`` - confirmed
live** (``VERSION=1.1.0&TYPENAMES=...`` genuinely 500s; ``VERSION=1.1.0&
TYPENAME=...`` succeeds; the server's own capabilities list only
``1.0.0``/``1.1.0`` as supported versions, never ``2.0.0``, at all).
Rather than bypass the shared client's own ``TYPENAMES``-only request
builder, :meth:`ZurichClient.iter_roadworks` passes ``version="1.1.0"``
and adds the real working ``TYPENAME`` via ``extra_params`` - confirmed
live that a request carrying both the (here, invalid) plural and the
valid singular parameter together still succeeds, since the server
simply uses whichever one it recognises.

**CRS: genuinely WGS84, confirmed empirically despite an empty
`DefaultSRS` capabilities tag - a real metadata gap, not a parsing
miss.** The WFS's own ``FeatureType`` capabilities entry states
``<DefaultSRS></DefaultSRS>`` (blank) and lists only
``<OtherSRS>EPSG:4326</OtherSRS>`` as an alternative. A plain
``GetFeature`` request with no ``srsName`` returned coordinates
(``[8.57, 47.40]``) that exactly match that same ``FeatureType``'s own
stated ``WGS84BoundingBox`` (``8.462-8.605°E``, ``47.326-47.432°N``) -
confirming the real default output genuinely is WGS84 even though the
capabilities document never says so explicitly. :data:`CRS` is requested
explicitly as ``EPSG:4326`` here regardless, per this SDK's standing
policy of never relying on an ambiguous server default.

**A real, confirmed unique identifier - unlike the canton's dataset.**
``baunr`` (project number, e.g. ``"18071"``) is 140/140 distinct across
the full live pull - used as ``reference`` by
:mod:`streetworks.common.from_zurich`.

**``kategorie`` is a constant `"Grössere Baustelle"`** ("larger
construction site") across all 140 real rows - this dataset is already
curated to significant/major projects, not every minor street closure.
Stated honestly as scoped that way in the converter's own ``works_type``
value, not implied to be an exhaustive citywide feed.

**``projektleiter``/``projektleiter_email``/``tel`` are a named
individual (the project leader), not an organisation** - the same
treatment as the canton's own ``ansprechperson``: preserved on
``WorksSite.raw`` only, never promoted to ``Works.promoter``.

**Licence: the same opendata.swiss "Open use" tier as the canton
dataset, confirmed live** via this resource's own ``rights`` field
(``https://opendata.swiss/terms-of-use#terms_open``) - usable for both
non-commercial and commercial purposes, no attribution required.

**No credentials required** - every claim above came from a fully
unauthenticated GetFeature request.
"""

from __future__ import annotations

from typing import Any

import httpx

from ..ogc.client import OGCFeaturesClient

__all__ = ["BASE_URL", "TYPE_NAME", "CRS", "ZurichClient"]

JSON = dict[str, Any]

#: Found via opendata.swiss's own CKAN catalogue entry
#: (aktuelle-tiefbauprojekte-im-offentlichen-grund), confirmed live. See
#: module docstring.
BASE_URL = (
    "https://www.ogd.stadt-zuerich.ch/wfs/geoportal/"
    "Aktuelle_Tiefbauprojekte_im_oeffentlichen_Grund"
)

TYPE_NAME = "aer_baustellen_a"

#: Genuinely WGS84 - confirmed empirically, see module docstring for why
#: the capabilities document's own DefaultSRS tag can't be trusted here.
CRS = "EPSG:4326"

#: This GeoServer's only real JSON output format - not the shared
#: client's own "application/geo+json" default. See module docstring.
_OUTPUT_FORMAT = "application/vnd.geo+json"


class ZurichClient:
    """Fetch Stadt Zürich's real "Aktuelle Tiefbauprojekte im
    öffentlichen Grund" (current public-ground civil-engineering
    projects) from the city's own GeoServer WFS. No credentials
    required.

    >>> from streetworks.zurich import ZurichClient
    >>> from streetworks.common import from_zurich
    >>> with ZurichClient() as zurich:  # doctest: +SKIP
    ...     works = from_zurich(zurich.iter_roadworks())
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def iter_roadworks(self) -> list[JSON]:
        """Every real project feature - raw, unfiltered. This dataset
        is already curated to major projects, see module docstring."""
        payload = self._ogc.get_wfs_features(
            BASE_URL,
            type_name=TYPE_NAME,
            version="1.1.0",
            srs_name=CRS,
            output_format=_OUTPUT_FORMAT,
            extra_params={"TYPENAME": TYPE_NAME},
        )
        return list(payload.get("features") or ())

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> ZurichClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
