from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RuleStatus = Literal["active", "inactive"]
FactStatus = Literal["active", "inactive"]


class RuleCreate(BaseModel):
    rule_code: str = Field(min_length=3, max_length=40)
    category: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=3, max_length=160)
    rule_text: str = Field(min_length=5)
    source: str = Field(min_length=2, max_length=200)
    source_section: str | None = Field(default=None, max_length=120)
    severity: str = Field(default="warning", max_length=20)
    status: RuleStatus = "active"
    effective_date: date | None = None


class RuleUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=2, max_length=50)
    title: str | None = Field(default=None, min_length=3, max_length=160)
    rule_text: str | None = Field(default=None, min_length=5)
    source: str | None = Field(default=None, min_length=2, max_length=200)
    source_section: str | None = Field(default=None, max_length=120)
    severity: str | None = Field(default=None, max_length=20)
    status: RuleStatus | None = None
    effective_date: date | None = None


class RuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_code: str
    category: str
    title: str
    rule_text: str
    source: str
    source_section: str | None
    severity: str
    status: str
    effective_date: date | None
    created_at: datetime
    updated_at: datetime


class FactCreate(BaseModel):
    fact_code: str = Field(min_length=3, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    value: str = Field(min_length=1)
    unit: str | None = Field(default=None, max_length=80)
    source: str = Field(min_length=2, max_length=200)
    source_section: str | None = Field(default=None, max_length=120)
    valid_from: date | None = None
    valid_until: date | None = None
    status: FactStatus = "active"


class FactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fact_code: str
    name: str
    value: str
    unit: str | None
    source: str
    source_section: str | None
    valid_from: date | None
    valid_until: date | None
    status: str
    created_at: datetime
