#!/usr/bin/env python3
"""Generate Pydantic v2 models from a D-TRO data-model JSON schema.

The DfT publishes the D-TRO data specification as a JSON Schema (draft
2020-12) per version in
https://github.com/department-for-transport-public/D-TRO. This script turns a
downloaded schema into typed Pydantic models under
``src/streetworks/dtro/models/<version>/``.

    pip install -e ".[gen]"
    python scripts/generate_dtro_models.py \
        --version v3_5_1 --schema specs/dtro/v3_5_1/dtro-schema.json

Design choices baked in here:

* **Formatted strings stay plain ``str``.** The schema pairs ``format: email
  / uri / date / date-time`` with constraints like ``minLength``; emitting
  strict types (``EmailStr``/``AnyUrl``/``date``) both drags in the
  ``email-validator`` dependency and, worse, breaks validation where a
  ``minLength`` sits on a ``date`` field. Keeping them as ``str`` gives
  lenient, dependency-free validation that matches how the service actually
  accepts payloads.
* The cross-field ``if/then/else`` rules in the schema are not expressed in
  the models (no Pydantic generator encodes them); the D-TRO service performs
  that conditional validation on submission. These models catch structural,
  type, enum, and required-field errors before you send.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_ROOT = REPO_ROOT / "src" / "streetworks" / "dtro" / "models"

HEADER = (
    '"""GENERATED FILE - do not edit by hand.\n\n'
    "D-TRO data-model Pydantic models for schema {version}, generated from\n"
    "{source} by scripts/generate_dtro_models.py.\n\n"
    "Formatted strings (email/uri/date/date-time) are plain ``str`` for\n"
    "lenient, dependency-free validation. Cross-field conditional rules from\n"
    "the schema are enforced by the D-TRO service on submission, not here.\n"
    '"""\n\n'
)


def _plainify_formats(src: str) -> str:
    """Replace strict format types with plain ``str`` and clean imports."""
    for strict in ("AwareDatetime", "EmailStr", "AnyUrl"):
        src = re.sub(rf"\b{strict}\b", "str", src)
    src = re.sub(r"([:\[]\s*)date\b", r"\1str", src)
    src = src.replace("from datetime import date\n", "")
    src = re.sub(
        r"from pydantic import \([^)]*\)",
        "from pydantic import BaseModel, ConfigDict, Field, RootModel",
        src,
        flags=re.S,
    )
    src = re.sub(
        r"from pydantic import [^\n(][^\n]*",
        "from pydantic import BaseModel, ConfigDict, Field, RootModel",
        src,
    )
    return src


def generate(version: str, schema_path: Path) -> Path:
    out_dir = MODELS_ROOT / version
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "_raw.py"
    cmd = [
        sys.executable,
        "-m",
        "datamodel_code_generator",
        "--input", str(schema_path),
        "--input-file-type", "jsonschema",
        "--output", str(tmp),
        "--output-model-type", "pydantic_v2.BaseModel",
        "--target-python-version", "3.10",
        "--use-standard-collections",
        "--use-union-operator",
        "--use-schema-description",
        "--field-constraints",
        "--use-double-quotes",
        "--disable-timestamp",
    ]
    subprocess.run(cmd, check=True)
    src = _plainify_formats(tmp.read_text())
    tmp.unlink()
    out = out_dir / "models.py"
    out.write_text(HEADER.format(version=version, source=schema_path.name) + src)
    (out_dir / "__init__.py").write_text(
        f'"""Generated D-TRO models for schema {version}."""\n\n'
        "from .models import *  # noqa: F401,F403\n"
    )
    if not (MODELS_ROOT / "__init__.py").exists():
        (MODELS_ROOT / "__init__.py").write_text(
            '"""Generated D-TRO data-model models, namespaced by schema version."""\n'
        )
    print(f"wrote {out.relative_to(REPO_ROOT)}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Version namespace, e.g. v3_5_1")
    parser.add_argument("--schema", type=Path, required=True, help="Path to the JSON schema")
    args = parser.parse_args()
    if not args.schema.exists():
        print(f"schema not found: {args.schema}")
        return 1
    generate(args.version, args.schema)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
