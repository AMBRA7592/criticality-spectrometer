# Model Your First System

This tutorial builds a synthetic ten-node CI pipeline. It is deliberately small:
the purpose is to learn the contract, not to claim anything empirical about
software delivery.

The complete model is in
[`examples/tutorial/model.json`](../examples/tutorial/model.json).

## 1. Name the mission

The mission is one released package. The outcome therefore starts at
`source_code` and counts whether the `release` sink remains served:

```json
{
  "type": "served_sinks",
  "sources": ["source_code"],
  "sinks": ["release"]
}
```

A source is a reachability starting point. It is not automatically exempt from
dependencies or cascades. This tutorial leaves `source_code` without a
dependency, so it behaves as an independent origin.

## 2. Write explicit requirements

Compilation and testing each require both source code and an executor. Those are
two requirement groups under `AND` logic:

```json
{
  "target": "compiler",
  "logic": "AND",
  "requirements": [
    {"id": "source", "any_of": ["source_code"]},
    {"id": "executor", "any_of": ["runner_primary"]}
  ]
}
```

Later stages require compiled and tested output, a signing key, and a release
host. Every requirement is visible in the model rather than inferred from graph
position.

## 3. Add a timed alternative

The backup runner can cover the `executor` requirement after four time units:

```json
{
  "target": "compiler",
  "requirement_id": "executor",
  "replacement": "runner_backup",
  "activation_time": 4
}
```

The tutorial has a corresponding alternative for `unit_tests`. A substitute
covers only the requirement group it names.

## 4. Run the sweep

```bash
criticality-spectrometer run examples/tutorial/model.json
```

The primary runner has impact `[1, 0]`: its removal prevents release at
`tau=0`, while the backup restores the mission at `tau=4`. Its shape is
therefore `fully_adaptable`.

## 5. Use the Python API

```python
from criticality_spectrometer import load_model, run_sweep

model = load_model("examples/tutorial/model.json")
result = run_sweep(model)
runner = result.curves["runner_primary"]
print(runner.impact, runner.shape)
# [1, 0] fully_adaptable
```

## 6. Explain the curve

The sweep says the primary runner is `fully_adaptable`; `explain` shows the
mechanism — what breaks at `tau=0` and what restores the mission at `tau=4`:

```bash
criticality-spectrometer explain examples/tutorial/model.json runner_primary
```

Per horizon it reports lost and restored sinks, casualties grouped by cascade
round, every unsatisfied requirement group, and which substitutes are active
versus actually rescuing a group. Rounds are propagation stages, not
unique-causality claims. `--format json` emits the same content as a
self-identifying document.

From here, replace the synthetic nodes and assumptions with a system whose
requirements, alternatives, and activation times you can defend.

