"""Benchmark test suite for ScopeClassifier service on 50 diverse activity items."""

import json
from pathlib import Path

from app.services.scope_classifier import ScopeClassifier

BENCHMARK_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "benchmark_line_items_50.json"
)


def test_scope_classification_benchmark_50_items() -> None:
    """Validate that ScopeClassifier achieves >= 80% accuracy across 50 benchmark items."""
    with open(BENCHMARK_FIXTURE_PATH, encoding="utf-8") as f:
        items = json.load(f)

    assert len(items) == 50, f"Expected 50 benchmark items, found {len(items)}"

    classifier = ScopeClassifier()
    scope_matches = 0
    category_matches = 0
    total_items = len(items)
    mismatches: list[dict[str, object]] = []

    for item in items:
        result = classifier.classify(
            activity_type=item["activity_type"],
            unit=item["unit"],
            raw_line_ref=item["raw_line_ref"],
            supplier_ref=item["supplier_ref"],
        )

        # Basic contract assertions for every item
        assert result.scope in (1, 2, 3)
        assert len(result.ghg_category) > 0
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.reasoning) > 0

        is_scope_match = result.scope == item["expected_scope"]
        is_category_match = result.ghg_category == item["expected_category"]

        if is_scope_match:
            scope_matches += 1
        if is_category_match:
            category_matches += 1
        else:
            mismatches.append({
                "id": item["id"],
                "activity_type": item["activity_type"],
                "expected_scope": item["expected_scope"],
                "predicted_scope": result.scope,
                "expected_category": item["expected_category"],
                "predicted_category": result.ghg_category,
                "confidence": result.confidence,
            })

    scope_accuracy = scope_matches / total_items
    category_accuracy = category_matches / total_items

    # Acceptance criteria: > 80% accuracy against ground truth
    assert scope_accuracy >= 0.80, (
        f"Scope accuracy {scope_accuracy:.1%} is below required 80% threshold. "
        f"Mismatches: {mismatches}"
    )
    assert category_accuracy >= 0.80, (
        f"Category accuracy {category_accuracy:.1%} is below required 80% threshold. "
        f"Mismatches: {mismatches}"
    )


def test_scope_distribution_in_benchmark_fixture() -> None:
    """Verify the benchmark dataset has balanced coverage across Scopes 1, 2, and 3."""
    with open(BENCHMARK_FIXTURE_PATH, encoding="utf-8") as f:
        items = json.load(f)

    scope_counts = {1: 0, 2: 0, 3: 0}
    for item in items:
        scope_counts[item["expected_scope"]] += 1

    # Expected: 15 Scope 1, 10 Scope 2, 25 Scope 3
    assert scope_counts[1] == 15
    assert scope_counts[2] == 10
    assert scope_counts[3] == 25
