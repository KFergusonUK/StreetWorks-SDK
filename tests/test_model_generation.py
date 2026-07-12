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
