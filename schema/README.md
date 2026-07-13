# Schema

The canonical, runtime-loaded schema ships inside the package at
`src/criticality_spectrometer/_schema/model.schema.json` (loaded via
`importlib.resources`, so it resolves whether run from source or installed).

This directory holds a human-readable reference copy. If they ever diverge, the
packaged copy is authoritative.
