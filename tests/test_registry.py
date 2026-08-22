"""Tests for streetworks.registry - the provider discovery layer.

The most important test here isn't a behaviour test at all: it's the one
that actually imports every registered ``import_line`` and resolves every
registry ``client`` reference. A registry that describes an import path
that doesn't work, or a class that no longer exists, is worse than no
registry - this is what stops it lying.
"""

import inspect
import re
from pathlib import Path

import pytest

from streetworks.exceptions import AmbiguousProviderError, ProviderNotFoundError
from streetworks.registry import _REGISTRY, Kind, NetworkScope, get_provider, providers

PACKAGE_ROOT = Path(inspect.getfile(inspect.getmodule(providers))).parent

# Top-level packages/modules that are infrastructure, not providers, and are
# deliberately not in the registry. "nuar" is a different case within this
# set - not infrastructure, but a testing-only reference model with no live
# connector yet (see streetworks.nuar's own module docstring) - registering
# it would misrepresent it as a queryable provider before one exists.
_NON_PROVIDER_MODULES = {"common", "registry", "exceptions", "ogc", "socrata", "nuar"}


def test_every_import_line_actually_works():
    for entry in _REGISTRY:
        line = entry.import_line.split("#", 1)[0].strip()
        namespace: dict = {}
        exec(line, namespace)  # noqa: S102 - the exact point of this test
        assert entry._client_name in namespace, (
            f"{entry.key}: import_line {entry.import_line!r} doesn't bind "
            f"{entry._client_name!r}"
        )
        assert namespace[entry._client_name] is entry.client


def test_every_client_reference_resolves():
    for entry in _REGISTRY:
        assert entry.client is not None, f"{entry.key}: client did not resolve"


def test_registry_keys_are_unique_and_lowercase():
    keys = [e.key for e in _REGISTRY]
    assert len(keys) == len(set(keys)), "duplicate registry keys"
    assert all(k == k.lower() for k in keys)


def test_aliases_do_not_collide_with_keys_or_each_other():
    keys = {e.key for e in _REGISTRY}
    seen_aliases: set[str] = set()
    for entry in _REGISTRY:
        for alias in entry.aliases:
            assert alias not in keys, f"alias {alias!r} collides with a real key"
            assert alias not in seen_aliases, f"alias {alias!r} registered twice"
            seen_aliases.add(alias)


# --------------------------------------------------------------------------- #
# providers() filtering
# --------------------------------------------------------------------------- #


def test_providers_no_filter_returns_everything():
    assert len(providers()) == len(_REGISTRY)


def test_providers_territory_filter_case_insensitive():
    assert providers(territory="wales") == providers(territory="Wales")
    result = providers(territory="Wales")
    assert {e.key for e in result} >= {"datavia", "openusrn", "trafficwales"}


def test_providers_territory_uk_expands_to_four_nations():
    uk = {e.key for e in providers(territory="UK")}
    england_only = {e.key for e in providers(territory="England")}
    assert england_only <= uk
    assert "srwr" in uk  # Scotland
    assert "trafficwatchni" in uk  # Northern Ireland
    assert "wzdx" not in uk  # USA, not a UK nation


def test_providers_unknown_territory_warns_and_returns_empty():
    with pytest.warns(UserWarning, match="Unknown territory"):
        result = providers(territory="Narnia")
    assert result == []


def test_providers_kind_filter_streets():
    streets = providers(kind="streets")
    assert {e.key for e in streets} == {
        "datavia", "openusrn", "nwb", "bdtopo", "nvdb", "tigerweb", "linz_roads", "gnaf_roads",
        "idee", "osni", "dfi_roads", "anncsu", "jersey_streets", "guernsey_streets", "nrn",
        "gibraltar", "monaghan", "lmi", "digiroad", "marousi", "dar", "swisstopo", "bev",
        "vlaanderen", "registrucentras", "caclr", "hamburg_streets",
        "brandenburg_streets", "geosn_streets", "lisboa_streets",
    }
    assert all(e.kind is Kind.STREETS for e in streets)
    # Enum and string both accepted.
    assert providers(kind=Kind.STREETS) == streets


