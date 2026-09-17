"""Utility Bill PDF Parser Service.

Extracts structured activity line items from utility bill PDFs (electricity, natural gas,
fuel/freight) and normalizes them into ParsedPDFActivityItem records with PII tokenization applied.
"""

import io
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import dateutil.parser  # type: ignore[import-untyped]
import pypdf
import pypdf.errors

from app.services.pii_redaction import (
    ACCOUNT_LABEL_REGEX,
    ACCOUNT_STANDALONE_REGEX,
    PIIRedactor,
)


class PDFParserError(ValueError):
    """Raised when PDF content is empty, invalid, corrupted, or unreadable."""


@dataclass
class ParsedPDFActivityItem:
    """Normalized activity line item extracted from a utility bill PDF."""

    activity_type: str
    quantity: Decimal
    unit: str
    geography: str
    period_start: date
    period_end: date
    supplier_ref: str
    raw_line_ref: str
    account_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.quantity, Decimal):
            cleaned = str(self.quantity).strip().replace(",", "")
            self.quantity = Decimal(cleaned)
        if not self.supplier_ref.startswith("TOKEN_SUPP_"):
            self.supplier_ref = PIIRedactor.tokenize_supplier(self.supplier_ref)
        if self.account_ref and not self.account_ref.startswith("TOKEN_ACCT_"):
            self.account_ref = PIIRedactor.tokenize_account(self.account_ref)
        if not self.geography:
            self.geography = "US"
        if self.period_end is None:
            self.period_end = self.period_start

    def to_dict(self) -> dict[str, Any]:
        """Convert line item to canonical dictionary."""
        return {
            "activity_type": self.activity_type,
            "quantity": self.quantity,
            "unit": self.unit,
            "geography": self.geography,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "supplier_ref": self.supplier_ref,
            "raw_line_ref": self.raw_line_ref,
            "account_ref": self.account_ref,
        }

    def __getitem__(self, item: str) -> Any:
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)


# Alias for compatibility with brief specifications
ParsedLineItem = ParsedPDFActivityItem


# Supported US 2-letter state codes and territories
US_STATES: set[str] = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "VI", "GU",
}

# Common utility providers list
KNOWN_UTILITIES: list[str] = [
    "Pacific Gas & Electric",
    "Pacific Gas and Electric",
    "PG&E",
    "Southern California Edison",
    "SCE",
    "San Diego Gas & Electric",
    "SDG&E",
    "Consolidated Edison",
    "ConEdison",
    "Con Edison",
    "National Grid",
    "Duke Energy",
    "Florida Power & Light",
    "Florida Power and Light",
    "FPL",
    "Commonwealth Edison",
    "ComEd",
    "Georgia Power",
    "Xcel Energy",
    "Dominion Energy",
    "Consumers Energy",
    "DTE Energy",
    "Eversource Energy",
    "Eversource",
    "American Electric Power",
    "AEP",
    "NextEra Energy",
    "CenterPoint Energy",
    "Entergy",
    "PPL Electric Utilities",
    "PPL Electric",
    "PPL",
    "Public Service Electric and Gas",
    "PSE&G",
    "PSEG",
    "Austin Energy",
    "CPS Energy",
    "Puget Sound Energy",
    "Salt River Project",
    "SRP",
    "Arizona Public Service",
    "APS",
    "NV Energy",
    "PECO Energy",
    "PECO",
    "Baltimore Gas and Electric",
    "BGE",
    "Potomac Electric Power Company",
    "Pepco",
    "Ameren",
    "Exelon",
    "Atmos Energy",
    "Piedmont Natural Gas",
    "Southern California Gas Company",
    "SoCalGas",
    "Nicor Gas",
    "Washington Gas",
    "Peoples Gas",
    "New Jersey Natural Gas",
    "NJNG",
    "Southwest Gas",
    "Columbia Gas",
    "Shell Energy North America",
    "Shell Energy",
    "Constellation Energy",
    "Constellation",
    "Calpine",
    "Engie",
    "NRG Energy",
    "NRG",
    "Vistra Energy",
    "Vistra",
    "Tampa Electric",
    "TECO",
    "Alabama Power",
    "Oklahoma Gas & Electric",
    "OG&E",
    "Portland General Electric",
    "PGE",
    "PacifiCorp",
    "Pacific Power",
    "Rocky Mountain Power",
    "Avangrid",
    "Alliant Energy",
    "Ameren Illinois",
    "Ameren Missouri",
    "WEC Energy Group",
    "We Energies",
    "Wisconsin Electric",
    "OGE Energy",
    "Idaho Power",
    "Hawaiian Electric",
    "HECO",
    "Sierra Pacific Power",
    "Cleco",
    "El Paso Electric",
    "Otter Tail Power",
    "Black Hills Energy",
    "Northwestern Energy",
    "Green Mountain Power",
    "Liberty Utilities",
    "Unitil",
    "UGI Utilities",
    "UGI",
    "Spire Energy",
    "Spire",
]

