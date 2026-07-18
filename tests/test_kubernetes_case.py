"""Regression tests for the Kubernetes Bookinfo worked example."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from criticality_spectrometer import (
    explain_document,
    load_model,
    run_sweep,
    to_document,
)

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "examples" / "kubernetes"


@pytest.fixture(scope="module")
def models():
    return {
        "declared": load_model(str(CASE / "model_declared.json")),
        "observed": load_model(str(CASE / "model.json")),
    }


@pytest.fixture(scope="module")
def sweeps(models):
    return {name: run_sweep(model, [0, 5]) for name, model in models.items()}


def test_source_artifacts_are_separate_and_typed():
    declared = json.loads((CASE / "sources" / "declared_inventory.json").read_text())
    observed = json.loads((CASE / "sources" / "observed_request.json").read_text())
    assert declared["basis"] == "manifest-and-source-derived"
    assert observed["basis"] == "observed"
    assert observed["request_id"] == "90706b00-ee24-4f00-b988-f7b2cbff6be7"
    assert len(observed["records"]) == 3


def test_upstream_bookinfo_revision_and_hashes_are_pinned():
    declared = json.loads((CASE / "sources" / "declared_inventory.json").read_text())
    upstream = declared["upstream"]
    assert upstream["repository"] == "https://github.com/istio/istio"
    assert upstream["commit"] == "a54429a603bca459b4329adc226f247cac0b8fc4"
    assert len(upstream["files"]) == 7
    assert all(len(record["sha256"]) == 64 for record in upstream["files"])


def test_models_share_the_same_eleven_nodes(models):
    assert set(models["declared"].nodes) == set(models["observed"].nodes)
    assert len(models["observed"].nodes) == 11


def test_selector_view_preserves_all_reviews_endpoints(models):
    group = models["declared"].dependencies["reviews_service"].requirements[0]
    assert group.id == "endpoint"
    assert set(group.any_of) == {"reviews_v1", "reviews_v2", "reviews_v3"}


def test_observed_view_preserves_v1_and_timed_route_change(models):
    group = models["observed"].dependencies["reviews_service"].requirements[0]
    assert group.any_of == ("reviews_v1",)
    assert len(models["observed"].alternatives) == 1
    alternative = models["observed"].alternatives[0]
    assert (alternative.target, alternative.requirement_id) == (
        "reviews_service",
        "endpoint",
    )
    assert (alternative.replacement, alternative.activation_time) == ("reviews_v2", 5)


def test_declared_selector_view_hides_reviews_v1_criticality(sweeps):
    curve = sweeps["declared"].curves["reviews_v1"]
    assert curve.impact == [0, 0]
    assert curve.shape == "none"


def test_observed_route_view_produces_nonconstant_curve(sweeps):
    curve = sweeps["observed"].curves["reviews_v1"]
    assert curve.impact == [1, 0]
    assert curve.shape == "fully_adaptable"


def test_load_bearing_nodes_remain_persistent(sweeps):
    for node in ("details_v1", "productpage_v1", "complete_book_page"):
        curve = sweeps["observed"].curves[node]
        assert curve.impact == [1, 1], node
        assert curve.shape == "persistent"


def test_explanation_records_failure_rounds_and_restoration(models):
    document = explain_document(models["observed"], "reviews_v1", [0, 5])
    assert document["impact"] == [1, 0]
    assert document["shape"] == "fully_adaptable"
    at_zero, at_five = document["horizons"]
    assert [r["nodes"][0]["node"] for r in at_zero["casualties"]] == [
        "reviews_service",
        "productpage_v1",
        "complete_book_page",
    ]
    assert at_five["restored_sinks"] == ["complete_book_page"]
    assert [s["replacement"] for s in at_five["rescuing_substitutes"]] == [
        "reviews_v2"
    ]


def test_evidence_ledger_separates_facts_and_assumptions():
    ledger = json.loads((CASE / "evidence_ledger.json").read_text())
    bases = {entry["basis"] for entry in ledger}
    assert {
        "manifest-derived",
        "configuration-derived",
        "source-derived",
        "observed",
        "modeling-assumption",
    } <= bases
    assumptions = [entry for entry in ledger if entry["basis"] == "modeling-assumption"]
    assert assumptions
    assert all(entry["status"].startswith("assumption") for entry in assumptions)


def test_committed_results_and_explanation_match_fresh_runs(models, sweeps):
    results = json.loads((CASE / "results.json").read_text())
    for name, sweep in sweeps.items():
        assert results["reports"][name] == to_document(models[name], sweep)
    committed = json.loads((CASE / "explanations" / "reviews_v1.json").read_text())
    assert committed == explain_document(models["observed"], "reviews_v1", [0, 5])


def test_builder_is_location_independent_and_byte_deterministic(tmp_path):
    generated = [
        CASE / "model.json",
        CASE / "model_declared.json",
        CASE / "evidence_ledger.json",
        CASE / "results.json",
        CASE / "explanations" / "reviews_v1.json",
    ]
    before = {path: path.read_bytes() for path in generated}
    subprocess.run(
        [sys.executable, str(CASE / "build_bookinfo_case.py")],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert {path: path.read_bytes() for path in generated} == before
