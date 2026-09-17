"""Groq LLM-assisted Scope Classification Service.

Classifies ActivityData line items into Scope 1, Scope 2, or Scope 3 and canonical
GHG Protocol categories with confidence scoring.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from groq import Groq

from app.constants.ghg_taxonomy import (
    GHG_CATEGORIES_BY_SCOPE,
    validate_scope_category,
)
from app.core.config import settings
from app.services.pii_redaction import PIIRedactor

logger = logging.getLogger(__name__)


@dataclass
class ScopeClassificationResult:
    """Standardized classification output."""

    scope: int
    ghg_category: str
    confidence: float
    reasoning: str

    def __post_init__(self) -> None:
        self.scope = int(self.scope)
        self.confidence = float(self.confidence)
        if not (0.0 <= self.confidence <= 1.0):
            self.confidence = max(0.0, min(1.0, self.confidence))
        if not validate_scope_category(self.scope, self.ghg_category):
            # If category doesn't match scope, fall back to first valid category for that scope
            valid = GHG_CATEGORIES_BY_SCOPE.get(self.scope)
            if valid:
                self.ghg_category = valid[0]


class ScopeClassifier:
    """Classifies activities using Groq API (llama-3.3-70b-versatile) or heuristic fallback."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        groq_client: Any = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.groq_api_key
        self.model = model or settings.groq_model
        if groq_client:
            self._client = groq_client
        elif (
            self.api_key
            and self.api_key.strip()
            and not self.api_key.startswith("gsk_dummy")
        ):
            self._client = Groq(api_key=self.api_key.strip())
        else:
            self._client = None

    def classify(
        self,
        activity_type: str,
        unit: str,
        raw_line_ref: str = "",
        supplier_ref: str = "",
    ) -> ScopeClassificationResult:
        """Classify an activity row into Scope 1/2/3 and GHG category."""
        # Ensure supplier_ref is tokenized so raw supplier names never reach LLM
        safe_supplier_ref = (
            supplier_ref
            if supplier_ref.startswith("TOKEN_SUPP_")
            else PIIRedactor.tokenize_supplier(supplier_ref)
        )

        # If Groq client is configured, call the LLM
        if self._client:
            try:
                return self._call_groq(
                    activity_type=activity_type,
                    unit=unit,
                    raw_line_ref=raw_line_ref,
                    supplier_ref=safe_supplier_ref,
                )
            except Exception as exc:
                logger.warning(
                    "Groq API call failed (%s). Falling back to heuristic classifier.", exc
                )

        # Heuristic fallback (offline/tests or when no API key is set)
        return self._heuristic_classify(
            activity_type=activity_type,
            unit=unit,
            raw_line_ref=raw_line_ref,
            supplier_ref=safe_supplier_ref,
        )

    def _call_groq(
        self,
        activity_type: str,
        unit: str,
        raw_line_ref: str,
        supplier_ref: str,
    ) -> ScopeClassificationResult:
        """Invoke Groq chat completions with structured JSON response format."""
        system_prompt = (
            "You are an expert GHG accounting classifier following the GHG Protocol "
            "Corporate Standard.\n"
            "Classify the input activity into Scope 1, Scope 2, or Scope 3 and assign a "
            "valid category.\n"
            "Allowed Scope 1 categories: stationary_combustion, mobile_combustion, "
            "process_emissions, fugitive_emissions.\n"
            "Allowed Scope 2 categories: purchased_electricity, purchased_steam, "
            "purchased_heating, purchased_cooling.\n"
            "Allowed Scope 3 categories: purchased_goods_services, capital_goods, "
            "fuel_and_energy_related_activities, upstream_transportation_distribution, "
            "waste_generated_in_operations, business_travel, employee_commuting, "
            "upstream_leased_assets, downstream_transportation_distribution, "
            "processing_of_sold_products, use_of_sold_products, "
            "end_of_life_treatment_of_sold_products, downstream_leased_assets, "
            "franchises, investments.\n\n"
            'Return JSON matching: {"scope": int, "ghg_category": str, '
            '"confidence": float, "reasoning": str}.'
        )

        user_content = (
            f"Activity: {activity_type}\n"
            f"Unit: {unit}\n"
            f"Line Reference: {raw_line_ref}\n"
            f"Supplier Token: {supplier_ref}"
        )

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        return ScopeClassificationResult(
            scope=int(data["scope"]),
            ghg_category=str(data["ghg_category"]),
            confidence=float(data.get("confidence", 0.85)),
            reasoning=str(data.get("reasoning", "Classified by Groq LLM")),
        )

    @classmethod
    def _heuristic_classify(
        cls,
        activity_type: str,
        unit: str,
        raw_line_ref: str,
        supplier_ref: str,
    ) -> ScopeClassificationResult:
        """Deterministic heuristic classifier for offline testing and fallback."""
        text = f"{activity_type} {unit} {raw_line_ref}".lower().replace("_", " ")

        # Scope 2 keywords
        if any(
            w in text
            for w in ["electricity", "kwh", "mwh", "grid power", "electric purchase", "power"]
        ):
            return ScopeClassificationResult(
                scope=2,
                ghg_category="purchased_electricity",
                confidence=0.95,
                reasoning="Electricity grid purchase corresponds to Scope 2 purchased electricity.",
            )
        if any(w in text for w in ["district steam", "purchased steam", "steam"]):
            return ScopeClassificationResult(
                scope=2,
                ghg_category="purchased_steam",
                confidence=0.95,
                reasoning="Steam purchase corresponds to Scope 2 purchased steam.",
            )
        if (
            "district heating" in text
            or "purchased heating" in text
            or "hot water supply" in text
        ):
            return ScopeClassificationResult(
                scope=2,
                ghg_category="purchased_heating",
                confidence=0.95,
                reasoning="District heating corresponds to Scope 2 purchased heating.",
            )
        if "district cooling" in text or "chilled water" in text or "cooling" in text:
            return ScopeClassificationResult(
                scope=2,
                ghg_category="purchased_cooling",
                confidence=0.95,
                reasoning="District cooling corresponds to Scope 2 purchased cooling.",
            )

        # Scope 1 keywords
        if any(
            w in text
            for w in [
                "natural gas",
                "therms",
                "ccf",
                "boiler",
                "furnace",
                "fuel oil",
                "diesel generator",
                "generator",
                "stationary",
                "propane",
                "lpg",
            ]
        ):
            return ScopeClassificationResult(
                scope=1,
                ghg_category="stationary_combustion",
                confidence=0.95,
                reasoning=(
                    "On-site fuel combustion for heating/power corresponds to "
                    "Scope 1 stationary combustion."
                ),
            )
        if any(
            w in text
            for w in [
                "fleet",
                "company vehicle",
                "company car",
                "fleet diesel",
                "fleet gasoline",
                "owned truck",
                "truck diesel",
                "petrol",
            ]
        ):
            return ScopeClassificationResult(
                scope=1,
                ghg_category="mobile_combustion",
                confidence=0.95,
                reasoning=(
                    "Company-owned or leased fleet transport corresponds to "
                    "Scope 1 mobile combustion."
                ),
            )
        if any(
            w in text
            for w in ["refrigerant", "r-410a", "r-134a", "sf6", "leakage", "fugitive"]
        ):
            return ScopeClassificationResult(
                scope=1,
                ghg_category="fugitive_emissions",
                confidence=0.95,
                reasoning="Refrigerant gas releases correspond to Scope 1 fugitive emissions.",
            )
        if any(
            w in text
            for w in [
                "cement",
                "calcination",
                "kiln",
                "process emissions",
                "chemical synthesis",
            ]
        ):
            return ScopeClassificationResult(
                scope=1,
                ghg_category="process_emissions",
                confidence=0.90,
                reasoning=(
                    "Industrial chemical transformations correspond to "
                    "Scope 1 process emissions."
                ),
            )

        # Scope 3 keywords
        if any(
            w in text
            for w in [
                "flight",
                "airline",
                "air travel",
                "airfare",
                "hotel",
                "lodging",
                "business travel",
            ]
        ):
            return ScopeClassificationResult(
                scope=3,
                ghg_category="business_travel",
                confidence=0.95,
                reasoning=(
                    "Employee travel on commercial carriers corresponds to "
                    "Scope 3 Category 6 Business Travel."
                ),
            )
        if any(
            w in text
            for w in ["commute", "commuting", "subway", "transit pass", "metro", "shuttle"]
        ):
            return ScopeClassificationResult(
                scope=3,
                ghg_category="employee_commuting",
                confidence=0.95,
                reasoning=(
                    "Employee travel between residence and work corresponds to "
                    "Scope 3 Category 7 Employee Commuting."
                ),
            )
        if any(
            w in text
            for w in [
                "freight",
                "trucking",
                "shipping",
                "courier",
                "logistics",
                "tonne.km",
                "cargo",
                "parcel",
            ]
        ):
            return ScopeClassificationResult(
                scope=3,
                ghg_category="upstream_transportation_distribution",
                confidence=0.90,
                reasoning=(
                    "Third-party logistics corresponds to "
                    "Scope 3 Category 4 Upstream Transportation."
                ),
            )
        if any(w in text for w in ["waste", "landfill", "recycling", "compost", "refuse"]):
            return ScopeClassificationResult(
                scope=3,
                ghg_category="waste_generated_in_operations",
                confidence=0.90,
                reasoning=(
                    "Waste disposal corresponds to "
                    "Scope 3 Category 5 Waste Generated in Operations."
                ),
            )
        if any(
            w in text
            for w in [
                "capital",
                "machinery",
                "equipment purchase",
                "building acquisition",
                "server rack",
            ]
        ):
            return ScopeClassificationResult(
                scope=3,
                ghg_category="capital_goods",
                confidence=0.85,
                reasoning=(
                    "Purchased physical capital equipment corresponds to "
                    "Scope 3 Category 2 Capital Goods."
                ),
            )
        if any(
            w in text
            for w in [
                "consulting",
                "software",
                "legal",
                "office supplies",
                "raw materials",
                "procurement",
                "catering",
                "cleaning",
                "cloud service",
            ]
        ):
            return ScopeClassificationResult(
                scope=3,
                ghg_category="purchased_goods_services",
                confidence=0.85,
                reasoning=(
                    "Purchased services and supplies correspond to "
                    "Scope 3 Category 1 Purchased Goods & Services."
                ),
            )

        # Low confidence default fallback
        return ScopeClassificationResult(
            scope=3,
            ghg_category="purchased_goods_services",
            confidence=0.50,
            reasoning=(
                "Uncertain activity description; defaulted to Scope 3 "
                "with low confidence for human review."
            ),
        )
