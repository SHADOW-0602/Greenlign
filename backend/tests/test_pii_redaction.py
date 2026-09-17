import hashlib
import re

import pytest

from app.services.pii_redaction import PIIRedactor, RedactedResult


def test_redacted_result_dataclass() -> None:
    res = RedactedResult(
        redacted_text="Payment to TOKEN_SUPP_1234567890",
        token_map={"TOKEN_SUPP_1234567890": "Acme Corp"},
    )
    assert res.redacted_text == "Payment to TOKEN_SUPP_1234567890"
    assert res.token_map == {"TOKEN_SUPP_1234567890": "Acme Corp"}
    # Verify dict-style access convenience
    assert res["redacted_text"] == "Payment to TOKEN_SUPP_1234567890"
    assert res["token_map"] == {"TOKEN_SUPP_1234567890": "Acme Corp"}
    with pytest.raises(KeyError):
        _ = res["invalid_key"]


def test_tokenize_supplier_deterministic() -> None:
    supplier = "Acme Industrial Supplies LLC"
    token1 = PIIRedactor.tokenize_supplier(supplier)
    token2 = PIIRedactor.tokenize_supplier(supplier)
    assert token1 == token2
    assert token1.startswith("TOKEN_SUPP_")
    # Verify hex portion is 10 chars uppercase
    hex_part = token1.replace("TOKEN_SUPP_", "")
    assert len(hex_part) == 10
    assert hex_part.isupper()
    assert re.match(r"^[0-9A-F]{10}$", hex_part)

    # Expected hash computation
    expected_hex = (
        hashlib.sha256(b"acme industrial supplies llc")
        .hexdigest()[:10]
        .upper()
    )
    assert token1 == f"TOKEN_SUPP_{expected_hex}"


def test_tokenize_supplier_whitespace_and_case_insensitivity() -> None:
    token_std = PIIRedactor.tokenize_supplier("Pacific Gas & Electric")
    token_spaced = PIIRedactor.tokenize_supplier("  pacific gas & electric  ")
    token_upper = PIIRedactor.tokenize_supplier("PACIFIC GAS & ELECTRIC")
    token_tabs = PIIRedactor.tokenize_supplier("\tpacific gas & electric\n")

    assert token_std == token_spaced
    assert token_std == token_upper
    assert token_std == token_tabs


def test_tokenize_supplier_idempotency() -> None:
    already_tokenized = "TOKEN_SUPP_A1B2C3D4E5"
    assert PIIRedactor.tokenize_supplier(already_tokenized) == already_tokenized

    with_spaces = "  TOKEN_SUPP_A1B2C3D4E5  "
    assert PIIRedactor.tokenize_supplier(with_spaces) == already_tokenized


def test_tokenize_supplier_empty_and_unknown() -> None:
    assert PIIRedactor.tokenize_supplier("") == "TOKEN_SUPP_UNKNOWN"
    assert PIIRedactor.tokenize_supplier("   ") == "TOKEN_SUPP_UNKNOWN"
    assert PIIRedactor.tokenize_supplier("\t\n") == "TOKEN_SUPP_UNKNOWN"


def test_tokenize_account_deterministic() -> None:
    acct = "ACCT-9842-1104"
    token1 = PIIRedactor.tokenize_account(acct)
    token2 = PIIRedactor.tokenize_account(acct)
    assert token1 == token2
    assert token1.startswith("TOKEN_ACCT_")

    hex_part = token1.replace("TOKEN_ACCT_", "")
    assert len(hex_part) == 10
    assert hex_part.isupper()
    assert re.match(r"^[0-9A-F]{10}$", hex_part)

    # Normalization strips spaces and dashes, uppercased -> ACCT98421104
    expected_hex = hashlib.sha256(b"ACCT98421104").hexdigest()[:10].upper()
    assert token1 == f"TOKEN_ACCT_{expected_hex}"


def test_tokenize_account_normalization() -> None:
    token_dash = PIIRedactor.tokenize_account("ACCT-9842-1104")
    token_space = PIIRedactor.tokenize_account("acct 9842 1104")
    token_clean = PIIRedactor.tokenize_account("ACCT98421104")
    token_mixed = PIIRedactor.tokenize_account("  acct - 9842 - 1104  ")

    assert token_dash == token_space
    assert token_dash == token_clean
    assert token_dash == token_mixed


