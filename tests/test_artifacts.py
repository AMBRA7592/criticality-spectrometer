"""Tests for public schemas, generated artifacts, and the tutorial on-ramp."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re

import jsonschema

from criticality_spectrometer import __version__, load_model, run_sweep, to_text
from criticality_spectrometer.model import MODEL_SCHEMA_VERSION, _load_schema
from criticality_spectrometer.report import RESULT_SCHEMA_VERSION, _load_result_schema


ROOT = Path(__file__).resolve().parent.parent


def test_public_and_packaged_schemas_are_byte_identical():
    public = ROOT / "schema"
    packaged = ROOT / "src" / "criticality_spectrometer" / "_schema"
    for name in ("model.schema.json", "result.schema.json", "explain.schema.json"):
        assert (public / name).read_bytes() == (packaged / name).read_bytes()


def test_repository_and_packaged_example_models_are_byte_identical():
    packaged = ROOT / "src" / "criticality_spectrometer" / "_examples"
    pairs = {
        "canonical.json": ROOT / "examples" / "canonical" / "model.json",
        "tutorial.json": ROOT / "examples" / "tutorial" / "model.json",
    }
    for packaged_name, repository_path in pairs.items():
        assert (packaged / packaged_name).read_bytes() == repository_path.read_bytes()


def test_schema_versions_match_runtime_constants():
    assert _load_schema()["x-schema-version"] == MODEL_SCHEMA_VERSION
    assert _load_result_schema()["x-schema-version"] == RESULT_SCHEMA_VERSION
    packaged_explain = json.loads(
        (ROOT / "src" / "criticality_spectrometer" / "_schema" / "explain.schema.json").read_text()
    )
    from criticality_spectrometer import EXPLAIN_SCHEMA_VERSION

    assert packaged_explain["x-schema-version"] == EXPLAIN_SCHEMA_VERSION


def test_release_versions_are_synchronized():
    pyproject = (ROOT / "pyproject.toml").read_text()
    citation = (ROOT / "CITATION.cff").read_text()
    project_version = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    citation_version = re.search(r"^version: (.+)$", citation, re.MULTILINE)
    assert project_version is not None
    assert citation_version is not None
    assert project_version.group(1) == __version__
    assert citation_version.group(1) == __version__


def test_typing_marker_exists():
    assert (ROOT / "src" / "criticality_spectrometer" / "py.typed").is_file()


def test_committed_result_bundle_validates():
    paths = (
        ROOT / "examples" / "ai_compute" / "results.json",
        ROOT / "examples" / "kubernetes" / "results.json",
    )
    for path in paths:
        jsonschema.validate(json.loads(path.read_text()), _load_result_schema())


def test_path_loaded_model_hashes_raw_file_bytes():
    path = ROOT / "examples" / "canonical" / "model.json"
    model = load_model(str(path))
    assert model.source_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_readme_figure_is_fresh():
    path = ROOT / "scripts" / "render_readme_figure.py"
    spec = importlib.util.spec_from_file_location("render_readme_figure", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert (ROOT / "docs" / "criticality-curves.svg").read_text() == module.render()


def test_tutorial_runner_is_fully_adaptable():
    model = load_model(str(ROOT / "examples" / "tutorial" / "model.json"))
    curve = run_sweep(model).curves["runner_primary"]
    assert curve.impact == [1, 0]
    assert curve.shape == "fully_adaptable"


def test_readme_quickstart_matches_text_report():
    model = load_model(str(ROOT / "examples" / "canonical" / "model.json"))
    report = to_text(model, run_sweep(model))
    line = next(
        line.rstrip()
        for line in report.splitlines()
        if line.startswith("bottleneck")
    )
    assert line in (ROOT / "README.md").read_text()
