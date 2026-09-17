"""GHG Protocol Scope and Category Taxonomy Definitions."""

from typing import Final

# Supported Scopes
GHG_SCOPES: Final[tuple[int, ...]] = (1, 2, 3)

# Scope 1: Direct emissions from owned or controlled operations
SCOPE_1_CATEGORIES: Final[tuple[str, ...]] = (
    "stationary_combustion",  # Boilers, furnaces, heaters, incinerators
    "mobile_combustion",      # Company-owned or leased vehicles, fleet trucks
    "process_emissions",      # Chemical or physical processes (cement, aluminum)
    "fugitive_emissions",     # Refrigerant leaks, air conditioning, methane leaks
)

# Scope 2: Indirect emissions from the generation of purchased energy
SCOPE_2_CATEGORIES: Final[tuple[str, ...]] = (
    "purchased_electricity",  # Purchased grid electricity
    "purchased_steam",        # Purchased steam for manufacturing or heating
    "purchased_heating",      # District heating
    "purchased_cooling",      # District chilled water or cooling
)

# Scope 3: Value chain indirect emissions (Categories 1 through 15)
SCOPE_3_CATEGORIES: Final[tuple[str, ...]] = (
    "purchased_goods_services",  # Cat 1: Cradle-to-gate goods and services
    "capital_goods",  # Cat 2: Plant, property, equipment
    "fuel_and_energy_related_activities",  # Cat 3: Upstream fuel/energy emissions
    "upstream_transportation_distribution",  # Cat 4: Inbound logistics and freight
    "waste_generated_in_operations",  # Cat 5: Third-party disposal/treatment
    "business_travel",  # Cat 6: Commercial air travel, rail, hotel stays
    "employee_commuting",  # Cat 7: Employee travel to/from work
    "upstream_leased_assets",  # Cat 8: Operation of leased assets
    "downstream_transportation_distribution",  # Cat 9: Outbound logistics/storage
    "processing_of_sold_products",  # Cat 10: Processing intermediate products
    "use_of_sold_products",  # Cat 11: End use of goods and services sold
    "end_of_life_treatment_of_sold_products",  # Cat 12: Waste disposal of products
    "downstream_leased_assets",  # Cat 13: Operation of owned leased assets
    "franchises",  # Cat 14: Operation of franchises
    "investments",  # Cat 15: Financial investments, equity, debt financing
)

GHG_CATEGORIES_BY_SCOPE: Final[dict[int, tuple[str, ...]]] = {
    1: SCOPE_1_CATEGORIES,
    2: SCOPE_2_CATEGORIES,
    3: SCOPE_3_CATEGORIES,
}

ALL_GHG_CATEGORIES: Final[set[str]] = (
    set(SCOPE_1_CATEGORIES) | set(SCOPE_2_CATEGORIES) | set(SCOPE_3_CATEGORIES)
)


def validate_scope(scope: int) -> bool:
    """Check if the provided scope integer is valid (1, 2, or 3)."""
    return scope in GHG_SCOPES


def validate_category(category: str) -> bool:
    """Check if the category is recognized in the standard taxonomy."""
    return category in ALL_GHG_CATEGORIES


def validate_scope_category(scope: int, category: str) -> bool:
    """Check if the category belongs to the specified scope."""
    valid_categories = GHG_CATEGORIES_BY_SCOPE.get(scope)
    if not valid_categories:
        return False
    return category in valid_categories


def get_categories_for_scope(scope: int) -> list[str]:
    """Return the list of valid category names for a given scope."""
    return list(GHG_CATEGORIES_BY_SCOPE.get(scope, ()))
