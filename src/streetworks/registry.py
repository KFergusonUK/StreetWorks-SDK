"""Provider discovery - one registry, plus two thin functions over it.

The rest of this SDK is organised by *technology* (`streetworks.datex2.dgt`,
`streetworks.ogc.germany`), because that's how the code has to be
structured. But a user rarely starts from "I want a DATEX II v3 client" -
they start from "I want Spanish roadworks" or "what covers Wales?". That's
specialist knowledge this SDK exists to save them, so this module answers
discovery questions directly: :func:`providers` (browse/filter) and
:func:`get_provider` (fetch one client class by name).

**Purely additive.** No existing import path, class, or behaviour changes -
every native interface documented elsewhere in this SDK works exactly as
before. This is a discovery facade, not a new abstraction: the common model
(`streetworks.common.Works`/`WorksSite`) is already the provider-agnostic
layer.

**Deliberately not built here** (see the design brief): no uniform
`search()`/query facade - a method that looks like a database query but is
actually a 170 MB download (NDW), 113 sequential HTTP calls (Autobahn), or a
UTM33N ZIP needing reprojection before a WGS84 bbox could even apply
(Saxony) would make the SDK untrustworthy; no country-level aggregation
(`connect("germany")` merging four providers' licences/CRSs/source grades
into one list that looks homogeneous and isn't); no new client-side
abstraction layer. All deferred to their own design sessions.

**Capabilities are derived, never declared** - :meth:`ProviderEntry.capabilities`
inspects what the client class actually implements (method names, including
one level into known sub-API objects like ``StreetManagerClient.work``) each
time it's called, rather than reading from a hand-maintained dict that would
drift from reality within two releases. Only categories this SDK genuinely
models are reported: roadworks retrieval, planning artifacts, address
lookup, street lookup, safety context, write/publish. If a capability can't
be derived cleanly for some provider's shape, it's just absent from that
provider's result - never guessed to fill a gap.

**Registry vs. README duplication - registry is the source of truth for
territory/credentials/licence facts; the README's provider table is
independent human prose covering different ground (links, API surface
depth) and is allowed to duplicate the high-level facts.** Chose *accepted
duplication* over *generated table* because the two serve different
readers: this registry's ``description`` is deliberately a single
domain-naive line ("Great Britain's national gazetteer"), while the
README table rows carry links, protocol detail, and per-nine-API breakdowns
that would be lost forced through one shared template. Drift is caught by
``tests/test_registry.py``'s coverage test, which asserts every registry
entry's top-level module is mentioned in the README's provider table (and
vice versa) - not text equality, but nothing can go missing silently on
either side.

**Two "unconfirmed" gaps found building this registry, not previously
documented**: NDW (Netherlands) and Digitraffic (Finland) state no licence
anywhere in their own module code, and a live check of both portals' public
pages (2026-07) found no server-rendered licence statement either (both are
JS-rendered portals that didn't yield to a quick scrape) - marked
``licence=None`` with ``licence_confirmed=False``, the same honest-gap
convention Autobahn's module already established, rather than guessed at.
"""

from __future__ import annotations

import importlib
import inspect
import re
from dataclasses import dataclass, field
from difflib import get_close_matches
from enum import Enum
from typing import Any

from .exceptions import AmbiguousProviderError, ProviderNotFoundError

# Deliberately NOT `from .common.models import SourceGrade` here: that
# triggers `streetworks.common`'s package __init__, which eagerly imports
# every `from_<provider>` converter, which eagerly imports every provider's
# client module (httpx included) - exactly the "providers() must not import
# every provider module" cost this module's performance note rules out.
# `source_grade` below is a plain string matching `SourceGrade`'s values
# (`streetworks.common.SourceGrade.OPERATOR == "operator"` is True - it's a
# `str` Enum) - equality works both ways without importing the type.

__all__ = ["Kind", "NetworkScope", "ProviderEntry", "providers", "get_provider"]


class Kind(str, Enum):
    """What a provider fundamentally *is* - the four shapes this SDK
    actually models. Not a finer domain taxonomy (no "national-motorway"
    vs. "regional" split) - that's what ``scope_note`` is for.

    ``ADDRESSES`` and ``STREETS`` used to be one ``"gazetteer"`` value -
    split because lumping them together produced a real analytical error:
    "European gazetteers have no street geometry" looked true when BAN,
    BAG and Kartverket (all address registers) were the only three
    examples, but it's false - the geometry lives in a *street*-register,
    published separately by a different body in every territory checked
    so far (the NSG/USRN in the UK, NWB in the Netherlands). The UK is
    unusual in unifying both under one register (the NSG); everywhere
    else this SDK has checked, they're two different publishers with two
    different `kind`s, and `providers()` can only show that gap once the
    two are told apart.

    Still not a finer domain taxonomy on its own - "national-motorway" vs.
    "regional" now lives in :class:`NetworkScope` instead, a deliberately
    separate, roadworks-only field (see its own docstring for why it isn't
    folded in here).
    """

    ROADWORKS = "roadworks"
    ADDRESSES = "addresses"
    STREETS = "streets"
    CONTEXT = "context"


class NetworkScope(str, Enum):
    """What tier of the road network a roadworks provider's real data
    actually reaches - a second, orthogonal classification to
    :class:`Kind`, roadworks-only (``None`` on every gazetteer/address/
    street/context entry - see :attr:`ProviderEntry.network_scope`).

    Added from a dedicated audit (``docs/network-scope-audit.md``) after
    a real, live-confirmed surprise: DGT (Spain)'s own real data reaches
    several regional/provincial/insular road authorities' works besides
    the state network its name implies (``CV-``/Comunidad Valenciana,
    ``M-``/Madrid, ``Ma-``/``Me-``/the Balearic insular councils, ~10
    prefixes checked live), not just "the roads DGT itself owns" - a
    provider's stated remit is not proof of its real data's actual reach,
    checked here the same "verify, don't assume" way as everything else
    in this SDK.

    Deliberately **not** a finer split than the audit's real findings
    warrant: two providers (``trafficwatchni``, ``saxony``) have a
    genuine two-tier scope depending on which part of their own feed is
    queried - that nuance lives in the existing free-text ``scope_note``
    field, not a new enum value each, so this enum stays small and
    filterable rather than growing one value per provider's own
    idiosyncrasy. ``wzdx`` (a schema ~40+ agencies publish independently,
    not one provider's coverage) and ``dtro`` (a legal-orders register,
    not a works-progress feed - the concept doesn't apply the same way)
    both get ``UNKNOWN``/``NOT_APPLICABLE`` plus a ``scope_note``
    explaining why, rather than a forced, misleading single value.
    """

    #: All roads, all promoters - the permit-register tier (Street
    #: Manager, SRWR, Jersey; live-confirmed via real promoter/authority
    #: diversity in each case - see the audit).
    COMPREHENSIVE = "comprehensive"
    #: Several road authorities' interurban networks aggregated by one
    #: provider (state + regional/provincial/insular), but never reaching
    #: municipal streets - the DGT shape, live-confirmed via real
    #: road-number prefixes, not assumed from DGT's own "national" remit.
    MULTI_AUTHORITY_INTERURBAN = "multi_authority_interurban"
    #: One national/state road authority's own network only - explicitly
    #: excludes local/municipal roads (National Highways' SRN, Bison
    #: Futé's RRN, Autobahn's non-motorway siblings, and the single-
    #: national-authority DATEX/CSV adapters: Digitraffic, IRCA, Bulgaria,
    #: Via Lietuva, Luxembourg).
    STRATEGIC = "strategic"
    #: Motorways only - a stricter subset of STRATEGIC (Autobahn).
    MOTORWAY = "motorway"
    #: One sub-national authority's own network, not that area's
    #: municipal streets and not the whole country (Belgium/Flanders,
    #: Consell de Mallorca).
    REGIONAL = "regional"
    #: A multi-agency schema, not one provider's coverage - scope varies
    #: feed-by-feed and can't be summarised as one value (WZDx).
    VARIES_BY_FEED = "varies_by_feed"
    #: Not a works-progress register at all - a different kind of thing
    #: network scope doesn't meaningfully classify (D-TRO).
    NOT_APPLICABLE = "not_applicable"
    #: Never verified against real data - the honest default, not a
    #: guess (Vegvesen; also the default for any newly-added roadworks
    #: provider until it's actually audited).
    UNKNOWN = "unknown"


#: Query-expansion only - "UK" is never stored on a registry entry, never
#: added to the territory vocabulary the common model uses, and never
#: reaches `Works.territory`. It exists purely so `providers(territory="UK")`
#: expands to the four real nations before matching. Add further groupings
#: only if a real need appears - don't speculatively build "Europe".
_GROUPINGS: dict[str, frozenset[str]] = {
    "uk": frozenset({"England", "Scotland", "Wales", "Northern Ireland"}),
}

#: Obvious variant spellings that aren't just a case difference, normalised
#: before matching. Deliberately short - add entries as real confusion
#: surfaces, not speculatively.
_TERRITORY_SYNONYMS: dict[str, str] = {
    "us": "usa",
    "gb": "great britain",
}

#: Method-name prefixes that genuinely indicate a write/publish operation
#: on every real provider client checked (Street Manager's WorkAPI/
#: ReportingAPI, D-TRO's DTROClient) - a heuristic over real method names,
#: not a declared per-provider flag.
_WRITE_METHOD_PREFIXES = (
    "create_",
    "assess_",
    "start_",
    "stop_",
    "add_",
    "submit_",
    "publish_",
    "update_",
    "upload_",
)

_SUB_API_ASSIGNMENT = re.compile(r"self\.\w+\s*=\s*(\w+)\(")


def _public_names(cls: type) -> set[str]:
    """Every public method/attribute name reachable from ``cls`` - including
    one level into sub-API objects assigned in ``__init__`` (e.g.
    ``StreetManagerClient.work = WorkAPI(self)``), discovered by reading
    ``__init__``'s own source and resolving the class name through its
    ``__globals__`` - not guessed, not hardcoded to any one provider's
    shape. Falls back to the flat set if source isn't available (e.g. a
    C-extension type, never the case for this SDK's own clients) or no
    sub-API pattern is found."""
    names = {name for name in dir(cls) if not name.startswith("_")}
    init = getattr(cls, "__init__", None)
    if init is None:
        return names
    try:
        source = inspect.getsource(init)
    except (OSError, TypeError):
        return names
    for class_name in _SUB_API_ASSIGNMENT.findall(source):
        sub_cls = getattr(init, "__globals__", {}).get(class_name)
        if isinstance(sub_cls, type):
            names.update(name for name in dir(sub_cls) if not name.startswith("_"))
    return names


