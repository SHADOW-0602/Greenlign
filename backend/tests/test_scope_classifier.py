"""Tests for ScopeClassifier service."""

import json
from unittest.mock import MagicMock

from app.services.scope_classifier import ScopeClassificationResult, ScopeClassifier


def test_scope_classification_result_validation():
    res = ScopeClassificationResult(
        scope=1,
        ghg_category="stationary_combustion",
        confidence=0.92,
        reasoning="Natural gas burned in boiler",
    )
    assert res.scope == 1
    assert res.ghg_category == "stationary_combustion"
    assert res.confidence == 0.92


def test_scope_classification_result_mismatched_category_fallback():
    # If scope is 2 but category is stationary_combustion (Scope 1), fall back to Scope 2 category
    res = ScopeClassificationResult(
        scope=2,
        ghg_category="stationary_combustion",
        confidence=0.85,
        reasoning="Test mismatch",
    )
    assert res.ghg_category in {
        "purchased_electricity",
        "purchased_steam",
        "purchased_heating",
        "purchased_cooling",
    }


def test_heuristic_classify_electricity():
    classifier = ScopeClassifier()
    res = classifier.classify(
        activity_type="electricity_purchase",
        unit="kWh",
        raw_line_ref="page:1,line:10",
        supplier_ref="TOKEN_SUPP_12345",
    )
    assert res.scope == 2
    assert res.ghg_category == "purchased_electricity"
    assert res.confidence >= 0.75


def test_heuristic_classify_natural_gas():
    classifier = ScopeClassifier()
    res = classifier.classify(
        activity_type="natural_gas_combustion",
        unit="therms",
        raw_line_ref="line:5",
        supplier_ref="TOKEN_SUPP_54321",
    )
    assert res.scope == 1
    assert res.ghg_category == "stationary_combustion"
    assert res.confidence >= 0.75


def test_heuristic_classify_business_travel():
    classifier = ScopeClassifier()
    res = classifier.classify(
        activity_type="commercial_flight_domestic",
        unit="passenger.km",
        raw_line_ref="INV-001",
        supplier_ref="TOKEN_SUPP_AIRLINE",
    )
    assert res.scope == 3
    assert res.ghg_category == "business_travel"
    assert res.confidence >= 0.75


def test_heuristic_classify_low_confidence_fallback():
    classifier = ScopeClassifier()
    res = classifier.classify(
        activity_type="miscellaneous_unknown_entry",
        unit="items",
        raw_line_ref="line:99",
        supplier_ref="TOKEN_SUPP_UNKNOWN",
    )
    assert res.scope == 3
    assert res.confidence < 0.75


def test_groq_mock_client_call():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps({
        "scope": 1,
        "ghg_category": "fugitive_emissions",
        "confidence": 0.88,
        "reasoning": "R-410a refrigerant top-up in chiller unit",
    })
    mock_client.chat.completions.create.return_value.choices = [mock_choice]

    classifier = ScopeClassifier(groq_client=mock_client)
    res = classifier.classify(
        activity_type="chiller_refrigerant_recharge",
        unit="kg",
        raw_line_ref="INV-CHILL-1",
        supplier_ref="Acme HVAC Services",  # Raw name should be tokenized
    )

    assert res.scope == 1
    assert res.ghg_category == "fugitive_emissions"
    assert res.confidence == 0.88
    mock_client.chat.completions.create.assert_called_once()
