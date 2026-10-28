#!/usr/bin/env python3
"""Generate Pydantic v2 models from the Street Manager swagger specs.

The DfT publishes an OpenAPI JSON file for each of the nine Street Manager
APIs (OpenAPI 3 since at least V6.17.25; older releases were Swagger 2.0,
which is still accepted). This script turns them into typed Pydantic models
under ``src/streetworks/streetmanager/models/{version}/``.

Two ways to supply the specs:

1. **From URLs**, using a template with ``{api}`` (and optionally
   ``{version}``) placeholders. Prefer the DfT docs site's per-release specs,
   so the generated header records exactly which release the models match::

       python scripts/generate_models.py --version v6 \\
           --url-template "https://department-for-transport-streetmanager.github.io/street-manager-docs/api-documentation/V6/V6.17.25/json/{api}-swagger.json"

   The live ``https://api.sandbox.manage-roadworks.service.gov.uk/{version}/{api}/swagger.json``
   also works, but floats with whatever release the sandbox is on.

2. **From a directory** of downloaded JSON files, saved as
   ``specs/streetmanager/v6/work.json`` etc.::

       python scripts/generate_models.py --version v6 --from-dir specs/streetmanager/v6

Every object in the DfT specs is declared closed (``additionalProperties:
false``), which datamodel-code-generator turns into ``extra="forbid"``. V6
takes additive changes every fortnight, so a closed *response* model rejects
the next release's new fields (V6.17.24's ``asd_coordinate_geometry`` broke
``WorkResponse`` validation this way). ``open_response_schemas`` therefore
reopens response schemas before generation - a deliberate deviation from the
spec. Request models stay closed so a typo fails before a write.

Requires the ``gen`` extra: ``pip install -e ".[gen]"``.

The generated files are committed to the repository so end users get typed
models from PyPI without needing this script. Regenerate whenever DfT release
notes mention schema changes.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

APIS = [
    "work",
    "reporting",
    "lookup",
    "geojson",
    "party",
    "export",
    "event",
    "sampling",
    "worklist",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_ROOT = Path(
    os.environ.get(
        "STREETWORKS_MODELS_ROOT",
        REPO_ROOT / "src" / "streetworks" / "streetmanager" / "models",
    )
)

HEADER = (
    '"""GENERATED FILE - do not edit by hand.\n\n'
    "Generated from the DfT Street Manager {api} API swagger specification\n"
    "({source}) by scripts/generate_models.py using datamodel-code-generator.\n\n"
    'Response models are generated with extra="allow" (the spec says forbid) so\n'
    "fields added by later DfT releases are kept rather than rejected; request\n"
    'models keep extra="forbid". See open_response_schemas() in the script.\n'
    '"""\n\n'
)


