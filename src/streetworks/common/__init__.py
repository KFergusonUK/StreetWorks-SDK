"""Canonical cross-provider types for works data (streetworks 0.5.0+).

Converters (``from_<provider>``) sit alongside each provider's native,
full-fidelity interface - they never replace it. See :mod:`.models` for the
type design and the record-identity rules that decide what maps where.
"""

from .from_datex2 import from_datex2
from .from_srwr import from_srwr
from .from_streetmanager import from_streetmanager
from .from_trafficwales import from_trafficwales
from .from_trafficwatchni import from_trafficwatchni
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
]