def test_providers_kind_filter_addresses():
    addresses = providers(kind="addresses")
    assert {e.key for e in addresses} == {"ban", "bag", "kartverket", "linz", "gnaf"}
    assert all(e.kind is Kind.ADDRESSES for e in addresses)
    assert providers(kind=Kind.ADDRESSES) == addresses


def test_providers_credentials_filter():
    free = providers(credentials=False)
    assert all(e.credentials is None for e in free)
    needs_creds = providers(credentials=True)
    assert all(e.credentials is not None for e in needs_creds)
    assert len(free) + len(needs_creds) == len(_REGISTRY)


def test_providers_combined_filters():
    result = providers(territory="England", kind="roadworks")
    assert all(e.kind is Kind.ROADWORKS for e in result)
    assert all("England" in e.territories for e in result)


def test_providers_repr_includes_import_line():
    result = providers(territory="Spain")
    rendered = repr(result)
    assert "from streetworks.datex2.dgt import DGTClient" in rendered


# --------------------------------------------------------------------------- #
# get_provider()
# --------------------------------------------------------------------------- #


def test_get_provider_returns_class_not_instance():
    cls = get_provider("dgt")
    assert isinstance(cls, type)
    from streetworks.datex2.dgt import DGTClient

    assert cls is DGTClient


@pytest.mark.parametrize(
    "alias,expected_key",
    [
        ("finland", "digitraffic"),
        ("iceland", "irca"),
        ("scotland", "srwr"),
    ],
)
def test_single_provider_place_names_are_aliased(alias, expected_key):
    entry = next(e for e in _REGISTRY if e.key == expected_key)
    assert get_provider(alias) is entry.client


def test_get_provider_case_insensitive():
    assert get_provider("MALLORCA") is get_provider("mallorca")


@pytest.mark.parametrize(
    "key", ["germany", "england", "wales", "france", "netherlands", "norway", "spain"]
)
def test_get_provider_ambiguous_key_raises_naming_candidates(key):
    with pytest.raises(AmbiguousProviderError) as exc_info:
        get_provider(key)
    message = str(exc_info.value)
    # every real candidate for that territory must be named
    candidates = {e.key for e in providers(territory=key)}
    for candidate in candidates:
        assert candidate in message


def test_get_provider_unknown_key_raises_with_near_match():
    with pytest.raises(ProviderNotFoundError, match="streetmanager"):
        get_provider("strret_manager")


def test_get_provider_unknown_key_no_near_match_lists_known_keys():
    with pytest.raises(ProviderNotFoundError, match="dgt"):
        get_provider("completely-unrelated-nonsense-key")


# --------------------------------------------------------------------------- #
# Coverage: every provider module in the package appears in the registry
# --------------------------------------------------------------------------- #


def test_every_provider_package_is_registered():
    registered_top_level = {entry._module.split(".")[1] for entry in _REGISTRY}
    real_packages = {
        p.name
        for p in PACKAGE_ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(("_", "__"))
    }
    missing = real_packages - _NON_PROVIDER_MODULES - registered_top_level
    assert not missing, f"provider package(s) with no registry entry: {missing}"


def test_every_roadworks_provider_has_a_network_scope():
    """Every roadworks entry must set network_scope explicitly - to a real
    audited value, or NetworkScope.UNKNOWN if genuinely unaudited (never
    the bare None default, which means "this concept doesn't apply" -
    reserved for non-roadworks kinds). Mirrors
    test_every_provider_package_is_registered's discipline: a new
    roadworks provider can't silently ship without a scope any more than
    it can ship without a registry entry at all."""
    missing = [e.key for e in _REGISTRY if e.kind is Kind.ROADWORKS and e.network_scope is None]
    assert not missing, f"roadworks provider(s) with no network_scope set: {missing}"


def test_non_roadworks_providers_have_no_network_scope():
    """The inverse check - network_scope is roadworks-only, so a
    gazetteer/address/street/context entry should never have one set
    (that would imply the concept applies where it doesn't)."""
    wrongly_set = [
        e.key for e in _REGISTRY if e.kind is not Kind.ROADWORKS and e.network_scope is not None
    ]
    assert not wrongly_set, f"non-roadworks provider(s) with a network_scope set: {wrongly_set}"


def test_network_scope_values_are_real_enum_members():
    for entry in _REGISTRY:
        if entry.network_scope is not None:
            assert isinstance(entry.network_scope, NetworkScope)