# Sorted by length descending so longer provider names match before sub-acronyms
KNOWN_UTILITIES_SORTED = sorted(KNOWN_UTILITIES, key=len, reverse=True)

HEADER_SUPPLIER_REGEX = re.compile(
    r"(?i)\b(?:Utility\s+Provider|Utility\s+Name|Utility|Provider|Supplier\s+Name|Supplier|Biller|Vendor|Issued\s+by)\s*[:\-]\s*([A-Za-z0-9&.,\s\'\-]{2,60})"
)

# Date extraction regexes
MONTHS = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)

DATE_TOKEN = (
    rf"(?:{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}|"
    rf"\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS},?\s+\d{{4}}|"
    rf"\d{{4}}[-/.]\d{{1,2}}[-/.]\d{{1,2}}|"
    rf"\d{{1,2}}[-/.]\d{{1,2}}[-/.]\d{{2,4}})"
)

PERIOD_REGEX = re.compile(
    rf"(?i)(?:Billing\s+Period|Service\s+(?:Period|Dates)|Statement\s+Period|Billing\s+Dates)[\s:]+"
    rf"(?P<start>{DATE_TOKEN})\s*(?:-|–|—|\bto\b|\bthrough\b)\s*(?P<end>{DATE_TOKEN})"
)

PERIOD_FALLBACK_REGEX = re.compile(
    rf"(?i)\b(?P<start>{DATE_TOKEN})\s*(?:-|–|—|\bto\b|\bthrough\b)\s*(?P<end>{DATE_TOKEN})\b"
)

SINGLE_DATE_REGEX = re.compile(
    rf"(?i)(?:Invoice\s+Date|Bill\s+Date|Statement\s+Date|Service\s+Date|\bDate\b)[\s:]+"
    rf"(?P<date>{DATE_TOKEN})"
)


# Unit mappings to canonical unit name and activity_type
UNIT_MAPPINGS: dict[str, tuple[str, str]] = {
    "kwh": ("kWh", "electricity_purchase"),
    "kw-h": ("kWh", "electricity_purchase"),
    "kw·h": ("kWh", "electricity_purchase"),
    "mwh": ("MWh", "electricity_purchase"),
    "mw-h": ("MWh", "electricity_purchase"),
    "therm": ("therms", "natural_gas_combustion"),
    "therms": ("therms", "natural_gas_combustion"),
    "ccf": ("ccf", "natural_gas_combustion"),
    "mmbtu": ("MMBtu", "natural_gas_combustion"),
    "mm-btu": ("MMBtu", "natural_gas_combustion"),
    "mbtu": ("MMBtu", "natural_gas_combustion"),
    "gallon": ("gallons", "freight_road"),
    "gallons": ("gallons", "freight_road"),
    "gal": ("gallons", "freight_road"),
    "gals": ("gallons", "freight_road"),
    "liter": ("liters", "freight_road"),
    "liters": ("liters", "freight_road"),
    "litre": ("liters", "freight_road"),
    "litres": ("liters", "freight_road"),
    "tonne.km": ("tonne.km", "freight_road"),
    "tonne-km": ("tonne.km", "freight_road"),
    "tonne km": ("tonne.km", "freight_road"),
    "tkm": ("tonne.km", "freight_road"),
    "ton.km": ("tonne.km", "freight_road"),
    "ton-km": ("tonne.km", "freight_road"),
}

UNITS_REGEX_STR = (
    r"kWh|kW-h|kW·h|MWh|MW-h|"
    r"therms?|ccf|MMBtu|mm-btu|MBtu|"
    r"gallons?|gals?|liters?|litres?|"
    r"tonne[.\-\s]km|ton[.\-]km|tkm"
)

# Pattern 1: <qty> <unit>
# Ensures quantity is not preceded by currency, and unit is not preceded
# by / or per (e.g. $0.15 / kWh)
PAT_QTY_UNIT = re.compile(
    rf"(?<![\$\£\€\¥])(?<![\$\£\€\¥]\s)(?<!USD\s)(?<!EUR\s)(?<!GBP\s)"
    rf"\b(?P<qty>\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*"
    rf"(?<!/)(?<!per\s)(?P<unit>{UNITS_REGEX_STR})\b",
    re.IGNORECASE,
)