def fetch_spec(url: str) -> dict:
    import httpx

    response = httpx.get(url, timeout=60.0, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def _rewrite_refs(node: object) -> object:
    """Rewrite Swagger 2.0 ``#/definitions/`` refs to OpenAPI 3 locations."""
    if isinstance(node, dict):
        return {
            key: (
                value.replace("#/definitions/", "#/components/schemas/")
                if key == "$ref" and isinstance(value, str)
                else _rewrite_refs(value)
            )
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_rewrite_refs(item) for item in node]
    return node


def _schema_refs(node: object, found: set[str]) -> set[str]:
    """Collect the names of every schema ``node`` ``$ref``s, in either the
    Swagger 2.0 (``#/definitions/``) or OpenAPI 3 (``#/components/schemas/``)
    form."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                if value.startswith(("#/definitions/", "#/components/schemas/")):
                    found.add(value.rsplit("/", 1)[1])
            else:
                _schema_refs(value, found)
    elif isinstance(node, list):
        for item in node:
            _schema_refs(item, found)
    return found


def _reachable(schemas: dict, roots: set[str]) -> set[str]:
    seen, stack = set(roots), list(roots)
    while stack:
        for name in _schema_refs(schemas.get(stack.pop(), {}), set()) - seen:
            seen.add(name)
            stack.append(name)
    return seen


def _open_objects(node: object) -> None:
    """Flip ``additionalProperties: false`` to ``true`` on a schema and any
    inline object schemas inside it ($refs are left to their own schema)."""
    if isinstance(node, dict):
        if node.get("additionalProperties") is False:
            node["additionalProperties"] = True
        for value in node.values():
            _open_objects(value)
    elif isinstance(node, list):
        for item in node:
            _open_objects(item)


def open_response_schemas(spec: dict) -> dict:
    """Reopen the response schemas of a Swagger 2.0 or OpenAPI 3 spec, so
    their models are generated with ``extra="allow"`` instead of ``"forbid"``.

    Which schemas are responses comes from the spec's own ``paths``: anything
    reachable from an operation's ``responses`` is response-side, anything
    reachable from its ``requestBody``/``parameters`` is request-side. Names
    alone don't work - ``WorkFeature``, ``SiteDetails`` and ``GeoJSONGeometry``
    are response-side without ending in ``Response``. A schema reachable from
    both is opened (validating reads is the common use); one no path
    references falls back to the ``...Response`` naming convention.
    """
    spec = copy.deepcopy(spec)
    schemas = spec.get("components", {}).get("schemas") or spec.get("definitions") or {}

    response_roots: set[str] = set()
    request_roots: set[str] = set()
    for path_item in spec.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        _schema_refs(path_item.get("parameters", []), request_roots)
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            _schema_refs(operation.get("responses", {}), response_roots)
            _schema_refs(operation.get("requestBody", {}), request_roots)
            _schema_refs(operation.get("parameters", []), request_roots)

    response_side = _reachable(schemas, response_roots)
    referenced = response_side | _reachable(schemas, request_roots)
    for name, schema in schemas.items():
        if name in response_side or (name not in referenced and name.endswith("Response")):
            _open_objects(schema)
    return spec


def to_openapi3_schemas(spec: dict) -> dict:
    """Older Street Manager specs were Swagger 2.0; datamodel-code-generator
    reads OpenAPI 3 ``components/schemas``. Model generation only needs the
    schema definitions, so lift ``definitions`` across and rewrite refs.
    OpenAPI 3 documents pass through untouched."""
    if "definitions" in spec and "components" not in spec:
        return {
            "openapi": "3.0.0",
            "info": spec.get("info", {"title": "converted", "version": "0"}),
            "paths": {},
            "components": {"schemas": _rewrite_refs(spec["definitions"])},
        }
    return spec


def generate_one(api: str, spec_path: Path, output_path: Path, source: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "datamodel_code_generator",
        "--input",
        str(spec_path),
        "--input-file-type",
        "openapi",
        "--output",
        str(output_path),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.10",
        "--use-standard-collections",
        "--use-union-operator",
        "--use-schema-description",
        "--field-constraints",
        "--use-double-quotes",
        "--disable-timestamp",
    ]
    subprocess.run(cmd, check=True)
    body = output_path.read_text()
    output_path.write_text(HEADER.format(api=api, source=source) + body)
    try:
        rel = output_path.relative_to(REPO_ROOT)
    except ValueError:
        rel = output_path
    print(f"  wrote {rel}")


def write_package_init(version_dir: Path, apis: list[str]) -> None:
    lines = [f'"""Generated Street Manager models ({version_dir.name})."""\n']
    lines += [f"from . import {api} as {api}" for api in apis]
    (version_dir / "__init__.py").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="v6", help="API version namespace (e.g. v6, v7)")
    parser.add_argument("--apis", nargs="*", default=APIS, help="Subset of APIs to generate")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--from-dir", type=Path, help="Directory containing {api}.json swagger files"
    )
    source.add_argument(
        "--url-template",
        help="URL with {api}/{version} placeholders to download each spec from",
    )
    args = parser.parse_args()

    version_dir = MODELS_ROOT / args.version
    generated: list[str] = []
    failed: list[str] = []

    for api in args.apis:
        try:
            if args.from_dir:
                spec_path = args.from_dir / f"{api}.json"
                if not spec_path.exists():
                    print(f"  skipping {api}: {spec_path} not found")
                    failed.append(api)
                    continue
                spec = json.loads(spec_path.read_text())
                source_desc = spec_path.name
            else:
                url = args.url_template.format(api=api, version=args.version)
                print(f"  fetching {url}")
                spec = fetch_spec(url)
                source_desc = url
            spec = to_openapi3_schemas(open_response_schemas(spec))
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
                json.dump(spec, handle)
                tmp = Path(handle.name)
            generate_one(api, tmp, version_dir / f"{api}.py", source_desc)
            tmp.unlink()
            generated.append(api)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  FAILED {api}: {exc}")
            failed.append(api)

    if generated:
        write_package_init(version_dir, generated)
        models_init = MODELS_ROOT / "__init__.py"
        if not models_init.exists():
            models_init.write_text(
                '"""Generated Street Manager models, namespaced by API version."""\n'
            )

    print(f"\nGenerated: {', '.join(generated) or 'none'}")
    if failed:
        print(f"Failed/skipped: {', '.join(failed)}")
    return 0 if generated and not failed else (0 if generated else 1)


if __name__ == "__main__":
    raise SystemExit(main())
