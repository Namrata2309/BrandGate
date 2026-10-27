"""Persistence helpers for review analysis results and version history."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.review_models import ContentReview, ContentVersion, ReviewDecision, ReviewFinding
from app.schemas_review import ContentReviewResponse


def get_latest_version(db: Session, review_id: int) -> ContentVersion | None:
    return db.scalars(
        select(ContentVersion)
        .where(ContentVersion.review_id == review_id)
        .order_by(ContentVersion.version_number.desc())
        .limit(1)
    ).first()


def persist_analysis_findings(
    db: Session,
    version: ContentVersion,
    analysis: ContentReviewResponse,
) -> list[ReviewFinding]:
    """Normalize Phase 2 and Phase 3 results into a durable finding table."""
    records: list[ReviewFinding] = []

    for item in analysis.local_findings:
        finding = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        source_type = finding.get("source_type")
        source_id = finding.get("source_id")
        evidence = []
        if source_id:
            evidence.append({
                "source_type": source_type or "rule",
                "source_id": source_id,
                "title": (finding.get("metadata") or {}).get("fact_name") or finding.get("source_section") or finding.get("source") or source_id,
                "source": finding.get("source") or "Approved source",
                "source_section": finding.get("source_section"),
            })
        records.append(ReviewFinding(
            version_id=version.id,
            origin="local",
            check_type=finding.get("check_type"),
            category=finding.get("category", "other"),
            severity=finding.get("severity", "medium"),
            excerpt=finding.get("excerpt", ""),
            explanation=finding.get("message", "Local rule matched."),
            source_type=source_type,
            source_id=source_id,
            source=finding.get("source"),
            source_section=finding.get("source_section"),
            suggestion=finding.get("replacement"),
            verification_status=finding.get("verification_status", "needs_human_review"),
            evidence=evidence,
            metadata_json=finding.get("metadata") or {},
            validation_warnings=[],
        ))

    # Deterministic findings take precedence for exact matches. If the LLM
    # independently flags the same category and source ID, enrich the local
    # finding instead of showing users two cards for the same issue.
    local_by_source: dict[tuple[str, str], ReviewFinding] = {}
    for record in records:
        if record.source_id:
            local_by_source[(record.category, record.source_id)] = record

    for item in analysis.ai_findings:
        finding = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        evidence = finding.get("evidence") or []
        first = evidence[0] if evidence else {}
        category = finding.get("category", "other")
        matched_local = None
        for source_ref in evidence:
            source_id = str(source_ref.get("source_id", "")).strip()
            candidate = local_by_source.get((category, source_id))
            if candidate is not None:
                matched_local = candidate
                break

        if matched_local is not None:
            ai_explanation = str(finding.get("explanation", "")).strip()
            if ai_explanation and ai_explanation not in matched_local.explanation:
                matched_local.explanation = (
                    f"{matched_local.explanation.rstrip()}\nAI context: {ai_explanation}"
                )
            # Keep the exact local replacement where available; only use the
            # model's suggestion if the deterministic checker has none.
            if not matched_local.suggestion and finding.get("suggestion"):
                matched_local.suggestion = finding["suggestion"]
            combined_evidence = list(matched_local.evidence or [])
            seen_ids = {str(ref.get("source_id", "")) for ref in combined_evidence}
            combined_evidence.extend(
                ref for ref in evidence
                if str(ref.get("source_id", "")) not in seen_ids
            )
            matched_local.evidence = combined_evidence
            matched_local.validation_warnings = list(matched_local.validation_warnings or []) + list(finding.get("validation_warnings") or [])
            matched_local.origin = "hybrid"
            continue

        records.append(ReviewFinding(
            version_id=version.id,
            origin="ai",
            check_type=None,
            category=category,
            severity=finding.get("severity", "medium"),
            excerpt=finding.get("excerpt", ""),
            explanation=finding.get("explanation", ""),
            source_type=first.get("source_type"),
            source_id=first.get("source_id"),
            source=first.get("source"),
            source_section=first.get("source_section"),
            suggestion=finding.get("suggestion"),
            verification_status=finding.get("verification_status", "unverified"),
            evidence=evidence,
            metadata_json={},
            validation_warnings=finding.get("validation_warnings") or [],
        ))

    db.add_all(records)
    return records


def create_version_from_analysis(
    db: Session,
    review: ContentReview,
    *,
    version_number: int,
    content: str,
    analysis: ContentReviewResponse,
) -> ContentVersion:
    version = ContentVersion(
        review_id=review.id,
        version_number=version_number,
        content=content,
        overall_status=analysis.overall_status,
        llm_status=analysis.llm_status,
        summary=analysis.summary,
        retrieval_mode=analysis.retrieval_mode,
        retrieved_source_count=analysis.retrieved_source_count,
        warnings=list(analysis.warnings),
    )
    db.add(version)
    db.flush()  # obtains version.id before findings are linked
    persist_analysis_findings(db, version, analysis)
    return version


def version_to_dict(db: Session, version: ContentVersion) -> dict[str, Any]:
    findings = list(db.scalars(
        select(ReviewFinding).where(ReviewFinding.version_id == version.id).order_by(ReviewFinding.id.asc())
    ).all())
    return {
        "id": version.id,
        "review_id": version.review_id,
        "version_number": version.version_number,
        "content": version.content,
        "overall_status": version.overall_status,
        "llm_status": version.llm_status,
        "summary": version.summary,
        "retrieval_mode": version.retrieval_mode,
        "retrieved_source_count": version.retrieved_source_count,
        "warnings": version.warnings or [],
        "created_at": version.created_at,
        "findings": [finding for finding in findings],
    }


def review_detail_to_dict(db: Session, review: ContentReview) -> dict[str, Any]:
    versions = list(db.scalars(
        select(ContentVersion)
        .where(ContentVersion.review_id == review.id)
        .order_by(ContentVersion.version_number.desc())
    ).all())
    latest = versions[0] if versions else None
    decisions = list(db.scalars(
        select(ReviewDecision)
        .where(ReviewDecision.review_id == review.id)
        .order_by(ReviewDecision.created_at.desc(), ReviewDecision.id.desc())
    ).all())
    version_numbers = {version.id: version.version_number for version in versions}
    return {
        "id": review.id,
        "title": review.title,
        "status": review.status,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "current_version": version_to_dict(db, latest) if latest else None,
        "versions": [version_to_dict(db, version) for version in versions],
        "decisions": [
            {
                "id": decision.id,
                "review_id": decision.review_id,
                "version_id": decision.version_id,
                "reviewer_name": decision.reviewer_name,
                "decision": decision.decision,
                "comment": decision.comment,
                "acknowledged_partial_review": decision.acknowledged_partial_review,
                "created_at": decision.created_at,
                "version_number": version_numbers.get(decision.version_id, 0),
            }
            for decision in decisions
        ],
    }


def review_summary_to_dict(db: Session, review: ContentReview) -> dict[str, Any]:
    latest = get_latest_version(db, review.id)
    findings_count = 0
    if latest:
        findings_count = len(db.scalars(
            select(ReviewFinding.id).where(ReviewFinding.version_id == latest.id)
        ).all())
    return {
        "id": review.id,
        "title": review.title,
        "status": review.status,
        "current_version_id": latest.id if latest else None,
        "current_version_number": latest.version_number if latest else None,
        "overall_status": latest.overall_status if latest else None,
        "summary": latest.summary if latest else None,
        "finding_count": findings_count,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }
