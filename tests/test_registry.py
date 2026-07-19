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
from streetworks.registry import _REGISTRY, Kind, get_provider, providers

PACKAGE_ROOT = Path(inspect.getfile(inspect.getmodule(providers))).parent

# Top-level packages/modules that are infrastructure, not providers, and are
# deliberately not in the registry.
_NON_PROVIDER_MODULES = {"common", "registry", "exceptions", "ogc"}


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
    assert {e.key for e in result} >= {"streetmanager", "datavia", "openusrn", "trafficwales"}


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


def test_providers_kind_filter():
    gazetteers = providers(kind="gazetteer")
    assert {e.key for e in gazetteers} == {"datavia", "openusrn"}
    assert all(e.kind is Kind.GAZETTEER for e in gazetteers)
    # Enum and string both accepted.
    assert providers(kind=Kind.GAZETTEER) == gazetteers


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
    cls = get_provider("spain")
    assert isinstance(cls, type)
    from streetworks.datex2.dgt import DGTClient

    assert cls is DGTClient


@pytest.mark.parametrize(
    "alias,expected_key",
    [
        ("spain", "dgt"),
        ("finland", "digitraffic"),
        ("iceland", "irca"),
        ("netherlands", "ndw"),
        ("scotland", "srwr"),
        ("france", "bisonfute"),
        ("norway", "vegvesen"),
    ],
)
def test_single_provider_place_names_are_aliased(alias, expected_key):
    entry = next(e for e in _REGISTRY if e.key == expected_key)
    assert get_provider(alias) is entry.client


def test_get_provider_case_insensitive():
    assert get_provider("SPAIN") is get_provider("spain")


@pytest.mark.parametrize("key", ["germany", "england", "wales"])
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


def test_registry_top_level_modules_match_readme_provider_table():
    """Registry vs. README duplication is *accepted* (see registry.py's
    module docstring for why), not eliminated - so drift is caught here
    instead: every top-level module the registry references must appear as
    its own row in the README's provider table, and vice versa (except
    `streetworks.common`, which is infrastructure, not a provider)."""
    readme = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")
    table_start = readme.index("| Module | Service | Direction |")
    table_end = readme.index("\n\n", table_start)
    table = readme[table_start:table_end]
    readme_modules = set(re.findall(r"\| `streetworks\.(\w+)`", table))

    registry_modules = {entry._module.split(".")[1] for entry in _REGISTRY}

    assert registry_modules <= readme_modules, (
        f"registered but missing from the README table: {registry_modules - readme_modules}"
    )
    assert readme_modules - {"common"} <= registry_modules, (
        f"in the README table but not registered: "
        f"{readme_modules - {'common'} - registry_modules}"
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
    for key in ("dgt", "srwr", "openusrn", "police", "ndw"):
        entry = next(e for e in _REGISTRY if e.key == key)
        assert "write/publish" not in entry.capabilities()


def test_capabilities_reflect_kind():
    assert "gazetteer/street lookup" in get_entry("openusrn").capabilities()
    assert "safety context" in get_entry("police").capabilities()
    assert "roadworks retrieval" in get_entry("dgt").capabilities()


def get_entry(key: str):
    return next(e for e in _REGISTRY if e.key == key)


# --------------------------------------------------------------------------- #
# Norway (Vegvesen) - the one verified=False provider
# --------------------------------------------------------------------------- #


def test_norway_is_the_one_unverified_provider():
    unverified = [e for e in _REGISTRY if not e.verified]
    assert [e.key for e in unverified] == ["vegvesen"]


def test_unverified_provider_flagged_in_rendered_output():
    rendered = str(get_entry("vegvesen"))
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
