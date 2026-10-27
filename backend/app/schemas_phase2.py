from typing import Any, Literal
from pydantic import BaseModel, Field

class LocalCheckRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)

class LocalFinding(BaseModel):
    check_type: Literal["terminology", "fact_mismatch"]
    category: str
    severity: str
    excerpt: str
    message: str
    source_type: Literal["rule", "fact"]
    source_id: str | None = None
    source: str | None = None
    source_section: str | None = None
    replacement: str | None = None
    verification_status: str
    metadata: dict[str, Any] = Field(default_factory=dict)

class LocalCheckResponse(BaseModel):
    total_findings: int
    findings: list[LocalFinding]
    checks_run: list[str]
    warnings: list[str] = Field(default_factory=list)

class RetrievalRequest(BaseModel):
    query: str = Field(min_length=2, max_length=5_000)
    top_k: int = Field(default=5, ge=1, le=10)
    include_facts: bool = True
    use_semantic: bool = True

class RetrievedSource(BaseModel):
    source_type: Literal["rule", "fact"]
    source_id: str
    title: str
    text: str
    source: str
    source_section: str | None = None
    category: str
    severity: str | None = None
    status: str
    keyword_score: float
    semantic_score: float | None = None
    combined_score: float
    effective_date: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None

class RetrievalResponse(BaseModel):
    query: str
    retrieval_mode: Literal["hybrid", "keyword_fallback", "keyword_only"]
    model_name: str | None = None
    results: list[RetrievedSource]
    warnings: list[str] = Field(default_factory=list)

class RetrievalStatusResponse(BaseModel):
    model_name: str
    model_loaded: bool
    cached_embedding_count: int
    terminology_config_loaded: bool
    terminology_term_count: int
    notes: list[str] = Field(default_factory=list)