@dataclass(frozen=True)
class ProviderEntry:
    """One provider, as far as discovery needs to know. Everything a native
    client actually does lives in that client's own module - this is
    metadata *about* it, not a replacement for it."""

    key: str
    name: str
    description: str
    kind: Kind
    territories: frozenset[str]
    _module: str
    _client_name: str
    import_line: str
    administrative_area: str | None = None
    scope_note: str | None = None
    #: Which tier of the road network this provider's real data reaches -
    #: see :class:`NetworkScope`. Roadworks-only: left ``None`` (the
    #: dataclass default) on every gazetteer/address/street/context entry,
    #: since the concept doesn't apply there. Every ``kind=Kind.ROADWORKS``
    #: entry must set this explicitly - to a real audited value, or to
    #: ``NetworkScope.UNKNOWN`` if genuinely unaudited (Vegvesen) - never
    #: left at the bare ``None`` default, which is reserved for "this
    #: concept doesn't apply to this provider at all". Enforced by
    #: ``test_every_roadworks_provider_has_a_network_scope``.
    network_scope: NetworkScope | None = None
    credentials: str | None = None  # None means genuinely credential-free
    licence: str | None = None
    licence_confirmed: bool = True  # False = "unconfirmed", not "none exists"
    #: A plain string matching `streetworks.common.SourceGrade`'s values
    #: ("register" / "operator" / "traveller_info") - see module docstring
    #: for why this isn't the real enum type.
    source_grade: str | None = None
    verified: bool = True
    aliases: frozenset[str] = field(default_factory=frozenset)

    @property
    def client(self) -> Any:
        """The provider's client class (or, for `opendata`, its receive-only
        entry point - not every provider is an instantiable client, see its
        entry). Resolved lazily on access, not at import time - see module
        docstring's performance note."""
        module = importlib.import_module(self._module)
        return getattr(module, self._client_name)

    def capabilities(self) -> tuple[str, ...]:
        """What this provider's client actually implements, derived by
        inspection each call - never a stored/declared list. See module
        docstring."""
        names = _public_names(self.client)
        caps: list[str] = []
        if self.kind is Kind.ROADWORKS:
            caps.append("roadworks retrieval")
        elif self.kind is Kind.ADDRESSES:
            caps.append("address lookup")
        elif self.kind is Kind.STREETS:
            caps.append("street lookup")
        elif self.kind is Kind.CONTEXT:
            caps.append("safety context")
        if any(name.startswith(_WRITE_METHOD_PREFIXES) for name in names):
            caps.append("write/publish")
        if any("forward_plan" in name.lower() or "paa" in name.lower() for name in names):
            caps.append("planning artifacts")
        return tuple(caps)

    def __str__(self) -> str:
        lines = [f"{self.name}"]
        lines.append(f"  {self.description}")
        if self.network_scope is not None:
            lines.append(f"  Network scope: {self.network_scope.value.replace('_', ' ')}")
        if self.scope_note:
            lines.append(f"  Scope: {self.scope_note}")
        creds = self.credentials or "No credentials required"
        lines.append(f"  Credentials: {creds}")
        if not self.verified:
            lines.append("  ** Not yet verified against live data **")
        lines.append(f"  {self.import_line}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.__str__()


class ProviderList(list):
    """A `list[ProviderEntry]` that renders readably in a REPL - discovery
    and "how do I use it" are the same question, so the default one-line-
    per-entry list repr (which would bury the import line) isn't good
    enough here."""

    def __repr__(self) -> str:
        if not self:
            return "[]"
        return "\n\n".join(str(entry) for entry in self)


def _normalise_territory(value: str) -> str:
    lowered = value.strip().lower()
    return _TERRITORY_SYNONYMS.get(lowered, lowered)


def _matches_territory(entry: ProviderEntry, wanted: str) -> bool:
    wanted_norm = _normalise_territory(wanted)
    expanded = _GROUPINGS.get(wanted_norm)
    entry_territories_norm = {_normalise_territory(t) for t in entry.territories}
    if expanded is not None:
        expanded_norm = {_normalise_territory(t) for t in expanded}
        return bool(entry_territories_norm & expanded_norm)
    return wanted_norm in entry_territories_norm


def _all_known_territories() -> set[str]:
    result: set[str] = {name.upper() for name in _GROUPINGS}  # "uk" -> "UK", for display
    for entry in _REGISTRY:
        result.update(entry.territories)
    return result


def providers(
    *,
    territory: str | None = None,
    kind: Kind | str | None = None,
    credentials: bool | None = None,
) -> ProviderList:
    """Browse/filter the provider registry.

    >>> providers()                          # everything
    >>> providers(territory="Wales")         # every provider covering Wales
    >>> providers(territory="UK")            # expands to the four nations
    >>> providers(kind="addresses")         # address registers
    >>> providers(kind="streets")           # street/road-network registers
    >>> providers(credentials=False)         # the credential-free ones

    Territory matching is case-insensitive and tolerant of obvious variants
    ("wales"/"Wales", "UK"/"uk", "USA"/"US"). An unknown territory returns
    an empty :class:`ProviderList` and emits a ``UserWarning`` naming the
    known territories - not an exception (this is a browsing function, not
    a strict lookup - see :func:`get_provider` for that), and not silence
    either.
    """
    if territory is not None:
        known = _all_known_territories()
        known_norm = {_normalise_territory(t) for t in known}
        if _normalise_territory(territory) not in known_norm:
            import warnings

            warnings.warn(
                f"Unknown territory {territory!r}. Known territories: "
                f"{', '.join(sorted(known))}.",
                UserWarning,
                stacklevel=2,
            )
            return ProviderList()

    kind_norm: Kind | None = None
    if kind is not None:
        kind_norm = kind if isinstance(kind, Kind) else Kind(str(kind).strip().lower())

    result = ProviderList()
    for entry in _REGISTRY:
        if territory is not None and not _matches_territory(entry, territory):
            continue
        if kind_norm is not None and entry.kind is not kind_norm:
            continue
        if credentials is not None:
            needs_credentials = entry.credentials is not None
            if needs_credentials != credentials:
                continue
        result.append(entry)
    return result


def get_provider(key: str) -> Any:
    """Fetch one provider's client **class** (not an instance - clients have
    varying constructor signatures, e.g. Street Manager needs credentials
    and an environment, DGT needs neither, and returning an instance would
    paper over that).

    >>> DGTClient = get_provider("spain")
    >>> with DGTClient() as dgt:
    ...     situations = list(dgt.iter_roadworks())

    ``key`` is matched case-insensitively against every provider's own
    ``key`` and registered aliases first (unambiguous by construction).
    Failing that, it's tried as a territory name: a territory covered by
    exactly one provider resolves to that provider (the same convenience
    aliases like ``"spain"``/``"finland"`` give explicitly, for any
    territory that happens to be singly-covered); a territory covered by
    several **raises** :class:`~streetworks.exceptions.AmbiguousProviderError`
    naming every candidate - resolving ambiguity by guessing is exactly how
    a user ends up with the wrong dataset, so this never does it. An
    unrecognised key raises :class:`~streetworks.exceptions.ProviderNotFoundError`
    with near-matches, if any look close.
    """
    normalised = key.strip().lower()
    for entry in _REGISTRY:
        if entry.key == normalised or normalised in entry.aliases:
            return entry.client

    territory_matches = [e for e in _REGISTRY if _matches_territory(e, normalised)]
    if len(territory_matches) == 1:
        return territory_matches[0].client
    if len(territory_matches) > 1:
        candidates = ", ".join(sorted(e.key for e in territory_matches))
        raise AmbiguousProviderError(
            f"{key!r} matches more than one provider: {candidates}. Use "
            f"providers(territory={key!r}) to see what each one actually "
            f"covers, then call get_provider() with the specific key."
        )

    all_keys = sorted({e.key for e in _REGISTRY} | {a for e in _REGISTRY for a in e.aliases})
    near = get_close_matches(normalised, all_keys, n=5)
    hint = f" Did you mean: {', '.join(near)}?" if near else f" Known keys: {', '.join(all_keys)}."
    raise ProviderNotFoundError(f"No provider registered for {key!r}.{hint}")


# --------------------------------------------------------------------------- #
# Registry data
# --------------------------------------------------------------------------- #
#
# Every territory/credentials/licence fact below was checked against this
# SDK's own module docstrings and, where those were silent, against the
# provider's own live documentation (2026-07) - not copied from the design
# brief on trust. Two genuine gaps found doing that, not previously
# documented anywhere in this SDK:
#
# - Street Manager and DataVIA never state their territory in code or
#   README prose. England+Wales here is inferred by elimination (SRWR
#   exists specifically because Scotland runs its own separate register;
#   TrafficWatchNI exists specifically because Northern Ireland does too),
#   not an explicit in-repo or in-docs statement - flagged, not hidden.
# - D-TRO's territory is genuinely unstated even on the official gov.uk
#   D-TRO guidance page (checked live) - England+Wales here matches Street
#   Manager on the same reasoning, one inferential step further removed.
#
# NDW and Digitraffic's `licence=None` is the same "genuinely unconfirmed,
# not merely undocumented" case Autobahn's module already established -
# both checked live, 2026-07, no licence statement found on either portal.

_REGISTRY: list[ProviderEntry] = [
    ProviderEntry(
        key="streetmanager",
        name="Street Manager",
        description=(
            "England's statutory street works register - "
            "permits, works, inspections."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"England"}),  # inferred by elimination, see above
        scope_note=(
            "Not Scotland (see the srwr provider), Wales (see trafficwales), or Northern Ireland "
            "(see trafficwatchni)."
        ),
        credentials="Street Manager API account (email + password)",
        licence="N/A - access-controlled service, not open data",
        source_grade="register",
        _module="streetworks.streetmanager",
        _client_name="StreetManagerClient",
        import_line="from streetworks.streetmanager import StreetManagerClient",
    ),
    ProviderEntry(
        key="opendata",
        name="Street Manager Open Data",
        description=(
            "Push notifications (AWS SNS) of Street Manager works events - "
            "receive-only, same coverage as Street Manager itself."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"England"}),
        scope_note="Receive-only - you host the HTTPS endpoint AWS SNS pushes to.",
        credentials="A Street Manager Open Data subscription (no per-call auth)",
        licence="N/A - access-controlled service, not open data",
        source_grade="register",
        _module="streetworks.opendata",
        _client_name="handle",
        import_line="from streetworks.opendata import handle, parse_message",
    ),
    ProviderEntry(
        key="datavia",
        name="Geoplace DataVIA",
        description=(
            "England and Wales's National Street Gazetteer - the "
            "definitive street/highway reference layers."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"England", "Wales"}),  # inferred by elimination, see above
        credentials="DataVIA account (Basic auth or OAuth2 client credentials)",
        licence="N/A - access-controlled service, not open data",
        _module="streetworks.datavia",
        _client_name="DataViaClient",
        import_line="from streetworks.datavia import DataViaClient",
    ),
    ProviderEntry(
        key="dtro",
        name="DfT Digital Traffic Regulation Orders (D-TRO)",
        description=(
            "Legal traffic regulation orders - speed limits, closures, "
            "restrictions - as machine-readable data."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.NOT_APPLICABLE,
        territories=frozenset({"England", "Wales"}),  # one inferential step past Street Manager
        scope_note="A register of legal orders, not a works-progress register itself.",
        credentials="D-TRO API credentials (OAuth2 client id/secret + app id)",
        licence="N/A - access-controlled service, not open data",
        source_grade="register",
        _module="streetworks.dtro",
        _client_name="DTROClient",
        import_line="from streetworks.dtro import DTROClient",
    ),
    ProviderEntry(
        key="srwr",
        name="Scottish Road Works Register (SRWR)",
        description="Scotland's national road works register, as Open Data CSV extracts.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Scotland"}),
        credentials=None,
        licence="Open Government Licence v3.0 (OGL v3)",
        source_grade="register",
        aliases=frozenset({"scotland"}),
        _module="streetworks.srwr",
        _client_name="SRWRClient",
        import_line="from streetworks.srwr import SRWRClient",
    ),
    ProviderEntry(
        key="openusrn",
        name="OS Open USRN",
        description="Every Great British street (USRN) with geometry, from Ordnance Survey.",
        kind=Kind.STREETS,
        territories=frozenset({"England", "Scotland", "Wales"}),
        scope_note="Great Britain only - no Northern Ireland.",
        credentials=None,
        licence="Ordnance Survey OpenData (OGL v3)",
        _module="streetworks.openusrn",
        _client_name="OpenUSRNClient",
        import_line="from streetworks.openusrn import OpenUSRNClient",
    ),
    ProviderEntry(
        key="ban",
        name="BAN (Base Adresse Nationale)",
        description="France's national address base - ~25M addresses, no street register.",
        kind=Kind.ADDRESSES,
        territories=frozenset({"France"}),
        scope_note=(
            "An address base, not a street register like the UK gazetteers - streets/"
            "lieux-dits aren't published as their own entities, only recoverable as a "
            "derived grouping under addresses. See the module docstring."
        ),
        credentials=None,
        licence="Licence Ouverte / Open Licence 2.0 (Etalab)",
        # No "france" alias: France now has three providers (this one,
        # bisonfute, and bdtopo) - get_provider("france") resolves
        # through the territory-ambiguity path, naming all three.
        _module="streetworks.ban",
        _client_name="BANClient",
        import_line="from streetworks.ban import BANClient",
    ),
    ProviderEntry(
        key="bag",
        name="BAG (Basisregistratie Adressen en Gebouwen)",
        description="Netherlands' national addresses and buildings register.",
        kind=Kind.ADDRESSES,
        territories=frozenset({"Netherlands"}),
        scope_note=(
            "Street identity (openbare ruimte) is a real, versioned BAG object, "
            "but the bulk GeoPackage this SDK reads flattens it onto every address "
            "rather than giving it a table of its own. See the module docstring."
        ),
        credentials=None,
        licence="CC0 1.0 Universal",
        # No "netherlands" alias, for the same reason ndw's was removed:
        # two providers now cover the Netherlands.
        _module="streetworks.bag",
        _client_name="BAGClient",
        import_line="from streetworks.bag import BAGClient",
    ),
    ProviderEntry(
        key="kartverket",
        name="Kartverket (Matrikkelen Adresse + SSR stedsnavn)",
        description="Norway's national address register and official place names.",
        kind=Kind.ADDRESSES,
        territories=frozenset({"Norway"}),
        scope_note=(
            "Wide open and credential-free - unlike the vegvesen roadworks provider "
            "(same country, different agency, still blocked on credentials). Place "
            "names can carry several parallel official names (Norwegian, Sámi, Kven), "
            "each independently statused - see the module docstring. Classified as "
            "addresses for the address register (Matrikkelen Adresse); this client "
            "also wraps SSR, the official place-names register (settlements, "
            "natural features) - neither addresses nor streets, kept here rather "
            "than minting a third kind for one member, see the module docstring."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        # No "norway" alias: Norway now has three providers (this one,
        # vegvesen, and nvdb) - get_provider("norway") resolves through
        # the territory-ambiguity path, naming all three.
        _module="streetworks.kartverket",
        _client_name="KartverketClient",
        import_line="from streetworks.kartverket import KartverketClient",
    ),
    ProviderEntry(
        key="nvdb",
        name="NVDB (Nasjonal vegdatabank)",
        description="Norway's national road network - link topology and address placements.",
        kind=Kind.STREETS,
        territories=frozenset({"Norway"}),
        scope_note=(
            "The counterpart to kartverket's addresses. veglenkesekvenser (link "
            "sequences) are purely topological, no name of their own; naming/addressing "
            "lives in a separate Adresse road-object type carrying the same adressekode "
            "kartverket already models - a real join, not a name match, and one address "
            "can span several link sequences. See the module docstring."
        ),
        credentials=None,
        licence="Norsk lisens for offentlige data (NLOD) 1.0",
        # No "norway" alias, for the same reason kartverket's was removed:
        # three providers now cover Norway.
        _module="streetworks.nvdb",
        _client_name="NVDBClient",
        import_line="from streetworks.nvdb import NVDBClient",
    ),
    ProviderEntry(
        key="nwb",
        name="NWB (Nationaal Wegenbestand)",
        description=(
            "Netherlands' national road network - every named/numbered road, with geometry."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"Netherlands"}),
        scope_note=(
            "The counterpart to bag's addresses - a street is a *set* of wegvakken "
            "(road segments), joined back together via bag_orl, BAG's own street "
            "identifier, where present (not universal, not a name match). See the "
            "module docstring."
        ),
        credentials=None,
        licence="CC0 1.0 Universal",
        # No "netherlands" alias: the Netherlands now has three providers
        # (this one, ndw, and bag) - get_provider("netherlands") resolves
        # through the territory-ambiguity path, naming all three.
        _module="streetworks.nwb",
        _client_name="NWBClient",
        import_line="from streetworks.nwb import NWBClient",
    ),
    ProviderEntry(
        key="bdtopo",
        name="BD TOPO (IGN)",
        description=(
            "France's national road network (transport theme) - segments and named streets."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"France"}),
        scope_note=(
            "The counterpart to ban's addresses - troncon_de_route segments join to BAN "
            "via a real, stated identifier (identifiant_voie_ban), and voie_nommee gives "
            "a genuine named-street entity above them. WFS only - no bulk GeoPackage "
            "download route was found, see the module docstring."
        ),
        credentials=None,
        licence="Licence Ouverte / Open Licence ETALAB 2.0",
        # No "france" alias: France now has three providers (bisonfute,
        # ban, and this one) - get_provider("france") resolves through
        # the territory-ambiguity path, naming all three.
        _module="streetworks.bdtopo",
        _client_name="BDTopoClient",
        import_line="from streetworks.bdtopo import BDTopoClient",
    ),
    ProviderEntry(
        key="ndw",
        name="NDW (Nationale Databank Wegverkeersgegevens)",
        description="The Netherlands' national roadworks and traffic-events feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Netherlands"}),
        credentials=None,
        licence=None,
        licence_confirmed=False,  # checked live, 2026-07 - no statement found, see module docstring
        source_grade="operator",
        # No "netherlands" alias: the Netherlands now has two providers
        # (this one and the bag gazetteer) - get_provider("netherlands")
        # resolves through the territory-ambiguity path, same as "france".
        _module="streetworks.datex2",
        _client_name="NDWClient",
        import_line="from streetworks.datex2 import NDWClient",
    ),
    ProviderEntry(
        key="nationalhighways",
        name="National Highways",
        description="England's Strategic Road Network - motorways and major A-roads.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"England"}),
        administrative_area="National Highways",
        scope_note="The Strategic Road Network (SRN) only - not local roads.",
        credentials="Free subscription key (developer portal)",
        licence="N/A - access-controlled service, not open data",
        source_grade="operator",
        _module="streetworks.datex2",
        _client_name="NationalHighwaysClient",
        import_line="from streetworks.datex2 import NationalHighwaysClient",
    ),
    ProviderEntry(
        key="digitraffic",
        name="Digitraffic",
        description="Finland's national roadworks feed, from Fintraffic's open data platform.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Finland"}),
        credentials=None,
        licence=None,
        licence_confirmed=False,  # checked live, 2026-07 - no statement found, see module docstring
        source_grade="operator",
        aliases=frozenset({"finland"}),
        _module="streetworks.datex2",
        _client_name="DigitrafficClient",
        import_line="from streetworks.datex2 import DigitrafficClient",
    ),
    ProviderEntry(
        key="irca",
        name="IRCA / Vegagerðin",
        description=(
            "Iceland's national roadworks feed, from the Icelandic Road and "
            "Coastal Administration."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Iceland"}),
        credentials=None,
        licence=(
            "Free reuse, redistribution and commercial use permitted; mandatory "
            'attribution: "Based on information provided by the Icelandic Road '
            'and Coastal Administration (IRCA)"'
        ),
        source_grade="operator",
        aliases=frozenset({"iceland"}),
        _module="streetworks.datex2",
        _client_name="IcelandClient",
        import_line="from streetworks.datex2 import IcelandClient",
    ),
    ProviderEntry(
        key="bisonfute",
        name="Bison Futé / the DIRs",
        description="France's national (non-motorway-concession) roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"France"}),
        scope_note=(
            "The non-concessionary national road network (the state-run RRN) "
            "only - private autoroute concessionaires publish separately."
        ),
        credentials=None,
        licence="Licence Ouverte / Open Licence 2.0 (Etalab)",
        source_grade="operator",
        # No "france" alias: France now has three providers (this one,
        # ban, and bdtopo) - get_provider("france") resolves through
        # the territory-ambiguity path instead, same as "germany".
        _module="streetworks.datex2",
        _client_name="BisonFuteClient",
        import_line="from streetworks.datex2 import BisonFuteClient",
    ),
    ProviderEntry(
        key="dgt",
        name="DGT (Dirección General de Tráfico)",
        description="Spain's national roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.MULTI_AUTHORITY_INTERURBAN,
        territories=frozenset({"Spain"}),
        scope_note=(
            "National except Catalonia and the Basque Country, which run their "
            "own regional traffic authorities and publish separately. Not "
            "state-roads-only despite the name - real road-number prefixes "
            "reach several regional/provincial/insular authorities too (CV-/"
            "Comunidad Valenciana, M-/Madrid, Ma-/Me-/the Balearic insular "
            "councils, ~10 checked live), though never municipal streets. "
            "Confirmed live: overlaps with mallorca for at least some "
            "higher-impact Balearic works (matching road, km-range and end-"
            "date) - the two are complementary, not disjoint; never dedupe "
            "matches across them (or any two providers) - see mallorca's own "
            "scope_note and the README's 'never dedupe across providers' note."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="operator",
        # No "spain" alias: Spain now has two providers (this one and
        # mallorca) - get_provider("spain") resolves through the
        # territory-ambiguity path instead, same as "france"/"norway"/
        # "germany".
        _module="streetworks.datex2",
        _client_name="DGTClient",
        import_line="from streetworks.datex2.dgt import DGTClient",
    ),
    ProviderEntry(
        key="mallorca",
        name="Consell de Mallorca (IDEmallorca)",
        description="Mallorca's island roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.REGIONAL,
        territories=frozenset({"Spain"}),
        administrative_area="Consell de Mallorca",
        scope_note=(
            "Mallorca's own island-managed road network, in far more detail "
            "than DGT's national feed carries for the island (16-17 current "
            "records here vs. DGT's ~4-5). Confirmed live, not 'genuinely "
            "additive, not a duplicate' as first assumed: 2 of DGT's Balearic "
            "records match records here almost exactly on road, km-range and "
            "end-date (republication of the same real works, not a "
            "jurisdiction-boundary case - no independent reference field "
            "exists on DGT's side to attribute it otherwise, and the matched "
            "geometry sits within, not beside, the same work-zone span). Not "
            "a confirmed strict superset of DGT's Balearic entries either - "
            "at least 2 DGT Mallorca-area records had no live match here at "
            "check time (a data-lag artefact, not conclusively resolved). "
            "Never deduplicate matches against DGT (or any two providers) - "
            "see the README's standing note on this. Mallorca only, not a "
            "Balearic cluster - Menorca and Eivissa were checked and don't "
            "publish the same way (see the module docstring)."
        ),
        credentials=None,
        licence=(
            "Unconfirmed - checked the WFS capabilities (Fees/AccessConstraints "
            "both blank, not a deliberate statement), the IDEmallorca geoportal, "
            "and the Consell's general legal notice; no explicit reuse terms found"
        ),
        source_grade="operator",
        _module="streetworks.ogc.mallorca",
        _client_name="MallorcaClient",
        import_line="from streetworks.ogc.mallorca import MallorcaClient",
    ),
    ProviderEntry(
        key="sct",
        name="Servei Català de Trànsit",
        description="Catalonia's real-time road incidents feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.MULTI_AUTHORITY_INTERURBAN,
        territories=frozenset({"Spain"}),
        administrative_area="Servei Català de Trànsit",
        scope_note=(
            "Fills the larger of DGT's two documented exclusions (DGT "
            "explicitly omits Catalonia and the Basque Country). Real "
            "road-number prefixes span the Generalitat's own network (C-) "
            "and all four provincial councils' networks (B-/BV-/BP-, "
            "GI-/GIV-/GIP-, T-/TV-/TP-, L-/LV-) and some state roads within "
            "Catalan territory (N-/A-/AP-) - the same multi-authority shape "
            "as DGT's own real data. No overlap with DGT checked (DGT "
            "excludes Catalonia entirely, so none is expected), but never "
            "deduplicate matches across providers regardless - see the "
            "README's standing note. No start/end validity window exists "
            "anywhere in this feed - a genuinely real-time, continuously-"
            "refreshed current-state feed, not a works schedule; "
            "date_confidence is always unknown, see the module docstring."
        ),
        credentials=None,
        licence=(
            "Llicència oberta d'ús d'informació - Catalunya (reuse, "
            "distribution and derivative works permitted worldwide, "
            "attribution required: \"Generalitat de Catalunya. Departament "
            "d'Interior\") - confirmed live via the dataset's own metadata "
            "and administraciodigital.gencat.cat's licence page"
        ),
        source_grade="operator",
        _module="streetworks.sct",
        _client_name="SCTClient",
        import_line="from streetworks.sct import SCTClient",
    ),
    ProviderEntry(
        key="euskadi",
        name="Dirección de Tráfico del Gobierno Vasco",
        description="Basque Country roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.MULTI_AUTHORITY_INTERURBAN,
        territories=frozenset({"Spain"}),
        scope_note=(
            "Fills the other of DGT's two documented exclusions (DGT "
            "explicitly omits Catalonia - see sct - and the Basque "
            "Country). DATEX II v1.0, the oldest schema version in this "
            "SDK - reading it surfaced a real, additive parser fix "
            "(lower-case 'tpeglinearLocation', not the v2/v3 "
            "'tpegLinearLocation' - see the module docstring), confirmed "
            "via a live regression not to affect any other DATEX adapter. "
            "Coordinate coverage is genuinely partial (~42% in one live "
            "pull) - the rest state location via Alert-C + a road number "
            "and distance only, no other Spanish/DATEX adapter in this "
            "SDK has less than 100%. Real road numbers span the state "
            "network (N-/AP-) and all three Diputación Foral networks "
            "(GI-/Gipuzkoa, BI-/Bizkaia, Araba's own) - the same multi-"
            "authority shape as DGT's and SCT's own real data. Province "
            "(administrativeArea) is a real per-record field, exposed via "
            "the euskadi_provinces() helper - a real 'Desconocida' "
            "(unknown) placeholder is excluded, not treated as a name."
        ),
        credentials=None,
        licence=(
            "No licence - No contract, stated literally by the publisher "
            "on Spain's national NAP - genuinely more restrictive than an "
            "unconfirmed licence (absence of a licence grants no "
            "permission; it is not the same as 'free to use'). Probably "
            "reusable in practice under Spain's PSI/open-data "
            "transposition, but that is not the same as a granted "
            "licence - confirm your own rights before relying on this"
        ),
        # licence_confirmed=True (the default): the "No licence - No
        # contract" statement itself is confirmed, verbatim, on the NAP
        # dataset page - this is a confirmed absence, not an unconfirmed
        # guess, see module docstring for why that distinction matters.
        source_grade="operator",
        _module="streetworks.datex2",
        _client_name="EuskadiClient",
        import_line="from streetworks.datex2.euskadi import EuskadiClient",
    ),
    ProviderEntry(
        key="belgium",
        name="Verkeerscentrum Vlaanderen",
        description="Flanders' (not all-Belgium's) roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.REGIONAL,
        territories=frozenset({"Belgium"}),
        scope_note=(
            "Flanders only - confirmed live (supplierIdentification/"
            "nationalIdentifier states \"BETICV\", Belgium Traffic Information "
            "Centre Vlaanderen). Wallonia publishes its own separate feed, not "
            "wrapped here; Brussels wasn't checked. Coordinates are real "
            "EPSG:31370 (Belgian Lambert 72), not WGS84 - pass "
            "streetworks.datex2.belgium.CRS to from_datex2()."
        ),
        credentials=None,
        licence=(
            "No permissive licence - transportdata.be's own terms of use "
            "prohibit commercial redistribution to third parties"
        ),
        source_grade="operator",
        aliases=frozenset({"flanders"}),
        _module="streetworks.datex2",
        _client_name="BelgiumClient",
        import_line="from streetworks.datex2.belgium import BelgiumClient",
    ),
    ProviderEntry(
        key="luxembourg",
        name="Ponts et Chaussées",
        description="Luxembourg's national roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Luxembourg"}),
        credentials=None,
        licence="CC0 1.0 Universal (Public Domain Dedication)",
        source_grade="operator",
        _module="streetworks.datex2",
        _client_name="LuxembourgClient",
        import_line="from streetworks.datex2.luxembourg import LuxembourgClient",
    ),
    ProviderEntry(
        key="bulgaria",
        name="Road Infrastructure Agency (LIMA)",
        description="Bulgaria's national roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Bulgaria"}),
        scope_note=(
            "The NAP-listed host (lima.api.bg) is unreachable - the real, "
            "working host is datasheet.api.bg, confirmed live. Fetches the "
            "'Short-term Road Construction' (r03) dataset, confirmed live to "
            "be a strict superset of the other two roadworks categories "
            "('Closed Roads'/r01, 'Closed Roadways'/r02)."
        ),
        credentials=None,
        licence=(
            "Unconfirmed - no licence text on the reachable host "
            "(datasheet.api.bg); the real terms page (lima.api.bg) could not "
            "be reached directly to verify secondhand claims"
        ),
        source_grade="operator",
        _module="streetworks.datex2",
        _client_name="BulgariaClient",
        import_line="from streetworks.datex2.bulgaria import BulgariaClient",
    ),
    ProviderEntry(
        key="vegvesen",
        name="Statens vegvesen",
        description="Norway's national roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Norway"}),
        scope_note=(
            "Phase 2 confirmed (2026-07-30) against a real credentialed "
            "pull (844 real roadworks situations, ~24 MB) - no IP "
            "allow-listing needed, HTTP Basic confirmed correct. Real "
            "coordinates are genuinely mixed CRS within the same feed "
            "(UTM zone 33N/EPSG:25833 and WGS84) - now resolved "
            "honestly, per record: use "
            "streetworks.common.from_vegvesen (not from_datex2 "
            "directly), which resolves each record's declared srsName "
            "plus its own value range via "
            "streetworks.common._crs.resolve_coordinate_crs (axis order "
            "by magnitude, never declared/positional order; no silent "
            "reprojection). The real declared/inferred/corrected split "
            "isn't hardcoded here - run scripts/smoke_test.py for this "
            "run's actual counts."
        ),
        credentials="Statens vegvesen API credentials (HTTP Basic, confirmed; Bearer untested)",
        licence="NLOD 1.0 (Norwegian Licence for Open Government Data)",
        source_grade="operator",
        # No "norway" alias: Norway now has three providers (this one,
        # kartverket, and nvdb) - get_provider("norway") resolves through
        # the territory-ambiguity path instead, same as "france".
        _module="streetworks.datex2",
        _client_name="VegvesenClient",
        import_line="from streetworks.datex2 import VegvesenClient",
    ),
    ProviderEntry(
        key="trafikverket",
        name="Trafikverket",
        description="Sweden's national roadworks-relevant deviations feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Sweden"}),
        scope_note=(
            "Phase 1 scaffold - endpoint/auth/schema-version confirmed live "
            "via an invalid-key probe, but never run against real "
            "authenticated Swedish data, see below."
        ),
        credentials="Trafikverket API key (free self-service registration)",
        licence="CC0 1.0 Universal (Public Domain Dedication)",
        source_grade="operator",
        verified=False,
        _module="streetworks.datex2",
        _client_name="TrafikverketClient",
        import_line="from streetworks.datex2 import TrafikverketClient",
    ),
    ProviderEntry(
        key="vejdirektoratet",
        name="Vejdirektoratet",
        description="Denmark's national roadworks feed (Dataudveksleren).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Denmark"}),
        scope_note=(
            "Phase 1 scaffold - DATEX II 3.2 schema and the open metadata "
            "catalogue confirmed live, but the credential-gated data pull "
            "itself never exercised, see below."
        ),
        credentials=(
            "Dataudveksleren HTTP Basic Auth username/password + a "
            "per-dataset pull URL, both issued at registration"
        ),
        licence="CC BY 4.0",
        source_grade="operator",
        verified=False,
        _module="streetworks.datex2",
        _client_name="VejdirektoratetClient",
        import_line="from streetworks.datex2 import VejdirektoratetClient",
    ),
    ProviderEntry(
        key="nsw",
        name="Transport for NSW - Live Traffic Hazards",
        description="New South Wales roadwork hazards feed (Australia).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Australia", "New South Wales"}),
        administrative_area="Transport for NSW",
        scope_note=(
            "Phase 2 confirmed (2026-07-30) against a real credentialed "
            "pull (363 real roadwork + 19 real majorevent features) - "
            "found and fixed one real bug (endpoint paths are "
            "roadwork/open-style, not roadwork-open.json-style, see "
            "module docstring). Predominantly state roads, but a real "
            "~1.7% minority (6/363 in that pull) are isLocalRoad='Local "
            "road' - council works aren't fully siloed away, just rare "
            "in this feed."
        ),
        credentials="TfNSW API Gateway key (free self-service registration)",
        licence="CC BY 4.0",
        source_grade="operator",
        _module="streetworks.au",
        _client_name="NswLiveTrafficClient",
        import_line="from streetworks.au import NswLiveTrafficClient",
    ),
    ProviderEntry(
        key="vic",
        name="Department of Transport and Planning - Planned Disruptions",
        description="Victoria planned road disruptions feed (Australia).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Australia", "Victoria"}),
        administrative_area="Department of Transport and Planning",
        scope_note=(
            "Phase 2 confirmed (2026-07-30) against a real credentialed "
            "pull (500 real features on one page). Found one real design "
            "mistake in this module's own converter, since fixed: a "
            "GeometryCollection's LineString can span an entire route "
            "(~150km real example) rather than the disruption's precise "
            "extent, so only the Point is used, see module docstring. "
            "rmaClass is a real small coded set (FW/AO/MU/AH/PR observed "
            "live) - DTP's own remit is stated as arterials/freeways "
            "only, but 'MU' may mean municipal (62/500 real features, "
            "~12%) - not confirmed, so this scope may be narrower than "
            "STRATEGIC implies."
        ),
        credentials="Transport Victoria Open Data Hub subscription key (free)",
        licence="CC BY 4.0",
        source_grade="operator",
        _module="streetworks.au",
        _client_name="VicDisruptionsClient",
        import_line="from streetworks.au import VicDisruptionsClient",
    ),
    ProviderEntry(
        key="wa",
        name="Main Roads WA - WebEOC Roadworks",
        description="Western Australia roadworks feed (Australia), over an ArcGIS Feature Service.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Australia", "Western Australia"}),
        administrative_area="Main Roads Western Australia",
        scope_note=(
            "Credential-free, shipped live-verified with a real fixture "
            "from day one (227 real records, one live pull) - unlike "
            "NSW/Victoria, never a Credentials-wanted scaffold. A real "
            "~12.3% minority (28/227) states Road as the literal sentinel "
            "'LOCAL ROAD', not a real road name - LocalRoadName carries "
            "the real name in exactly those records; network_scope stays "
            "UNKNOWN rather than promoted, since that minority is far "
            "larger than NSW's ~1.7%. WorkStatus is a real field, "
            "confirmed always empty (0/227) - no live signal to grade a "
            "site past DateConfidence.ESTIMATED. Reuses the shared "
            "streetworks.arcgis.client.ArcGISFeatureClient for pagination, "
            "not a bespoke implementation - see module docstring."
        ),
        credentials=None,
        licence="CC BY 4.0",
        source_grade="operator",
        _module="streetworks.au",
        _client_name="WaMainRoadsClient",
        import_line="from streetworks.au import WaMainRoadsClient",
    ),
    ProviderEntry(
        key="qld",
        name="QLDTraffic Events (TMR)",
        description="Queensland roadworks feed (Australia), one typed feed over every event_type.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Australia", "Queensland"}),
        administrative_area=None,
        scope_note=(
            "Credential-free via a real, globally-shared public API key "
            "published in TMR's own spec - never a Credentials-wanted "
            "scaffold. Confirmed live (458 real events, 244 real "
            "Roadworks, 2026-08-01): two of the spec's own claims are "
            "wrong (geometry.type is NOT always GeometryCollection - only "
            "2.2% of real features are; the source_name enum has two real "
            "undocumented values, Asignit/MBRC). Real coordinates are "
            "EPSG:7844 (GDA2020), not WGS84 - labelled honestly, not "
            "relabelled. 88.5% of real Roadworks events have no Point at "
            "all, only line geometry - carried through as the real "
            "affected-road extent rather than dropped (a deliberate "
            "departure from Victoria's own precedent), since dropping it "
            "would leave most records with no geometry. administrative_area "
            "is per-record from source.provided_by (17 distinct real "
            "values: TMR, a private tollway operator, and over a dozen "
            "Queensland councils) - richer than a hardcoded value, but "
            "only a real minority of Queensland's local government areas "
            "are represented, so network_scope stays UNKNOWN rather than "
            "promoted. See module docstring."
        ),
        credentials=None,
        licence="CC BY 4.0 AU",
        source_grade="operator",
        _module="streetworks.au",
        _client_name="QldTrafficClient",
        import_line="from streetworks.au import QldTrafficClient",
    ),
    ProviderEntry(
        key="sa",
        name="Traffic SA - DIT Roadworks",
        description="South Australia roadworks feed (Australia), over an ArcGIS MapServer.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Australia", "South Australia"}),
        administrative_area="Department for Infrastructure and Transport",
        scope_note=(
            "Phase 1 scaffold, genuinely blocked on two access gates, not "
            "just credentials: the query endpoint is token-gated "
            "(location.sa.gov.au/arcgis/tokens/ - self-service vs gated by "
            "DIT is unresolved), and maps.sa.gov.au CloudFront-blocks some "
            "countries' network egress outright. No real feature has ever "
            "been retrieved. The layer's real field list (a genuine live "
            "?f=json pull, ground truth) includes ROAD_NO/GIS_LINK_ID - "
            "candidate stated-identifier join keys to a road register, "
            "which would be a first for this AU cluster if confirmed - but "
            "population and join semantics are unverified, so they are not "
            "wired into street_ref. See module docstring."
        ),
        credentials="ArcGIS token (location.sa.gov.au/arcgis/tokens/)",
        licence="CC BY 4.0",
        source_grade="operator",
        verified=False,
        _module="streetworks.au",
        _client_name="TrafficSaClient",
        import_line="from streetworks.au import TrafficSaClient",
    ),
    ProviderEntry(
        key="act",
        name="Temporary Traffic Management (TTM) - Roads ACT",
        description="ACT road-closures feed (Australia), the only municipal-level AU coverage.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Australia", "Australian Capital Territory"}),
        administrative_area="Roads ACT",
        scope_note=(
            "Confirmed live (2026-08-01, 98 real records) - credential-"
            "free, never a Credentials-wanted scaffold. The only AU "
            "provider reaching genuine municipal/local streets - the ACT "
            "has no separate local-government tier, so Roads ACT's own "
            "feed IS the whole real network, unlike every other AU "
            "provider (which only ever reach a state authority's own "
            "roads, sometimes with a small confirmed local-road minority). "
            "A real correction to the source investigation: this is "
            "ArcGIS underneath (the dataACT Socrata catalogue entry is a "
            "plain link/pointer), not a new Socrata client shape. "
            "Licence is CC BY-SA 4.0 (Share-Alike), distinct from every "
            "other AU provider's plain CC-BY. See module docstring."
        ),
        credentials=None,
        licence="CC BY-SA 4.0",
        source_grade="operator",
        _module="streetworks.au",
        _client_name="ActTtmClient",
        import_line="from streetworks.au import ActTtmClient",
    ),
    ProviderEntry(
        key="tas",
        name="Roadworks - State Roads (Department of State Growth)",
        description="Tasmania state-road roadworks feed (Australia), the only AU one with lines.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Australia", "Tasmania"}),
        administrative_area="Department of State Growth",
        scope_note=(
            "Confirmed live (2026-08-01, 10 real records - genuinely this "
            "small) - credential-free, never a Credentials-wanted "
            "scaffold, but licence is genuinely unconfirmed (the ArcGIS "
            "item's own portal metadata states both licenseInfo and "
            "accessInformation as null) - shipped anyway on the same "
            "openly-queryable basis as streetworks.arcgis.jersey, not "
            "blocked the way SA is. State roads only, confirmed live with "
            "zero non-state contamination (EVENT_TYPE=='Roadworks' on "
            "10/10 real records, no incident mix). Real line geometry, "
            "not points - the only AU provider where this is true. Native "
            "CRS is GDA94/MGA zone 55, not Web Mercator - deliberately "
            "does not reuse WA/SA's closed-form reprojection guard, since "
            "the wrong formula would silently produce wrong coordinates "
            "rather than none at all. See module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        _module="streetworks.au",
        _client_name="TasRoadworksClient",
        import_line="from streetworks.au import TasRoadworksClient",
    ),
    ProviderEntry(
        key="nt",
        name="Road Report NT",
        description="NT road-conditions service (Australia) - no published API, documented only.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Australia", "Northern Territory"}),
        administrative_area="Department of Infrastructure, Planning and Logistics",
        scope_note=(
            "Investigated and registered honestly-unavailable, not "
            "silently skipped - a different tier from Trafikverket/"
            "Vejdirektoratet/SA, all of which are blocked on access to a "
            "real, published interface. Road Report NT has no published "
            "REST/GeoJSON API at all: its real backend is an undocumented "
            "SignalR hub ('roadsReportingHub', confirmed live by "
            "inspecting the site's own minified Angular bundle - not a "
            "published spec). RoadReportNtClient() always raises "
            "ProviderUnavailableError rather than encoding reverse-"
            "engineered hub internals as a stable contract. Statewide "
            "NT-Government roads (councils excluded); a road-condition "
            "system (closures/flooding/weight restrictions) where "
            "roadworks is a minor subset, the weakest real works-fit in "
            "this SDK. See module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        verified=False,
        _module="streetworks.au",
        _client_name="RoadReportNtClient",
        import_line="from streetworks.au import RoadReportNtClient",
    ),
    ProviderEntry(
        key="maproad",
        name="MapRoad Roadworks Licensing",
        description="Ireland's national roadworks licence register - a real API, gated, not open.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Ireland"}),
        administrative_area="Road Management Office (RMO) / LGMA",
        scope_note=(
            "Investigated and registered honestly-unavailable, not "
            "silently skipped - a different tier from Trafikverket/"
            "Vejdirektoratet/SA (blocked on access to a real, published "
            "interface) and a different reason from NT (which has no "
            "published API at all). MapRoad has a real, government-"
            "catalogued API (datacatalogue.gov.ie: 'API Available: Yes') "
            "but the same listing states 'Open Data: No', 'Data Sharing: "
            "Yes', 'Personal Data: Yes' together - a formal, GDPR-gated "
            "data-sharing arrangement, not a self-service developer key. "
            "No published endpoint/schema/auth mechanism for a read path "
            "was found anywhere. TII's own DATEX II feed (data.tii.ie) "
            "was checked and ruled out first - its real dataset catalogue "
            "carries no roadworks/Situation publication at all, only "
            "travel times/weather/VMS/VDS/collision/traffic-count data. "
            "MapRoadClient() always raises ProviderUnavailableError "
            "rather than guessing an unpublished private contract. Real "
            "coverage would be national AND local roads (TII's own "
            "national-road consents route through it; local authorities' "
            "regional/local consents also do) - the richest real scope of "
            "any Irish roadworks source found, if it were reachable. See "
            "module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        verified=False,
        _module="streetworks.maproad",
        _client_name="MapRoadClient",
        import_line="from streetworks.maproad import MapRoadClient",
    ),
    ProviderEntry(
        key="greece",
        name="Greece",
        description="No roadworks source exists - Greece's NAP carries only POI/sensor data.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Greece"}),
        scope_note=(
            "Investigated and registered honestly-unavailable, not "
            "silently skipped - the same tier as Road Report NT (no "
            "roadworks source at all, as opposed to Trafikverket/"
            "Vejdirektoratet/SA/MapRoad, all of which have a real "
            "interface merely blocked). Greece's real NAP (nap.gov.gr, "
            "confirmed as the official MMTIS/RTTI/SRTI/SSTP NAP per the "
            "European Commission's own October 2025 NAP list) is a "
            "decentralised metadata catalogue of POI/sensor data (truck "
            "parking, refuelling points, KTEL bus/ferry timetables, "
            "Thessaloniki floating car data, toll-operator VDS/VMS/"
            "weather from Attiki Odos/Egnatia Odos/the Hellastron "
            "network) - confirmed via its own real dataset titles to "
            "carry no roadworks or DATEX II Situation dataset at all. A "
            "second, independent reason: the portal itself is currently "
            "unreachable, confirmed live (2026-08-03, a real 502 Bad "
            "Gateway on its own CKAN backend, both on the dataset list "
            "and its /api/3/action/package_list endpoint; its imet.gr "
            "mirror hangs at the TLS handshake stage). "
            "GreeceClient() always raises ProviderUnavailableError "
            "rather than guessing. Even a best-case future toll-operator "
            "feed would only ever be motorway-concession-only, "
            "fragmented per operator - not a genuine national source. "
            "See module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        verified=False,
        _module="streetworks.greece",
        _client_name="GreeceClient",
        import_line="from streetworks.greece import GreeceClient",
    ),
    ProviderEntry(
        key="autobahn",
        name="Autobahn GmbH",
        description="Germany's national motorway roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.MOTORWAY,
        territories=frozenset({"Germany"}),
        administrative_area="Autobahn GmbH",
        scope_note=(
            "National motorways only - state/regional roads are separate "
            "(see the hamburg/brandenburg/saxony providers)."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,  # checked four sources, none confirm - see module docstring
        source_grade="operator",
        _module="streetworks.autobahn",
        _client_name="AutobahnClient",
        import_line="from streetworks.autobahn import AutobahnClient",
    ),
    ProviderEntry(
        key="hamburg",
        name="Hamburg",
        description="Hamburg's state roadworks feed (Baustellen).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Germany"}),
        administrative_area="Hamburg",
        credentials=None,
        licence="Datenlizenz Deutschland - Namensnennung - Version 2.0 (dl-de/by-2-0)",
        source_grade="operator",
        _module="streetworks.ogc.germany",
        _client_name="GermanRoadworksClient",
        import_line='from streetworks.ogc.germany import GermanRoadworksClient # .fetch("Hamburg")',
    ),
    ProviderEntry(
        key="brandenburg",
        name="Brandenburg",
        description="Brandenburg's state roadworks feed (Baustelleninfo).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Germany"}),
        administrative_area="Brandenburg",
        credentials=None,
        licence="Datenlizenz Deutschland - Namensnennung - Version 2.0 (dl-de/by-2-0)",
        source_grade="operator",
        _module="streetworks.ogc.germany",
        _client_name="GermanRoadworksClient",
        import_line=(
            'from streetworks.ogc.germany import GermanRoadworksClient # .fetch("Brandenburg")'
        ),
    ),
    ProviderEntry(
        key="saxony",
        name="Saxony (Sachsen)",
        description=(
            "Saxony's state roadworks feed (Baustelleninformationen), "
            "district and municipal included."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Germany"}),
        administrative_area="Sachsen",
        scope_note=(
            "Coordinates are EPSG:25833 (UTM33N), not WGS84 - see the module "
            "docstring. Genuinely broader than its hamburg/brandenburg "
            "siblings, which are state-network-only - Saxony aggregates "
            "district and municipal roadworks alongside state roads."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="operator",
        aliases=frozenset({"sachsen"}),
        _module="streetworks.ogc.germany",
        _client_name="GermanRoadworksClient",
        import_line='from streetworks.ogc.germany import GermanRoadworksClient # .fetch("Sachsen")',
    ),
    ProviderEntry(
        key="berlin",
        name="Berlin (VIZ)",
        description="Berlin's city-wide traffic-information-centre Baustellen/Sperrungen feeds.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Germany"}),
        administrative_area="Land Berlin - VIZ",
        scope_note=(
            "Confirmed live (2026-08-08, 373 + 240 real records across "
            "two feeds) - credential-free, never a Credentials-wanted "
            "scaffold. The largest remaining German gap this cluster had "
            "- Berlin is a city-state Land entirely surrounded by the "
            "already-covered brandenburg. Two public GeoJSON feeds "
            "(Landesmeldestelle/tic3, Verkehrsredaktion/daten), not one "
            "- the source brief assumed Verkehrsredaktion is a detail-"
            "enriched subset of Landesmeldestelle, but live data via the "
            "real lms_id<->id join key shows only 104 of ~215-313 real "
            "roadworks records overlap; each feed has genuine unique "
            "content the other lacks. iter_roadworks() merges both via "
            "that verified key rather than picking one as primary. "
            "source_grade=traveller_info (VIZ is a traffic-information/"
            "editorial source, not a statutory register, unlike "
            "streetmanager/nycdot/chicagodot/paris). Comprehensive "
            "city-wide streets, not state-network-only like hamburg/"
            "brandenburg. See module docstring."
        ),
        credentials=None,
        licence="Datenlizenz Deutschland - Namensnennung - Version 2.0 (dl-de/by-2-0)",
        licence_confirmed=True,
        source_grade="traveller_info",
        _module="streetworks.berlin",
        _client_name="BerlinClient",
        import_line="from streetworks.berlin import BerlinClient",
    ),
    ProviderEntry(
        key="wzdx",
        name="WZDx (Work Zone Data Exchange)",
        description="The US standard for work-zone data, published independently by ~40+ agencies.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.VARIES_BY_FEED,
        territories=frozenset({"USA"}),
        scope_note=(
            "Not one provider's coverage - a schema ~40+ agencies publish "
            "independently. streetworks.wzdx.list_feeds() reads the real "
            "USDOT feed registry (41 real rows, confirmed live 2026-08-02) "
            "and defaults to wzdx_only=True - excluding real CWZ (a "
            "different ITE schema, version=='CWZ 1.0') and sub-3.1/"
            "unparseable-version entries, a documented skip rather than a "
            "mis-parse. Two real auth tiers: ~27/41 need no key at all "
            "(511NY/NYSDOT confirmed live end-to-end, the first concrete "
            "verified feed - 6,895 real events, MultiPoint geometry); "
            "~13/41 state needapikey=true with a real apikeyurl for "
            "signup, the caller's own key to supply. Not US-only - a "
            "real, active Quebec City (Canada) feed is registered too, so "
            "territory/administrative_area are per-feed "
            "(from_wzdx(..., territory=..., administrative_area=...)), "
            "never hardcoded. Confirmed live 2026-08-03: fldot (Florida, "
            "keyless, 17,932 real events) and austin (Texas, keyless, "
            "CC0, 100% work-zone - the cleanest feed found in this SDK). "
            "No statewide California feed exists at all (only mtc/Bay "
            "Area MTC, keyed); Texas's own statewide feed also needs a "
            "key. NYC DOT's own local-street works (see 'nycdot') and "
            "Chicago's (see 'chicagodot') are separate Socrata providers, "
            "not in this registry at all. See streetworks.wzdx.registry's "
            "own module docstring."
        ),
        credentials=None,
        licence="Varies by publishing agency - not independently confirmed per-agency",
        source_grade="operator",
        aliases=frozenset({"usa", "us"}),
        _module="streetworks.wzdx",
        _client_name="WZDxClient",
        import_line="from streetworks.wzdx import WZDxClient",
    ),
    ProviderEntry(
        key="nycdot",
        name="NYC DOT Street Construction Permits",
        description="New York City's street-opening permit register, over NYC Open Data.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        # Both "USA" (country-level, matching wzdx's own convention - this
        # is still a real US provider) and "New York City" (this provider's
        # actual real reach is city-scoped, not state or national - unlike
        # wzdx's federated multi-state coverage) - see providers(territory=
        # "New York City") and examples/roadworks_world_map.py's own city
        # centroid.
        territories=frozenset({"USA", "New York City"}),
        administrative_area="New York City Department of Transportation (DOT)",
        scope_note=(
            "Confirmed live (2026-08-02, 3,798,494 real rows total) - "
            "credential-free, never a Credentials-wanted scaffold. The "
            "local follow-on WZDx's own registry harvest deliberately "
            "scoped out - New York State (511NY, see wzdx) covers state "
            "highways, NYC DOT is a separate authority publishing a "
            "separate shape entirely, not WZDx. A genuine permit "
            "register - source_grade=register, this SDK's second after "
            "England's Street Manager and the first in the US. No LION "
            "segmentid or any street-register identifier anywhere in "
            "the real 39-column schema - street_ref is never populated, "
            "confirmed by direct schema inspection, not a guess. Real "
            "geometry exists anyway (wkt, 80.5% of rows, native SR "
            "EPSG:2263/NAD83 New York Long Island, inferred not stated, "
            "never reprojected). iter_roadworks() filters to two "
            "evidenced series (STREET OPENING PERMIT, DOT IN-HOUSE "
            "PAVING AND MILLING); BUILDING OPERATION PERMIT is "
            "genuinely mixed at a finer level and deliberately excluded "
            "rather than guessed at. Licence unconfirmed - NYC Open "
            "Data states no formal reuse licence. See module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.nycdot",
        _client_name="NycDotClient",
        import_line="from streetworks.nycdot import NycDotClient",
    ),
    ProviderEntry(
        key="chicagodot",
        name="Chicago CDOT Street Closures",
        description="Chicago's street-closure permit register, over Chicago's Open Data portal.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        # Both "USA" and "Chicago" (this provider's real reach is
        # city-scoped) - see providers(territory="Chicago") and
        # examples/roadworks_world_map.py's own city centroid, the same
        # pattern nycdot already established.
        territories=frozenset({"USA", "Chicago"}),
        administrative_area="City of Chicago Department of Transportation (CDOT)",
        scope_note=(
            "Confirmed live (2026-08-03, 466,829 real rows in the "
            "Street Closures view) - credential-free, never a "
            "Credentials-wanted scaffold. This SDK's second US city "
            "permit register after nycdot, source_grade=register. The "
            "source brief's own primary dataset id (6fd2-pzze) is dead - "
            "a genuinely empty schema despite 2.3M historical rows - the "
            "real, current dataset is jdis-5sry (Transportation "
            "Department Permits - Street Closures), a Chicago-maintained "
            "view already filtered to 3 of 11 real applicationtype "
            "values. That pre-filter alone isn't sufficient though - a "
            "finer worktype field still mixes in real non-roadworks "
            "activity (BlockParty, Festival, Filming, Parade, ...), so "
            "iter_roadworks() filters on 7 confirmed roadworks worktypes "
            "instead. No segment/street identifier anywhere in the real "
            "46-column schema - street_ref is never populated. Cleaner "
            "than nycdot in two real ways: native WGS84 GeoJSON Point "
            "geometry (no WKT/State-Plane CRS question) and dates, both "
            "populated on 99.94% of real rows. Licence unconfirmed - the "
            "dataset states only 'See Terms of Use'. See module "
            "docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.chicagodot",
        _client_name="ChicagoDotClient",
        import_line="from streetworks.chicagodot import ChicagoDotClient",
    ),
    ProviderEntry(
        key="paris",
        name="Paris Chantiers (Ville de Paris)",
        description="Paris's own occupation-permit register for street/public-space worksites.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        # Both "France" (country-level, matching bisonfute's own
        # convention - a real, distinct, municipal-not-national
        # provider, never deduplicated against it) and "Paris"
        # (city-scoped real reach) - see providers(territory="Paris")
        # and examples/roadworks_world_map.py's own city centroid, the
        # same pattern nycdot/chicagodot already established.
        territories=frozenset({"France", "Paris"}),
        administrative_area="Ville de Paris - Direction de la Voirie et des Déplacements",
        scope_note=(
            "Confirmed live (2026-08-06, 4,707 real records) - "
            "credential-free, never a Credentials-wanted scaffold. This "
            "SDK's third municipal permit register after nycdot/"
            "chicagodot, source_grade=register - and the first on "
            "OpenDataSoft (the French/EU Socrata-equivalent), built "
            "bespoke rather than via a shared client, the same sequence "
            "that produced streetworks.socrata's SodaClient (bespoke "
            "first, extracted only when a second same-platform provider "
            "needs the identical shape). The real chantier_categorie "
            "field has exactly 3 values live: city works and network-"
            "operator works are genuine roadworks; 'Tiers (travaux sur "
            "batiment)' (private building works/scaffolding, 2,918 of "
            "4,707 real rows) is excluded by iter_roadworks(). Geometry "
            "is already WGS84 (geo_shape/geo_point_2d) despite the "
            "underlying Paris data being surveyed in Lambert 93 - "
            "OpenDataSoft reprojects on the way out, so no CRS transform "
            "is needed here. No street/segment identifier field - "
            "street_ref is never populated, the same nycdot/chicagodot/"
            "Roads-ACT discipline. Licence is ODbL 1.0 (Open Database "
            "License, share-alike), confirmed from the dataset's own "
            "metadata - a stronger documentation case than nycdot/"
            "chicagodot's own unconfirmed-licence tier, and the same "
            "share-alike nuance streetworks.au.act's CC BY-SA licence "
            "carries relative to its plain-CC-BY siblings. See module "
            "docstring."
        ),
        credentials=None,
        licence="ODbL 1.0",
        licence_confirmed=True,
        source_grade="register",
        _module="streetworks.paris",
        _client_name="ParisClient",
        import_line="from streetworks.paris import ParisClient",
    ),
    ProviderEntry(
        key="trafficwatchni",
        name="TrafficWatchNI",
        description=(
            "Northern Ireland's roadworks/incidents feed, from DfI's "
            "Traffic Information and Control Centre."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Northern Ireland"}),
        scope_note=(
            "Genuinely two-tier, not a single scope: trunk roads and "
            "motorways NI-wide (the STRATEGIC classification here), but "
            "*all* roads within Greater Belfast specifically - see the "
            "client's own BELFAST feed variant. Query the right feed for "
            "the area in question rather than assuming NI-wide strategic-"
            "only coverage everywhere."
        ),
        credentials=None,
        licence="Attribution required (DfI TICC) - no named reuse licence stated by the publisher",
        source_grade="traveller_info",
        _module="streetworks.trafficwatchni",
        _client_name="TrafficWatchNIClient",
        import_line="from streetworks.trafficwatchni import TrafficWatchNIClient",
    ),
    ProviderEntry(
        key="trafficwales",
        name="Traffic Wales",
        description="Wales's motorway/trunk-road roadworks feed, from the Welsh Government.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Wales"}),
        credentials=None,
        licence=(
            "Attribution required (Traffic Wales) - no named reuse "
            "licence stated by the publisher"
        ),
        source_grade="traveller_info",
        _module="streetworks.trafficwales",
        _client_name="TrafficWalesClient",
        import_line="from streetworks.trafficwales import TrafficWalesClient",
    ),
    ProviderEntry(
        key="cciss",
        name="CCISS (Centro di Coordinamento Informazioni sulla Sicurezza Stradale)",
        description="Italy's real-time traffic bulletin RSS, from Italy's own confirmed RTTI NAP.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Italy"}),
        scope_note=(
            "Confirmed live (2026-08-03, 100 real items, 78 real "
            "roadworks after classification) - credential-free, never "
            "a Credentials-wanted scaffold. cciss.it is Italy's own "
            "confirmed official RTTI/SRTI National Access Point (per "
            "the European Commission's own October 2025 NAP list), "
            "reached here via its real, public, keyless RSS route "
            "rather than the registration-gated DATEX II one - a "
            "second, later option, not pursued here. Same shape as "
            "trafficwatchni/trafficwales: a traveller-information feed "
            "mixing roadworks with weather, breakdowns, accidents and "
            "demonstrations in one stream (unlike NI/Wales, which "
            "already serve a roadworks-only feed) - iter_roadworks-"
            "equivalent filtering happens via item.is_roadworks, a real "
            "evidenced classification (lavori/personale su strada/ "
            "pulizia del manto stradale), not a guess. No geometry - "
            "confirmed live, correcting an earlier wrong AI-summarised "
            "claim that the feed carried coordinates. Licence "
            "unconfirmed. See module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="traveller_info",
        _module="streetworks.cciss",
        _client_name="CcissClient",
        import_line="from streetworks.cciss import CcissClient",
    ),
    ProviderEntry(
        key="police",
        name="UK Police",
        description="Street-level crime data - a worker-safety signal, not a street-works feed.",
        kind=Kind.CONTEXT,
        territories=frozenset({"England", "Wales", "Northern Ireland"}),
        scope_note="Not Scotland - Police Scotland doesn't publish to data.police.uk.",
        credentials=None,
        licence="Open Government Licence v3.0 (OGL v3)",
        _module="streetworks.police",
        _client_name="PoliceClient",
        import_line="from streetworks.police import PoliceClient",
    ),
    ProviderEntry(
        key="jersey",
        name="Jersey RoadWorkx",
        description="Jersey's roadworks register, over its public ArcGIS Feature Service.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Jersey"}),
        scope_note=(
            "This SDK's first Channel Islands coverage. The real layer truncates "
            "at 1,000 of 22,105 records and its own resultOffset paging is "
            "silently broken - streetworks.arcgis.jersey pages around it. "
            "Licence unconfirmed - see the module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.arcgis.jersey",
        _client_name="JerseyRoadworksClient",
        import_line="from streetworks.arcgis.jersey import JerseyRoadworksClient",
    ),
    ProviderEntry(
        key="tigerweb",
        name="TIGERweb (US Census Bureau)",
        description="The US national road-segment network, over the TIGERweb ArcGIS service.",
        kind=Kind.STREETS,
        territories=frozenset({"USA"}),
        scope_note=(
            "A statistical/cartographic product, not a legal street register - "
            "no USRN equivalent, real identifiers are dataset-scoped. Segment "
            "only, no Street entity exists in this service - see the module "
            "docstring. No 'usa'/'us' alias: wzdx already owns those; use "
            "providers(territory='USA') or the 'tigerweb' key directly."
        ),
        credentials=None,
        licence="Public domain (17 U.S.C. Sec. 105 - a work of the United States Government)",
        _module="streetworks.arcgis.tigerweb",
        _client_name="TIGERwebClient",
        import_line="from streetworks.arcgis.tigerweb import TIGERwebClient",
    ),
    ProviderEntry(
        key="vialietuva",
        name="Via Lietuva",
        description="Lithuania's national roadworks feed (open data.gov.lt route).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Lithuania"}),
        administrative_area="Via Lietuva",
        scope_note=(
            "The open data.gov.lt route (CC BY 4.0), not the RTTI NAP - that "
            "listed NAP is agreement-gated and 403s without one. Only the "
            "'Remontas' (road repairs) table is modelled as roadworks; "
            "'Kliutis' (obstacles) and 'Renginys' (events) were checked and "
            "are genuinely not roadworks (condition hazards / event "
            "closures) - see the module docstring. Coordinates are real "
            "Lithuanian LKS-94 (EPSG:3346), WKT axis order (Northing, "
            "Easting) - reversed from the usual WKT convention, confirmed "
            "live."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="operator",
        _module="streetworks.vialietuva",
        _client_name="ViaLietuvaClient",
        import_line="from streetworks.vialietuva import ViaLietuvaClient",
    ),
    ProviderEntry(
        key="nzta",
        name="NZTA (Waka Kotahi) Highway Information - Road Events",
        description="New Zealand's national state-highway roadworks feed, over ArcGIS.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"New Zealand"}),
        administrative_area="Waka Kotahi NZ Transport Agency",
        scope_note=(
            "Confirmed live (2026-08-02, 104 real records) - credential-"
            "free, never a Credentials-wanted scaffold. This SDK's first "
            "New Zealand works coverage; see also 'linz' for the paired "
            "gazetteer strand, not joined to this one (no structured road/"
            "route identifier anywhere in the real schema - free text "
            "only, see module docstring). A real correction to the source "
            "investigation: this is the ArcGIS open-data portal service, "
            "not the bespoke trafficnz.info REST/SOAP API. State highways "
            "only, not local/municipal roads. The richest real "
            "status->DateConfidence signal confirmed anywhere in this SDK "
            "(status/planned correlate perfectly with eventType). See "
            "module docstring."
        ),
        credentials=None,
        licence="NZTA 4.0 BY CC (a CC BY 4.0 variant)",
        source_grade="operator",
        _module="streetworks.nzta",
        _client_name="NztaClient",
        import_line="from streetworks.nzta import NztaClient",
    ),
    ProviderEntry(
        key="gnaf",
        name="G-NAF National Address Points",
        description="Australia's national address register, over the Digital Atlas of Australia.",
        kind=Kind.ADDRESSES,
        territories=frozenset({"Australia"}),
        administrative_area="Geoscape Australia",
        scope_note=(
            "Confirmed live (2026-08-02, 15,901,249 real addresses per "
            "the layer's own feature count) - a real, credential-free "
            "ArcGIS Feature Service. No "
            "separate street/locality PID on this derivative - street "
            "identity is text only (STREET_NAME/STREET_TYPE), the same "
            "'no street table of its own' shape as bag. A real 'unit'/"
            "flat concept (FLAT_TYPE/FLAT_NUMBER) has no canonical field "
            "- confirmed as the second built source with this gap, "
            "after linz - see the gazetteer Address model's own "
            "docstring. Licence CC BY 4.0 plus a genuine mandatory "
            "restriction on generating mail-address lists without "
            "independent verification - irrelevant to gazetteer use, "
            "stated for completeness. See module docstring."
        ),
        credentials=None,
        licence=(
            "Creative Commons Attribution 4.0 International (CC BY 4.0), "
            "plus a mail-use restriction"
        ),
        source_grade="register",
        _module="streetworks.gnaf",
        _client_name="GnafClient",
        import_line="from streetworks.gnaf import GnafClient",
    ),
    ProviderEntry(
        key="gnaf_roads",
        name="National Roads (Australia)",
        description="Australia's national road network, over the Digital Atlas of Australia.",
        kind=Kind.STREETS,
        territories=frozenset({"Australia"}),
        administrative_area="Geoscape Australia",
        scope_note=(
            "Confirmed live (2026-08-02, 4,346,217 real segments per the "
            "layer's own feature count) - genuinely comprehensive, not a "
            "highways-only skim: real hierarchy values reach LOCAL ROAD "
            "(the largest single value), FOOTPATH and CYCLEPATH, beyond "
            "even TIGERweb's own local-road layer. road_id is real but "
            "segment-scoped, not an aggregated named-street id, and no "
            "separate named-street layer exists alongside it - emits "
            "Segment only, never Street, the same discipline nwb already "
            "established. Real status values include both OPERATIONAL "
            "and PROPOSED (not-yet-built) roads - iter_roads() is the "
            "raw network, unfiltered by default. No stated join to gnaf "
            "(Australia's addresses) - resolves the source "
            "investigation's own join question on better evidence than "
            "it had (it assumed the only road-network option was "
            "Geoscape's commercial, unavailable product). Licence CC BY "
            "4.0, no extra restriction. See module docstring."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="register",
        _module="streetworks.gnaf",
        _client_name="GnafClient",
        import_line="from streetworks.gnaf import GnafClient",
    ),
    ProviderEntry(
        key="linz",
        name="LINZ NZ Addresses",
        description="New Zealand's national address register.",
        kind=Kind.ADDRESSES,
        territories=frozenset({"New Zealand"}),
        administrative_area="Toitū Te Whenua Land Information New Zealand",
        scope_note=(
            "Confirmed live (2026-08-02, 2,421,642 real addresses per the "
            "layer's own feature_count) - a public ArcGIS Online mirror, "
            "no LINZ Data Service key needed. Covers the current NZ "
            "Addresses family (layer 123113), not the retired NZ Roads "
            "(Addressing) layer. A real, currently uncanonicalised 'unit'/"
            "flat-number concept is present (see the gazetteer Address "
            "model's own docstring) - stays on .raw only. See also "
            "'linz_roads' for this cluster's street/segment coverage "
            "(same client, a genuinely different verification tier), and "
            "module docstring for the unconfirmed road_id cross-reference "
            "between the two."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="register",
        _module="streetworks.linz",
        _client_name="LinzClient",
        import_line="from streetworks.linz import LinzClient",
    ),
    ProviderEntry(
        key="linz_roads",
        name="LINZ NZ Addresses: Roads / Road Sections",
        description="New Zealand's national road network - aggregated centrelines and sections.",
        kind=Kind.STREETS,
        territories=frozenset({"New Zealand"}),
        administrative_area="Toitū Te Whenua Land Information New Zealand",
        scope_note=(
            "Phase 1 scaffold - schema and a real attribute sample both "
            "confirmed live from LINZ's own public Koordinates metadata "
            "API (Roads layer 123110, Road Sections layer 123109; real "
            "totals 82,221/250,409 per each layer's own feature_count), "
            "but never queried through the real WFS - this needs a "
            "genuine LINZ Data Service (LDS) API key this build doesn't "
            "have (self-service registration needs a real account this "
            "session can't create). The real WFS URL shape (API key in "
            "the URL path, Koordinates' own convention) and startIndex/"
            "count pagination are implemented to spec but unexercised "
            "against a real response. Same LinzClient as 'linz' - a "
            "genuinely different verification tier on the same client, "
            "not a separate module. See module docstring."
        ),
        credentials="LINZ Data Service (LDS) API key (data.linz.govt.nz)",
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="register",
        verified=False,
        _module="streetworks.linz",
        _client_name="LinzClient",
        import_line="from streetworks.linz import LinzClient",
    ),
]
