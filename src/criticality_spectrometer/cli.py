"""
Command-line interface.

    criticality-spectrometer run MODEL.json [--horizons 0,12,24]
                                            [--format json|text]
                                            [--policy]
    criticality-spectrometer validate MODEL.json
    criticality-spectrometer example NAME [--output PATH]
    criticality-spectrometer explain MODEL.json NODE [--horizons 0,12,24]
                                                     [--format text|json]

`run` loads and validates a model, runs the sweep, and prints a deterministic
report. `validate` loads and validates only, printing OK or the error.
`example` emits a bundled example model byte-for-byte (stdout by default), so a
pip-installed instrument can be exercised without cloning the repository.
`explain` reports, per horizon, why one node's removal has the impact it has:
lost and restored sinks, casualties by cascade round, unsatisfied requirement
groups, and substitute status.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from importlib import resources

from ._version import __version__
from .explain import explain_json, explain_document, explain_text
from .model import load_model, ModelError
from .sweep import run_sweep, BaselineError
from .report import to_json, to_text


class CLIError(Exception):
    """User-facing CLI input error -> exit code 2."""


def _parse_horizons(s: str | None) -> list[float] | None:
    if not s:
        return None
    out: list[float] = []
    for part in s.split(","):
        part = part.strip()
        if part == "":
            continue
        try:
            v = float(part)
        except ValueError:
            raise CLIError(f"invalid horizon {part!r}: not a number")
        if not math.isfinite(v):
            raise CLIError(f"invalid horizon {part!r}: must be finite")
        if v < 0:
            raise CLIError(f"invalid horizon {part!r}: must be >= 0")
        out.append(v)
    if not out:
        raise CLIError("no valid horizons provided")
    return out


def _load(path: str):
    try:
        return load_model(path)
    except FileNotFoundError:
        raise CLIError(f"file not found: {path}")
    except json.JSONDecodeError as e:
        raise CLIError(f"malformed JSON in {path}: {e}")
    # ModelError propagates to caller (also exit 2).


def cmd_run(args: argparse.Namespace) -> int:
    try:
        horizons = _parse_horizons(args.horizons)
        model = _load(args.model)
    except (CLIError, ModelError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    try:
        result = run_sweep(model, horizons)
    except BaselineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    if args.format == "json":
        print(to_json(model, result, include_policy=args.policy))
    else:
        print(to_text(model, result, include_policy=args.policy))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        model = _load(args.model)
    except (CLIError, ModelError) as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 2
    print(f"OK: {model.name or 'model'} — {len(model.nodes)} nodes, "
          f"{len(model.dependencies)} dependencies, {len(model.alternatives)} alternatives")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    try:
        horizons = _parse_horizons(args.horizons)
        model = _load(args.model)
    except (CLIError, ModelError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    try:
        if args.format == "json":
            print(explain_json(model, args.node, horizons))
        else:
            print(explain_text(explain_document(model, args.node, horizons)))
    except ModelError as e:  # unknown node
        print(f"error: {e}", file=sys.stderr)
        return 2
    except BaselineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    return 0


EXAMPLE_NAMES = ("canonical", "tutorial")


def cmd_example(args: argparse.Namespace) -> int:
    # Emit the packaged copy byte-for-byte so the file's SHA-256 matches the
    # repository fixture and any provenance-stamped report derived from it.
    data = (
        resources.files("criticality_spectrometer._examples")
        .joinpath(f"{args.name}.json")
        .read_bytes()
    )
    if args.output is None:
        sys.stdout.buffer.write(data)
        return 0
    try:
        with open(args.output, "xb") as f:
            f.write(data)
    except FileExistsError:
        print(f"error: refusing to overwrite existing file: {args.output}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"error: cannot write {args.output}: {e}", file=sys.stderr)
        return 2
    print(f"wrote {args.name} example model to {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="criticality-spectrometer")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="run the sweep and print a report")
    r.add_argument("model", help="path to a model JSON file")
    r.add_argument("--horizons", help="comma-separated tau values, e.g. 0,12,24")
    r.add_argument("--format", choices=["json", "text"], default="text")
    r.add_argument("--policy", action="store_true", help="include optional policy verbs")
    r.set_defaults(func=cmd_run)

    v = sub.add_parser("validate", help="validate a model without running")
    v.add_argument("model", help="path to a model JSON file")
    v.set_defaults(func=cmd_validate)

    e = sub.add_parser("example", help="emit a bundled example model")
    e.add_argument("name", choices=EXAMPLE_NAMES, help="which bundled model to emit")
    e.add_argument("--output", help="write to this path instead of stdout; refuses to overwrite")
    e.set_defaults(func=cmd_example)

    x = sub.add_parser("explain", help="explain one node's impact curve")
    x.add_argument("model", help="path to a model JSON file")
    x.add_argument("node", help="node id to explain")
    x.add_argument("--horizons", help="comma-separated tau values, e.g. 0,12,24")
    x.add_argument("--format", choices=["text", "json"], default="text")
    x.set_defaults(func=cmd_explain)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
