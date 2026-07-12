"""Custom logic for the Street Lookup API's ``/nsg/streets`` responses.

Keeps the lookup model import and the "is this street traffic sensitive"
reduction out of ``client.py``. Consistent with the rest of the SDK, the result
is a plain dict; the generated ``AdditionalSpecialDesignationsResponse`` model,
when available, is used only to *verify* the ASD rows, not as the return type.
Validation is skipped when the models have not been generated.
"""

from __future__ import annotations

from typing import Any

# Special-designation code 2 = "traffic sensitive". The raw API value is the
# int 2, which also equals the generated enum member's value.
_TRAFFIC_SENSITIVE_CODE = 2


def summarise_traffic_sensitive(street: dict) -> dict[str, Any]:
    """Reduce a raw ``/nsg/streets/{usrn}`` response to::

        {"is_traffic_sensitive": bool, "designations": [<raw ASD row>, ...]}

    ``is_traffic_sensitive`` is True if the street carries the blanket
    ``traffic_sensitive`` flag or has any "traffic sensitive" (code 2) special
    designation. ``designations`` is the list of those code-2 ASD entries -
    returned as their original row dicts, so the time windows
    (``special_desig_start_time``/``end_time``) and ``whole_road`` detail are
    preserved - or ``[]``.

    If the generated v6 models are present, each ASD entry is validated against
    ``AdditionalSpecialDesignationsResponse`` first, so malformed/drifted data
    raises rather than being silently reduced. (We validate the ASD rows we
    actually reduce over - not the whole ``StreetResponse`` - because the live
    API can return a ``crs`` object on the street geometry that the generated
    geometry models reject; that drift is unrelated to traffic sensitivity.)
    If the models are not generated, validation is skipped and the values are
    read straight off the raw dictionary.
    """
    raw_asds = street.get("additional_special_designations_response") or []
    try:
        from ..models.v6.lookup import AdditionalSpecialDesignationsResponse
    except ModuleNotFoundError:
        pass  # models not generated - skip validation, read the raw dict directly
    else:
        for asd in raw_asds:
            AdditionalSpecialDesignationsResponse.model_validate(asd)  # verify

    designations = [
        asd for asd in raw_asds if asd.get("street_special_desig_code") == _TRAFFIC_SENSITIVE_CODE
    ]
    return {
        "is_traffic_sensitive": bool(street.get("traffic_sensitive")) or bool(designations),
        "designations": designations,
    }
