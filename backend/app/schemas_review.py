"""Pydantic schemas for the contextual content-review API."""
from typing import Literal

from pydantic import BaseModel, Field

ReviewCategory = Literal[
    "tone",
    "messaging",
    "terminology",
    "promotional_claim",
    "factual_accuracy",
    "visual_consistency",
    "accessibility",
    "other",
]
FindingSeverity = Literal["info", "low", "medium", "high", "critical"]
VerificationStatus = Literal["source_cited", "needs_human_review", "unverified"]
LLMStatus = Literal[
    "completed",
    "not_configured",
    "rate_limited",
    "authentication_failed",
    "provider_unavailable",
    "provider_error",
    "invalid_response",
]


class ContentReviewRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    top_k: int = Field(default=5, ge=1, le=10)
    use_semantic: bool = True


class ModelFinding(BaseModel):
    """Untrusted structured output requested from the LLM."""

    category: ReviewCategory
    severity: FindingSeverity = "medium"
    excerpt: str = Field(min_length=1, max_length=1_000)
    explanation: str = Field(min_length=1, max_length=2_000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=10)
    suggestion: str | None = Field(default=None, max_length=2_000)
    verification_status: VerificationStatus = "needs_human_review"


class ModelReviewPayload(BaseModel):
    summary: str = Field(default="", max_length=2_000)
    findings: list[ModelFinding] = Field(default_factory=list, max_length=30)


class EvidenceReference(BaseModel):
    source_type: Literal["rule", "fact"]
    source_id: str
    title: str
    source: str
    source_section: str | None = None


class AIReviewFinding(BaseModel):
    category: ReviewCategory
    severity: FindingSeverity
    excerpt: str
    explanation: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    suggestion: str | None = None
    verification_status: VerificationStatus
    validation_warnings: list[str] = Field(default_factory=list)


class ContentReviewResponse(BaseModel):
    overall_status: Literal["complete", "partial"]
    llm_status: LLMStatus
    summary: str
    local_findings: list[dict] = Field(default_factory=list)
    ai_findings: list[AIReviewFinding] = Field(default_factory=list)
    retrieval_mode: Literal["hybrid", "keyword_fallback", "keyword_only"]
    retrieved_source_count: int
    warnings: list[str] = Field(default_factory=list)

