"""Stream BAN's bulk address files - never loads a whole file into memory,
following the SRWR/OS Open USRN precedent (~25M addresses nationally; the
national file is ~900 MB-1.4 GB gzipped, confirmed live 2026-07).

**Two real bulk CSV formats are live today** at
``https://adresse.data.gouv.fr/data/ban/adresses/latest/{format}/adresses-{dept}.csv.gz``
(``{dept}`` a 2-character département code, e.g. ``"75"``/``"2A"``/``"971"``,
or ``"france"`` for the national file):

* ``csv-bal`` - **canonical here.** The only bulk format carrying BAN's
  permanent UUID (``uid_adresse``, see :mod:`streetworks.ban.models`), plus
  ``date_der_maj`` (last update) and ``commune_deleguee_*`` (a merged/former
  commune's own INSEE code and name, when the address's commune is one -
  confirmed live, e.g. Audierne, Finistère). Matches the design brief's own
  steer towards whichever format carries the more stable identifier.
* ``csv`` - exposed via :func:`iter_addresses_csv`, not hidden, per the
  design brief. No ``uid_adresse``/UUID, but does carry ``id_fantoir`` and
  ``code_postal`` directly. ``id_fantoir`` is, despite its name, already a
  TOPO-length code (DGFiP's FANTOIR replacement, since July 2023 - see
  :mod:`streetworks.ban.models` for the confirmed live join) - and notably,
  ``csv-bal`` does **not** carry a postcode column at all (postcodes don't
  map 1:1 to communes in France, so BAL scopes by commune, not postcode).

Two formats the design brief named as plausible (``csv-with-ids``,
``csv-bal-with-lang``) were checked live and **do not exist** as separate
downloadable files today - only ``csv``, ``csv-bal`` and ``addok`` (a search
index, not a flat file - out of scope here) are real. Treat any source
naming the other two as describing a format landscape that predates this
consolidation.

Regional-language street names: the ``csv`` format's ``alias`` column is
where these would appear, but it was empty across every real row sampled
(Finistère, a genuinely Breton-speaking département, included) - unconfirmed
live, not modelled as absent, just not observed.
"""

from __future__ import annotations

import csv
import gzip
import io
from collections.abc import Iterator
from pathlib import Path
from typing import IO

from .models import BANAddress, address_from_bal_row, address_from_csv_row

__all__ = [
    "BULK_BASE_URL",
    "bulk_url",
    "iter_addresses",
    "iter_addresses_csv",
    "open_ban_csv",
]

#: Confirmed live 2026-07 via the data.gouv.fr dataset API for
#: "base-adresse-nationale" (not the deprecated `adresse.data.gouv.fr/data/ban/`
#: directory listing page, which is now a JS-rendered app, not a plain index).
BULK_BASE_URL = "https://adresse.data.gouv.fr/data/ban/adresses/latest"


def bulk_url(area: str = "france", *, format: str = "csv-bal") -> str:
    """The download URL for one département's (or, by default, the whole
    country's) bulk file. ``area`` is a département code (``"75"``,
    ``"2A"``) or ``"france"`` for the national file; both confirmed live."""
    return f"{BULK_BASE_URL}/{format}/adresses-{area}.csv.gz"


def open_ban_csv(source: str | Path | IO[str]) -> tuple[IO[str], bool]:
    """Return a text stream for ``source`` and whether the caller must
    close it. Accepts a path to a ``.csv``, a path to a ``.csv.gz`` (as
    downloaded), or an already-open text stream."""
    if not isinstance(source, (str, Path)):
        return source, False  # caller's stream, caller's responsibility
    path = Path(source)
    if path.suffix.lower() == ".gz":
        raw = gzip.open(path, "rb")
        return io.TextIOWrapper(raw, encoding="utf-8", newline=""), True
    return open(path, encoding="utf-8", newline=""), True


def iter_addresses(source: str | Path | IO[str]) -> Iterator[BANAddress]:
    """Stream :class:`~streetworks.ban.models.BANAddress` records from a
    ``csv-bal`` file (a path to ``.csv``/``.csv.gz``, or an open text
    stream) - the canonical bulk format, see the module docstring."""
    stream, owned = open_ban_csv(source)
    try:
        reader = csv.DictReader(stream, delimiter=";")
        for row in reader:
            yield address_from_bal_row(row)
    finally:
        if owned:
            stream.close()


def iter_addresses_csv(source: str | Path | IO[str]) -> Iterator[BANAddress]:
    """Stream :class:`~streetworks.ban.models.BANAddress` records from the
    plain ``csv`` bulk format (secondary - see the module docstring;
    ``ban_id`` is always ``None`` from this route)."""
    stream, owned = open_ban_csv(source)
    try:
        reader = csv.DictReader(stream, delimiter=";")
        for row in reader:
            yield address_from_csv_row(row)
    finally:
        if owned:
            stream.close()
