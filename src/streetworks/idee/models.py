"""Spain: national road-transport network - IGN's (Instituto Geográfico
Nacional) own native model over IDEE's INSPIRE WFS. See
:mod:`streetworks.idee.client` for the full investigation this build acts
on, and ``docs/inspire-gml-investigation.md`` for the original live
association-chasing findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from streetworks.common.models import Coordinate

__all__ = ["Road"]


@dataclass(frozen=True)
class Road:
    """One real ``tn-ro:Road`` feature, with its constituent
    ``tn-ro:RoadLink`` geometry already resolved and aggregated - the
    two-hop join ``docs/inspire-gml-investigation.md`` found necessary,
    hidden behind this one object so callers never see ``RoadLink`` (or
    the ``xlink:href`` association chasing it takes) at all.

    ``geometry.parts`` holds one part per real, successfully-resolved
    RoadLink, in the Road's own stated ``net:link`` order - the same
    multi-line aggregation shape DataVIA's ``StreetLines`` already uses
    for one street spanning several ESUs (see
    :mod:`streetworks.common.from_datavia`). ``geometry`` is ``None``
    only when every real ``net:link`` on this Road failed to resolve - a
    broken cross-reference is a confirmed, real, non-systemic case (1 of
    3 sampled during the original investigation), not assumed
    impossible.

    ``unresolved_links`` counts real ``net:link`` hrefs that could not be
    resolved into a ``RoadLink`` - surfaced rather than silently dropped,
    per this SDK's evidence discipline.

    ``national_road_code``/``local_road_code`` are carried as-is,
    undecoded, and are **not assumed nationally unique** -
    ``local_road_code`` in particular is real but genuinely
    municipality-scoped, with no stated scoping identifier accompanying
    it on this feature to record honestly, so it stays a bare string
    field rather than a scoped :class:`~streetworks.common.Identifier`.

    ``id`` is this WFS's own internal ``gml:id`` (e.g.
    ``"TN-RO_ROAD_VIAL_LI80960000289"``) - what ``RESOURCEID``/
    ``GetFeatureById`` actually take. ``inspire_local_id``/
    ``inspire_namespace`` are the *separately* stated real INSPIRE
    identifier (``net:inspireId/base:Identifier``, e.g. local id
    ``"VIAL_LI80960000289"`` scoped to namespace ``"ES.SCNE.IGR-RT"``) -
    related but not textually identical to ``id``, so both are kept
    rather than one being derived from the other.
    """

    id: str
    name: str | None
    national_road_code: str | None
    local_road_code: str | None
    inspire_local_id: str | None
    inspire_namespace: str | None
    geometry: Coordinate | None
    unresolved_links: int
    raw: dict[str, Any] = field(default_factory=dict)
