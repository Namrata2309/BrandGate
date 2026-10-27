from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import ApprovedFact, BrandRule
from app.services.review_engine import analyze_content


class FakeProvider:
    configured = True

    async def complete_json(self, system_prompt, user_prompt):
        assert "CONTENT TO REVIEW" in user_prompt
        assert "RETRIEVED APPROVED SOURCES" in user_prompt
        return {
            "summary": "A promotional claim needs review.",
            "findings": [{
                "category": "promotional_claim",
                "severity": "high",
                "excerpt": "guarantees double their sales",
                "explanation": "The supplied policy does not support this guarantee.",
                "evidence_ids": ["BG-003"],
                "suggestion": "Explore tools designed to support sales growth.",
                "verification_status": "source_cited",
            }],
        }


class UnconfiguredProvider:
    configured = False


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    db.add_all([
        BrandRule(
            rule_code="BG-002", category="terminology", title="Product terminology",
            rule_text="Use Northstar Workspace, not Dashboard.", source="Brand Guide",
            source_section="Section 1", severity="warning", status="active",
            effective_date=date(2026, 1, 1),
        ),
        BrandRule(
            rule_code="BG-003", category="promotional_claim", title="Unsupported guarantees",
            rule_text="Do not guarantee business outcomes without approved evidence.",
            source="Claims Policy", source_section="Section 4", severity="high",
            status="active", effective_date=date(2026, 1, 1),
        ),
        ApprovedFact(
            fact_code="FACT-001", name="Monthly subscription price", value="999",
            unit="INR/month", source="Product Fact Sheet", source_section="Section 2",
            valid_from=date(2026, 1, 1), valid_until=None, status="active",
        ),
    ])
    db.commit()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.asyncio
async def test_analysis_returns_local_and_validated_ai_findings(db_session):
    result = await analyze_content(
        "Our Dashboard guarantees double their sales. Pay ₹799 per month!",
        db_session,
        top_k=5,
        use_semantic=False,
        provider=FakeProvider(),
    )
    assert result.overall_status == "complete"
    assert result.llm_status == "completed"
    assert any(item["source_id"] == "BG-002" for item in result.local_findings)
    assert any(item["source_id"] == "FACT-001" for item in result.local_findings)
    assert result.ai_findings[0].evidence_ids == ["BG-003"]
    assert result.ai_findings[0].evidence[0].source == "Claims Policy"
    assert result.ai_findings[0].verification_status == "needs_human_review"


@pytest.mark.asyncio
async def test_unconfigured_llm_returns_partial_not_clean_pass(db_session):
    result = await analyze_content(
        "A simple draft.",
        db_session,
        top_k=5,
        use_semantic=False,
        provider=UnconfiguredProvider(),
    )
    assert result.overall_status == "partial"
    assert result.llm_status == "not_configured"
    assert result.ai_findings == []
    assert any("not configured" in warning.lower() for warning in result.warnings)
