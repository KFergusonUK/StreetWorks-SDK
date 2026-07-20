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

__all__ = ["Kind", "ProviderEntry", "providers", "get_provider"]


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
    """

    ROADWORKS = "roadworks"
    ADDRESSES = "addresses"
    STREETS = "streets"
    CONTEXT = "context"


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
        territories=frozenset({"Spain"}),
        scope_note=(
            "National except Catalonia and the Basque Country, which run their "
            "own regional traffic authorities and publish separately."
        ),
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="operator",
        aliases=frozenset({"spain"}),
        _module="streetworks.datex2",
        _client_name="DGTClient",
        import_line="from streetworks.datex2.dgt import DGTClient",
    ),
    ProviderEntry(
        key="vegvesen",
        name="Statens vegvesen",
        description="Norway's national roadworks feed.",
        kind=Kind.ROADWORKS,
        territories=frozenset({"Norway"}),
        scope_note="Phase 1 scaffold - never run against real Norwegian data, see below.",
        credentials="Statens vegvesen API credentials (Basic or Bearer) + IP allow-listing",
        licence=None,
        licence_confirmed=False,  # blocked on credentials for Phase 2, see module docstring
        source_grade="operator",
        verified=False,
        # No "norway" alias: Norway now has three providers (this one,
        # kartverket, and nvdb) - get_provider("norway") resolves through
        # the territory-ambiguity path instead, same as "france".
        _module="streetworks.datex2",
        _client_name="VegvesenClient",
        import_line="from streetworks.datex2 import VegvesenClient",
    ),
    ProviderEntry(
        key="autobahn",
        name="Autobahn GmbH",
        description="Germany's national motorway roadworks feed.",
        kind=Kind.ROADWORKS,
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
        territories=frozenset({"Germany"}),
        administrative_area="Sachsen",
        scope_note="Coordinates are EPSG:25833 (UTM33N), not WGS84 - see the module docstring.",
        credentials=None,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        source_grade="operator",
        aliases=frozenset({"sachsen"}),
        _module="streetworks.ogc.germany",
        _client_name="GermanRoadworksClient",
        import_line='from streetworks.ogc.germany import GermanRoadworksClient # .fetch("Sachsen")',
    ),
    ProviderEntry(
        key="wzdx",
        name="WZDx (Work Zone Data Exchange)",
        description="The US standard for work-zone data, published independently by ~40+ agencies.",
        kind=Kind.ROADWORKS,
        territories=frozenset({"USA"}),
        scope_note=(
            "Not one provider's coverage - a schema ~40+ agencies publish "
            "independently. Use streetworks.wzdx.list_feeds() to find a "
            "specific agency's feed URL."
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
        key="trafficwatchni",
        name="TrafficWatchNI",
        description=(
            "Northern Ireland's roadworks/incidents feed, from DfI's "
            "Traffic Information and Control Centre."
        ),
        kind=Kind.ROADWORKS,
        territories=frozenset({"Northern Ireland"}),
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
]
