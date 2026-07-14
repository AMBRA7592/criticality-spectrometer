# Schema

The canonical, runtime-loaded schema ships inside the package at
`src/criticality_spectrometer/_schema/model.schema.json` (loaded via
`importlib.resources`, so it resolves whether run from source or installed).

This directory holds human-readable reference copies of the model and result
schemas. Their packaged counterparts live under
`src/criticality_spectrometer/_schema/`. Tests require each pair to remain
byte-identical; the packaged copies are authoritative at runtime.
