"""Unit tests for TabularParser service.

Tests parsing of CSV and XLSX tabular data with configurable column mapping,
heuristic auto-detection, localized decimal conversion, robust date handling,
supplier PII tokenization, and error cases.
"""

import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import openpyxl
import pytest

from app.services.pii_redaction import PIIRedactor
from app.services.tabular_parser import (
    ParsedActivityRow,
    TabularParser,
    TabularParserError,
)


def _build_xlsx_bytes(headers: list[str], rows: list[list[Any]]) -> bytes:
    """Helper to build in-memory XLSX bytes using openpyxl."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(headers)
    for r in rows:
        ws.append(r)
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


class TestTabularParserCSV:
    """Tests CSV parsing functionality."""

    def test_parse_csv_with_explicit_custom_mapping(self) -> None:
        """Standard ERP CSV with explicit custom mapping dictionary."""
        csv_content = (
            b"TxnID,Vendor,ExpenseCategory,UsageAmount,UOM,Country,StartDate,EndDate\n"
            b"TX-1001,Shell Energy,Natural Gas,1250.50,therms,US,2025-01-01,2025-01-31\n"
            b"TX-1002,National Grid,Electricity,5400.00,kWh,GB,2025-02-01,2025-02-28\n"
        )

        mapping = {
            "raw_line_ref": "TxnID",
            "supplier_ref": "Vendor",
            "activity_type": "ExpenseCategory",
            "quantity": "UsageAmount",
            "unit": "UOM",
            "geography": "Country",
            "period_start": "StartDate",
            "period_end": "EndDate",
        }

        rows = TabularParser.parse_csv(csv_content, mapping=mapping)

        assert len(rows) == 2
        r1 = rows[0]
        assert isinstance(r1, ParsedActivityRow)
        assert r1.raw_line_ref == "TX-1001"
        assert r1.supplier_ref == PIIRedactor.tokenize_supplier("Shell Energy")
        assert r1.supplier_ref.startswith("TOKEN_SUPP_")
        assert r1.activity_type == "Natural Gas"
        assert isinstance(r1.quantity, Decimal)
        assert r1.quantity == Decimal("1250.50")
        assert r1.unit == "therms"
        assert r1.geography == "US"
        assert r1.period_start == date(2025, 1, 1)
        assert r1.period_end == date(2025, 1, 31)

        r2 = rows[1]
        assert r2.raw_line_ref == "TX-1002"
        assert r2.supplier_ref == PIIRedactor.tokenize_supplier("National Grid")
        assert r2.activity_type == "Electricity"
        assert r2.quantity == Decimal("5400.00")
        assert r2.unit == "kWh"
        assert r2.geography == "GB"
        assert r2.period_start == date(2025, 2, 1)
        assert r2.period_end == date(2025, 2, 28)

    def test_parse_csv_with_heuristic_autodetection(self) -> None:
        """CSV parsing auto-detects columns when mapping is None."""
        csv_content = (
            b"Line,Supplier Name,Fuel Type,Consumption,Unit of Measure,"
            b"Location,Start Date,End Date\n"
            b"L-01,Acme Fuels,Diesel,320.75,gallons,US,2025-03-01,2025-03-15\n"
        )

        rows = TabularParser.parse_csv(csv_content, mapping=None)

        assert len(rows) == 1
        r = rows[0]
        assert r.raw_line_ref == "L-01"
        assert r.supplier_ref == PIIRedactor.tokenize_supplier("Acme Fuels")
        assert r.activity_type == "Diesel"
        assert r.quantity == Decimal("320.75")
        assert r.unit == "gallons"
        assert r.geography == "US"
        assert r.period_start == date(2025, 3, 1)
        assert r.period_end == date(2025, 3, 15)

    def test_parse_csv_minimal_columns_and_defaults(self) -> None:
        """Minimal CSV containing only required columns defaults others appropriately."""
        csv_content = (
            b"Fuel,Quantity,Unit,Date\n"
            b"Propane,150,liters,2025-04-10\n"
        )

        rows = TabularParser.parse_csv(csv_content, default_geography="CA")

        assert len(rows) == 1
        r = rows[0]
        assert r.activity_type == "Propane"
        assert r.quantity == Decimal("150")
        assert r.unit == "liters"
        assert r.geography == "CA"  # Default geography passed
        assert r.period_start == date(2025, 4, 10)
        assert r.period_end == date(2025, 4, 10)  # Defaulted to period_start
        assert r.supplier_ref == "TOKEN_SUPP_UNKNOWN"  # No supplier in file
        assert r.raw_line_ref == "row:1"  # 1-indexed fallback

    def test_parse_csv_utf8_bom(self) -> None:
        """CSV with UTF-8 BOM encoding is handled cleanly."""
        csv_text = "Fuel,Quantity,Unit,Date\nPetrol,50,litres,2025-05-01\n"
        bom_bytes = b"\xef\xbb\xbf" + csv_text.encode("utf-8")

        rows = TabularParser.parse_csv(bom_bytes)
        assert len(rows) == 1
        assert rows[0].activity_type == "Petrol"
        assert rows[0].quantity == Decimal("50")

    def test_parse_csv_instance_usage(self) -> None:
        """TabularParser can be used as an instance with preconfigured defaults."""
        parser = TabularParser(
            mapping={
                "quantity": "Consump",
                "activity_type": "Energy",
                "unit": "UOM",
                "period_start": "Dt",
            },
            default_geography="FR",
        )
        csv_content = b"Energy,Consump,UOM,Dt\nSolar,88.4,kWh,2025-06-01\n"
        rows = parser.parse_csv(csv_content)
        assert len(rows) == 1
        assert rows[0].activity_type == "Solar"
        assert rows[0].quantity == Decimal("88.4")
        assert rows[0].geography == "FR"


class TestTabularParserXLSX:
    """Tests XLSX parsing functionality."""

    def test_parse_xlsx_auto_detection(self) -> None:
        """XLSX with auto-detected columns without mapping."""
        headers = ["Line Item", "Vendor", "Fuel", "Usage", "UOM", "Date", "Country"]
        data = [
            ["INV-99", "Pacific Power", "Grid Electricity", 10250.5, "kWh", "2025-05-15", "US"],
            ["INV-100", "Clean Energy", "Biogas", 450, "m3", "2025-05-16", "US"],
        ]
        xlsx_bytes = _build_xlsx_bytes(headers, data)

        rows = TabularParser.parse_xlsx(xlsx_bytes)

        assert len(rows) == 2
        assert rows[0].raw_line_ref == "INV-99"
        assert rows[0].activity_type == "Grid Electricity"
        assert rows[0].quantity == Decimal("10250.5")
        assert rows[0].unit == "kWh"
        assert rows[0].period_start == date(2025, 5, 15)
        assert rows[0].period_end == date(2025, 5, 15)
        assert rows[0].supplier_ref == PIIRedactor.tokenize_supplier("Pacific Power")

        assert rows[1].raw_line_ref == "INV-100"
        assert rows[1].activity_type == "Biogas"
        assert rows[1].quantity == Decimal("450")

    def test_parse_xlsx_with_explicit_mapping(self) -> None:
        """XLSX parsing with custom mapping."""
        headers = ["ColA", "ColB", "ColC", "ColD", "ColE"]
        data = [["Heating Oil", 650.25, "gallons", "2025-01-10", "ConEd"]]
        xlsx_bytes = _build_xlsx_bytes(headers, data)

        mapping = {
            "activity_type": "ColA",
            "quantity": "ColB",
            "unit": "ColC",
            "period_start": "ColD",
            "supplier_ref": "ColE",
        }

        rows = TabularParser.parse_xlsx(xlsx_bytes, mapping=mapping, default_geography="US")
        assert len(rows) == 1
        assert rows[0].activity_type == "Heating Oil"
        assert rows[0].quantity == Decimal("650.25")
        assert rows[0].unit == "gallons"
        assert rows[0].period_start == date(2025, 1, 10)
        assert rows[0].supplier_ref == PIIRedactor.tokenize_supplier("ConEd")
        assert rows[0].raw_line_ref == "row:1"


class TestTabularParserQuantityConversion:
    """Tests robust localized Decimal conversion."""

    @pytest.mark.parametrize(
        ("raw_qty", "expected"),
        [
            ("$1,234.50", Decimal("1234.50")),
            ("2500", Decimal("2500")),
            ("0.85", Decimal("0.85")),
            ("€ 5,432.10", Decimal("5432.10")),
            ("£ 1,000,000", Decimal("1000000")),
            ("(150.25)", Decimal("-150.25")),
            ("-75.00", Decimal("-75.00")),
            (2500, Decimal("2500")),
            (1234.5, Decimal("1234.5")),
            (Decimal("99.99"), Decimal("99.99")),
        ],
    )
    def test_localized_quantities(self, raw_qty: object, expected: Decimal) -> None:
        csv_text = f'Fuel,Quantity,Unit,Date\nDiesel,"{raw_qty}",litres,2025-01-01\n'
        rows = TabularParser.parse_csv(csv_text.encode("utf-8"))
        assert len(rows) == 1
        assert isinstance(rows[0].quantity, Decimal)
        assert rows[0].quantity == expected


class TestTabularParserDateConversion:
    """Tests date parsing across multiple formats."""

    @pytest.mark.parametrize(
        ("date_str", "expected"),
        [
            ("2025-01-15", date(2025, 1, 15)),
            ("2025-01-15T00:00:00Z", date(2025, 1, 15)),
            ("01/15/2025", date(2025, 1, 15)),
            ("15/01/2025", date(2025, 1, 15)),
            ("15-01-2025", date(2025, 1, 15)),
        ],
    )
    def test_date_string_formats(self, date_str: str, expected: date) -> None:
        csv_text = f"Fuel,Quantity,Unit,Date\nGas,100,m3,{date_str}\n"
        rows = TabularParser.parse_csv(csv_text.encode("utf-8"))
        assert len(rows) == 1
        assert isinstance(rows[0].period_start, date)
        assert rows[0].period_start == expected
        assert rows[0].period_end == expected

    def test_excel_native_datetime(self) -> None:
        """Excel cells returning datetime.date or datetime.datetime."""
        headers = ["Fuel", "Quantity", "Unit", "Date"]
        data = [
            ["Coal", 50, "tons", datetime(2025, 6, 20, 14, 30, 0)],
            ["Wood", 10, "tons", date(2025, 6, 21)],
        ]
        xlsx_bytes = _build_xlsx_bytes(headers, data)
        rows = TabularParser.parse_xlsx(xlsx_bytes)

        assert len(rows) == 2
        assert rows[0].period_start == date(2025, 6, 20)
        assert rows[0].period_end == date(2025, 6, 20)
        assert rows[1].period_start == date(2025, 6, 21)


class TestTabularParserPIITokenization:
    """Tests supplier PII tokenization invariants."""

    def test_supplier_always_tokenized(self) -> None:
        csv_text = (
            "Fuel,Quantity,Unit,Date,Supplier\n"
            "Diesel,100,gal,2025-01-01,BP Products North America Inc\n"
            "Electricity,200,kWh,2025-01-01,TOKEN_SUPP_ALREADYTOK\n"
            "Gas,300,therms,2025-01-01,\n"
        )
        rows = TabularParser.parse_csv(csv_text.encode("utf-8"))
        assert len(rows) == 3

        # Fresh raw supplier is tokenized
        assert rows[0].supplier_ref.startswith("TOKEN_SUPP_")
        expected_supp = PIIRedactor.tokenize_supplier("BP Products North America Inc")
        assert rows[0].supplier_ref == expected_supp
        assert "BP" not in rows[0].supplier_ref

        # Already tokenized supplier preserved
        assert rows[1].supplier_ref == "TOKEN_SUPP_ALREADYTOK"

        # Empty supplier converted to UNKNOWN token
        assert rows[2].supplier_ref == "TOKEN_SUPP_UNKNOWN"


class TestTabularParserErrorHandling:
    """Tests error handling for empty files, invalid mappings, and missing data."""

    def test_empty_csv_bytes(self) -> None:
        with pytest.raises(TabularParserError, match="empty"):
            TabularParser.parse_csv(b"")

    def test_whitespace_only_csv(self) -> None:
        with pytest.raises(TabularParserError, match="empty"):
            TabularParser.parse_csv(b"   \n   \r\n   ")

    def test_csv_no_data_rows(self) -> None:
        with pytest.raises(TabularParserError, match="No data rows"):
            TabularParser.parse_csv(b"Fuel,Quantity,Unit,Date\n")

    def test_empty_xlsx_bytes(self) -> None:
        with pytest.raises(TabularParserError):
            TabularParser.parse_xlsx(b"")

    def test_xlsx_no_data_rows(self) -> None:
        headers = ["Fuel", "Quantity", "Unit", "Date"]
        xlsx_bytes = _build_xlsx_bytes(headers, [])
        with pytest.raises(TabularParserError, match="No data rows"):
            TabularParser.parse_xlsx(xlsx_bytes)

    def test_missing_required_column_in_csv(self) -> None:
        # Missing Quantity column entirely
        csv_text = "Fuel,Unit,Date\nDiesel,litres,2025-01-01\n"
        with pytest.raises(TabularParserError, match="Missing required column"):
            TabularParser.parse_csv(csv_text.encode("utf-8"))

    def test_mapped_column_not_in_source(self) -> None:
        csv_text = "Fuel,Quantity,Unit,Date\nDiesel,100,litres,2025-01-01\n"
        mapping = {"quantity": "NonExistentColumn"}
        with pytest.raises(TabularParserError, match="NonExistentColumn"):
            TabularParser.parse_csv(csv_text.encode("utf-8"), mapping=mapping)

    def test_invalid_quantity_value(self) -> None:
        csv_text = "Fuel,Quantity,Unit,Date\nDiesel,INVALID_QTY,litres,2025-01-01\n"
        with pytest.raises(TabularParserError, match="quantity"):
            TabularParser.parse_csv(csv_text.encode("utf-8"))

    def test_invalid_date_value(self) -> None:
        csv_text = "Fuel,Quantity,Unit,Date\nDiesel,100,litres,INVALID_DATE\n"
        with pytest.raises(TabularParserError, match="date"):
            TabularParser.parse_csv(csv_text.encode("utf-8"))
