"""
Criticality Spectrometer — a domain-agnostic instrument for measuring how
node-removal impact changes as alternatives become available over an adaptation
horizon in systems with AND/OR dependencies.

The engine contains no case-specific entities. All domain content lives in
model instances validated against schema/model.schema.json.
"""

from .model import (
    Model,
    Dependency,
    RequirementGroup,
    Alternative,
    Outcome,
    ModelError,
    ModelWarning,
    load_model,
)
from .cascade import functioning_nodes
from .outcome import count_outcome, baseline_outcome, induced_edges
from .sweep import run_sweep, SweepResult, NodeCurve, default_horizons, BaselineError
from .classify import classify, policy_verb
from .compare import or_relax, survival_gap
from .report import to_document, to_json, to_text
from ._version import __version__

__all__ = [
    "Model", "Dependency", "RequirementGroup", "Alternative", "Outcome",
    "ModelError", "ModelWarning", "BaselineError", "load_model",
    "functioning_nodes", "count_outcome", "baseline_outcome", "induced_edges",
    "run_sweep", "SweepResult", "NodeCurve", "default_horizons",
    "classify", "policy_verb", "or_relax", "survival_gap", "to_document",
    "to_json", "to_text",
    "__version__",
]
