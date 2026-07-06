"""Custom logic for the Reporting API's ``/section-58s`` endpoint.

Keeps the Section 58 model import and the "which restriction is active"
reduction out of ``client.py``. Consistent with the rest of the SDK, the result
is a plain dict; ``Section58SummaryResponse`` is used only to *verify* each row
(and to order by real datetimes), not as the return type.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

_MODELS_MISSING = (
    "Street Manager v6 models are not generated, so `active_section_58` cannot "
    "validate rows. They live at streetworks.streetmanager.models.v6.reporting "
    "and are produced by scripts/generate_models.py (see README.md)."
)


def summarise_active(rows: Iterable[dict]) -> dict[str, Any]:
    """Reduce raw ``/section-58s`` rows to a small summary::

        {"active": bool, "upcoming": bool, "section_58": <raw row> | None}

    ``section_58`` is the in-force restriction (latest ``end_date``), else the
    next upcoming one (soonest ``start_date``), else None - returned as the
    original row dict. Every row is validated against ``Section58SummaryResponse``
    first, so malformed/drifted data raises rather than being silently reduced.
    "In force"/"upcoming" key off Street Manager's ``section_58_status``.

    Raises ``RuntimeError`` if the v6 models have not been generated.
    """
    try:
        from ..models.v6.reporting import Section58StatusResponse, Section58SummaryResponse
    except ModuleNotFoundError as exc:  # models not generated
        raise RuntimeError(_MODELS_MISSING) from exc

    rows = list(rows)
    parsed = [Section58SummaryResponse.model_validate(r) for r in rows]  # verify
    pairs = list(zip(rows, parsed, strict=True))

    in_force = [
        (raw, m) for raw, m in pairs if m.section_58_status == Section58StatusResponse.in_force
    ]
    if in_force:
        raw, _ = max(in_force, key=lambda pair: pair[1].end_date)
        return {"active": True, "upcoming": False, "section_58": raw}

    proposed = [
        (raw, m) for raw, m in pairs if m.section_58_status == Section58StatusResponse.proposed
    ]
    if proposed:
        raw, _ = min(proposed, key=lambda pair: pair[1].start_date)
        return {"active": False, "upcoming": True, "section_58": raw}

    return {"active": False, "upcoming": False, "section_58": None}