def test_registry_top_level_modules_match_docs_provider_table():
    """Registry vs. docs duplication is *accepted* (see registry.py's
    module docstring for why), not eliminated - so drift is caught here
    instead: every top-level module the registry references must appear as
    its own row in docs/providers/index.md's module table, and vice versa
    (except `streetworks.common`, which is infrastructure, not a provider).

    This table used to live in README.md; the phase-two docs migration
    moved it verbatim to docs/providers/index.md and slimmed the README to
    a front door with a link instead - see docs/phase-two-removal-map.md."""
    docs_page = (
        Path(__file__).parent.parent / "docs" / "providers" / "index.md"
    ).read_text(encoding="utf-8")
    table_start = docs_page.index("| Module | Service | Direction |")
    table_end = docs_page.index("\n\n", table_start)
    table = docs_page[table_start:table_end]
    docs_modules = set(re.findall(r"\| `streetworks\.(\w+)`", table))

    registry_modules = {entry._module.split(".")[1] for entry in _REGISTRY}

    assert registry_modules <= docs_modules, (
        f"registered but missing from the docs table: {registry_modules - docs_modules}"
    )
    assert docs_modules - {"common"} <= registry_modules, (
        f"in the docs table but not registered: "
        f"{docs_modules - {'common'} - registry_modules}"
    )


def test_registry_only_references_real_top_level_packages():
    real_packages = {
        p.name
        for p in PACKAGE_ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(("_", "__"))
    }
    for entry in _REGISTRY:
        top_level = entry._module.split(".")[1]
        assert top_level in real_packages, f"{entry.key}: {entry._module} doesn't exist"


# --------------------------------------------------------------------------- #
# Capabilities - derived, checked against real, known method shapes
# --------------------------------------------------------------------------- #


def test_capabilities_detect_write_publish_including_nested_sub_apis():
    sm = next(e for e in _REGISTRY if e.key == "streetmanager")
    assert "write/publish" in sm.capabilities()
    assert "planning artifacts" in sm.capabilities()  # forward_plans, on a nested sub-API

    dtro = next(e for e in _REGISTRY if e.key == "dtro")
    assert "write/publish" in dtro.capabilities()


def test_capabilities_do_not_false_positive_on_read_only_clients():
    for key in (
        "dgt", "srwr", "openusrn", "police", "ndw", "ban", "bag", "kartverket", "nwb", "bdtopo",
        "nvdb",
    ):
        entry = next(e for e in _REGISTRY if e.key == key)
        assert "write/publish" not in entry.capabilities()


def test_capabilities_reflect_kind():
    assert "street lookup" in get_entry("openusrn").capabilities()
    assert "address lookup" in get_entry("ban").capabilities()
    assert "safety context" in get_entry("police").capabilities()
    assert "roadworks retrieval" in get_entry("dgt").capabilities()


def get_entry(key: str):
    return next(e for e in _REGISTRY if e.key == key)


# --------------------------------------------------------------------------- #
# Norway (Vegvesen) - the one verified=False provider
# --------------------------------------------------------------------------- #


