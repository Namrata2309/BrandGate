"""Persisted review workflow APIs: create, revise, inspect and decide by version."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.review_models import ContentReview, ReviewDecision
from app.schemas_review import ContentReviewResponse
from app.schemas_workflow import (
    ContentRevisionRequest,
    ReviewCreateRequest,
    ReviewDecisionRequest,
    ReviewDetailRead,
    ReviewSummaryRead,
)
from app.services.review_engine import analyze_content
from app.services.review_persistence import (
    create_version_from_analysis,
    get_latest_version,
    review_detail_to_dict,
    review_summary_to_dict,
)

router = APIRouter()


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Review not found.")


@router.post("/workflow/reviews", response_model=ReviewDetailRead, status_code=status.HTTP_201_CREATED)
async def create_review(payload: ReviewCreateRequest, db: Session = Depends(get_db)) -> dict:
    """Create a review, run Phase 3 analysis, and persist version 1 plus findings."""
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Content cannot be blank.")

    # Run the potentially slow external analysis before opening a write
    # transaction, so the SQLite write lock is not held during an API call.
    analysis = await analyze_content(
        content=content,
        db=db,
        top_k=payload.top_k,
        use_semantic=payload.use_semantic,
    )
    review = ContentReview(title=payload.title.strip() or "Untitled content review", status="submitted")
    db.add(review)
    try:
        db.flush()
        create_version_from_analysis(
            db, review, version_number=1, content=content, analysis=analysis
        )
        review.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(review)
    except Exception:
        db.rollback()
        raise
    return review_detail_to_dict(db, review)


@router.get("/workflow/reviews", response_model=list[ReviewSummaryRead])
def list_reviews(db: Session = Depends(get_db)) -> list[dict]:
    reviews = list(db.scalars(
        select(ContentReview).order_by(ContentReview.updated_at.desc(), ContentReview.id.desc())
    ).all())
    return [review_summary_to_dict(db, review) for review in reviews]


@router.get("/workflow/reviews/{review_id}", response_model=ReviewDetailRead)
def get_review(review_id: int, db: Session = Depends(get_db)) -> dict:
    review = db.get(ContentReview, review_id)
    if review is None:
        raise _not_found()
    return review_detail_to_dict(db, review)


@router.post("/workflow/reviews/{review_id}/versions", response_model=ReviewDetailRead, status_code=status.HTTP_201_CREATED)
async def submit_revision(
    review_id: int,
    payload: ContentRevisionRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Create and analyse an immutable new version based on the latest known version."""
    review = db.get(ContentReview, review_id)
    if review is None:
        raise _not_found()
    latest = get_latest_version(db, review_id)
    if latest is None:
        raise HTTPException(status_code=409, detail="Review has no content version to revise.")
    if payload.base_version_id != latest.id:
        raise HTTPException(
            status_code=409,
            detail="This review has a newer version. Reload it before submitting a revision.",
        )

    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Content cannot be blank.")
    if content == latest.content:
        raise HTTPException(status_code=422, detail="No content changes detected. Edit the draft before resubmitting.")

    # Run analysis before committing the new version. Existing versions and decisions stay unchanged.
    analysis = await analyze_content(
        content=content,
        db=db,
        top_k=payload.top_k,
        use_semantic=payload.use_semantic,
    )
    new_number = latest.version_number + 1
    try:
        create_version_from_analysis(
            db, review, version_number=new_number, content=content, analysis=analysis
        )
        review.status = "resubmitted"
        review.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(review)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A concurrent revision was saved. Reload the review and try again.",
        ) from exc
    except Exception:
        db.rollback()
        raise
    return review_detail_to_dict(db, review)


@router.post("/workflow/reviews/{review_id}/decisions", response_model=ReviewDetailRead)
def record_decision(
    review_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Record a human decision against the latest version only."""
    review = db.get(ContentReview, review_id)
    if review is None:
        raise _not_found()
    latest = get_latest_version(db, review_id)
    if latest is None:
        raise HTTPException(status_code=409, detail="Review has no content version.")
    if payload.version_id != latest.id:
        raise HTTPException(
            status_code=409,
            detail="Decisions can only be recorded against the latest version. Reload the review.",
        )
    if not payload.reviewer_name.strip():
        raise HTTPException(status_code=422, detail="Reviewer name cannot be blank.")
    if payload.decision == "approved" and latest.overall_status == "partial" and not payload.acknowledge_partial_review:
        raise HTTPException(
            status_code=409,
            detail="The AI review was incomplete. Explicitly acknowledge this before recording approval.",
        )
    if payload.decision == "needs_revision" and not (payload.comment or "").strip():
        raise HTTPException(
            status_code=422,
            detail="A comment is required when requesting revisions.",
        )

    decision = ReviewDecision(
        review_id=review.id,
        version_id=latest.id,
        reviewer_name=payload.reviewer_name.strip(),
        decision=payload.decision,
        comment=(payload.comment or "").strip() or None,
        acknowledged_partial_review=payload.acknowledge_partial_review,
    )
    db.add(decision)
    review.status = payload.decision
    review.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review_detail_to_dict(db, review)
