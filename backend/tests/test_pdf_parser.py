"""Unit tests for PDFParser service.

Tests extraction of structured activity line items from utility bill PDFs
(electricity, natural gas, fuel/freight), canonical normalization, PII tokenization
of suppliers and accounts, multi-page parsing, date handling, and error cases.
"""

import io
from datetime import date
from decimal import Decimal
from pathlib import Path

import pypdf
import pytest

from app.services.pdf_parser import (
    ParsedLineItem,
    ParsedPDFActivityItem,
    PDFParser,
    PDFParserError,
)
from app.services.pii_redaction import PIIRedactor


def create_test_pdf(pages: list[list[str]] | list[str]) -> bytes:
    """Helper to programmatically generate minimal valid PDF bytes with text.

    Accepts either a single page (list of strings) or multiple pages (list of lists of strings).
    """
    writer = pypdf.PdfWriter()

    page_list: list[list[str]]
    if pages and isinstance(pages[0], str):
        page_list = [pages]  # type: ignore[list-item]
    else:
        page_list = pages  # type: ignore[assignment]

    for lines in page_list:
        page = writer.add_blank_page(width=612, height=792)
        escaped_lines: list[str] = []
        for line in lines:
            esc = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            escaped_lines.append(f"({esc}) Tj T*")

        content = "BT /F1 12 Tf 14 TL 72 720 Td " + " ".join(escaped_lines) + " ET"
        stream = pypdf.generic.DecodedStreamObject()
        stream.set_data(content.encode("latin-1", errors="replace"))
        page[pypdf.generic.NameObject("/Contents")] = stream

        f1 = pypdf.generic.DictionaryObject()
        f1[pypdf.generic.NameObject("/Type")] = pypdf.generic.NameObject("/Font")
        f1[pypdf.generic.NameObject("/Subtype")] = pypdf.generic.NameObject("/Type1")
        f1[pypdf.generic.NameObject("/BaseFont")] = pypdf.generic.NameObject("/Helvetica")
        fonts = pypdf.generic.DictionaryObject()
        fonts[pypdf.generic.NameObject("/F1")] = f1
        resources = pypdf.generic.DictionaryObject()
        resources[pypdf.generic.NameObject("/Font")] = fonts
        page[pypdf.generic.NameObject("/Resources")] = resources

    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


class TestPDFParserElectric:
    """Tests electric utility bill PDF extraction."""

    def test_electric_bill_standard(self) -> None:
        lines = [
            "Pacific Gas & Electric",
            "Account Number: 9842-1104",
            "Billing Period: 01/01/2025 - 01/31/2025",
            "Total Electricity Usage: 1,450.50 kWh",
            "Total Charges: $215.40",
        ]
        pdf_bytes = create_test_pdf(lines)
        items = PDFParser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 1
        item = items[0]
        assert item.activity_type == "electricity_purchase"
        assert item.unit == "kWh"
        assert item.quantity == Decimal("1450.50")
        assert isinstance(item.quantity, Decimal)
        assert item.supplier_ref.startswith("TOKEN_SUPP_")
        assert item.supplier_ref == PIIRedactor.tokenize_supplier("Pacific Gas & Electric")
        assert item.period_start == date(2025, 1, 1)
        assert item.period_end == date(2025, 1, 31)
        assert item.raw_line_ref == "page:1,line:4"

    def test_electric_bill_mwh_and_instance_call(self) -> None:
        lines = [
            "Duke Energy",
            "Service Dates: 2025-06-01 to 2025-06-30",
            "Industrial Supply: 25.5 MWh",
            "Amount Due: $3,825.00",
        ]
        pdf_bytes = create_test_pdf(lines)
        parser = PDFParser()
        items = parser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 1
        item = items[0]
        assert item.activity_type == "electricity_purchase"
        assert item.unit == "MWh"
        assert item.quantity == Decimal("25.5")
        assert item.supplier_ref == PIIRedactor.tokenize_supplier("Duke Energy")
        assert item.period_start == date(2025, 6, 1)
        assert item.period_end == date(2025, 6, 30)

    def test_electric_unit_first_format(self) -> None:
        lines = [
            "ConEdison",
            "Invoice Date: 2025-04-15",
            "Usage (kWh): 875.25",
            "Current Charges: $131.29",
        ]
        pdf_bytes = create_test_pdf(lines)
        items = PDFParser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 1
        assert items[0].activity_type == "electricity_purchase"
        assert items[0].unit == "kWh"
        assert items[0].quantity == Decimal("875.25")
        assert items[0].period_start == date(2025, 4, 15)
        assert items[0].period_end == date(2025, 4, 15)


