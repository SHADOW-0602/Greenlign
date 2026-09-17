"""Tests for GHG Protocol taxonomy constants and validators."""


from app.constants.ghg_taxonomy import (
    ALL_GHG_CATEGORIES,
    GHG_SCOPES,
    SCOPE_1_CATEGORIES,
    SCOPE_2_CATEGORIES,
    SCOPE_3_CATEGORIES,
    get_categories_for_scope,
    validate_category,
    validate_scope,
    validate_scope_category,
)


def test_scopes_defined():
    assert GHG_SCOPES == (1, 2, 3)
    assert validate_scope(1) is True
    assert validate_scope(2) is True
    assert validate_scope(3) is True
    assert validate_scope(0) is False
    assert validate_scope(4) is False


def test_scope_1_categories():
    assert "stationary_combustion" in SCOPE_1_CATEGORIES
    assert "mobile_combustion" in SCOPE_1_CATEGORIES
    assert "fugitive_emissions" in SCOPE_1_CATEGORIES
    assert "process_emissions" in SCOPE_1_CATEGORIES
    assert validate_scope_category(1, "stationary_combustion") is True
    assert validate_scope_category(1, "purchased_electricity") is False


def test_scope_2_categories():
    assert "purchased_electricity" in SCOPE_2_CATEGORIES
    assert "purchased_steam" in SCOPE_2_CATEGORIES
    assert validate_scope_category(2, "purchased_electricity") is True
    assert validate_scope_category(2, "business_travel") is False


def test_scope_3_categories():
    assert len(SCOPE_3_CATEGORIES) == 15
    assert "purchased_goods_services" in SCOPE_3_CATEGORIES
    assert "business_travel" in SCOPE_3_CATEGORIES
    assert "employee_commuting" in SCOPE_3_CATEGORIES
    assert validate_scope_category(3, "business_travel") is True
    assert validate_scope_category(3, "mobile_combustion") is False


def test_all_categories_union():
    total_count = len(SCOPE_1_CATEGORIES) + len(SCOPE_2_CATEGORIES) + len(SCOPE_3_CATEGORIES)
    assert len(ALL_GHG_CATEGORIES) == total_count
    assert validate_category("stationary_combustion") is True
    assert validate_category("purchased_electricity") is True
    assert validate_category("business_travel") is True
    assert validate_category("invalid_unknown_category") is False


def test_get_categories_for_scope():
    assert get_categories_for_scope(1) == list(SCOPE_1_CATEGORIES)
    assert get_categories_for_scope(2) == list(SCOPE_2_CATEGORIES)
    assert get_categories_for_scope(3) == list(SCOPE_3_CATEGORIES)
    assert get_categories_for_scope(99) == []
