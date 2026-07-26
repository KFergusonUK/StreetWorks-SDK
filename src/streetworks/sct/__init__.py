"""Servei Català de Trànsit (SCT) - Catalonia's real-time road incidents.

Fills the larger of DGT's two documented exclusions (DGT explicitly omits
Catalonia and the Basque Country - see :mod:`streetworks.datex2.dgt`).
See ``docs/catalonia-sct-investigation.md`` for the recon this build is
based on.

The feed (``incidenciesGML.xml``) is genuine WFS/GML - real ``gml:Point``
geometry inside a ``wfs:FeatureCollection`` - but flat and simple: one
geometry element plus a dozen scalar sibling fields per record, no
nesting, no ``xlink`` associations. This module is a **small, contained
parser for this specific shape**, the same way Autobahn GmbH got its own
bespoke JSON parser rather than being forced through the DATEX path - it
deliberately **does not start, touch, or depend on** this SDK's parked
general INSPIRE-GML-reader decision (the one Mecklenburg-Vorpommern/
Saxony-Anhalt/CartoCiudad are parked behind). No new dependency: plain
``xml.etree.ElementTree``, matched by local name, the same tolerant
approach :mod:`streetworks.datex2.parser` already takes.

**Discriminator**: ``descripcio_tipus`` - real, clean, explicit
(``"Obres"``/``"Retenció"``/``"Cons"``, confirmed live) - see
:mod:`streetworks.sct.models` for the one genuine edge case checked
(a congestion record whose free-text ``causa`` happens to say "Obres")
and why it's deliberately not reclassified.

**No start/end validity window anywhere in this feed** - a genuinely
real-time, continuously-refreshed current-state feed (confirmed via the
dataset's own metadata and by watching ``Last-Modified`` change between
live pulls), not a works schedule. See :mod:`streetworks.sct.models` and
:mod:`streetworks.common.from_sct` for how this is handled honestly.

**CRS**: WGS84 (``EPSG:4326``), confirmed live from the feed's own
``srsName`` and real coordinate magnitudes - no reprojection question, the
simplest CRS story of any Spanish adapter in this SDK.

**Licence**: Catalonia's own "Llicència oberta d'ús d'informació" -
confirmed genuinely open (reuse, distribution, and derivative works
permitted worldwide, attribution required: "Generalitat de Catalunya.
Departament d'Interior") - the cleanest licence of any Spanish source
checked this session. Real trimmed fixture used here, not synthetic.

**Network scope**: ``multi_authority_interurban`` - the same shape as
DGT's own real data (see ``docs/network-scope-audit.md``). Real road-
number prefixes span the Generalitat's own network (``C-``) *and* all
four provincial councils' networks (``B-``/``BV-``/``BP-``,
``GI-``/``GIV-``/``GIP-``, ``T-``/``TV-``/``TP-``, ``L-``/``LV-``) *and*
some state roads within Catalan territory (``N-``, ``A-``, ``AP-``) -
never confirmed to reach municipal streets.
"""

from .client import BASE_URL, INCIDENTS_PATH, SCTClient
from .models import ROADWORKS_DESCRIPCIO_TIPUS, Incident
from .parser import parse_incidents

__all__ = [
    "SCTClient",
    "BASE_URL",
    "INCIDENTS_PATH",
    "Incident",
    "ROADWORKS_DESCRIPCIO_TIPUS",
    "parse_incidents",
]
