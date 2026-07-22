"""Canonical cross-provider types for works data (streetworks 0.5.0+) and
gazetteer data (streetworks 0.8.0+).

Converters (``from_<provider>``) sit alongside each provider's native,
full-fidelity interface - they never replace it. See :mod:`.models` for the
works type design and the record-identity rules that decide what maps
where, and :mod:`.gazetteer` for the `Street`/`Segment`/`Address` design.
"""

from .from_autobahn import from_autobahn
from .from_bag import from_bag
from .from_ban import from_ban
from .from_bdtopo import from_bdtopo
from .from_datavia import from_datavia
from .from_datex2 import from_datex2
from .from_jersey import from_jersey
from .from_kartverket import from_kartverket
from .from_nvdb import from_nvdb
from .from_nwb import from_nwb
from .from_ogc_features import from_ogc_features
from .from_openusrn import from_openusrn
from .from_srwr import from_srwr
from .from_streetmanager import from_streetmanager
from .from_tigerweb import from_tigerweb
from .from_trafficwales import from_trafficwales
from .from_trafficwatchni import from_trafficwatchni
from .from_wzdx import from_wzdx
from .gazetteer import (
    Address,
    AddressRange,
    GeometryGrade,
    Name,
    Segment,
    Street,
    StreetType,
)
from .models import (
    Coordinate,
    DateConfidence,
    Identifier,
    Notice,
    Point2D,
    Point3D,
    SourceGrade,
    Works,
    WorksPlanning,
    WorksSite,
)

__all__ = [
    "SourceGrade",
    "DateConfidence",
    "Point2D",
    "Point3D",
    "Coordinate",
    "Identifier",
    "Notice",
    "WorksSite",
    "WorksPlanning",
    "Works",
    "GeometryGrade",
    "Name",
    "StreetType",
    "AddressRange",
    "Street",
    "Segment",
    "Address",
    "from_srwr",
    "from_trafficwatchni",
    "from_trafficwales",
    "from_datex2",
    "from_streetmanager",
    "from_wzdx",
    "from_autobahn",
    "from_ogc_features",
    "from_datavia",
    "from_openusrn",
    "from_bdtopo",
    "from_nvdb",
    "from_nwb",
    "from_ban",
    "from_bag",
    "from_kartverket",
    "from_jersey",
    "from_tigerweb",
]