# Pattern 2: <unit>[: ]+<qty>
# E.g. "Usage (kWh): 1,450.50", "Total kWh: 1,450.50"
PAT_UNIT_QTY = re.compile(
    rf"(?<![/a-zA-Z\$\£\€\¥])\b(?P<unit>{UNITS_REGEX_STR})\b[\]\)]?\s*[:=\-]?\s*"
    rf"(?<![\$\£\€\¥])(?<![\$\£\€\¥]\s)(?<!USD\s)(?<!EUR\s)(?<!GBP\s)"
    rf"\b(?P<qty>\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?|\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)


def _parse_date(val: str) -> date:
    """Safely parse a date string into a date object."""
    s = val.strip()
    try:
        return dateutil.parser.parse(s, dayfirst=False).date()
    except Exception:
        return dateutil.parser.parse(s, dayfirst=True).date()


def _extract_document_dates(text: str) -> tuple[date, date]:
    """Extract billing period start and end dates from document text.

    Defaults to today if no date found, and defaults period_end to period_start if single date.
    """
    m_period = PERIOD_REGEX.search(text)
    if m_period:
        try:
            s_date = _parse_date(m_period.group("start"))
            e_date = _parse_date(m_period.group("end"))
            return s_date, e_date
        except Exception:
            pass

    m_single = SINGLE_DATE_REGEX.search(text)
    if m_single:
        try:
            s_date = _parse_date(m_single.group("date"))
            return s_date, s_date
        except Exception:
            pass

    m_fallback = PERIOD_FALLBACK_REGEX.search(text)
    if m_fallback:
        try:
            s_date = _parse_date(m_fallback.group("start"))
            e_date = _parse_date(m_fallback.group("end"))
            return s_date, e_date
        except Exception:
            pass

    today = date.today()
    return today, today


def _extract_provider_token(text: str, custom_known: list[str] | None = None) -> str:
    """Identify utility provider from document text and return tokenized supplier ref."""
    known_list = list(custom_known or []) + KNOWN_UTILITIES_SORTED

    for util in sorted(known_list, key=len, reverse=True):
        pattern = rf"(?i)\b{re.escape(util)}\b"
        if re.search(pattern, text):
            return PIIRedactor.tokenize_supplier(util)

    m_hdr = HEADER_SUPPLIER_REGEX.search(text)
    if m_hdr:
        raw_name = m_hdr.group(1).strip()
        if raw_name:
            return PIIRedactor.tokenize_supplier(raw_name)

    return PIIRedactor.tokenize_supplier("")


def _extract_account_token(text: str) -> str | None:
    """Identify labeled or standalone account/meter numbers and return tokenized account."""
    m_label = ACCOUNT_LABEL_REGEX.search(text)
    if m_label:
        raw_acct = m_label.group("account")
        return PIIRedactor.tokenize_account(raw_acct)

    m_standalone = ACCOUNT_STANDALONE_REGEX.search(text)
    if m_standalone:
        raw_acct = m_standalone.group(0)
        return PIIRedactor.tokenize_account(raw_acct)

    return None


def _extract_geography(text: str, default_geography: str = "US") -> str:
    """Extract geography code (US state or region) from address or header."""
    m_reg = re.search(r"(?i)\b(?:State|Region|Province|Geography)[\s:]+([A-Za-z0-9\-]+)\b", text)
    if m_reg:
        val = m_reg.group(1).upper()
        if val in US_STATES or val.startswith("US-") or len(val) <= 16:
            return val

    m_addr = re.search(r",\s*([A-Z]{2})\s+\d{5}\b", text)
    if m_addr and m_addr.group(1) in US_STATES:
        return m_addr.group(1)

    return default_geography


class _ParsePDFDescriptor:
    """Descriptor enabling parse_utility_pdf to work on both class and instance calls."""

    def __get__(
        self,
        instance: "PDFParser | None",
        owner: type["PDFParser"] | None = None,
    ) -> Callable[..., list[ParsedPDFActivityItem]]:
        if instance is None:
            assert owner is not None
            return owner._parse_class
        return instance._parse_instance


class PDFParser:
    """Parser service for extracting and normalizing activity items from utility bill PDFs."""

    def __init__(
        self,
        default_geography: str = "US",
        known_suppliers: list[str] | None = None,
    ) -> None:
        self.default_geography = default_geography
        self.known_suppliers = list(known_suppliers or [])

    @classmethod
    def _parse_class(
        cls,
        content: bytes,
        default_geography: str = "US",
    ) -> list[ParsedPDFActivityItem]:
        return cls._parse_core(content, default_geography=default_geography)

    def _parse_instance(
        self,
        content: bytes,
        default_geography: str | None = None,
    ) -> list[ParsedPDFActivityItem]:
        geo = default_geography if default_geography is not None else self.default_geography
        return self._parse_core(
            content,
            default_geography=geo,
            known_suppliers=self.known_suppliers,
        )

    @classmethod
    def _parse_core(
        cls,
        content: bytes,
        default_geography: str = "US",
        known_suppliers: list[str] | None = None,
    ) -> list[ParsedPDFActivityItem]:
        if not content or not content.strip():
            raise PDFParserError("PDF content cannot be empty.")

        try:
            reader = pypdf.PdfReader(io.BytesIO(content))
        except Exception as e:
            raise PDFParserError(f"Failed to read PDF document: {e}") from e

        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as e:
                raise PDFParserError(f"Failed to decrypt encrypted PDF: {e}") from e

        if not reader.pages:
            return []

        # Extract text per page
        page_lines: list[tuple[int, list[str]]] = []
        all_text_parts: list[str] = []

        for page_num, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            all_text_parts.append(page_text)
            page_lines.append((page_num, page_text.splitlines()))

        full_text = "\n".join(all_text_parts)
        if not full_text.strip():
            return []

        # Document-level metadata extraction
        doc_supplier_token = _extract_provider_token(full_text, known_suppliers)
        doc_account_token = _extract_account_token(full_text)
        doc_period_start, doc_period_end = _extract_document_dates(full_text)
        doc_geography = _extract_geography(full_text, default_geography=default_geography)

        items: list[ParsedPDFActivityItem] = []

        for page_num, lines in page_lines:
            for line_idx, raw_line in enumerate(lines, start=1):
                line = raw_line.strip()
                if not line:
                    continue

                # Check for line-level billing period override
                line_start = doc_period_start
                line_end = doc_period_end
                m_line_period = PERIOD_REGEX.search(line) or PERIOD_FALLBACK_REGEX.search(line)
                if m_line_period:
                    try:
                        line_start = _parse_date(m_line_period.group("start"))
                        line_end = _parse_date(m_line_period.group("end"))
                    except Exception:
                        pass

                # Scan for consumption matches
                matched_spans: list[tuple[int, int]] = []
                line_records: list[tuple[str, str, Decimal]] = []

                # 1. Check quantity then unit
                for m in PAT_QTY_UNIT.finditer(line):
                    u_key = m.group("unit").strip().lower()
                    if u_key in UNIT_MAPPINGS:
                        canon_unit, act_type = UNIT_MAPPINGS[u_key]
                        qty_str = m.group("qty").replace(",", "").strip()
                        qty_dec = Decimal(qty_str)
                        matched_spans.append(m.span())
                        line_records.append((act_type, canon_unit, qty_dec))

                # 2. Check unit then quantity (avoid overlapping spans)
                for m in PAT_UNIT_QTY.finditer(line):
                    m_start, m_end = m.span()
                    overlaps = any(
                        not (m_end <= s_start or m_start >= s_end)
                        for (s_start, s_end) in matched_spans
                    )
                    if overlaps:
                        continue
                    u_key = m.group("unit").strip().lower()
                    if u_key in UNIT_MAPPINGS:
                        canon_unit, act_type = UNIT_MAPPINGS[u_key]
                        qty_str = m.group("qty").replace(",", "").strip()
                        qty_dec = Decimal(qty_str)
                        matched_spans.append(m.span())
                        line_records.append((act_type, canon_unit, qty_dec))

                # Create ParsedPDFActivityItem for each matched record
                for act_type, canon_unit, qty_dec in line_records:
                    item = ParsedPDFActivityItem(
                        activity_type=act_type,
                        quantity=qty_dec,
                        unit=canon_unit,
                        geography=doc_geography,
                        period_start=line_start,
                        period_end=line_end,
                        supplier_ref=doc_supplier_token,
                        raw_line_ref=f"page:{page_num},line:{line_idx}",
                        account_ref=doc_account_token,
                    )
                    items.append(item)

        return items

    parse_utility_pdf = _ParsePDFDescriptor()
