"""Custom logic for the Reporting API's ``/section-58s`` endpoint.

Keeps the Section 58 model import and the "which restriction is active"
reduction out of ``client.py``. Consistent with the rest of the SDK, the result
is a plain dict; ``Section58SummaryResponse``, when available, is used only to
*verify* each row, not as the return type. Validation is skipped (not fatal)
when the models have not been generated.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def summarise_active_section_58(rows: Iterable[dict]) -> dict[str, Any]:
    """Reduce raw ``/section-58s`` rows to a small summary::

        {"active": bool, "upcoming": bool, "section_58": <raw row> | None}

    ``section_58`` is the in-force restriction (latest ``end_date``), else the
    next upcoming one (soonest ``start_date``), else None - returned as the
    original row dict. "In force"/"upcoming" key off Street Manager's
    ``section_58_status``. Ordering keys off the raw ISO-8601 date strings;
    Street Manager returns UTC (``...Z``), for which lexical ordering equals
    chronological ordering.

    If the generated v6 models are present, every row is validated against
    ``Section58SummaryResponse`` first, so malformed/drifted data raises rather
    than being silently reduced. If the models are not generated, validation is
    skipped and the values are read straight off the raw dict.
    """
    rows = list(rows)
    try:
        from ..models.v6.reporting import Section58SummaryResponse
    except ModuleNotFoundError:
        pass  # models not generated - skip validation, read the raw dict directly
    else:
        for row in rows:
            Section58SummaryResponse.model_validate(row)  # verify

    in_force = [r for r in rows if r.get("section_58_status") == "in_force"]
    if in_force:
        raw = max(in_force, key=lambda r: r["end_date"])
        return {"active": True, "upcoming": False, "section_58": raw}

    proposed = [r for r in rows if r.get("section_58_status") == "proposed"]
    if proposed:
        raw = min(proposed, key=lambda r: r["start_date"])
        return {"active": False, "upcoming": True, "section_58": raw}

    return {"active": False, "upcoming": False, "section_58": None}
