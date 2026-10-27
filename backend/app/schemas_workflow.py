"""API schemas for persisted review workflows."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ReviewStatus = Literal["submitted", "needs_revision", "resubmitted", "approved"]
DecisionType = Literal["approved", "needs_revision"]


class ReviewCreateRequest(BaseModel):
    title: str = Field(default="Untitled content review", min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20_000)
    top_k: int = Field(default=5, ge=1, le=10)
    use_semantic: bool = True


class ContentRevisionRequest(BaseModel):
    base_version_id: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=20_000)
    top_k: int = Field(default=5, ge=1, le=10)
    use_semantic: bool = True


class ReviewDecisionRequest(BaseModel):
    version_id: int = Field(gt=0)
    reviewer_name: str = Field(min_length=1, max_length=160)
    decision: DecisionType
    comment: str | None = Field(default=None, max_length=4_000)
    acknowledge_partial_review: bool = False


class ReviewFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    origin: Literal["local", "ai", "hybrid"]
    check_type: str | None = None
    category: str
    severity: str
    excerpt: str
    explanation: str
    source_type: str | None = None
    source_id: str | None = None
    source: str | None = None
    source_section: str | None = None
    suggestion: str | None = None
    verification_status: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    validation_warnings: list[str] = Field(default_factory=list)
    created_at: datetime


class ReviewVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    version_number: int
    content: str
    overall_status: Literal["complete", "partial"]
    llm_status: str
    summary: str
    retrieval_mode: str
    retrieved_source_count: int
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    findings: list[ReviewFindingRead] = Field(default_factory=list)


class ReviewDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    version_id: int
    reviewer_name: str
    decision: DecisionType
    comment: str | None = None
    acknowledged_partial_review: bool
    created_at: datetime
    version_number: int


class ReviewSummaryRead(BaseModel):
    id: int
    title: str
    status: ReviewStatus
    current_version_id: int | None = None
    current_version_number: int | None = None
    overall_status: str | None = None
    summary: str | None = None
    finding_count: int = 0
    created_at: datetime
    updated_at: datetime


class ReviewDetailRead(BaseModel):
    id: int
    title: str
    status: ReviewStatus
    created_at: datetime
    updated_at: datetime
    current_version: ReviewVersionRead | None = None
    versions: list[ReviewVersionRead] = Field(default_factory=list)
    decisions: list[ReviewDecisionRead] = Field(default_factory=list)
