#!/usr/bin/env python3
"""Build the Kubernetes Bookinfo declared-vs-observed worked example."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from criticality_spectrometer import (  # noqa: E402
    explain_document,
    load_model,
    run_sweep,
    to_document,
)
from criticality_spectrometer.report import (  # noqa: E402
    RESULT_SCHEMA_VERSION,
    _load_result_schema,
)

SOURCES = HERE / "sources"
DECLARED_SOURCE = SOURCES / "declared_inventory.json"
OBSERVED_SOURCE = SOURCES / "observed_request.json"
HORIZONS = [0, 5]

NODE_IDS = [
    "client_request",
    "details_v1",
    "ratings_v1",
    "reviews_v1",
    "reviews_v2",
    "reviews_v3",
    "productpage_v1",
    "details_service",
    "ratings_service",
    "reviews_service",
    "complete_book_page",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_sources(declared: dict, observed: dict) -> None:
    expected = {
        "details_service": ["details_v1"],
        "productpage_service": ["productpage_v1"],
        "ratings_service": ["ratings_v1"],
        "reviews_service": ["reviews_v1", "reviews_v2", "reviews_v3"],
    }
    if declared["service_selectors"] != expected:
        raise ValueError("declared Bookinfo selector inventory changed")
    if declared["traffic_policy"]["virtual_service_routes"]["reviews_service"] != "reviews_v1":
        raise ValueError("pinned traffic policy must route reviews to v1")
    if observed["request_id"] != "90706b00-ee24-4f00-b988-f7b2cbff6be7":
        raise ValueError("observed request fixture changed")
    destinations = [record["destination"] for record in observed["records"]]
    if destinations != ["productpage_v1", "details_v1", "reviews_v1"]:
        raise ValueError("observed Bookinfo destination sequence changed")


def dependencies(review_members: list[str]) -> list[dict]:
    return [
        {
            "target": "details_service",
            "logic": "OR",
            "requirements": [{"id": "endpoint", "any_of": ["details_v1"]}],
        },
        {
            "target": "ratings_service",
            "logic": "OR",
            "requirements": [{"id": "endpoint", "any_of": ["ratings_v1"]}],
        },
        {
            "target": "reviews_v2",
            "logic": "AND",
            "requirements": [{"id": "ratings", "any_of": ["ratings_service"]}],
        },
        {
            "target": "reviews_v3",
            "logic": "AND",
            "requirements": [{"id": "ratings", "any_of": ["ratings_service"]}],
        },
        {
            "target": "reviews_service",
            "logic": "OR",
            "requirements": [{"id": "endpoint", "any_of": review_members}],
        },
        {
            "target": "productpage_v1",
            "logic": "AND",
            "requirements": [
                {"id": "request", "any_of": ["client_request"]},
                {"id": "details", "any_of": ["details_service"]},
                {"id": "reviews", "any_of": ["reviews_service"]},
            ],
        },
        {
            "target": "complete_book_page",
            "logic": "AND",
            "requirements": [{"id": "rendered", "any_of": ["productpage_v1"]}],
        },
    ]


def model_document(name: str, review_members: list[str], observed: bool) -> dict:
    description = (
        "Bookinfo service-selector view: every reviews deployment selected by the "
        "Kubernetes Service is immediately eligible."
    )
    alternatives: list[dict] = []
    if observed:
        description = (
            "Bookinfo observed all-v1 route view: the bounded request selected "
            "reviews-v1; a route switch to deployed reviews-v2 is modeled at five minutes."
        )
        alternatives = [
            {
                "target": "reviews_service",
                "requirement_id": "endpoint",
                "replacement": "reviews_v2",
                "activation_time": 5,
                "source": "modeling assumption: operator changes the route within five minutes",
            }
        ]
    return {
        "version": "0.1",
        "name": name,
        "description": description,
        "nodes": [{"id": node} for node in NODE_IDS],
        "dependencies": dependencies(review_members),
        "alternatives": alternatives,
        "outcome": {
            "type": "served_sinks",
            "sources": ["client_request"],
            "sinks": ["complete_book_page"],
        },
        "horizons": HORIZONS,
    }


def evidence_ledger(declared: dict, observed: dict) -> list[dict]:
    upstream = declared["upstream"]
    return [
        {
            "claim": "The Bookinfo base manifest exposes details, ratings, reviews, and productpage Services backed by the listed deployments.",
            "basis": "manifest-derived",
            "source": f"{upstream['repository']}/tree/{upstream['commit']}/samples/bookinfo/platform/kube/bookinfo.yaml",
            "status": "verified",
        },
        {
            "claim": "The reviews Service selector admits reviews-v1, reviews-v2, and reviews-v3 as eligible endpoints.",
            "basis": "manifest-derived",
            "source": "sources/declared_inventory.json#service_selectors",
            "status": "verified",
        },
        {
            "claim": "The pinned all-v1 VirtualService routes reviews traffic to subset v1 while the DestinationRule defines v1, v2, and v3 subsets.",
            "basis": "configuration-derived",
            "source": "sources/declared_inventory.json#traffic_policy",
            "status": "verified",
        },
        {
            "claim": "productpage calls details and reviews; reviews-v2 and reviews-v3 call ratings while reviews-v1 does not.",
            "basis": "source-derived",
            "source": "sources/declared_inventory.json#service_calls",
            "status": "verified",
        },
        {
            "claim": "One externally reported request reached productpage-v1, details-v1, and reviews-v1 with a shared request ID and HTTP 200 records; ratings was not present in the excerpt.",
            "basis": "observed",
            "source": observed["source_attribution"]["source_url"],
            "status": "verified-for-one-request",
        },
        {
            "claim": "The mission requires a page containing both details and reviews.",
            "basis": "modeling-assumption",
            "source": "examples/kubernetes/README.md#mission",
            "status": "assumption",
        },
        {
            "claim": "After reviews-v1 removal, an operator can route to the already-deployed reviews-v2 within five minutes.",
            "basis": "modeling-assumption",
            "source": "examples/kubernetes/README.md#adaptation-assumption",
            "status": "assumption-not-measured",
        },
    ]


def main() -> None:
    declared = read_json(DECLARED_SOURCE)
    observed = read_json(OBSERVED_SOURCE)
    validate_sources(declared, observed)

    declared_doc = model_document(
        "bookinfo_declared_selector_view",
        declared["service_selectors"]["reviews_service"],
        observed=False,
    )
    observed_doc = model_document(
        "bookinfo_observed_v1_route",
        ["reviews_v1"],
        observed=True,
    )
    write_json(HERE / "model_declared.json", declared_doc)
    write_json(HERE / "model.json", observed_doc)
    write_json(HERE / "evidence_ledger.json", evidence_ledger(declared, observed))

    models = {
        "declared": load_model(str(HERE / "model_declared.json")),
        "observed": load_model(str(HERE / "model.json")),
    }
    reports = {
        name: to_document(model, run_sweep(model, HORIZONS))
        for name, model in models.items()
    }
    bundle = {"result_schema_version": RESULT_SCHEMA_VERSION, "reports": reports}
    jsonschema.validate(bundle, _load_result_schema())
    write_json(HERE / "results.json", bundle)

    explanation = explain_document(models["observed"], "reviews_v1", HORIZONS)
    write_json(HERE / "explanations" / "reviews_v1.json", explanation)

    print("regenerated Bookinfo models, ledger, results, and explanation")


if __name__ == "__main__":
    main()
