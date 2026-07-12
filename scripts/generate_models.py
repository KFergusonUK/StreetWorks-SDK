#!/usr/bin/env python3
"""Generate Pydantic v2 models from the Street Manager swagger specs.

The DfT publishes an OpenAPI/Swagger 2.0 JSON file for each of the nine
Street Manager APIs. This script turns them into typed Pydantic models under
``src/streetworks/streetmanager/models/{version}/``.

Two ways to supply the specs:

1. **From a directory** of downloaded JSON files (the reliable route - the
   API documentation page links every swagger.json; save them as
   ``specs/streetmanager/v6/work.json`` etc.)::

       python scripts/generate_models.py --version v6 --from-dir specs/streetmanager/v6

2. **From URLs**, using a template with ``{api}`` (and optionally
   ``{version}``) placeholders - useful in CI where the runner can reach the
   DfT hosts::

       python scripts/generate_models.py --version v6 \\
           --url-template "https://api.sandbox.manage-roadworks.service.gov.uk/{version}/{api}/swagger.json"

Requires the ``gen`` extra: ``pip install -e ".[gen]"``.

The generated files are committed to the repository so end users get typed
models from PyPI without needing this script. Regenerate whenever DfT release
notes mention schema changes.
"""

from __future__ import annotations

import argparse
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
    "({source}) by scripts/generate_models.py using datamodel-code-generator.\n"
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


def to_openapi3_schemas(spec: dict) -> dict:
    """The Street Manager specs are Swagger 2.0; datamodel-code-generator
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
            spec = to_openapi3_schemas(spec)
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
