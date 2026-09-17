"""PII Redaction & Supplier Tokenization Service.

Ensures that sensitive raw supplier names, customer identifiers, meter numbers,
and account numbers are deterministically tokenized and never exposed in downstream
models or LLM prompts.
"""

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Regex for detecting labeled account, customer, and meter identifiers in unstructured text.
# Matches forms such as 'Account #: 9842-1104', 'Acct: 12345678', 'Meter No: MTR-5544321', etc.
# Requires at least one digit in the identifier to avoid capturing non-PII words like 'Summary'.
ACCOUNT_LABEL_REGEX = re.compile(
    r"(?i)\b(?P<label>"
    r"(?:Account|Acct|Acc)"
    r"(?:[\s/]*(?:Number|No\.?|Num\.?|ID|Id|Code))?"
    r"|Customer[\s/]*(?:Account|ID|Id|No\.?|Num\.?|Number)"
    r"|Cust[\s/]*(?:Account|ID|Id|No\.?|Num\.?|Number)"
    r"|Meter[\s/]*(?:ID|Id|No\.?|Num\.?|Number|#)?"
    r"|(?:Contract|Billing|Utility)[\s/]*Account(?:[\s/]*(?:Number|No\.?|Num\.?|ID|Id))?"
    r")"
    r"[\s#:.-]+"
    r"(?P<account>(?!TOKEN_)(?=[A-Za-z0-9\-]*\d)[A-Za-z0-9\-]{5,25}\b)"
)

# Regex for detecting standalone prefixed account/customer/meter numbers
# (e.g. ACCT-9842-1104, MTR-5544321).
ACCOUNT_STANDALONE_REGEX = re.compile(
    r"(?i)\b(?<!TOKEN_)(?:ACCT|ACC|CUST|MTR|METER)[-_][A-Za-z0-9\-]{4,24}\b"
)


@dataclass
class RedactedResult:
    """Data container for redacted text and token-to-raw value mappings."""

    redacted_text: str
    token_map: dict[str, str] = field(default_factory=dict)

    def __getitem__(self, item: str) -> Any:
        if item == "redacted_text":
            return self.redacted_text
        if item == "token_map":
            return self.token_map
        raise KeyError(item)


def _build_supplier_pattern(phrase: str) -> re.Pattern[str]:
    """Build a regex pattern matching a supplier name case-insensitively with word boundaries."""
    words = [re.escape(w) for w in phrase.strip().split()]
    inner = r"\s+".join(words)
    left = r"\b" if re.match(r"^\w", phrase.strip()) else r""
    right = r"\b" if re.search(r"\w$", phrase.strip()) else r""
    return re.compile(f"{left}{inner}{right}", re.IGNORECASE)


class _RedactTextDescriptor:
    """Descriptor enabling PIIRedactor.redact_text to work both as a class and instance method."""

    def __get__(
        self,
        instance: "PIIRedactor | None",
        owner: type["PIIRedactor"] | None = None,
    ) -> Callable[..., RedactedResult]:
        if instance is None:
            assert owner is not None
            return owner._redact_core
        return instance._redact_instance


