"""Northern Ireland: DfI Roads Highway Network centreline - this SDK's
own native model. See :mod:`streetworks.dfi_roads.client` for the full
investigation and provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from streetworks.common.models import Coordinate

__all__ = ["RoadSection"]


@dataclass(frozen=True)
class RoadSection:
    """One real DfI Roads "Highway Network" section - a maintained-road
    centreline plus its real classification and adoption status.

    ``adoption_status`` is real and genuinely two-valued
    (``"Adopted"``/``"Unadopted"``, confirmed live: 70,522/1,074 of
    71,596 real sections) - the field the "adoption status filter" the
    module docstring describes is built on.

    ``geometry`` carries the real polyline exactly as stated, in the
    service's own native CRS (Irish Grid, see the module docstring for
    the confirmed EPSG code) - never reprojected. A section is
    overwhelmingly a single real path (one ``LineString``); the rare
    genuine multi-path case (a disjoint section) is preserved via
    ``Coordinate.parts``, never silently dropped to the first path only.

    No USRN or USRN-shaped field exists anywhere in this schema -
    confirmed by its full real field list, not assumed from Northern
    Ireland being outside the GB scheme (unlike
    :mod:`streetworks.osni`, which had to correct that exact
    assumption).
    """

    section_code: str
    section_name: str
    division_name: str
    section_office_name: str
    class_name: str
    section_type: str
    adoption_status: str
    shape_length: float
    geometry: Coordinate
    raw: dict[str, Any] = field(default_factory=dict)