class TestPDFParserNaturalGas:
    """Tests natural gas utility bill PDF extraction."""

    def test_gas_therms_extraction(self) -> None:
        lines = [
            "Southern California Gas Company",
            "Billing Period: 02/01/2025 - 02/28/2025",
            "Natural Gas Usage: 120 therms",
            "Total Charges: $165.00",
        ]
        pdf_bytes = create_test_pdf(lines)
        items = PDFParser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 1
        item = items[0]
        assert item.activity_type == "natural_gas_combustion"
        assert item.unit == "therms"
        assert item.quantity == Decimal("120")
        assert item.supplier_ref == PIIRedactor.tokenize_supplier("Southern California Gas Company")
        assert item.period_start == date(2025, 2, 1)
        assert item.period_end == date(2025, 2, 28)

    def test_gas_ccf_and_mmbtu_extraction(self) -> None:
        lines = [
            "National Grid",
            "Service Dates: 03/01/2025 to 03/31/2025",
            "Meter 1 Gas Consumption: 85.5 CCF",
            "Heating Plant Usage: 45 MMBtu",
        ]
        pdf_bytes = create_test_pdf(lines)
        items = PDFParser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 2
        assert items[0].activity_type == "natural_gas_combustion"
        assert items[0].unit == "ccf"
        assert items[0].quantity == Decimal("85.5")

        assert items[1].activity_type == "natural_gas_combustion"
        assert items[1].unit == "MMBtu"
        assert items[1].quantity == Decimal("45")


class TestPDFParserFreightAndFuel:
    """Tests fuel and freight delivery bill PDF extraction."""

    def test_freight_and_fuel_units(self) -> None:
        lines = [
            "Supplier: Logistics Energy Fleet LLC",
            "Invoice Date: 2025-05-10",
            "Diesel Fuel Delivered: 500 gallons",
            "Secondary Reservoir: 1,250 liters",
            "Road Freight Delivery: 3,400.5 tonne.km",
        ]
        pdf_bytes = create_test_pdf(lines)
        items = PDFParser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 3
        assert items[0].activity_type == "freight_road"
        assert items[0].unit == "gallons"
        assert items[0].quantity == Decimal("500")

        assert items[1].activity_type == "freight_road"
        assert items[1].unit == "liters"
        assert items[1].quantity == Decimal("1250")

        assert items[2].activity_type == "freight_road"
        assert items[2].unit == "tonne.km"
        assert items[2].quantity == Decimal("3400.5")


class TestPDFParserMultiPage:
    """Tests multi-page utility bill extraction."""

    def test_multipage_bill_with_shared_header(self) -> None:
        page_1 = [
            "Florida Power & Light",
            "Account Number: 1122-3344-55",
            "Billing Period: 01/01/2025 - 01/31/2025",
            "Electricity Usage: 2,100 kWh",
            "Page 1 Total: $280.00",
        ]
        page_2 = [
            "Florida Power & Light - Operations",
            "Natural Gas Generator: 350 therms",
            "Backup Generator: 150 gallons",
            "Page 2 Total: $350.00",
        ]
        pdf_bytes = create_test_pdf([page_1, page_2])
        items = PDFParser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 3

        # Page 1 item
        assert items[0].activity_type == "electricity_purchase"
        assert items[0].quantity == Decimal("2100")
        assert items[0].raw_line_ref == "page:1,line:4"
        assert items[0].supplier_ref == PIIRedactor.tokenize_supplier("Florida Power & Light")
        assert items[0].period_start == date(2025, 1, 1)

        # Page 2 items inherit supplier and period
        assert items[1].activity_type == "natural_gas_combustion"
        assert items[1].quantity == Decimal("350")
        assert items[1].raw_line_ref == "page:2,line:2"
        assert items[1].supplier_ref == items[0].supplier_ref
        assert items[1].period_start == date(2025, 1, 1)

        assert items[2].activity_type == "freight_road"
        assert items[2].quantity == Decimal("150")
        assert items[2].raw_line_ref == "page:2,line:3"


class TestPDFParserDollarExclusion:
    """Tests that dollar amounts and rates are excluded from quantities."""

    def test_dollar_amounts_not_captured(self) -> None:
        lines = [
            "Southern California Edison",
            "Billing Period: 01/01/2025 - 01/31/2025",
            "Account Balance: $1,250.00",
            "Previous Balance: $350.00",
            "Payments Received: -$350.00",
            "Total Amount Due: $1,250.00",
            "Energy Charges: 1,450.50 kWh @ $0.15 / kWh = $217.58",
            "Fixed Customer Charge: $25.00",
        ]
        pdf_bytes = create_test_pdf(lines)
        items = PDFParser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 1
        assert items[0].activity_type == "electricity_purchase"
        assert items[0].quantity == Decimal("1450.50")
        assert items[0].unit == "kWh"

    def test_only_dollar_charges_returns_empty(self) -> None:
        lines = [
            "Pacific Gas & Electric",
            "Billing Period: 01/01/2025 - 01/31/2025",
            "Monthly Service Charge: $50.00",
            "Late Fee: $10.00",
            "Total Due: $60.00",
        ]
        pdf_bytes = create_test_pdf(lines)
        items = PDFParser.parse_utility_pdf(pdf_bytes)
        assert items == []