class PIIRedactor:
    """Deterministic PII redaction and supplier/account tokenization service."""

    def __init__(self, known_suppliers: list[str] | None = None) -> None:
        self.known_suppliers: list[str] = list(known_suppliers or [])

    @staticmethod
    def tokenize_supplier(name: str) -> str:
        """Normalize and tokenize a raw supplier name.

        - Normalizes raw supplier name (strips whitespace, case-folds).
        - Returns TOKEN_SUPP_<sha256[:10].upper()>.
        - If string already starts with TOKEN_SUPP_, returns as-is.
        - If empty/whitespace, returns 'TOKEN_SUPP_UNKNOWN'.
        """
        if not name or not isinstance(name, str):
            return "TOKEN_SUPP_UNKNOWN"
        stripped = name.strip()
        if not stripped:
            return "TOKEN_SUPP_UNKNOWN"
        if stripped.startswith("TOKEN_SUPP_"):
            return stripped
        normalized = " ".join(stripped.split()).casefold()
        if not normalized:
            return "TOKEN_SUPP_UNKNOWN"
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10].upper()
        return f"TOKEN_SUPP_{digest}"

    @staticmethod
    def tokenize_account(acct: str) -> str:
        """Normalize and tokenize an account number.

        - Normalizes account number (strips spaces, dashes, converts to uppercase).
        - Returns TOKEN_ACCT_<sha256[:10].upper()>.
        - If string already starts with TOKEN_ACCT_, returns as-is.
        - If empty/non-alphanumeric, returns 'TOKEN_ACCT_UNKNOWN'.
        """
        if not acct or not isinstance(acct, str):
            return "TOKEN_ACCT_UNKNOWN"
        stripped = acct.strip()
        if not stripped:
            return "TOKEN_ACCT_UNKNOWN"
        if stripped.startswith("TOKEN_ACCT_"):
            return stripped
        normalized = re.sub(r"[\s\-]+", "", stripped).upper()
        if not normalized:
            return "TOKEN_ACCT_UNKNOWN"
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10].upper()
        return f"TOKEN_ACCT_{digest}"

    @classmethod
    def _redact_core(
        cls,
        text: str,
        known_suppliers: list[str] | None = None,
    ) -> RedactedResult:
        if not text:
            return RedactedResult(redacted_text="", token_map={})

        redacted = text
        token_map: dict[str, str] = {}

        # 1. Redact known suppliers (ordered longest to shortest to prevent partial matching)
        suppliers_to_process = [
            s.strip()
            for s in (known_suppliers or [])
            if s and s.strip() and not s.strip().startswith("TOKEN_SUPP_")
        ]
        suppliers_to_process.sort(key=len, reverse=True)

        for supp in suppliers_to_process:
            supp_token = cls.tokenize_supplier(supp)
            pattern = _build_supplier_pattern(supp)

            def _replace_supp(match: re.Match[str]) -> str:
                if supp_token not in token_map:
                    token_map[supp_token] = supp
                return supp_token

            if pattern.search(redacted):
                redacted = pattern.sub(_replace_supp, redacted)

        # 2. Redact standalone prefixed account/meter numbers first
        # (e.g. ACCT-9842-1104, MTR-5544321) so the prefix is not mistargeted as a label
        def _replace_standalone_account(match: re.Match[str]) -> str:
            raw_acct = match.group(0)
            acct_token = cls.tokenize_account(raw_acct)
            token_map[acct_token] = raw_acct
            return acct_token

        redacted = ACCOUNT_STANDALONE_REGEX.sub(_replace_standalone_account, redacted)

        # 3. Redact labeled account/meter numbers
        # (e.g. Account #: 9842-1104, Billing Account: 123456789)
        def _replace_labeled_account(match: re.Match[str]) -> str:
            label = match.group("label")
            raw_acct = match.group("account")
            acct_token = cls.tokenize_account(raw_acct)
            token_map[acct_token] = raw_acct
            delim = match.group(0)[len(label) : -len(raw_acct)]
            return f"{label}{delim}{acct_token}"

        redacted = ACCOUNT_LABEL_REGEX.sub(_replace_labeled_account, redacted)

        # 4. Guarantee pass: ensure none of the identified raw identifiers remain
        for supp in suppliers_to_process:
            pattern = _build_supplier_pattern(supp)
            if pattern.search(redacted):
                supp_token = cls.tokenize_supplier(supp)
                redacted = pattern.sub(supp_token, redacted)
                if supp_token not in token_map:
                    token_map[supp_token] = supp

        for raw_val in list(token_map.values()):
            if raw_val in redacted:
                tok = (
                    cls.tokenize_supplier(raw_val)
                    if raw_val in suppliers_to_process
                    else cls.tokenize_account(raw_val)
                )
                redacted = redacted.replace(raw_val, tok)

        return RedactedResult(redacted_text=redacted, token_map=token_map)

    def _redact_instance(
        self,
        text: str,
        known_suppliers: list[str] | None = None,
    ) -> RedactedResult:
        effective_suppliers = (
            known_suppliers if known_suppliers is not None else self.known_suppliers
        )
        return self._redact_core(text, effective_suppliers)

    redact_text = _RedactTextDescriptor()