def test_credentials_wanted_is_the_only_unverified_tier():
    """Sweden, Denmark, and South Australia are the "Credentials wanted"
    tier - built to a confirmed API/schema shape but never run against
    real authenticated data. Norway/NSW/Victoria graduated out on
    2026-07-30 after a real credentialed pull confirmed each (see their
    own module docstrings - Norway's real geometry is mixed-CRS and still
    has an open caveat, but the connectivity/schema itself is confirmed).
    South Australia (`sa`) is the worst-off of the three - blocked on both
    a token-gated query endpoint and a geo-restricted host, so unlike
    Trafikverket/Vejdirektoratet, even the endpoint/auth shape has never
    been exercised against a real response, only the layer *metadata* -
    see streetworks.au.sa's own module docstring.

    The Northern Territory (`nt`) graduated out on 2026-08-19 after a
    real, credential-free pull of GET /api/Obstruction/GetAll confirmed
    a public JSON envelope (140 CURRENT records, 26 official Roadworks).
    See streetworks.au.nt's own module docstring.

    LINZ Roads/Road Sections (`linz_roads`) is back in Trafikverket's own
    tier: schema and a real attribute sample confirmed live from LINZ's
    own public Koordinates metadata API, but never queried through the
    real WFS - blocked on a genuine LINZ Data Service (LDS) API key this
    build doesn't have. Its sibling `linz` (NZ Addresses) is verified -
    same LinzClient, genuinely different verification tier per capability,
    see streetworks.linz.client's own module docstring.

    MapRoad (`maproad`, Ireland) is a documented-unavailable scaffold,
    not Trafikverket's credentials-wanted tier -
    it has a real, government-catalogued API, but the catalogue's own
    metadata (API Available: Yes, Open Data: No, Data Sharing: Yes,
    Personal Data: Yes) describes a formal, GDPR-gated data-sharing
    arrangement, not a self-service key, and no technical shape for a
    read path is published anywhere - see streetworks.maproad.client's
    own module docstring and streetworks.exceptions.ProviderUnavailableError.

    Greece (`greece`) is squarely MapRoad's own tier - not a real interface
    blocked, but investigated and found to have no roadworks source at
    all: its real NAP (nap.gov.gr) carries only POI/sensor data, and the
    portal itself is currently unreachable besides (a real live 502) -
    see streetworks.greece.client's own module docstring.

    Stockholm (`stockholm`) is worse-off than every other Credentials
    wanted provider, not on the same footing as Trafikverket/SA: every
    real surface tested (WFS/WMS GetCapabilities) 401s before any
    dataset name, layer, or field is ever revealed - no schema of any
    kind has been confirmed, unlike Trafikverket (object type/fields
    confirmed via public docs) or SA (public layer metadata) - see
    streetworks.stockholm.client's own module docstring.

    Austria (`austria`) is genuine DATEX II, so it's better-schema-
    confirmed than Trafikverket's bespoke envelope, but worse-access-
    confirmed than Vejdirektoratet at the same stage: Vejdirektoratet's
    protocol spec states its auth scheme (HTTP Basic) verbatim; no
    equivalent statement exists anywhere public for ASFINAG - checked
    the dataset page, its licence page, and the registration portal's
    own JS bundle. The auth mechanism itself, not just the credential
    value, is unknown - see streetworks.datex2.austria's own module
    docstring.

    Saskatchewan Highway Hotline (`sk511`), New Brunswick 511 (`nb511`),
    Newfoundland and Labrador 511 (`nl511`), Nova Scotia 511 (`ns511`),
    511 Yukon (`yt511`), Nevada 511 (`nv511`) and Georgia 511 (`ga511`)
    are all better-off than every other entry in this tier: each needs a
    real developer key this build doesn't have, but the field schema
    itself isn't a guess or documentation-only claim - it's drawn from a
    real, live, unauthenticated pull against the identical commercial
    platform (Ontario 511, `on511`, verified) plus Alberta's own
    published docs matching field-for-field, and every one of them
    answers the identical structured "Invalid Key" rejection live. What's
    unconfirmed is narrower than any other entry here: only whether each
    jurisdiction's own authenticated response round-trips through this
    exact parsing unchanged - see streetworks.na511.client's own module
    docstring. 511 Alberta (`ab511`) was in this same tier until a real
    developer key confirmed exactly that live (2026-08-22, 302 real
    events, no code changes needed) - it's verified now, the first
    key-gated jurisdiction on this platform to graduate out of this tier.

    Every other provider is verified against real data."""
    unverified = [e for e in _REGISTRY if not e.verified]
    assert {e.key for e in unverified} == {
        "trafikverket",
        "vejdirektoratet",
        "sa",
        "linz_roads",
        "maproad",
        "greece",
        "stockholm",
        "austria",
        "sk511",
        "nb511",
        "nl511",
        "ns511",
        "yt511",
        "nv511",
        "ga511",
    }


def test_unverified_provider_flagged_in_rendered_output():
    rendered = str(get_entry("trafikverket"))
    assert "Not yet verified" in rendered


# --------------------------------------------------------------------------- #
# Performance: importing the registry must not import heavy provider modules
# --------------------------------------------------------------------------- #


def test_importing_registry_does_not_import_httpx():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c", "import sys; import streetworks.registry; "
         "print('httpx' in sys.modules)"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "False"