class TestPDFParserDateAndGeography:
    """Tests billing period fallbacks and geography detection."""

    def test_single_invoice_date_defaults_end_to_start(self) -> None:
        lines = [
            "ConEdison",
            "Invoice Date: 2025-07-20",
            "Total Electricity Usage: 500 kWh",
        ]
        pdf_bytes = create_test_pdf(lines)
        items = PDFParser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 1
        assert items[0].period_start == date(2025, 7, 20)
        assert items[0].period_end == date(2025, 7, 20)

    def test_missing_date_defaults_to_today(self) -> None:
        lines = [
            "National Grid",
            "Usage: 750 kWh",
        ]
        pdf_bytes = create_test_pdf(lines)
        items = PDFParser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 1
        today = date.today()
        assert items[0].period_start == today
        assert items[0].period_end == today

    def test_geography_defaults_and_override(self) -> None:
        lines = [
            "Utility Provider: British Power Ltd",
            "Electricity: 1,000 kWh",
        ]
        pdf_bytes = create_test_pdf(lines)

        # Default US
        items_us = PDFParser.parse_utility_pdf(pdf_bytes)
        assert items_us[0].geography == "US"

        # Explicit default geography GB
        items_gb = PDFParser.parse_utility_pdf(pdf_bytes, default_geography="GB")
        assert items_gb[0].geography == "GB"

    def test_extracted_geography_from_state(self) -> None:
        lines = [
            "Pacific Gas & Electric",
            "Service Address: 77 Beale Street, San Francisco, CA 94105",
            "Electricity: 1,200 kWh",
        ]
        pdf_bytes = create_test_pdf(lines)
        items = PDFParser.parse_utility_pdf(pdf_bytes)

        assert len(items) == 1
        assert items[0].geography == "CA"


class TestPDFParserErrorHandling:
    """Tests error handling for invalid or empty PDF inputs."""

    def test_empty_bytes_raises_error(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            PDFParser.parse_utility_pdf(b"")
        assert "empty" in str(exc_info.value).lower()

    def test_whitespace_bytes_raises_error(self) -> None:
        with pytest.raises(ValueError):
            PDFParser.parse_utility_pdf(b"   \n\t   ")

    def test_non_pdf_bytes_raises_error(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            PDFParser.parse_utility_pdf(b"This is not a PDF at all")
        assert issubclass(exc_info.type, ValueError | PDFParserError)

    def test_blank_pdf_returns_empty_list(self) -> None:
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        bio = io.BytesIO()
        writer.write(bio)
        items = PDFParser.parse_utility_pdf(bio.getvalue())
        assert items == []


class TestPDFParserDataContainer:
    """Tests ParsedPDFActivityItem dataclass behavior and exports."""

    def test_dataclass_methods_and_aliases(self) -> None:
        d_start = date(2025, 1, 1)
        d_end = date(2025, 1, 31)
        item = ParsedPDFActivityItem(
            activity_type="electricity_purchase",
            quantity=Decimal("1500.50"),
            unit="kWh",
            geography="US",
            period_start=d_start,
            period_end=d_end,
            supplier_ref="Acme Energy",  # should tokenize in post_init
            raw_line_ref="page:1,line:5",
        )

        assert item.supplier_ref.startswith("TOKEN_SUPP_")
        assert item.supplier_ref == PIIRedactor.tokenize_supplier("Acme Energy")
        assert item["activity_type"] == "electricity_purchase"
        assert item["quantity"] == Decimal("1500.50")

        d = item.to_dict()
        assert d["activity_type"] == "electricity_purchase"
        assert d["quantity"] == Decimal("1500.50")
        assert d["unit"] == "kWh"
        assert d["supplier_ref"].startswith("TOKEN_SUPP_")

        # Alias check
        assert ParsedLineItem is ParsedPDFActivityItem


class TestPDFParserFixture:
    """Tests parsing the synthetic sample_utility_bill.pdf fixture."""

    def test_fixture_utility_bill_file(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "sample_utility_bill.pdf"
        assert fixture_path.exists(), f"Fixture file not found: {fixture_path}"

        content = fixture_path.read_bytes()
        items = PDFParser.parse_utility_pdf(content)

        # The fixture has electric & gas on page 1, freight & fuel on page 2
        assert len(items) == 4

        # Electric
        electric = next(it for it in items if it.activity_type == "electricity_purchase")
        assert electric.unit == "kWh"
        assert electric.quantity == Decimal("1450.50")
        assert electric.supplier_ref == PIIRedactor.tokenize_supplier("Pacific Gas & Electric")
        assert electric.period_start == date(2025, 1, 1)
        assert electric.period_end == date(2025, 1, 31)
        assert electric.geography == "CA"

        # Gas
        gas = next(it for it in items if it.activity_type == "natural_gas_combustion")
        assert gas.unit == "therms"
        assert gas.quantity == Decimal("120.0")

        # Freight & Fuel on Page 2
        freight = next(it for it in items if it.unit == "tonne.km")
        assert freight.activity_type == "freight_road"
        assert freight.quantity == Decimal("3400.5")
        assert freight.raw_line_ref.startswith("page:2,")

        fuel = next(it for it in items if it.unit == "gallons")
        assert fuel.activity_type == "freight_road"
        assert fuel.quantity == Decimal("500")
        assert fuel.raw_line_ref.startswith("page:2,")