def test_tokenize_account_idempotency() -> None:
    already_tokenized = "TOKEN_ACCT_98421104AB"
    assert PIIRedactor.tokenize_account(already_tokenized) == already_tokenized

    with_spaces = "  TOKEN_ACCT_98421104AB  "
    assert PIIRedactor.tokenize_account(with_spaces) == already_tokenized


def test_tokenize_account_empty_and_unknown() -> None:
    assert PIIRedactor.tokenize_account("") == "TOKEN_ACCT_UNKNOWN"
    assert PIIRedactor.tokenize_account("   ") == "TOKEN_ACCT_UNKNOWN"
    assert PIIRedactor.tokenize_account(" - - ") == "TOKEN_ACCT_UNKNOWN"
    assert PIIRedactor.tokenize_account("---") == "TOKEN_ACCT_UNKNOWN"
    assert PIIRedactor.tokenize_account(".:;!?") == "TOKEN_ACCT_UNKNOWN"
    assert PIIRedactor.tokenize_account("@#$%^&*()") == "TOKEN_ACCT_UNKNOWN"


def test_pii_redactor_instance_methods() -> None:
    redactor = PIIRedactor()
    supp_token = redactor.tokenize_supplier("Acme Corp")
    acct_token = redactor.tokenize_account("ACCT-123456")
    assert supp_token == PIIRedactor.tokenize_supplier("Acme Corp")
    assert acct_token == PIIRedactor.tokenize_account("ACCT-123456")


def test_redact_text_known_suppliers() -> None:
    text = (
        "Received natural gas delivery from Shell Energy North America "
        "and electricity from Pacific Gas & Electric."
    )
    known = ["Shell Energy North America", "Pacific Gas & Electric"]

    redactor = PIIRedactor()
    res = redactor.redact_text(text, known_suppliers=known)

    assert "Shell Energy North America" not in res.redacted_text
    assert "Pacific Gas & Electric" not in res.redacted_text

    shell_token = PIIRedactor.tokenize_supplier("Shell Energy North America")
    pge_token = PIIRedactor.tokenize_supplier("Pacific Gas & Electric")

    assert shell_token in res.redacted_text
    assert pge_token in res.redacted_text

    assert res.token_map[shell_token] == "Shell Energy North America"
    assert res.token_map[pge_token] == "Pacific Gas & Electric"


def test_redact_text_case_insensitive_supplier() -> None:
    text = "Payment sent to pacific gas & electric on Friday."
    known = ["Pacific Gas & Electric"]

    res = PIIRedactor.redact_text(text, known_suppliers=known)
    token = PIIRedactor.tokenize_supplier("Pacific Gas & Electric")

    assert "pacific gas & electric" not in res.redacted_text
    assert "Pacific Gas & Electric" not in res.redacted_text
    assert token in res.redacted_text


def test_redact_text_account_numbers() -> None:
    text = (
        "Monthly invoice. Account #: ACCT-9842-1104. "
        "Meter No: MTR-5544321. Billing Account: 123456789."
    )
    redactor = PIIRedactor()
    res = redactor.redact_text(text)

    # Sensitive numbers must be absent
    assert "ACCT-9842-1104" not in res.redacted_text
    assert "MTR-5544321" not in res.redacted_text
    assert "123456789" not in res.redacted_text

    acct_token1 = PIIRedactor.tokenize_account("ACCT-9842-1104")
    acct_token2 = PIIRedactor.tokenize_account("MTR-5544321")
    acct_token3 = PIIRedactor.tokenize_account("123456789")

    assert acct_token1 in res.redacted_text
    assert acct_token2 in res.redacted_text
    assert acct_token3 in res.redacted_text

    assert res.token_map[acct_token1] == "ACCT-9842-1104"
    assert res.token_map[acct_token2] == "MTR-5544321"
    assert res.token_map[acct_token3] == "123456789"


def test_redact_text_standalone_account_number() -> None:
    text = "Processed recurring payment for ACCT-9842-1104 via ACH."
    res = PIIRedactor().redact_text(text)

    assert "ACCT-9842-1104" not in res.redacted_text
    acct_token = PIIRedactor.tokenize_account("ACCT-9842-1104")
    assert acct_token in res.redacted_text
    assert res.token_map[acct_token] == "ACCT-9842-1104"


