"""Phase 2 endpoints: deterministic local checks and hybrid rule/fact retrieval."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApprovedFact, BrandRule
from app.schemas_phase2 import (
    LocalCheckRequest,
    LocalCheckResponse,
    LocalFinding,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalStatusResponse,
)
from app.services.local_checks import check_fact_mismatches, check_terminology, load_terminology_config
from app.services.retrieval import get_model_status, search_sources

router = APIRouter()


@router.post("/checks/local", response_model=LocalCheckResponse)
def run_local_checks(payload: LocalCheckRequest, db: Session = Depends(get_db)) -> LocalCheckResponse:
    """Run credit-free terminology and approved numeric-fact checks."""
    today = date.today()
    rules = list(db.scalars(select(BrandRule).where(BrandRule.status == "active")).all())
    facts = list(db.scalars(select(ApprovedFact).where(ApprovedFact.status == "active")).all())
    terms, config_warnings = load_terminology_config()

    terminology_findings, terminology_warnings = check_terminology(
        payload.content, rules=rules, terms=terms, today=today
    )
    fact_findings = check_fact_mismatches(payload.content, facts=facts, today=today)
    findings = terminology_findings + fact_findings
    warnings = config_warnings + terminology_warnings
    return LocalCheckResponse(
        total_findings=len(findings),
        findings=[LocalFinding(**finding) for finding in findings],
        checks_run=["terminology", "approved_numeric_facts"],
        warnings=warnings,
    )


@router.post("/retrieval/search", response_model=RetrievalResponse)
def retrieve_brand_sources(payload: RetrievalRequest, db: Session = Depends(get_db)) -> RetrievalResponse:
    """Retrieve active, currently valid brand rules and approved facts for a query."""
    rules = list(db.scalars(select(BrandRule).where(BrandRule.status == "active")).all())
    facts = list(db.scalars(select(ApprovedFact).where(ApprovedFact.status == "active")).all())
    result = search_sources(
        query=payload.query,
        rules=rules,
        facts=facts,
        top_k=payload.top_k,
        include_facts=payload.include_facts,
        use_semantic=payload.use_semantic,
        today=date.today(),
    )
    return RetrievalResponse(
        query=payload.query,
        retrieval_mode=result["retrieval_mode"],
        model_name=result.get("model_name"),
        results=result["results"],
        warnings=result.get("warnings", []),
    )


@router.get("/retrieval/status", response_model=RetrievalStatusResponse)
def retrieval_status() -> RetrievalStatusResponse:
    """Report model/cache state without triggering a model download."""
    status = get_model_status()
    terms, config_warnings = load_terminology_config()
    notes = [
        "The embedding model is loaded lazily on the first semantic retrieval request.",
        "The first successful use may download the model files; subsequent requests reuse the local cache.",
        "Embedding vectors are cached in process memory for this MVP and are rebuilt after a backend restart.",
    ]
    notes.extend(config_warnings)
    return RetrievalStatusResponse(
        model_name=status["model_name"],
        model_loaded=status["model_loaded"],
        cached_embedding_count=status["cached_embedding_count"],
        terminology_config_loaded=not bool(config_warnings),
        terminology_term_count=len(terms),
        notes=notes,
    )
