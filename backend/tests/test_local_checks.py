from datetime import date

from app.services.local_checks import check_fact_mismatches, check_terminology

TODAY = date(2026, 10, 27)
RULES = [
    {
        "rule_code": "BG-002",
        "category": "terminology",
        "title": "Use approved product name",
        "rule_text": "Do not use Dashboard as a substitute product name.",
        "source": "Northstar Terminology Guide",
        "source_section": "Section 1 - Product naming",
        "severity": "warning",
        "status": "active",
        "effective_date": date(2026, 10, 1),
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


def test_terminology_check_finds_term_and_source_reference():
    findings, warnings = check_terminology(
        "Try our DASHBOARD today.", RULES, TERMS, today=TODAY
    )
    assert not warnings
    assert len(findings) == 1
    assert findings[0]["source_id"] == "BG-002"
    assert findings[0]["source"] == "Northstar Terminology Guide"
    assert findings[0]["replacement"] == "Northstar Workspace"
    assert findings[0]["metadata"]["occurrences"] == 1


def test_terminology_check_respects_word_boundaries():
    findings, _ = check_terminology(
        "Our dashboarding tips are useful.", RULES, TERMS, today=TODAY
    )
    assert findings == []


def test_terminology_check_skips_missing_rule_citation():
    missing_rule_terms = [dict(TERMS[0], rule_code="BG-404")]
    findings, warnings = check_terminology(
        "Use Dashboard now.", RULES, missing_rule_terms, today=TODAY
    )
    assert findings == []
    assert any("BG-404" in warning for warning in warnings)


def test_price_mismatch_is_linked_to_approved_fact():
    findings = check_fact_mismatches(
        "Get access for only ₹799 per month!", FACTS, today=TODAY
    )
    assert len(findings) == 1
    assert findings[0]["source_id"] == "FACT-001"
    assert findings[0]["verification_status"] == "mismatch_with_approved_fact"
    assert findings[0]["metadata"]["approved_value"] == "999"
    assert "799" in findings[0]["metadata"]["mentioned_values"]


def test_correct_price_does_not_flag():
    findings = check_fact_mismatches(
        "Get access for only ₹999 per month!", FACTS, today=TODAY
    )
    assert findings == []


def test_expired_fact_is_not_used():
    expired = [dict(FACTS[0], valid_until=date(2026, 10, 1))]
    findings = check_fact_mismatches(
        "Get access for only ₹799 per month!", expired, today=TODAY
    )
    assert findings == []
