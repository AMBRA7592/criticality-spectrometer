# Contributing

Criticality Spectrometer is an alpha research instrument. Contributions should preserve a small, inspectable engine and make assumptions explicit.

## Development setup

```bash
python -m pip install -e ".[test]"
pytest -q
```

Before submitting a change, also run:

```bash
git diff --check
python examples/ai_compute/build_ai_case.py
pytest -q
```

The generated AI example files must remain byte-deterministic.

## Engine boundary

Code under `src/criticality_spectrometer/` must remain domain-independent. Put domain entities, assumptions, evidence, and expected results under `examples/` instead.

A new empirical example should include:

- a model that validates against the packaged schema;
- a short statement of its mission outcome;
- an evidence ledger separating sourced facts from assumptions;
- regression assertions for the claimed curves;
- explicit non-claims and known translation gaps.

Do not tune the generic engine to recover a case-specific result. A divergence from an earlier model is useful when it is reproducible and explained.

## Scope

Focused bug fixes, tests, documentation corrections, and independent worked examples are welcome. Larger changes to cascade semantics or the model contract should begin as an issue with a minimal counterexample.
