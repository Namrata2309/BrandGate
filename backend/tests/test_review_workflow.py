from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app import models  # noqa: F401 - register Phase 1 tables
from app import review_models  # noqa: F401 - register workflow tables
from app.api import review_workflow
from app.schemas_review import AIReviewFinding, ContentReviewResponse, EvidenceReference


def make_analysis(content: str, partial: bool = False) -> ContentReviewResponse:
    local = []
    if "Dashboard" in content:
        local.append({
            "check_type": "terminology",
            "category": "terminology",
            "severity": "warning",
            "excerpt": content[max(0, content.index("Dashboard") - 10):content.index("Dashboard") + 20],
            "message": "Use the approved product name.",
            "source_type": "rule",
            "source_id": "BG-002",
            "source": "Northstar Terminology Guide",
            "source_section": "Section 1",
            "replacement": "Northstar Workspace",
            "verification_status": "rule_match",
            "metadata": {
                "matched_term": "Dashboard",
                "occurrences": 1,
                "positions": [{"start": content.index("Dashboard"), "end": content.index("Dashboard") + len("Dashboard")}],
            },
        })
    ai = [AIReviewFinding(
        category="promotional_claim",
        severity="high",
        excerpt="guarantees sales growth",
        explanation="The supplied evidence does not support a guaranteed outcome.",
        evidence_ids=["BG-003"],
        evidence=[EvidenceReference(
            source_type="rule", source_id="BG-003", title="Promotional claims",
            source="Northstar Claims Policy", source_section="Section 4",
        )],
        suggestion="is designed to help teams identify growth opportunities",
        verification_status="needs_human_review",
        validation_warnings=[],
    )] if "guarantees" in content.casefold() else []
    return ContentReviewResponse(
        overall_status="partial" if partial else "complete",
        llm_status="provider_error" if partial else "completed",
        summary="Mock review summary",
        local_findings=local,
        ai_findings=ai,
        retrieval_mode="hybrid",
        retrieved_source_count=3,
        warnings=["mock provider unavailable"] if partial else [],
    )


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(review_workflow.router, prefix="/api")
    app.dependency_overrides[get_db] = override_get_db

    async def fake_analyze_content(content, db, *, top_k=5, use_semantic=True, provider=None):
        return make_analysis(content)

    monkeypatch.setattr(review_workflow, "analyze_content", fake_analyze_content)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def create_sample_review(client: TestClient, content: str = "Our Dashboard guarantees sales growth.") -> dict:
    response = client.post("/api/workflow/reviews", json={"title": "Demo post", "content": content})
    assert response.status_code == 201, response.text
    return response.json()


def test_create_review_persists_v1_and_findings(client: TestClient):
    body = create_sample_review(client)
    assert body["status"] == "submitted"
    assert body["current_version"]["version_number"] == 1
    assert body["current_version"]["content"] == "Our Dashboard guarantees sales growth."
    assert len(body["current_version"]["findings"]) == 2
    assert body["current_version"]["findings"][0]["source_id"] == "BG-002"

    loaded = client.get(f"/api/workflow/reviews/{body['id']}")
    assert loaded.status_code == 200
    assert len(loaded.json()["versions"]) == 1


def test_revision_creates_new_immutable_version(client: TestClient):
    body = create_sample_review(client)
    current = body["current_version"]
    response = client.post(f"/api/workflow/reviews/{body['id']}/versions", json={
        "base_version_id": current["id"],
        "content": "Our Northstar Workspace is designed to help teams grow.",
    })
    assert response.status_code == 201, response.text
    updated = response.json()
    assert updated["status"] == "resubmitted"
    assert updated["current_version"]["version_number"] == 2
    assert updated["versions"][-1]["content"] == current["content"]


