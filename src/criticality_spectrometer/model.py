"""
Model loading and validation.

A Model is a pure data object: nodes, typed dependencies with identified
requirement groups, group-targeted time-stamped alternatives, and an outcome.
The engine reads this and nothing else. Loading validates against the JSON
Schema and then applies referential-integrity checks the schema cannot express.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from dataclasses import dataclass, field
from importlib import resources
from typing import Any

import jsonschema


MODEL_SCHEMA_VERSION = "0.1"


class ModelError(ValueError):
    """Raised when a model instance is invalid."""


class ModelWarning(UserWarning):
    """Warns about valid but potentially surprising model semantics."""


@dataclass(frozen=True)
class RequirementGroup:
    id: str
    any_of: tuple[str, ...]


@dataclass(frozen=True)
class Dependency:
    target: str
    logic: str  # "AND" or "OR"
    requirements: tuple[RequirementGroup, ...]

    def group(self, gid: str) -> RequirementGroup | None:
        for g in self.requirements:
            if g.id == gid:
                return g
        return None


@dataclass(frozen=True)
class Alternative:
    target: str
    requirement_id: str
    replacement: str
    activation_time: float
    source: str | None = None


@dataclass(frozen=True)
class Outcome:
    type: str  # "served_sinks" or "ordered_served_sinks"
    sources: tuple[str, ...]
    sinks: tuple[str, ...]
    waypoints: tuple[tuple[str, ...], ...] = ()


@dataclass
class Model:
    version: str
    nodes: dict[str, dict[str, Any]]
    dependencies: dict[str, Dependency]
    alternatives: list[Alternative]
    outcome: Outcome
    horizons: list[float] = field(default_factory=list)
    name: str = ""
    description: str = ""
    source_sha256: str = ""

    @property
    def node_ids(self) -> set[str]:
        return set(self.nodes.keys())


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ModelError(message)


def _load_schema() -> dict:
    # Schema is packaged inside criticality_spectrometer/_schema/ so it resolves
    # correctly whether run from source or installed as a wheel.
    with resources.files("criticality_spectrometer._schema").joinpath(
        "model.schema.json"
    ).open("r", encoding="utf-8") as f:
        return json.load(f)


def load_model(path_or_dict: str | dict) -> Model:
    if isinstance(path_or_dict, str):
        with open(path_or_dict, "rb") as f:
            source_bytes = f.read()
        data = json.loads(source_bytes.decode("utf-8"))
    else:
        data = path_or_dict
        source_bytes = json.dumps(
            data, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()

    # --- JSON Schema validation (structure, types, enums, additionalProperties) ---
    try:
        jsonschema.validate(instance=data, schema=_load_schema())
    except jsonschema.ValidationError as e:
        raise ModelError(f"Schema validation failed: {e.message}") from e

    # --- nodes ---
    nodes: dict[str, dict[str, Any]] = {}
    for rec in data["nodes"]:
        nid = rec["id"]
        _require(nid not in nodes, f"Duplicate node id: {nid!r}.")
        _require(
            nid == nid.strip() and " " not in nid,
            f"Node id {nid!r} must be whitespace-free.",
        )
        nodes[nid] = rec

    # --- dependencies ---
    dependencies: dict[str, Dependency] = {}
    for rec in data.get("dependencies", []):
        target = rec["target"]
        _require(target in nodes, f"Dependency target {target!r} is not a declared node.")
        _require(target not in dependencies, f"Duplicate dependency for target {target!r}.")
        groups: list[RequirementGroup] = []
        seen_gids: set[str] = set()
        for greq in rec["requirements"]:
            gid = greq["id"]
            _require(gid not in seen_gids, f"Duplicate requirement id {gid!r} in target {target!r}.")
            seen_gids.add(gid)
            for member in greq["any_of"]:
                _require(
                    member in nodes,
                    f"Requirement {gid!r} of {target!r} references undeclared node {member!r}.",
                )
                _require(
                    member != target,
                    f"Requirement {gid!r} of {target!r} directly references its own target. "
                    "Direct self-satisfaction bypasses dependency enforcement.",
                )
            groups.append(RequirementGroup(id=gid, any_of=tuple(greq["any_of"])))
        dependencies[target] = Dependency(target=target, logic=rec["logic"], requirements=tuple(groups))

    # --- alternatives ---
    alternatives: list[Alternative] = []
    for rec in data.get("alternatives", []):
        target = rec["target"]
        rid = rec["requirement_id"]
        replacement = rec["replacement"]
        _require(target in nodes, f"Alternative target {target!r} is not a declared node.")
        _require(replacement in nodes, f"Alternative replacement {replacement!r} is not a declared node.")
        _require(
            replacement != target,
            f"Alternative for {target!r} uses the target itself as replacement. "
            "Direct self-satisfaction bypasses dependency enforcement.",
        )
        _require(target in dependencies, f"Alternative targets {target!r}, which has no dependency.")
        _require(
            dependencies[target].group(rid) is not None,
            f"Alternative references requirement_id {rid!r} not present in target {target!r}.",
        )
        alternatives.append(
            Alternative(
                target=target,
                requirement_id=rid,
                replacement=replacement,
                activation_time=float(rec["activation_time"]),
                source=rec.get("source"),
            )
        )

    # --- outcome ---
    o = data["outcome"]
    otype = o["type"]
    for sid in o["sources"]:
        _require(sid in nodes, f"Outcome source {sid!r} is not a declared node.")
    for tid in o["sinks"]:
        _require(tid in nodes, f"Outcome sink {tid!r} is not a declared node.")
    waypoints: list[tuple[str, ...]] = []
    if otype == "ordered_served_sinks":
        _require("waypoints" in o, "ordered_served_sinks requires 'waypoints'.")
        for group in o["waypoints"]:
            for member in group:
                _require(member in nodes, f"Waypoint references undeclared node {member!r}.")
            waypoints.append(tuple(group))
    outcome = Outcome(
        type=otype,
        sources=tuple(o["sources"]),
        sinks=tuple(o["sinks"]),
        waypoints=tuple(waypoints),
    )
    for sid in outcome.sources:
        if sid in dependencies:
            warnings.warn(
                f"Outcome source {sid!r} has a dependency. Sources are reachability "
                "starting points, not independent origins, and may stop functioning.",
                ModelWarning,
                stacklevel=2,
            )

    horizons = [float(h) for h in data.get("horizons", [])]

    return Model(
        version=str(data["version"]),
        nodes=nodes,
        dependencies=dependencies,
        alternatives=alternatives,
        outcome=outcome,
        horizons=horizons,
        name=data.get("name", ""),
        description=data.get("description", ""),
        source_sha256=source_sha256,
    )
