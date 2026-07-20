"""France's BD TOPO (IGN) - the transport theme (`troncon_de_route`,
`voie_nommee`) of IGN's national topographic database, and France's
street-geometry counterpart to `streetworks.ban`'s addresses, the third
non-UK street register after `streetworks.nwb`. Native only - no
canonical street type, no `streetworks.common` converter.

**`voie_nommee` (named street) is real, confirmed live, and gives France
a genuine two-level spine** - a named street above, segments
(`troncon_de_route`) below, each carrying a real, stated join to BAN
(`identifiant_voie_ban`, exactly BAN's own compact toponyme-id format,
plus `id_ban_odonyme`, a street-level BAN UUID not otherwise exposed).
See :mod:`streetworks.bdtopo.models` for the full live-verified detail,
including the real over-merge check run on two whole communes (one
mainland, one overseas) and the real left/right structure BD TOPO carries
that neither NWB nor the UK's USRN has.

**Only one access route is built here: the Géoplateforme WFS**
(`data.geopf.fr/wfs/ows`, credential-free, real `CQL_FILTER` support -
see :mod:`streetworks.bdtopo.client`). IGN's bulk per-département
GeoPackage is real and identically licensed, but this investigation found
no automatable, unauthenticated download route for it: the documented
download portal (`geoservices.ign.fr/telechargement`) now redirects to
`cartes.gouv.fr`, a JavaScript single-page app with no static resource
list; `data.gouv.fr`'s own BD TOPO dataset lists 149 resources, none of
them an actual GeoPackage file (only documentation, WMS/WMTS/WFS capability
URLs, and one shapefile catalogue link that itself redirects to the same
SPA); the legacy `wxs.ign.fr` host no longer resolves; and the WFS itself
does not offer GeoPackage as an output format (confirmed live via its own
`GetCapabilities` - only GML, GeoJSON, KML and CSV). A GeoPackage *reader*
(:mod:`streetworks.bdtopo.reader`) is still built, for anyone who obtains
a real file from `cartes.gouv.fr` manually - but it was not verified
against a real downloaded file, only against IGN's own confirmed-live WFS
field/table naming convention, which is documented as generated from the
same data model. That's a reasonable inference, not a confirmed fact -
flagged plainly, not hidden.

CRS: the WFS declares WGS84 (EPSG:4326) on every real response checked,
mainland and overseas alike. IGN's own documentation states the bulk
GeoPackage uses RGF93 / Lambert-93 (EPSG:2154) instead - plausible, but
not independently re-confirmed here (see above). Licence: Licence
Ouverte / Open Licence ETALAB 2.0, confirmed via data.gouv.fr's dataset
metadata - the same licence as `streetworks.ban` and
`streetworks.datex2.bisonfute`.

Not built: **Route 500** (a separate, coarser IGN road product - not a
substitute for BD TOPO), and BD TOPO's other themes (buildings,
hydrography, vegetation, administrative boundaries, ...) - this module
reads the transport theme only, per the design brief's scope.
"""

from .client import WFS_BASE_URL, AsyncBDTopoClient, BDTopoClient
from .models import Troncon, VoieNommee
from .reader import BDTopoDatabase, BDTopoFeature, TableInfo

__all__ = [
    "WFS_BASE_URL",
    "AsyncBDTopoClient",
    "BDTopoClient",
    "BDTopoDatabase",
    "BDTopoFeature",
    "TableInfo",
    "Troncon",
    "VoieNommee",
]
