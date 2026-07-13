"""
Curve classification.

Conservative v0.1 labels only. A classification is a pure function of the
impact vector over the swept horizons.

  none                -- zero impact at every horizon
  persistent          -- the same positive impact at every horizon (all equal)
  fully_adaptable     -- positive at tau=0, zero by the last horizon
  partially_adaptable -- declines but is neither flat nor fully to zero

No phase-transition claims; a few horizons cannot support them.
"""

from __future__ import annotations


def classify(impact: list[int]) -> str:
    if not impact:
        return "none"
    if all(v == 0 for v in impact):
        return "none"
    if all(v == impact[0] and v > 0 for v in impact):
        return "persistent"
    if impact[0] > 0 and impact[-1] == 0:
        return "fully_adaptable"
    return "partially_adaptable"


# The policy interpretation layer is optional and explicitly not a theorem.
# See docs/nonclaims.md.
POLICY_VERBS = {
    "persistent": "protect",
    "fully_adaptable": "enable alternatives",
    "partially_adaptable": "invest and bridge",
    "none": "no action",
}


def policy_verb(shape: str) -> str:
    """Optional interpretation. Not a proved result; a reading of the shape."""
    return POLICY_VERBS.get(shape, "no action")
