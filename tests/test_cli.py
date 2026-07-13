"""
CLI tests: exit codes and error handling for bad input.
"""

import json
import os
import tempfile

import pytest

from criticality_spectrometer.cli import main


CANONICAL = os.path.join(os.path.dirname(__file__), "..", "examples", "canonical", "model.json")


def _write(tmp_path, name, content):
    p = os.path.join(tmp_path, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return p


def test_run_canonical_ok():
    assert main(["run", CANONICAL, "--format", "json"]) == 0


def test_validate_ok():
    assert main(["validate", CANONICAL]) == 0


def test_missing_file_exit_2():
    assert main(["run", "/no/such/file.json"]) == 2


def test_malformed_json_exit_2(tmp_path):
    p = _write(tmp_path, "bad.json", "{ not valid json ")
    assert main(["run", p]) == 2


def test_invalid_model_exit_2(tmp_path):
    # Valid JSON, invalid model (missing required 'outcome').
    p = _write(tmp_path, "nomodel.json", json.dumps({"version": "0.1", "nodes": [{"id": "a"}]}))
    assert main(["run", p]) == 2


def test_bad_horizon_not_a_number_exit_2():
    assert main(["run", CANONICAL, "--horizons", "abc"]) == 2


def test_bad_horizon_negative_exit_2():
    assert main(["run", CANONICAL, "--horizons", "0,-5,12"]) == 2


def test_bad_horizon_nan_exit_2():
    assert main(["run", CANONICAL, "--horizons", "nan"]) == 2


def test_bad_horizon_empty_exit_2():
    assert main(["run", CANONICAL, "--horizons", ","]) == 2


def test_baseline_failure_exit_3(tmp_path):
    # Zero-baseline model -> BaselineError -> exit 3.
    d = {
        "version": "0.1",
        "nodes": [{"id": "src"}, {"id": "sink"}, {"id": "dead"}],
        "dependencies": [
            {"target": "dead", "logic": "AND", "requirements": [{"id": "imposs", "any_of": ["sink"]}]},
            {"target": "sink", "logic": "AND", "requirements": [{"id": "fin", "any_of": ["dead"]}]},
        ],
        "outcome": {"type": "served_sinks", "sources": ["src"], "sinks": ["sink"]},
    }
    p = _write(tmp_path, "zero.json", json.dumps(d))
    assert main(["run", p]) == 3


def test_validate_missing_file_exit_2():
    assert main(["validate", "/no/such/file.json"]) == 2


def test_good_horizons_run_ok():
    assert main(["run", CANONICAL, "--horizons", "0,12,24"]) == 0
