"""
CLI tests: exit codes and error handling for bad input.
"""

import json
import os
import tempfile

import pytest

from criticality_spectrometer.cli import main
from criticality_spectrometer import __version__, ModelWarning


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


def test_duplicate_horizons_are_deduplicated(capsys):
    assert main([
        "run",
        CANONICAL,
        "--horizons",
        "12,0,12,0",
        "--format",
        "json",
    ]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["run"]["horizons"] == [0.0, 12.0]


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"criticality-spectrometer {__version__}"


def test_validate_source_dependency_warns_and_exits_zero(tmp_path):
    document = {
        "version": "0.1",
        "nodes": [{"id": "src"}, {"id": "upstream"}, {"id": "sink"}],
        "dependencies": [
            {
                "target": "src",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["upstream"]}],
            },
            {
                "target": "sink",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["src"]}],
            },
        ],
        "outcome": {"type": "served_sinks", "sources": ["src"], "sinks": ["sink"]},
    }
    path = _write(tmp_path, "dependent-source.json", json.dumps(document))
    with pytest.warns(ModelWarning):
        assert main(["validate", path]) == 0


def test_example_stdout_is_byte_identical_to_repository_fixture(capsysbinary):
    assert main(["example", "canonical"]) == 0
    emitted = capsysbinary.readouterr().out
    with open(CANONICAL, "rb") as f:
        assert emitted == f.read()


def test_example_output_file_loads_and_runs(tmp_path):
    target = os.path.join(tmp_path, "model.json")
    assert main(["example", "canonical", "--output", target]) == 0
    assert main(["run", target]) == 0


def test_example_tutorial_is_available(tmp_path):
    target = os.path.join(tmp_path, "tutorial.json")
    assert main(["example", "tutorial", "--output", target]) == 0
    assert main(["validate", target]) == 0


def test_example_refuses_to_overwrite(tmp_path):
    target = _write(tmp_path, "existing.json", "{}")
    assert main(["example", "canonical", "--output", target]) == 2
    with open(target, "r", encoding="utf-8") as f:
        assert f.read() == "{}"


def test_example_unknown_name_rejected():
    with pytest.raises(SystemExit) as exc:
        main(["example", "no-such-model"])
    assert exc.value.code == 2


def test_explain_text_ok(capsys):
    assert main(["explain", CANONICAL, "bottleneck"]) == 0
    out = capsys.readouterr().out
    assert "explain 'bottleneck'" in out
    assert "round 1: assembler" in out


def test_explain_json_ok(capsys):
    assert main(["explain", CANONICAL, "bottleneck", "--format", "json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["impact"] == [1, 0, 0]
    assert document["shape"] == "fully_adaptable"


def test_explain_unknown_node_exit_2(capsys):
    assert main(["explain", CANONICAL, "ghost"]) == 2
    assert "not a declared node" in capsys.readouterr().err


def test_explain_missing_file_exit_2():
    assert main(["explain", "/no/such/file.json", "x"]) == 2


def test_explain_bad_horizons_exit_2():
    assert main(["explain", CANONICAL, "bottleneck", "--horizons", "abc"]) == 2


def test_explain_zero_baseline_exit_3(tmp_path):
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
    assert main(["explain", p, "src"]) == 3