def test_approval_is_bound_to_version_and_old_version_cannot_be_approved_after_revision(client: TestClient):
    body = create_sample_review(client, "Our Dashboard helps teams work.")
    v1 = body["current_version"]
    approval = client.post(f"/api/workflow/reviews/{body['id']}/decisions", json={
        "version_id": v1["id"], "reviewer_name": "Reviewer", "decision": "approved"
    })
    assert approval.status_code == 200, approval.text
    assert approval.json()["decisions"][0]["version_id"] == v1["id"]

    revision = client.post(f"/api/workflow/reviews/{body['id']}/versions", json={
        "base_version_id": v1["id"], "content": "Our Northstar Workspace helps teams work."
    })
    assert revision.status_code == 201, revision.text
    v2 = revision.json()["current_version"]
    assert revision.json()["status"] == "resubmitted"
    assert revision.json()["decisions"][0]["version_id"] == v1["id"]

    stale_approval = client.post(f"/api/workflow/reviews/{body['id']}/decisions", json={
        "version_id": v1["id"], "reviewer_name": "Reviewer", "decision": "approved"
    })
    assert stale_approval.status_code == 409

    current_approval = client.post(f"/api/workflow/reviews/{body['id']}/decisions", json={
        "version_id": v2["id"], "reviewer_name": "Reviewer", "decision": "approved"
    })
    assert current_approval.status_code == 200
    assert current_approval.json()["status"] == "approved"
    assert current_approval.json()["decisions"][0]["version_id"] == v2["id"]


def test_partial_review_requires_explicit_acknowledgement(client: TestClient, monkeypatch):
    async def fake_partial(content, db, *, top_k=5, use_semantic=True, provider=None):
        return make_analysis(content, partial=True)
    monkeypatch.setattr(review_workflow, "analyze_content", fake_partial)
    body = create_sample_review(client, "A draft with a potential risk.")
    version = body["current_version"]

    rejected = client.post(f"/api/workflow/reviews/{body['id']}/decisions", json={
        "version_id": version["id"], "reviewer_name": "Reviewer", "decision": "approved"
    })
    assert rejected.status_code == 409

    accepted = client.post(f"/api/workflow/reviews/{body['id']}/decisions", json={
        "version_id": version["id"], "reviewer_name": "Reviewer", "decision": "approved",
        "acknowledge_partial_review": True,
    })
    assert accepted.status_code == 200
    assert accepted.json()["decisions"][0]["acknowledged_partial_review"] is True


def test_request_revision_requires_comment(client: TestClient):
    body = create_sample_review(client)
    response = client.post(f"/api/workflow/reviews/{body['id']}/decisions", json={
        "version_id": body["current_version"]["id"],
        "reviewer_name": "Reviewer",
        "decision": "needs_revision",
    })
    assert response.status_code == 422


def test_stale_revision_base_is_rejected(client: TestClient):
    body = create_sample_review(client)
    v1 = body["current_version"]
    new_version = client.post(f"/api/workflow/reviews/{body['id']}/versions", json={
        "base_version_id": v1["id"], "content": "An edited and improved draft."
    })
    assert new_version.status_code == 201
    stale = client.post(f"/api/workflow/reviews/{body['id']}/versions", json={
        "base_version_id": v1["id"], "content": "Another edit made from stale version one."
    })
    assert stale.status_code == 409


def test_same_local_and_ai_source_is_saved_as_one_hybrid_finding(client: TestClient, monkeypatch):
    async def fake_duplicate(content, db, *, top_k=5, use_semantic=True, provider=None):
        local_result = make_analysis("Our Dashboard helps teams work.")
        return ContentReviewResponse(
            overall_status="complete",
            llm_status="completed",
            summary="Review completed",
            local_findings=local_result.local_findings,
            ai_findings=[AIReviewFinding(
                category="terminology",
                severity="medium",
                excerpt="Dashboard",
                explanation="The alternate name can confuse users about the official product name.",
                evidence_ids=["BG-002"],
                evidence=[EvidenceReference(
                    source_type="rule", source_id="BG-002", title="Product naming",
                    source="Northstar Terminology Guide", source_section="Section 1",
                )],
                suggestion="Northstar Workspace",
                verification_status="needs_human_review",
                validation_warnings=[],
            )],
            retrieval_mode="hybrid",
            retrieved_source_count=2,
            warnings=[],
        )
    monkeypatch.setattr(review_workflow, "analyze_content", fake_duplicate)
    body = create_sample_review(client, "Our Dashboard helps teams work.")
    findings = body["current_version"]["findings"]
    assert len(findings) == 1
    assert findings[0]["origin"] == "hybrid"
    assert "AI context:" in findings[0]["explanation"]
