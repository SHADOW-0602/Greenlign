"""Tabular Parser for CSV and XLSX ERP Exports.

Provides normalized ingestion of arbitrary CSV and XLSX ERP / utility / travel exports
into standardized ParsedActivityRow structures ready for ActivityData persistence.
Includes configurable column mapping, heuristic synonym auto-detection,
localized Decimal conversion, multi-format date parsing, and supplier PII tokenization.
"""

import csv
import io
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import dateutil.parser  # type: ignore[import-untyped]
import openpyxl

from app.services.pii_redaction import PIIRedactor

TARGET_FIELDS: set[str] = {
    "activity_type",
    "quantity",
    "unit",
    "geography",
    "period_start",
    "period_end",
    "supplier_ref",
    "raw_line_ref",
}

REQUIRED_TARGET_FIELDS: set[str] = {
    "activity_type",
    "quantity",
    "unit",
    "period_start",
}

SYNONYMS: dict[str, list[str]] = {
    "period_start": [
        "period_start",
        "period start",
        "period_from",
        "period from",
        "start_date",
        "start date",
        "start_period",
        "start period",
        "start",
        "from_date",
        "from date",
        "from",
        "service_start",
        "service start",
        "service_start_date",
        "service start date",
        "billing_start",
        "billing start",
        "billing_start_date",
        "billing start date",
        "invoice_date",
        "invoice date",
        "transaction_date",
        "transaction date",
        "reading_date",
        "reading date",
        "activity_date",
        "activity date",
        "date",
    ],
    "period_end": [
        "period_end",
        "period end",
        "period_to",
        "period to",
        "end_date",
        "end date",
        "end_period",
        "end period",
        "end",
        "to_date",
        "to date",
        "to",
        "service_end",
        "service end",
        "service_end_date",
        "service end date",
        "billing_end",
        "billing end",
        "billing_end_date",
        "billing end date",
    ],
    "activity_type": [
        "activity_type",
        "activity type",
        "activity",
        "fuel_type",
        "fuel type",
        "fuel",
        "energy_type",
        "energy type",
        "energy_source",
        "energy source",
        "emission_source",
        "emission source",
        "source_type",
        "source type",
        "expense_category",
        "expense category",
        "expense_type",
        "expense type",
        "item_description",
        "item description",
        "item_type",
        "item type",
        "category",
        "type",
        "item",
        "commodity",
        "scope_category",
    ],
    "quantity": [
        "quantity",
        "qty",
        "usage",
        "usage_amount",
        "usage amount",
        "usage_qty",
        "usage qty",
        "consumption",
        "consumption_amount",
        "consumption amount",
        "volume",
        "amount",
        "meter_reading",
        "meter reading",
        "reading",
        "total_quantity",
        "total quantity",
        "total_qty",
        "total qty",
        "value",
    ],
    "unit": [
        "unit",
        "units",
        "uom",
        "unit_of_measure",
        "unit of measure",
        "unit_of_measurement",
        "unit of measurement",
        "unit_code",
        "unit code",
        "measure",
        "measurement",
        "metric",
    ],
    "geography": [
        "geography",
        "geo",
        "country",
        "country_code",
        "country code",
        "region",
        "state",
        "province",
        "location",
        "facility_location",
        "facility location",
        "site_location",
        "site location",
        "facility",
        "site",
        "grid_region",
        "grid region",
    ],
    "supplier_ref": [
        "supplier_ref",
        "supplier ref",
        "supplier",
        "supplier_name",
        "supplier name",
        "vendor",
        "vendor_name",
        "vendor name",
        "provider",
        "utility_provider",
        "utility provider",
        "utility",
        "merchant",
        "biller",
        "contractor",
    ],
    "raw_line_ref": [
        "raw_line_ref",
        "raw line ref",
        "line_id",
        "line id",
        "line_ref",
        "line ref",
        "line_number",
        "line number",
        "line_no",
        "line no",
        "line",
        "line_item",
        "line item",
        "row_id",
        "row id",
        "row_number",
        "row number",
        "transaction_id",
        "transaction id",
        "trans_id",
        "txn_id",
        "txnid",
        "invoice_id",
        "invoice id",
        "invoice_number",
        "invoice number",
        "invoice_no",
        "reference",
        "ref",
    ],
}


class TabularParserError(ValueError):
    """Raised when tabular data cannot be parsed, columns are missing, or records are invalid."""


@dataclass
class ParsedActivityRow:
    """Normalized activity record structure ready for insertion into ActivityData."""

    activity_type: str
    quantity: Decimal
    unit: str
    geography: str
    period_start: date
    period_end: date
    supplier_ref: str
    raw_line_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.quantity, Decimal):
            self.quantity = Decimal(str(self.quantity))
        if not self.supplier_ref.startswith("TOKEN_SUPP_"):
            self.supplier_ref = PIIRedactor.tokenize_supplier(self.supplier_ref)
        if not self.geography:
            self.geography = "US"
        if self.period_end is None:
            self.period_end = self.period_start


def _normalize_header(header: Any) -> str:
    """Normalize header string for heuristic and case-insensitive comparison."""
    if header is None:
        return ""
    cleaned = str(header).strip().lower()
    return re.sub(r"[\s\-_]+", " ", cleaned)


def _parse_decimal(val: Any) -> Decimal:
    """Safely convert localized strings, ints, or floats to Decimal (never float)."""
    if val is None:
        raise ValueError("Quantity cannot be None")
    if isinstance(val, Decimal):
        return val
    if isinstance(val, int):
        return Decimal(val)
    if isinstance(val, float):
        return Decimal(str(val))

    s = str(val).strip()
    if not s:
        raise ValueError("Quantity cannot be empty")

    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        is_negative = True
        s = s[1:].strip()
    elif s.startswith("+"):
        s = s[1:].strip()

    # Strip currency symbols and ISO currency prefixes
    s = re.sub(r"[\$€£¥₹]", "", s)
    s = re.sub(r"\b(USD|EUR|GBP|CAD|AUD|JPY|INR)\b", "", s, flags=re.IGNORECASE)
    # Strip thousands separator commas
    s = s.replace(",", "").strip()

    if is_negative:
        s = f"-{s}"

    try:
        dec = Decimal(s)
    except Exception as e:
        raise ValueError(f"Cannot convert '{val}' to Decimal: {e}") from e

    if not dec.is_finite():
        raise ValueError(f"Quantity must be a finite number, got '{val}'")
    return dec


def _parse_date(val: Any) -> date:
    """Robustly parse date from date, datetime, Excel serial, or date string."""
    if val is None:
        raise ValueError("Date cannot be None")
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    # Excel unformatted serial number (days since 1899-12-30)
    if isinstance(val, int | float):
        if 10000 <= val <= 100000:
            return date(1899, 12, 30) + timedelta(days=int(val))
        raise ValueError(f"Unrecognized numeric date value: {val}")

    s = str(val).strip()
    if not s:
        raise ValueError("Date string cannot be empty")

    if s.isdigit() and 10000 <= int(s) <= 100000:
        return date(1899, 12, 30) + timedelta(days=int(s))

    try:
        # Standard parse with dayfirst=False (US / ISO standard)
        dt = dateutil.parser.parse(s, dayfirst=False)
        return dt.date()
    except Exception:
        pass

    try:
        # Fallback with dayfirst=True for EU dates (e.g. DD/MM/YYYY)
        dt = dateutil.parser.parse(s, dayfirst=True)
        return dt.date()
    except Exception as e:
        raise ValueError(f"Cannot parse date '{val}': {e}") from e


def _resolve_column_mapping(
    source_headers: list[str],
    mapping: dict[str, str] | None = None,
) -> dict[str, str]:
    """Resolve target fields to source header names using mapping and synonyms."""
    clean_headers = [h.strip() for h in source_headers if h and str(h).strip()]
    norm_to_actual: dict[str, str] = {_normalize_header(h): h for h in clean_headers}
    actual_set: set[str] = set(clean_headers)

    resolved: dict[str, str] = {}
    assigned_sources: set[str] = set()

    # 1. Apply explicit mappings
    if mapping:
        for k, v in mapping.items():
            k_str = str(k).strip()
            v_str = str(v).strip()

            target_field: str
            source_candidate: str
            if k_str in TARGET_FIELDS:
                target_field = k_str
                source_candidate = v_str
            elif v_str in TARGET_FIELDS:
                target_field = v_str
                source_candidate = k_str
            else:
                target_field = k_str
                source_candidate = v_str

            # Find matching actual source header
            matched_header: str | None = None
            if source_candidate in actual_set:
                matched_header = source_candidate
            else:
                norm_candidate = _normalize_header(source_candidate)
                if norm_candidate in norm_to_actual:
                    matched_header = norm_to_actual[norm_candidate]

            if matched_header is None:
                raise TabularParserError(
                    f"Mapped column '{source_candidate}' for field '{target_field}' "
                    f"not found in source headers: {clean_headers}"
                )

            resolved[target_field] = matched_header
            assigned_sources.add(matched_header)

    # 2. Heuristic synonym auto-detection for unmapped target fields
    fields_to_detect = [f for f in TARGET_FIELDS if f not in resolved]
    for target_field in fields_to_detect:
        synonym_list = SYNONYMS.get(target_field, [])
        for syn in synonym_list:
            norm_syn = _normalize_header(syn)
            if norm_syn in norm_to_actual:
                actual_header = norm_to_actual[norm_syn]
                if actual_header not in assigned_sources:
                    resolved[target_field] = actual_header
                    assigned_sources.add(actual_header)
                    break

    # 3. Validate required fields
    missing_required = [f for f in sorted(REQUIRED_TARGET_FIELDS) if f not in resolved]
    if missing_required:
        raise TabularParserError(
            f"Missing required column(s): {', '.join(missing_required)}. "
            f"Available headers: {clean_headers}"
        )

    return resolved


