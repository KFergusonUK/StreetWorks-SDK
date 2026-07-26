"""Typed model for Servei Català de Trànsit (SCT) road incidents.

One :class:`Incident` per real ``cite:mct2_v_afectacions_data`` record in
the live ``incidenciesGML.xml`` feed - see :mod:`streetworks.sct.parser`
for the full field-by-field mapping this is built from.

**No start/end validity window exists anywhere in this feed - a genuine,
real gap, not an oversight.** Every other DATEX/GeoJSON adapter in this
SDK states a proposed or actual start/end pair; this one states exactly
one timestamp per record (:attr:`Incident.data`), and its own dataset
description ("RSS sobre l'estat del trànsit... Freqüència d'actualització:
Contínua") confirms this is a continuously-refreshed *current-state*
feed, not a works schedule - ``data`` reads as "when this record was last
reported/updated," not "when the works start." Treated honestly in
:func:`streetworks.common.from_sct`: kept on ``.raw``, never promoted
into ``proposed_start``/``actual_start``, which would misrepresent a
report timestamp as a scheduled or confirmed start.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

__all__ = ["ROADWORKS_DESCRIPCIO_TIPUS", "Incident"]

JSON = dict[str, Any]

#: The one real ``descripcio_tipus`` value that means roadworks - confirmed
#: live (136/165 real records in one pull). ``"Retenció"`` (congestion) and
#: ``"Cons"`` (temporary cone/lane measures) are the only other two real
#: values seen and are deliberately excluded - checked, not assumed: one
#: real ``"Retenció"`` record does carry ``causa="Obres"`` (congestion
#: whose *cause* is roadworks elsewhere), but ``descripcio_tipus`` is the
#: source's own primary, dedicated discriminator field (unlike DGT, which
#: has none) - promoting a secondary free-text ``causa`` value into the
#: primary is_roadworks decision would be exactly the kind of inference
#: this SDK avoids, and would likely just double-count a works site
#: already reported separately under its own real ``"Obres"`` record.
ROADWORKS_DESCRIPCIO_TIPUS = frozenset({"Obres"})


@dataclass
class Incident:
    """One real road incident record from SCT's live feed."""

    identificador: str
    tipus: str | None = None  # numeric type code, e.g. "3" - descripcio_tipus is its label
    subtipus: str | None = None  # numeric sub-type code, meaning not decoded here
    carretera: str | None = None  # road number, e.g. "C-15"
    pk_inici: float | None = None
    pk_fi: float | None = None
    #: Specific free-text cause, e.g. "Treballs de manteniment", "Senyalització
    #: vertical" - a finer classification than descripcio_tipus, not the
    #: discriminator itself. See ROADWORKS_DESCRIPCIO_TIPUS's own comment for
    #: the one real record where this says "Obres" under a non-Obres tipus.
    causa: str | None = None
    #: Genuinely dual-purpose across real records, confirmed live - sometimes
    #: a destination town ("GIRONA"), sometimes a free-text time-window note
    #: ("HORARI: 21 a 5h") - kept as stated, never guessed which applies.
    cap_a: str | None = None
    data: datetime | None = None  # report/last-update time - see module docstring
    nivell: str | None = None  # severity code 1-5, meaning not decoded here
    sentit: str | None = None  # direction, human-readable (e.g. "Creixent")
    descripcio: str | None = None  # short free-text status
    descripcio_tipus: str | None = None  # type label - see ROADWORKS_DESCRIPCIO_TIPUS
    font: str | None = None  # source attribution, always "SCT" in real data
    #: (lat, lon) - flipped from the feed's native GML (lon, lat) order to
    #: this SDK's WGS84 convention, same as from_datex2/from_wzdx/
    #: from_autobahn. None only if a record genuinely has no geometry
    #: (not seen live - 165/165 real records checked carried one).
    point: tuple[float, float] | None = None
    raw: JSON = field(default_factory=dict)

    @property
    def is_roadworks(self) -> bool:
        return self.descripcio_tipus in ROADWORKS_DESCRIPCIO_TIPUS
