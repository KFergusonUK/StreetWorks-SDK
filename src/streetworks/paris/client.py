"""Paris: "Chantiers à Paris" - the City of Paris's own occupation-permit
register for street/public-space worksites, over the Paris Data open-data
portal. This SDK's third municipal permit register after NYC DOT and
Chicago CDOT, and the first genuinely new platform: **OpenDataSoft**, the
French/EU near-equivalent of Socrata - see :mod:`streetworks.socrata` for
that comparison, and this module's own docstring below for why no shared
``streetworks.opendatasoft`` client is being extracted yet (bespoke first,
extracted only when a second OpenDataSoft-backed provider needs the
identical shape - the same sequence that produced ``SodaClient`` itself).

.. attention::
   **Confirmed live (2026-08-06)** against a real, unauthenticated pull
   (``opendata.paris.fr``, no app key sent or required, 4,707 real
   records at time of writing).

**Dataset**: ``chantiers-a-paris`` - *"chantiers en cours"* (ongoing
worksites) of the City of Paris, network operators, and private projects
occupying public space, published by the *Direction de la Voirie et des
Déplacements - Ville de Paris*. Updated daily. Each record is one
*emprise* (a worksite footprint); several emprises can share one parent
*chantier*.

**Roadworks-vs-private filter, evidenced not guessed.** The real
``chantier_categorie`` field has exactly three live values: ``"Ville de
Paris (Tvx sur espace ou édifice public)"`` (598 rows - the city's own
works on public space), ``"Opérateurs de réseau
(gaz-électricité-RATP-etc)"`` (1,191 rows - gas/electricity/RATP/telecom
network operators), and ``"Tiers (travaux sur bâtiment)"`` (2,918 rows -
private building works, e.g. scaffolding, occupying public space but not
roadworks). :meth:`ParisClient.iter_roadworks` excludes only the last
category - the other two are genuine street/public-space works.

**Geometry is already WGS84** - both ``geo_shape`` (a GeoJSON ``Feature``,
always ``Polygon`` in every record checked live - the emprise footprint)
and ``geo_point_2d`` (``{"lon": ..., "lat": ...}``, ODS's own
representative point for the shape) are served in WGS84 degrees, despite
the underlying Paris data itself being surveyed in Lambert 93
(EPSG:2154) - OpenDataSoft reprojects on the way out. No reprojection
needed here, unlike this SDK's British National Grid providers.

**Promoter is real and specific**: ``moa_principal`` (*maîtrise d'ouvrage
principale*) carries 28 real distinct values live - ``ENEDIS`` (446),
``GRDF`` (137), ``EAU DE PARIS`` (71), ``RATP`` (93), ``CPCU`` (278, the
district heating network), ``Direction de la Voirie et des
Déplacements`` (270), ``Ville de Paris (autres)`` (177), and more - not a
placeholder field.

**Grouping, the same shape as NYC's ``applicationtrackingid``.**
``chantier_cite_id`` genuinely groups multiple real emprise rows under
one parent chantier (e.g. a real 3-emprise green-space maintenance job,
``chantier_cite_id=329467``, spanning 3 distinct real polygons in the
16th arrondissement) - see :mod:`streetworks.common.from_paris` for how
this becomes one ``Works`` with several ``WorksSite`` entries.
``num_emprise`` is the per-site identifier; ``demande_cite_id`` is the
underlying permit-application id (not otherwise used by the converter).

**No street/segment identifier field** - only ``cp_arrondissement``
(postcode) and the geometry itself; ``WorksSite.street_ref`` is never
populated, the same NYC/Chicago/Roads-ACT discipline.

**No explicit status field** - only ``date_debut``/``date_fin``, the
same honest gap NYC's ``permitstatusshortdesc``/Chicago's
``applicationstatus`` don't really close either (a permit's own status
isn't a "the work actually happened as scheduled" signal). See
:mod:`streetworks.common.from_paris` for how this maps to
``date_confidence``.

**Licence: ODbL 1.0 (Open Database License), confirmed live** from the
dataset's own metadata (``http://opendatacommons.org/licenses/odbl/``) -
a **stronger documentation case** than NYC/Chicago's own unconfirmed-
licence tier, not a gap: this is a real, named, share-alike licence.
ODbL's share-alike clause means an adapted/derived database must itself
be released under ODbL (or a compatible licence) - a real obligation
that flows to anyone redistributing a derived dataset built from this
feed, the same nuance :mod:`streetworks.au.act`'s own CC BY-SA licence
carries relative to its plain-CC-BY siblings. Attribution: "Ville de
Paris".

**No app key required** - every read in this investigation succeeded
unauthenticated; ODS app keys (if ever added) only raise rate limits,
the same optional-courtesy role Socrata's ``X-App-Token`` plays.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["CHANTIERS_URL", "ParisClient"]

JSON = dict[str, Any]

#: OpenDataSoft Explore API v2 records endpoint for the "Chantiers à
#: Paris" dataset - confirmed live, no app key required.
CHANTIERS_URL = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/chantiers-a-paris/records"

#: Real, evidenced roadworks filter - excludes only the confirmed
#: private/non-roadworks category. See module docstring for the real
#: category counts this was built from.
_ROADWORKS_WHERE = 'chantier_categorie != "Tiers (travaux sur bâtiment)"'

#: A safety net against a malformed/looping server response, not evidence
#: ODS's own limit/offset pagination is unreliable - the same role
#: streetworks.socrata.SodaClient's _MAX_PAGES plays.
_MAX_PAGES = 10_000


class ParisClient:
    """Fetch worksite records from the City of Paris's "Chantiers à
    Paris" register. No credentials required.

    >>> from streetworks.paris import ParisClient
    >>> from streetworks.common import from_paris
    >>> with ParisClient() as paris:  # doctest: +SKIP
    ...     works = from_paris(list(paris.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_permits(self, *, where: str | None = None, page_size: int = 100) -> Iterator[JSON]:
        """Yield every real emprise record matching ``where`` (ODSQL, e.g.
        ``'chantier_categorie = "Ville de Paris (Tvx sur espace ou
        édifice public)"'``), paging via ``limit``/``offset`` until a page
        comes back shorter than ``page_size`` or ``offset`` reaches the
        server's own ``total_count``."""
        offset = 0
        for _ in range(_MAX_PAGES):
            params: dict[str, str] = {"limit": str(page_size), "offset": str(offset)}
            if where:
                params["where"] = where
            response = self._transport.request("GET", CHANTIERS_URL, params=params)
            body = response.json()
            results = body.get("results") or []
            yield from results
            offset += len(results)
            if len(results) < page_size or offset >= body.get("total_count", offset):
                return

    def iter_roadworks(self, *, where: str = _ROADWORKS_WHERE) -> Iterator[JSON]:
        """Real emprise records excluding the confirmed private/non-
        roadworks category (``chantier_categorie = "Tiers (travaux sur
        bâtiment)"``) - see module docstring for the real category counts
        this filter was built from."""
        yield from self.iter_permits(where=where)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> ParisClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
