"""Endpoint for a complete local + RAG + contextual AI review request."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas_review import ContentReviewRequest, ContentReviewResponse
from app.services.review_engine import analyze_content

router = APIRouter()


@router.post("/reviews/analyze", response_model=ContentReviewResponse)
async def analyze_submitted_content(
    payload: ContentReviewRequest,
    db: Session = Depends(get_db),
) -> ContentReviewResponse:
    """Run local checks and RAG first, then optional hosted LLM analysis.

    A provider failure returns a partial result rather than a false clean pass.
    """
    return await analyze_content(
        content=payload.content,
        db=db,
        top_k=payload.top_k,
        use_semantic=payload.use_semantic,
    )
