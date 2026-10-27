from datetime import date

from app.services.retrieval import build_candidates, keyword_score, rank_candidates

TODAY = date(2026, 10, 27)
RULES = [
    {
        "rule_code": "BG-002", "category": "terminology", "title": "Use approved product name",
        "rule_text": "Refer to the product as Northstar Workspace. Do not use Dashboard as a substitute product name.",
        "source": "Northstar Terminology Guide", "source_section": "Section 1 - Product naming",
        "severity": "warning", "status": "active", "effective_date": date(2026, 10, 1),
    },
    {
        "rule_code": "BG-003", "category": "promotional_claim", "title": "Avoid unsupported guaranteed outcomes",
        "rule_text": "Do not promise guaranteed sales, revenue, productivity or business outcomes without approved evidence.",
        "source": "Northstar Claims Policy", "source_section": "Section 4 - Promotional claims",
        "severity": "high", "status": "active", "effective_date": date(2026, 10, 1),
    },
    {
        "rule_code": "BG-005", "category": "accessibility", "title": "Maintain readable text contrast",
        "rule_text": "Ordinary text should have sufficient contrast against its actual background.",
        "source": "Northstar Accessibility Guide", "source_section": "Section 1 - Text contrast",
        "severity": "warning", "status": "active", "effective_date": date(2026, 10, 1),
    },
]
FACTS = [
    {
        "fact_code": "FACT-001", "name": "Monthly subscription price", "value": "999", "unit": "INR/month",
        "source": "Northstar Approved Product Facts", "source_section": "Pricing",
        "valid_from": date(2026, 10, 1), "valid_until": None, "status": "active",
    }
]


def test_keyword_retrieval_ranks_matching_rule_first():
    candidates = build_candidates(RULES, FACTS, today=TODAY)
    ranked = rank_candidates("Dashboard product name terminology", candidates, semantic_scores=None, top_k=5)
    assert ranked[0]["source_id"] == "BG-002"
    assert ranked[0]["source"] == "Northstar Terminology Guide"
    assert ranked[0]["source_section"] == "Section 1 - Product naming"
    assert ranked[0]["keyword_score"] > 0


def test_hybrid_ranking_can_use_semantic_similarity_for_synonyms():
    candidates = build_candidates(RULES, FACTS, today=TODAY)
    semantic_scores = {
        "rule:BG-002": 0.10,
        "rule:BG-003": 0.86,
        "rule:BG-005": 0.08,
        "fact:FACT-001": 0.12,
    }
    ranked = rank_candidates("promises a guaranteed increase in revenue", candidates, semantic_scores, top_k=4)
    assert ranked[0]["source_id"] == "BG-003"
    assert ranked[0]["semantic_score"] == 0.86
    assert ranked[0]["combined_score"] > ranked[1]["combined_score"]


def test_candidate_builder_keeps_rule_and_fact_provenance():
    candidates = build_candidates(RULES, FACTS, today=TODAY)
    by_id = {candidate["source_id"]: candidate for candidate in candidates}
    assert by_id["BG-003"]["source_type"] == "rule"
    assert by_id["BG-003"]["source_section"] == "Section 4 - Promotional claims"
    assert by_id["FACT-001"]["source_type"] == "fact"
    assert by_id["FACT-001"]["source_section"] == "Pricing"
    assert "999" in by_id["FACT-001"]["text"]


def test_inactive_rule_is_excluded():
    inactive = [dict(RULES[0], status="inactive")]
    candidates = build_candidates(inactive, [], today=TODAY)
    assert candidates == []


def test_keyword_score_is_bounded():
    score = keyword_score("approved product name", "Use the approved product name consistently")
    assert 0 <= score <= 1
