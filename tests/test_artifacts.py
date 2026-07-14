"""Tests for public schemas, generated artifacts, and the tutorial on-ramp."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import jsonschema

from criticality_spectrometer import load_model, run_sweep, to_text
from criticality_spectrometer.report import _load_result_schema


ROOT = Path(__file__).resolve().parent.parent


def test_public_and_packaged_schemas_are_byte_identical():
    public = ROOT / "schema"
    packaged = ROOT / "src" / "criticality_spectrometer" / "_schema"
    for name in ("model.schema.json", "result.schema.json"):
        assert (public / name).read_bytes() == (packaged / name).read_bytes()


def test_committed_result_bundle_validates():
    document = json.loads(
        (ROOT / "examples" / "ai_compute" / "results.json").read_text()
    )
    jsonschema.validate(document, _load_result_schema())


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
