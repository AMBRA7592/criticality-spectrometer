"""Regenerate every committed derived artifact from authoritative sources."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from criticality_spectrometer import load_model, run_sweep, to_document  # noqa: E402
from criticality_spectrometer.report import (  # noqa: E402
    RESULT_SCHEMA_VERSION,
    _load_result_schema,
)


AI = ROOT / "examples" / "ai_compute"
RESULTS = AI / "results.json"
MISSIONS = {
    "topology": AI / "model_topology.json",
    "frontier_stack": AI / "model_frontier_stack.json",
    "frontier_fab_only": AI / "model_frontier_fab_only.json",
}


def run_script(path: Path) -> None:
    subprocess.run([sys.executable, str(path)], cwd=ROOT, check=True)


def main() -> None:
    run_script(AI / "build_ai_case.py")

    reports = {}
    for mission, path in MISSIONS.items():
        # Sweep each model over its own declared horizons instead of a
        # hardcoded list. Read them verbatim from the file (load_model coerces
        # to float, which would serialize 0 as 0.0 in the committed bundle and
        # in the figure's axis labels).
        declared = json.loads(path.read_text(encoding="utf-8")).get("horizons")
        model = load_model(str(path))
        result = run_sweep(model, declared)
        reports[mission] = to_document(model, result)

    bundle = {
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "reports": reports,
    }
    jsonschema.validate(bundle, _load_result_schema())
    RESULTS.write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    run_script(ROOT / "scripts" / "render_readme_figure.py")
    run_script(ROOT / "examples" / "kubernetes" / "build_bookinfo_case.py")
    print(
        "regenerated AI models, Kubernetes models, ledgers, results, "
        "explanations, and README figure"
    )


if __name__ == "__main__":
    main()
