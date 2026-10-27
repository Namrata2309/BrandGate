from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApprovedFact, BrandRule
from app.schemas import FactCreate, FactRead, RuleCreate, RuleRead, RuleUpdate

router = APIRouter()


@router.get("/rules", response_model=list[RuleRead])
def list_rules(
    status_filter: str = Query(default="active", alias="status", pattern="^(active|inactive|all)$"),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[BrandRule]:
    query = select(BrandRule)
    if status_filter != "all":
        query = query.where(BrandRule.status == status_filter)
    if category:
        query = query.where(BrandRule.category == category)
    query = query.order_by(BrandRule.rule_code.asc())
    return list(db.scalars(query).all())


@router.post("/rules", response_model=RuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)) -> BrandRule:
    rule = BrandRule(**payload.model_dump())
    db.add(rule)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule code '{payload.rule_code}' already exists.",
        ) from exc
    db.refresh(rule)
    return rule


@router.get("/rules/{rule_id}", response_model=RuleRead)
def get_rule(rule_id: int, db: Session = Depends(get_db)) -> BrandRule:
    rule = db.get(BrandRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found.")
    return rule


@router.put("/rules/{rule_id}", response_model=RuleRead)
def update_rule(rule_id: int, payload: RuleUpdate, db: Session = Depends(get_db)) -> BrandRule:
    rule = db.get(BrandRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found.")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(rule, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="The rule could not be updated due to a data conflict.") from exc
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", response_model=RuleRead)
def deactivate_rule(rule_id: int, db: Session = Depends(get_db)) -> BrandRule:
    """Soft-delete a rule so past findings can still refer to it."""
    rule = db.get(BrandRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found.")
    rule.status = "inactive"
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/facts", response_model=list[FactRead])
def list_facts(
    status_filter: str = Query(default="active", alias="status", pattern="^(active|inactive|all)$"),
    db: Session = Depends(get_db),
) -> list[ApprovedFact]:
    query = select(ApprovedFact)
    if status_filter != "all":
        query = query.where(ApprovedFact.status == status_filter)
    query = query.order_by(ApprovedFact.fact_code.asc())
    return list(db.scalars(query).all())


@router.post("/facts", response_model=FactRead, status_code=status.HTTP_201_CREATED)
def create_fact(payload: FactCreate, db: Session = Depends(get_db)) -> ApprovedFact:
    fact = ApprovedFact(**payload.model_dump())
    db.add(fact)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Fact code '{payload.fact_code}' already exists.",
        ) from exc
    db.refresh(fact)
    return fact
