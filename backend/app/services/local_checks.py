"""Deterministic, API-credit-free checks for BrandGate Phase 2.

Prohibited terminology is configured explicitly. We do not try to infer every
prohibited term from free-form policy prose because that is error-prone.
"""
from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TERMINOLOGY_PATH = PROJECT_ROOT / "demo" / "terminology_terms.json"

_PRICE_PATTERNS = (
    re.compile(r"(?:₹\s*|\bINR\s*|\bRs\.?\s*)(\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE),
    re.compile(r"(\d[\d,]*(?:\.\d{1,2})?)\s*(?:\bINR\b|\brupees?\b|\bRs\.?|₹)", re.IGNORECASE),
    re.compile(r"(\d[\d,]*(?:\.\d{1,2})?)\s*(?:per\s+month|/\s*month|monthly)\b", re.IGNORECASE),
)
_NUMBER_PATTERN = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])")
_WORD_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOP_WORDS = {
    "a", "an", "and", "or", "the", "of", "to", "for", "in", "on", "at",
    "by", "is", "are", "was", "were", "be", "with", "from", "your", "our",
    "their", "this", "that", "it", "as", "per", "approved", "current", "official",
}


def _get(record: Any, key: str, default: Any = None) -> Any:
    return record.get(key, default) if isinstance(record, dict) else getattr(record, key, default)


def load_terminology_config(path: str | Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """Load explicit terminology rules from demo/terminology_terms.json."""
    config_path = Path(path) if path else DEFAULT_TERMINOLOGY_PATH
    if not config_path.exists():
        return [], [f"Terminology config not found: {config_path.name}. No configured terms were checked."]
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"Terminology config could not be read ({type(exc).__name__})."]

    terms = payload.get("terms", []) if isinstance(payload, dict) else []
    if not isinstance(terms, list):
        return [], ["Terminology config must contain a list named 'terms'."]

    valid_terms: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, item in enumerate(terms):
        required = ("term", "replacement", "rule_code", "reason")
        if not isinstance(item, dict) or any(not str(item.get(field, "")).strip() for field in required):
            warnings.append(f"Terminology entry {index + 1} is missing a required field and was skipped.")
            continue
        valid_terms.append({
            "term": str(item["term"]).strip(),
            "replacement": str(item["replacement"]).strip(),
            "rule_code": str(item["rule_code"]).strip(),
            "reason": str(item["reason"]).strip(),
            "whole_word": bool(item.get("whole_word", True)),
            "case_sensitive": bool(item.get("case_sensitive", False)),
        })
    return valid_terms, warnings


def _rule_is_current(rule: Any, today: date) -> bool:
    if _get(rule, "status", "active") != "active":
        return False
    effective = _get(rule, "effective_date")
    return effective is None or effective <= today


def _fact_is_current(fact: Any, today: date) -> bool:
    if _get(fact, "status", "active") != "active":
        return False
    valid_from = _get(fact, "valid_from")
    valid_until = _get(fact, "valid_until")
    return (valid_from is None or valid_from <= today) and (valid_until is None or valid_until >= today)