def test_redact_text_combined_utility_bill_snippet() -> None:
    snippet = (
        "PACIFIC GAS & ELECTRIC UTILITY STATEMENT\n"
        "Period: 2025-01-01 to 2025-01-31\n"
        "Customer: Acme Industrial Supplies LLC\n"
        "Account Number: ACCT-9842-1104\n"
        "Meter #: MTR-009988\n"
        "Total Electricity: 14,250.50 kWh\n"
        "Total Amount Due: $2,840.10\n"
    )
    known_suppliers = ["Pacific Gas & Electric", "Acme Industrial Supplies LLC"]

    res = PIIRedactor.redact_text(snippet, known_suppliers=known_suppliers)

    # Sensitive tokens completely absent
    assert "PACIFIC GAS & ELECTRIC" not in res.redacted_text
    assert "Pacific Gas & Electric" not in res.redacted_text
    assert "Acme Industrial Supplies LLC" not in res.redacted_text
    assert "ACCT-9842-1104" not in res.redacted_text
    assert "MTR-009988" not in res.redacted_text

    # Non-sensitive utility activity data preserved
    assert "Period: 2025-01-01 to 2025-01-31" in res.redacted_text
    assert "14,250.50 kWh" in res.redacted_text
    assert "$2,840.10" in res.redacted_text

    supp1 = PIIRedactor.tokenize_supplier("Pacific Gas & Electric")
    supp2 = PIIRedactor.tokenize_supplier("Acme Industrial Supplies LLC")
    acct1 = PIIRedactor.tokenize_account("ACCT-9842-1104")
    acct2 = PIIRedactor.tokenize_account("MTR-009988")

    assert supp1 in res.redacted_text
    assert supp2 in res.redacted_text
    assert acct1 in res.redacted_text
    assert acct2 in res.redacted_text

    assert res.token_map[supp1] == "Pacific Gas & Electric"
    assert res.token_map[supp2] == "Acme Industrial Supplies LLC"
    assert res.token_map[acct1] == "ACCT-9842-1104"
    assert res.token_map[acct2] == "MTR-009988"


def test_redact_text_preserves_non_pii_headers() -> None:
    text = (
        "Account Summary\n"
        "Account Details: Overview of electric charges\n"
        "Account Status: Active\n"
        "Acct #: ACCT-11223344"
    )
    res = PIIRedactor().redact_text(text)

    # Headings without digits must not be corrupted
    assert "Account Summary" in res.redacted_text
    assert "Account Details" in res.redacted_text
    assert "Account Status" in res.redacted_text

    # Account number must be redacted
    assert "ACCT-11223344" not in res.redacted_text
    acct_token = PIIRedactor.tokenize_account("ACCT-11223344")
    assert acct_token in res.redacted_text


def test_redact_text_idempotent_on_already_redacted() -> None:
    supp_token = PIIRedactor.tokenize_supplier("Acme Corp")
    acct_token = PIIRedactor.tokenize_account("ACCT-9842-1104")
    text = f"Supplier: {supp_token}, Account: {acct_token}"

    res = PIIRedactor.redact_text(text, known_suppliers=["Acme Corp"])
    assert res.redacted_text == text
    assert len(res.token_map) == 0


def test_redact_text_empty_and_none() -> None:
    res = PIIRedactor.redact_text("")
    assert res.redacted_text == ""
    assert res.token_map == {}


def test_redact_text_instance_default_suppliers() -> None:
    redactor = PIIRedactor(known_suppliers=["Consolidated Edison", "National Grid"])
    text = "Charges from Consolidated Edison and National Grid for power."
    res = redactor.redact_text(text)

    assert "Consolidated Edison" not in res.redacted_text
    assert "National Grid" not in res.redacted_text

    coned_tok = PIIRedactor.tokenize_supplier("Consolidated Edison")
    ng_tok = PIIRedactor.tokenize_supplier("National Grid")
    assert coned_tok in res.redacted_text
    assert ng_tok in res.redacted_text
    assert res.token_map[coned_tok] == "Consolidated Edison"
    assert res.token_map[ng_tok] == "National Grid"


def test_redact_text_longest_supplier_matched_first() -> None:
    known = ["Acme", "Acme Industrial Supplies LLC"]
    text = "Delivered to Acme Industrial Supplies LLC main depot."
    res = PIIRedactor.redact_text(text, known_suppliers=known)

    full_tok = PIIRedactor.tokenize_supplier("Acme Industrial Supplies LLC")
    assert full_tok in res.redacted_text
    assert "Acme Industrial Supplies LLC" not in res.redacted_text
    assert "Industrial Supplies LLC" not in res.redacted_text
    assert res.token_map[full_tok] == "Acme Industrial Supplies LLC"


