"""Norway's NVDB (Nasjonal vegdatabank) - the fourth non-UK street register
and the last before the canonical-model design session. Native only - no
canonical street type, no `streetworks.common` converter. The `streets`
counterpart to `streetworks.kartverket`'s `addresses`.

**No credentials required for reads** - confirmed live and confirmed in
NVDB's own API guidelines (see :mod:`streetworks.nvdb.client`). Worth
stating plainly: Norway now has three providers with three different
access stories from two agencies - roadworks
(:mod:`streetworks.datex2.vegvesen`, credential-blocked, this SDK's one
unverified provider), addresses (:mod:`streetworks.kartverket`, open),
and this one, road network geometry (open too). Statens vegvesen
publishes both the roadworks feed and NVDB; only the roadworks one is
gated.

**`veglenkesekvens` (road link sequence) is purely topological - no name
of its own.** Naming and addressing live in a separate object type
(`Adresse`, NVDB type 538), which carries `adressekode` - confirmed live
to be the *same* identifier :mod:`streetworks.kartverket` already models,
a real, stated join to Matrikkelen addresses. And, confirmed live, one
named address can span *multiple* link sequences - Norway's naming layer
and topological layer are not nested the way France's `voie_nommee`/
`troncon_de_route` are (see :mod:`streetworks.bdtopo.models`). Full
detail, including the CRS correction (EPSG:5973, a compound 3D CRS, not
the design brief's plain EPSG:25833 guess) and the third identifier
system (`vegsystemreferanser`, administrative road-numbering), is in
:mod:`streetworks.nvdb.models`'s module docstring.

Licence: NLOD 1.0 (Norsk lisens for offentlige data) - confirmed from the
NVDB API's own documentation, not Elveg/Kartverket's CC BY 4.0 (same
underlying network, different publisher, different licence - see
:mod:`streetworks.nvdb.client`).

**Elveg / NVDB Vegnett Pluss** (Kartverket's own distribution of the same
network, "with address information") is real but SOSI/GML only - noted,
not built, the same treatment as `streetworks.bdtopo`'s unreachable bulk
route. The NVDB Eksport CSV service was evaluated and not built either -
the REST API already paginates and filters by municipality cleanly
enough that a second bulk route would do the same job.
"""

from .client import (
    ADRESSE_TYPE_ID,
    VEGNETT_BASE_URL,
    VEGOBJEKTER_BASE_URL,
    AsyncNVDBClient,
    NVDBClient,
)
from .models import VegAdresse, Veglenke, Veglenkesekvens

__all__ = [
    "ADRESSE_TYPE_ID",
    "VEGNETT_BASE_URL",
    "VEGOBJEKTER_BASE_URL",
    "AsyncNVDBClient",
    "NVDBClient",
    "VegAdresse",
    "Veglenke",
    "Veglenkesekvens",
]
