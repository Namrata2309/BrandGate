from app.schemas_review import ModelReviewPayload
from app.services.review_engine import validate_ai_findings


def test_valid_retrieved_source_is_attached_but_requires_human_review():
    payload = ModelReviewPayload.model_validate({
        "summary": "Possible claim issue.",
        "findings": [{
            "category": "promotional_claim",
            "severity": "high",
            "excerpt": "guarantees double the sales",
            "explanation": "The retrieved policy does not support this guarantee.",
            "evidence_ids": ["BG-003"],
            "suggestion": "Explore tools designed to support sales growth.",
            "verification_status": "source_cited",
        }],
    })
    sources = [{
        "source_type": "rule",
        "source_id": "BG-003",
        "title": "Promotional claims",
        "source": "Claims Policy",
        "source_section": "Section 4",
    }]
    findings, warnings = validate_ai_findings(payload, sources)
    assert findings[0].evidence_ids == ["BG-003"]
    assert findings[0].evidence[0].source == "Claims Policy"
    assert findings[0].verification_status == "needs_human_review"
    assert warnings == []


def test_fabricated_source_id_is_removed_and_finding_marked_unverified():
    payload = ModelReviewPayload.model_validate({
        "summary": "Potential issue.",
        "findings": [{
            "category": "factual_accuracy",
            "severity": "medium",
            "excerpt": "Some statement",
            "explanation": "I cannot support this from retrieved evidence.",
            "evidence_ids": ["BG-999"],
            "suggestion": None,
            "verification_status": "source_cited",
        }],
    })
    findings, warnings = validate_ai_findings(payload, [])
    assert findings[0].evidence_ids == []
    assert findings[0].evidence == []
    assert findings[0].verification_status == "unverified"
    assert findings[0].validation_warnings
    assert warnings


def test_valid_and_invalid_ids_keep_only_real_source_ids():
    payload = ModelReviewPayload.model_validate({
        "findings": [{
            "category": "messaging",
            "severity": "low",
            "excerpt": "Our dashboard",
            "explanation": "Terminology may be inconsistent.",
            "evidence_ids": ["BG-002", "BG-999"],
            "suggestion": "Our Workspace",
            "verification_status": "source_cited",
        }],
    })
    sources = [{
        "source_type": "rule",
        "source_id": "BG-002",
        "title": "Product terminology",
        "source": "Brand Guide",
        "source_section": "Section 1",
    }]
    findings, warnings = validate_ai_findings(payload, sources)
    assert findings[0].evidence_ids == ["BG-002"]
    assert findings[0].verification_status == "unverified"
    assert warnings