def test_redact_text_multiple_occurrences_redacted() -> None:
    known = ["Acme Corp"]
    text = (
        "Acme Corp bill for Account #: ACCT-123456. "
        "Please send check to Acme Corp referencing ACCT-123456."
    )
    res = PIIRedactor.redact_text(text, known_suppliers=known)

    assert "Acme Corp" not in res.redacted_text
    assert "ACCT-123456" not in res.redacted_text

    supp_tok = PIIRedactor.tokenize_supplier("Acme Corp")
    acct_tok = PIIRedactor.tokenize_account("ACCT-123456")

    assert res.redacted_text.count(supp_tok) == 2
    assert res.redacted_text.count(acct_tok) == 2


def test_redact_text_various_account_label_formats() -> None:
    cases = [
        ("Account #: 9842-1104", "9842-1104"),
        ("Acct. 9842-1104", "9842-1104"),
        ("Acc # 9842-1104", "9842-1104"),
        ("Account No: 9842-1104", "9842-1104"),
        ("Customer Account: 9842-1104", "9842-1104"),
        ("Customer ID: 9842-1104", "9842-1104"),
        ("Cust ID: 9842-1104", "9842-1104"),
        ("Utility Account #: 9842-1104", "9842-1104"),
        ("Contract Account: 9842-1104", "9842-1104"),
        ("Meter Number: 9842-1104", "9842-1104"),
        ("Meter No.: 9842-1104", "9842-1104"),
    ]
    for text, expected_raw in cases:
        res = PIIRedactor.redact_text(text)
        assert expected_raw not in res.redacted_text, f"Failed for text: {text}"
        tok = PIIRedactor.tokenize_account(expected_raw)
        assert tok in res.redacted_text, f"Expected {tok} in {res.redacted_text}"
        assert res.token_map[tok] == expected_raw


def test_services_package_export() -> None:
    from app.services import PIIRedactor as ExportedPIIRedactor
    from app.services import RedactedResult as ExportedRedactedResult

    assert ExportedPIIRedactor is PIIRedactor
    assert ExportedRedactedResult is RedactedResult


def test_redact_text_tax_id_ein_vat_tin_formats() -> None:
    invoice_text = (
        "Vendor Details:\n"
        "Tax ID: 12-3456789\n"
        "EIN: 98-7654321\n"
        "VAT Number: GB123456789\n"
        "TIN: 555-66-7777\n"
        "Standalone Ref: TAX-99887766\n"
    )
    res = PIIRedactor.redact_text(invoice_text)

    assert "12-3456789" not in res.redacted_text
    assert "98-7654321" not in res.redacted_text
    assert "GB123456789" not in res.redacted_text
    assert "555-66-7777" not in res.redacted_text
    assert "TAX-99887766" not in res.redacted_text

    tax_tok = PIIRedactor.tokenize_account("12-3456789")
    ein_tok = PIIRedactor.tokenize_account("98-7654321")
    vat_tok = PIIRedactor.tokenize_account("GB123456789")
    tin_tok = PIIRedactor.tokenize_account("555-66-7777")
    standalone_tok = PIIRedactor.tokenize_account("TAX-99887766")

    assert tax_tok in res.redacted_text
    assert ein_tok in res.redacted_text
    assert vat_tok in res.redacted_text
    assert tin_tok in res.redacted_text
    assert standalone_tok in res.redacted_text

    assert res.token_map[tax_tok] == "12-3456789"
    assert res.token_map[ein_tok] == "98-7654321"
    assert res.token_map[vat_tok] == "GB123456789"
    assert res.token_map[tin_tok] == "555-66-7777"
    assert res.token_map[standalone_tok] == "TAX-99887766"


def test_redact_text_word_bounded_guarantee_preserves_consumption_numbers() -> None:
    # Account number 12345 shares substring with consumption quantity 123450 kWh
    text = (
        "Electric Statement - Account: 12345\n"
        "Total metered usage for cycle: 123450 kWh at $0.14/kWh.\n"
        "Billed amount: $17,283.00 for Account: 12345."
    )
    res = PIIRedactor.redact_text(text)

    # The account number 12345 must be redacted
    acct_tok = PIIRedactor.tokenize_account("12345")
    assert acct_tok in res.redacted_text

    # The consumption number '123450 kWh' must NOT be corrupted to 'TOKEN_ACCT_...0 kWh'
    assert "123450 kWh" in res.redacted_text
    # The standalone account number 12345 must not appear anywhere as a distinct word
    assert re.search(r"\b12345\b", res.redacted_text.replace(acct_tok, "")) is None
