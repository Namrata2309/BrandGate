"""Regression tests for retrieval, local checks, and evidence validation.

These tests deliberately avoid hosted model calls and model downloads.
Run from backend/: python -m pytest tests/test_regression_quality.py -q
"""
from datetime import date
from pathlib import Path
import json

import pytest

from app.services import retrieval
from app.services.local_checks import check_fact_mismatches, check_terminology

TODAY = date(2026, 10, 28)
RULES = [
    {
        "rule_code": "BG-002",
        "category": "terminology",
        "title": "Use approved product name",
        "rule_text": "Refer to the main product as Northstar Workspace. Do not use Dashboard as a substitute product name.",
        "source": "Northstar Terminology Guide",
        "source_section": "Section 1 - Product naming",
        "severity": "warning",
        "status": "active",
        "effective_date": date(2026, 10, 1),
    },
    {
        "rule_code": "BG-003",
        "category": "promotional_claim",
        "title": "Avoid unsupported guaranteed outcomes",
        "rule_text": "Do not promise guaranteed sales, revenue, productivity or business outcomes unless the exact claim has current approved evidence.",
        "source": "Northstar Claims Policy",
        "source_section": "Section 4 - Promotional claims",
        "severity": "high",
        "status": "active",
        "effective_date": date(2026, 10, 1),
    },
]
FACTS = [
    {
        "fact_code": "FACT-001",
        "name": "Monthly subscription price",
        "value": "999",
        "unit": "INR/month",
        "source": "Northstar Approved Product Facts",
        "source_section": "Pricing",
        "valid_from": date(2026, 10, 1),
        "valid_until": None,
        "status": "active",
    }
]
TERMS = [
    {
        "term": "Dashboard",
        "replacement": "Northstar Workspace",
        "rule_code": "BG-002",
        "reason": "Use the approved product name.",
        "whole_word": True,
        "case_sensitive": False,
    }
]


def test_inactive_rule_is_not_retrieved():
    rules = [RULES[0], dict(RULES[1], status="inactive")]
    result = retrieval.search_sources(
        "guaranteed sales outcomes", rules, facts=FACTS,
        top_k=5, include_facts=True, use_semantic=False, today=TODAY,
    )
    ids = {item["source_id"] for item in result["results"]}
    assert "BG-003" not in ids
    assert "BG-002" in ids


def test_expired_fact_is_not_retrieved():
    expired_fact = dict(FACTS[0], valid_until=date(2026, 10, 1))
    result = retrieval.search_sources(
        "monthly subscription price 999 INR", RULES, facts=[expired_fact],
        top_k=5, include_facts=True, use_semantic=False, today=TODAY,
    )
    assert "FACT-001" not in {item["source_id"] for item in result["results"]}


def test_semantic_failure_is_reported_as_keyword_fallback(monkeypatch):
    def fail_semantic(*args, **kwargs):
        raise RuntimeError("simulated model unavailable")

    monkeypatch.setattr(retrieval, "_semantic_scores", fail_semantic)
    result = retrieval.search_sources(
        "official product name Dashboard", RULES, facts=FACTS,
        top_k=5, include_facts=True, use_semantic=True, today=TODAY,
    )
    assert result["retrieval_mode"] == "keyword_fallback"
    assert result["warnings"]
    assert "BG-002" in {item["source_id"] for item in result["results"]}


def test_retrieval_keeps_source_provenance():
    result = retrieval.search_sources(
        "guaranteed sales outcomes", RULES, facts=FACTS,
        top_k=5, include_facts=True, use_semantic=False, today=TODAY,
    )
    source = next(item for item in result["results"] if item["source_id"] == "BG-003")
    assert source["source_type"] == "rule"
    assert source["source"] == "Northstar Claims Policy"
    assert source["source_section"] == "Section 4 - Promotional claims"


def test_local_checks_return_expected_source_ids():
    term_findings, term_warnings = check_terminology(
        "Try our Dashboard today.", RULES, TERMS, today=TODAY
    )
    fact_findings = check_fact_mismatches(
        "Get access for only ₹799 per month.", FACTS, today=TODAY
    )
    assert not term_warnings
    assert {f["source_id"] for f in term_findings} == {"BG-002"}
    assert {f["source_id"] for f in fact_findings} == {"FACT-001"}


def test_clean_copy_does_not_trigger_term_or_price_checks():
    term_findings, term_warnings = check_terminology(
        "Northstar Workspace helps teams organise projects.", RULES, TERMS, today=TODAY
    )
    fact_findings = check_fact_mismatches(
        "Get access for ₹999 per month.", FACTS, today=TODAY
    )
    assert not term_warnings
    assert term_findings == []
    assert fact_findings == []


def test_labelled_dataset_has_required_fields_and_unique_ids():
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "demo" / "labelled_test_cases.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    assert len(cases) >= 4
    ids = [case["case_id"] for case in cases]
    assert len(ids) == len(set(ids))
    for case in cases:
        assert case["content"].strip()
        assert case["retrieval_query"].strip()
        assert "expected_local_source_ids" in case
        assert "expected_retrieved_source_ids" in case