class _ParseDescriptor:
    """Descriptor enabling TabularParser methods to work both as class and instance methods."""

    def __init__(self, method_name: str) -> None:
        self.method_name = method_name

    def __get__(
        self,
        instance: "TabularParser | None",
        owner: type["TabularParser"] | None = None,
    ) -> Callable[..., list[ParsedActivityRow]]:
        target_cls = owner if owner is not None else type(instance)
        core_func: Callable[..., list[ParsedActivityRow]] = getattr(
            target_cls, f"_{self.method_name}_core"
        )
        if instance is None:
            assert target_cls is not None

            def _class_call(
                content: bytes,
                mapping: dict[str, str] | None = None,
                default_geography: str = "US",
            ) -> list[ParsedActivityRow]:
                return core_func(content, mapping, default_geography)

            return _class_call

        assert instance is not None
        bound_instance = instance

        def _instance_call(
            content: bytes,
            mapping: dict[str, str] | None = None,
            default_geography: str | None = None,
        ) -> list[ParsedActivityRow]:
            eff_mapping = mapping if mapping is not None else bound_instance.mapping
            eff_geo = (
                default_geography
                if default_geography is not None
                else bound_instance.default_geography
            )
            return core_func(content, eff_mapping, eff_geo)

        return _instance_call


class TabularParser:
    """Parser for arbitrary tabular ERP exports in CSV and XLSX format."""

    def __init__(
        self,
        mapping: dict[str, str] | None = None,
        default_geography: str = "US",
    ) -> None:
        self.mapping = mapping
        self.default_geography = default_geography

    @classmethod
    def _parse_csv_core(
        cls,
        content: bytes,
        mapping: dict[str, str] | None = None,
        default_geography: str = "US",
    ) -> list[ParsedActivityRow]:
        if not content or not content.strip():
            raise TabularParserError("The tabular document is empty or contains no valid rows.")

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except UnicodeDecodeError as e:
                raise TabularParserError(f"Failed to decode CSV content: {e}") from e

        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            raise TabularParserError("The tabular document is empty or contains no valid rows.")

        sample = "\n".join(lines[:10])
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ","

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        raw_rows = [r for r in reader if any(cell.strip() for cell in r)]
        if not raw_rows:
            raise TabularParserError("The tabular document is empty or contains no valid rows.")

        headers = [h.strip() for h in raw_rows[0]]
        resolved = _resolve_column_mapping(headers, mapping)

        data_rows = raw_rows[1:]
        if not data_rows:
            raise TabularParserError("No data rows found in tabular document.")

        parsed: list[ParsedActivityRow] = []
        for row_idx, row in enumerate(data_rows, start=1):
            row_dict = {
                headers[i]: row[i].strip() if i < len(row) else ""
                for i in range(len(headers))
            }
            parsed_row = cls._build_parsed_row(row_dict, resolved, row_idx, default_geography)
            parsed.append(parsed_row)

        if not parsed:
            raise TabularParserError("No data rows found in tabular document.")

        return parsed

    @classmethod
    def _parse_xlsx_core(
        cls,
        content: bytes,
        mapping: dict[str, str] | None = None,
        default_geography: str = "US",
    ) -> list[ParsedActivityRow]:
        if not content:
            raise TabularParserError("The tabular document is empty or contains no valid rows.")

        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
        except Exception as e:
            raise TabularParserError(f"Failed to read XLSX file: {e}") from e

        sheet = wb.active
        if sheet is None and wb.worksheets:
            sheet = wb.worksheets[0]
        if sheet is None:
            raise TabularParserError("No worksheet found in XLSX workbook.")

        raw_rows: list[list[Any]] = []
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None and str(cell).strip() != "" for cell in row):
                raw_rows.append(list(row))

        if not raw_rows:
            raise TabularParserError("The tabular document is empty or contains no valid rows.")

        headers = [str(h).strip() if h is not None else "" for h in raw_rows[0]]
        resolved = _resolve_column_mapping(headers, mapping)

        data_rows = raw_rows[1:]
        if not data_rows:
            raise TabularParserError("No data rows found in tabular document.")

        parsed: list[ParsedActivityRow] = []
        for row_idx, row in enumerate(data_rows, start=1):
            row_dict = {
                headers[i]: row[i] if i < len(row) else None
                for i in range(len(headers))
                if headers[i]
            }
            parsed_row = cls._build_parsed_row(row_dict, resolved, row_idx, default_geography)
            parsed.append(parsed_row)

        if not parsed:
            raise TabularParserError("No data rows found in tabular document.")

        return parsed

    @classmethod
    def _build_parsed_row(
        cls,
        row_dict: dict[str, Any],
        resolved: dict[str, str],
        row_idx: int,
        default_geography: str,
    ) -> ParsedActivityRow:
        """Construct a validated ParsedActivityRow from mapped row data."""
        # 1. activity_type (required)
        raw_act = row_dict.get(resolved["activity_type"])
        if raw_act is None or not str(raw_act).strip():
            raise TabularParserError(f"Row {row_idx}: activity_type cannot be empty")
        activity_type = str(raw_act).strip()

        # 2. quantity (required)
        raw_qty = row_dict.get(resolved["quantity"])
        if raw_qty is None or (isinstance(raw_qty, str) and not raw_qty.strip()):
            raise TabularParserError(f"Row {row_idx}: quantity cannot be empty")
        try:
            quantity = _parse_decimal(raw_qty)
        except Exception as e:
            raise TabularParserError(f"Row {row_idx}: invalid quantity value: {e}") from e

        # 3. unit (required)
        raw_unit = row_dict.get(resolved["unit"])
        if raw_unit is None or not str(raw_unit).strip():
            raise TabularParserError(f"Row {row_idx}: unit cannot be empty")
        unit = str(raw_unit).strip()

        # 4. period_start (required)
        raw_start = row_dict.get(resolved["period_start"])
        if raw_start is None or (isinstance(raw_start, str) and not raw_start.strip()):
            raise TabularParserError(f"Row {row_idx}: period_start date cannot be empty")
        try:
            period_start = _parse_date(raw_start)
        except Exception as e:
            raise TabularParserError(f"Row {row_idx}: invalid date value: {e}") from e

        # 5. period_end (optional, defaults to period_start)
        period_end = period_start
        if "period_end" in resolved:
            raw_end = row_dict.get(resolved["period_end"])
            if raw_end is not None and (not isinstance(raw_end, str) or raw_end.strip()):
                try:
                    period_end = _parse_date(raw_end)
                except Exception as e:
                    raise TabularParserError(f"Row {row_idx}: invalid period_end date: {e}") from e

        # 6. geography (optional, defaults to default_geography)
        geography = default_geography
        if "geography" in resolved:
            raw_geo = row_dict.get(resolved["geography"])
            if raw_geo is not None and str(raw_geo).strip():
                geography = str(raw_geo).strip()

        # 7. supplier_ref (optional, tokenized via PIIRedactor)
        raw_supp = ""
        if "supplier_ref" in resolved:
            raw_supp_val = row_dict.get(resolved["supplier_ref"])
            if raw_supp_val is not None:
                raw_supp = str(raw_supp_val)
        supplier_ref = PIIRedactor.tokenize_supplier(raw_supp)

        # 8. raw_line_ref (optional, defaults to row:{row_idx})
        raw_line_ref = f"row:{row_idx}"
        if "raw_line_ref" in resolved:
            raw_ref_val = row_dict.get(resolved["raw_line_ref"])
            if raw_ref_val is not None and str(raw_ref_val).strip():
                raw_line_ref = str(raw_ref_val).strip()

        return ParsedActivityRow(
            activity_type=activity_type,
            quantity=quantity,
            unit=unit,
            geography=geography,
            period_start=period_start,
            period_end=period_end,
            supplier_ref=supplier_ref,
            raw_line_ref=raw_line_ref,
        )

    parse_csv = _ParseDescriptor("parse_csv")
    parse_xlsx = _ParseDescriptor("parse_xlsx")
