"""Canonical cross-provider types for works data (streetworks 0.5.0+).

Converters (``from_<provider>``) sit alongside each provider's native,
full-fidelity interface - they never replace it. See :mod:`.models` for the
type design and the record-identity rules that decide what maps where.
"""

from .from_autobahn import from_autobahn
from .from_datex2 import from_datex2
from .from_ogc_features import from_ogc_features
from .from_srwr import from_srwr
from .from_streetmanager import from_streetmanager
from .from_trafficwales import from_trafficwales
from .from_trafficwatchni import from_trafficwatchni
from .from_wzdx import from_wzdx
from .models import (
    Coordinate,
    DateConfidence,
    Notice,
    SourceGrade,
    Works,
    WorksPlanning,
    WorksSite,
)

__all__ = [
    "SourceGrade",
    "DateConfidence",
    "Coordinate",
    "Notice",
    "WorksSite",
    "WorksPlanning",
    "Works",
    "from_srwr",
    "from_trafficwatchni",
    "from_trafficwales",
    "from_datex2",
    "from_streetmanager",
    "from_wzdx",
    "from_autobahn",
    "from_ogc_features",
]