def check_terminology(
    content: str,
    rules: Iterable[Any],
    terms: list[dict[str, Any]] | None = None,
    today: date | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return terminology findings and configuration/source warnings."""
    today = today or date.today()
    rules_by_code = {
        str(_get(rule, "rule_code", "")): rule
        for rule in rules
        if _rule_is_current(rule, today)
    }
    findings: list[dict[str, Any]] = []
    warnings: list[str] = []

    for config in terms or []:
        rule_code = config["rule_code"]
        rule = rules_by_code.get(rule_code)
        if rule is None:
            warnings.append(
                f"Configured term '{config['term']}' references missing, inactive, or not-yet-effective rule {rule_code}; skipped."
            )
            continue
        escaped = re.escape(config["term"])
        pattern = rf"(?<!\w){escaped}(?!\w)" if config.get("whole_word", True) else escaped
        flags = 0 if config.get("case_sensitive", False) else re.IGNORECASE
        matches = list(re.finditer(pattern, content, flags))
        if not matches:
            continue

        first = matches[0]
        excerpt = content[max(0, first.start() - 55):min(len(content), first.end() + 55)].replace("\n", " ").strip()
        findings.append({
            "check_type": "terminology",
            "category": str(_get(rule, "category", "terminology")),
            "severity": str(_get(rule, "severity", "warning")),
            "excerpt": excerpt,
            "message": config["reason"],
            "source_type": "rule",
            "source_id": rule_code,
            "source": _get(rule, "source"),
            "source_section": _get(rule, "source_section"),
            "replacement": config["replacement"],
            "verification_status": "rule_match",
            "metadata": {
                "matched_term": config["term"],
                "occurrences": len(matches),
                "positions": [{"start": match.start(), "end": match.end()} for match in matches],
            },
        })
    return findings, warnings


def _normalise_decimal(value: str | int | float | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _is_price_fact(fact: Any) -> bool:
    name_and_unit = f"{_get(fact, 'name', '')} {_get(fact, 'unit', '')}".casefold()
    return any(word in name_and_unit for word in ("price", "subscription", "monthly fee", "cost", "inr/month", "per month"))


def _extract_price_mentions(content: str) -> list[tuple[Decimal, str]]:
    """Extract explicit price-like mentions, avoiding repeated identical values."""
    mentions: list[tuple[Decimal, str]] = []
    seen: set[tuple[Decimal, str]] = set()
    for pattern in _PRICE_PATTERNS:
        for match in pattern.finditer(content):
            amount = _normalise_decimal(match.group(1))
            if amount is None:
                continue
            raw = match.group(0).strip()
            key = (amount, raw.casefold())
            if key not in seen:
                seen.add(key)
                mentions.append((amount, raw))
    return mentions


def _sentence_chunks(content: str) -> list[str]:
    return [chunk.strip() for chunk in re.split(r"(?<=[.!?;\n])\s*", content) if chunk.strip()]


def check_fact_mismatches(content: str, facts: Iterable[Any], today: date | None = None) -> list[dict[str, Any]]:
    """Check explicit price mentions and narrowly scoped named numeric facts.

    This checker does not declare arbitrary claims false. It only flags a number
    that conflicts with a current approved record when the relevant context is
    recognizable. Unsupported non-numeric promotional claims need contextual review.
    """
    today = today or date.today()
    findings: list[dict[str, Any]] = []
    sentences = _sentence_chunks(content)

    for fact in facts:
        if not _fact_is_current(fact, today):
            continue
        fact_code = str(_get(fact, "fact_code", ""))
        name = str(_get(fact, "name", ""))
        expected_raw = str(_get(fact, "value", ""))
        expected_number = _normalise_decimal(expected_raw)
        mismatch_values: list[str] = []
        excerpts: list[str] = []

        if _is_price_fact(fact) and expected_number is not None:
            for amount, raw in _extract_price_mentions(content):
                if amount != expected_number:
                    mismatch_values.append(str(amount))
                    excerpts.append(raw)
        elif expected_number is not None:
            name_tokens = {
                token for token in _WORD_PATTERN.findall(name.casefold())
                if token not in _STOP_WORDS and len(token) > 2
            }
            for sentence in sentences:
                sentence_tokens = set(_WORD_PATTERN.findall(sentence.casefold()))
                if not name_tokens or not (name_tokens & sentence_tokens):
                    continue
                numbers = [_normalise_decimal(match.group(0)) for match in _NUMBER_PATTERN.finditer(sentence)]
                numbers = [number for number in numbers if number is not None]
                if numbers and expected_number not in numbers:
                    mismatch_values.extend(str(number) for number in numbers)
                    excerpts.append(sentence[:240])

        if not mismatch_values:
            continue
        deduped_values = list(dict.fromkeys(mismatch_values))
        expected_display = f"{expected_raw} {_get(fact, 'unit', '') or ''}".strip()
        findings.append({
            "check_type": "fact_mismatch",
            "category": "factual_accuracy",
            "severity": "high" if _is_price_fact(fact) else "warning",
            "excerpt": excerpts[0] if excerpts else name,
            "message": (
                f"The content mentions {', '.join(deduped_values)}, but the approved record lists "
                f"{expected_display}. Verify the content against the approved source."
            ),
            "source_type": "fact",
            "source_id": fact_code,
            "source": _get(fact, "source"),
            "source_section": _get(fact, "source_section"),
            "replacement": expected_display,
            "verification_status": "mismatch_with_approved_fact",
            "metadata": {
                "fact_name": name,
                "approved_value": expected_raw,
                "approved_unit": _get(fact, "unit"),
                "mentioned_values": deduped_values,
                "valid_from": str(_get(fact, "valid_from")) if _get(fact, "valid_from") else None,
                "valid_until": str(_get(fact, "valid_until")) if _get(fact, "valid_until") else None,
            },
        })
    return findings
