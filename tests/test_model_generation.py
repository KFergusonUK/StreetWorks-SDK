"""End-to-end test of the swagger -> Pydantic generation pipeline, using a
small fixture spec shaped like the Street Manager Swagger 2.0 documents."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pydantic
import pytest

pytest.importorskip("datamodel_code_generator")

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "mini-swagger.json"


def test_generate_models_from_swagger2_fixture(tmp_path, monkeypatch):
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    shutil.copy(FIXTURE, spec_dir / "work.json")

    # Redirect output into tmp_path by running the script with a patched root
    script = REPO_ROOT / "scripts" / "generate_models.py"
    env_root = tmp_path / "out"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--version",
            "vtest",
            "--apis",
            "work",
            "--from-dir",
            str(spec_dir),
        ],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/usr/local/bin", "STREETWORKS_MODELS_ROOT": str(env_root)},
    )
    assert result.returncode == 0, result.stdout + result.stderr

    generated = env_root / "vtest" / "work.py"
    assert generated.exists()
    assert "GENERATED FILE" in generated.read_text()

    # Import the generated module and validate a payload with it
    spec = importlib.util.spec_from_file_location("generated_work", generated)
    module = importlib.util.module_from_spec(spec)
    sys.modules["generated_work"] = module  # needed for pydantic forward refs
    spec.loader.exec_module(module)

    permit = module.PermitSummaryResponse.model_validate(
        {"permit_reference_number": "TSR123-01", "status": "granted", "usrn": 12345}
    )
    assert permit.status == module.PermitStatus.granted

    with pytest.raises(pydantic.ValidationError):
        module.PermitSummaryResponse.model_validate({"status": "not-a-status"})


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_models", REPO_ROOT / "scripts" / "generate_models.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _closed(**properties):
    return {"type": "object", "additionalProperties": False, "properties": properties}


@pytest.mark.parametrize("swagger2", [True, False])
def test_open_response_schemas_classifies_by_paths(swagger2):
    prefix = "#/definitions/" if swagger2 else "#/components/schemas/"

    def ref(name):
        return {"$ref": prefix + name}

    schemas = {
        "ThingCreateRequest": _closed(site=ref("SiteInput")),
        "SiteInput": _closed(x={"type": "string"}),
        "ThingResponse": _closed(site=ref("SiteDetails"), inline=_closed()),
        "SiteDetails": _closed(x={"type": "string"}),  # response-side, not named *Response
        "OrphanResponse": _closed(),
        "OrphanThing": _closed(),
    }
    if swagger2:
        operation = {
            "parameters": [{"in": "body", "name": "body", "schema": ref("ThingCreateRequest")}],
            "responses": {"201": {"schema": ref("ThingResponse")}},
        }
        spec = {"swagger": "2.0", "paths": {"/things": {"post": operation}}, "definitions": schemas}
    else:
        body = {"content": {"application/json": {"schema": ref("ThingCreateRequest")}}}
        result = {"content": {"application/json": {"schema": ref("ThingResponse")}}}
        operation = {"requestBody": body, "responses": {"201": result}}
        spec = {
            "openapi": "3.0.0",
            "paths": {"/things": {"post": operation}},
            "components": {"schemas": schemas},
        }

    opened = _load_generator().open_response_schemas(spec)
    out = opened["definitions"] if swagger2 else opened["components"]["schemas"]
    extra = {name: schema["additionalProperties"] for name, schema in out.items()}
    assert extra == {
        "ThingCreateRequest": False,
        "SiteInput": False,
        "ThingResponse": True,
        "SiteDetails": True,
        "OrphanResponse": True,
        "OrphanThing": False,
    }
    assert out["ThingResponse"]["properties"]["inline"]["additionalProperties"] is True
    assert schemas["ThingResponse"]["additionalProperties"] is False  # input not mutated
