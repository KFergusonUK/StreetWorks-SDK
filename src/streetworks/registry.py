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

**Deliberately not built here**: no uniform
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
        # No "france" alias: France now has several providers (this
        # one, ban, bdtopo, paris, and the départements below) -
        # get_provider("france") resolves through the territory-
        # ambiguity path instead, same as "germany".
        _module="streetworks.datex2",
        _client_name="BisonFuteClient",
        import_line="from streetworks.datex2 import BisonFuteClient",
    ),
    ProviderEntry(
        key="sarthe",
        name="Sarthe (Conseil départemental)",
        description="Sarthe's own département roadworks feed (Routes Départementales).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"France"}),
        administrative_area="Conseil départemental de la Sarthe",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free. This SDK's "
            "first French *département*-level roadworks provider - the "
            "majority of the French road network by length (Routes "
            "Départementales) is each département's own responsibility "
            "and isn't in Bison Futé at all, the same real gap Germany's "
            "own state fan-out closed relative to Autobahn GmbH. 9 real "
            "features, real Point-de-Repère road/kilometre-marker "
            "referencing (loc_txt, e.g. 'RD 0316 : Du 0+100 au 1+700'), "
            "structured ISO datetimes with an explicit UTC offset - the "
            "only département checked so far with real structured "
            "dates. Over the same real OpenDataSoft Explore API v2.1 "
            "platform streetworks.paris already established - a second "
            "and third real consumer (this one, Loire-Atlantique, "
            "Hauts-de-Seine) justified extracting a small shared "
            "streetworks.opendatasoft client, Paris's own code left "
            "untouched. See streetworks.opendatasoft.france_departements's "
            "module docstring for the full write-up, including a real "
            "GML-only département (Corrèze) and a real non-OpenDataSoft "
            "one (Côtes d'Armor, 5,292 features on a Koumoul/data-fair "
            "REST API) found but not built this round."
        ),
        credentials=None,
        licence="Licence Ouverte / Open Licence 2.0 (Etalab)",
        source_grade="operator",
        _module="streetworks.opendatasoft.france_departements",
        _client_name="DepartementRoadworksClient",
        import_line=(
            "from streetworks.opendatasoft.france_departements import "
            'DepartementRoadworksClient # .fetch("Sarthe")'
        ),
    ),
    ProviderEntry(
        key="loire_atlantique",
        name="Loire-Atlantique (Département)",
        description="Loire-Atlantique's own département roadworks feed (Routes Départementales).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"France"}),
        administrative_area="Département de Loire-Atlantique",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free, described "
            "by its own publisher as real-time. 21 real Point-geometry "
            "features. No structured dates at all - a real French "
            "free-text date range only (ligne4, e.g. 'Du 18/08/2026 au "
            "20/08/2026'), never parsed, so every record carries "
            "DateConfidence.UNKNOWN honestly. No real per-record "
            "identifier either - Works.reference is genuinely an empty "
            "string. Real point field is named 'localisation', not "
            "'geo_point_2d' like its siblings - a real per-dataset "
            "choice, not an OpenDataSoft platform standard, confirmed "
            "live. See streetworks.opendatasoft.france_departements's "
            "module docstring."
        ),
        credentials=None,
        licence="Licence Ouverte / Open Licence 2.0 (Etalab)",
        source_grade="operator",
        _module="streetworks.opendatasoft.france_departements",
        _client_name="DepartementRoadworksClient",
        import_line=(
            "from streetworks.opendatasoft.france_departements import "
            'DepartementRoadworksClient # .fetch("Loire-Atlantique")'
        ),
    ),
    ProviderEntry(
        key="hauts_de_seine",
        name="Hauts-de-Seine (Département)",
        description="Hauts-de-Seine's own département infrastructure-works register.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"France"}),
        administrative_area="Département des Hauts-de-Seine",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free. 122 real "
            "features - but a genuinely different register from its "
            "siblings: a capital-works/infrastructure-project register "
            "(tramway extensions, cycle-lane programmes; real "
            "'avancement' project-phase field - "
            "'Travaux en cours'/'Travaux programmés'/'Projet à "
            "l'étude'), not a day-to-day closures feed - no structured "
            "dates exist here either (date_travaux is real free text, "
            "often spanning years, or None outright), so "
            "DateConfidence.UNKNOWN throughout, the same honest gap "
            "Loire-Atlantique has. Real 'voie' field genuinely lists "
            "several route numbers per record (comma-separated) since "
            "one project can span several routes. See "
            "streetworks.opendatasoft.france_departements's module "
            "docstring."
        ),
        credentials=None,
        licence="Licence Ouverte / Open Licence 2.0 (Etalab)",
        source_grade="operator",
        _module="streetworks.opendatasoft.france_departements",
        _client_name="DepartementRoadworksClient",
        import_line=(
            "from streetworks.opendatasoft.france_departements import "
            'DepartementRoadworksClient # .fetch("Hauts-de-Seine")'
        ),
    ),
    ProviderEntry(
        key="toulouse",
        name="Toulouse Métropole",
        description="Toulouse Métropole's own roadworks register, over OpenDataSoft.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"France"}),
        administrative_area="Toulouse Métropole",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free. 987 real "
            "features - the richest area in this SDK's French cluster, "
            "and this SDK's second French *municipal*-tier roadworks "
            "provider after Paris, found via the same real OpenDataSoft "
            "shape the département field maps already established. "
            "Real per-record case numbers (numero, e.g. "
            "'T26VLT04616'), structured ISO dates, a real specific "
            "promoter (declarant, e.g. 'ORANGE' - a utility, not always "
            "the métropole itself). Real commune values confirm this "
            "genuinely spans several communes within the métropole, not "
            "Toulouse city alone. See "
            "streetworks.opendatasoft.france_departements's module "
            "docstring."
        ),
        credentials=None,
        licence="Licence Ouverte / Open Licence 2.0 (Etalab)",
        source_grade="operator",
        _module="streetworks.opendatasoft.france_departements",
        _client_name="DepartementRoadworksClient",
        import_line=(
            "from streetworks.opendatasoft.france_departements import "
            'DepartementRoadworksClient # .fetch("Toulouse Métropole")'
        ),
    ),
    ProviderEntry(
        key="rennes",
        name="Rennes Métropole",
        description="Rennes Métropole's own roadworks register, over OpenDataSoft.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"France"}),
        administrative_area="Rennes Métropole",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free. 463 real "
            "features - the largest of three real time-window siblings "
            "the source itself publishes (1-day/6-day/30-day; the "
            "30-day superset used here, avoiding three overlapping "
            "client calls for what's genuinely one underlying feed). A "
            "real, clean disruption-level status field "
            "(niv_perturbation, e.g. 'Circulation difficile'), a real "
            "per-record business identifier (id_evt) preferred over the "
            "dataset's own opaque row id. No real promoter field - a "
            "real interlocuteur field exists but is populated on only "
            "1/463 real records checked live, with a cryptic "
            "abbreviation, not an organisation name. See "
            "streetworks.opendatasoft.france_departements's module "
            "docstring."
        ),
        credentials=None,
        licence="ODC Open Database License (ODbL)",
        source_grade="operator",
        _module="streetworks.opendatasoft.france_departements",
        _client_name="DepartementRoadworksClient",
        import_line=(
            "from streetworks.opendatasoft.france_departements import "
            'DepartementRoadworksClient # .fetch("Rennes Métropole")'
        ),
    ),
    ProviderEntry(
        key="lyon",
        name="Lyon (Métropole de Lyon)",
        description="Métropole de Lyon's own roadworks feed, over a plain GeoServer WFS.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"France"}),
        administrative_area="Métropole de Lyon",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free. 351 real "
            "features on a plain WFS 2.0.0 (GeoServer), not "
            "OpenDataSoft - a genuine third real platform shape in "
            "this SDK's French cluster, built bespoke over the same "
            "generic streetworks.ogc.client.OGCFeaturesClient the "
            "German state cluster already uses. Real road name (100% "
            "populated), real commune/INSEE code (genuinely spans "
            "several communes, not Lyon city alone), a real 4-value "
            "restriction-type status field. Only real geometry is "
            "MultiPolygon (worksite footprint) - no point/line field "
            "exists at all - the real first ring's first vertex is "
            "used as the representative point, the same 'one real, "
            "arbitrarily-chosen-but-genuinely-stated point, never a "
            "computed centroid' discipline this SDK's own gazetteer "
            "converters (Oslo, Kanton Zürich, GeoSN) already "
            "establish, applied here to a roadworks record. Real "
            "'intervenant' promoter field is genuinely uninformative "
            "on 347/351 records ('Autre') - mapped anyway, since it's "
            "what the source states. avancement (status/progress) is "
            "real but constant ('Chantier en cours') on every record "
            "at investigation time - this endpoint states only "
            "currently-active works, no separate planned tier. See "
            "the module docstring."
        ),
        credentials=None,
        licence="Licence Ouverte / Open Licence 2.0 (Etalab)",
        source_grade="operator",
        _module="streetworks.lyon",
        _client_name="LyonClient",
        import_line="from streetworks.lyon import LyonClient",
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
        key="madrid",
        name="Ayuntamiento de Madrid (INFORMO)",
        description="Madrid's municipal traffic-incidents feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Spain"}),
        administrative_area="Ayuntamiento de Madrid",
        scope_note=(
            "Confirmed live (2026-08-08, 217 real incidents) - "
            "credential-free, never a Credentials-wanted scaffold. The "
            "capital and largest Spanish city, absent from dgt's own "
            "national/interurban coverage (dgt explicitly never reaches "
            "municipal streets, though it does carry some M-prefixed "
            "interurban roads in the wider Madrid region - see dgt's own "
            "scope_note; no confirmed overlap checked, never dedupe "
            "matches regardless, per the standing note on this). "
            "Comprehensive city-wide streets, not interurban-only like "
            "dgt or state-network-only like the German OGC cluster - real "
            "records span everything from named residential streets "
            "(e.g. 'Antonio Leyva') to motorway sections (A-3/A-5), "
            "spread across the whole municipality, not one road tier. "
            "An earlier-documented URL "
            "(informo.munimadrid.es) is dead - Madrid relaunched its "
            "whole open-data portal in February 2026; this client targets "
            "the real current host (informo.madrid.es) confirmed via the "
            "new CKAN portal's own redirect. Roadworks filter uses the "
            "source's own es_obras flag, not a free-text type guess - "
            "settles two real findings live data revealed: lane closures "
            "and asphalt-resurfacing operations are both real and common "
            "but neither is flagged es_obras, so both are excluded. "
            "source_grade=operator (road-authority-published, DATEX-"
            "coded types per the source's own field dictionary), not "
            "traveller_info, an easy assumption from the source name alone "
            "- matches dgt/sct/mallorca's own classification, not Berlin's "
            "VIZ (an "
            "editorial relay, not the road authority itself). Coordinates "
            "are native ETRS89 (EPSG:4258/EPSG:25830, confirmed from the "
            "source's own field dictionary), labelled as such, not "
            "silently WGS84. See module docstring."
        ),
        credentials=None,
        licence=(
            "CC BY - confirmed live at nap.dgt.es/dataset/trafico-"
            "incidencias-en-via-publica (organization: ayuntamiento-de-"
            "madrid, license field: cc-by, 'Creative Commons Attribution' "
            "stated on the page itself); the exact attribution string on "
            "datos.madrid.es's own new CKAN portal wasn't separately "
            "re-verified"
        ),
        source_grade="operator",
        _module="streetworks.madrid",
        _client_name="MadridClient",
        import_line="from streetworks.madrid import MadridClient",
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
        key="austria",
        name="ASFINAG",
        description="Austria's national motorway/expressway roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Austria"}),
        administrative_area="ASFINAG",
        scope_note=(
            "Phase 0 scaffold - even less confirmed than Vejdirektoratet "
            "at the same stage. ASFINAG's own official dataset page "
            "confirms a real DATEX II Situations/SituationRecords "
            "roadworks dataset ('Verkehrsmeldungen zu geplanten "
            "Ereignissen'), but neither the real pull URL nor the auth "
            "mechanism (not just the credential value) is stated "
            "anywhere public - checked the dataset page, its licence "
            "page, and the registration portal's own JS bundle. The "
            "natural 'check for an open RSS feed first' question is "
            "resolved, negatively: the real keyless RSS/ATOM "
            "feed on the same NAP is confirmed live to cover only "
            "'unplanned and safety-related traffic events', not "
            "roadworks - no keyless shortcut exists. An older documented "
            "API host (services2.asfinag.at) is unreachable from this "
            "build environment. Licence is CC-BY-4.0 with real "
            "supplementary conditions beyond plain CC-BY (must disclose "
            "downstream services to ASFINAG; they may publicly reference "
            "the licensee) - confirmed live, not glossed over."
        ),
        credentials=(
            "ASFINAG Content Portal registration - issues the real pull URL; "
            "the auth mechanism itself is unconfirmed"
        ),
        licence="CC-BY-4.0 plus supplementary conditions - confirmed live",
        source_grade="operator",
        verified=False,
        _module="streetworks.datex2",
        _client_name="AsfinagClient",
        import_line="from streetworks.datex2 import AsfinagClient",
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
            "A real correction to an earlier assumption: this is "
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
        description="Tasmania state-road roadworks feed (Australia), real multi-vertex linework.",
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
        description="NT road-conditions service (Australia) - public GetAll JSON.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Australia", "Northern Territory"}),
        administrative_area="Department of Infrastructure, Planning and Logistics",
        scope_note=(
            "Confirmed live (2026-08-19) against the public JSON endpoint "
            "GET /api/Obstruction/GetAll - 140 CURRENT records, 26 of them "
            "official Roadworks (type-code 28). Credential-free; licence "
            "genuinely unconfirmed. Statewide NT-Government roads "
            "(councils excluded) - NetworkScope.STRATEGIC. Still a "
            "road-condition system: iter_roadworks() returns only records "
            "that are actually works, not the weight/flooding/surface "
            "majority. The reverse-engineered SignalR hub is not consumed. "
            "See module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
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
            "interface) and a different reason from Greece (which has "
            "no roadworks source at all). MapRoad has a real, government-"
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
            "silently skipped - the same tier as MapRoad (no usable "
            "roadworks interface at all, as opposed to Trafikverket/"
            "Vejdirektoratet/SA, all of which have a real interface "
            "merely blocked). Greece's real NAP (nap.gov.gr, "
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
            "Repeats at municipal level too: the City of Athens' own "
            "real OGC API Features server (api.gis.cityofathens.gr, "
            "pygeoapi - found only on a later, closer look) was "
            "checked directly (2026-08-09) - 3 real collections (lakes, "
            "neighbourhood boundaries, building blocks), none roadworks. "
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
        key="baden_wuerttemberg",
        name="Baden-Württemberg",
        description="Baden-Württemberg's state roadworks feed (Baustelleninformationen).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.MULTI_AUTHORITY_INTERURBAN,
        territories=frozenset({"Germany"}),
        administrative_area="Verkehrsministerium Baden-Württemberg",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free, a real direct "
            "GeoJSON download off the state's own MobiData BW platform, no "
            "WFS query needed. 928 real features covering Bundesstraßen, "
            "Landesstraßen and Kreisstraßen (federal/state/county roads) - "
            "never municipal streets, hence multi_authority_interurban, "
            "not comprehensive. The one state in this cluster with a real "
            "time-of-day (not just a date) on its start/end fields, with a "
            "genuine DST-aware UTC offset. Real per-feature identifier "
            "lives in a lowercase `id` property, a third shape alongside "
            "Hamburg's/Brandenburg's own conventions - see "
            "StateFieldMap.id_field."
        ),
        credentials=None,
        licence="Datenlizenz Deutschland - Namensnennung - Version 2.0 (dl-de/by-2-0)",
        source_grade="operator",
        aliases=frozenset({"bw"}),
        _module="streetworks.ogc.germany",
        _client_name="GermanRoadworksClient",
        import_line=(
            'from streetworks.ogc.germany import GermanRoadworksClient '
            '# .fetch("Baden-Württemberg")'
        ),
    ),
    ProviderEntry(
        key="schleswig_holstein",
        name="Schleswig-Holstein",
        description="Schleswig-Holstein's state roadworks feed (Baustelleninformationen).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Germany"}),
        administrative_area="Landesbetrieb Straßenbau und Verkehr Schleswig-Holstein (LBV.SH)",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free. 1,116 real "
            "features, genuinely GML-only (a real OUTPUTFORMAT=application/"
            "json request is rejected outright) - parsed client-side via "
            "the standard library's own xml.etree.ElementTree, geometry "
            "reprojected from the service's real native EPSG:25832 "
            "(ETRS89/UTM32N) to WGS84. Real road-class prefixes span B "
            "(Bundesstraße), L (Landesstraße), K (Kreisstraße) and a bare "
            "'G' (Gemeindestraße/municipal, 466/1,116 real records - the "
            "single largest group, a real but low-information value, "
            "carried through as-is) - comprehensive, reaching down to "
            "municipal roads by classification, unlike Baden-Württemberg's "
            "own interurban-only scope. This same WFS deployment "
            "(dienste.gdi-sh.de, run by LBV.SH) also carries Niedersachsen "
            "and Mecklenburg-Vorpommern feature types - deliberately not "
            "built: neither has its own confirmed open licence (both trace "
            "to gated Mobilithek marketplace offers, the same shape "
            "already parked for NRW), unlike Schleswig-Holstein's own real "
            "CC BY 4.0, confirmed directly on the state's own open-data "
            "portal. See the module docstring for the full write-up."
        ),
        credentials=None,
        licence="Creative Commons Namensnennung - 4.0 International (CC BY 4.0)",
        source_grade="operator",
        aliases=frozenset({"sh"}),
        _module="streetworks.ogc.germany",
        _client_name="GermanRoadworksClient",
        import_line=(
            'from streetworks.ogc.germany import GermanRoadworksClient '
            '# .fetch("Schleswig-Holstein")'
        ),
    ),
    ProviderEntry(
        key="rheinland_pfalz",
        name="Rheinland-Pfalz",
        description="Rhineland-Palatinate's state roadworks feed (Baustelleninformationen).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Germany"}),
        administrative_area=(
            "Ministerium für Wirtschaft, Verkehr, Landwirtschaft und Weinbau (MWVLW)"
        ),
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free, real WFS run "
            "directly by RLP's own transport ministry "
            "(maps.mobilitaetsatlas.de/geoserver). This exact real layer "
            "(mwvlw:baustelle) genuinely aggregates several sources on "
            "one shared platform - confirmed live via the real 'quelle' "
            "property: 999 records genuinely from RLP's own traffic "
            "authorities, plus 1,201 from Autobahn GmbH, 652 from Baden-"
            "Württemberg and 220 from the city of Karlsruhe, all already "
            "covered by this SDK's own separate providers. A real "
            "cql_filter scopes this entry to RLP's own real contribution "
            "only (999 records, 100% carrying a real road field). "
            "Real ansprechpartner (contact) values vary per record down "
            "to individual Kreis/municipal traffic authorities - "
            "comprehensive, not state-network-only. This GeoServer only "
            "registers application/json for this layer, not "
            "OGCFeaturesClient's own application/geo+json default - a "
            "real InvalidParameterValue exception confirmed live, "
            "handled via a new StateFieldMap.output_format override. "
            "Licence genuinely unconfirmed, not 'none exists' - "
            "govdata.de, the WFS's own GetCapabilities AccessConstraints, "
            "and open.rlp.de's own API were all checked; the last two "
            "state nothing and the latter blocks the API path outright "
            "(a real 403, not routed around). See the module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        aliases=frozenset({"rlp"}),
        _module="streetworks.ogc.germany",
        _client_name="GermanRoadworksClient",
        import_line=(
            'from streetworks.ogc.germany import GermanRoadworksClient '
            '# .fetch("Rheinland-Pfalz")'
        ),
    ),
    ProviderEntry(
        key="saarland",
        name="Saarland",
        description="Saarland's state roadworks feed (Landesbetrieb für Straßenbau).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.MULTI_AUTHORITY_INTERURBAN,
        territories=frozenset({"Germany"}),
        administrative_area="Landesbetrieb für Straßenbau (LfS)",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free. 38 real "
            "features at investigation time, genuinely smaller than "
            "this SDK's other German states, consistent with Saarland's "
            "own small size. Found by reading LfS's own real public map "
            "app's bundled JS (baustellen.saarland) - the same "
            "technique that found Lisboa's Condicionamentos endpoint - "
            "not a WFS, so this doesn't go through "
            "streetworks.ogc.germany's shared field-map architecture; "
            "it's a bespoke streetworks.saarland client instead. Real "
            "road-class prefixes span B (Bundesstraße)/L (Landesstraße) "
            "only - no K/A seen live. Dates are genuinely naive (no UTC "
            "offset stated at all), unlike Baden-Württemberg's own "
            "explicit-offset dates. Licence genuinely unconfirmed, not "
            "'none exists' - govdata.de, the GDI-DE metadata catalogue "
            "(a real 403), and saarland.de's own general pages (a real "
            "403, a site-wide WAF, not this dataset specifically) were "
            "all checked. See the module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        _module="streetworks.saarland",
        _client_name="SaarlandClient",
        import_line="from streetworks.saarland import SaarlandClient",
    ),
    ProviderEntry(
        key="dortmund",
        name="Dortmund",
        description="The City of Dortmund's own roadworks register (NRW), over OpenDataSoft.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Germany"}),
        administrative_area="Stadt Dortmund",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free. This SDK's "
            "first German *municipal* roadworks provider, a genuinely "
            "different tier from the state-level cluster in "
            "streetworks.ogc.germany - opened up because NRW's own "
            "state-level route stays gated (Mobilithek/DATEX), but this "
            "one real city's own feed isn't. Found via GOVdata, not "
            "assumed: Cologne and Aachen were both checked live and "
            "trace only to Mobilithek marketplace offers, no "
            "independent open republish found for either - Dortmund is "
            "a genuine exception, not representative of a wider open "
            "NRW-municipal pattern. 172 real records at investigation "
            "time (134 'tagesaktuell'/currently-active + 38 "
            "'geplant'/planned, same real schema). Real promoter field "
            "(auftraggeber, e.g. 'EB70 - Stadtentwässerung', "
            "'Dortmunder Netz', 'Stadt Dortmund') and real city-district "
            "field (stadtbezirk) - no clean separate street field, the "
            "same honest gap NYC/Chicago/Paris's own permit registers "
            "already carry. A real per-record identifier exists only "
            "via the older v2 catalog API (record.id) - the newer v2.1 "
            "Explore API's own flattened records carry no id at all, "
            "confirmed live. Same OpenDataSoft platform family as "
            "streetworks.paris's own 'Chantiers à Paris'."
        ),
        credentials=None,
        licence="Datenlizenz Deutschland - Zero - Version 2.0 (dl-zero-de/2.0)",
        source_grade="operator",
        _module="streetworks.dortmund",
        _client_name="DortmundClient",
        import_line="from streetworks.dortmund import DortmundClient",
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
            "- an easy assumption is that Verkehrsredaktion is a detail-"
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
            "and defaults to wzdx_only=True - excluding sub-3.1/"
            "unparseable-version entries only, a documented skip rather "
            "than a mis-parse. CWZ (a related AASHTO/ITE/NEMA/SAE schema "
            "built on WZDx v4.2, version=='CWZ 1.0') is parsed too, "
            "including one real vendor's camelCase field-naming quirk "
            "(Massachusetts DOT) - see streetworks.wzdx.parser's own "
            "module docstring. Two real auth tiers: ~27/41 need no key at all "
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
            "first, most-obvious dataset id (6fd2-pzze) is dead - "
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
        key="dc",
        name="Washington DC DDOT Construction Permits",
        description="DC's public-space construction permit register, over DDOT's ArcGIS feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        # Both "USA" and "Washington DC" (this provider's real reach is
        # city/district-scoped) - see providers(territory="Washington DC")
        # and examples/roadworks_world_map.py's own city centroid, the
        # same pattern nycdot/chicagodot/paris already established. Not
        # in the WZDx/CWZ US registry at all - DC has no row there.
        territories=frozenset({"USA", "Washington DC"}),
        administrative_area="District Department of Transportation (DDOT)",
        scope_note=(
            "Confirmed live (2026-08-21, 3,453 real rows in the "
            "Construction Permit - Last 30 Days layer) - credential-free, "
            "never a Credentials-wanted scaffold. This SDK's third US "
            "city permit register after nycdot/chicagodot, "
            "source_grade=register, and its first over a plain ArcGIS "
            "REST MapServer rather than Socrata - built on the same "
            "generic streetworks.arcgis.ArcGISFeatureClient Jersey/"
            "TIGERweb already use. Confirmed to be genuinely street/"
            "right-of-way work, not general building permits, by reading "
            "real sample records (ISEXCAVATION true on ~80% of a 1,000-"
            "record sample) - a generically-named 'Construction_Permits' "
            "dataset found first this session turned out on inspection "
            "to be unrelated Boulder, Colorado building-permit data, not "
            "DC's at all; this entry points at the real DDOT service "
            "instead. A related Occupancy Permit layer on the same "
            "service also covers non-construction public-space use (a "
            "real sampled record: a music festival) - not consumed here, "
            "the same 'related but distinct, noted not consumed' "
            "treatment Jersey's own Projects layer gets. Real WGS84 "
            "point geometry under f=geojson, confirmed live. Licence: "
            "Creative Commons Attribution 4.0 International, confirmed "
            "live via opendata.dc.gov's own dataset metadata. See module "
            "docstring."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        licence_confirmed=True,
        source_grade="register",
        _module="streetworks.arcgis.dc",
        _client_name="DCConstructionPermitsClient",
        import_line="from streetworks.arcgis.dc import DCConstructionPermitsClient",
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
        key="tfl",
        name="Transport for London (Road Disruption)",
        description=(
            "TfL's live operational roadworks/disruption feed for London's "
            "strategic road network - the accessible complement to Street "
            "Manager's own all-borough permit register."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"England", "London"}),
        administrative_area="Transport for London",
        scope_note=(
            "Confirmed live (2026-08-15, 118 real disruption rows, 116 "
            "real Works rows) - credential-free, genuinely keyless, "
            "better than the usual 'register for a free key' "
            "assumption; TfL's optional app_key only raises the "
            "rate limit, the same role Socrata's X-App-Token plays for "
            "SodaClient. category == 'Works' is a real, clean filter, "
            "confirmed by reading the two excluded non-Works records "
            "directly. Geometry states its own CRS explicitly "
            "(EPSG:4326) on every record - the cleanest CRS situation "
            "of any provider in this SDK. corridorIds (a plausible "
            "road-number field) is genuinely incomplete - only 44% of "
            "real Works rows carry one, including just half of the core "
            "'TfL works' subcategory - so it's never promoted to "
            "street_ref. status was 'Active' on every real row checked "
            "(this endpoint only returns currently-active disruptions), "
            "checked explicitly rather than assumed constant, driving "
            "real VERIFIED date-confidence grading. Do-not-dedupe "
            "against streetmanager's own opendata (all-London-borough "
            "permit register, register-grade) - a works on a TLRN red "
            "route can genuinely appear in both. Licence: TfL's own OGL "
            "v2.0-with-amendments terms, confirmed live, requiring three "
            "real attribution statements, not just the one commonly "
            "quoted."
        ),
        credentials=None,
        licence=(
            "OGL v2.0 with TfL amendments - confirmed live; requires "
            "three attribution statements ('Powered by TfL Open Data', "
            "OS data, and Geomni UK Map data credits)"
        ),
        source_grade="operator",
        _module="streetworks.tfl",
        _client_name="TflClient",
        import_line="from streetworks.tfl import TflClient",
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
        key="jersey_streets",
        name="Jersey Street Gazetteer",
        description="Jersey's real street register, over the same ArcGIS deployment as RoadWorkx.",
        kind=Kind.STREETS,
        territories=frozenset({"Jersey"}),
        scope_note=(
            "Confirmed live (2026-08-16) - credential-free, found by "
            "walking the same roadworks.gov.je ArcGIS deployment "
            "'jersey' (roadworks) already uses. A real second service "
            "(JSearch, not JSWFeatureService) - 2,159 real named 'Road' "
            "features (of 7,553 total polygons; the rest are "
            "'Pavement'). Real GB-NSG-style USRNs in a distinct "
            "Crown-Dependency numbering block, every one confirmed a "
            "whole integer. Geometry is a genuine two-CRS-in-one-record "
            "situation: the real polygon geometry is WGS84, but this "
            "converts on the real, separately-stated USRN_XY1/USRN_XY2 "
            "attribute pair instead (native EPSG:3109, never "
            "reprojected) - forcing the polygon ring into "
            "Coordinate.points would misuse that field's own contract, "
            "the same discipline from_paris established. 89.7% of real "
            "'Road' rows carry a stated pair; GeometryGrade.ABSENT on "
            "the rest, never a fabricated centroid. Licence unconfirmed "
            "- see the module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.arcgis.jersey",
        _client_name="JerseyStreetsClient",
        import_line="from streetworks.arcgis.jersey import JerseyStreetsClient",
    ),
    ProviderEntry(
        key="guernsey_streets",
        name="Guernsey Street Gazetteer",
        description="Guernsey's real street register, over its own public ArcGIS deployment.",
        kind=Kind.STREETS,
        territories=frozenset({"Guernsey"}),
        scope_note=(
            "Confirmed live (2026-08-16) - credential-free. This SDK's "
            "second Channel Islands streets provider, found by checking "
            "whether Jersey's real setup has a Guernsey sibling - it "
            "does, on the same real shape (roadworks.gov.gg's own "
            "ArcGIS deployment, a GSearch service mirroring Jersey's "
            "JSearch). 2,591 real named 'Road' features (of 2,727 total "
            "polygons) - no clean type field exists to separate genuine "
            "street names from other real values sharing the same field "
            "(e.g. 'CAR PARK'), so every non-blank one converts. Real "
            "USRNs include genuine fractional subdivisions (e.g. parent "
            "20194 with child polygons 20194.02/20194.04/...), a "
            "distinct numbering block from Jersey's own. No stated "
            "point/line field exists at all (unlike Jersey's own real "
            "USRN_XY1/USRN_XY2 pair) - every Street carries "
            "GeometryGrade.ABSENT, the real polygon preserved in .raw "
            "only. Licence unconfirmed - see the module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.arcgis.guernsey",
        _client_name="GuernseyStreetsClient",
        import_line="from streetworks.arcgis.guernsey import GuernseyStreetsClient",
    ),
    ProviderEntry(
        key="lisboa_streets",
        name="Toponímia de Lisboa (CML)",
        description="Lisbon's own official street naming register, over CML's ArcGIS deployment.",
        kind=Kind.STREETS,
        territories=frozenset({"Portugal"}),
        administrative_area="Câmara Municipal de Lisboa (CML)",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free. This SDK's "
            "first Portuguese streets/gazetteer provider; national "
            "streets were already ruled out (Infraestruturas de "
            "Portugal's own road network carries route-classification "
            "codes, no name field - see "
            "docs/portugal-streets-investigation.md), so this checks "
            "the capital itself, the same 'try the capital/a city' "
            "fallback shape Germany's own state fan-out uses. Found by "
            "walking CML's real Geodados ArcGIS Online organisation "
            "(130 real items) - two other real candidates on the same "
            "deployment were set aside first: a 'Topónimos' layer (only "
            "40 real neighbourhood-label points, not streets) and a "
            "'Rede Viária' layer (3,763 real segments but only 375 "
            "distinct names - the city's structuring road network, not "
            "exhaustive). The 'Toponímia de Lisboa' layer used here is "
            "the real, official register instead - 3,671 real records, "
            "100% named, already one row per street (not segmented), "
            "each carrying genuine municipal-decree provenance (real "
            "deliberation/edict/publication dates, former names, a "
            "prose history of the name) - see the module docstring for "
            "the full write-up. Geometry is a real LineString/"
            "MultiLineString, confirmed genuine WGS84 via a live "
            "f=geojson request despite the service's own stated native "
            "CRS being Web Mercator. Licence: real, explicit CC0, "
            "alongside a real non-legal-use cartography caveat."
        ),
        credentials=None,
        licence="Creative Commons CC Zero (CC0)",
        source_grade="register",
        _module="streetworks.arcgis.lisboa",
        _client_name="LisboaStreetsClient",
        import_line="from streetworks.arcgis.lisboa import LisboaStreetsClient",
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
        key="nrn",
        name="National Road Network (NRN, Canada)",
        description="Canada's national road-segment network, over Statistics Canada's ArcGIS REST.",
        kind=Kind.STREETS,
        territories=frozenset({"Canada"}),
        administrative_area="Statistics Canada / Natural Resources Canada",
        scope_note=(
            "Confirmed live (2026-08-16) - credential-free, this SDK's "
            "first Canadian streets/gazetteer provider, found via the "
            "same GeoBase-series catalogue entry that gave IDEE "
            "Transportes its shape for Spain. Segment only, the same "
            "TIGERweb/NWB outcome - no separate named-street entity "
            "exists in this REST service. 65 real, genuinely "
            "non-redundant layers (5 road-class tiers x 13 provinces/ "
            "territories, confirmed live by comparing feature counts - "
            "not a cartographic pyramid like TIGERweb's own layers "
            "0-9). No genuine per-segment identifier is exposed over "
            "this REST service (unlike the bulk GeoPackage product's "
            "own NID field) - Segment.identifiers stays empty. Real "
            "left/right place-name divergence on administrative-"
            "boundary segments handled the same way from_bdtopo's own "
            "commune split is: administrative_area is the shared value "
            "only, None where the two sides genuinely differ, never an "
            "arbitrary pick. Licence: Open Government Licence - Canada."
        ),
        credentials=None,
        licence="Open Government Licence - Canada",
        source_grade="register",
        _module="streetworks.arcgis.nrn",
        _client_name="NrnClient",
        import_line="from streetworks.arcgis.nrn import NrnClient",
    ),
    ProviderEntry(
        key="monaghan",
        name="Monaghan County Council road network",
        description="A real Irish county's own road network, over its ArcGIS REST services.",
        kind=Kind.STREETS,
        territories=frozenset({"Ireland", "Monaghan"}),
        administrative_area="Monaghan County Council",
        scope_note=(
            "Confirmed live (2026-08-16) - credential-free, this SDK's "
            "first Irish gazetteer coverage. A pilot for a real, "
            "genuine 31-county fan-out (see docs/providers/pending.md's "
            "own live investigation, which ruled out a single national "
            "named-street source for Ireland). Segment only, and "
            "deliberately never a fabricated Street - real Irish rural "
            "roads genuinely have no name; the real Road_Name field is "
            "Ireland's own official route number ('L-31011-0'), not a "
            "street name, carried as a real Identifier instead of a "
            "fabricated one. Three real, distinct road-class services "
            "(National/Regional/Local, 27/122/1,612 real segments). "
            "Licence unconfirmed - no explicit statement found on the "
            "real ArcGIS Online items checked, the same open-by-design "
            "situation Jersey's own services have; see module "
            "docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.arcgis.monaghan",
        _client_name="MonaghanRoadsClient",
        import_line="from streetworks.arcgis.monaghan import MonaghanRoadsClient",
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
            "only, see module docstring). A real correction to an "
            "earlier assumption: this is the ArcGIS open-data portal service, "
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
            "(Australia's addresses) - resolves an earlier open "
            "question on better evidence than was available at the time "
            "(the assumption then was that the only road-network option was "
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
    ProviderEntry(
        key="idee",
        name="IDEE Transportes (Spain national road network)",
        description="Spain's national road-transport network, published by IGN.",
        kind=Kind.STREETS,
        territories=frozenset({"Spain"}),
        administrative_area="Instituto Geográfico Nacional (IGN)",
        scope_note=(
            "Confirmed live (2026-08-15) - credential-free, never a "
            "Credentials-wanted scaffold. A different agency and data "
            "class from this SDK's existing Spanish roadworks coverage "
            "(DGT, Consell de Mallorca, SCT) - do not conflate. Resolves "
            "docs/inspire-gml-investigation.md's own real problem: a "
            "RoadLink carries geometry but no name, so this client "
            "fetches Road (name/codes plus a list of RoadLink "
            "references) and batch-resolves its RoadLinks in one "
            "RESOURCEID request - a broken cross-reference is a "
            "confirmed real case, counted not raised. Spain's separate "
            "INSPIRE Addresses service (Catastro) was investigated the "
            "same day and deliberately not built alongside this - its "
            "documented endpoint no longer responds, and its own "
            "confirmed licence prohibits redistributing original data "
            "unmodified, conflicting with this SDK's usual real-fixture "
            "convention. See module docstring and "
            "docs/providers/pending.md."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="register",
        _module="streetworks.idee",
        _client_name="IdeeTransportesClient",
        import_line="from streetworks.idee import IdeeTransportesClient",
    ),
    ProviderEntry(
        key="lmi",
        name="Landmælingar Íslands (IS 50V road network)",
        description="Iceland's national road network, published by the National Land Survey.",
        kind=Kind.STREETS,
        territories=frozenset({"Iceland"}),
        administrative_area="Landmælingar Íslands (National Land Survey of Iceland)",
        scope_note=(
            "Confirmed live (2026-08-17) - credential-free, this SDK's "
            "first Icelandic streets/gazetteer provider. A real sibling "
            "to Iceland's existing roadworks coverage (IRCA/Vegagerðin, "
            "streetworks.datex2.irca) - both point to the same real "
            "agency, Vegagerðin, confirmed via this layer's own "
            "gagnaeigandi field. 58,266 real national road-segment "
            "features, 84.0% carrying a real stated name - confirmed "
            "against the complete dataset, not a naive IS NOT NULL "
            "check, which overstated this at 99.98% (a real majority of "
            "unnamed rows store a literal single-space string, not "
            "NULL) - see module docstring. A separate INSPIRE Transport "
            "Networks layer also exists on this deployment but carries "
            "no name field at all, the same outcome Germany's BKG and "
            "Gibraltar's own INSPIRE layer had; this native IS 50V "
            "layer was built instead. Licence: Creative Commons "
            "Attribution 4.0 International, confirmed live directly "
            "from Landmælingar Íslands' own licence page."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="register",
        _module="streetworks.lmi",
        _client_name="LmiStreetsClient",
        import_line="from streetworks.lmi import LmiStreetsClient",
    ),
    ProviderEntry(
        key="digiroad",
        name="Digiroad (Finland)",
        description="Finland's real national road/street network, over Väylävirasto's open WFS.",
        kind=Kind.STREETS,
        territories=frozenset({"Finland"}),
        administrative_area="Väylävirasto (Finnish Transport Infrastructure Agency)",
        scope_note=(
            "Confirmed live (2026-08-17) - credential-free, this SDK's "
            "first Finnish streets/gazetteer provider, and a real "
            "sibling to Finland's existing roadworks coverage "
            "(Digitraffic, streetworks.datex2.digitraffic) from the "
            "same real government department. Maanmittauslaitos' own "
            "Maastotietokanta was checked first but genuinely requires "
            "a self-service API key (confirmed live via a real 401) - "
            "per this project's own access-boundary rules, not "
            "registered on the project's behalf; Väylävirasto's "
            "separate WFS deployment is genuinely keyless instead. "
            "3,363,654 real national road-link features - three "
            "identically-shaped layer names on this deployment "
            "(confirmed via DescribeFeatureType and resultType=hits) "
            "resolve to the same real table, the same cartographic-view "
            "trap TIGERweb's own layers 0-9 were. Real bilingual names "
            "(Finnish/Swedish, Finland's genuine official convention) "
            "carried as two Name objects via Name.language, never "
            "merged. Real 3D geometry - Z genuinely present and "
            "preserved through reprojection, never defaulted to zero. "
            "Licence: Creative Commons Attribution 4.0 International, "
            "confirmed live from the dataset's own avoindata.fi entry."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="register",
        _module="streetworks.digiroad",
        _client_name="DigiroadClient",
        import_line="from streetworks.digiroad import DigiroadClient",
    ),
    ProviderEntry(
        key="marousi",
        name="Δήμος Αμαρουσίου (Marousi, Greece)",
        description="A real Greek municipality's own street-name register, over its GeoServer WFS.",
        kind=Kind.STREETS,
        territories=frozenset({"Greece", "Marousi"}),
        administrative_area="Δήμος Αμαρουσίου (Municipality of Marousi)",
        scope_note=(
            "Confirmed live (2026-08-17) - credential-free, this SDK's "
            "first Greek gazetteer coverage. A pilot for a real, "
            "genuine per-municipality fan-out (580 real datasets on "
            "data.gov.gr matching 'streets'), not a national build - "
            "Greece's official INSPIRE geoportal (geodata.gov.gr) times "
            "out completely on every real connection attempt, the same "
            "real failure streetworks.greece already documented for "
            "nap.gov.gr; the national cadastre 403s. 721 real named "
            "street-extent polygon features, 100% carrying a real "
            "name, confirmed against the complete dataset. No stated "
            "point/line field exists on this minimal schema - every "
            "Street carries GeometryGrade.ABSENT, the real polygon "
            "preserved in .raw only, the same discipline "
            "from_guernsey_street established. Licence genuinely "
            "unstated - every one of the 580 real municipal datasets "
            "checked on data.gov.gr shows 'License not specified,' a "
            "real consistent gap, not an oversight on this one; built "
            "on the project owner's explicit instruction, the same "
            "basis Jersey shipped on. See module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.marousi",
        _client_name="MarousiStreetsClient",
        import_line="from streetworks.marousi import MarousiStreetsClient",
    ),
    ProviderEntry(
        key="dar",
        name="Danmarks Adresseregister (DAR)",
        description="Denmark's national named-road register, over Datafordeleren's REST API.",
        kind=Kind.STREETS,
        territories=frozenset({"Denmark"}),
        administrative_area="SDFI (Danish Agency for Data Supply and Infrastructure)",
        scope_note=(
            "Confirmed live (2026-08-18) - credential-free, this SDK's "
            "first Danish streets/gazetteer provider, a real sibling to "
            "Denmark's existing roadworks coverage (Copenhagen/"
            "Gravetilladelser, streetworks.copenhagen; Vejdirektoratet, "
            "Credentials wanted). Built against DAR's own Navngivenvej "
            "(named-road) entity on Datafordeleren, not the originally "
            "checked DAWA (api.dataforsyningen.dk) - DAWA's own docs "
            "carry a live 'DAWA lukker' warning, confirmed via web "
            "search to be closing toward 1 October 2026, superseded by "
            "Datafordeleren; building on a feed six weeks from shutdown "
            "would ship something already due to break. 99.96% of a "
            "live 5000-record sample carries a real stated name - the "
            "highest name coverage of any streets provider built this "
            "session. Real CRS-only gap: this REST endpoint states only "
            "ETRS89/UTM32N (EPSG:25832) geometry, confirmed live (a "
            "srid=EPSG:4326 parameter was tried and rejected with a "
            "real 400) - reprojected client-side via a closed-form "
            "Transverse Mercator inverse (streetworks.common._utm32n, "
            "no Helmert step needed since ETRS89 and WGS84 are "
            "coincident at this SDK's stated accuracy), cross-checked "
            "against DAWA's own real WGS84 output for the same road "
            "(agreement to within a few metres). See module docstring."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="register",
        _module="streetworks.dar",
        _client_name="DarClient",
        import_line="from streetworks.dar import DarClient",
    ),
    ProviderEntry(
        key="swisstopo",
        name="Amtliches Verzeichnis der Strassen (swisstopo)",
        description=(
            "Switzerland's federal street-name register, run by the Federal Office of Topography."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"Switzerland"}),
        administrative_area="swisstopo (Bundesamt für Landestopografie)",
        scope_note=(
            "Confirmed live (2026-08-18) - credential-free, this SDK's "
            "first Swiss streets/gazetteer provider, a sibling to the "
            "existing Swiss roadworks coverage (Kanton Zurich, Stadt "
            "Zurich) at national scale. A genuine federal register, not "
            "a swisstopo-original survey - street names are declared in "
            "the Gebaude- und Wohnungsregister (GWR, run by the Federal "
            "Statistical Office) and transmitted to swisstopo daily, "
            "which adds geometry and republishes. 224,985 real national "
            "street records, 100% carrying a real name and a real "
            "coordinate, zero duplicate IDs - the cleanest coverage "
            "figures of any streets provider this SDK has built. Bulk "
            "CSV chosen over a real, live, keyless point-query API "
            "(api3.geo.admin.ch) since that API only supports search, "
            "not 'everything' - the same bulk-vs-live-query call ANNCSU "
            "(Italy) already made. Geometry is a real single point "
            "(EPSG:2056, Swiss LV95) only, not the live API's own "
            "richer LineString - a deliberate trade-off, not a gap; the "
            "richer INSPIRE-adjacent File Geodatabase/XTF bulk formats "
            "exist too but the XTF alone is a real 842 MB file, too "
            "large for this SDK's no-heavy-GIS-dependency convention. A "
            "real Liechtenstein-scoped sibling resource exists on the "
            "same collection, confirmed live, not fetched by this "
            "client. Licence: swisstopo's own OGD terms (free use, "
            "commercial and non-commercial, mandatory source "
            "attribution), confirmed live. See module docstring."
        ),
        credentials=None,
        licence=(
            "swisstopo OGD terms (free use, commercial and non-commercial, attribution required)"
        ),
        source_grade="register",
        _module="streetworks.swisstopo",
        _client_name="SwisstopoStreetsClient",
        import_line="from streetworks.swisstopo import SwisstopoStreetsClient",
    ),
    ProviderEntry(
        key="bev",
        name="Österreichisches Adressregister (BEV)",
        description=(
            "Austria's national street-name register, run by the Federal Office "
            "of Metrology and Surveying."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"Austria"}),
        administrative_area="BEV (Bundesamt für Eich- und Vermessungswesen)",
        scope_note=(
            "Confirmed live (2026-08-18) - credential-free, this SDK's "
            "first Austrian streets/gazetteer provider, a sibling to "
            "the existing Austrian roadworks coverage (Vienna's own "
            "WFS; ASFINAG's national Credentials-wanted scaffold). Not "
            "the first source found - BEV's own product page "
            "(bev.gv.at) lists a paid, per-record shop product; a "
            "separate free CC-BY-4.0 line was found instead on BEV's "
            "own data.bev.gv.at GeoNetwork portal (distinct from the "
            "general data.gv.at national portal, a JS SPA with no "
            "easily discoverable API). 137,767 real national street "
            "rows, 100% carrying a real name, zero duplicate SKZ - the "
            "same pure name-registry shape ANNCSU (Italy) already "
            "established, joined against a real 2,092-row municipality "
            "table (GEMEINDE.csv, a clean 1:1 join, confirmed against "
            "the complete dataset) so administrative_area carries a "
            "resolved name, not a bare code. No geometry anywhere in "
            "this resource - GeometryGrade.ABSENT on every Street, not "
            "a gap - real coordinates exist only on a much larger "
            "sibling address-level resource (325MB ADRESSE.csv, plus a "
            "separate ~183MB INSPIRE address product), deliberately not "
            "fetched here, the same streets-built/address-side-scoped-"
            "out call ANNCSU already made. A real, disclosed "
            "limitation: this product is a periodically dated snapshot "
            "('Stichtag') with no stable latest-alias URL found "
            "anywhere checked - BASE_URL points at the most recent "
            "snapshot confirmed live (Stichtag 01.10.2025) at "
            "investigation time; a future maintainer will need to "
            "update it once BEV publishes a newer one. See module "
            "docstring."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="register",
        _module="streetworks.bev",
        _client_name="BevStreetsClient",
        import_line="from streetworks.bev import BevStreetsClient",
    ),
    ProviderEntry(
        key="vlaanderen",
        name="Straatnamenregister (Flanders, Belgium)",
        description=(
            "Flanders' (not all-Belgium's) street-name register, part of "
            "Basisregisters Vlaanderen."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"Belgium"}),
        administrative_area="Vlaamse overheid (Flanders)",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free, this SDK's "
            "first Belgian streets/gazetteer provider, a sibling to the "
            "existing Belgian roadworks coverage (Verkeerscentrum "
            "Vlaanderen, streetworks.datex2.belgium) - both genuinely "
            "Flanders-only, not all-Belgium (Wallonia publishes its own "
            "separate feed, not wrapped here; Brussels wasn't checked). "
            "Not the layer first checked - Informatie Vlaanderen's own "
            "Wegenregister WFS carries real line geometry but street "
            "identity there is a genuinely richer, two-sided shape "
            "(linkerstraatnaam/rechterstraatnaam can differ) closer to "
            "NWB's own segment-aggregation model than a queryable named "
            "entity; the Basisregisters Vlaanderen REST API's own "
            "Straatnaam resource was used instead. Roughly 99,600 real "
            "street names (bounded live via offset bisection - no total "
            "count field exists on the list response). No geometry on "
            "this resource - GeometryGrade.ABSENT on every Street, the "
            "same shape ANNCSU/BEV already established. A real, "
            "confirmed API quirk: the documented gemeenteniscode filter "
            "parameter is silently ignored (three requests - two "
            "different codes and none at all - returned byte-identical "
            "results); an undocumented gemeentenaam= text filter "
            "genuinely works but would need an unattempted "
            "~300-municipality fan-out, so administrative_area is left "
            "unresolved. Licence: Flanders' standard "
            "'Modellicentie Gratis Hergebruik' (free reuse, attribution "
            "required) - the government's stated default, not this "
            "API's own confirmed per-dataset licence field. See module "
            "docstring."
        ),
        credentials=None,
        licence=(
            "Modellicentie Gratis Hergebruik (Flanders' standard free-reuse licence, "
            "attribution required) - stated default, not per-dataset-confirmed"
        ),
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.vlaanderen",
        _client_name="VlaanderenStreetsClient",
        import_line="from streetworks.vlaanderen import VlaanderenStreetsClient",
    ),
    ProviderEntry(
        key="registrucentras",
        name="Adresų registras (Registrų centras, Lithuania)",
        description=(
            "Lithuania's national street-centerline register, run by the State "
            "Enterprise Centre of Registers."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"Lithuania"}),
        administrative_area="Registrų centras (State Enterprise Centre of Registers)",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free, this SDK's "
            "first Lithuanian streets/gazetteer provider, a sibling to "
            "the existing Lithuanian roadworks coverage (Via Lietuva, "
            "streetworks.vialietuva). 22,547 real national street "
            "records, 100% carrying a real name and real geometry, zero "
            "duplicate street codes. Found via data.gov.lt's own DCAT "
            "dataset page; its promoted download link bakes a version "
            "number into the URL (the same no-stable-latest-alias shape "
            "Austria's BEV register has), but a shorter distribution "
            "link on the same page was followed and found to redirect "
            "to a real, stable, version-less route "
            "(get.data.gov.lt/datasets/gov/rc/ar/gragatve/GraGatve, "
            "confirmed byte-identical to the versioned URL) - used "
            "instead. A real, confirmed axis-order quirk found live: "
            "the source's own WKT geometry states coordinate pairs as "
            "(Northing, Easting), not the standard WKT/GeoJSON (X, Y) "
            "order - confirmed by bounds-checking a real sample point "
            "against LKS-94's own real Lithuanian easting/northing "
            "ranges, both ways. Reprojected client-side from LKS-94 "
            "(EPSG:3346) via a new closed-form Transverse Mercator "
            "inverse (streetworks.common._lks94), no server-side "
            "reprojection option existing on this plain REST/JSON "
            "resource. administrative_area is left unresolved - the "
            "real settlement reference on each row would need a "
            "disproportionate 127MB separate national dataset just to "
            "label one field, unlike Austria's BEV, whose own "
            "municipality lookup was a cheap 51KB bundled table. "
            "Licence: CC BY 4.0, confirmed live. See module docstring."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="register",
        _module="streetworks.registrucentras",
        _client_name="RegistruCentrasStreetsClient",
        import_line="from streetworks.registrucentras import RegistruCentrasStreetsClient",
    ),
    ProviderEntry(
        key="caclr",
        name="CACLR (Registre national des localités et des rues, Luxembourg)",
        description=(
            "Luxembourg's national street register, run by the Administration du "
            "Cadastre et de la Topographie."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"Luxembourg"}),
        administrative_area="ACT (Administration du Cadastre et de la Topographie)",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free, this SDK's "
            "first Luxembourgish streets/gazetteer provider, a sibling "
            "to the existing Luxembourg roadworks coverage (Ponts et "
            "Chaussées, streetworks.datex2.luxembourg). Not a modern "
            "WFS/REST feed - the live geoportail.lu WFS was checked "
            "first and ruled out (MapServer-based, no working per-theme "
            "map identifier found; its GeoNetwork catalogue search API "
            "only returned real 400s). The real route is CACLR's own "
            "bulk export on data.public.lu (a udata instance, same "
            "software family as France's data.gouv.fr) - a real, fixed-"
            "width flat-file format confirmed field-by-field from ACT's "
            "own published PostgreSQL import script. 9,946 real "
            "national street records, 100% carrying a real name, zero "
            "duplicate street numbers. A real, stable 'current resource' "
            "API (data.public.lu's own udata REST endpoint) is used to "
            "resolve the real download URL each call, rather than "
            "hardcoding the dataset page's own dated-snapshot link - "
            "genuinely self-updating, unlike the workaround this SDK "
            "used for Austria's BEV register. A real join trap found "
            "and worked around before shipping: Luxembourg's commune "
            "codes are only unique within their own canton, confirmed "
            "live - joining on the bare code alone resolves a real "
            "Luxembourg-City street to the wrong commune ('Burmerange', "
            "~30km away); the real composite (canton, commune) key both "
            "tables carry resolves it correctly. No geometry anywhere "
            "in this resource - GeometryGrade.ABSENT on every Street, "
            "the same shape ANNCSU/BEV already established. Licence: "
            "Creative Commons Zero (CC0), confirmed live - the most "
            "permissive licence any provider in this SDK carries. See "
            "module docstring."
        ),
        credentials=None,
        licence="Creative Commons Zero (CC0)",
        source_grade="register",
        _module="streetworks.caclr",
        _client_name="CaclrStreetsClient",
        import_line="from streetworks.caclr import CaclrStreetsClient",
    ),
    ProviderEntry(
        key="hamburg_streets",
        name="Zentraler AdressService Hamburg (GAGES)",
        description=(
            "Hamburg's own street gazetteer, run jointly by the state statistics and "
            "surveying offices."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"Germany"}),
        administrative_area="Hamburg",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free, this SDK's "
            "first German state-level streets/gazetteer provider. "
            "Berlin was checked first - genuinely blocked, not ruled "
            "out: its own GDI WFS host (gdi.berlin.de, serving every "
            "Berlin geodata WFS) is confirmed live to be down for "
            "maintenance across every real path tried, no ETA stated - "
            "a real, reportable connectivity failure, not routed "
            "around. Hamburg's own joint StA-Nord/LGV gazetteer "
            "(GAGES) was checked instead, over a real, live, keyless "
            "OGC API Features service (found via the dataset's own "
            "catalogue page, not the archived FIS-Broker-era WFS it "
            "still lists). 9,639 real Hamburg street records, 100% "
            "carrying a real name. Real Point geometry, genuinely "
            "reprojected server-side to WGS84 by this API's own "
            "default (native storage is EPSG:25832). "
            "administrative_area is a per-provider constant "
            "('Hamburg') - a finer real Ortsteil (district) code exists "
            "inline in one composite field but no separate lookup "
            "collection exists on this API to resolve it to a name. "
            "Licence: Datenlizenz Deutschland - Namensnennung - 2.0, "
            "confirmed live from the dataset's own CKAN metadata. See "
            "module docstring."
        ),
        credentials=None,
        licence="Datenlizenz Deutschland - Namensnennung - 2.0 (DL-DE-BY-2.0)",
        source_grade="register",
        _module="streetworks.hamburg",
        _client_name="HamburgStreetsClient",
        import_line="from streetworks.hamburg import HamburgStreetsClient",
    ),
    ProviderEntry(
        key="brandenburg_streets",
        name="WFS BB-BE Gazetteer (Brandenburg)",
        description=(
            "Brandenburg's own street gazetteer, run by the state surveying and "
            "geoinformation agency."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"Germany"}),
        administrative_area="Land Brandenburg (LGB)",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free, this SDK's "
            "second German state-level streets/gazetteer provider "
            "(after Hamburg's own GAGES), continuing the 'state "
            "fan-out' fallback path Germany's national streets "
            "investigation left open. 52,902 real street records, "
            "confirmed live via resultType=hits - much larger than "
            "Hamburg's 9,639, consistent with Brandenburg's far "
            "greater land area. A real, confirmed GML-only WFS - no "
            "JSON output format exists (a real outputFormat=application/"
            "json request was rejected with a genuine 400), so this "
            "module parses real GML/XML directly via the standard "
            "library's own xml.etree.ElementTree rather than using the "
            "shared JSON-first OGCFeaturesClient. Real, comprehensive "
            "per-record fields, richer than Hamburg's own schema - "
            "administrative_area is reconstructed from two real, "
            "independently-stated fields (ortsnamePost + "
            "zusatzOrtsname), confirmed live to match the record's own "
            "gemeindename_normalisiert field, not a guessed "
            "concatenation. The only real geometry stated is a Polygon "
            "(the street's areal extent) - GeometryGrade.ABSENT on "
            "every Street, the same discipline from_marousi_street "
            "already established for its own polygon-only source; the "
            "real polygon is preserved unmodified on .raw. A real, "
            "live-confirmed, non-exhaustive Berlin presence: this "
            "source's own land field carries both Brandenburg's and "
            "Berlin's real German state codes (8/500 in a live sample "
            "were Berlin) - scoped and documented as Brandenburg's own "
            "provider, not a claim of exhaustive Berlin coverage. "
            "Licence: Datenlizenz Deutschland - Namensnennung - 2.0, "
            "confirmed live from this WFS's own GetCapabilities "
            "AccessConstraints element. See module docstring."
        ),
        credentials=None,
        licence="Datenlizenz Deutschland - Namensnennung - 2.0 (DL-DE-BY-2.0)",
        source_grade="register",
        _module="streetworks.brandenburg",
        _client_name="BrandenburgStreetsClient",
        import_line="from streetworks.brandenburg import BrandenburgStreetsClient",
    ),
    ProviderEntry(
        key="geosn_streets",
        name="GeoSN Hauskoordinaten (Saxony)",
        description=(
            "Saxony's statewide address-point export, deduplicated to streets by the "
            "state surveying agency."
        ),
        kind=Kind.STREETS,
        territories=frozenset({"Germany"}),
        administrative_area="Freistaat Sachsen (GeoSN)",
        scope_note=(
            "Confirmed live (2026-08-20) - credential-free, this SDK's "
            "third German state-level streets/gazetteer provider, "
            "completing the 'state fan-out' Germany's national streets "
            "investigation named (Hamburg, Brandenburg, Saxony, "
            "Berlin). Not the shared Deutschland-Online-Gazetteer WFS "
            "Hamburg and Brandenburg both use - confirmed live that "
            "Saxony genuinely doesn't participate in it (that "
            "service's own real member states are Brandenburg and "
            "Berlin only), and Saxony's own ALKIS WFS carries no "
            "street/address feature type at all. Saxony instead "
            "publishes a real statewide address-point bulk export "
            "(~206MB uncompressed, ~51MB zipped, the largest single "
            "download this SDK's German-state cluster has needed) - "
            "990,090 real address rows, 100% carrying a real street "
            "name, deduplicated to 42,824 real distinct (municipality, "
            "street) combinations by the client itself, since this is "
            "address-point data, not a dedicated street register. "
            "Geometry is a real address point, reprojected client-side "
            "from ETRS89/UTM zone 33N (EPSG:25833, confirmed live via "
            "the file's own zone column and cross-checked against a "
            "real Frohburg address) - standard axis order, no swap "
            "needed, unlike Lithuania's own UTM-family source. "
            "administrative_area carries the real gmd (municipality "
            "name) field directly - already resolved, unlike "
            "Brandenburg's own two-field reconstruction. Licence: "
            "Datenlizenz Deutschland - Namensnennung - 2.0, confirmed "
            "live and explicitly stated to permit commercial reuse. "
            "See module docstring."
        ),
        credentials=None,
        licence="Datenlizenz Deutschland - Namensnennung - 2.0 (DL-DE-BY-2.0)",
        source_grade="register",
        _module="streetworks.geosn",
        _client_name="GeoSNStreetsClient",
        import_line="from streetworks.geosn import GeoSNStreetsClient",
    ),
    ProviderEntry(
        key="osni",
        name="OSNI Open Data - Gazetteer - Streetnames",
        description="Northern Ireland's street-name gazetteer - name plus one point.",
        kind=Kind.STREETS,
        territories=frozenset({"Northern Ireland"}),
        administrative_area="Ordnance Survey Northern Ireland (OSNI)",
        scope_note=(
            "Confirmed live (2026-08-16) - credential-free, via a real "
            "bulk-download route, not the documented ArcGIS REST "
            "MapServer endpoint, which is currently down (the whole "
            "services.spatialni.gov.uk domain redirects to a broken "
            "NICS holding page). A genuinely thinner shape than a full "
            "street/address register - name plus one point, no ASD-"
            "style richness. Carries a real, fully-populated, fully-"
            "unique USRN field, but it is OSNI's own, not confirmed to "
            "cross-reference GB's national USRN/NSG scheme - Northern "
            "Ireland sits outside that scheme, so this is scoped "
            "'OSNI', not presented as a national identifier. CRS is "
            "Irish Grid (EPSG:29902, TM65), used from the feed's own "
            "X_Coord/Y_Coord fields rather than its reprojected WGS84 "
            "geometry - corrected from an initial EPSG:29903 guess once "
            "a directly comparable NI government service (dfi_roads) "
            "confirmed EPSG:29902 live for the same coordinate family; "
            "still not a direct live read of this dataset's own CRS, "
            "since OSNI's own endpoint is the same one that's down. "
            "Jurisdiction-distinct, same treatment as Jersey/Scotland - "
            "never folded under a generic UK territory. See module "
            "docstring."
        ),
        credentials=None,
        licence="Open Government Licence v3.0 (OGL)",
        source_grade="register",
        _module="streetworks.osni",
        _client_name="OsniStreetnamesClient",
        import_line="from streetworks.osni import OsniStreetnamesClient",
    ),
    ProviderEntry(
        key="dfi_roads",
        name="DfI Roads Highway Network centreline",
        description="Northern Ireland's real, maintained road-network centreline geometry.",
        kind=Kind.STREETS,
        territories=frozenset({"Northern Ireland"}),
        administrative_area="Department for Infrastructure (DfI) Roads",
        scope_note=(
            "Confirmed live (2026-08-16) - credential-free. The real "
            "geometry counterpart to osni's name+point gazetteer. The "
            "promoted 'open data' CSV/XML downloads are genuinely "
            "attribute-only - zero geometry, despite being called a "
            "centreline product - so this client uses the real ArcGIS "
            "FeatureServer behind the public map viewer instead, found "
            "by tracing the viewer app's own item/web-map/layer chain. "
            "Not built on this SDK's shared ArcGISFeatureClient, since "
            "that client's f=geojson-first behaviour would silently "
            "reproject this service's real Irish Grid coordinates to "
            "WGS84 without ever triggering its native-format fallback - "
            "confirmed live, not assumed. CRS is EPSG:29902 (TM65 / "
            "Irish Grid), read directly from this service's own "
            "spatialReference, not inferred - the same code osni's own "
            "CRS label was corrected to match once this evidence "
            "existed. Real, genuinely two-valued ADOPTION_S field "
            "(Adopted/Unadopted) - iter_road_sections() defaults to "
            "adopted-only. No USRN or USRN-shaped field exists in this "
            "schema. See module docstring."
        ),
        credentials=None,
        licence="Open Government Licence v3.0 (OGL)",
        source_grade="register",
        _module="streetworks.dfi_roads",
        _client_name="DfiRoadsClient",
        import_line="from streetworks.dfi_roads import DfiRoadsClient",
    ),
    ProviderEntry(
        key="anncsu",
        name="ANNCSU (Anagrafe Nazionale Numeri Civici e Strade Urbane)",
        description="Italy's national street-name register - name only, no geometry.",
        kind=Kind.STREETS,
        territories=frozenset({"Italy"}),
        administrative_area="Agenzia delle Entrate / ISTAT",
        scope_note=(
            "Confirmed live (2026-08-16) - credential-free, this SDK's "
            "first Italian streets gazetteer. A genuine national street-"
            "name registry (1,219,990 real streets), jointly run by "
            "Agenzia delle Entrate and ISTAT since DPCM 12 May 2016. "
            "Streets only, deliberately - the address/civic-number side "
            "of the same registry is real but has only partial "
            "coordinate coverage and was scoped out; see "
            "docs/providers/pending.md. Uses the real national bulk "
            "download (a keyless ZIP+CSV), not the separate live "
            "point-query API, since the API only supports lookup by "
            "municipality plus a name match, not 'give me everything'. "
            "No geometry exists anywhere in this resource - a real, "
            "defining characteristic, not a gap: every Street converts "
            "with GeometryGrade.ABSENT, the same documented state OS "
            "Open USRN already establishes. Two real, independently-"
            "stated municipality identifiers are kept (the traditional "
            "'Belfiore' code and ISTAT's own numeric code). See module "
            "docstring."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="register",
        _module="streetworks.anncsu",
        _client_name="AnncsuClient",
        import_line="from streetworks.anncsu import AnncsuClient",
    ),
    ProviderEntry(
        key="gibraltar",
        name="Gibraltar Street Gazetteer",
        description="Gibraltar's real named-road layer, over the Geoportal's own GeoServer WFS.",
        kind=Kind.STREETS,
        territories=frozenset({"Gibraltar"}),
        administrative_area="HM Government of Gibraltar",
        scope_note=(
            "Confirmed live (2026-08-16) - credential-free, this SDK's "
            "first British Overseas Territory coverage. Found by "
            "walking the Geoportal's service-wide WFS capabilities, "
            "not just its INSPIRE workspace - the INSPIRE-mandated "
            "TN_RoadTransportNetwork_RoadLink layer is real but carries "
            "no name field anywhere, the same 'geometry with no "
            "identity' outcome Germany's BKG WFS had; the native "
            "gibgis:roads_lb_vw layer underneath is the real, named one "
            "(277 real streets). Genuinely multi-part MultiLineString "
            "geometry on 54% of real records - Coordinate.parts is "
            "always used, never a first-line-only shortcut. Licence: "
            "no single confirmed open document - built on the project "
            "owner's explicit instruction, the same basis Jersey "
            "shipped on; see module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.gibraltar",
        _client_name="GibraltarStreetsClient",
        import_line="from streetworks.gibraltar import GibraltarStreetsClient",
    ),
    ProviderEntry(
        key="drivebc",
        name="DriveBC (British Columbia, Open511)",
        description="British Columbia's provincial road-events feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Canada"}),
        administrative_area="Province of British Columbia (DriveBC)",
        scope_note=(
            "Confirmed live (2026-08-08, 246 real events) - "
            "credential-free, never a Credentials-wanted scaffold. This "
            "SDK's first Canadian roadworks provider (Quebec City is "
            "already covered separately, via the existing wzdx feed "
            "registry - a real, active feed, not a new build). BC's own "
            "implementation of Open511, a Canadian-origin multi-"
            "jurisdiction standard - built bespoke as streetworks.drivebc "
            "rather than a general streetworks.open511 parser: checked "
            "live before committing to a shared parser, and DriveBC is "
            "the only real, confirmed "
            "roadworks-events Open511 implementation found (San "
            "Francisco Bay Area 511's Open511 use is transit data, a "
            "different resource) - the same 'extract shared code only on "
            "the second real consumer' pattern already applied to Paris "
            "Chantiers over a premature streetworks.opendatasoft. "
            "event_type == 'CONSTRUCTION' is the roadworks filter "
            "(194/246 real events); INCIDENT/ROAD_CONDITION/"
            "WEATHER_CONDITION excluded. Two real, mutually-exclusive "
            "schedule shapes exist (intervals vs. recurring_schedules, "
            "222/24 real events) - a genuine finding beyond what was "
            "originally planned for, see module docstring. "
            "network_scope=strategic: "
            "every real event's areas[] names one of BC MoTI's own "
            "internal Districts, never a municipality, though roads[] "
            "includes real unnumbered local-sounding names on 'Other "
            "Roads' events (67/246) - not confirmed to ever cross into "
            "municipal territory, but flagged rather than silently "
            "assumed comprehensive."
        ),
        credentials=None,
        licence=(
            "Open Government Licence - British Columbia (OGL-BC), "
            "confirmed live from the API's own /help page ('Use of the "
            "Information provided by this API is governed by the "
            "OGL-BC') - worldwide, royalty-free, commercial use "
            "permitted, attribution required. The jurisdiction "
            "resource's own license_url field (a data.gov.bc.ca PDF "
            "path) is dead - confirmed 404-redirects to a generic "
            "catalogue page - so this cites the real, live OGL-BC text "
            "instead, not that stale pointer"
        ),
        source_grade="operator",
        _module="streetworks.drivebc",
        _client_name="DriveBCClient",
        import_line="from streetworks.drivebc import DriveBCClient",
    ),
    ProviderEntry(
        key="quebec",
        name="Québec (MTQ Travaux routiers)",
        description="Québec province's own roadworks feed, from the Ministère des Transports.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Canada"}),
        administrative_area="Ministère des Transports et de la Mobilité durable (MTQ)",
        scope_note=(
            "Confirmed live (2026-08-21, 526 real features) - "
            "credential-free, never a Credentials-wanted scaffold. This "
            "SDK's first Canadian *provincial* roadworks provider "
            "(DriveBC/British Columbia is regional-authority-scoped, not "
            "province-wide the same way; Quebec City's own separate WZDx "
            "feed remains a distinct real municipal authority, never "
            "deduplicated against this one). Found via Données Québec "
            "(the provincial open-data portal), over MTQ's own plain WFS "
            "2.0.0 (MapServer) deployment - the same generic "
            "streetworks.ogc.client.OGCFeaturesClient this SDK's German "
            "state cluster and streetworks.lyon already use, no new "
            "fetch code needed. identifiantChantier genuinely groups "
            "multiple real entraves into one project (391 distinct "
            "chantiers across 526 records, 71 with 2-5 real entraves "
            "each) - the same shape Jersey's own PROJID/JOBID gives. No "
            "independent verified/status flag exists, so date_confidence "
            "is uniformly ESTIMATED, the same reasoning drivebc's own "
            "comparable live feed already documents. A genuinely "
            "bilingual official source - descriptionFrancais/"
            "descriptionAnglais are both real, MTQ-published fields, not "
            "one derived from the other; French is used as the canonical "
            "text, English stays in .raw. See module docstring."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        licence_confirmed=True,
        source_grade="operator",
        _module="streetworks.quebec",
        _client_name="QuebecClient",
        import_line="from streetworks.quebec import QuebecClient",
    ),
    ProviderEntry(
        key="on511",
        name="Ontario 511",
        description="Ontario's own real-time roadwork/incident feed (North American 511 platform).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Canada"}),
        administrative_area="Ontario Ministry of Transportation (MTO)",
        scope_note=(
            "Confirmed live (2026-08-21, 590 real roadwork events of 595 "
            "total) - credential-free, never a Credentials-wanted "
            "scaffold, despite the site's own 'Sign up for an account' "
            "prompt (confirmed to gate only human-facing My511 "
            "personalisation, not the API). Genuinely the same "
            "commercial 511 platform Alberta ('ab511') and Saskatchewan "
            "('sk511') also run (identical endpoint/field shape, "
            "confirmed field-for-field against Alberta's own published "
            "docs) - one shared streetworks.na511.NA511Client, keyed by "
            "jurisdiction per call, the same shape "
            "streetworks.ogc.germany.GermanRoadworksClient already gives "
            "its own .fetch(state). EventType=='roadwork' is the real "
            "filter. Real Google Encoded Polyline geometry on ~50% of "
            "real events, decoded and confirmed correct against each "
            "record's own separately-stated Latitude/Longitude. See "
            "streetworks.na511.client's own module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        _module="streetworks.na511",
        _client_name="NA511Client",
        import_line='from streetworks.na511 import NA511Client  # .fetch("ontario")',
    ),
    ProviderEntry(
        key="ab511",
        name="511 Alberta",
        description="Alberta's own real-time roadwork/incident feed (North American 511 platform).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Canada"}),
        administrative_area="Alberta Transportation and Economic Corridors",
        scope_note=(
            "Same real platform as Ontario 511 ('on511') - see that "
            "entry and streetworks.na511.client's own module docstring. "
            "Confirmed live with a real developer key (2026-08-22): 302 "
            "real events round-tripped through the exact same parsing "
            "Ontario's keyless response already proved, no code changes "
            "needed - 161 real roadwork events, 54 with a real decoded "
            "polyline. Surfaced a genuine correction along the way: the "
            "real EventType enum has six values, not three - Ontario's "
            "own sample never showed restrictionClass/generalInfo/"
            "specialEvents, but the roadwork filter itself stayed exactly "
            "correct on this materially less roadwork-skewed real "
            "population."
        ),
        credentials="511 API developer key (self-service registration - see module docstring)",
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        _module="streetworks.na511",
        _client_name="NA511Client",
        import_line='from streetworks.na511 import NA511Client  # .fetch("alberta")',
    ),
    ProviderEntry(
        key="sk511",
        name="Saskatchewan Highway Hotline",
        description="Saskatchewan's own real-time roadwork/incident feed (North American 511)",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Canada"}),
        administrative_area="Saskatchewan Ministry of Highways",
        scope_note=(
            "Same real platform as Ontario 511 ('on511') and 511 "
            "Alberta ('ab511') - see those entries and "
            "streetworks.na511.client's own module docstring. The real "
            "API endpoint is still live and requires a key (the "
            "identical structured 'Invalid Key' rejection, confirmed "
            "2026-08-21) - not obtained on a caller's behalf, same "
            "standing rule as Alberta/Massachusetts CWZ. But the public "
            "self-service developer signup path itself has since been "
            "taken down (confirmed live 2026-08-21: /developers/doc "
            "404s, /developers redirects to /notfound, no dev/API link "
            "found anywhere on the current site) - a real regression "
            "from when this was found days earlier, not assumed still "
            "there. No known current route to a key; flagged honestly "
            "rather than left silently stale."
        ),
        credentials="511 API developer key (self-service path no longer found - see scope_note)",
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        verified=False,
        _module="streetworks.na511",
        _client_name="NA511Client",
        import_line='from streetworks.na511 import NA511Client  # .fetch("saskatchewan")',
    ),
    ProviderEntry(
        key="nb511",
        name="New Brunswick 511",
        description="New Brunswick's own real-time roadwork/incident feed (North American 511).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Canada"}),
        administrative_area="New Brunswick Department of Transportation and Infrastructure",
        scope_note=(
            "Same real platform as Ontario 511 ('on511') - see that "
            "entry and streetworks.na511.client's own module docstring. "
            "Confirmed live (2026-08-21) to require a real developer "
            "key (the identical structured 'Invalid Key' rejection) - "
            "not obtained on a caller's behalf, same standing rule as "
            "Alberta/Massachusetts CWZ. The field schema is not a "
            "guess: proven by Ontario's own real, unauthenticated "
            "response on the identical platform."
        ),
        credentials="511 API developer key (self-service registration - see module docstring)",
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        verified=False,
        _module="streetworks.na511",
        _client_name="NA511Client",
        import_line='from streetworks.na511 import NA511Client  # .fetch("new_brunswick")',
    ),
    ProviderEntry(
        key="nl511",
        name="Newfoundland and Labrador 511",
        description="NL's own real-time roadwork/incident feed (North American 511 platform).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Canada"}),
        administrative_area=(
            "Newfoundland and Labrador Department of Transportation and Infrastructure"
        ),
        scope_note=(
            "Same real platform as Ontario 511 ('on511') - see that "
            "entry and streetworks.na511.client's own module docstring. "
            "Confirmed live (2026-08-21) to require a real developer "
            "key (the identical structured 'Invalid Key' rejection) - "
            "not obtained on a caller's behalf, same standing rule as "
            "Alberta/Massachusetts CWZ. The field schema is not a "
            "guess: proven by Ontario's own real, unauthenticated "
            "response on the identical platform."
        ),
        credentials="511 API developer key (self-service registration - see module docstring)",
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        verified=False,
        _module="streetworks.na511",
        _client_name="NA511Client",
        import_line=(
            'from streetworks.na511 import NA511Client  '
            '# .fetch("newfoundland_and_labrador")'
        ),
    ),
    ProviderEntry(
        key="ns511",
        name="Nova Scotia 511",
        description="Nova Scotia's own real-time roadwork/incident feed (North American 511).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Canada"}),
        administrative_area="Nova Scotia Public Works",
        scope_note=(
            "Same real platform as Ontario 511 ('on511') - see that "
            "entry and streetworks.na511.client's own module docstring. "
            "The real API endpoint still requires a key (the identical "
            "structured 'Invalid Key' rejection, confirmed 2026-08-21) - "
            "not obtained on a caller's behalf, same standing rule as "
            "Alberta/Massachusetts CWZ. Like Saskatchewan ('sk511'), the "
            "public self-service signup page has since been taken down "
            "(/developers/doc 404s, /developers redirects to /notfound) "
            "- no known current route to a key. The field schema is not "
            "a guess either way: proven by Ontario's own real, "
            "unauthenticated response on the identical platform."
        ),
        credentials="511 API developer key (self-service path no longer found - see scope_note)",
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        verified=False,
        _module="streetworks.na511",
        _client_name="NA511Client",
        import_line='from streetworks.na511 import NA511Client  # .fetch("nova_scotia")',
    ),
    ProviderEntry(
        key="yt511",
        name="511 Yukon",
        description="Yukon's own real-time roadwork/incident feed (North American 511 platform).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"Canada"}),
        administrative_area="Yukon Department of Highways and Public Works",
        scope_note=(
            "Same real platform as Ontario 511 ('on511') - see that "
            "entry and streetworks.na511.client's own module docstring. "
            "Confirmed live (2026-08-21) to require a real developer "
            "key (the identical structured 'Invalid Key' rejection) - "
            "not obtained on a caller's behalf, same standing rule as "
            "Alberta/Massachusetts CWZ. The field schema is not a "
            "guess: proven by Ontario's own real, unauthenticated "
            "response on the identical platform. This SDK's first "
            "Canadian *territorial* roadworks coverage."
        ),
        credentials="511 API developer key (self-service registration - see module docstring)",
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        verified=False,
        _module="streetworks.na511",
        _client_name="NA511Client",
        import_line='from streetworks.na511 import NA511Client  # .fetch("yukon")',
    ),
    ProviderEntry(
        key="nv511",
        name="Nevada 511",
        description="Nevada's own real-time roadwork/incident feed (North American 511 platform).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"USA"}),
        administrative_area="Nevada Department of Transportation (NDOT)",
        scope_note=(
            "Found while surveying US roadworks coverage gaps (not in "
            "the WZDx/CWZ US registry at all - confirmed live, no "
            "Nevada row of any kind), then confirmed to be the exact "
            "same commercial platform as Ontario 511 ('on511') and the "
            "six Canadian jurisdictions above - the identical "
            "/api/v2/get/event endpoint, the identical structured "
            "'Invalid Key' rejection, and a real, working "
            "/developers/doc page whose field-by-field documentation "
            "matches exactly. Not obtained on a caller's behalf, same "
            "standing rule as Alberta/Massachusetts CWZ. The field "
            "schema is not a guess: proven by Ontario's own real, "
            "unauthenticated response on the identical platform. This "
            "SDK's first US jurisdiction on this platform. Confirmed "
            "live with a real developer key (2026-08-22): 92 real "
            "events round-tripped through the exact same parsing "
            "Ontario's and Alberta's own responses already proved, no "
            "code changes needed - 74 real roadwork events, 61 with a "
            "real decoded polyline. A second real EventType-enum "
            "cross-check: this pull also carried restrictionClass/"
            "specialEvents records (the same non-roadwork values "
            "Alberta's own pull first surfaced), further confirming the "
            "enum has more than the three values Ontario's sample alone "
            "showed - the roadworks filter itself stayed exactly "
            "correct on a third jurisdiction."
        ),
        credentials="511 API developer key (self-service registration - see module docstring)",
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        _module="streetworks.na511",
        _client_name="NA511Client",
        import_line='from streetworks.na511 import NA511Client  # .fetch("nevada")',
    ),
    ProviderEntry(
        key="ga511",
        name="Georgia 511",
        description="Georgia's own real-time roadwork/incident feed (North American 511 platform).",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.STRATEGIC,
        territories=frozenset({"USA"}),
        administrative_area="Georgia Department of Transportation (GDOT)",
        scope_note=(
            "Found while investigating GDOT's own ArcGIS Hub "
            "'TrafficImpacts' pages - a real dead end, those turned out "
            "to be per-project public-information pages (e.g. 'I-285 & "
            "SR 400 Improvements'), not a live data feed. Checking "
            "Georgia's own 511 site (511ga.org) directly against the "
            "same platform as Ontario 511 ('on511') confirmed it "
            "immediately: the identical /api/v2/get/event endpoint, the "
            "identical structured 'Invalid Key' rejection, and a real, "
            "working /developers/doc page matching field-for-field. Not "
            "obtained on a caller's behalf, same standing rule as "
            "Alberta/Massachusetts CWZ. The field schema is not a "
            "guess: proven by Ontario's own real, unauthenticated "
            "response on the identical platform."
        ),
        credentials="511 API developer key (self-service registration - see module docstring)",
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        verified=False,
        _module="streetworks.na511",
        _client_name="NA511Client",
        import_line='from streetworks.na511 import NA511Client  # .fetch("georgia")',
    ),
    ProviderEntry(
        key="vancouver",
        name="Vancouver Road Ahead",
        description="Vancouver's own real-time/planned roadworks feed, over OpenDataSoft",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Canada"}),
        administrative_area="City of Vancouver",
        scope_note=(
            "Confirmed live (2026-08-21, 27/80/228 real records across "
            "three real datasets) - credential-free, never a "
            "Credentials-wanted scaffold. Found while surveying Canadian "
            "municipal portals (Toronto, Montreal also checked - see "
            "docs/providers/canada.md; Montreal's own real resources are "
            "currently broken, Toronto's real feed has a genuine JSON "
            "defect not yet worked around). Reuses "
            "streetworks.opendatasoft.OpenDataSoftClient directly - the "
            "same platform streetworks.paris and the French département "
            "cluster already use - no new fetch code. Three real "
            "datasets (current closures/under construction/upcoming), "
            "none stating its own tier as a per-record field - "
            "from_vancouver takes status/date_confidence as explicit "
            "caller-supplied arguments per call, the same design "
            "from_wzdx already uses for territory/administrative_area. "
            "geo_point_2d is the one reliably-populated coordinate; a "
            "real GeometryCollection shape (LineStrings mixed with "
            "Polygons) is deliberately not decomposed. See module "
            "docstring."
        ),
        credentials=None,
        licence="Open Government Licence - Vancouver",
        licence_confirmed=True,
        source_grade="operator",
        _module="streetworks.vancouver",
        _client_name="VancouverClient",
        import_line=(
            "from streetworks.vancouver import VancouverClient  "
            "# .iter_current_closures()/.iter_under_construction()/.iter_upcoming()"
        ),
    ),
    ProviderEntry(
        key="toronto",
        name="Toronto Road Restrictions/Closures",
        description="Toronto's own real-time roadwork/closures feed - contractor, permit fields",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Canada"}),
        administrative_area="City of Toronto",
        scope_note=(
            "Confirmed live (2026-08-21, 2,274 real records) - "
            "credential-free, never a Credentials-wanted scaffold. "
            "This SDK's second Canadian municipal roadworks provider "
            "after Vancouver ('vancouver'). Every real record is "
            "roadworks-relevant - type is 'CONSTRUCTION' (1,823) or "
            "'ROAD_CLOSED' (451, every one carrying subType == "
            "'ROAD_CLOSED_CONSTRUCTION'), no non-roadworks value ever "
            "observed, so no filter is applied. A real, confirmed JSON "
            "defect in the source (one stray, un-escaped backslash "
            "inside a free-text description, found live, not a fetch "
            "error) is repaired defensively before parsing - see "
            "streetworks.toronto.client's own module docstring. "
            "contractor is real and populated on 2,214/2,274 records - "
            "richer than most roadworks sources this SDK has. "
            "source/workEventType/permitType are confirmed identical "
            "to each other on every record, but a genuine export "
            "defect leaves 950/2,274 (42%) holding an identical literal "
            "placeholder string instead of real text - carried through "
            "as-is, not filtered. Real bespoke geoPolyline geometry "
            "(comma-joined [lon,lat] pairs, not JSON array syntax or a "
            "Google Encoded Polyline) parsed via a dedicated regex."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        _module="streetworks.toronto",
        _client_name="TorontoClient",
        import_line="from streetworks.toronto import TorontoClient",
    ),
    ProviderEntry(
        key="lisboa",
        name="Câmara Municipal de Lisboa (Condicionamentos de Trânsito)",
        description="Lisbon's municipal traffic-conditioning feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Portugal"}),
        administrative_area="Câmara Municipal de Lisboa",
        scope_note=(
            "Confirmed live (2026-08-09, 694 real features) - "
            "credential-free, never a Credentials-wanted scaffold. This "
            "SDK's first Portugal provider at any level - sidesteps the "
            "national IMT NAP entirely (still credential-parked) via a "
            "separate keyless municipal feed. The catalogue record "
            "(dados.gov.pt) states 'última atualização: 22 de maio de "
            "2023', which alone would suggest a dead dataset (the "
            "Chicago/Madrid stale-portal lesson); checked live before "
            "trusting that - the real platform's own backend, found by "
            "reading its Angular app's bundled JS (the same technique "
            "that found Road Report NT's real backend), returns genuinely "
            "current data (453/694 real features carry a 2026 pedido "
            "id). The endpoint itself "
            "(lisboa.city-platform.com/percursos/ws/app/public/traffic/"
            "closures/) is not documented anywhere public - found only "
            "by reading the app's own client-side code. Roadworks filter "
            "is evidence-based free-text (motivo, 27 real distinct "
            "values, no clean boolean like Madrid's es_obras) - 473/694 "
            "(68%) classified as roadworks; genuinely ambiguous values "
            "(LIGAÇÃO DE RAMAL, AUTOGRUA) are excluded rather than "
            "guessed either way. Comprehensive city-wide coverage - 27 "
            "distinct freguesias (parishes) confirmed live, matching "
            "Lisbon's real administrative divisions, not a subset. "
            "Real MultiLineString geometry (not Point/LineString like "
            "this SDK's other municipal sources) - only the first "
            "sub-line is used, same simplification as Berlin's multi-"
            "LineString GeometryCollection case. See module docstring."
        ),
        credentials=None,
        licence=(
            "CC BY 4.0 - confirmed live at dados.gov.pt's catalogue page "
            "for this exact dataset ('Licença: Creative Commons "
            "Attribution 4.0 - CC BY 4.0', publisher Município de "
            "Lisboa). The catalogue's stale 'última atualização' date is "
            "a metadata-freshness issue, not a licence-currency one - "
            "the licence statement isn't dated the same way and governs "
            "the same official CML dataset the live platform serves"
        ),
        source_grade="operator",
        _module="streetworks.lisboa",
        _client_name="LisboaClient",
        import_line="from streetworks.lisboa import LisboaClient",
    ),
    ProviderEntry(
        key="ip",
        name="Infraestruturas de Portugal (Condicionamentos)",
        description="Portugal's national real-time road restrictions/roadworks feed.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Portugal"}),
        administrative_area="Infraestruturas de Portugal (IP)",
        scope_note=(
            "This SDK's first Portugal *national* roadworks provider - "
            "Lisboa ('lisboa') is municipal. Found by tracing IP's own "
            "live public 'Trânsito em Tempo Real' page, the same "
            "technique that found Lisboa's and Road Report NT's real "
            "backends: the page embeds a real ArcGIS Instant App, "
            "resolved via the sharing REST API to a real webmap naming "
            "four operational layers on one shared ArcGIS MapServer - "
            "Condicionamentos (this entry), Outras Ocorrências, "
            "Acidentes, and a Serra da Estrela driving-conditions layer, "
            "none of the other three consumed here. Confirmed live "
            "2026-08-22: 93 real active records, tipo=='MaintenanceWorks' "
            "(86) or 'ConstructionWorks' (2) are genuine roadworks - "
            "88/93. The other two real values are confirmed, not "
            "assumed, to be something else: PoorRoadInfrastructure (4, "
            "a real defect report, not active repair work) and "
            "GenericIncident (1). The two sibling layers, checked live "
            "rather than trusted by name, are genuinely not roadworks "
            "either. This directly supersedes the earlier NAP-survey "
            "finding that the national NAP (nap-portugal.imt-ip.pt) "
            "carries no roadworks content - genuinely true (confirmed "
            "again by reading its own JS bundle end to end: zero "
            "roadworks vocabulary anywhere), but IP publishes this feed "
            "entirely separately from the NAP registration/catalogue "
            "system. A real 'no defined end' placeholder in datafim "
            "(2050-12-31 23:59:59 UTC, 3/34 real non-null values) is "
            "never surfaced as a real date. See "
            "streetworks.arcgis.ip's own module docstring."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="operator",
        _module="streetworks.arcgis.ip",
        _client_name="IPRoadworksClient",
        import_line="from streetworks.arcgis.ip import IPRoadworksClient",
    ),
    ProviderEntry(
        key="roma",
        name="Roma Capitale (Roma si trasforma)",
        description="Rome's civic-interventions tracker, filtered to street/infrastructure works.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Italy"}),
        administrative_area="Roma Capitale",
        scope_note=(
            "Confirmed live (2026-08-09, 1215 real records) - "
            "credential-free, never a Credentials-wanted scaffold. This "
            "SDK's second Italy provider (after cciss, national) and "
            "first Rome-municipal source. The most obvious candidate "
            "source (RSM's ArcGIS Hub) doesn't hold: checked "
            "live, its real 81-dataset DCAT feed has zero cantieri/"
            "roadworks datasets. Roma Capitale's own CKAN portal was "
            "checked next as a fallback - zero real "
            "results for 'cantieri'/'lavori'/'viabilità'/'opere' via its "
            "real search API. The real source is a third site neither "
            "candidate named - romasitrasforma.it ('Roma si trasforma') - "
            "found by reading its own Drupal module's bundled JS, the "
            "same technique that found Road Report NT's and Lisboa's "
            "real backends. network_scope=unknown, deliberately, not "
            "comprehensive/strategic/regional: this is a general "
            "capital-projects tracker (schools, libraries, parks, "
            "digital infrastructure - 4 macro-themes), not a roadworks "
            "register - real, currently in-progress street/"
            "infrastructure work is 69/1215 (5.7%) of the feed, the "
            "thinnest roadworks signal of any municipal provider in "
            "this SDK, and real geographic reach across Rome's own "
            "network was never audited (only ~half of even that thin "
            "subset carries a coordinate). A real bug found and "
            "corrected, not reproduced: the source's own field_posizione "
            "'lon'/'lat' keys are swapped relative to true geography, "
            "confirmed against every real coordinate in this pull. No "
            "date field exists anywhere in the schema - date_confidence "
            "is always unknown. See module docstring."
        ),
        credentials=None,
        licence=(
            "Unconfirmed - checked the live site's page text, footer, "
            "and common Italian open-data terms (licenza, IODL, "
            "riutilizzo, copyright, note legali); none found stated "
            "anywhere"
        ),
        source_grade="operator",
        _module="streetworks.roma",
        _client_name="RomaClient",
        import_line="from streetworks.roma import RomaClient",
    ),
    ProviderEntry(
        key="copenhagen",
        name="Copenhagen (Gravetilladelser)",
        description=(
            "Københavns Kommune's excavation-permit register, this SDK's first Nordic coverage."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Denmark", "Copenhagen"}),
        administrative_area="Københavns Kommune",
        scope_note=(
            "Confirmed live (2026-08-10, 2240 real feature rows) - "
            "credential-free. This SDK's first Nordic roadworks coverage, "
            "alongside the separate, already credential-scaffolded "
            "national Vejdirektoratet feed (do-not-dedupe, same as NYC "
            "vs WZDx). Neither an initially assumed dataset name nor "
            "backend hold up: 'vejarbejde' over an assumed ArcGIS/OGC "
            "Features service was the first guess; "
            "the real, live dataset is 'Gravetilladelser' (excavation "
            "permits) on opendata.dk, served from a classic WFS 1.0.0 "
            "GetFeature endpoint. A real, load-bearing geometry finding "
            "not anticipated going in: the layer mixes Point/"
            "LineString/Polygon rows, and a repeated case number "
            "(sagsnr) means the same real permit recorded once per "
            "geometry shape (confirmed: all 832 real multi-row permits "
            "have identical non-geometry properties across their rows), "
            "not several distinct worksites - so the converter dedupes "
            "by sagsnr and prefers LineString over Point; zero of the "
            "1241 real permits are Polygon-only, so no polygon-ring "
            "handling was needed. See module docstring for the full "
            "investigation, including a secondary pre-converted-to-point "
            "layer checked and rejected (covers only 56% of real cases)."
        ),
        credentials=None,
        licence=(
            "Creative Commons Attribution 4.0 (CC-BY-4.0) - confirmed live via the "
            "dataset's own CKAN metadata"
        ),
        source_grade="register",
        _module="streetworks.copenhagen",
        _client_name="CopenhagenClient",
        import_line="from streetworks.copenhagen import CopenhagenClient",
    ),
    ProviderEntry(
        key="amsterdam",
        name="Amsterdam (WIOR)",
        description=(
            "Gemeente Amsterdam's public-space-works coordination register, this SDK's "
            "first Dutch municipal roadworks coverage."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Netherlands", "Amsterdam"}),
        administrative_area="Gemeente Amsterdam",
        scope_note=(
            "Confirmed live (2026-08-18) - credential-free, this SDK's "
            "first Dutch municipal roadworks provider, a sibling to the "
            "existing national coverage (NDW/streetworks.datex2, "
            "NWB/streets, BAG/addresses) at city scale, the same "
            "national-plus-one-city shape Denmark (Vejdirektoratet + "
            "Copenhagen), Norway (Vegvesen + Oslo) and Switzerland "
            "(Kanton Zurich + Stadt Zurich) already have. WIOR (Werken "
            "in de Openbare Ruimte) is Gemeente Amsterdam's own "
            "coordination register for public-space works - 10,063 real "
            "records confirmed live, 100% carrying real start/end dates "
            "and a real project name. Served over api.data.amsterdam.nl "
            "(Amsterdam's own DSO-API platform) - a real path quirk was "
            "found and worked around: the dataset's own published path "
            "is relative to its sub-router, so the real live endpoint is "
            "the doubled /v1/wior/wior/. Geometry is real "
            "Polygon/MultiPolygon only (no Point/LineString rows found "
            "live) - the first ring's first vertex is used as a "
            "representative point, the same discipline from_oslo/"
            "from_canton_zurich already apply; unlike Denmark's DAR, "
            "this endpoint genuinely honours server-side reprojection "
            "to WGS84 via a real Accept-Crs header, confirmed live. A "
            "real data-quality quirk kept rather than normalised away: "
            "one live record carries hoofdstatus='Yes' instead of a "
            "genuine Dutch status value - the status field is never "
            "validated against a closed enum. Licence: Gemeente "
            "Amsterdam's own general open-data terms (free reuse, "
            "commercial and non-commercial, attribution not required) - "
            "functionally CC0-equivalent but not asserted under that "
            "specific label, since it wasn't stated under it anywhere "
            "checked. See module docstring."
        ),
        credentials=None,
        licence=(
            "Gemeente Amsterdam's own open-data terms - free reuse, commercial and "
            "non-commercial, attribution not required (not asserted as CC0, since that "
            "specific label wasn't found stated)"
        ),
        source_grade="register",
        _module="streetworks.amsterdam",
        _client_name="AmsterdamClient",
        import_line="from streetworks.amsterdam import AmsterdamClient",
    ),
    ProviderEntry(
        key="oslo",
        name="Oslo (SøkSys)",
        description=(
            "Oslo kommune's real digging/work-permit case system, "
            "this SDK's second Nordic coverage."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Norway", "Oslo"}),
        administrative_area="Oslo kommune",
        scope_note=(
            "Confirmed live (2026-08-10, 1354 real feature rows) - "
            "credential-free. This SDK's second Nordic roadworks "
            "coverage, alongside the separate, already-verified national "
            "Statens vegvesen DATEX II feed (do-not-dedupe, same as NYC "
            "vs WZDx). Neither of two plausible candidate backends "
            "(an Origo/Bymiljøetaten GeoServer layer, or the national "
            "NVDB) holds up: the real source is 'SøkSys', a 2024 permit/"
            "case system run on Oslo's behalf by Geomatikk, found via "
            "pub.soksys.no's own map.js bundle. Real geometry mixes "
            "Point/LineString/Polygon; a repeated case id here is a "
            "genuinely different shape from Copenhagen's - 256 of 261 "
            "real multi-row permits are pure tiling-query duplicate "
            "artifacts (identical id, identical geometry), but a real "
            "handful genuinely span several distinct real sub-areas "
            "under one activity_id, a Jersey/NYC-DOT-style multi-site "
            "grouping, not Copenhagen's single-geometry-pick pattern. "
            "CRS is EPSG:25832 (projected UTM32N, not WGS84) - "
            "Coordinate.value stays unswapped (easting, northing). "
            "Licence genuinely unconfirmed - checked both the public map "
            "page and Oslo kommune's own SøkSys explainer page, nothing "
            "stated on either. See module docstring for the full "
            "investigation, including a separate pre-permit /plans "
            "endpoint checked and left for a future pass."
        ),
        credentials=None,
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.oslo",
        _client_name="OsloClient",
        import_line="from streetworks.oslo import OsloClient",
    ),
    ProviderEntry(
        key="helsinki",
        name="Helsinki (Kaivuilmoitus)",
        description=(
            "City of Helsinki's excavation-notification register, "
            "this SDK's third Nordic coverage."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Finland", "Helsinki"}),
        administrative_area="Helsingin kaupunki",
        scope_note=(
            "Confirmed live (2026-08-13, 3431 real feature rows) - "
            "credential-free. This SDK's third Nordic roadworks coverage, "
            "alongside the separate, already keyless-built national "
            "Digitraffic DATEX II feed (do-not-dedupe, same as NYC vs "
            "WZDx). Resolves an earlier open question over whether a "
            "Helsinki roadworks dataset even exists: HRI's (Helsinki "
            "Region Infoshare) CKAN catalogue "
            "surfaces 'Land usage permission system for public areas in "
            "the City of Helsinki', backed by a live GeoServer WFS layer "
            "literally named Kaivuilmoitus_alue ('excavation notification, "
            "area'). Real geometry is MultiPolygon throughout; a repeated "
            "hakemustunnus (application reference) means one excavation "
            "notification genuinely spans several distinct real "
            "sub-areas - an Oslo-shaped grouping (up to 164 real rows "
            "under one reference), not Copenhagen's single-geometry-pick "
            "pattern. CRS is EPSG:3879 (projected ETRS-GK25FIN, not "
            "WGS84) - Coordinate.value stays unswapped (easting, "
            "northing), even though the WFS can reproject to WGS84 on "
            "request (confirmed live, not used, per this SDK's standing "
            "CRS policy). status is a genuinely informative two-value "
            "field (Käynnissä=active now, Tuleva=upcoming, cross-checked "
            "against real dates) - unlike Oslo's always-'granted' status, "
            "this drives real VERIFIED/ESTIMATED date-confidence grading. "
            "Two related layers checked live and deliberately not used: "
            "a point-geometry layer confirmed to be a redundant subset "
            "(not disjoint data), and a structurally distinct temporary-"
            "traffic-arrangement layer left for a future pass, the same "
            "'found, not built' treatment Oslo gave its own /plans "
            "endpoint. See module docstring for the full investigation."
        ),
        credentials=None,
        licence=(
            "Creative Commons Attribution 4.0 (CC-BY-4.0) - confirmed live via the "
            "dataset's own CKAN metadata"
        ),
        source_grade="register",
        _module="streetworks.helsinki",
        _client_name="HelsinkiClient",
        import_line="from streetworks.helsinki import HelsinkiClient",
    ),
    ProviderEntry(
        key="milano",
        name="Milano (Avvisi di manomissione)",
        description=(
            "Comune di Milano's excavation-notice register, this SDK's "
            "second Italy municipal coverage after Roma."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Italy", "Milan"}),
        administrative_area="Comune di Milano",
        scope_note=(
            "Confirmed live (2026-08-14, 139 real feature rows) - "
            "credential-free. Resolves an open question left after Rome "
            "fell off-board as capital-projects-only, given Italy's "
            "roadworks coverage was known to run through populous cities "
            "rather than the capital: the Lombardy Socrata ecosystem was "
            "already known to carry real 'Cantieri stradali' "
            "for Cremona/Pavia/Rho, but not a Milan-specific dataset - "
            "checked live, none exists there. Milan's own CKAN portal "
            "has none named 'cantieri' either, but 'scavo' (excavation) "
            "surfaces 'Avvisi di manomissione' - the real Italian legal "
            "term, not the more literal term first assumed - maintained by the "
            "city's own Direzione Mobilità e Trasporti, updated daily, "
            "with a direct GeoJSON download (no API/WFS/key needed). A "
            "real, confirmed quirk: the download URL embeds a daily "
            "generation timestamp in its filename, but CKAN resolves "
            "purely by resource UUID - a substituted filename returned "
            "identical live content, so a stable, non-timestamped URL "
            "can be hardcoded safely. Real geometry is Point, genuine "
            "native WGS84 (not the projected Monte Mario/ETRF2000 CRS "
            "Italian sources often use) - flipped to (lat, lon) like Lisboa/Paris, "
            "unlike Oslo/Helsinki's unswapped projected sources. Every "
            "protocol number is unique - one Works per feature, no "
            "grouping. This is a utility-operator excavation register "
            "(water/electricity/gas/sewage/district-heating companies), "
            "the Milan equivalent of Paris's 'Opérateurs de réseau' "
            "category - not the city's own separate road-maintenance "
            "programme, stated honestly rather than implied broader."
        ),
        credentials=None,
        licence=(
            "Creative Commons Attribution (CC-BY) - confirmed live via the "
            "dataset's own CKAN metadata"
        ),
        source_grade="register",
        _module="streetworks.milano",
        _client_name="MilanoClient",
        import_line="from streetworks.milano import MilanoClient",
    ),
    ProviderEntry(
        key="canton_zurich",
        name="Kanton Zürich (Baustellen Kantonsstrassen)",
        description=(
            "Kanton Zürich's own cantonal-road works register, this SDK's "
            "first Swiss coverage."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Switzerland", "Zürich"}),
        administrative_area="Kanton Zürich",
        scope_note=(
            "Confirmed live (2026-08-14, 66 real feature rows) - "
            "credential-free. Found via opendata.swiss's own CKAN "
            "catalogue (wfs-baustellen-kantonsstrassen), a real GeoServer "
            "WFS run by the canton's own Tiefbauamt. Two real layers "
            "carry the same 66 closures, not disjoint data (confirmed by "
            "matching properties 1:1) - the detail layer's real Polygon "
            "footprints are used, the overview layer's Point geometry is "
            "not. CRS is EPSG:2056 (Swiss LV95, confirmed live), stored "
            "unswapped. No unique identifier field exists anywhere in "
            "the schema - a composite key is 65/66 unique, but the one "
            "collision is two genuinely distinct real closures (opposite "
            "directions of the same road) sharing every composite field, "
            "proving a fabricated key would misrepresent them - reference "
            "stays None, a documented gap not a guess. status_baustelle "
            "is a real, informative two-value field (aktiv/zukünftig) "
            "driving real VERIFIED/ESTIMATED date-confidence grading, the "
            "same shape as Helsinki's Käynnissä/Tuleva. Deliberately not "
            "deduped against the separate, non-overlapping Stadt Zürich "
            "city-streets coverage. Licence: opendata.swiss 'Open use' "
            "tier, confirmed live via the resource's own rights field "
            "(not its empty CKAN license_id) - no attribution required."
        ),
        credentials=None,
        licence=(
            "opendata.swiss 'Open use' - usable commercially and "
            "non-commercially, no attribution required, confirmed live"
        ),
        source_grade="operator",
        _module="streetworks.canton_zurich",
        _client_name="CantonZurichClient",
        import_line="from streetworks.canton_zurich import CantonZurichClient",
    ),
    ProviderEntry(
        key="zurich",
        name="Stadt Zürich (Aktuelle Tiefbauprojekte)",
        description=(
            "City of Zürich's own current civil-engineering-projects "
            "register, this SDK's second Swiss coverage."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Switzerland", "Zürich"}),
        administrative_area="Stadt Zürich",
        scope_note=(
            "Confirmed live (2026-08-14, 140 real feature rows) - "
            "credential-free. Found via the same opendata.swiss CKAN "
            "catalogue entry as Kanton Zürich (aktuelle-tiefbauprojekte-"
            "im-offentlichen-grund), the city's own GeoServer WFS. Two "
            "real quirks confirmed live: this server's only working JSON "
            "format is application/vnd.geo+json, not the shared client's "
            "own default; and it 500s on WFS 2.0.0's plural TYPENAMES "
            "alone, needing the real working 1.1.0 singular TYPENAME "
            "sent alongside it. CRS is genuinely WGS84, confirmed "
            "empirically (real coordinates match the layer's own stated "
            "WGS84BoundingBox) despite an empty DefaultSRS capabilities "
            "tag - a real metadata gap, not a parsing miss. baunr (project "
            "number) is a real, 100%-unique identifier, unlike the "
            "canton's dataset. kategorie is a constant 'Grössere "
            "Baustelle' - this feed is already curated to significant "
            "projects, stated honestly rather than implied exhaustive. "
            "Deliberately not deduped against the separate, non-"
            "overlapping Kanton Zürich cantonal-road coverage. Licence: "
            "the same opendata.swiss 'Open use' tier, confirmed live."
        ),
        credentials=None,
        licence=(
            "opendata.swiss 'Open use' - usable commercially and "
            "non-commercially, no attribution required, confirmed live"
        ),
        source_grade="operator",
        _module="streetworks.zurich",
        _client_name="ZurichClient",
        import_line="from streetworks.zurich import ZurichClient",
    ),
    ProviderEntry(
        key="vienna",
        name="Vienna (verkehrswirksame Baustellen)",
        description=(
            "Stadt Wien's traffic-relevant roadworks/closures register, "
            "this SDK's second Austria coverage."
        ),
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.COMPREHENSIVE,
        territories=frozenset({"Austria", "Vienna"}),
        administrative_area="Stadt Wien",
        scope_note=(
            "Confirmed live (2026-08-14, 111 real feature rows) - "
            "credential-free. The most obvious candidate URL (data.gv.at) "
            "is a JS-rendered SPA with no real content reachable from a "
            "plain fetch; the real data lives directly on Vienna's own "
            "GeoServer WFS, found via web search. Two real layers "
            "(BAUSTELLENPKTOGD/Point, 39 rows; BAUSTELLENLINOGD/"
            "LineString, 72 rows) are genuinely disjoint, not the same "
            "data twice - zero real ID or location-name overlap - both "
            "are fetched and combined. Two real server quirks, both "
            "masked-failure risks confirmed by reading response bodies "
            "not just status codes: application/geo+json returns a real "
            "HTTP 200 wrapping an XML error, and the server needs WFS "
            "1.1.0's singular TYPENAME alongside the shared client's own "
            "plural TYPENAMES. CRS is EPSG:31256 (MGI/Austria GK East), "
            "cross-verified via a same-feature WGS84 reprojection landing "
            "on real Vienna coordinates. A real correction to the "
            "obvious initial assumption: ANTRAGSTELLER (applicant) shows "
            "genuine third-party applicants (utility companies, the transit "
            "operator, even a private developer), confirming this is a "
            "permit register, not an authority publishing only its own "
            "works - source_grade is REGISTER, not the OPERATOR grade "
            "an authority-published dataset might suggest. A real false "
            "lead (Bausperre §8 zoning-freeze "
            "layers) was checked and correctly excluded. Licence: Stadt "
            "Wien's stated general CC BY 4.0 open-data policy, not this "
            "specific dataset's own confirmed per-record licence field "
            "(unreachable behind the same JS-rendered catalogue)."
        ),
        credentials=None,
        licence=(
            "CC BY 4.0 - Stadt Wien's stated general open-data policy, "
            "not per-dataset-confirmed (see scope_note)"
        ),
        licence_confirmed=False,
        source_grade="register",
        _module="streetworks.vienna",
        _client_name="ViennaClient",
        import_line="from streetworks.vienna import ViennaClient",
    ),
    ProviderEntry(
        key="stockholm",
        name="Stockholm (Trafikkontoret)",
        description="Stockholm city geodata WFS - blocked before any schema was ever seen.",
        kind=Kind.ROADWORKS,
        network_scope=NetworkScope.UNKNOWN,
        territories=frozenset({"Sweden", "Stockholm"}),
        scope_note=(
            "Phase 0 scaffold - one phase earlier than "
            "streetworks.datex2.trafikverket. Confirms a real risk "
            "flagged early on - that Stockholm's city portal might "
            "publish only road-network/rules data rather than actual "
            "roadworks, the same pattern already seen elsewhere (a city "
            "portal that looks roadworks-shaped but only carries network "
            "geometry) - rather than disproving it: every real surface tested "
            "(WFS/WMS GetCapabilities) returns a genuine HTTP 401 before "
            "any dataset name, layer, or field is ever revealed - no "
            "schema of any kind has been seen, unlike Trafikverket (whose "
            "object type/fields are confirmed via public docs) or South "
            "Australia (whose layer definition is public). A promising "
            "'regional roadworks coordination map' lead traces back to "
            "the already credential-parked national Trafikverket system, "
            "not a separate Stockholm dataset. Whether a real roadworks "
            "layer exists on this platform at all is genuinely "
            "unresolved - see module docstring."
        ),
        credentials="Trafikkontoret API key (registration path unconfirmed)",
        licence=None,
        licence_confirmed=False,
        source_grade="register",
        verified=False,
        _module="streetworks.stockholm",
        _client_name="StockholmClient",
        import_line="from streetworks.stockholm import StockholmClient",
    ),
]
